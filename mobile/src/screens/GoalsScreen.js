import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, ScrollView, TouchableOpacity, ActivityIndicator, Alert, TextInput } from 'react-native';
import { getGoals, createGoal, getGoalSkillGaps, deleteGoal } from '../services/api';

export default function GoalsScreen({ navigation }) {
  const [goals, setGoals] = useState([]);
  const [selectedGoal, setSelectedGoal] = useState(null);
  const [skillGaps, setSkillGaps] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newRole, setNewRole] = useState('');

  const fetchGoals = async () => {
    try {
      setLoading(true);
      const data = await getGoals();
      setGoals(data);
      if (data.length > 0 && !selectedGoal) {
        handleSelectGoal(data[0]);
      }
    } catch (err) {
      console.warn('Failed to load goals:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectGoal = async (goal) => {
    setSelectedGoal(goal);
    try {
      const gaps = await getGoalSkillGaps(goal._id || goal.id);
      setSkillGaps(gaps);
    } catch (err) {
      console.warn('Failed to load skill gaps:', err);
    }
  };

  const handleCreate = async () => {
    if (!newTitle.trim()) {
      Alert.alert('Required', 'Please enter a goal title.');
      return;
    }
    try {
      await createGoal({
        title: newTitle.trim(),
        target_role: newRole.trim() || undefined,
        required_skills: [
          { name: 'Core Foundations', required_level: 80.0, weight: 1.2 },
          { name: 'Practical Applications', required_level: 75.0, weight: 1.0 }
        ]
      });
      setNewTitle('');
      setNewRole('');
      setShowAddModal(false);
      fetchGoals();
    } catch (err) {
      Alert.alert('Error', err.message || 'Failed to create goal');
    }
  };

  const handleDelete = async (goalId) => {
    Alert.alert('Confirm Delete', 'Delete this learning goal?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await deleteGoal(goalId);
            setSelectedGoal(null);
            setSkillGaps(null);
            fetchGoals();
          } catch (err) {
            Alert.alert('Error', 'Failed to delete goal');
          }
        }
      }
    ]);
  };

  useEffect(() => {
    fetchGoals();
  }, []);

  if (loading && goals.length === 0) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#6366f1" />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.headerRow}>
        <View>
          <Text style={styles.screenTitle}>🎯 Career Goals & Skill Gaps</Text>
          <Text style={styles.screenSubtitle}>Benchmark tracking and prerequisite readiness</Text>
        </View>
        <TouchableOpacity style={styles.addBtn} onPress={() => setShowAddModal(!showAddModal)}>
          <Text style={styles.addBtnText}>{showAddModal ? '✕ Cancel' : '+ New Goal'}</Text>
        </TouchableOpacity>
      </View>

      {/* Add Goal Form */}
      {showAddModal && (
        <View style={styles.formCard}>
          <Text style={styles.formTitle}>Define Learning Goal</Text>
          <TextInput
            style={styles.input}
            placeholder="Goal Title (e.g. Full-Stack Data Engineer)"
            placeholderTextColor="#64748b"
            value={newTitle}
            onChangeText={setNewTitle}
          />
          <TextInput
            style={styles.input}
            placeholder="Target Career Role (e.g. Senior Analytics Engineer)"
            placeholderTextColor="#64748b"
            value={newRole}
            onChangeText={setNewRole}
          />
          <TouchableOpacity style={styles.submitBtn} onPress={handleCreate}>
            <Text style={styles.submitBtnText}>Create Benchmark Goal</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Goal Selector Chips */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipScroll}>
        {goals.map((g) => {
          const isSelected = selectedGoal && (selectedGoal._id === g._id || selectedGoal.id === g.id);
          return (
            <TouchableOpacity
              key={g._id || g.id}
              style={[styles.goalChip, isSelected && styles.goalChipActive]}
              onPress={() => handleSelectGoal(g)}
            >
              <Text style={[styles.goalChipText, isSelected && styles.goalChipTextActive]}>{g.title}</Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {/* Goal Readiness & Skill Gap Breakdown */}
      {selectedGoal && skillGaps ? (
        <View style={styles.detailCard}>
          <View style={styles.detailHeader}>
            <View style={{ flex: 1 }}>
              <Text style={styles.selectedGoalTitle}>{selectedGoal.title}</Text>
              {selectedGoal.target_role && (
                <Text style={styles.selectedGoalRole}>{selectedGoal.target_role}</Text>
              )}
            </View>
            <TouchableOpacity onPress={() => handleDelete(selectedGoal._id || selectedGoal.id)}>
              <Text style={styles.deleteText}>Delete</Text>
            </TouchableOpacity>
          </View>

          {/* Readiness Meter */}
          <View style={styles.readinessMeter}>
            <View style={styles.readinessHeader}>
              <Text style={styles.readinessLabel}>Overall Goal Readiness</Text>
              <Text style={styles.readinessScore}>{Math.round(skillGaps.overall_readiness_score || 0)}%</Text>
            </View>
            <View style={styles.meterBarBg}>
              <View style={[styles.meterBarFill, { width: `${Math.round(skillGaps.overall_readiness_score || 0)}%` }]} />
            </View>
            <Text style={styles.readinessStatus}>Status: <Text style={styles.boldWhite}>{skillGaps.status || 'IN_PROGRESS'}</Text></Text>
          </View>

          {/* Prerequisite Bottlenecks */}
          {skillGaps.prerequisite_bottlenecks?.length > 0 && (
            <View style={styles.bottleneckCard}>
              <Text style={styles.bottleneckTitle}>⚠️ Prerequisite Bottlenecks</Text>
              {skillGaps.prerequisite_bottlenecks.map((b, i) => (
                <Text key={i} style={styles.bottleneckItem}>
                  • <Text style={styles.boldWhite}>{b.blocking_prerequisite || b}</Text> blocks target concept
                </Text>
              ))}
            </View>
          )}

          {/* Detailed Skill Benchmarks */}
          <Text style={styles.sectionHeading}>Required Skill Benchmarks</Text>
          {skillGaps.skill_gaps?.map((gap, i) => {
            const isReady = gap.status === 'READY';
            const isBlocked = gap.status === 'BLOCKED';
            return (
              <View key={i} style={styles.skillCard}>
                <View style={styles.skillHeader}>
                  <Text style={styles.skillName}>{gap.skill_name}</Text>
                  <Text style={[styles.statusTag, isReady ? styles.tagReady : isBlocked ? styles.tagBlocked : styles.tagLearning]}>
                    {gap.status}
                  </Text>
                </View>

                <View style={styles.benchmarkValues}>
                  <Text style={styles.benchmarkText}>Current: <Text style={styles.boldWhite}>{Math.round(gap.current_mastery)}%</Text></Text>
                  <Text style={styles.benchmarkText}>Target: <Text style={styles.boldWhite}>{Math.round(gap.required_mastery)}%</Text></Text>
                  <Text style={styles.benchmarkText}>Gap: <Text style={styles.boldAmber}>{Math.max(0, Math.round(gap.required_mastery - gap.current_mastery))}%</Text></Text>
                </View>

                {gap.blocking_prerequisites?.length > 0 && (
                  <Text style={styles.prereqWarning}>
                    Blocked by: {gap.blocking_prerequisites.join(', ')}
                  </Text>
                )}
              </View>
            );
          })}
        </View>
      ) : (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>Select or create a goal above to view skill gap analytics.</Text>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#090d16', paddingHorizontal: 16 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#090d16' },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 20, marginBottom: 12 },
  screenTitle: { color: '#f8fafc', fontSize: 18, fontWeight: 'bold' },
  screenSubtitle: { color: '#64748b', fontSize: 11, marginTop: 2 },
  addBtn: { backgroundColor: '#1e293b', paddingVertical: 6, paddingHorizontal: 12, borderRadius: 8, borderWidth: 1, borderColor: '#334155' },
  addBtnText: { color: '#818cf8', fontWeight: 'bold', fontSize: 11 },
  
  formCard: { backgroundColor: '#101726', borderWidth: 1, borderColor: '#1e293b', borderRadius: 12, padding: 14, marginBottom: 12 },
  formTitle: { color: '#f8fafc', fontSize: 13, fontWeight: 'bold', marginBottom: 8 },
  input: { backgroundColor: '#090d16', borderWidth: 1, borderColor: '#1e293b', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 8, color: '#fff', fontSize: 12, marginBottom: 8 },
  submitBtn: { backgroundColor: '#6366f1', paddingVertical: 8, borderRadius: 8, alignItems: 'center' },
  submitBtnText: { color: '#fff', fontSize: 12, fontWeight: 'bold' },

  chipScroll: { marginVertical: 8 },
  goalChip: { backgroundColor: '#101726', borderWidth: 1, borderColor: '#1e293b', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20, marginRight: 8 },
  goalChipActive: { backgroundColor: '#6366f1', borderColor: '#818cf8' },
  goalChipText: { color: '#94a3b8', fontSize: 12, fontWeight: '600' },
  goalChipTextActive: { color: '#ffffff', fontWeight: 'bold' },

  detailCard: { backgroundColor: '#101726', borderRadius: 16, padding: 16, marginVertical: 12, borderWidth: 1, borderColor: '#1e293b' },
  detailHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 },
  selectedGoalTitle: { color: '#ffffff', fontSize: 16, fontWeight: 'bold' },
  selectedGoalRole: { color: '#818cf8', fontSize: 11, marginTop: 2 },
  deleteText: { color: '#f87171', fontSize: 11, fontWeight: 'bold' },

  readinessMeter: { backgroundColor: '#172136', padding: 12, borderRadius: 12, marginBottom: 12 },
  readinessHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  readinessLabel: { color: '#94a3b8', fontSize: 12 },
  readinessScore: { color: '#34d399', fontSize: 16, fontWeight: 'bold' },
  meterBarBg: { height: 8, backgroundColor: '#090d16', borderRadius: 4, overflow: 'hidden', marginBottom: 6 },
  meterBarFill: { height: '100%', backgroundColor: '#10b981', borderRadius: 4 },
  readinessStatus: { color: '#64748b', fontSize: 10 },

  bottleneckCard: { backgroundColor: 'rgba(244, 63, 94, 0.1)', borderWidth: 1, borderColor: 'rgba(244, 63, 94, 0.3)', borderRadius: 10, padding: 12, marginBottom: 12 },
  bottleneckTitle: { color: '#f87171', fontSize: 12, fontWeight: 'bold', marginBottom: 4 },
  bottleneckItem: { color: '#cbd5e1', fontSize: 11, marginVertical: 2 },

  sectionHeading: { color: '#cbd5e1', fontSize: 13, fontWeight: 'bold', marginTop: 8, marginBottom: 8 },
  skillCard: { backgroundColor: '#172136', borderRadius: 10, padding: 12, marginVertical: 4 },
  skillHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  skillName: { color: '#ffffff', fontSize: 13, fontWeight: 'bold' },
  statusTag: { fontSize: 10, fontWeight: 'bold', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 },
  tagReady: { backgroundColor: 'rgba(16, 185, 129, 0.2)', color: '#34d399' },
  tagBlocked: { backgroundColor: 'rgba(244, 63, 94, 0.2)', color: '#f87171' },
  tagLearning: { backgroundColor: 'rgba(245, 158, 11, 0.2)', color: '#fbbf24' },

  benchmarkValues: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 8 },
  benchmarkText: { color: '#94a3b8', fontSize: 11 },
  prereqWarning: { color: '#f87171', fontSize: 10, marginTop: 6 },
  boldWhite: { color: '#ffffff', fontWeight: 'bold' },
  boldAmber: { color: '#fbbf24', fontWeight: 'bold' },
  emptyContainer: { padding: 40, alignItems: 'center' },
  emptyText: { color: '#64748b', fontSize: 12, textAlign: 'center' }
});
