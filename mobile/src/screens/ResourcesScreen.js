import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, FlatList, TouchableOpacity, ActivityIndicator, Linking, Alert } from 'react-native';
import { getRecommendedResources, submitResourceFeedback, completeResource, trackResourceClick } from '../services/api';

export default function ResourcesScreen({ route }) {
  const conceptName = route?.params?.conceptName || 'Linear Regression';
  const [resources, setResources] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchResources = async () => {
    try {
      setLoading(true);
      const data = await getRecommendedResources(conceptName);
      setResources(data);
    } catch (err) {
      console.log('Error fetching resources:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResources();
  }, [conceptName]);

  const handleOpen = async (res) => {
    try {
      await trackResourceClick(res._id);
      Linking.openURL(res.url);
    } catch (err) {
      Alert.alert('Error', 'Failed to open resource link.');
    }
  };

  const handleComplete = async (resId) => {
    try {
      await completeResource(resId);
      Alert.alert('Status Updated', 'Resource marked as completed (+10 XP).');
      fetchResources();
    } catch (err) {
      Alert.alert('Error', 'Failed to record completion.');
    }
  };

  const handleFeedback = async (resId, isHelpful) => {
    try {
      await submitResourceFeedback(resId, null, isHelpful);
      Alert.alert('Feedback Registered', 'Thank you for your rating! (+10 XP).');
      fetchResources();
    } catch (err) {
      Alert.alert('Error', 'Failed to register feedback.');
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#38bdf8" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Guides for: {conceptName}</Text>
      
      <FlatList
        data={resources}
        keyExtractor={(item) => item._id}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <Text style={styles.resTitle}>{item.title}</Text>
            <Text style={styles.reason}>{item.rank_reason}</Text>
            
            <View style={styles.actions}>
              <TouchableOpacity style={styles.buttonLink} onPress={() => handleOpen(item)}>
                <Text style={styles.buttonLinkText}>🌐 Open Link</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.buttonLink} onPress={() => handleComplete(item._id)}>
                <Text style={styles.buttonLinkText}>✅ Complete</Text>
              </TouchableOpacity>
            </View>
            
            <View style={styles.helpfulBlock}>
              <Text style={styles.helpfulText}>Was this helpful?</Text>
              <View style={styles.helpfulButtons}>
                <TouchableOpacity style={styles.voteBtn} onPress={() => handleFeedback(item._id, true)}>
                  <Text style={styles.voteBtnText}>Yes 👍</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.voteBtn} onPress={() => handleFeedback(item._id, false)}>
                  <Text style={styles.voteBtnText}>No 👎</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        )}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyText}>No recommended resources for this concept.</Text>
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
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 20,
  },
  card: {
    backgroundColor: '#1e293b',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#334155',
    padding: 15,
    marginBottom: 12,
  },
  resTitle: {
    fontSize: 13,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 6,
  },
  reason: {
    fontSize: 11,
    color: '#94a3b8',
    marginBottom: 12,
  },
  actions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 15,
  },
  buttonLink: {
    width: '48%',
    height: 36,
    backgroundColor: '#334155',
    borderRadius: 6,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonLinkText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: 'bold',
  },
  helpfulBlock: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: '#334155',
    paddingTop: 10,
  },
  helpfulText: {
    fontSize: 11,
    color: '#94a3b8',
  },
  helpfulButtons: {
    flexDirection: 'row',
  },
  voteBtn: {
    backgroundColor: '#0f172a',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: '#334155',
    marginLeft: 6,
  },
  voteBtnText: {
    color: '#fff',
    fontSize: 10,
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
