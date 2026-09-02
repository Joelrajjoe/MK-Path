import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, ScrollView, TouchableOpacity, ActivityIndicator, Alert } from 'react-native';
import { getDashboardStats, runDemoSeeder } from '../services/api';

export default function DashboardScreen({ navigation }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

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

  const handleSeed = async () => {
    try {
      setLoading(true);
      await runDemoSeeder();
      Alert.alert('Demo Seeder', 'Demo curriculum and user attempts seeded successfully.');
      fetchStats();
    } catch (err) {
      Alert.alert('Error', 'Failed to seed demo curriculum.');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#38bdf8" />
      </View>
    );
  }

  const averageMastery = stats?.average_mastery !== null ? `${Math.round(stats.average_mastery)}%` : 'Unassessed';

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.greeting}>Welcome, Learner</Text>
        <Text style={styles.subtitle}>Track your machine learning trajectory</Text>
      </View>

      <View style={styles.statsGrid}>
        <View style={styles.statCard}>
          <Text style={styles.statLabel}>Avg Mastery</Text>
          <Text style={styles.statValue}>{averageMastery}</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statLabel}>Concepts Mined</Text>
          <Text style={styles.statValue}>{stats?.concepts_count || 0}</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statLabel}>XP Level</Text>
          <Text style={styles.statValue}>Lv {stats?.level || 1}</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statLabel}>Streak</Text>
          <Text style={styles.statValue}>{stats?.study_streak || 0} Days</Text>
        </View>
      </View>

      {stats?.concepts_count === 0 && (
        <View style={styles.emptyCard}>
          <Text style={styles.emptyTitle}>Curriculum empty</Text>
          <Text style={styles.emptyText}>Upload your study materials or load the demo curriculum.</Text>
          <TouchableOpacity style={styles.seedButton} onPress={handleSeed}>
            <Text style={styles.seedButtonText}>Seed Demo Curriculum</Text>
          </TouchableOpacity>
        </View>
      )}

      <View style={styles.menu}>
        <TouchableOpacity style={styles.menuItem} onPress={() => navigation.navigate('Materials')}>
          <Text style={styles.menuText}>📂 Study Materials</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.menuItem} onPress={() => navigation.navigate('Concepts')}>
          <Text style={styles.menuText}>🧠 Curriculum Mapping</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.menuItem} onPress={() => navigation.navigate('StudyPath')}>
          <Text style={styles.menuText}>🎯 Spaced Repetition Study Path</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.menuItem} onPress={() => navigation.navigate('Assessment')}>
          <Text style={styles.menuText}>📝 Take Adaptive Quiz</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.menuItem} onPress={() => navigation.navigate('Progress')}>
          <Text style={styles.menuText}>📊 Analytical Dashboard</Text>
        </TouchableOpacity>
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
  header: {
    marginBottom: 20,
  },
  greeting: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#fff',
  },
  subtitle: {
    fontSize: 12,
    color: '#94a3b8',
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  statCard: {
    width: '48%',
    backgroundColor: '#1e293b',
    borderRadius: 8,
    padding: 15,
    borderWidth: 1,
    borderColor: '#334155',
    marginBottom: 12,
  },
  statLabel: {
    fontSize: 11,
    color: '#94a3b8',
    marginBottom: 4,
  },
  statValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#38bdf8',
  },
  emptyCard: {
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: 20,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#ef4444',
    marginBottom: 20,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 5,
  },
  emptyText: {
    fontSize: 12,
    color: '#94a3b8',
    textAlign: 'center',
    marginBottom: 15,
  },
  seedButton: {
    backgroundColor: '#38bdf8',
    paddingHorizontal: 15,
    paddingVertical: 10,
    borderRadius: 6,
  },
  seedButtonText: {
    color: '#0f172a',
    fontWeight: 'bold',
    fontSize: 12,
  },
  menu: {
    marginBottom: 40,
  },
  menuItem: {
    height: 52,
    backgroundColor: '#1e293b',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#334155',
    justifyContent: 'center',
    paddingHorizontal: 15,
    marginBottom: 10,
  },
  menuText: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '600',
  },
});
