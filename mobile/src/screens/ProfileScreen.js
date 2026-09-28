import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, ScrollView, TouchableOpacity, TextInput, ActivityIndicator, Alert } from 'react-native';
import { getUserProfile, getUserPreferences, updateUserPreferences, setAuthToken } from '../services/api';

export default function ProfileScreen({ navigation }) {
  const [profile, setProfile] = useState(null);
  const [prefs, setPrefs] = useState({
    display_name: '',
    target_role: '',
    target_exam: '',
    current_level: 'Intermediate',
    preferred_difficulty: 'intermediate',
    daily_study_target_minutes: 30,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchProfileData();
  }, []);

  const fetchProfileData = async () => {
    try {
      setLoading(true);
      const [profData, prefData] = await Promise.allSettled([
        getUserProfile(),
        getUserPreferences(),
      ]);

      if (profData.status === 'fulfilled') setProfile(profData.value);
      if (prefData.status === 'fulfilled' && prefData.value) {
        setPrefs(prev => ({ ...prev, ...prefData.value }));
      }
    } catch (err) {
      console.warn('Failed to load profile:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await updateUserPreferences(prefs);
      Alert.alert('Success', 'Profile and study target preferences saved!');
    } catch (err) {
      Alert.alert('Save Error', err.message || 'Failed to update preferences');
    } finally {
      setSaving(false);
    }
  };

  const handleSignOut = () => {
    Alert.alert('Sign Out', 'Are you sure you want to sign out?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Sign Out',
        style: 'destructive',
        onPress: () => {
          setAuthToken(null);
          navigation.navigate('Auth');
        },
      },
    ]);
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#6366f1" />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>👤 Learner Profile</Text>
        <Text style={styles.subtitle}>Manage career targets, preferences & accessibility</Text>
      </View>

      {/* Profile Card */}
      <View style={styles.profileCard}>
        <View style={styles.avatarCircle}>
          <Text style={styles.avatarText}>
            {(profile?.display_name || profile?.email || 'L')[0].toUpperCase()}
          </Text>
        </View>
        <View style={styles.profileMeta}>
          <Text style={styles.profileName}>{profile?.display_name || 'Authenticated Learner'}</Text>
          <Text style={styles.profileEmail}>{profile?.email || 'user@mkpath.dev'}</Text>
        </View>
      </View>

      {/* Target Role & Career Preferences Form */}
      <View style={styles.sectionCard}>
        <Text style={styles.sectionHeading}>Career & Exam Benchmarks</Text>

        <Text style={styles.fieldLabel}>Display Name</Text>
        <TextInput
          style={styles.input}
          value={prefs.display_name || ''}
          onChangeText={(val) => setPrefs(p => ({ ...p, display_name: val }))}
          placeholder="Your full name"
          placeholderTextColor="#64748b"
        />

        <Text style={styles.fieldLabel}>Target Career Role</Text>
        <TextInput
          style={styles.input}
          value={prefs.target_role || ''}
          onChangeText={(val) => setPrefs(p => ({ ...p, target_role: val }))}
          placeholder="e.g. Senior Machine Learning Engineer"
          placeholderTextColor="#64748b"
        />

        <Text style={styles.fieldLabel}>Target Certification / Exam</Text>
        <TextInput
          style={styles.input}
          value={prefs.target_exam || ''}
          onChangeText={(val) => setPrefs(p => ({ ...p, target_exam: val }))}
          placeholder="e.g. AWS Certified Machine Learning"
          placeholderTextColor="#64748b"
        />

        <Text style={styles.fieldLabel}>Daily Study Target (Minutes)</Text>
        <TextInput
          style={styles.input}
          keyboardType="numeric"
          value={String(prefs.daily_study_target_minutes || 30)}
          onChangeText={(val) => setPrefs(p => ({ ...p, daily_study_target_minutes: parseInt(val, 10) || 30 }))}
          placeholderTextColor="#64748b"
        />

        <TouchableOpacity style={styles.saveBtn} onPress={handleSave} disabled={saving}>
          {saving ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Text style={styles.saveBtnText}>Save Preferences</Text>
          )}
        </TouchableOpacity>
      </View>

      {/* Sign Out Button */}
      <TouchableOpacity style={styles.signOutBtn} onPress={handleSignOut}>
        <Text style={styles.signOutBtnText}>Sign Out of MK-Path</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#090d16', paddingHorizontal: 16 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#090d16' },
  header: { marginTop: 20, marginBottom: 14 },
  title: { color: '#f8fafc', fontSize: 18, fontWeight: 'bold' },
  subtitle: { color: '#64748b', fontSize: 11, marginTop: 2 },

  profileCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#101726', padding: 16, borderRadius: 14, borderWidth: 1, borderColor: '#1e293b', marginBottom: 14 },
  avatarCircle: { width: 48, height: 48, borderRadius: 24, backgroundColor: '#6366f1', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  avatarText: { color: '#ffffff', fontSize: 20, fontWeight: 'bold' },
  profileMeta: { flex: 1 },
  profileName: { color: '#ffffff', fontSize: 15, fontWeight: 'bold' },
  profileEmail: { color: '#64748b', fontSize: 11, marginTop: 2 },

  sectionCard: { backgroundColor: '#101726', borderRadius: 14, padding: 16, borderWidth: 1, borderColor: '#1e293b', marginBottom: 16 },
  sectionHeading: { color: '#f8fafc', fontSize: 13, fontWeight: 'bold', marginBottom: 12 },
  fieldLabel: { color: '#94a3b8', fontSize: 11, fontWeight: '600', marginBottom: 4 },
  input: { backgroundColor: '#090d16', borderWidth: 1, borderColor: '#1e293b', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 8, color: '#ffffff', fontSize: 12, marginBottom: 12 },
  saveBtn: { backgroundColor: '#6366f1', paddingVertical: 10, borderRadius: 8, alignItems: 'center', marginTop: 4 },
  saveBtnText: { color: '#ffffff', fontSize: 12, fontWeight: 'bold' },

  signOutBtn: { backgroundColor: 'rgba(244, 63, 94, 0.1)', borderWidth: 1, borderColor: 'rgba(244, 63, 94, 0.3)', paddingVertical: 12, borderRadius: 10, alignItems: 'center', marginBottom: 32 },
  signOutBtnText: { color: '#f87171', fontSize: 12, fontWeight: 'bold' }
});
