import React, { useState, useEffect } from 'react'
import { useUser, useAuth } from '@clerk/react'
import { Trophy, Zap, Star, Lock, Loader2, AlertCircle, Crown } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// All defined achievements with metadata for display
const ACHIEVEMENT_METADATA = {
  first_upload: { label: 'First Upload', icon: '📄', desc: 'Uploaded your first study material', color: 'blue' },
  first_quiz: { label: 'Quiz Starter', icon: '✏️', desc: 'Completed your first quiz question', color: 'indigo' },
  perfect_quiz: { label: 'Perfectionist', icon: '💯', desc: 'Scored 100% on a concept quiz', color: 'emerald' },
  streak_3: { label: '3-Day Streak', icon: '🔥', desc: 'Studied 3 days in a row', color: 'amber' },
  streak_7: { label: 'Week Warrior', icon: '🏆', desc: 'Maintained a 7-day learning streak', color: 'amber' },
  mastered_5: { label: 'Concept Master', icon: '🧠', desc: 'Mastered 5 concepts', color: 'purple' },
  mastered_20: { label: 'Knowledge Base', icon: '🌐', desc: 'Mastered 20 concepts', color: 'purple' },
  level_5: { label: 'Rising Scholar', icon: '⭐', desc: 'Reached Level 5', color: 'yellow' },
  level_10: { label: 'Expert Learner', icon: '🎓', desc: 'Reached Level 10', color: 'yellow' },
  first_path: { label: 'Path Finder', icon: '🗺️', desc: 'Generated your first study path', color: 'teal' },
  first_assignment: { label: 'Assigned', icon: '📝', desc: 'Completed your first assignment', color: 'indigo' },
  speedster: { label: 'Speedster', icon: '⚡', desc: 'Answered a question in under 5 seconds correctly', color: 'emerald' },
  high_confidence: { label: 'Confident Learner', icon: '💪', desc: 'Reported max confidence 10 times', color: 'green' },
}

const colorMap = {
  blue: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/30', glow: 'shadow-blue-500/20' },
  indigo: { bg: 'bg-indigo-500/10', text: 'text-indigo-400', border: 'border-indigo-500/30', glow: 'shadow-indigo-500/20' },
  emerald: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/30', glow: 'shadow-emerald-500/20' },
  amber: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/30', glow: 'shadow-amber-500/20' },
  purple: { bg: 'bg-purple-500/10', text: 'text-purple-400', border: 'border-purple-500/30', glow: 'shadow-purple-500/20' },
  yellow: { bg: 'bg-yellow-500/10', text: 'text-yellow-400', border: 'border-yellow-500/30', glow: 'shadow-yellow-500/20' },
  teal: { bg: 'bg-teal-500/10', text: 'text-teal-400', border: 'border-teal-500/30', glow: 'shadow-teal-500/20' },
  green: { bg: 'bg-green-500/10', text: 'text-green-400', border: 'border-green-500/30', glow: 'shadow-green-500/20' },
}

export default function Achievements() {
  const { user } = useUser()
  const { getToken } = useAuth()
  const [gamification, setGamification] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const load = async () => {
      if (!user) return
      try {
        const token = await getToken()
        const res = await fetch(`${API}/api/gamification`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        if (res.ok) setGamification(await res.json())
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [user])

  if (loading) return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
    </div>
  )
  if (error) return (
    <div className="flex items-center justify-center min-h-[60vh] gap-2 text-red-400">
      <AlertCircle size={18} /> <span className="text-sm">{error}</span>
    </div>
  )

  const earned = gamification?.achievements || []
  const xp = gamification?.xp || 0
  const level = gamification?.level || 1
  const levelName = gamification?.level_name || 'Beginner'

  const allAchievementKeys = Object.keys(ACHIEVEMENT_METADATA)
  const earnedSet = new Set(earned)
  const earnedList = allAchievementKeys.filter(k => earnedSet.has(k))
  const lockedList = allAchievementKeys.filter(k => !earnedSet.has(k))

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      <div className="flex flex-col space-y-1">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Achievements & Badges</h1>
        <p className="text-slate-400 text-sm">Review your earned skill merits, study streaks, and learning milestones.</p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-3 gap-4">
        <div className="border border-purple-500/20 bg-purple-500/5 rounded-xl p-4 text-center">
          <p className="text-3xl font-extrabold text-purple-400">{earnedList.length}</p>
          <p className="text-xs text-slate-400 mt-1">Earned</p>
        </div>
        <div className="border border-indigo-500/20 bg-indigo-500/5 rounded-xl p-4 text-center">
          <p className="text-3xl font-extrabold text-indigo-400">{xp.toLocaleString()}</p>
          <p className="text-xs text-slate-400 mt-1">Total XP</p>
        </div>
        <div className="border border-yellow-500/20 bg-yellow-500/5 rounded-xl p-4 text-center">
          <p className="text-3xl font-extrabold text-yellow-400">{level}</p>
          <p className="text-xs text-slate-400 mt-1">{levelName}</p>
        </div>
      </div>

      {/* Earned Achievements */}
      {earnedList.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Trophy size={15} className="text-yellow-400" /> Earned Achievements ({earnedList.length})
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {earnedList.map(key => {
              const meta = ACHIEVEMENT_METADATA[key] || { label: key, icon: '🏅', desc: '', color: 'indigo' }
              const c = colorMap[meta.color] || colorMap.indigo
              return (
                <div key={key} className={`border ${c.border} ${c.bg} rounded-xl p-4 text-center space-y-2 shadow-lg ${c.glow} hover:scale-[1.02] transition-transform duration-200`}>
                  <div className="text-3xl">{meta.icon}</div>
                  <p className={`text-sm font-bold ${c.text}`}>{meta.label}</p>
                  <p className="text-xs text-slate-500 leading-snug">{meta.desc}</p>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Locked Achievements */}
      {lockedList.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-bold text-slate-500 flex items-center gap-2">
            <Lock size={15} /> Locked Achievements ({lockedList.length})
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {lockedList.map(key => {
              const meta = ACHIEVEMENT_METADATA[key] || { label: key, icon: '?', desc: '' }
              return (
                <div key={key} className="border border-slate-800 bg-slate-900/30 rounded-xl p-4 text-center space-y-2 opacity-40 grayscale">
                  <div className="text-3xl filter blur-sm">{meta.icon}</div>
                  <p className="text-sm font-bold text-slate-400">{meta.label}</p>
                  <p className="text-xs text-slate-600 leading-snug">{meta.desc}</p>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Empty state */}
      {earnedList.length === 0 && !loading && (
        <div className="border border-slate-800 bg-slate-900/30 rounded-2xl p-16 flex flex-col items-center justify-center space-y-4 text-center">
          <div className="p-4 bg-purple-500/10 text-purple-400 rounded-full border border-purple-500/20">
            <Trophy className="h-10 w-10" />
          </div>
          <div className="space-y-1 max-w-sm">
            <h3 className="font-bold text-lg text-white">No achievements yet</h3>
            <p className="text-slate-400 text-sm">
              Upload study material and complete your first quiz to earn XP and unlock badges.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
