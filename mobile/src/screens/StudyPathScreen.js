import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, FlatList, TouchableOpacity, ActivityIndicator } from 'react-native';
import { getStudyPath } from '../services/api';

export default function StudyPathScreen({ navigation }) {
  const [pathItems, setPathItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchStudyPath = async () => {
    try {
      setLoading(true);
      const data = await getStudyPath();
      setPathItems(data.ordered_concepts || []);
    } catch (err) {
      console.log('Error fetching study path:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStudyPath();
  }, []);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#38bdf8" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Study Path Recommendation</Text>
      
      <FlatList
        data={pathItems}
        keyExtractor={(item) => item.concept_id}
        renderItem={({ item, index }) => (
          <View style={styles.card}>
            <View style={styles.stepIndicator}>
              <Text style={styles.stepNum}>#{index + 1}</Text>
            </View>
            
            <View style={styles.content}>
              <Text style={styles.conceptName}>{item.concept_name}</Text>
              <Text style={styles.reason}>{item.reason}</Text>
              
              <View style={styles.meta}>
                <Text style={styles.metaText}>Score: {Math.round(item.mastery_score)}%</Text>
                <View style={[
                  styles.badge,
                  { backgroundColor: item.category === 'Mastered' ? '#10b981' : '#ef4444' }
                ]}>
                  <Text style={styles.badgeText}>{item.category}</Text>
                </View>
              </View>
              
              <TouchableOpacity 
                style={styles.actionButton} 
                onPress={() => navigation.navigate('Resources', { conceptName: item.concept_name })}
              >
                <Text style={styles.actionText}>Study Guides & Video Tutorials</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyText}>Study path empty. Seed or upload materials first.</Text>
          </View>
        }
      />
    </View>
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
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 20,
  },
  card: {
    flexDirection: 'row',
    backgroundColor: '#1e293b',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#334155',
    padding: 15,
    marginBottom: 15,
  },
  stepIndicator: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#38bdf8',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  stepNum: {
    color: '#0f172a',
    fontWeight: 'bold',
    fontSize: 12,
  },
  content: {
    flex: 1,
  },
  conceptName: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 6,
  },
  reason: {
    fontSize: 11,
    color: '#94a3b8',
    lineHeight: 16,
    marginBottom: 12,
  },
  meta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  metaText: {
    fontSize: 11,
    color: '#94a3b8',
    fontWeight: 'bold',
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  badgeText: {
    color: '#fff',
    fontSize: 9,
    fontWeight: 'bold',
  },
  actionButton: {
    height: 34,
    backgroundColor: '#334155',
    borderRadius: 6,
    alignItems: 'center',
    justifyContent: 'center',
  },
  actionText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '600',
  },
  empty: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyText: {
    color: '#94a3b8',
    fontSize: 12,
  },
});
