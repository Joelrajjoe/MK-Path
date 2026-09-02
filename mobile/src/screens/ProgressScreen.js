import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, ScrollView, ActivityIndicator } from 'react-native';
import { getDashboardStats } from '../services/api';

export default function ProgressScreen() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const data = await getDashboardStats();
        setStats(data);
      } catch (err) {
        console.log('Error fetching stats:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#38bdf8" />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Analytical Dashboard</Text>
      
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Knowledge Streaks</Text>
        <Text style={styles.bigValue}>{stats?.study_streak || 0} Consecutive Days</Text>
        <Text style={styles.desc}>Keep studying or reviewing concepts daily to build your streak!</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Gamification Standing</Text>
        <View style={styles.row}>
          <Text style={styles.label}>Experience points:</Text>
          <Text style={styles.val}>{stats?.xp || 0} XP</Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>Player Level:</Text>
          <Text style={styles.val}>Level {stats?.level || 1} ({stats?.level_name || 'Beginner'})</Text>
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Curriculum Coverage</Text>
        <View style={styles.row}>
          <Text style={styles.label}>Concepts Mined:</Text>
          <Text style={styles.val}>{stats?.concepts_count || 0}</Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>Average Mastery Score:</Text>
          <Text style={styles.val}>{stats?.average_mastery !== null ? `${Math.round(stats.average_mastery)}%` : '0%'}</Text>
        </View>
      </View>
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
  title: {
    fontSize: 20,
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
    marginBottom: 15,
  },
  cardTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#38bdf8',
    marginBottom: 10,
  },
  bigValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 5,
  },
  desc: {
    fontSize: 11,
    color: '#94a3b8',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  label: {
    fontSize: 12,
    color: '#94a3b8',
  },
  val: {
    fontSize: 12,
    color: '#fff',
    fontWeight: 'bold',
  },
});
