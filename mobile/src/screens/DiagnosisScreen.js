import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, ScrollView, TouchableOpacity, ActivityIndicator } from 'react-native';
import { getDiagnoses, evaluateDiagnosis } from '../services/api';

export default function DiagnosisScreen({ navigation }) {
  const [diagnoses, setDiagnoses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);

  const fetchDiagnoses = async () => {
    try {
      setLoading(true);
      const data = await getDiagnoses();
      setDiagnoses(data.diagnoses || []);
    } catch (err) {
      console.warn('Failed to load diagnoses:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleEvaluate = async () => {
    try {
      setEvaluating(true);
      await evaluateDiagnosis();
      fetchDiagnoses();
    } catch (err) {
      console.warn('Evaluation failed:', err);
      setEvaluating(false);
    }
  };

  useEffect(() => {
    fetchDiagnoses();
  }, []);

  if (loading && diagnoses.length === 0) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#6366f1" />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.headerRow}>
        <View style={{ flex: 1 }}>
          <Text style={styles.screenTitle}>🔬 Misconception Diagnosis</Text>
          <Text style={styles.screenSubtitle}>Root-cause prerequisite breakdown & BKT evidence</Text>
        </View>
        <TouchableOpacity style={styles.evalBtn} onPress={handleEvaluate} disabled={evaluating}>
          {evaluating ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Text style={styles.evalBtnText}>Re-Diagnose</Text>
          )}
        </TouchableOpacity>
      </View>

      {diagnoses.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyIcon}>🛡️</Text>
          <Text style={styles.emptyTitle}>No Active Misconceptions</Text>
          <Text style={styles.emptyText}>
            Your learning progression shows healthy concept understanding. Complete more quizzes or assignments to trigger deep diagnostic modeling.
          </Text>
        </View>
      ) : (
        diagnoses.map((d, index) => (
          <View key={index} style={styles.diagCard}>
            <View style={styles.cardHeader}>
              <Text style={styles.diagTypeBadge}>{d.diagnosis_type?.replace(/_/g, ' ')}</Text>
              <Text style={styles.confBadge}>Confidence: {Math.round((d.confidence || 0.8) * 100)}%</Text>
            </View>

            <Text style={styles.targetConcept}>Target Concept: <Text style={styles.textWhite}>{d.target_concept}</Text></Text>

            {d.suspected_root_concept && (
              <View style={styles.rootBox}>
                <Text style={styles.rootLabel}>SUSPECTED ROOT CAUSE:</Text>
                <Text style={styles.rootConcept}>{d.suspected_root_concept}</Text>
              </View>
            )}

            <View style={styles.evidenceBlock}>
              <Text style={styles.evidenceTitle}>Diagnostic Evidence:</Text>
              <Text style={styles.evidenceText}>{d.evidence || d.reason}</Text>
            </View>

            {d.recommended_action && (
              <View style={styles.recBlock}>
                <Text style={styles.recLabel}>Recommended Action:</Text>
                <Text style={styles.recAction}>{d.recommended_action}</Text>
              </View>
            )}
          </View>
        ))
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#090d16', paddingHorizontal: 16 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#090d16' },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 20, marginBottom: 14 },
  screenTitle: { color: '#f8fafc', fontSize: 18, fontWeight: 'bold' },
  screenSubtitle: { color: '#64748b', fontSize: 11, marginTop: 2 },
  evalBtn: { backgroundColor: '#6366f1', paddingVertical: 6, paddingHorizontal: 12, borderRadius: 8 },
  evalBtnText: { color: '#ffffff', fontWeight: 'bold', fontSize: 11 },

  diagCard: { backgroundColor: '#101726', borderWidth: 1, borderColor: '#1e293b', borderRadius: 14, padding: 16, marginVertical: 8 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  diagTypeBadge: { color: '#f43f5e', fontSize: 10, fontWeight: 'bold', textTransform: 'uppercase', backgroundColor: 'rgba(244, 63, 94, 0.15)', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 },
  confBadge: { color: '#94a3b8', fontSize: 10 },

  targetConcept: { color: '#94a3b8', fontSize: 13, marginBottom: 8 },
  textWhite: { color: '#ffffff', fontWeight: 'bold' },
  
  rootBox: { backgroundColor: 'rgba(245, 158, 11, 0.1)', borderWidth: 1, borderColor: 'rgba(245, 158, 11, 0.3)', borderRadius: 8, padding: 10, marginBottom: 10 },
  rootLabel: { color: '#fbbf24', fontSize: 9, fontWeight: 'bold' },
  rootConcept: { color: '#ffffff', fontSize: 13, fontWeight: 'bold', marginTop: 2 },

  evidenceBlock: { backgroundColor: '#172136', padding: 10, borderRadius: 8, marginBottom: 8 },
  evidenceTitle: { color: '#94a3b8', fontSize: 10, fontWeight: 'bold', marginBottom: 2 },
  evidenceText: { color: '#cbd5e1', fontSize: 11, lineHeight: 16 },

  recBlock: { backgroundColor: 'rgba(99, 102, 241, 0.1)', padding: 10, borderRadius: 8 },
  recLabel: { color: '#818cf8', fontSize: 10, fontWeight: 'bold' },
  recAction: { color: '#e0e7ff', fontSize: 12, fontWeight: '600', marginTop: 2 },

  emptyContainer: { padding: 40, alignItems: 'center', marginTop: 40 },
  emptyIcon: { fontSize: 40, marginBottom: 12 },
  emptyTitle: { color: '#ffffff', fontSize: 16, fontWeight: 'bold', marginBottom: 6 },
  emptyText: { color: '#64748b', fontSize: 12, textAlign: 'center', lineHeight: 18 }
});
