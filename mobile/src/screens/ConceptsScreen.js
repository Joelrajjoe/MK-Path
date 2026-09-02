import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, FlatList, TouchableOpacity, ActivityIndicator } from 'react-native';
import { getConcepts } from '../services/api';

export default function ConceptsScreen({ navigation }) {
  const [concepts, setConcepts] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchConcepts = async () => {
    try {
      setLoading(true);
      const data = await getConcepts();
      setConcepts(data);
    } catch (err) {
      console.log('Error fetching concepts:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConcepts();
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
      <Text style={styles.title}>Curriculum Mapping</Text>
      
      <FlatList
        data={concepts}
        keyExtractor={(item) => item._id}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <View style={styles.row}>
              <Text style={styles.cardTitle}>{item.name}</Text>
              <View style={styles.badge}>
                <Text style={styles.badgeText}>{item.difficulty}</Text>
              </View>
            </View>
            <Text style={styles.desc}>{item.description}</Text>
            
            <View style={styles.metaRow}>
              <Text style={styles.metaLabel}>Exam Rel: <Text style={styles.metaVal}>{item.exam_relevance}%</Text></Text>
              <Text style={styles.metaLabel}>Industry Rel: <Text style={styles.metaVal}>{item.industry_relevance}%</Text></Text>
            </View>
            
            <TouchableOpacity 
              style={styles.recommendButton} 
              onPress={() => navigation.navigate('Resources', { conceptName: item.name })}
            >
              <Text style={styles.recommendButtonText}>View Recommended Guides</Text>
            </TouchableOpacity>
          </View>
        )}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyText}>No concepts mined yet.</Text>
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
    backgroundColor: '#1e293b',
    borderRadius: 8,
    padding: 15,
    borderWidth: 1,
    borderColor: '#334155',
    marginBottom: 12,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  cardTitle: {
    fontSize: 15,
    fontWeight: 'bold',
    color: '#fff',
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
    textTransform: 'uppercase',
  },
  desc: {
    fontSize: 12,
    color: '#94a3b8',
    lineHeight: 18,
    marginBottom: 12,
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 15,
    borderTopWidth: 1,
    borderTopColor: '#334155',
    paddingTop: 8,
  },
  metaLabel: {
    fontSize: 11,
    color: '#94a3b8',
  },
  metaVal: {
    color: '#38bdf8',
    fontWeight: 'bold',
  },
  recommendButton: {
    height: 36,
    backgroundColor: '#334155',
    borderRadius: 6,
    alignItems: 'center',
    justifyContent: 'center',
  },
  recommendButtonText: {
    color: '#fff',
    fontSize: 12,
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
