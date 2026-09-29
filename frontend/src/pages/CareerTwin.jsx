import React, { useState, useEffect } from 'react'
import { useAuth } from '@clerk/react'
import {
  Briefcase,
  Target,
  Sparkles,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Layers,
  ArrowRight,
  ShieldAlert,
  HelpCircle,
  FileText,
  Plus,
  Compass,
  Code2,
  BookOpen,
  Award,
  ChevronRight,
  Loader2,
  Search
} from 'lucide-react'
import { API_BASE_URL } from '../config'

export default function CareerTwin() {
  const { getToken } = useAuth()

  const [goals, setGoals] = useState([])
  const [activeGoal, setActiveGoal] = useState(null)
  const [skills, setSkills] = useState([])
  const [readinessReport, setReadinessReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [analyzingJob, setAnalyzingJob] = useState(false)
  const [jobText, setJobText] = useState('')
  const [jobRoleHint, setJobRoleHint] = useState('')
  const [analyzedResult, setAnalyzedResult] = useState(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [activeTab, setActiveTab] = useState('overview') // overview, skills, gaps, evidence

  // Fetch all career goals
  const fetchGoals = async () => {
    try {
      setLoading(true)
      const token = await getToken()
      const res = await fetch(`${API_BASE_URL}/api/career/goals`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        const fetchedGoals = data.goals || []
        setGoals(fetchedGoals)
        if (fetchedGoals.length > 0) {
          setActiveGoal(fetchedGoals[0])
        } else {
          setLoading(false)
        }
      } else {
        setLoading(false)
      }
    } catch (e) {
      console.error('Error fetching career goals:', e)
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchGoals()
  }, [])

  // When active goal changes, fetch skills and readiness report
  useEffect(() => {
    if (!activeGoal) return

    const fetchGoalDetails = async () => {
      try {
        const token = await getToken()
        const goalId = activeGoal._id || activeGoal.id

        // Fetch skills
        const skillsRes = await fetch(`${API_BASE_URL}/api/career/goals/${goalId}/skills`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        if (skillsRes.ok) {
          const sData = await skillsRes.json()
          setSkills(sData.skills || [])
        }

        // Fetch readiness
        const readRes = await fetch(`${API_BASE_URL}/api/career/goals/${goalId}/readiness`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        if (readRes.ok) {
          const rData = await readRes.json()
          setReadinessReport(rData)
        }
      } catch (e) {
        console.error('Error fetching goal details:', e)
      } finally {
        setLoading(false)
      }
    }

    fetchGoalDetails()
  }, [activeGoal])

  // Handle job description analysis
  const handleAnalyzeJob = async (e) => {
    e.preventDefault()
    if (!jobText.trim()) return

    try {
      setAnalyzingJob(true)
      const token = await getToken()
      const res = await fetch(`${API_BASE_URL}/api/career/analyze-job`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          job_description: jobText,
          role_hint: jobRoleHint
        })
      })
      if (res.ok) {
        const data = await res.json()
        setAnalyzedResult(data)
      }
    } catch (e) {
      console.error('Failed to analyze job:', e)
    } finally {
      setAnalyzingJob(false)
    }
  }

  // Create Goal from Analyzed Result
  const handleCreateGoalFromAnalysis = async () => {
    if (!analyzedResult) return
    try {
      setLoading(true)
      const token = await getToken()
      const res = await fetch(`${API_BASE_URL}/api/career/goals`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          role: analyzedResult.role_title,
          experience_level: analyzedResult.target_level,
          job_description_raw: jobText,
          extracted_skills: analyzedResult.extracted_skill_nodes
        })
      })
      if (res.ok) {
        setShowCreateModal(false)
        setJobText('')
        setAnalyzedResult(null)
        await fetchGoals()
      }
    } catch (e) {
      console.error('Failed to create goal:', e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800/80 p-6 md:p-8 rounded-3xl relative overflow-hidden shadow-2xl">
        <div className="space-y-2 relative z-10">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold">
            <Sparkles size={14} />
            <span>MK-Path 2.0 Digital Career Twin</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
            Autonomous Career Twin & Readiness Engine
          </h1>
          <p className="text-slate-400 text-sm max-w-2xl leading-relaxed">
            Multi-dimensional simulation comparing your verifiable knowledge, practical project artifacts, and interview confidence directly against live job market expectations.
          </p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="relative z-10 flex items-center justify-center space-x-2 px-5 py-3 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold shadow-lg shadow-indigo-600/25 transition cursor-pointer"
        >
          <Plus size={16} />
          <span>New Target Career</span>
        </button>
      </div>

      {/* Target Role Selector Tabs */}
      {goals.length > 0 && (
        <div className="flex items-center space-x-3 overflow-x-auto pb-2 border-b border-slate-800">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider pl-1">Target Goals:</span>
          {goals.map((g) => {
            const gId = String(g._id || g.id || '')
            const activeId = String(activeGoal?._id || activeGoal?.id || '')
            const isSel = activeGoal && (gId === activeId || g.title === activeGoal.title || g.role === activeGoal.role)
            return (
              <button
                key={gId || g.title}
                onClick={() => setActiveGoal(g)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-bold transition whitespace-nowrap cursor-pointer ${
                  isSel
                    ? 'bg-indigo-600/20 border border-indigo-500/40 text-indigo-300'
                    : 'bg-slate-900/60 border border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                <Briefcase size={14} />
                <span>{g.role || g.title}</span>
              </button>
            )
          })}
        </div>
      )}

      {/* Main Twin Content */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-24 space-y-3">
          <Loader2 size={32} className="animate-spin text-indigo-500" />
          <p className="text-xs text-slate-400 font-medium">Synthesizing Career Twin evidence matrix...</p>
        </div>
      ) : !activeGoal ? (
        <div className="p-12 text-center bg-slate-900/40 border border-slate-800/80 rounded-3xl space-y-4">
          <Target size={48} className="mx-auto text-indigo-400 opacity-60" />
          <h3 className="text-lg font-bold text-white">No Career Twin Configured</h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto">
            Upload a job description or enter your target role to build an explainable career readiness graph.
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition"
          >
            Create Career Goal
          </button>
        </div>
      ) : (
        <div className="space-y-8">
          {/* Readiness Dashboard KPI Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Overall Readiness */}
            <div className="bg-slate-900/60 border border-slate-800 p-5 rounded-2xl space-y-2 relative overflow-hidden">
              <div className="flex justify-between items-center text-xs text-slate-400 font-medium">
                <span>Overall Readiness</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  (readinessReport?.overall_readiness_score || 0) >= 80 ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                  (readinessReport?.overall_readiness_score || 0) >= 50 ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20' :
                  'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                }`}>
                  {readinessReport?.status || 'IN_PROGRESS'}
                </span>
              </div>
              <div className="text-3xl font-extrabold text-white">
                {readinessReport?.overall_readiness_score ?? 0}%
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-indigo-500 h-full rounded-full transition-all duration-500"
                  style={{ width: `${readinessReport?.overall_readiness_score || 0}%` }}
                />
              </div>
            </div>

            {/* Knowledge Score */}
            <div className="bg-slate-900/60 border border-slate-800 p-5 rounded-2xl space-y-2">
              <div className="flex justify-between items-center text-xs text-slate-400 font-medium">
                <span>Knowledge Mastery</span>
                <BookOpen size={14} className="text-indigo-400" />
              </div>
              <div className="text-2xl font-bold text-white">
                {readinessReport?.knowledge_readiness_score ?? 0}%
              </div>
              <p className="text-[11px] text-slate-500">Verified via quizzes & BKT</p>
            </div>

            {/* Practical / Project Evidence */}
            <div className="bg-slate-900/60 border border-slate-800 p-5 rounded-2xl space-y-2">
              <div className="flex justify-between items-center text-xs text-slate-400 font-medium">
                <span>Practical Evidence</span>
                <Code2 size={14} className="text-purple-400" />
              </div>
              <div className="text-2xl font-bold text-white">
                {readinessReport?.practical_readiness_score ?? 0}%
              </div>
              <p className="text-[11px] text-slate-500">
                {(readinessReport?.evidence_deficits_count || 0) > 0 ? (
                  <span className="text-amber-400 font-semibold">{readinessReport.evidence_deficits_count} Evidence Deficits</span>
                ) : (
                  'Verified code & assignments'
                )}
              </p>
            </div>

            {/* Interview Simulation */}
            <div className="bg-slate-900/60 border border-slate-800 p-5 rounded-2xl space-y-2">
              <div className="flex justify-between items-center text-xs text-slate-400 font-medium">
                <span>Interview Readiness</span>
                <Award size={14} className="text-sky-400" />
              </div>
              <div className="text-2xl font-bold text-white">
                {readinessReport?.interview_readiness_score ?? 0}%
              </div>
              <p className="text-[11px] text-slate-500">Technical role Q&A</p>
            </div>
          </div>

          {/* Recommended Next Action Banner */}
          {readinessReport?.recommended_next_action && (
            <div className="p-5 rounded-2xl bg-gradient-to-r from-indigo-950/40 via-purple-950/20 to-slate-900 border border-indigo-500/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center space-x-2 text-xs font-bold text-indigo-400 uppercase tracking-wider">
                  <Sparkles size={12} />
                  <span>High-Impact Recommended Next Step</span>
                </div>
                <h4 className="text-sm font-bold text-white">
                  {readinessReport.recommended_next_action.title}
                </h4>
                <p className="text-xs text-slate-400">
                  {readinessReport.recommended_next_action.description}
                </p>
              </div>
              <div className="flex-shrink-0">
                <span className="px-3 py-1.5 rounded-lg bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 text-xs font-bold">
                  {readinessReport.recommended_next_action.type}
                </span>
              </div>
            </div>
          )}

          {/* Sub-Navigation Tabs */}
          <div className="flex items-center space-x-2 border-b border-slate-800">
            {[
              { id: 'overview', label: 'Career Skill Graph' },
              { id: 'gaps', label: `Skill & Prerequisite Gaps (${readinessReport?.knowledge_gaps_count || 0})` },
              { id: 'evidence', label: 'Evidence & Deficit Matrix' },
              { id: 'explain', label: 'Explainable Readiness Breakdown' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2.5 text-xs font-bold transition border-b-2 cursor-pointer ${
                  activeTab === tab.id
                    ? 'border-indigo-500 text-indigo-400'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* TAB 1: Career Skill Graph */}
          {activeTab === 'overview' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {skills.map((s, idx) => (
                <div
                  key={idx}
                  className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-3 hover:border-slate-700 transition"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                        {s.category}
                      </span>
                      <h4 className="text-sm font-bold text-white">{s.skill_name}</h4>
                    </div>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                      s.status === 'MASTERED' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                      s.status === 'EVIDENCE_DEFICIT' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                      s.status === 'BLOCKED_BY_PREREQUISITE' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                      'bg-slate-800 text-slate-400 border-slate-700'
                    }`}>
                      {s.status.replace(/_/g, ' ')}
                    </span>
                  </div>

                  {/* Multi-Dimensional Progress Bars */}
                  <div className="space-y-1.5 text-xs">
                    <div className="flex justify-between text-slate-400 text-[11px]">
                      <span>Knowledge ({s.knowledge_score}%)</span>
                      <span>Practical ({s.practical_evidence_score}%)</span>
                    </div>
                    <div className="grid grid-cols-2 gap-1.5">
                      <div className="w-full bg-slate-800 h-1 rounded-full overflow-hidden">
                        <div className="bg-indigo-500 h-full rounded-full" style={{ width: `${s.knowledge_score}%` }} />
                      </div>
                      <div className="w-full bg-slate-800 h-1 rounded-full overflow-hidden">
                        <div className="bg-purple-500 h-full rounded-full" style={{ width: `${s.practical_evidence_score}%` }} />
                      </div>
                    </div>
                  </div>

                  {s.has_evidence_deficit && (
                    <div className="flex items-center space-x-1.5 text-[11px] text-amber-400 bg-amber-500/10 p-2 rounded-lg border border-amber-500/20">
                      <AlertTriangle size={12} className="flex-shrink-0" />
                      <span>Evidence Deficit: Quiz mastery verified, practical project missing.</span>
                    </div>
                  )}

                  {s.unmet_prerequisites && s.unmet_prerequisites.length > 0 && (
                    <div className="text-[11px] text-red-400 bg-red-500/10 p-2 rounded-lg border border-red-500/20">
                      <span className="font-semibold">Blocked by:</span> {s.unmet_prerequisites.join(', ')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* TAB 2: Gaps */}
          {activeTab === 'gaps' && (
            <div className="space-y-4">
              {skills.filter(s => s.gap > 0 || s.has_evidence_deficit || s.prerequisite_status === 'BLOCKED').map((s, idx) => (
                <div key={idx} className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="text-sm font-bold text-white">{s.skill_name}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                        Importance: {s.career_importance}x
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">
                      Target: {s.required_level}% | Current: {s.current_mastery}% | Gap: <span className="text-amber-400 font-bold">{s.gap}%</span>
                    </p>
                  </div>
                  <span className="text-xs font-bold text-indigo-400">
                    {s.prerequisite_status === 'BLOCKED' ? 'Prereq Blocker' : s.has_evidence_deficit ? 'Evidence Deficit' : 'Knowledge Gap'}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* TAB 3: Evidence Matrix */}
          {activeTab === 'evidence' && (
            <div className="bg-slate-900/40 border border-slate-800 rounded-2xl overflow-hidden">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950/60 text-slate-400 uppercase font-semibold border-b border-slate-800 text-[10px]">
                  <tr>
                    <th className="p-4">Target Competency</th>
                    <th className="p-4">Knowledge Evidence</th>
                    <th className="p-4">Practical Evidence</th>
                    <th className="p-4">Evidence Quality</th>
                    <th className="p-4">Deficit Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {skills.map((s, idx) => (
                    <tr key={idx} className="hover:bg-slate-800/30 transition">
                      <td className="p-4 font-bold text-white">{s.skill_name}</td>
                      <td className="p-4 text-indigo-300 font-mono">{s.knowledge_score}%</td>
                      <td className="p-4 text-purple-300 font-mono">{s.practical_evidence_score}%</td>
                      <td className="p-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          s.evidence_quality === 'HIGH' ? 'bg-emerald-500/10 text-emerald-400' :
                          s.evidence_quality === 'MODERATE' ? 'bg-indigo-500/10 text-indigo-400' :
                          'bg-slate-800 text-slate-400'
                        }`}>
                          {s.evidence_quality}
                        </span>
                      </td>
                      <td className="p-4">
                        {s.has_evidence_deficit ? (
                          <span className="text-amber-400 font-bold">Deficit (Quiz only)</span>
                        ) : (
                          <span className="text-emerald-400">Balanced</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* TAB 4: Explainable Breakdown */}
          {activeTab === 'explain' && readinessReport && (
            <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 space-y-4">
              <h3 className="text-sm font-bold text-white">Explainable Readiness Analysis</h3>
              <ul className="space-y-2">
                {readinessReport.explainable_breakdown.map((item, idx) => (
                  <li key={idx} className="flex items-start space-x-2 text-xs text-slate-300">
                    <CheckCircle2 size={14} className="text-indigo-400 flex-shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Modal: Create Career Goal from Job Description */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-2xl w-full p-6 space-y-5 shadow-2xl animate-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white">Configure Career Twin Target</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-white text-xs font-bold"
              >
                Close
              </button>
            </div>

            {!analyzedResult ? (
              <form onSubmit={handleAnalyzeJob} className="space-y-4">
                <div>
                  <label className="text-xs font-semibold text-slate-400 block mb-1">
                    Role Title / Target Role (Optional Hint)
                  </label>
                  <input
                    type="text"
                    value={jobRoleHint}
                    onChange={(e) => setJobRoleHint(e.target.value)}
                    placeholder="e.g. Senior Machine Learning Engineer"
                    className="w-full px-4 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-xs text-slate-200 outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-400 block mb-1">
                    Paste Job Description Text
                  </label>
                  <textarea
                    rows={6}
                    value={jobText}
                    onChange={(e) => setJobText(e.target.value)}
                    placeholder="Paste job posting text (requirements, responsibilities, tech stack)..."
                    className="w-full p-4 bg-slate-950/60 border border-slate-800 rounded-xl text-xs text-slate-200 outline-none focus:border-indigo-500 leading-relaxed font-mono"
                  />
                </div>

                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={analyzingJob || !jobText.trim()}
                    className="flex items-center space-x-2 px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold disabled:opacity-50"
                  >
                    {analyzingJob && <Loader2 size={12} className="animate-spin" />}
                    <span>Analyze Job Description</span>
                  </button>
                </div>
              </form>
            ) : (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                  <div className="flex justify-between">
                    <span className="text-xs font-bold text-indigo-400">{analyzedResult.role_title}</span>
                    <span className="text-[10px] text-slate-500 uppercase font-bold">{analyzedResult.target_level}</span>
                  </div>
                  <div className="text-xs text-slate-300">
                    <span className="font-semibold text-slate-400">Extracted Skills:</span> {analyzedResult.technical_skills.join(', ')}
                  </div>
                  <div className="text-xs text-slate-300">
                    <span className="font-semibold text-slate-400">Frameworks:</span> {analyzedResult.tools_and_frameworks.join(', ')}
                  </div>
                </div>

                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setAnalyzedResult(null)}
                    className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white"
                  >
                    Re-analyze
                  </button>
                  <button
                    type="button"
                    onClick={handleCreateGoalFromAnalysis}
                    className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold"
                  >
                    Activate Career Twin
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
