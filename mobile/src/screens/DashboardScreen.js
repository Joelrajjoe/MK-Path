import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, ScrollView, TouchableOpacity, ActivityIndicator, RefreshControl } from 'react-native';
import { getDashboardSummary, getNextBestAction, getDiagnoses } from '../services/api';

export default function DashboardScreen({ navigation }) {
  const [summary, setSummary] = useState(null);
  const [nba, setNba] = useState(null);
  const [diagnoses, setDiagnoses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const [sumData, nbaData, diagData] = await Promise.allSettled([
        getDashboardSummary(),
        getNextBestAction(),
        getDiagnoses(),
      ]);

      if (sumData.status === 'fulfilled') setSummary(sumData.value);
      if (nbaData.status === 'fulfilled') setNba(nbaData.value?.next_action);
      if (diagData.status === 'fulfilled') setDiagnoses(diagData.value?.diagnoses || []);
    } catch (err) {
      console.warn('Failed to load dashboard summary:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading && !refreshing) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#6366f1" />
        <Text style={styles.loadingText}>Synthesizing Learner Intelligence...</Text>
      </View>
    );
  }

  const activeGoal = summary?.active_goal;
  const readiness = activeGoal?.readiness || summary?.goal_readiness;
  const skillGaps = activeGoal?.skill_gaps || [];

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadData(); }} tintColor="#6366f1" />}
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.brandTitle}>MK-Path Intelligence</Text>
        <Text style={styles.headerSubtitle}>Adaptive Multimodal Knowledge Trajectory</Text>
      </View>

      {/* Gamification Strip */}
      <View style={styles.xpCard}>
        <View style={styles.xpRow}>
          <Text style={styles.levelBadge}>Level {summary?.gamification?.level || 1} • {summary?.gamification?.rank || 'Explorer'}</Text>
          <Text style={styles.xpText}>{summary?.gamification?.xp || 0} XP</Text>
        </View>
        <View style={styles.progressBarBg}>
          <View style={[styles.progressBarFill, { width: `${Math.min(100, ((summary?.gamification?.xp || 0) % 100))}%` }]} />
        </View>
      </View>

      {/* NEXT-BEST LEARNING ACTION (NBA) */}
      {nba && (
        <View style={styles.nbaCard}>
          <View style={styles.nbaBadgeRow}>
            <Text style={styles.nbaBadge}>⚡ NEXT-BEST ACTION</Text>
            <Text style={styles.priorityBadge}>{nba.priority || 'HIGH'}</Text>
          </View>
          <Text style={styles.nbaTitle}>{nba.title || nba.concept_name || 'Personalized Recommended Action'}</Text>
          <Text style={styles.nbaReason}><Text style={styles.bold}>Why: </Text>{nba.reason}</Text>
          {nba.expected_effect && (
            <Text style={styles.nbaEffect}><Text style={styles.bold}>Expected Effect: </Text>{nba.expected_effect}</Text>
          )}
          <TouchableOpacity
            style={styles.nbaActionBtn}
            onPress={() => {
              if (nba.action_type === 'ASSESS' || nba.action_type === 'PRACTICE') navigation.navigate('Assessment');
              else if (nba.action_type === 'COMPLETE_ASSIGNMENT') navigation.navigate('Assignments');
              else navigation.navigate('StudyPath');
            }}
          >
            <Text style={styles.nbaActionBtnText}>Execute Action</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* ACTIVE GOAL & READINESS */}
      <View style={styles.sectionCard}>
        <Text style={styles.sectionTitle}>🎯 Active Learning Goal</Text>
        {activeGoal ? (
          <View>
            <View style={styles.goalHeaderRow}>
              <Text style={styles.goalTitle}>{activeGoal.title}</Text>
              <Text style={styles.readinessBadge}>{readiness ? `${Math.round(readiness.overall_readiness_score || readiness)}% Ready` : 'Evaluating'}</Text>
            </View>
            {activeGoal.target_role && (
              <Text style={styles.goalRole}>Target Role: {activeGoal.target_role}</Text>
            )}

            {/* Skill Gaps Breakdown */}
            {skillGaps.length > 0 && (
              <View style={styles.skillGapsContainer}>
                <Text style={styles.subheading}>Key Skill Benchmarks:</Text>
                {skillGaps.slice(0, 3).map((gap, idx) => (
                  <View key={idx} style={styles.gapRow}>
                    <Text style={styles.gapSkillName}>{gap.skill_name}</Text>
                    <Text style={[styles.gapStatus, gap.status === 'READY' ? styles.statusReady : gap.status === 'BLOCKED' ? styles.statusBlocked : styles.statusLearning]}>
                      {gap.status} ({Math.round(gap.current_mastery)}% / {Math.round(gap.required_mastery)}%)
                    </Text>
                  </View>
                ))}
              </View>
            )}

            <TouchableOpacity style={styles.outlineBtn} onPress={() => navigation.navigate('Goals')}>
              <Text style={styles.outlineBtnText}>View Full Goal & Skill Gaps →</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.emptyPrompt}>
            <Text style={styles.emptyPromptText}>No active learning goal selected.</Text>
            <TouchableOpacity style={styles.primaryBtn} onPress={() => navigation.navigate('Goals')}>
              <Text style={styles.primaryBtnText}>Set Goal & Career Target</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>

      {/* RECENT MISCONCEPTION DIAGNOSES */}
      {diagnoses.length > 0 && (
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>🔬 Misconception & Prerequisite Diagnosis</Text>
          {diagnoses.slice(0, 2).map((diag, i) => (
            <View key={i} style={styles.diagItem}>
              <Text style={styles.diagType}>{diag.diagnosis_type?.replace(/_/g, ' ')}</Text>
              <Text style={styles.diagTarget}>Target: <Text style={styles.textWhite}>{diag.target_concept}</Text></Text>
              {diag.suspected_root_concept && (
                <Text style={styles.diagRoot}>Root Cause: <Text style={styles.textAmber}>{diag.suspected_root_concept}</Text></Text>
              )}
              <Text style={styles.diagReason}>{diag.reason}</Text>
            </View>
          ))}
          <TouchableOpacity style={styles.outlineBtn} onPress={() => navigation.navigate('Diagnosis')}>
            <Text style={styles.outlineBtnText}>View All Diagnostic Evidence →</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* QUICK INTELLIGENCE HUB */}
      <View style={styles.hubGrid}>
        <TouchableOpacity style={styles.hubCard} onPress={() => navigation.navigate('Simulation')}>
          <Text style={styles.hubIcon}>🔮</Text>
          <Text style={styles.hubTitle}>What-If Simulator</Text>
          <Text style={styles.hubDesc}>Simulate counterfactual mastery outcomes</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.hubCard} onPress={() => navigation.navigate('Assignments')}>
          <Text style={styles.hubIcon}>📑</Text>
          <Text style={styles.hubTitle}>Assignments</Text>
          <Text style={styles.hubDesc}>Complete auto-graded AI assignments</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.hubCard} onPress={() => navigation.navigate('Graph')}>
          <Text style={styles.hubIcon}>🕸️</Text>
          <Text style={styles.hubTitle}>Knowledge Graph</Text>
          <Text style={styles.hubDesc}>Explore interactive concept network</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.hubCard} onPress={() => navigation.navigate('Materials')}>
          <Text style={styles.hubIcon}>📚</Text>
          <Text style={styles.hubTitle}>Study Materials</Text>
          <Text style={styles.hubDesc}>Upload & mine multimodal files</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#090d16', paddingHorizontal: 16 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#090d16' },
  loadingText: { color: '#94a3b8', fontSize: 13, marginTop: 12 },
  header: { paddingTop: 20, paddingBottom: 12 },
  brandTitle: { color: '#f8fafc', fontSize: 24, fontWeight: 'bold', letterSpacing: -0.5 },
  headerSubtitle: { color: '#64748b', fontSize: 12, marginTop: 2 },
  
  xpCard: { backgroundColor: '#131c2e', borderRadius: 14, padding: 14, marginVertical: 8, borderWidth: 1, borderColor: '#1e293b' },
  xpRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  levelBadge: { color: '#818cf8', fontWeight: 'bold', fontSize: 12 },
  xpText: { color: '#fbbf24', fontWeight: 'bold', fontSize: 12 },
  progressBarBg: { height: 6, backgroundColor: '#1e293b', borderRadius: 3, overflow: 'hidden' },
  progressBarFill: { height: '100%', backgroundColor: '#6366f1', borderRadius: 3 },

  nbaCard: { backgroundColor: 'rgba(99, 102, 241, 0.08)', borderWidth: 1.5, borderColor: 'rgba(99, 102, 241, 0.4)', borderRadius: 16, padding: 16, marginVertical: 8 },
  nbaBadgeRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  nbaBadge: { color: '#a5b4fc', fontSize: 10, fontWeight: '800', letterSpacing: 0.5 },
  priorityBadge: { color: '#f87171', fontSize: 10, fontWeight: 'bold' },
  nbaTitle: { color: '#ffffff', fontSize: 16, fontWeight: 'bold', marginBottom: 6 },
  nbaReason: { color: '#94a3b8', fontSize: 12, lineHeight: 18, marginBottom: 4 },
  nbaEffect: { color: '#38bdf8', fontSize: 11, lineHeight: 16, marginBottom: 12 },
  nbaActionBtn: { backgroundColor: '#6366f1', paddingVertical: 10, borderRadius: 10, alignItems: 'center' },
  nbaActionBtnText: { color: '#ffffff', fontWeight: 'bold', fontSize: 13 },

  sectionCard: { backgroundColor: '#101726', borderRadius: 16, padding: 16, marginVertical: 8, borderWidth: 1, borderColor: '#1e293b' },
  sectionTitle: { color: '#f1f5f9', fontSize: 15, fontWeight: 'bold', marginBottom: 12 },
  goalHeaderRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  goalTitle: { color: '#ffffff', fontSize: 16, fontWeight: 'bold', flex: 1 },
  readinessBadge: { backgroundColor: 'rgba(16, 185, 129, 0.15)', color: '#34d399', fontSize: 11, fontWeight: 'bold', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  goalRole: { color: '#64748b', fontSize: 12, marginTop: 4 },
  skillGapsContainer: { marginTop: 12, borderTopWidth: 1, borderTopColor: '#1e293b', paddingTop: 10 },
  subheading: { color: '#94a3b8', fontSize: 11, fontWeight: '600', marginBottom: 6 },
  gapRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginVertical: 4 },
  gapSkillName: { color: '#cbd5e1', fontSize: 12 },
  gapStatus: { fontSize: 10, fontWeight: 'bold' },
  statusReady: { color: '#34d399' },
  statusBlocked: { color: '#f87171' },
  statusLearning: { color: '#fbbf24' },

  diagItem: { backgroundColor: '#172136', padding: 12, borderRadius: 10, marginVertical: 4 },
  diagType: { color: '#f43f5e', fontSize: 10, fontWeight: 'bold', textTransform: 'uppercase' },
  diagTarget: { color: '#94a3b8', fontSize: 12, marginTop: 2 },
  diagRoot: { color: '#94a3b8', fontSize: 12, marginTop: 1 },
  diagReason: { color: '#64748b', fontSize: 11, marginTop: 4 },
  textWhite: { color: '#ffffff', fontWeight: '600' },
  textAmber: { color: '#fbbf24', fontWeight: 'bold' },
  bold: { fontWeight: 'bold', color: '#e2e8f0' },

  outlineBtn: { marginTop: 12, paddingVertical: 8, alignItems: 'center', borderWidth: 1, borderColor: '#334155', borderRadius: 8 },
  outlineBtnText: { color: '#94a3b8', fontSize: 12, fontWeight: '600' },
  primaryBtn: { backgroundColor: '#6366f1', paddingVertical: 10, paddingHorizontal: 16, borderRadius: 10, marginTop: 8, alignItems: 'center' },
  primaryBtnText: { color: '#fff', fontSize: 12, fontWeight: 'bold' },
  emptyPrompt: { alignItems: 'center', paddingVertical: 12 },
  emptyPromptText: { color: '#64748b', fontSize: 12, marginBottom: 8 },

  hubGrid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', marginVertical: 12, paddingBottom: 24 },
  hubCard: { width: '48%', backgroundColor: '#101726', borderWidth: 1, borderColor: '#1e293b', borderRadius: 14, padding: 14, marginBottom: 12 },
  hubIcon: { fontSize: 22, marginBottom: 6 },
  hubTitle: { color: '#f8fafc', fontSize: 13, fontWeight: 'bold', marginBottom: 2 },
  hubDesc: { color: '#64748b', fontSize: 10, lineHeight: 14 }
});
