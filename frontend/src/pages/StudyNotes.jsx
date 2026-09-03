import React, { useState, useEffect } from 'react'
import { useAuth } from '@clerk/react'
import { 
  FileText, 
  Sparkles, 
  GitFork, 
  RotateCw, 
  CheckCircle2, 
  Brain, 
  Plus, 
  Trash2, 
  ArrowRight, 
  ArrowLeft,
  BookOpen,
  Zap,
  Filter,
  Layers,
  ChevronDown,
  ChevronRight,
  AlertCircle,
  Copy,
  Check,
  Download
} from 'lucide-react'

// Recursive Tree Node Component for Mind-Map Rendering
function MindMapTreeNode({ node, level = 0 }) {
  const [expanded, setExpanded] = useState(true)
  const hasChildren = node.children && node.children.length > 0

  return (
    <div className={`space-y-2 ${level > 0 ? 'ml-6 pl-4 border-l-2 border-slate-800/80' : ''}`}>
      <div 
        onClick={() => hasChildren && setExpanded(!expanded)}
        className={`p-3 rounded-xl border transition-all cursor-pointer flex items-start justify-between gap-3 ${
          level === 0 
            ? 'bg-gradient-to-r from-indigo-950/40 to-purple-950/40 border-indigo-500/40 text-white shadow-lg' 
            : level === 1 
            ? 'bg-slate-900 border-slate-800 text-indigo-200 hover:border-slate-700' 
            : 'bg-slate-950/60 border-slate-850 text-slate-300'
        }`}
      >
        <div className="flex items-start space-x-2.5">
          {hasChildren ? (
            <button className="text-slate-400 mt-0.5 hover:text-white">
              {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </button>
          ) : (
            <div className="w-3.5 h-3.5 rounded-full bg-indigo-500/20 border border-indigo-500/40 mt-1 flex-shrink-0" />
          )}
          <div className="space-y-0.5">
            <span className="font-bold text-xs md:text-sm block">{node.label}</span>
            {node.details && (
              <p className="text-[11px] text-slate-400 font-normal leading-relaxed">{node.details}</p>
            )}
          </div>
        </div>

        {hasChildren && (
          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
            {node.children.length} {node.children.length === 1 ? 'branch' : 'branches'}
          </span>
        )}
      </div>

      {hasChildren && expanded && (
        <div className="space-y-2 mt-2 animate-fade-in">
          {node.children.map((child, idx) => (
            <MindMapTreeNode key={child.id || idx} node={child} level={level + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function StudyNotes() {
  const { getToken } = useAuth()
  
  // State
  const [notes, setNotes] = useState([])
  const [concepts, setConcepts] = useState([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [selectedNote, setSelectedNote] = useState(null)
  const [error, setError] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)
  const [copied, setCopied] = useState(false)
  
  // Modal & Generation filter
  const [showGenModal, setShowGenModal] = useState(false)
  const [genSelectedConcepts, setGenSelectedConcepts] = useState([])
  const [activeViewMode, setActiveViewMode] = useState('both') // 'notes' | 'mindmap' | 'both'
  const [selectedFilterConcept, setSelectedFilterConcept] = useState('all')

  useEffect(() => {
    fetchInitialData()
  }, [])

  const fetchInitialData = async () => {
    setLoading(true)
    setError(null)
    try {
      const token = await getToken()
      const headers = { Authorization: `Bearer ${token}` }
      
      const [notesRes, conceptsRes] = await Promise.all([
        fetch('http://localhost:8000/api/study-notes', { headers }),
        fetch('http://localhost:8000/api/concepts', { headers })
      ])
      
      if (notesRes.ok) {
        const notesData = await notesRes.json()
        setNotes(notesData)
        if (notesData.length > 0 && !selectedNote) {
          setSelectedNote(notesData[0])
        }
      }
      if (conceptsRes.ok) setConcepts(await conceptsRes.json())
    } catch (err) {
      console.error('Failed to load study notes:', err)
      setError('Could not connect to the backend server.')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateNotes = async () => {
    setGenerating(true)
    setError(null)
    setSuccessMsg(null)
    try {
      const token = await getToken()
      const res = await fetch('http://localhost:8000/api/study-notes/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          concept_ids: genSelectedConcepts.length > 0 ? genSelectedConcepts : undefined,
          depth: 'comprehensive'
        })
      })
      
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to synthesize study notes')
      }
      
      setSuccessMsg(`Successfully generated ${data.count} structured study modules & mind-maps!`)
      setShowGenModal(false)
      setGenSelectedConcepts([])
      await fetchInitialData()
      if (data.notes && data.notes.length > 0) {
        setSelectedNote(data.notes[0])
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setGenerating(false)
    }
  }

  const handleDeleteNote = async (noteId, e) => {
    e?.stopPropagation()
    if (!window.confirm('Are you sure you want to delete this study note module?')) return
    
    try {
      const token = await getToken()
      const res = await fetch(`http://localhost:8000/api/study-notes/${noteId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        setNotes(prev => prev.filter(n => (n._id || n.id) !== noteId))
        if ((selectedNote?._id || selectedNote?.id) === noteId) {
          const remaining = notes.filter(n => (n._id || n.id) !== noteId)
          setSelectedNote(remaining.length > 0 ? remaining[0] : null)
        }
      }
    } catch (err) {
      console.error('Delete error:', err)
    }
  }

  const handleCopyMarkdown = () => {
    if (!selectedNote) return
    navigator.clipboard.writeText(selectedNote.markdown_content || selectedNote.summary)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const filteredNotes = notes.filter(n => {
    if (selectedFilterConcept !== 'all' && n.concept_name !== selectedFilterConcept && n.concept_id !== selectedFilterConcept) {
      return false
    }
    return true
  })

  return (
    <div className="space-y-8 animate-fade-in pb-16">
      
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-500/20">
              <FileText className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white flex items-center gap-2">
                Study Notes & Mind-Maps
                <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  Visual Tree Synthesis
                </span>
              </h1>
              <p className="text-sm text-slate-400 mt-0.5">
                AI-synthesized comprehensive study cheat-sheets and hierarchical branch trees grounded in your knowledge graph.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowGenModal(true)}
            className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-medium text-sm transition-all shadow-md shadow-indigo-600/20 active:scale-95 cursor-pointer"
          >
            <Sparkles className="h-4 w-4" />
            <span>Synthesize Notes</span>
          </button>
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-xs hover:underline cursor-pointer">Dismiss</button>
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-xs hover:underline cursor-pointer">Dismiss</button>
        </div>
      )}

      {loading ? (
        <div className="p-20 text-center text-slate-500 space-y-3">
          <RotateCw className="h-8 w-8 animate-spin mx-auto text-indigo-400" />
          <p className="text-sm font-medium">Loading study notes and visual mind-maps...</p>
        </div>
      ) : notes.length === 0 ? (
        <div className="p-16 rounded-2xl bg-slate-900/40 border border-dashed border-slate-800 text-center space-y-4">
          <div className="w-14 h-14 rounded-full bg-indigo-500/10 text-indigo-400 flex items-center justify-center mx-auto">
            <FileText size={28} />
          </div>
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-white">No Study Notes Synthesized Yet</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Select concepts from your extracted curriculum and let MK-Path generate structured notes with interactive mind-map trees.
            </p>
          </div>
          <button
            onClick={() => setShowGenModal(true)}
            className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-md shadow-indigo-600/20 cursor-pointer"
          >
            Synthesize First Study Module
          </button>
        </div>
      ) : (
        /* ─── TWO-PANE EXPLORER & VIEWER ─── */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          
          {/* Left Column: Note Library Selector */}
          <div className="lg:col-span-4 space-y-4">
            
            {/* Filter */}
            <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800 flex items-center justify-between gap-2">
              <span className="text-xs font-bold text-slate-300">Modules ({filteredNotes.length}):</span>
              <select
                value={selectedFilterConcept}
                onChange={(e) => setSelectedFilterConcept(e.target.value)}
                className="px-2.5 py-1 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-300 focus:outline-none"
              >
                <option value="all">All Concepts</option>
                {concepts.map(c => (
                  <option key={c._id || c.id} value={c.name}>{c.name}</option>
                ))}
              </select>
            </div>

            {/* Note Cards List */}
            <div className="space-y-2.5 max-h-[720px] overflow-y-auto pr-1">
              {filteredNotes.map((n) => {
                const noteId = n._id || n.id
                const isSelected = (selectedNote?._id || selectedNote?.id) === noteId
                return (
                  <div
                    key={noteId}
                    onClick={() => setSelectedNote(n)}
                    className={`p-4 rounded-xl border transition-all cursor-pointer relative group ${
                      isSelected 
                        ? 'bg-indigo-600/15 border-indigo-500/50 shadow-md shadow-indigo-500/10' 
                        : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 truncate max-w-[180px]">
                        {n.concept_name}
                      </span>
                      <button
                        onClick={(e) => handleDeleteNote(noteId, e)}
                        className="text-slate-500 hover:text-red-400 p-1 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                        title="Delete note"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>

                    <h4 className="text-xs font-bold text-white line-clamp-1">{n.title}</h4>
                    <p className="text-[11px] text-slate-400 line-clamp-2 mt-1 leading-relaxed">{n.summary}</p>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Right Column: Interactive Study Module & Mind-Map Viewer */}
          {selectedNote && (
            <div className="lg:col-span-8 bg-slate-900 border border-slate-800 rounded-2xl p-6 md:p-8 space-y-8 shadow-2xl">
              
              {/* Header */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">{selectedNote.concept_name}</span>
                    <span className="text-slate-600">•</span>
                    <span className="text-[11px] text-slate-400">Synthesized Knowledge Module</span>
                  </div>
                  <h2 className="text-xl md:text-2xl font-black text-white tracking-tight">{selectedNote.title}</h2>
                </div>

                {/* View Mode Controls & Copy Button */}
                <div className="flex items-center space-x-2">
                  <div className="bg-slate-950 p-1 rounded-xl border border-slate-800 flex items-center space-x-1">
                    <button
                      onClick={() => setActiveViewMode('both')}
                      className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                        activeViewMode === 'both' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      Split View
                    </button>
                    <button
                      onClick={() => setActiveViewMode('notes')}
                      className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                        activeViewMode === 'notes' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      Notes Only
                    </button>
                    <button
                      onClick={() => setActiveViewMode('mindmap')}
                      className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                        activeViewMode === 'mindmap' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      Mind-Map Only
                    </button>
                  </div>

                  <button
                    onClick={handleCopyMarkdown}
                    className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition cursor-pointer"
                    title="Copy Markdown content"
                  >
                    {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
                  </button>
                </div>
              </div>

              {/* Executive Summary Callout */}
              <div className="p-4 rounded-xl bg-indigo-950/20 border border-indigo-900/30 text-indigo-200 text-xs leading-relaxed space-y-1">
                <strong className="text-white block uppercase tracking-wider text-[10px]">Executive Summary</strong>
                <p>{selectedNote.summary}</p>
              </div>

              {/* Split Content Body */}
              <div className={`grid gap-6 ${activeViewMode === 'both' ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'}`}>
                
                {/* Panel 1: Structured Notes, Takeaways, Axioms, Pitfalls */}
                {(activeViewMode === 'both' || activeViewMode === 'notes') && (
                  <div className="space-y-6">
                    {/* Key Takeaways */}
                    {selectedNote.key_takeaways?.length > 0 && (
                      <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2.5">
                        <span className="text-[11px] font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                          <Zap size={13} /> Key Takeaways
                        </span>
                        <ul className="space-y-1.5 text-xs text-slate-300">
                          {selectedNote.key_takeaways.map((item, idx) => (
                            <li key={idx} className="flex items-start space-x-2">
                              <span className="text-amber-400 font-bold">•</span>
                              <span>{item}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Mathematical Axioms or Syntax Rules */}
                    {selectedNote.formulae_or_rules?.length > 0 && (
                      <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2.5">
                        <span className="text-[11px] font-bold text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
                          <Brain size={13} /> Core Axioms & Formulae
                        </span>
                        <div className="space-y-1.5 text-xs font-mono text-indigo-200 bg-slate-950 p-3 rounded-lg border border-slate-850">
                          {selectedNote.formulae_or_rules.map((item, idx) => (
                            <div key={idx}>{item}</div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Common Pitfalls & Traps */}
                    {selectedNote.common_pitfalls?.length > 0 && (
                      <div className="p-4 rounded-xl bg-red-950/20 border border-red-900/30 space-y-2.5">
                        <span className="text-[11px] font-bold text-red-400 uppercase tracking-wider flex items-center gap-1.5">
                          <AlertCircle size={13} /> Common Exam Traps & Misconceptions
                        </span>
                        <ul className="space-y-1.5 text-xs text-red-200">
                          {selectedNote.common_pitfalls.map((item, idx) => (
                            <li key={idx} className="flex items-start space-x-2">
                              <span className="text-red-400 font-bold">✕</span>
                              <span>{item}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Detailed Markdown Content */}
                    {selectedNote.markdown_content && (
                      <div className="p-5 rounded-xl bg-slate-950/40 border border-slate-800 space-y-3">
                        <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                          Full Lecture Notes
                        </span>
                        <div className="text-xs text-slate-300 leading-relaxed whitespace-pre-line prose prose-invert max-w-none">
                          {selectedNote.markdown_content}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Panel 2: Interactive Mind-Map Tree */}
                {(activeViewMode === 'both' || activeViewMode === 'mindmap') && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold text-purple-400 uppercase tracking-wider flex items-center gap-1.5">
                        <GitFork size={13} /> Hierarchical Mind-Map Tree
                      </span>
                      <span className="text-[10px] text-slate-500">Click branches to expand/collapse</span>
                    </div>

                    <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 max-h-[600px] overflow-y-auto">
                      {selectedNote.mind_map_tree && selectedNote.mind_map_tree.label ? (
                        <MindMapTreeNode node={selectedNote.mind_map_tree} />
                      ) : (
                        <div className="p-8 text-center text-slate-500 text-xs">
                          Mind-map tree representation unavailable for this module.
                        </div>
                      )}
                    </div>
                  </div>
                )}

              </div>

            </div>
          )}

        </div>
      )}

      {/* ─── GENERATE STUDY NOTES MODAL ─── */}
      {showGenModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-lg w-full space-y-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center space-x-2.5">
                <div className="p-2 rounded-lg bg-indigo-600/10 text-indigo-400 border border-indigo-500/20">
                  <Sparkles size={18} />
                </div>
                <h3 className="text-lg font-bold text-white">Synthesize Study Notes & Mind-Maps</h3>
              </div>
              <button
                onClick={() => setShowGenModal(false)}
                className="text-slate-400 hover:text-white text-sm cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Select Concepts to Synthesize ({concepts.length} Available)
                </label>
                <div className="max-h-56 overflow-y-auto space-y-1.5 bg-slate-950/60 p-2.5 rounded-xl border border-slate-800">
                  {concepts.length === 0 ? (
                    <p className="text-xs text-slate-500 p-2 text-center">No concepts available. Upload study materials first.</p>
                  ) : (
                    concepts.map((c) => {
                      const id = c._id || c.id
                      const isSelected = genSelectedConcepts.includes(id)
                      return (
                        <div
                          key={id}
                          onClick={() => {
                            setGenSelectedConcepts(prev => 
                              isSelected ? prev.filter(x => x !== id) : [...prev, id]
                            )
                          }}
                          className={`p-2 rounded-lg text-xs flex items-center justify-between cursor-pointer transition-all ${
                            isSelected ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30' : 'bg-slate-900/40 text-slate-400 hover:bg-slate-850'
                          }`}
                        >
                          <span className="font-medium truncate">{c.name}</span>
                          <span className="text-[10px] uppercase font-bold text-slate-500">{c.difficulty}</span>
                        </div>
                      )
                    })
                  )}
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  {genSelectedConcepts.length === 0 ? 'Synthesizing for top foundational concepts by default' : `Selected ${genSelectedConcepts.length} concepts`}
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end space-x-3 pt-2">
              <button
                type="button"
                onClick={() => setShowGenModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleGenerateNotes}
                disabled={generating || concepts.length === 0}
                className="px-5 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-semibold text-xs flex items-center space-x-2 transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50 cursor-pointer"
              >
                {generating ? (
                  <>
                    <RotateCw className="h-3.5 w-3.5 animate-spin" />
                    <span>Synthesizing Mind-Maps...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="h-3.5 w-3.5" />
                    <span>Synthesize Notes</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}
