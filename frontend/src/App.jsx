import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Landing from './pages/Landing'
import SignInPage from './pages/SignInPage'
import SignUpPage from './pages/SignUpPage'
import Dashboard from './pages/Dashboard'
import Materials from './pages/Materials'
import KnowledgeGraph from './pages/KnowledgeGraph'
import Flashcards from './pages/Flashcards'
import Assessment from './pages/Assessment'
import StudyPath from './pages/StudyPath'
import Resources from './pages/Resources'
import Progress from './pages/Progress'
import Achievements from './pages/Achievements'
import Assignments from './pages/Assignments'
import Profile from './pages/Profile'
import Settings from './pages/Settings'
import AccessibilityPage from './pages/AccessibilityPage'
import Search from './pages/Search'
import ExportStudio from './pages/ExportStudio'
import StudyNotes from './pages/StudyNotes'
import ConceptTutor from './pages/ConceptTutor'
import NotFound from './pages/NotFound'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Routes Shell */}
        <Route path="/" element={<Layout />}>
          <Route index element={<Landing />} />
          <Route path="sign-in" element={<SignInPage />} />
          <Route path="sign-up" element={<SignUpPage />} />

          {/* Protected Routes Shell */}
          <Route element={<ProtectedRoute />}>
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="materials" element={<Materials />} />
            <Route path="knowledge-graph" element={<KnowledgeGraph />} />
            <Route path="flashcards" element={<Flashcards />} />
            <Route path="study-notes" element={<StudyNotes />} />
            <Route path="tutor" element={<ConceptTutor />} />
            <Route path="assessment" element={<Assessment />} />
            <Route path="study-path" element={<StudyPath />} />
            <Route path="resources" element={<Resources />} />
            <Route path="progress" element={<Progress />} />
            <Route path="achievements" element={<Achievements />} />
            <Route path="assignments" element={<Assignments />} />
            <Route path="export" element={<ExportStudio />} />
            <Route path="profile" element={<Profile />} />
            <Route path="settings" element={<Settings />} />
            <Route path="accessibility" element={<AccessibilityPage />} />
            <Route path="search" element={<Search />} />
          </Route>

          {/* 404 — proper page instead of redirect */}
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
