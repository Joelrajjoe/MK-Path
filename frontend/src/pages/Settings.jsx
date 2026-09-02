import React, { useState, useEffect, useCallback } from 'react'
import { useUser, useAuth } from '@clerk/react'
import { useNavigate } from 'react-router-dom'
import {
  Settings as SettingsIcon, Bell, Palette, Accessibility,
  ShieldAlert, Trash2, AlertTriangle, CheckCircle, Loader2, X,
  Volume2, Eye, Type, Sun, Moon, ChevronRight
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const CLEAR_CATEGORIES = [
  { id: 'assessments', label: 'Assessment History', desc: 'Deletes all quiz attempts and responses', color: 'amber' },
  { id: 'gamification', label: 'XP & Achievements', desc: 'Resets XP, level, and unlocked badges to zero', color: 'purple' },
  { id: 'study_paths', label: 'Study Paths', desc: 'Clears all generated study path data', color: 'blue' },
  { id: 'concepts', label: 'Concepts & Graph', desc: 'Removes all extracted concepts and relationships', color: 'red' },
  { id: 'materials', label: 'All Materials & Data', desc: 'Removes materials, concepts, questions, attempts, mastery — everything', color: 'red' },
]

export default function Settings() {
  const { user } = useUser()
  const { getToken } = useAuth()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('account')
  const [toast, setToast] = useState(null)
  const [confirmModal, setConfirmModal] = useState(null) // { category, label }
  const [confirmText, setConfirmText] = useState('')
  const [clearing, setClearing] = useState(false)
  // Local appearance / accessibility prefs stored in localStorage
  const [fontSizePref, setFontSizePref] = useState(() => localStorage.getItem('mkp_font_size') || 'medium')
  const [reducedMotion, setReducedMotion] = useState(() => localStorage.getItem('mkp_reduced_motion') === 'true')
  const [highContrast, setHighContrast] = useState(() => localStorage.getItem('mkp_high_contrast') === 'true')
  const [ttsEnabled, setTtsEnabled] = useState(() => localStorage.getItem('mkp_tts') === 'true')
  const [ttsRate, setTtsRate] = useState(() => parseFloat(localStorage.getItem('mkp_tts_rate') || '1'))
  const [notifEnabled, setNotifEnabled] = useState(() => localStorage.getItem('mkp_notif') !== 'false')

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }

  // Apply localStorage prefs to document
  useEffect(() => {
    const fontMap = { small: '13px', medium: '15px', large: '17px', xlarge: '20px' }
    document.documentElement.style.setProperty('--mkp-font-size', fontMap[fontSizePref] || '15px')
    document.documentElement.classList.toggle('reduce-motion', reducedMotion)
    document.documentElement.classList.toggle('high-contrast', highContrast)
    localStorage.setItem('mkp_font_size', fontSizePref)
    localStorage.setItem('mkp_reduced_motion', reducedMotion)
    localStorage.setItem('mkp_high_contrast', highContrast)
    localStorage.setItem('mkp_tts', ttsEnabled)
    localStorage.setItem('mkp_tts_rate', ttsRate)
    localStorage.setItem('mkp_notif', notifEnabled)
  }, [fontSizePref, reducedMotion, highContrast, ttsEnabled, ttsRate, notifEnabled])

  const handleClear = async () => {
    if (!confirmModal) return
    if (confirmText.trim().toLowerCase() !== 'delete') {
      showToast('Type "delete" to confirm', 'error')
      return
    }
    setClearing(true)
    try {
      const token = await getToken()
      const res = await fetch(`${API}/api/data/clear`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ category: confirmModal.category })
      })
      if (!res.ok) throw new Error(await res.text())
      showToast(`Cleared: ${confirmModal.label}`)
      setConfirmModal(null)
      setConfirmText('')
    } catch (e) {
      showToast('Clear failed: ' + e.message, 'error')
    } finally {
      setClearing(false)
    }
  }

  const tabs = [
    { id: 'account', label: 'Account', icon: <SettingsIcon size={14} /> },
    { id: 'appearance', label: 'Appearance', icon: <Palette size={14} /> },
    { id: 'notifications', label: 'Notifications', icon: <Bell size={14} /> },
    { id: 'accessibility', label: 'Accessibility', icon: <Accessibility size={14} /> },
    { id: 'data', label: 'Privacy & Data', icon: <ShieldAlert size={14} /> },
  ]

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-6 right-6 z-50 flex items-center gap-2 px-5 py-3 rounded-xl shadow-2xl text-sm font-semibold border animate-in slide-in-from-right duration-300 ${
          toast.type === 'error'
            ? 'bg-red-950 border-red-500/40 text-red-300'
            : 'bg-emerald-950 border-emerald-500/40 text-emerald-300'
        }`}>
          {toast.type === 'error' ? <AlertTriangle size={16} /> : <CheckCircle size={16} />}
          {toast.msg}
        </div>
      )}

      {/* Confirm Modal */}
      {confirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-red-500/30 rounded-2xl p-6 max-w-sm w-full mx-4 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-red-500/10 rounded-lg"><AlertTriangle className="h-5 w-5 text-red-400" /></div>
              <h3 className="font-bold text-white">Confirm Delete</h3>
            </div>
            <p className="text-sm text-slate-400 mb-1">You are about to clear: <span className="text-white font-semibold">{confirmModal.label}</span></p>
            <p className="text-xs text-slate-500 mb-4">This cannot be undone. Type <span className="text-red-400 font-mono">delete</span> to confirm.</p>
            <input
              type="text"
              value={confirmText}
              onChange={e => setConfirmText(e.target.value)}
              placeholder="Type: delete"
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-sm text-white outline-none focus:border-red-500 mb-4"
            />
            <div className="flex gap-3">
              <button
                onClick={handleClear}
                disabled={clearing}
                className="flex-1 bg-red-700 hover:bg-red-600 disabled:opacity-50 text-white text-sm font-semibold py-2 rounded-xl transition flex items-center justify-center gap-2"
              >
                {clearing ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                {clearing ? 'Clearing…' : 'Clear Data'}
              </button>
              <button onClick={() => { setConfirmModal(null); setConfirmText('') }}
                className="flex-1 text-slate-400 text-sm border border-slate-700 rounded-xl py-2 hover:text-white transition">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex flex-col space-y-1">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Settings</h1>
        <p className="text-slate-400 text-sm">Manage preferences, appearance, and your application data.</p>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 bg-slate-900/50 border border-slate-800 rounded-xl p-1 flex-wrap">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold transition ${
              activeTab === t.id
                ? 'bg-indigo-600 text-white shadow'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="border border-slate-800 bg-slate-900/30 rounded-2xl p-6 space-y-6">
        {/* Account */}
        {activeTab === 'account' && (
          <div className="space-y-5">
            <SectionHeader icon={<SettingsIcon size={15} />} title="Account Information" />
            <div className="space-y-3">
              <InfoRow label="Name" value={user?.fullName || '—'} />
              <InfoRow label="Email" value={user?.primaryEmailAddress?.emailAddress || '—'} />
              <InfoRow label="User ID" value={user?.id ? user.id.slice(0, 20) + '…' : '—'} />
            </div>
            <div className="pt-2 border-t border-slate-800">
              <p className="text-xs text-slate-500 mb-3">Your identity and authentication is managed by Clerk. Use the profile button in the sidebar to change your password or email.</p>
              <button
                onClick={() => navigate('/profile')}
                className="flex items-center gap-2 text-sm text-indigo-400 hover:text-indigo-300 font-semibold transition"
              >
                Edit Learning Profile <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}

        {/* Appearance */}
        {activeTab === 'appearance' && (
          <div className="space-y-5">
            <SectionHeader icon={<Palette size={15} />} title="Appearance" />
            <SettingRow label="Font Size" desc="Adjusts text size across the application">
              <div className="flex gap-2">
                {['small', 'medium', 'large', 'xlarge'].map(s => (
                  <button key={s} onClick={() => setFontSizePref(s)}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold border transition ${fontSizePref === s ? 'bg-indigo-600 border-indigo-500 text-white' : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-white'}`}>
                    {s.charAt(0).toUpperCase() + s.slice(1)}
                  </button>
                ))}
              </div>
            </SettingRow>
            <SettingRow label="Reduced Motion" desc="Disables animations and transitions">
              <Toggle checked={reducedMotion} onChange={setReducedMotion} />
            </SettingRow>
            <SettingRow label="High Contrast" desc="Increases contrast for better visibility">
              <Toggle checked={highContrast} onChange={setHighContrast} />
            </SettingRow>
          </div>
        )}

        {/* Notifications */}
        {activeTab === 'notifications' && (
          <div className="space-y-5">
            <SectionHeader icon={<Bell size={15} />} title="Notifications" />
            <SettingRow label="In-App Notifications" desc="Show achievement and progress alerts">
              <Toggle checked={notifEnabled} onChange={setNotifEnabled} />
            </SettingRow>
            <p className="text-xs text-slate-600">Push notifications are not yet available. Email notifications are managed through Clerk account settings.</p>
          </div>
        )}

        {/* Accessibility */}
        {activeTab === 'accessibility' && (
          <div className="space-y-5">
            <SectionHeader icon={<Accessibility size={15} />} title="Accessibility & Voice" />
            <SettingRow label="Text-to-Speech" desc="Reads content aloud using browser speech synthesis">
              <Toggle checked={ttsEnabled} onChange={setTtsEnabled} />
            </SettingRow>
            {ttsEnabled && (
              <SettingRow label={`Speech Rate: ${ttsRate}×`} desc="Speed of text-to-speech narration">
                <input type="range" min="0.5" max="2" step="0.1"
                  value={ttsRate}
                  onChange={e => setTtsRate(parseFloat(e.target.value))}
                  className="w-36 accent-indigo-500"
                />
              </SettingRow>
            )}
            <div className="bg-slate-950/40 rounded-xl p-4 text-xs text-slate-500 space-y-1">
              <p className="font-semibold text-slate-400">Keyboard Navigation</p>
              <p><span className="font-mono text-slate-300">Ctrl + K</span> — Open global search</p>
              <p><span className="font-mono text-slate-300">Tab / Shift+Tab</span> — Navigate interactive elements</p>
              <p><span className="font-mono text-slate-300">Enter / Space</span> — Activate buttons and links</p>
              <p><span className="font-mono text-slate-300">Escape</span> — Close modals and dialogs</p>
            </div>
          </div>
        )}

        {/* Privacy & Data */}
        {activeTab === 'data' && (
          <div className="space-y-5">
            <SectionHeader icon={<ShieldAlert size={15} />} title="Privacy & Data Management" />
            <div className="bg-amber-950/20 border border-amber-500/20 rounded-xl p-4 text-xs text-amber-400 flex gap-2">
              <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold mb-0.5">Destructive operations</p>
                <p className="text-amber-500/80">All data clearing is permanent and cannot be undone. Your Clerk account and identity are NOT affected.</p>
              </div>
            </div>
            <div className="space-y-2">
              {CLEAR_CATEGORIES.map(cat => (
                <div key={cat.id} className="flex items-center justify-between p-4 border border-slate-800 rounded-xl hover:border-slate-700 transition group">
                  <div>
                    <p className="text-sm font-semibold text-white">{cat.label}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{cat.desc}</p>
                  </div>
                  <button
                    onClick={() => setConfirmModal({ category: cat.id, label: cat.label })}
                    className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg border transition flex-shrink-0 ml-4 ${
                      cat.color === 'red'
                        ? 'text-red-400 border-red-500/30 hover:bg-red-950/40'
                        : 'text-amber-400 border-amber-500/30 hover:bg-amber-950/40'
                    }`}
                  >
                    <Trash2 size={12} /> Clear
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/* ── Helpers ─────────────────────────────────────── */
function SectionHeader({ icon, title }) {
  return (
    <div className="flex items-center gap-2 text-indigo-400 pb-1 border-b border-slate-800">
      {icon}
      <span className="font-bold text-white text-sm">{title}</span>
    </div>
  )
}
function InfoRow({ label, value }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-slate-800/50">
      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{label}</span>
      <span className="text-sm text-slate-200">{value}</span>
    </div>
  )
}
function SettingRow({ label, desc, children }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-white">{label}</p>
        {desc && <p className="text-xs text-slate-500 mt-0.5">{desc}</p>}
      </div>
      <div className="flex-shrink-0">{children}</div>
    </div>
  )
}
function Toggle({ checked, onChange }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 rounded-full border-2 transition-colors duration-200 ${
        checked ? 'bg-indigo-600 border-indigo-500' : 'bg-slate-700 border-slate-600'
      }`}
    >
      <span className={`inline-block h-4 w-4 rounded-full bg-white shadow transform transition-transform duration-200 mt-0.5 ${checked ? 'translate-x-5' : 'translate-x-0.5'}`} />
    </button>
  )
}
