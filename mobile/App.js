import React, { useState } from 'react';
import { StyleSheet, SafeAreaView, View, Text, TouchableOpacity, StatusBar } from 'react-native';
import AuthScreen from './src/screens/AuthScreen';
import DashboardScreen from './src/screens/DashboardScreen';
import GoalsScreen from './src/screens/GoalsScreen';
import DiagnosisScreen from './src/screens/DiagnosisScreen';
import SimulationScreen from './src/screens/SimulationScreen';
import AssignmentsScreen from './src/screens/AssignmentsScreen';
import KnowledgeGraphScreen from './src/screens/KnowledgeGraphScreen';
import MaterialsScreen from './src/screens/MaterialsScreen';
import UploadScreen from './src/screens/UploadScreen';
import AssessmentScreen from './src/screens/AssessmentScreen';
import StudyPathScreen from './src/screens/StudyPathScreen';
import ProfileScreen from './src/screens/ProfileScreen';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState('Auth');
  const [routeParams, setRouteParams] = useState(null);

  const navigate = (screen, params = null) => {
    setCurrentScreen(screen);
    setRouteParams(params);
  };

  const navigation = {
    navigate: navigate,
  };

  const renderScreen = () => {
    switch (currentScreen) {
      case 'Auth':
        return <AuthScreen navigation={navigation} />;
      case 'Dashboard':
        return <DashboardScreen navigation={navigation} />;
      case 'Goals':
        return <GoalsScreen navigation={navigation} />;
      case 'Diagnosis':
        return <DiagnosisScreen navigation={navigation} />;
      case 'Simulation':
        return <SimulationScreen navigation={navigation} />;
      case 'Assignments':
        return <AssignmentsScreen navigation={navigation} />;
      case 'Graph':
        return <KnowledgeGraphScreen navigation={navigation} />;
      case 'Materials':
        return <MaterialsScreen navigation={navigation} />;
      case 'Upload':
        return <UploadScreen navigation={navigation} />;
      case 'Assessment':
        return <AssessmentScreen navigation={navigation} />;
      case 'StudyPath':
        return <StudyPathScreen navigation={navigation} />;
      case 'Profile':
        return <ProfileScreen navigation={navigation} />;
      default:
        return <DashboardScreen navigation={navigation} />;
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#090d16" />
      <View style={styles.content}>
        {renderScreen()}
      </View>
      
      {currentScreen !== 'Auth' && (
        <View style={styles.navBar}>
          <TouchableOpacity style={styles.navBtn} onPress={() => navigate('Dashboard')}>
            <Text style={[styles.navIcon, currentScreen === 'Dashboard' && styles.navIconActive]}>🏠</Text>
            <Text style={[styles.navText, currentScreen === 'Dashboard' && styles.navTextActive]}>Home</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.navBtn} onPress={() => navigate('Goals')}>
            <Text style={[styles.navIcon, currentScreen === 'Goals' && styles.navIconActive]}>🎯</Text>
            <Text style={[styles.navText, currentScreen === 'Goals' && styles.navTextActive]}>Goals</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.navBtn} onPress={() => navigate('Graph')}>
            <Text style={[styles.navIcon, currentScreen === 'Graph' && styles.navIconActive]}>🕸️</Text>
            <Text style={[styles.navText, currentScreen === 'Graph' && styles.navTextActive]}>Graph</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.navBtn} onPress={() => navigate('Assessment')}>
            <Text style={[styles.navIcon, currentScreen === 'Assessment' && styles.navIconActive]}>📝</Text>
            <Text style={[styles.navText, currentScreen === 'Assessment' && styles.navTextActive]}>Quiz</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.navBtn} onPress={() => navigate('StudyPath')}>
            <Text style={[styles.navIcon, currentScreen === 'StudyPath' && styles.navIconActive]}>🗺️</Text>
            <Text style={[styles.navText, currentScreen === 'StudyPath' && styles.navTextActive]}>Path</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.navBtn} onPress={() => navigate('Profile')}>
            <Text style={[styles.navIcon, currentScreen === 'Profile' && styles.navIconActive]}>👤</Text>
            <Text style={[styles.navText, currentScreen === 'Profile' && styles.navTextActive]}>Profile</Text>
          </TouchableOpacity>
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#090d16',
  },
  content: {
    flex: 1,
  },
  navBar: {
    height: 60,
    backgroundColor: '#101726',
    borderTopWidth: 1,
    borderTopColor: '#1e293b',
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    paddingBottom: 4,
  },
  navBtn: {
    alignItems: 'center',
    paddingVertical: 4,
    paddingHorizontal: 8,
  },
  navIcon: {
    fontSize: 16,
    opacity: 0.6,
  },
  navIconActive: {
    opacity: 1,
    transform: [{ scale: 1.15 }],
  },
  navText: {
    color: '#64748b',
    fontSize: 10,
    marginTop: 2,
    fontWeight: '600',
  },
  navTextActive: {
    color: '#818cf8',
    fontWeight: 'bold',
  },
});
