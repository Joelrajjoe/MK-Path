import React, { useState, useEffect, useRef } from 'react'
import { useUser, useAuth } from '@clerk/react'
import { useNavigate } from 'react-router-dom'
import {
  ClipboardList, Plus, Loader2, AlertCircle, CheckCircle2,
  Clock, BookOpen, Target, Trash2, Play, ChevronRight,
  X, ChevronLeft, Award, RotateCcw, Save
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const STATUS_CONFIG = {
  pending: { label: 'Pending', cls: 'bg-slate-700 text-slate-300' },
  in_progress: { label: 'In Progress', cls: 'bg-blue-700/40 text-blue-300 border border-blue-500/30' },
  completed: { label: 'Completed', cls: 'bg-emerald-700/40 text-emerald-300 border border-emerald-500/30' },
  overdue: { label: 'Overdue', cls: 'bg-red-700/40 text-red-300 border border-red-500/30' },
}

export default function Assignments() {
  const { user } = useUser()
  const { getToken } = useAuth()
  const [assignments, setAssignments] = useState([])
  const [concepts, setConcepts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [activeAssignment, setActiveAssignment] = useState(null) // assignment being taken
  const [toast, setToast] = useState(null)

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }


  const load = async () => {
    if (!user) return
    try {
      const token = await getToken()
      const headers = { Authorization: `Bearer ${token}` }
      const [aRes, cRes] = await Promise.all([
        fetch(`${API}/api/assignments`, { headers }),
        fetch(`${API}/api/concepts`, { headers }),
      ])
      if (aRes.ok) {
        const d = await aRes.json()
        setAssignments(d.assignments || [])
      }
      if (cRes.ok) setConcepts(await cRes.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [user])

  const handleDelete = async (id) => {
    const token = await getToken()
    const res = await fetch(`${API}/api/assignments/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    })
    if (res.ok) {
      setAssignments(a => a.filter(x => x._id !== id))
      showToast('Assignment deleted')
    } else {
      showToast('Delete failed', 'error')
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
    </div>
  )

  if (activeAssignment) return (
    <AssignmentRunner
      assignment={activeAssignment}
      getToken={getToken}
      onClose={() => { setActiveAssignment(null); load() }}
      showToast={showToast}
    />
  )

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-6 right-6 z-50 flex items-center gap-2 px-5 py-3 rounded-xl shadow-2xl text-sm font-semibold border animate-in slide-in-from-right duration-300 ${
          toast.type === 'error'
            ? 'bg-red-950 border-red-500/40 text-red-300'
            : 'bg-emerald-950 border-emerald-500/40 text-emerald-300'
        }`}>
          {toast.type === 'error' ? <AlertCircle size={16} /> : <CheckCircle2 size={16} />}
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Assignments</h1>
          <p className="text-slate-400 text-sm mt-1">Create and manage your learning assignments.</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold px-4 py-2.5 rounded-xl transition shadow-lg shadow-indigo-900/30"
        >
          <Plus size={15} /> New Assignment
        </button>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <CreateAssignmentModal
          concepts={concepts}
          getToken={getToken}
          onClose={() => setShowCreate(false)}
          onCreated={(a) => { setAssignments(prev => [a, ...prev]); setShowCreate(false); showToast('Assignment created!') }}
          showToast={showToast}
        />
      )}

      {error && (
        <div className="flex items-center gap-2 text-red-400 text-sm bg-red-950/30 border border-red-500/20 rounded-xl p-4">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {/* Assignment List */}
      {assignments.length === 0 ? (
        <div className="border border-slate-800 bg-slate-900/30 rounded-2xl p-16 flex flex-col items-center justify-center space-y-4 text-center min-h-[350px]">
          <div className="p-4 bg-indigo-500/10 text-indigo-400 rounded-full border border-indigo-500/20">
            <ClipboardList className="h-10 w-10" />
          </div>
          <div className="space-y-1 max-w-sm">
            <h3 className="font-bold text-lg text-white">No Assignments Yet</h3>
            <p className="text-slate-400 text-sm">
              Create an assignment to test your knowledge on specific concepts. Upload materials first to unlock AI question generation.
            </p>
          </div>
          <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold px-5 py-2.5 rounded-xl transition">
            <Plus size={15} /> Create Assignment
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {assignments.map(a => {
            const statusCfg = STATUS_CONFIG[a.status] || STATUS_CONFIG.pending
            const qCount = a.questions?.length || 0
            return (
              <div key={a._id} className="border border-slate-800 bg-slate-900/40 rounded-xl p-5 flex items-center gap-4 hover:border-slate-700 transition group">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-bold text-white text-sm truncate">{a.title}</h3>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${statusCfg.cls}`}>
                      {statusCfg.label}
                    </span>
                  </div>
                  {a.description && <p className="text-xs text-slate-500 mt-1 truncate">{a.description}</p>}
                  <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                    <span className="flex items-center gap-1"><Target size={11} /> {qCount} questions</span>
                    <span className="flex items-center gap-1"><Clock size={11} /> {a.estimated_duration_minutes} min</span>
                    {a.score !== null && a.score !== undefined && (
                      <span className="flex items-center gap-1 text-emerald-400"><Award size={11} /> {Math.round(a.score)}%</span>
                    )}
                    {a.concept_names?.length > 0 && (
                      <span className="flex items-center gap-1"><BookOpen size={11} /> {a.concept_names.slice(0, 2).join(', ')}{a.concept_names.length > 2 ? '…' : ''}</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {a.status !== 'completed' && qCount > 0 && (
                    <button
                      onClick={() => setActiveAssignment(a)}
                      className="flex items-center gap-1.5 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded-lg transition"
                    >
                      <Play size={12} /> {a.status === 'in_progress' ? 'Resume' : 'Start'}
                    </button>
                  )}
                  {a.status === 'completed' && (
                    <button
                      onClick={() => setActiveAssignment(a)}
                      className="flex items-center gap-1.5 text-xs font-semibold bg-slate-700 hover:bg-slate-600 text-slate-300 px-3 py-1.5 rounded-lg transition"
                    >
                      <ChevronRight size={12} /> Review
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(a._id)}
                    className="p-1.5 text-slate-600 hover:text-red-400 rounded-lg hover:bg-red-950/30 transition opacity-0 group-hover:opacity-100"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

/* ── Create Assignment Modal ──────────────────────── */
function CreateAssignmentModal({ concepts, getToken, onClose, onCreated, showToast }) {
  const [form, setForm] = useState({ title: '', description: '', difficulty: 'intermediate', estimated_duration_minutes: 20, concept_ids: [], concept_names: [], assignment_type: 'practice' })
  const [creating, setCreating] = useState(false)

  const toggleConcept = (c) => {
    setForm(f => {
      const ids = f.concept_ids.includes(c._id) ? f.concept_ids.filter(i => i !== c._id) : [...f.concept_ids, c._id]
      const names = f.concept_names.includes(c.name) ? f.concept_names.filter(n => n !== c.name) : [...f.concept_names, c.name]
      return { ...f, concept_ids: ids, concept_names: names }
    })
  }

  const handleCreate = async () => {
    if (!form.title.trim()) { showToast('Title is required', 'error'); return }
    setCreating(true)
    try {
      const token = await getToken()
      const res = await fetch(`${API}/api/assignments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(form)
      })
      if (!res.ok) throw new Error(await res.text())
      onCreated(await res.json())
    } catch (e) {
      showToast('Failed: ' + e.message, 'error')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-lg w-full mx-4 shadow-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-white text-lg">New Assignment</h2>
          <button onClick={onClose} className="p-1 text-slate-500 hover:text-white rounded-lg transition"><X size={18} /></button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs text-slate-400 font-semibold uppercase tracking-wide">Title *</label>
            <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              placeholder="e.g. Neural Network Foundations Quiz"
              className="w-full mt-1.5 px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white outline-none focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 font-semibold uppercase tracking-wide">Description</label>
            <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              rows={2} placeholder="Optional description..."
              className="w-full mt-1.5 px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white outline-none focus:border-indigo-500 resize-none"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-400 font-semibold uppercase tracking-wide">Difficulty</label>
              <select value={form.difficulty} onChange={e => setForm(f => ({ ...f, difficulty: e.target.value }))}
                className="w-full mt-1.5 px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white outline-none focus:border-indigo-500">
                <option value="basic">Basic</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400 font-semibold uppercase tracking-wide">Duration (min)</label>
              <input type="number" min="5" max="180" value={form.estimated_duration_minutes}
                onChange={e => setForm(f => ({ ...f, estimated_duration_minutes: parseInt(e.target.value) || 20 }))}
                className="w-full mt-1.5 px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white outline-none focus:border-indigo-500"
              />
            </div>
          </div>
          {concepts.length > 0 && (
            <div>
              <label className="text-xs text-slate-400 font-semibold uppercase tracking-wide">Concepts (select to auto-generate questions)</label>
              <div className="flex flex-wrap gap-2 mt-2 max-h-36 overflow-y-auto">
                {concepts.map(c => (
                  <button key={c._id} onClick={() => toggleConcept(c)}
                    className={`text-xs px-2.5 py-1 rounded-lg border transition ${
                      form.concept_ids.includes(c._id)
                        ? 'bg-indigo-600 border-indigo-500 text-white'
                        : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-white'
                    }`}
                  >{c.name}</button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex gap-3 mt-6">
          <button onClick={handleCreate} disabled={creating}
            className="flex-1 flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-semibold py-2.5 rounded-xl transition">
            {creating ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
            {creating ? 'Creating…' : 'Create Assignment'}
          </button>
          <button onClick={onClose} className="flex-1 text-slate-400 border border-slate-700 rounded-xl text-sm hover:text-white transition">
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

/* ── Assignment Runner (Quiz interface) ───────────── */
function AssignmentRunner({ assignment, getToken, onClose, showToast }) {
  const questions = assignment.questions || []
  const isReview = assignment.status === 'completed'
  const [currentIdx, setCurrentIdx] = useState(0)
  const [answers, setAnswers] = useState(
    isReview ? {} : Object.fromEntries(Object.entries(assignment.draft_answers || {}).map(([k, v]) => [parseInt(k), v]))
  )
  const [submitted, setSubmitted] = useState(isReview)
  const [results, setResults] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const startTime = useRef(Date.now())

  const handleAnswer = (qIdx, optIdx) => {
    if (submitted) return
    setAnswers(a => ({ ...a, [qIdx]: optIdx }))
  }

  const handleSaveDraft = async () => {
    const token = await getToken()
    await fetch(`${API}/api/assignments/${assignment._id}/save-progress`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ draft_answers: Object.fromEntries(Object.entries(answers).map(([k, v]) => [String(k), v])) })
    })
    showToast('Progress saved')
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    const timeSpent = (Date.now() - startTime.current) / 1000
    const answersPayload = Object.entries(answers).map(([qi, si]) => ({
      question_index: parseInt(qi),
      selected_option_index: si,
      confidence: 3,
      response_time_seconds: 10
    }))
    try {
      const token = await getToken()
      const res = await fetch(`${API}/api/assignments/${assignment._id}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ answers: answersPayload, time_spent_seconds: timeSpent })
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setResults(data)
      setSubmitted(true)
    } catch (e) {
      showToast('Submit failed: ' + e.message, 'error')
    } finally {
      setSubmitting(false)
    }
  }

  const q = questions[currentIdx]
  const answered = Object.keys(answers).length
  const canSubmit = answered === questions.length && !submitted

  if (!q && !isReview) return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="border border-slate-800 bg-slate-900/30 rounded-2xl p-12 text-center space-y-3">
        <AlertCircle className="h-10 w-10 text-amber-400 mx-auto" />
        <h3 className="font-bold text-white">No questions in this assignment</h3>
        <p className="text-slate-400 text-sm">No questions were generated. Delete and recreate with concepts selected.</p>
        <button onClick={onClose} className="mt-2 text-sm text-indigo-400 hover:text-indigo-300">← Back to Assignments</button>
      </div>
    </div>
  )

  // Results screen
  if (submitted && results) return (
    <div className="max-w-2xl mx-auto space-y-6">
      <button onClick={onClose} className="flex items-center gap-1 text-sm text-slate-400 hover:text-white transition"><ChevronLeft size={15} /> Back</button>
      <div className="border border-emerald-500/30 bg-emerald-950/10 rounded-2xl p-8 text-center space-y-4">
        <Award className="h-12 w-12 text-emerald-400 mx-auto" />
        <h2 className="text-2xl font-extrabold text-white">Assignment Complete!</h2>
        <p className="text-4xl font-extrabold text-emerald-400">{results.score}%</p>
        <p className="text-slate-400 text-sm">{results.correct} / {results.total} correct · {results.xp_earned} XP earned</p>
      </div>
      <div className="space-y-3">
        {questions.map((qItem, idx) => {
          const qr = results.per_question_results?.find(r => r.question_index === idx)
          const selected = answers[idx]
          return (
            <div key={idx} className={`border rounded-xl p-4 ${qr?.is_correct ? 'border-emerald-500/30 bg-emerald-950/10' : 'border-red-500/30 bg-red-950/10'}`}>
              <p className="text-sm font-semibold text-white mb-3">{idx + 1}. {qItem.question_text}</p>
              {(qItem.options || []).map((opt, oi) => (
                <div key={oi} className={`text-xs px-3 py-1.5 rounded-lg mb-1 ${
                  oi === qr?.correct_option_index ? 'bg-emerald-700/30 text-emerald-300' :
                  oi === selected && !qr?.is_correct ? 'bg-red-700/30 text-red-300' : 'text-slate-500'
                }`}>{opt}</div>
              ))}
              {qr?.explanation && <p className="text-xs text-slate-500 mt-2 italic">{qr.explanation}</p>}
            </div>
          )
        })}
      </div>
    </div>
  )

  // Review mode (already completed)
  if (isReview) return (
    <div className="max-w-2xl mx-auto space-y-4">
      <button onClick={onClose} className="flex items-center gap-1 text-sm text-slate-400 hover:text-white transition"><ChevronLeft size={15} /> Back</button>
      <div className="border border-slate-800 bg-slate-900/30 rounded-2xl p-6 text-center">
        <p className="text-2xl font-extrabold text-emerald-400">{Math.round(assignment.score || 0)}%</p>
        <p className="text-slate-400 text-sm mt-1">Final Score</p>
      </div>
      {questions.map((qItem, idx) => (
        <div key={idx} className="border border-slate-800 bg-slate-900/30 rounded-xl p-4">
          <p className="text-sm font-semibold text-white mb-3">{idx + 1}. {qItem.question_text}</p>
          {(qItem.options || []).map((opt, oi) => (
            <div key={oi} className={`text-xs px-3 py-1.5 rounded-lg mb-1 ${oi === qItem.correct_option_index ? 'bg-emerald-700/30 text-emerald-300' : 'text-slate-500'}`}>{opt}</div>
          ))}
        </div>
      ))}
    </div>
  )

  // Quiz mode
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <button onClick={onClose} className="flex items-center gap-1 text-sm text-slate-400 hover:text-white transition"><ChevronLeft size={15} /> Exit</button>
        <div className="text-xs text-slate-500">{answered}/{questions.length} answered</div>
        <button onClick={handleSaveDraft} className="flex items-center gap-1 text-xs text-slate-400 hover:text-white transition"><Save size={12} /> Save Draft</button>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-slate-800 rounded-full">
        <div className="h-full bg-indigo-500 rounded-full transition-all duration-300" style={{ width: `${(currentIdx / questions.length) * 100}%` }} />
      </div>

      {/* Question */}
      <div className="border border-slate-800 bg-slate-900/40 rounded-2xl p-6 space-y-4">
        <p className="text-xs text-slate-500">Question {currentIdx + 1} of {questions.length}</p>
        <p className="text-base font-semibold text-white">{q.question_text}</p>
        <div className="space-y-2">
          {(q.options || []).map((opt, oi) => (
            <button
              key={oi}
              onClick={() => handleAnswer(currentIdx, oi)}
              className={`w-full text-left text-sm px-4 py-3 rounded-xl border transition ${
                answers[currentIdx] === oi
                  ? 'bg-indigo-600/30 border-indigo-500 text-white'
                  : 'bg-slate-800/40 border-slate-700 text-slate-300 hover:border-indigo-500/50 hover:bg-slate-800'
              }`}
            >
              <span className="font-bold text-indigo-400 mr-2">{String.fromCharCode(65 + oi)}.</span> {opt}
            </button>
          ))}
        </div>
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setCurrentIdx(i => Math.max(0, i - 1))}
          disabled={currentIdx === 0}
          className="flex items-center gap-1.5 text-sm text-slate-400 disabled:opacity-30 hover:text-white transition"
        >
          <ChevronLeft size={15} /> Previous
        </button>
        <div className="flex gap-1.5">
          {questions.map((_, i) => (
            <button key={i} onClick={() => setCurrentIdx(i)}
              className={`w-2.5 h-2.5 rounded-full transition ${i === currentIdx ? 'bg-indigo-500' : answers[i] !== undefined ? 'bg-emerald-600' : 'bg-slate-700'}`}
            />
          ))}
        </div>
        {currentIdx < questions.length - 1 ? (
          <button
            onClick={() => setCurrentIdx(i => Math.min(questions.length - 1, i + 1))}
            className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition"
          >
            Next <ChevronRight size={15} />
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={!canSubmit || submitting}
            className="flex items-center gap-1.5 text-sm bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-semibold px-4 py-1.5 rounded-lg transition"
          >
            {submitting ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}
            {submitting ? 'Submitting…' : 'Submit'}
          </button>
        )}
      </div>
    </div>
  )
}
