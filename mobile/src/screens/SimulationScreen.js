import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, ScrollView, TouchableOpacity, ActivityIndicator, Alert } from 'react-native';
import { getConcepts, runWhatIfSimulation } from '../services/api';

export default function SimulationScreen({ navigation }) {
  const [concepts, setConcepts] = useState([]);
  const [simulatedMasteries, setSimulatedMasteries] = useState({});
  const [simulationResult, setSimulationResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);

  useEffect(() => {
    fetchConcepts();
  }, []);

  const fetchConcepts = async () => {
    try {
      setLoading(true);
      const data = await getConcepts();
      setConcepts(data);
      const initial = {};
      data.forEach(c => {
        initial[c.name] = c.mastery_score || 30.0;
      });
      setSimulatedMasteries(initial);
    } catch (err) {
      console.warn('Failed to fetch concepts for simulation:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAdjustMastery = (conceptName, delta) => {
    setSimulatedMasteries(prev => {
      const current = prev[conceptName] || 30.0;
      const updated = Math.min(100, Math.max(0, current + delta));
      return { ...prev, [conceptName]: updated };
    });
  };

  const handleRunSimulation = async () => {
    try {
      setSimulating(true);
      const result = await runWhatIfSimulation(simulatedMasteries);
      setSimulationResult(result);
    } catch (err) {
      Alert.alert('Simulation Error', err.message || 'Counterfactual simulation failed');
    } finally {
      setSimulating(false);
    }
  };

  if (loading && concepts.length === 0) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#6366f1" />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>🔮 What-If Simulator</Text>
        <Text style={styles.subtitle}>Test counterfactual mastery scenarios without altering production state</Text>
      </View>

      {/* Counterfactual Notice */}
      <View style={styles.noticeBox}>
        <Text style={styles.noticeText}>
          🔒 <Text style={styles.boldWhite}>Safe Sandbox Mode:</Text> Adjust concept proficiencies below to project future goal readiness and unlocked prerequisites. Real learner records remain untouched.
        </Text>
      </View>

      {/* Simulation Trigger */}
      <TouchableOpacity
        style={styles.simulateBtn}
        onPress={handleRunSimulation}
        disabled={simulating}
      >
        {simulating ? (
          <ActivityIndicator size="small" color="#fff" />
        ) : (
          <Text style={styles.simulateBtnText}>Compute Counterfactual Trajectory</Text>
        )}
      </TouchableOpacity>

      {/* Simulation Results */}
      {simulationResult && (
        <View style={styles.resultsCard}>
          <Text style={styles.resultsTitle}>📊 Simulation Projection</Text>
          
          <View style={styles.scoreRow}>
            <View style={styles.scoreBox}>
              <Text style={styles.scoreLabel}>Current Readiness</Text>
              <Text style={styles.currentScore}>{Math.round(simulationResult.current_readiness_score || 0)}%</Text>
            </View>
            <Text style={styles.arrow}>→</Text>
            <View style={styles.scoreBox}>
              <Text style={styles.scoreLabel}>Simulated Readiness</Text>
              <Text style={styles.simScore}>{Math.round(simulationResult.simulated_readiness_score || 0)}%</Text>
            </View>
          </View>

          {/* Unlocked Skills */}
          {simulationResult.unlocked_skills?.length > 0 && (
            <View style={styles.unlockedBox}>
              <Text style={styles.unlockedTitle}>✨ Unlocked Prerequisite Targets:</Text>
              {simulationResult.unlocked_skills.map((s, i) => (
                <Text key={i} style={styles.unlockedItem}>• {s}</Text>
              ))}
            </View>
          )}

          {/* Projected Next Action */}
          {simulationResult.projected_next_action && (
            <View style={styles.nbaBox}>
              <Text style={styles.nbaLabel}>Projected Next-Best Action:</Text>
              <Text style={styles.nbaText}>{simulationResult.projected_next_action.concept_name || simulationResult.projected_next_action.title}</Text>
              <Text style={styles.nbaReason}>{simulationResult.projected_next_action.reason}</Text>
            </View>
          )}
        </View>
      )}

      {/* Concepts Slider List */}
      <Text style={styles.sectionHeader}>Adjust Simulated Concept Masteries</Text>
      {concepts.map((c) => {
        const val = simulatedMasteries[c.name] || 0;
        return (
          <View key={c._id || c.id} style={styles.conceptItem}>
            <View style={styles.conceptMeta}>
              <Text style={styles.conceptName}>{c.name}</Text>
              <Text style={styles.masteryValue}>{Math.round(val)}%</Text>
            </View>
            
            <View style={styles.stepperRow}>
              <TouchableOpacity style={styles.stepBtn} onPress={() => handleAdjustMastery(c.name, -10)}>
                <Text style={styles.stepBtnText}>-10%</Text>
              </TouchableOpacity>
              <View style={styles.progressBg}>
                <View style={[styles.progressFill, { width: `${val}%` }]} />
              </View>
              <TouchableOpacity style={styles.stepBtn} onPress={() => handleAdjustMastery(c.name, 10)}>
                <Text style={styles.stepBtnText}>+10%</Text>
              </TouchableOpacity>
            </View>
          </View>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#090d16', paddingHorizontal: 16 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#090d16' },
  header: { marginTop: 20, marginBottom: 12 },
  title: { color: '#f8fafc', fontSize: 18, fontWeight: 'bold' },
  subtitle: { color: '#64748b', fontSize: 11, marginTop: 2 },
  
  noticeBox: { backgroundColor: 'rgba(99, 102, 241, 0.1)', borderWidth: 1, borderColor: 'rgba(99, 102, 241, 0.25)', borderRadius: 10, padding: 12, marginBottom: 12 },
  noticeText: { color: '#94a3b8', fontSize: 11, lineHeight: 16 },
  boldWhite: { color: '#ffffff', fontWeight: 'bold' },

  simulateBtn: { backgroundColor: '#6366f1', paddingVertical: 12, borderRadius: 10, alignItems: 'center', marginBottom: 16 },
  simulateBtnText: { color: '#ffffff', fontWeight: 'bold', fontSize: 13 },

  resultsCard: { backgroundColor: '#101726', borderWidth: 1, borderColor: '#1e293b', borderRadius: 14, padding: 16, marginBottom: 16 },
  resultsTitle: { color: '#ffffff', fontSize: 14, fontWeight: 'bold', marginBottom: 10 },
  scoreRow: { flexDirection: 'row', justifyContent: 'space-around', alignItems: 'center', marginBottom: 12 },
  scoreBox: { alignItems: 'center' },
  scoreLabel: { color: '#64748b', fontSize: 10, marginBottom: 2 },
  currentScore: { color: '#94a3b8', fontSize: 18, fontWeight: 'bold' },
  simScore: { color: '#34d399', fontSize: 22, fontWeight: 'bold' },
  arrow: { color: '#6366f1', fontSize: 20, fontWeight: 'bold' },

  unlockedBox: { backgroundColor: 'rgba(16, 185, 129, 0.1)', padding: 10, borderRadius: 8, marginBottom: 10 },
  unlockedTitle: { color: '#34d399', fontSize: 11, fontWeight: 'bold' },
  unlockedItem: { color: '#e2e8f0', fontSize: 11, marginTop: 2 },

  nbaBox: { backgroundColor: '#172136', padding: 10, borderRadius: 8 },
  nbaLabel: { color: '#818cf8', fontSize: 10, fontWeight: 'bold' },
  nbaText: { color: '#ffffff', fontSize: 12, fontWeight: 'bold', marginTop: 2 },
  nbaReason: { color: '#64748b', fontSize: 10, marginTop: 2 },

  sectionHeader: { color: '#cbd5e1', fontSize: 13, fontWeight: 'bold', marginBottom: 8 },
  conceptItem: { backgroundColor: '#101726', padding: 12, borderRadius: 10, marginBottom: 8, borderWidth: 1, borderColor: '#1e293b' },
  conceptMeta: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  conceptName: { color: '#ffffff', fontSize: 12, fontWeight: 'bold' },
  masteryValue: { color: '#38bdf8', fontSize: 12, fontWeight: 'bold' },
  stepperRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  stepBtn: { backgroundColor: '#1e293b', paddingVertical: 4, paddingHorizontal: 10, borderRadius: 6 },
  stepBtnText: { color: '#94a3b8', fontSize: 11, fontWeight: 'bold' },
  progressBg: { flex: 1, height: 6, backgroundColor: '#090d16', borderRadius: 3, marginHorizontal: 8, overflow: 'hidden' },
  progressFill: { height: '100%', backgroundColor: '#38bdf8' }
});
