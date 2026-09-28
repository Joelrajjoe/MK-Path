import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, ScrollView, TouchableOpacity, ActivityIndicator, TextInput } from 'react-native';
import { getKnowledgeGraph, getMasteryEvidence } from '../services/api';

export default function KnowledgeGraphScreen({ navigation }) {
  const [graph, setGraph] = useState({ nodes: [], edges: [] });
  const [filter, setFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNode, setSelectedNode] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchGraph();
  }, []);

  const fetchGraph = async () => {
    try {
      setLoading(true);
      const data = await getKnowledgeGraph();
      setGraph(data);
    } catch (err) {
      console.warn('Failed to load knowledge graph:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectNode = async (node) => {
    setSelectedNode(node);
    try {
      const ev = await getMasteryEvidence(node.id || node._id);
      setEvidence(ev);
    } catch (err) {
      setEvidence(null);
    }
  };

  const filteredNodes = graph.nodes?.filter((n) => {
    const name = n.data?.label || n.name || '';
    const matchesSearch = name.toLowerCase().includes(searchQuery.toLowerCase());
    if (!matchesSearch) return false;

    const mastery = n.data?.mastery_score || 0;
    if (filter === 'WEAK') return mastery < 40;
    if (filter === 'LEARNING') return mastery >= 40 && mastery < 70;
    if (filter === 'MASTERED') return mastery >= 85;
    return true;
  }) || [];

  if (loading && (!graph.nodes || graph.nodes.length === 0)) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#6366f1" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>🕸️ Knowledge Graph</Text>
        <Text style={styles.subtitle}>Mobile concept topology & prerequisite pathways</Text>
      </View>

      {/* Search & Filter Bar */}
      <TextInput
        style={styles.searchInput}
        placeholder="Search concepts..."
        placeholderTextColor="#64748b"
        value={searchQuery}
        onChangeText={setSearchQuery}
      />

      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filterScroll}>
        {['ALL', 'WEAK', 'LEARNING', 'MASTERED'].map((f) => (
          <TouchableOpacity
            key={f}
            style={[styles.filterChip, filter === f && styles.filterChipActive]}
            onPress={() => setFilter(f)}
          >
            <Text style={[styles.filterChipText, filter === f && styles.filterChipTextActive]}>{f}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Node Grid View */}
      <ScrollView style={styles.graphCanvas}>
        <View style={styles.nodeGrid}>
          {filteredNodes.map((n) => {
            const mastery = Math.round(n.data?.mastery_score || 0);
            const isSelected = selectedNode && (selectedNode.id === n.id);
            const statusColor = mastery < 40 ? '#f43f5e' : mastery < 70 ? '#fbbf24' : '#10b981';

            return (
              <TouchableOpacity
                key={n.id}
                style={[styles.graphNode, isSelected && styles.graphNodeActive, { borderColor: statusColor }]}
                onPress={() => handleSelectNode(n)}
              >
                <Text style={styles.nodeLabel}>{n.data?.label || n.name}</Text>
                <Text style={[styles.nodeMastery, { color: statusColor }]}>{mastery}%</Text>
              </TouchableOpacity>
            );
          })}
        </View>

        {filteredNodes.length === 0 && (
          <View style={styles.empty}>
            <Text style={styles.emptyText}>No concepts match the current filter.</Text>
          </View>
        )}
      </ScrollView>

      {/* Selected Node Drawer */}
      {selectedNode && (
        <View style={styles.drawer}>
          <View style={styles.drawerHeader}>
            <Text style={styles.drawerTitle}>{selectedNode.data?.label || selectedNode.name}</Text>
            <TouchableOpacity onPress={() => setSelectedNode(null)}>
              <Text style={styles.closeBtn}>✕</Text>
            </TouchableOpacity>
          </View>

          <Text style={styles.drawerDesc}>{selectedNode.data?.description || 'Core curriculum knowledge element.'}</Text>
          
          <View style={styles.drawerMetrics}>
            <Text style={styles.drawerMetric}>Exam: {selectedNode.data?.exam_relevance || 80}%</Text>
            <Text style={styles.drawerMetric}>Industry: {selectedNode.data?.industry_relevance || 80}%</Text>
            <Text style={styles.drawerMetric}>Mastery: {Math.round(selectedNode.data?.mastery_score || 0)}%</Text>
          </View>

          {evidence && (
            <View style={styles.evidenceBox}>
              <Text style={styles.evidenceHeading}>BKT Uncertainty & Evidence:</Text>
              <Text style={styles.evidenceDetail}>
                Probability: {Math.round((evidence.bkt_probability || 0.5) * 100)}% • Uncertainty: {evidence.uncertainty_score?.toFixed(2) || '0.25'}
              </Text>
            </View>
          )}

          <TouchableOpacity
            style={styles.actionBtn}
            onPress={() => navigation.navigate('Assessment')}
          >
            <Text style={styles.actionBtnText}>Practice Concept Questions</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#090d16', paddingHorizontal: 16 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#090d16' },
  header: { marginTop: 20, marginBottom: 10 },
  title: { color: '#f8fafc', fontSize: 18, fontWeight: 'bold' },
  subtitle: { color: '#64748b', fontSize: 11, marginTop: 2 },
  
  searchInput: { backgroundColor: '#101726', borderWidth: 1, borderColor: '#1e293b', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 8, color: '#fff', fontSize: 12, marginBottom: 8 },
  filterScroll: { marginBottom: 10 },
  filterChip: { backgroundColor: '#101726', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 16, marginRight: 8, borderWidth: 1, borderColor: '#1e293b' },
  filterChipActive: { backgroundColor: '#6366f1', borderColor: '#818cf8' },
  filterChipText: { color: '#94a3b8', fontSize: 11, fontWeight: 'bold' },
  filterChipTextActive: { color: '#fff' },

  graphCanvas: { flex: 1 },
  nodeGrid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between' },
  graphNode: { width: '48%', backgroundColor: '#101726', borderWidth: 1.5, borderRadius: 12, padding: 12, marginBottom: 10 },
  graphNodeActive: { backgroundColor: '#172136', transform: [{ scale: 1.02 }] },
  nodeLabel: { color: '#ffffff', fontSize: 12, fontWeight: 'bold', marginBottom: 4 },
  nodeMastery: { fontSize: 12, fontWeight: 'bold' },

  drawer: { backgroundColor: '#101726', borderTopWidth: 1, borderColor: '#1e293b', padding: 16, borderTopLeftRadius: 16, borderTopRightRadius: 16, position: 'absolute', bottom: 0, left: 0, right: 0 },
  drawerHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  drawerTitle: { color: '#ffffff', fontSize: 15, fontWeight: 'bold' },
  closeBtn: { color: '#94a3b8', fontSize: 14, fontWeight: 'bold' },
  drawerDesc: { color: '#94a3b8', fontSize: 11, lineHeight: 16, marginBottom: 8 },
  drawerMetrics: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  drawerMetric: { color: '#cbd5e1', fontSize: 11, fontWeight: '600' },

  evidenceBox: { backgroundColor: '#172136', padding: 8, borderRadius: 8, marginBottom: 10 },
  evidenceHeading: { color: '#818cf8', fontSize: 10, fontWeight: 'bold' },
  evidenceDetail: { color: '#cbd5e1', fontSize: 10, marginTop: 2 },

  actionBtn: { backgroundColor: '#6366f1', paddingVertical: 10, borderRadius: 8, alignItems: 'center' },
  actionBtnText: { color: '#ffffff', fontSize: 12, fontWeight: 'bold' },
  empty: { padding: 40, alignItems: 'center' },
  emptyText: { color: '#64748b', fontSize: 12 }
});
