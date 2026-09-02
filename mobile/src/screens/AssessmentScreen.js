import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, ScrollView, TouchableOpacity, ActivityIndicator, Alert } from 'react-native';
import { getAdaptiveQuestion, submitAssessment } from '../services/api';

export default function AssessmentScreen({ navigation }) {
  const [question, setQuestion] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedOption, setSelectedOption] = useState(null);
  const [confidence, setConfidence] = useState(3);
  const [startTime, setStartTime] = useState(null);
  const [seenIds, setSeenIds] = useState([]);

  const fetchQuestion = async () => {
    try {
      setLoading(true);
      setSelectedOption(null);
      const data = await getAdaptiveQuestion(seenIds);
      setQuestion(data);
      setStartTime(Date.now());
    } catch (err) {
      console.log('Error fetching adaptive question:', err);
      Alert.alert('No Questions Available', 'Upload materials and mine concepts before starting quizzes.');
      navigation.navigate('Dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQuestion();
  }, []);

  const handleSubmit = async () => {
    if (selectedOption === null) {
      Alert.alert('Selection Required', 'Please select an option to submit.');
      return;
    }

    try {
      setLoading(true);
      const durationSeconds = (Date.now() - startTime) / 1000.0;
      
      const payload = [{
        question_id: question._id,
        selected_option_index: selectedOption,
        confidence: confidence,
        response_time_seconds: durationSeconds
      }];

      const res = await submitAssessment(payload);
      
      const result = res.review[0];
      const correctStr = result.is_correct ? 'Correct! 🎉' : 'Incorrect. ❌';
      
      Alert.alert(
        correctStr,
        `Explanation: ${result.explanation}\n\nYour Mastery: ${Math.round(result.new_mastery_score)}%`,
        [
          { 
            text: 'Next Question', 
            onPress: () => {
              setSeenIds([...seenIds, question._id]);
              fetchQuestion();
            } 
          },
          { 
            text: 'Exit Quiz', 
            onPress: () => navigation.navigate('Dashboard') 
          }
        ]
      );
    } catch (err) {
      Alert.alert('Error', 'Failed to submit quiz attempt.');
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#38bdf8" />
      </View>
    );
  }

  if (!question) {
    return (
      <View style={styles.center}>
        <Text style={styles.emptyText}>No active questions found.</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.conceptHeader}>
        <Text style={styles.conceptName}>Topic: {question.concept_name}</Text>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{question.difficulty}</Text>
        </View>
      </View>

      <Text style={styles.questionText}>{question.question_text}</Text>

      <View style={styles.optionsBlock}>
        {question.options.map((opt, idx) => (
          <TouchableOpacity 
            key={idx}
            style={[
              styles.optionButton,
              selectedOption === idx && styles.selectedOption
            ]}
            onPress={() => setSelectedOption(idx)}
          >
            <Text style={[
              styles.optionText,
              selectedOption === idx && styles.selectedOptionText
            ]}>{opt}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <View style={styles.confidenceSection}>
        <Text style={styles.confidenceLabel}>Confidence Level (1-5):</Text>
        <View style={styles.confidenceRow}>
          {[1, 2, 3, 4, 5].map((val) => (
            <TouchableOpacity
              key={val}
              style={[
                styles.confidenceButton,
                confidence === val && styles.selectedConfidence
              ]}
              onPress={() => setConfidence(val)}
            >
              <Text style={[
                styles.confidenceText,
                confidence === val && styles.selectedConfidenceText
              ]}>{val}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      <TouchableOpacity style={styles.submitButton} onPress={handleSubmit}>
        <Text style={styles.submitText}>Submit Answer</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f172a',
    padding: 15,
  },
  center: {
    flex: 1,
    backgroundColor: '#0f172a',
    alignItems: 'center',
    justifyContent: 'center',
  },
  conceptHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  conceptName: {
    fontSize: 14,
    color: '#94a3b8',
    fontWeight: 'bold',
  },
  badge: {
    backgroundColor: '#38bdf8',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  badgeText: {
    color: '#0f172a',
    fontSize: 9,
    fontWeight: 'bold',
  },
  questionText: {
    fontSize: 16,
    color: '#fff',
    fontWeight: '600',
    lineHeight: 24,
    marginBottom: 25,
  },
  optionsBlock: {
    marginBottom: 25,
  },
  optionButton: {
    backgroundColor: '#1e293b',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#334155',
    padding: 15,
    marginBottom: 10,
  },
  selectedOption: {
    borderColor: '#38bdf8',
    backgroundColor: 'rgba(56, 189, 248, 0.1)',
  },
  optionText: {
    color: '#fff',
    fontSize: 13,
  },
  selectedOptionText: {
    color: '#38bdf8',
    fontWeight: 'bold',
  },
  confidenceSection: {
    marginBottom: 30,
  },
  confidenceLabel: {
    fontSize: 12,
    color: '#94a3b8',
    fontWeight: 'bold',
    marginBottom: 10,
  },
  confidenceRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  confidenceButton: {
    width: '18%',
    height: 40,
    backgroundColor: '#1e293b',
    borderWidth: 1,
    borderColor: '#334155',
    borderRadius: 6,
    alignItems: 'center',
    justifyContent: 'center',
  },
  selectedConfidence: {
    backgroundColor: '#38bdf8',
    borderColor: '#38bdf8',
  },
  confidenceText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  selectedConfidenceText: {
    color: '#0f172a',
  },
  submitButton: {
    height: 48,
    backgroundColor: '#38bdf8',
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 40,
  },
  submitText: {
    color: '#0f172a',
    fontWeight: 'bold',
    fontSize: 14,
  },
  emptyText: {
    color: '#94a3b8',
    fontSize: 13,
  },
});
