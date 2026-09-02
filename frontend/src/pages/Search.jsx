import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useUser, useAuth } from '@clerk/react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import { Search, FileText, Brain, HelpCircle, ClipboardList, Loader2, X, AlertCircle } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function SearchPage() {
  const { user } = useUser()
  const { getToken } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const inputRef = useRef(null)
  const [query, setQuery] = useState(searchParams.get('q') || '')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const doSearch = useCallback(async (q) => {
    if (!q || q.trim().length < 2 || !user) return
    setLoading(true)
    setError(null)
    try {
      const token = await getToken()
      const res = await fetch(`${API}/api/search?q=${encodeURIComponent(q.trim())}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!res.ok) throw new Error(await res.text())
      setResults(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [user])

  // Search when URL q param changes
  useEffect(() => {
    const q = searchParams.get('q') || ''
    setQuery(q)
    if (q) doSearch(q)
  }, [searchParams, doSearch])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (query.trim().length >= 2) {
      setSearchParams({ q: query.trim() })
    }
  }

  useEffect(() => { inputRef.current?.focus() }, [])

  const total = results?.total || 0
  const cats = results?.results || {}

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <div className="flex flex-col space-y-1">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Search</h1>
        <p className="text-slate-400 text-sm">Search across your materials, concepts, questions, and assignments.</p>
      </div>

      {/* Search Input */}
      <form onSubmit={handleSubmit} className="relative">
        <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search concepts, materials, questions…"
          className="w-full pl-11 pr-12 py-3 bg-slate-900/60 border border-slate-700 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 rounded-xl text-slate-200 text-sm outline-none placeholder-slate-600 transition"
        />
        {query && (
          <button type="button" onClick={() => { setQuery(''); setResults(null); setSearchParams({}) }}
            className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-500 hover:text-white rounded-lg transition">
            <X size={15} />
          </button>
        )}
      </form>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-indigo-400" />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 text-red-400 text-sm bg-red-950/30 border border-red-500/20 rounded-xl p-4">
          <AlertCircle size={15} /> {error}
        </div>
      )}

      {/* Results */}
      {results && !loading && (
        <div className="space-y-6">
          <p className="text-xs text-slate-500">
            {total > 0 ? `${total} result${total !== 1 ? 's' : ''} for "${searchParams.get('q')}"` : `No results for "${searchParams.get('q')}"`}
          </p>

          <ResultSection
            title="Concepts"
            icon={<Brain size={14} />}
            items={cats.concepts || []}
            renderItem={c => (
              <Link to="/knowledge-graph" key={c._id}
                className="flex flex-col gap-1 p-3 border border-slate-800 bg-slate-900/30 rounded-xl hover:border-indigo-500/40 transition">
                <p className="text-sm font-semibold text-white">{c.name}</p>
                <p className="text-xs text-slate-500 line-clamp-2">{c.description}</p>
                <div className="flex gap-2 text-xs text-slate-600 mt-1">
                  <span className="capitalize">{c.difficulty}</span>
                  <span>·</span>
                  <span>Exam: {c.exam_relevance}%</span>
                </div>
              </Link>
            )}
          />

          <ResultSection
            title="Materials"
            icon={<FileText size={14} />}
            items={cats.materials || []}
            renderItem={m => (
              <Link to="/materials" key={m._id}
                className="flex flex-col gap-1 p-3 border border-slate-800 bg-slate-900/30 rounded-xl hover:border-indigo-500/40 transition">
                <p className="text-sm font-semibold text-white">{m.title}</p>
                <div className="flex gap-2 text-xs text-slate-500 mt-0.5">
                  <span className="uppercase">{m.source_type}</span>
                  <span>·</span>
                  <span className={m.status === 'processed' ? 'text-emerald-400' : 'text-amber-400'}>{m.status}</span>
                </div>
              </Link>
            )}
          />

          <ResultSection
            title="Questions"
            icon={<HelpCircle size={14} />}
            items={cats.questions || []}
            renderItem={q => (
              <Link to="/assessment" key={q._id}
                className="flex flex-col gap-1 p-3 border border-slate-800 bg-slate-900/30 rounded-xl hover:border-indigo-500/40 transition">
                <p className="text-sm font-semibold text-white line-clamp-2">{q.question_text}</p>
                <p className="text-xs text-slate-500">{q.concept_name} · {q.difficulty}</p>
              </Link>
            )}
          />

          <ResultSection
            title="Assignments"
            icon={<ClipboardList size={14} />}
            items={cats.assignments || []}
            renderItem={a => (
              <Link to="/assignments" key={a._id}
                className="flex flex-col gap-1 p-3 border border-slate-800 bg-slate-900/30 rounded-xl hover:border-indigo-500/40 transition">
                <p className="text-sm font-semibold text-white">{a.title}</p>
                <p className="text-xs text-slate-500">{a.status} · {a.questions?.length || 0} questions</p>
              </Link>
            )}
          />

          {total === 0 && (
            <div className="text-center py-16 text-slate-500">
              <Search size={40} className="mx-auto mb-4 opacity-30" />
              <p className="text-sm">No results found. Try a different search term.</p>
              <p className="text-xs mt-1 text-slate-600">Tip: Upload more study materials to expand your searchable content.</p>
            </div>
          )}
        </div>
      )}

      {/* Initial state */}
      {!results && !loading && !query && (
        <div className="text-center py-16 text-slate-600">
          <Search size={40} className="mx-auto mb-4 opacity-20" />
          <p className="text-sm">Type to search your learning content</p>
          <p className="text-xs mt-1">Tip: Press <kbd className="px-1.5 py-0.5 bg-slate-800 border border-slate-700 rounded text-slate-300 font-mono text-xs">Ctrl+K</kbd> from anywhere</p>
        </div>
      )}
    </div>
  )
}

function ResultSection({ title, icon, items, renderItem }) {
  if (!items.length) return null
  return (
    <div className="space-y-2">
      <h2 className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
        {icon} {title} <span className="text-slate-600 font-normal">({items.length})</span>
      </h2>
      <div className="grid grid-cols-1 gap-2">
        {items.map((item, i) => renderItem(item))}
      </div>
    </div>
  )
}
