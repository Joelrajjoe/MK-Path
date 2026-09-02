import React, { useState } from 'react';
import { StyleSheet, Text, View, TextInput, TouchableOpacity, Alert } from 'react-native';
import { setAuthToken } from '../services/api';

export default function AuthScreen({ navigation }) {
  const [token, setToken] = useState('');

  const handleLogin = () => {
    if (!token.trim()) {
      Alert.alert('Authentication Error', 'Please paste your Clerk session token to proceed.');
      return;
    }
    setAuthToken(token.trim());
    navigation.navigate('Dashboard');
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>MK-Path Mobile</Text>
      <Text style={styles.subtitle}>Adaptive Knowledge-Graph Platform</Text>
      
      <View style={styles.form}>
        <Text style={styles.label}>Paste Clerk Identity Token:</Text>
        <TextInput
          style={styles.input}
          placeholder="eyJhbGciOiJSUzI1Ni..."
          placeholderTextColor="#64748b"
          value={token}
          onChangeText={setToken}
          secureTextEntry
          autoCapitalize="none"
        />
        
        <TouchableOpacity style={styles.button} onPress={handleLogin}>
          <Text style={styles.buttonText}>Authenticate Session</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f172a',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#38bdf8',
    marginBottom: 5,
  },
  subtitle: {
    fontSize: 14,
    color: '#94a3b8',
    marginBottom: 40,
  },
  form: {
    width: '100%',
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: 20,
    borderWidth: 1,
    borderColor: '#334155',
  },
  label: {
    fontSize: 12,
    color: '#94a3b8',
    marginBottom: 8,
    fontWeight: 'bold',
  },
  input: {
    height: 48,
    backgroundColor: '#0f172a',
    borderRadius: 8,
    paddingHorizontal: 12,
    color: '#fff',
    borderWidth: 1,
    borderColor: '#334155',
    marginBottom: 20,
  },
  button: {
    height: 48,
    backgroundColor: '#38bdf8',
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonText: {
    color: '#0f172a',
    fontWeight: 'bold',
    fontSize: 14,
  },
});
