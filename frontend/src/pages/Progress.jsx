import React, { useState, useEffect } from 'react'
import { useUser, useAuth } from '@clerk/react'
import {
  Award, Zap, TrendingUp, Target, BookOpen, CheckCircle2,
  Loader2, AlertCircle, Flame, Calendar, BarChart2, Brain
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function Progress() {
  const { user } = useUser()
  const { getToken } = useAuth()
  const [data, setData] = useState(null)
  const [mastery, setMastery] = useState([])
  const [gamification, setGamification] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const load = async () => {
      if (!user) return
      try {
        const token = await getToken()
        const headers = { Authorization: `Bearer ${token}` }
        const [statsRes, masteryRes, gamRes] = await Promise.all([
          fetch(`${API}/api/dashboard/stats`, { headers }),
          fetch(`${API}/api/mastery`, { headers }),
          fetch(`${API}/api/gamification`, { headers }),
        ])
        if (statsRes.ok) setData(await statsRes.json())
        if (masteryRes.ok) setMastery(await masteryRes.json())
        if (gamRes.ok) setGamification(await gamRes.json())
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

  const xp = gamification?.xp ?? 0
  const level = gamification?.level ?? 1
  const levelName = gamification?.level_name ?? 'Beginner'
  const xpForNext = level * 200
  const xpProgress = Math.min((xp % (level * 200)) / (level * 200) * 100, 100)

  const masteryArray = Array.isArray(mastery) ? mastery : []
  const masteredCount = masteryArray.filter(m => m.category === 'Mastered').length
  const proficientCount = masteryArray.filter(m => m.category === 'Proficient').length
  const learningCount = masteryArray.filter(m => m.category === 'Learning').length
  const weakCount = masteryArray.filter(m => m.category === 'Weak').length

  const topConcepts = [...masteryArray].sort((a, b) => b.mastery_score - a.mastery_score).slice(0, 5)
  const weakConcepts = [...masteryArray].sort((a, b) => a.mastery_score - b.mastery_score).slice(0, 5)

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      <div className="flex flex-col space-y-1">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Learning Progress</h1>
        <p className="text-slate-400 text-sm">Track your mastery, XP, and learning trajectory.</p>
      </div>

      {/* XP & Level */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          icon={<Zap className="h-5 w-5" />}
          label="Total XP"
          value={xp.toLocaleString()}
          color="indigo"
        />
        <StatCard
          icon={<TrendingUp className="h-5 w-5" />}
          label="Level"
          value={`${level} — ${levelName}`}
          color="purple"
        />
        <StatCard
          icon={<Brain className="h-5 w-5" />}
          label="Concepts Tracked"
          value={masteryArray.length}
          color="emerald"
        />
      </div>

      {/* Level Progress Bar */}
      <div className="border border-slate-800 bg-slate-900/40 rounded-2xl p-6 space-y-3">
        <div className="flex items-center justify-between text-sm">
          <span className="font-bold text-white">Level {level} · {levelName}</span>
          <span className="text-slate-400 text-xs">{xp % (level * 200)} / {xpForNext} XP to next level</span>
        </div>
        <div className="h-3 bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-indigo-600 to-purple-500 rounded-full transition-all duration-700"
            style={{ width: `${xpProgress}%` }}
          />
        </div>
        <p className="text-xs text-slate-500">Keep answering questions and completing assignments to earn XP.</p>
      </div>

      {/* Mastery Breakdown */}
      {masteryArray.length > 0 && (
        <div className="border border-slate-800 bg-slate-900/40 rounded-2xl p-6 space-y-5">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <BarChart2 size={16} className="text-indigo-400" /> Concept Mastery Breakdown
          </h2>
          {/* Category Bars */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <MasteryBar label="Mastered" count={masteredCount} total={masteryArray.length} color="emerald" />
            <MasteryBar label="Proficient" count={proficientCount} total={masteryArray.length} color="indigo" />
            <MasteryBar label="Learning" count={learningCount} total={masteryArray.length} color="amber" />
            <MasteryBar label="Weak" count={weakCount} total={masteryArray.length} color="red" />
          </div>

          {/* Top Concepts */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-2">
            <div className="space-y-2">
              <p className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Strongest Concepts</p>
              {topConcepts.map(c => (
                <ConceptBar key={c.concept_id || c.concept_name} concept={c} />
              ))}
            </div>
            <div className="space-y-2">
              <p className="text-xs font-semibold text-red-400 uppercase tracking-wider">Needs Work</p>
              {weakConcepts.map(c => (
                <ConceptBar key={c.concept_id || c.concept_name} concept={c} />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Stats from dashboard */}
      {data && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <StatCard icon={<BookOpen className="h-5 w-5" />} label="Materials" value={data.material_count ?? 0} color="blue" />
          <StatCard icon={<Brain className="h-5 w-5" />} label="Concepts" value={data.concept_count ?? 0} color="purple" />
          <StatCard icon={<Target className="h-5 w-5" />} label="Questions" value={data.question_count ?? 0} color="amber" />
          <StatCard icon={<CheckCircle2 className="h-5 w-5" />} label="Attempts" value={data.attempt_count ?? 0} color="emerald" />
        </div>
      )}

      {/* Empty state */}
      {masteryArray.length === 0 && !loading && (
        <div className="border border-slate-800 bg-slate-900/30 rounded-2xl p-16 flex flex-col items-center justify-center space-y-4 text-center">
          <div className="p-4 bg-yellow-500/10 text-yellow-400 rounded-full border border-yellow-500/20">
            <Award className="h-8 w-8" />
          </div>
          <div className="space-y-2 max-w-sm">
            <h3 className="font-bold text-white text-base">No progress data yet</h3>
            <p className="text-slate-400 text-xs leading-relaxed">
              Upload study material and complete your first quiz to start tracking XP, mastery, and learning milestones.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

/* ── Helpers ──────────────────────────────────────── */
const colorMap = {
  indigo: { bg: 'bg-indigo-500/10', text: 'text-indigo-400', bar: 'bg-indigo-500', border: 'border-indigo-500/20' },
  purple: { bg: 'bg-purple-500/10', text: 'text-purple-400', bar: 'bg-purple-500', border: 'border-purple-500/20' },
  emerald: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', bar: 'bg-emerald-500', border: 'border-emerald-500/20' },
  amber: { bg: 'bg-amber-500/10', text: 'text-amber-400', bar: 'bg-amber-500', border: 'border-amber-500/20' },
  blue: { bg: 'bg-blue-500/10', text: 'text-blue-400', bar: 'bg-blue-500', border: 'border-blue-500/20' },
  red: { bg: 'bg-red-500/10', text: 'text-red-400', bar: 'bg-red-500', border: 'border-red-500/20' },
}

function StatCard({ icon, label, value, color }) {
  const c = colorMap[color] || colorMap.indigo
  return (
    <div className={`border ${c.border} ${c.bg} rounded-xl p-4 flex items-center gap-3`}>
      <div className={`p-2 ${c.bg} rounded-lg ${c.text}`}>{icon}</div>
      <div>
        <p className="text-xs text-slate-500">{label}</p>
        <p className={`text-lg font-extrabold ${c.text}`}>{value}</p>
      </div>
    </div>
  )
}

function MasteryBar({ label, count, total, color }) {
  const pct = total > 0 ? Math.round(count / total * 100) : 0
  const c = colorMap[color] || colorMap.indigo
  return (
    <div className={`border ${c.border} ${c.bg} rounded-xl p-4 space-y-2`}>
      <div className="flex items-center justify-between">
        <span className={`text-xs font-semibold ${c.text}`}>{label}</span>
        <span className="text-sm font-bold text-white">{count}</span>
      </div>
      <div className="h-1.5 bg-slate-800 rounded-full">
        <div className={`h-full ${c.bar} rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-slate-500">{pct}% of concepts</p>
    </div>
  )
}

function ConceptBar({ concept }) {
  const score = Math.round(concept.mastery_score || 0)
  const cat = concept.category || 'Weak'
  const colorKey = cat === 'Mastered' ? 'emerald' : cat === 'Proficient' ? 'indigo' : cat === 'Learning' ? 'amber' : 'red'
  const c = colorMap[colorKey]
  return (
    <div className="flex items-center gap-3 py-1.5">
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-white truncate">{concept.concept_name || concept.name}</p>
        <div className="h-1 bg-slate-800 rounded-full mt-1">
          <div className={`h-full ${c.bar} rounded-full transition-all duration-500`} style={{ width: `${score}%` }} />
        </div>
      </div>
      <span className={`text-xs font-bold ${c.text} flex-shrink-0 w-8 text-right`}>{score}%</span>
    </div>
  )
}
