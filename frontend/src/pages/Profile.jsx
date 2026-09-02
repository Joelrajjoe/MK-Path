import React, { useState, useEffect } from 'react'
import { useUser, useAuth } from '@clerk/react'
import {
  User, Save, AlertCircle, CheckCircle, Loader2,
  BookOpen, Briefcase, Target, Clock, Zap, RotateCcw
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const DIFFICULTY_OPTIONS = ['basic', 'intermediate', 'advanced']
const RESOURCE_TYPE_OPTIONS = ['video', 'article', 'documentation', 'tutorial', 'book']
const INDUSTRY_OPTIONS = [
  'Software Engineering', 'Data Science', 'Machine Learning', 'DevOps',
  'Cybersecurity', 'Finance', 'Healthcare', 'Business Analysis',
  'Product Management', 'UX Design'
]

const defaultPrefs = {
  preferred_name: '',
  learning_goal: '',
  target_role: '',
  preferred_difficulty: 'intermediate',
  daily_study_target_minutes: 30,
  preferred_session_duration_minutes: 25,
  exam_target: '',
  industry_interests: [],
  preferred_resource_types: [],
  notifications_enabled: true,
}

export default function Profile() {
  const { user } = useUser()
  const { getToken } = useAuth()
  const [prefs, setPrefs] = useState(defaultPrefs)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState(null)

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }

  useEffect(() => {
    const load = async () => {
      try {
        const token = await getToken()
        const res = await fetch(`${API}/api/user/preferences`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        if (res.ok) {
          const data = await res.json()
          setPrefs(prev => ({ ...prev, ...data }))
        }
      } catch (e) {
        console.error('Failed to load preferences:', e)
      } finally {
        setLoading(false)
      }
    }
    if (user) load()
  }, [user])

  const handleSave = async () => {
    setSaving(true)
    try {
      const token = await getToken()
      const res = await fetch(`${API}/api/user/preferences`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(prefs)
      })
      if (!res.ok) throw new Error(await res.text())
      showToast('Preferences saved!')
    } catch (e) {
      showToast('Failed to save: ' + e.message, 'error')
    } finally {
      setSaving(false)
    }
  }

  const toggleArrayItem = (key, val) => {
    setPrefs(p => ({
      ...p,
      [key]: p[key].includes(val) ? p[key].filter(x => x !== val) : [...p[key], val]
    }))
  }

  if (loading) return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
    </div>
  )

  return (
    <div className="space-y-8 max-w-3xl mx-auto">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-6 right-6 z-50 flex items-center gap-2 px-5 py-3 rounded-xl shadow-2xl text-sm font-semibold border animate-in slide-in-from-right duration-300 ${
          toast.type === 'error'
            ? 'bg-red-950 border-red-500/40 text-red-300'
            : 'bg-emerald-950 border-emerald-500/40 text-emerald-300'
        }`}>
          {toast.type === 'error' ? <AlertCircle size={16} /> : <CheckCircle size={16} />}
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col space-y-1">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Learner Profile</h1>
        <p className="text-slate-400 text-sm">Personalise your learning experience. All fields are optional.</p>
      </div>

      {/* Clerk Identity Card */}
      <div className="border border-slate-700/60 bg-slate-900/50 rounded-2xl p-6 flex items-center gap-5 shadow-lg">
        {user?.imageUrl
          ? <img src={user.imageUrl} alt="avatar" className="h-16 w-16 rounded-full border-2 border-indigo-500/50 object-cover" />
          : <div className="h-16 w-16 rounded-full bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center">
              <User className="h-7 w-7 text-indigo-400" />
            </div>
        }
        <div className="flex-1 min-w-0">
          <p className="text-lg font-bold text-white truncate">{user?.fullName || 'Learner'}</p>
          <p className="text-sm text-slate-400 truncate">{user?.primaryEmailAddress?.emailAddress}</p>
          <p className="text-xs text-slate-600 mt-0.5">Identity managed by Clerk · <span className="text-indigo-500">Account verified</span></p>
        </div>
      </div>

      {/* Personal Preferences */}
      <Section icon={<User size={16} />} title="Personal" subtitle="How you'd like to be addressed">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Preferred Name">
            <input
              id="preferred_name"
              type="text"
              placeholder="e.g. Alex"
              value={prefs.preferred_name || ''}
              onChange={e => setPrefs(p => ({ ...p, preferred_name: e.target.value }))}
              className={inputCls}
            />
          </Field>
          <Field label="Target Role">
            <input
              id="target_role"
              type="text"
              placeholder="e.g. ML Engineer"
              value={prefs.target_role || ''}
              onChange={e => setPrefs(p => ({ ...p, target_role: e.target.value }))}
              className={inputCls}
            />
          </Field>
        </div>
        <Field label="Learning Goal">
          <textarea
            id="learning_goal"
            rows={2}
            placeholder="What do you want to achieve? e.g. Pass the AWS exam, become proficient in React..."
            value={prefs.learning_goal || ''}
            onChange={e => setPrefs(p => ({ ...p, learning_goal: e.target.value }))}
            className={`${inputCls} resize-none`}
          />
        </Field>
        <Field label="Exam / Certification Target">
          <input
            id="exam_target"
            type="text"
            placeholder="e.g. AWS Solutions Architect, IELTS, CFA..."
            value={prefs.exam_target || ''}
            onChange={e => setPrefs(p => ({ ...p, exam_target: e.target.value }))}
            className={inputCls}
          />
        </Field>
      </Section>

      {/* Study Preferences */}
      <Section icon={<Clock size={16} />} title="Study Preferences" subtitle="Daily targets and session length">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label={`Daily Study Target: ${prefs.daily_study_target_minutes} min`}>
            <input
              id="daily_study_target"
              type="range" min="5" max="480" step="5"
              value={prefs.daily_study_target_minutes}
              onChange={e => setPrefs(p => ({ ...p, daily_study_target_minutes: parseInt(e.target.value) }))}
              className="w-full accent-indigo-500 mt-2"
            />
          </Field>
          <Field label={`Preferred Session: ${prefs.preferred_session_duration_minutes} min`}>
            <input
              id="preferred_session"
              type="range" min="5" max="120" step="5"
              value={prefs.preferred_session_duration_minutes}
              onChange={e => setPrefs(p => ({ ...p, preferred_session_duration_minutes: parseInt(e.target.value) }))}
              className="w-full accent-indigo-500 mt-2"
            />
          </Field>
        </div>
        <Field label="Content Difficulty">
          <div className="flex gap-2 flex-wrap">
            {DIFFICULTY_OPTIONS.map(d => (
              <button
                key={d}
                onClick={() => setPrefs(p => ({ ...p, preferred_difficulty: d }))}
                className={`px-4 py-1.5 rounded-lg text-xs font-semibold border transition ${
                  prefs.preferred_difficulty === d
                    ? 'bg-indigo-600 border-indigo-500 text-white shadow-md'
                    : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-indigo-500/50 hover:text-white'
                }`}
              >{d.charAt(0).toUpperCase() + d.slice(1)}</button>
            ))}
          </div>
        </Field>
      </Section>

      {/* Industry Interests */}
      <Section icon={<Briefcase size={16} />} title="Industry Interests" subtitle="Select all that apply">
        <div className="flex flex-wrap gap-2">
          {INDUSTRY_OPTIONS.map(ind => (
            <button
              key={ind}
              onClick={() => toggleArrayItem('industry_interests', ind)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
                prefs.industry_interests.includes(ind)
                  ? 'bg-purple-700/40 border-purple-500/60 text-purple-300'
                  : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-purple-500/40 hover:text-white'
              }`}
            >{ind}</button>
          ))}
        </div>
      </Section>

      {/* Preferred Resource Types */}
      <Section icon={<BookOpen size={16} />} title="Preferred Resources" subtitle="Types of learning content you prefer">
        <div className="flex flex-wrap gap-2">
          {RESOURCE_TYPE_OPTIONS.map(rt => (
            <button
              key={rt}
              onClick={() => toggleArrayItem('preferred_resource_types', rt)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
                prefs.preferred_resource_types.includes(rt)
                  ? 'bg-emerald-700/30 border-emerald-500/50 text-emerald-300'
                  : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-emerald-500/40 hover:text-white'
              }`}
            >{rt.charAt(0).toUpperCase() + rt.slice(1)}</button>
          ))}
        </div>
      </Section>

      {/* Action Buttons */}
      <div className="flex items-center gap-3 pb-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-semibold px-6 py-2.5 rounded-xl transition shadow-lg shadow-indigo-900/30"
        >
          {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
          {saving ? 'Saving…' : 'Save Profile'}
        </button>
        <button
          onClick={() => setPrefs(defaultPrefs)}
          className="flex items-center gap-2 text-slate-400 hover:text-white text-sm font-medium px-4 py-2.5 rounded-xl border border-slate-700 hover:border-slate-500 transition"
        >
          <RotateCcw size={14} /> Reset
        </button>
      </div>
    </div>
  )
}

/* ── Helpers ──────────────────────────────────────── */
const inputCls = 'w-full px-3.5 py-2 bg-slate-950/60 border border-slate-700 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/40 rounded-lg text-sm text-slate-200 outline-none placeholder-slate-600 transition'

function Section({ icon, title, subtitle, children }) {
  return (
    <div className="border border-slate-800/70 bg-slate-900/30 rounded-2xl p-6 space-y-4 shadow">
      <div className="flex items-center gap-2 text-indigo-400">
        {icon}
        <span className="font-bold text-white text-sm">{title}</span>
        {subtitle && <span className="text-slate-500 text-xs">· {subtitle}</span>}
      </div>
      {children}
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-semibold text-slate-400 uppercase tracking-wide">{label}</label>
      {children}
    </div>
  )
}
