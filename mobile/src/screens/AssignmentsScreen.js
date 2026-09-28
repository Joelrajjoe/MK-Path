import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, ScrollView, TouchableOpacity, ActivityIndicator, Alert, TextInput } from 'react-native';
import { getAssignments, getAssignmentDetail, generateAssignment, submitAssignment } from '../services/api';

export default function AssignmentsScreen({ navigation }) {
  const [assignments, setAssignments] = useState([]);
  const [activeAssignment, setActiveAssignment] = useState(null);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submissionResult, setSubmissionResult] = useState(null);

  useEffect(() => {
    fetchAssignments();
  }, []);

  const fetchAssignments = async () => {
    try {
      setLoading(true);
      const data = await getAssignments();
      setAssignments(data);
    } catch (err) {
      console.warn('Failed to load assignments:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenAssignment = async (assignId) => {
    try {
      setLoading(true);
      const detail = await getAssignmentDetail(assignId);
      setActiveAssignment(detail);
      setAnswers(detail.answers || {});
      setSubmissionResult(null);
    } catch (err) {
      Alert.alert('Error', 'Could not open assignment');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateNew = async () => {
    try {
      setLoading(true);
      const res = await generateAssignment({ difficulty: 'intermediate' });
      Alert.alert('Success', 'Synthesized new AI assignment (+20 XP)');
      fetchAssignments();
      if (res.assignment) {
        setActiveAssignment(res.assignment);
      }
    } catch (err) {
      Alert.alert('Generation Error', err.message || 'Failed to generate assignment');
      setLoading(false);
    }
  };

  const handleSelectOption = (qIdx, optIdx) => {
    setAnswers(prev => ({ ...prev, [qIdx]: optIdx }));
  };

  const handleSubmit = async () => {
    if (!activeAssignment) return;
    try {
      setSubmitting(true);
      const res = await submitAssignment(activeAssignment._id || activeAssignment.id, answers);
      setSubmissionResult(res);
      fetchAssignments();
    } catch (err) {
      Alert.alert('Submission Error', err.message || 'Failed to evaluate assignment');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading && assignments.length === 0) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#6366f1" />
      </View>
    );
  }

  // Active Assignment View
  if (activeAssignment) {
    return (
      <ScrollView style={styles.container}>
        <TouchableOpacity style={styles.backBtn} onPress={() => { setActiveAssignment(null); setSubmissionResult(null); }}>
          <Text style={styles.backBtnText}>← Back to Assignments</Text>
        </TouchableOpacity>

        <View style={styles.detailHeader}>
          <Text style={styles.assignTitle}>{activeAssignment.title}</Text>
          <Text style={styles.assignDesc}>{activeAssignment.description}</Text>
          <View style={styles.badgeRow}>
            <Text style={styles.diffBadge}>{activeAssignment.difficulty}</Text>
            <Text style={styles.statusBadge}>{activeAssignment.status}</Text>
          </View>
        </View>

        {/* Submission Feedback Banner */}
        {submissionResult && (
          <View style={styles.resultBanner}>
            <Text style={styles.resultScore}>Score: {Math.round(submissionResult.score || 0)}%</Text>
            <Text style={styles.resultXp}>+{submissionResult.xp_awarded || 50} XP Awarded!</Text>
            <Text style={styles.resultFeedback}>{submissionResult.feedback}</Text>
          </View>
        )}

        {/* Questions */}
        {activeAssignment.questions?.map((q, qIdx) => {
          const selectedOpt = answers[qIdx];
          return (
            <View key={qIdx} style={styles.questionCard}>
              <Text style={styles.questionNum}>Question {qIdx + 1}</Text>
              <Text style={styles.questionText}>{q.question_text || q.text}</Text>

              <View style={styles.optionsList}>
                {q.options?.map((opt, optIdx) => {
                  const isSelected = selectedOpt === optIdx;
                  return (
                    <TouchableOpacity
                      key={optIdx}
                      style={[styles.optBtn, isSelected && styles.optBtnSelected]}
                      onPress={() => handleSelectOption(qIdx, optIdx)}
                    >
                      <Text style={[styles.optText, isSelected && styles.optTextSelected]}>
                        {String.fromCharCode(65 + optIdx)}. {opt}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
            </View>
          );
        })}

        {activeAssignment.status !== 'EVALUATED' && !submissionResult && (
          <TouchableOpacity
            style={styles.submitBtn}
            onPress={handleSubmit}
            disabled={submitting}
          >
            {submitting ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <Text style={styles.submitBtnText}>Submit & Auto-Evaluate</Text>
            )}
          </TouchableOpacity>
        )}
      </ScrollView>
    );
  }

  // Assignments List View
  return (
    <ScrollView style={styles.container}>
      <View style={styles.headerRow}>
        <View>
          <Text style={styles.screenTitle}>📑 Intelligent Assignments</Text>
          <Text style={styles.screenSubtitle}>Lifecycle evaluation and mastery impact</Text>
        </View>
        <TouchableOpacity style={styles.createBtn} onPress={handleGenerateNew}>
          <Text style={styles.createBtnText}>+ Synthesize</Text>
        </TouchableOpacity>
      </View>

      {assignments.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyIcon}>📝</Text>
          <Text style={styles.emptyTitle}>No Assignments Yet</Text>
          <Text style={styles.emptyText}>Tap "+ Synthesize" above to generate your first AI assessment assignment.</Text>
        </View>
      ) : (
        assignments.map((a) => (
          <TouchableOpacity
            key={a._id || a.id}
            style={styles.assignCard}
            onPress={() => handleOpenAssignment(a._id || a.id)}
          >
            <View style={styles.assignCardHeader}>
              <Text style={styles.cardTitle}>{a.title}</Text>
              <Text style={[styles.cardStatus, a.status === 'EVALUATED' ? styles.statusDone : styles.statusDraft]}>
                {a.status}
              </Text>
            </View>
            <Text style={styles.cardDesc} numberOfLines={2}>{a.description}</Text>
            <View style={styles.cardFooter}>
              <Text style={styles.cardMeta}>{a.questions?.length || 0} Questions • {a.difficulty}</Text>
              {a.score !== undefined && a.score !== null && (
                <Text style={styles.cardScore}>{Math.round(a.score)}%</Text>
              )}
            </View>
          </TouchableOpacity>
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
  createBtn: { backgroundColor: '#6366f1', paddingVertical: 6, paddingHorizontal: 12, borderRadius: 8 },
  createBtnText: { color: '#ffffff', fontWeight: 'bold', fontSize: 11 },

  assignCard: { backgroundColor: '#101726', borderWidth: 1, borderColor: '#1e293b', borderRadius: 14, padding: 16, marginBottom: 10 },
  assignCardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 },
  cardTitle: { color: '#ffffff', fontSize: 14, fontWeight: 'bold', flex: 1 },
  cardStatus: { fontSize: 10, fontWeight: 'bold', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 },
  statusDone: { backgroundColor: 'rgba(16, 185, 129, 0.15)', color: '#34d399' },
  statusDraft: { backgroundColor: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24' },
  cardDesc: { color: '#94a3b8', fontSize: 11, lineHeight: 16, marginBottom: 8 },
  cardFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderTopWidth: 1, borderTopColor: '#1e293b', paddingTop: 8 },
  cardMeta: { color: '#64748b', fontSize: 10 },
  cardScore: { color: '#34d399', fontSize: 12, fontWeight: 'bold' },

  backBtn: { marginTop: 16, marginBottom: 12 },
  backBtnText: { color: '#818cf8', fontSize: 12, fontWeight: 'bold' },
  detailHeader: { backgroundColor: '#101726', padding: 16, borderRadius: 14, marginBottom: 12, borderWidth: 1, borderColor: '#1e293b' },
  assignTitle: { color: '#ffffff', fontSize: 16, fontWeight: 'bold', marginBottom: 4 },
  assignDesc: { color: '#94a3b8', fontSize: 12, lineHeight: 16, marginBottom: 8 },
  badgeRow: { flexDirection: 'row', gap: 6 },
  diffBadge: { backgroundColor: '#1e293b', color: '#cbd5e1', fontSize: 10, paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 },
  statusBadge: { backgroundColor: '#1e293b', color: '#818cf8', fontSize: 10, paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 },

  resultBanner: { backgroundColor: 'rgba(16, 185, 129, 0.12)', borderWidth: 1, borderColor: 'rgba(16, 185, 129, 0.3)', borderRadius: 12, padding: 14, marginBottom: 12 },
  resultScore: { color: '#34d399', fontSize: 18, fontWeight: 'bold' },
  resultXp: { color: '#fbbf24', fontSize: 12, fontWeight: 'bold', marginTop: 2 },
  resultFeedback: { color: '#cbd5e1', fontSize: 11, marginTop: 4, lineHeight: 16 },

  questionCard: { backgroundColor: '#101726', borderRadius: 12, padding: 14, marginBottom: 12, borderWidth: 1, borderColor: '#1e293b' },
  questionNum: { color: '#818cf8', fontSize: 10, fontWeight: 'bold', marginBottom: 4 },
  questionText: { color: '#ffffff', fontSize: 13, fontWeight: '600', lineHeight: 18, marginBottom: 10 },
  optionsList: { gap: 6 },
  optBtn: { backgroundColor: '#172136', padding: 10, borderRadius: 8, borderWidth: 1, borderColor: '#1e293b' },
  optBtnSelected: { borderColor: '#6366f1', backgroundColor: 'rgba(99, 102, 241, 0.15)' },
  optText: { color: '#cbd5e1', fontSize: 12 },
  optTextSelected: { color: '#ffffff', fontWeight: 'bold' },

  submitBtn: { backgroundColor: '#6366f1', paddingVertical: 12, borderRadius: 10, alignItems: 'center', marginVertical: 16 },
  submitBtnText: { color: '#ffffff', fontSize: 13, fontWeight: 'bold' },

  emptyContainer: { padding: 40, alignItems: 'center', marginTop: 40 },
  emptyIcon: { fontSize: 40, marginBottom: 12 },
  emptyTitle: { color: '#ffffff', fontSize: 16, fontWeight: 'bold', marginBottom: 6 },
  emptyText: { color: '#64748b', fontSize: 12, textAlign: 'center' }
});
