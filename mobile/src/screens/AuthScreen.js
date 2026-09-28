import React, { useState } from 'react';
import { StyleSheet, Text, View, TextInput, TouchableOpacity, Alert, ActivityIndicator } from 'react-native';
import { setAuthToken } from '../services/api';

export default function AuthScreen({ navigation }) {
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!token.trim()) {
      Alert.alert('Authentication Required', 'Please enter your Clerk JWT session token or use the Demo mode.');
      return;
    }
    try {
      setLoading(true);
      setAuthToken(token.trim());
      navigation.navigate('Dashboard');
    } catch (err) {
      Alert.alert('Auth Error', 'Failed to authenticate session.');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = () => {
    // Standard mock demo token for immediate sandbox evaluation
    const demoToken = 'mock_demo_jwt_session_token_mkpath';
    setAuthToken(demoToken);
    navigation.navigate('Dashboard');
  };

  return (
    <View style={styles.container}>
      <View style={styles.brandBox}>
        <Text style={styles.logoIcon}>🎓</Text>
        <Text style={styles.title}>MK-Path</Text>
        <Text style={styles.subtitle}>Mobile Learner Intelligence Engine</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardHeading}>Sign In with Clerk</Text>
        <Text style={styles.infoText}>
          Enter your authenticated Clerk session token from the MK-Path Web client or mobile session.
        </Text>

        <TextInput
          style={styles.input}
          placeholder="Paste JWT Token (Bearer eyJhbG...)"
          placeholderTextColor="#64748b"
          value={token}
          onChangeText={setToken}
          autoCapitalize="none"
          autoCorrect={false}
        />

        <TouchableOpacity style={styles.primaryBtn} onPress={handleLogin} disabled={loading}>
          {loading ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Text style={styles.primaryBtnText}>Authenticate with Clerk</Text>
          )}
        </TouchableOpacity>

        <View style={styles.dividerRow}>
          <View style={styles.line} />
          <Text style={styles.orText}>OR</Text>
          <View style={styles.line} />
        </View>

        <TouchableOpacity style={styles.demoBtn} onPress={handleDemoLogin}>
          <Text style={styles.demoBtnText}>⚡ Instant Demo Evaluation Mode</Text>
        </TouchableOpacity>
      </View>

      <Text style={styles.securityFooter}>
        🔒 All intelligence calculations, BKT, and graph analytics execute server-side on FastAPI.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#090d16', padding: 20, justifyContent: 'center' },
  brandBox: { alignItems: 'center', marginBottom: 28 },
  logoIcon: { fontSize: 44, marginBottom: 8 },
  title: { color: '#f8fafc', fontSize: 26, fontWeight: 'bold', letterSpacing: -0.5 },
  subtitle: { color: '#64748b', fontSize: 12, marginTop: 4 },

  card: { backgroundColor: '#101726', borderRadius: 16, padding: 20, borderWidth: 1, borderColor: '#1e293b' },
  cardHeading: { color: '#ffffff', fontSize: 16, fontWeight: 'bold', marginBottom: 6 },
  infoText: { color: '#94a3b8', fontSize: 11, lineHeight: 16, marginBottom: 14 },
  input: { backgroundColor: '#090d16', borderWidth: 1, borderColor: '#1e293b', borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, color: '#ffffff', fontSize: 12, marginBottom: 14 },

  primaryBtn: { backgroundColor: '#6366f1', paddingVertical: 12, borderRadius: 10, alignItems: 'center' },
  primaryBtnText: { color: '#ffffff', fontSize: 13, fontWeight: 'bold' },

  dividerRow: { flexDirection: 'row', alignItems: 'center', marginVertical: 14 },
  line: { flex: 1, height: 1, backgroundColor: '#1e293b' },
  orText: { color: '#64748b', fontSize: 10, marginHorizontal: 10, fontWeight: 'bold' },

  demoBtn: { backgroundColor: '#172136', borderWidth: 1, borderColor: '#334155', paddingVertical: 11, borderRadius: 10, alignItems: 'center' },
  demoBtnText: { color: '#cbd5e1', fontSize: 12, fontWeight: '600' },

  securityFooter: { color: '#475569', fontSize: 10, textAlign: 'center', marginTop: 24, paddingHorizontal: 20, lineHeight: 14 }
});
