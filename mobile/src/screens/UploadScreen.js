import React, { useState } from 'react';
import { StyleSheet, Text, View, TextInput, TouchableOpacity, Alert } from 'react-native';
import { uploadMaterial } from '../services/api';

export default function UploadScreen({ navigation }) {
  const [title, setTitle] = useState('');
  const [text, setText] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleUpload = async () => {
    if (!title.trim() || !text.trim()) {
      Alert.alert('Validation Error', 'Please fill in both the title and text content fields.');
      return;
    }

    try {
      setSubmitting(true);
      // Simulate multipart upload text payload
      const payload = new FormData();
      payload.append('title', title.trim());
      payload.append('file_name', `${title.toLowerCase().replace(/ /g, '_')}.txt`);
      payload.append('text_override', text.trim());
      
      // In a real device environment, this uses DocumentPicker to pick files.
      // For this MVP client, we expose a direct text payload submission.
      await uploadMaterial(payload);
      Alert.alert('Upload Complete', 'Material uploaded successfully. Concepts are being mined.');
      navigation.navigate('Materials');
    } catch (err) {
      Alert.alert('Error', 'Failed to upload material.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Upload Study Material</Text>
      
      <View style={styles.form}>
        <Text style={styles.label}>Material Title:</Text>
        <TextInput
          style={styles.input}
          placeholder="e.g. Intro to Neural Networks"
          placeholderTextColor="#64748b"
          value={title}
          onChangeText={setTitle}
        />
        
        <Text style={styles.label}>Paste Notes / Transcript Text Content:</Text>
        <TextInput
          style={[styles.input, styles.textArea]}
          placeholder="Neural networks are computational models inspired by the human brain..."
          placeholderTextColor="#64748b"
          value={text}
          onChangeText={setText}
          multiline
          numberOfLines={10}
        />
        
        <TouchableOpacity 
          style={[styles.button, submitting && { opacity: 0.6 }]} 
          onPress={handleUpload}
          disabled={submitting}
        >
          <Text style={styles.buttonText}>{submitting ? 'Uploading...' : 'Extract Concepts'}</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f172a',
    padding: 15,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 20,
  },
  form: {
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
  textArea: {
    height: 160,
    textAlignVertical: 'top',
    paddingVertical: 12,
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
