import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, FlatList, TouchableOpacity, ActivityIndicator, Alert } from 'react-native';
import { getMaterials, extractConcepts, reprocessMaterial, deleteMaterial } from '../services/api';

export default function MaterialsScreen({ navigation }) {
  const [materials, setMaterials] = useState([]);
  const [selectedMaterial, setSelectedMaterial] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionInProgress, setActionInProgress] = useState(false);

  const fetchMaterials = async () => {
    try {
      setLoading(true);
      const data = await getMaterials();
      setMaterials(data);
    } catch (err) {
      console.warn('Error fetching materials:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMaterials();
  }, []);

  const handleExtract = async (matId) => {
    try {
      setActionInProgress(true);
      await extractConcepts(matId);
      Alert.alert('Success', 'Concepts and prerequisite relationships mined by AI!');
      fetchMaterials();
    } catch (err) {
      Alert.alert('Extraction Error', err.message || 'Failed to extract concepts');
    } finally {
      setActionInProgress(false);
    }
  };

  const handleReprocess = async (matId) => {
    try {
      setActionInProgress(true);
      await reprocessMaterial(matId);
      Alert.alert('Success', 'Material chunks and semantic vector embeddings refreshed!');
      fetchMaterials();
    } catch (err) {
      Alert.alert('Reprocess Error', err.message || 'Failed to reprocess material');
    } finally {
      setActionInProgress(false);
    }
  };

  const handleDelete = async (matId) => {
    Alert.alert('Confirm Delete', 'Delete this study material and all derived chunks, flashcards, and notes?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await deleteMaterial(matId);
            setSelectedMaterial(null);
            fetchMaterials();
          } catch (err) {
            Alert.alert('Delete Error', 'Failed to delete material');
          }
        }
      }
    ]);
  };

  if (loading && materials.length === 0) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#6366f1" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>📂 Study Materials</Text>
          <Text style={styles.subtitle}>Multimodal ingestion, chunking & RAG embeddings</Text>
        </View>
        <TouchableOpacity style={styles.uploadButton} onPress={() => navigation.navigate('Upload')}>
          <Text style={styles.uploadButtonText}>+ Upload</Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={materials}
        keyExtractor={(item) => item._id || item.id}
        renderItem={({ item }) => {
          const statusUpper = (item.status || '').toUpperCase();
          const isReady = statusUpper === 'READY' || statusUpper === 'EXTRACTED' || statusUpper === 'PROCESSED';
          const isPartial = statusUpper === 'PARTIAL';

          return (
            <TouchableOpacity
              style={styles.card}
              onPress={() => setSelectedMaterial(selectedMaterial?._id === item._id ? null : item)}
            >
              <View style={styles.cardTop}>
                <Text style={styles.cardTitle}>{item.title || item.file_name}</Text>
                <View style={[
                  styles.badge,
                  isReady ? styles.badgeReady : isPartial ? styles.badgePartial : styles.badgeProcessing
                ]}>
                  <Text style={styles.badgeText}>{item.status}</Text>
                </View>
              </View>

              <Text style={styles.metaText}>
                {item.source_type?.toUpperCase() || 'DOCUMENT'} • {item.page_count ? `${item.page_count} pages • ` : ''}{item.file_size ? `${Math.round(item.file_size / 1024)} KB` : ''}
              </Text>

              {/* Actions Accordion */}
              {selectedMaterial?._id === item._id && (
                <View style={styles.actionPanel}>
                  {item.raw_text && (
                    <Text style={styles.rawPreview} numberOfLines={3}>
                      {item.raw_text}
                    </Text>
                  )}

                  <View style={styles.btnRow}>
                    <TouchableOpacity
                      style={styles.actionBtnPrimary}
                      onPress={() => handleExtract(item._id || item.id)}
                      disabled={actionInProgress}
                    >
                      <Text style={styles.btnTextWhite}>Mine Concepts</Text>
                    </TouchableOpacity>

                    <TouchableOpacity
                      style={styles.actionBtnSecondary}
                      onPress={() => handleReprocess(item._id || item.id)}
                      disabled={actionInProgress}
                    >
                      <Text style={styles.btnText}>Re-chunk</Text>
                    </TouchableOpacity>

                    <TouchableOpacity
                      style={styles.actionBtnDanger}
                      onPress={() => handleDelete(item._id || item.id)}
                    >
                      <Text style={styles.btnTextDanger}>Delete</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              )}
            </TouchableOpacity>
          );
        }}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyIcon}>📄</Text>
            <Text style={styles.emptyTitle}>No Study Materials Yet</Text>
            <Text style={styles.emptyText}>Upload PDFs, notes, or lecture documents to start.</Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#090d16', paddingHorizontal: 16 },
  center: { flex: 1, backgroundColor: '#090d16', alignItems: 'center', justifyContent: 'center' },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 20, marginBottom: 14 },
  title: { fontSize: 18, fontWeight: 'bold', color: '#f8fafc' },
  subtitle: { fontSize: 11, color: '#64748b', marginTop: 2 },
  uploadButton: { backgroundColor: '#6366f1', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8 },
  uploadButtonText: { color: '#ffffff', fontWeight: 'bold', fontSize: 11 },

  card: { backgroundColor: '#101726', borderRadius: 12, padding: 14, borderWidth: 1, borderColor: '#1e293b', marginBottom: 10 },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 },
  cardTitle: { color: '#ffffff', fontSize: 14, fontWeight: 'bold', flex: 1, marginRight: 8 },
  badge: { paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 },
  badgeReady: { backgroundColor: 'rgba(16, 185, 129, 0.15)' },
  badgePartial: { backgroundColor: 'rgba(56, 189, 248, 0.15)' },
  badgeProcessing: { backgroundColor: 'rgba(245, 158, 11, 0.15)' },
  badgeText: { fontSize: 10, fontWeight: 'bold', color: '#cbd5e1' },
  metaText: { color: '#64748b', fontSize: 11 },

  actionPanel: { marginTop: 10, borderTopWidth: 1, borderTopColor: '#1e293b', paddingTop: 10 },
  rawPreview: { color: '#94a3b8', fontSize: 11, fontStyle: 'italic', marginBottom: 10, lineHeight: 16 },
  btnRow: { flexDirection: 'row', gap: 8 },
  actionBtnPrimary: { flex: 1, backgroundColor: '#6366f1', paddingVertical: 8, borderRadius: 6, alignItems: 'center' },
  actionBtnSecondary: { backgroundColor: '#1e293b', paddingVertical: 8, paddingHorizontal: 12, borderRadius: 6 },
  actionBtnDanger: { backgroundColor: 'rgba(244, 63, 94, 0.15)', paddingVertical: 8, paddingHorizontal: 12, borderRadius: 6 },
  btnTextWhite: { color: '#ffffff', fontSize: 11, fontWeight: 'bold' },
  btnText: { color: '#94a3b8', fontSize: 11, fontWeight: 'bold' },
  btnTextDanger: { color: '#f87171', fontSize: 11, fontWeight: 'bold' },

  empty: { padding: 40, alignItems: 'center', marginTop: 40 },
  emptyIcon: { fontSize: 40, marginBottom: 10 },
  emptyTitle: { color: '#ffffff', fontSize: 16, fontWeight: 'bold', marginBottom: 4 },
  emptyText: { color: '#64748b', fontSize: 12, textAlign: 'center' }
});
