import React, { useState } from 'react';
import { StyleSheet, SafeAreaView, View, Text, TouchableOpacity } from 'react-native';
import AuthScreen from './src/screens/AuthScreen';
import DashboardScreen from './src/screens/DashboardScreen';
import MaterialsScreen from './src/screens/MaterialsScreen';
import UploadScreen from './src/screens/UploadScreen';
import ConceptsScreen from './src/screens/ConceptsScreen';
import AssessmentScreen from './src/screens/AssessmentScreen';
import StudyPathScreen from './src/screens/StudyPathScreen';
import ResourcesScreen from './src/screens/ResourcesScreen';
import ProgressScreen from './src/screens/ProgressScreen';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState('Auth');
  const [routeParams, setRouteParams] = useState(null);

  const navigate = (screen, params = null) => {
    setCurrentScreen(screen);
    setRouteParams(params);
  };

  // Polyfill React Navigation stack navigator
  const navigation = {
    navigate: navigate
  };

  const renderScreen = () => {
    switch (currentScreen) {
      case 'Auth':
        return <AuthScreen navigation={navigation} />;
      case 'Dashboard':
        return <DashboardScreen navigation={navigation} />;
      case 'Materials':
        return <MaterialsScreen navigation={navigation} />;
      case 'Upload':
        return <UploadScreen navigation={navigation} />;
      case 'Concepts':
        return <ConceptsScreen navigation={navigation} />;
      case 'Assessment':
        return <AssessmentScreen navigation={navigation} />;
      case 'StudyPath':
        return <StudyPathScreen navigation={navigation} />;
      case 'Resources':
        return <ResourcesScreen route={{ params: routeParams }} navigation={navigation} />;
      case 'Progress':
        return <ProgressScreen navigation={navigation} />;
      default:
        return <AuthScreen navigation={navigation} />;
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        {renderScreen()}
      </View>
      
      {currentScreen !== 'Auth' && (
        <View style={styles.navBar}>
          <TouchableOpacity style={styles.navBtn} onPress={() => navigate('Dashboard')}>
            <Text style={styles.navText}>🏠 Home</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.navBtn} onPress={() => navigate('StudyPath')}>
            <Text style={styles.navText}>🎯 Path</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.navBtn} onPress={() => navigate('Assessment')}>
            <Text style={styles.navText}>📝 Quiz</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.navBtn} onPress={() => navigate('Progress')}>
            <Text style={styles.navText}>📊 Stats</Text>
          </TouchableOpacity>
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f172a',
  },
  content: {
    flex: 1,
  },
  navBar: {
    height: 56,
    backgroundColor: '#1e293b',
    borderTopWidth: 1,
    borderTopColor: '#334155',
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
  },
  navBtn: {
    padding: 8,
  },
  navText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
});
