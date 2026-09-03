import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { useAuth } from '@clerk/react'
import { 
  ReactFlow, 
  MiniMap, 
  Controls, 
  Background, 
  useNodesState, 
  useEdgesState,
  Handle,
  Position
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { 
  FileText, 
  Sparkles, 
  GitFork, 
  RotateCw, 
  CheckCircle2, 
  Brain, 
  Trash2, 
  ArrowRight, 
  ArrowLeft,
  BookOpen,
  Zap,
  Filter,
  Layers,
  AlertCircle,
  Copy,
  Check,
  Maximize2,
  Minimize2
} from 'lucide-react'

// Custom Visual Tree Node for Mind-Map Flow Canvas
function MindMapCanvasNode({ data }) {
  const isRoot = data.level === 0
  const isBranch = data.level === 1
  const isLeaf = data.level === 2

  return (
    <div 
      className={`px-4 py-3 rounded-2xl border transition-all duration-300 shadow-xl select-none min-w-[190px] max-w-[280px] ${
        isRoot 
          ? 'bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 text-white border-white/30 ring-4 ring-indigo-500/20' 
          : isBranch
          ? 'bg-slate-900/95 border-indigo-500/50 text-indigo-100 ring-2 ring-indigo-500/10 hover:border-indigo-400'
          : 'bg-slate-950/90 border-slate-800 text-slate-200 hover:border-slate-700'
      }`}
    >
      {/* Input connector for child nodes */}
      {!isRoot && (
        <Handle 
          type="target" 
          position={Position.Left} 
          className="!bg-indigo-400 !w-3 !h-3 !border-2 !border-slate-900" 
        />
      )}

      <div className="space-y-1">
        <div className="flex items-center justify-between gap-2">
          <span className={`font-black tracking-tight line-clamp-1 ${isRoot ? 'text-sm' : isBranch ? 'text-xs' : 'text-[11px]'}`}>
            {data.label}
          </span>
          {data.branchTag && (
            <span className="text-[9px] uppercase font-bold px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300">
              {data.branchTag}
            </span>
          )}
        </div>

        {data.details && (
          <p className={`line-clamp-2 leading-relaxed font-normal ${isRoot ? 'text-white/80 text-[11px]' : 'text-slate-400 text-[10px]'}`}>
            {data.details}
          </p>
        )}
      </div>

      {/* Output connector for parent/branch nodes */}
      {!isLeaf && (
        <Handle 
          type="source" 
          position={Position.Right} 
          className="!bg-purple-400 !w-3 !h-3 !border-2 !border-slate-900" 
        />
      )}
    </div>
  )
}

const nodeTypes = {
  mindMapNode: MindMapCanvasNode
}

// Convert Hierarchical Tree JSON to ReactFlow Nodes & Smooth Animated Edges
function buildFlowGraphFromTree(tree) {
  const nodes = []
  const edges = []
  
  if (!tree || !tree.label) return { nodes, edges }

  // 1. Root Node
  const rootId = 'root'
  nodes.push({
    id: rootId,
    type: 'mindMapNode',
    position: { x: 50, y: 300 },
    data: {
      label: tree.label,
      details: tree.details,
      level: 0
    }
  })

  const branches = tree.children || []
  const branchSpacingY = 220
  const startBranchY = 300 - ((branches.length - 1) * branchSpacingY) / 2

  branches.forEach((branch, bIdx) => {
    const branchId = `branch_${bIdx}`
    const branchY = startBranchY + bIdx * branchSpacingY
    const branchX = 400

    nodes.push({
      id: branchId,
      type: 'mindMapNode',
      position: { x: branchX, y: branchY },
      data: {
        label: branch.label,
        details: branch.details,
        level: 1,
        branchTag: `Branch ${bIdx + 1}`
      }
    })

    // Edge Root -> Branch
    edges.push({
      id: `e_${rootId}_${branchId}`,
      source: rootId,
      target: branchId,
      type: 'smoothstep',
      animated: true,
      style: { stroke: '#818cf8', strokeWidth: 2.5 }
    })

    const leaves = branch.children || []
    const leafSpacingY = 110
    const startLeafY = branchY - ((leaves.length - 1) * leafSpacingY) / 2

    leaves.forEach((leaf, lIdx) => {
      const leafId = `leaf_${bIdx}_${lIdx}`
      const leafY = startLeafY + lIdx * leafSpacingY
      const leafX = 750

      nodes.push({
        id: leafId,
        type: 'mindMapNode',
        position: { x: leafX, y: leafY },
        data: {
          label: leaf.label,
          details: leaf.details,
          level: 2
        }
      })

      // Edge Branch -> Leaf
      edges.push({
        id: `e_${branchId}_${leafId}`,
        source: branchId,
        target: leafId,
        type: 'smoothstep',
        animated: true,
        style: { stroke: '#c084fc', strokeWidth: 2 }
      })
    })
  })

  return { nodes, edges }
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
  
  // Tab selector: 'notes' | 'mindmap'
  const [activeTab, setActiveTab] = useState('mindmap')
  const [isFullscreen, setIsFullscreen] = useState(false)

  // ReactFlow state for mind-map canvas
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  // Modal & Generation filter
  const [showGenModal, setShowGenModal] = useState(false)
  const [genSelectedConcepts, setGenSelectedConcepts] = useState([])
  const [selectedFilterConcept, setSelectedFilterConcept] = useState('all')

  useEffect(() => {
    fetchInitialData()
  }, [])

  // Sync ReactFlow Graph when selectedNote changes
  useEffect(() => {
    if (!selectedNote) return

    // Derive or build mind-map tree
    const tree = (selectedNote.mind_map_tree && selectedNote.mind_map_tree.label) 
      ? selectedNote.mind_map_tree 
      : {
          id: 'root',
          label: selectedNote.concept_name || 'Concept Overview',
          details: selectedNote.summary,
          children: [
            {
              id: 'branch_takeaways',
              label: 'Core Principles & Key Takeaways',
              details: `${selectedNote.key_takeaways?.length || 0} critical takeaways`,
              children: (selectedNote.key_takeaways || []).map((t, idx) => ({
                id: `t_${idx}`,
                label: t,
                details: ''
              }))
            },
            {
              id: 'branch_rules',
              label: 'Core Axioms & Rules',
              details: `${selectedNote.formulae_or_rules?.length || 0} rules & equations`,
              children: (selectedNote.formulae_or_rules || []).map((r, idx) => ({
                id: `r_${idx}`,
                label: r,
                details: ''
              }))
            },
            {
              id: 'branch_traps',
              label: 'Exam Traps & Pitfalls',
              details: `${selectedNote.common_pitfalls?.length || 0} pitfall warnings`,
              children: (selectedNote.common_pitfalls || []).map((p, idx) => ({
                id: `p_${idx}`,
                label: p,
                details: ''
              }))
            }
          ].filter(b => b.children.length > 0)
        }

    const flowData = buildFlowGraphFromTree(tree)
    setNodes(flowData.nodes)
    setEdges(flowData.edges)
  }, [selectedNote])

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
    <div className="space-y-6 animate-fade-in pb-16">
      
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-500/20">
              <GitFork className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white flex items-center gap-2">
                Study Notes & Visual Mind-Map Canvas
                <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  Interactive Node Graph
                </span>
              </h1>
              <p className="text-sm text-slate-400 mt-0.5">
                Draggable, zoomable hierarchical tree canvas with animated flow branches and detailed lecture cheat-sheets.
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
          <p className="text-sm font-medium">Loading mind-map canvas and study modules...</p>
        </div>
      ) : notes.length === 0 ? (
        <div className="p-16 rounded-2xl bg-slate-900/40 border border-dashed border-slate-800 text-center space-y-4">
          <div className="w-14 h-14 rounded-full bg-indigo-500/10 text-indigo-400 flex items-center justify-center mx-auto">
            <GitFork size={28} />
          </div>
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-white">No Mind-Map Modules Found</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Select concepts from your extracted curriculum and let MK-Path synthesize interactive draggable tree diagrams.
            </p>
          </div>
          <button
            onClick={() => setShowGenModal(true)}
            className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-md shadow-indigo-600/20 cursor-pointer"
          >
            Synthesize First Mind-Map Module
          </button>
        </div>
      ) : (
        /* ─── MAIN TWO-COLUMN WORKSPACE ─── */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          
          {/* Left Column: Concept Selector Sidebar */}
          <div className="lg:col-span-3 space-y-3">
            <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-800 flex items-center justify-between gap-2">
              <span className="text-xs font-bold text-slate-300">Modules ({filteredNotes.length})</span>
              <select
                value={selectedFilterConcept}
                onChange={(e) => setSelectedFilterConcept(e.target.value)}
                className="px-2 py-1 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-300 focus:outline-none"
              >
                <option value="all">All Concepts</option>
                {concepts.map(c => (
                  <option key={c._id || c.id} value={c.name}>{c.name}</option>
                ))}
              </select>
            </div>

            <div className="space-y-2 max-h-[700px] overflow-y-auto pr-1">
              {filteredNotes.map((n) => {
                const noteId = n._id || n.id
                const isSelected = (selectedNote?._id || selectedNote?.id) === noteId
                return (
                  <div
                    key={noteId}
                    onClick={() => setSelectedNote(n)}
                    className={`p-3.5 rounded-xl border transition-all cursor-pointer relative group ${
                      isSelected 
                        ? 'bg-indigo-600/15 border-indigo-500/60 shadow-md shadow-indigo-500/10' 
                        : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 truncate max-w-[150px]">
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
                  </div>
                )
              })}
            </div>
          </div>

          {/* Right Column: Visual Mind-Map Canvas & Notes Studio */}
          {selectedNote && (
            <div className="lg:col-span-9 bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6 shadow-2xl">
              
              {/* Module Header Bar */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
                <div className="space-y-0.5">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">{selectedNote.concept_name}</span>
                    <span className="text-slate-600">•</span>
                    <span className="text-[11px] text-slate-400">Interactive Visual Tree</span>
                  </div>
                  <h2 className="text-xl font-black text-white tracking-tight">{selectedNote.title}</h2>
                </div>

                {/* Switcher Tabs: Mind-Map vs Written Notes */}
                <div className="flex items-center space-x-2">
                  <div className="bg-slate-950 p-1 rounded-xl border border-slate-800 flex items-center space-x-1">
                    <button
                      onClick={() => setActiveTab('mindmap')}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center space-x-1.5 ${
                        activeTab === 'mindmap' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      <GitFork size={13} />
                      <span>Mind-Map Tree Canvas</span>
                    </button>
                    <button
                      onClick={() => setActiveTab('notes')}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center space-x-1.5 ${
                        activeTab === 'notes' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      <FileText size={13} />
                      <span>Structured Notes</span>
                    </button>
                  </div>

                  <button
                    onClick={handleCopyMarkdown}
                    className="p-2 rounded-xl bg-slate-800 hover:bg-slate-750 text-slate-300 hover:text-white border border-slate-700 transition cursor-pointer"
                    title="Copy Markdown notes"
                  >
                    {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
                  </button>
                </div>
              </div>

              {/* ─── SECTION 1: DEDICATED VISUAL MIND-MAP CANVAS ─── */}
              {activeTab === 'mindmap' && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span className="flex items-center gap-1.5 font-medium">
                      <Sparkles size={13} className="text-purple-400" />
                      Drag nodes freely, zoom with mouse wheel, or explore animated branch connections.
                    </span>
                    <span className="text-[11px] text-slate-500 font-mono">
                      {nodes.length} Nodes • {edges.length} Animated Links
                    </span>
                  </div>

                  <div className="h-[550px] w-full rounded-2xl border border-slate-800 bg-slate-950/80 relative overflow-hidden shadow-inner">
                    <ReactFlow
                      nodes={nodes}
                      edges={edges}
                      onNodesChange={onNodesChange}
                      onEdgesChange={onEdgesChange}
                      nodeTypes={nodeTypes}
                      fitView
                      fitViewOptions={{ padding: 0.2 }}
                      colorMode="dark"
                    >
                      <Background color="#1e1b4b" gap={20} size={1.5} />
                      <Controls className="bg-slate-900 border border-slate-800 text-white rounded-xl shadow-xl" />
                      <MiniMap 
                        nodeStrokeColor="#818cf8"
                        nodeColor="#0f172a"
                        maskColor="rgba(15, 23, 42, 0.7)"
                        className="bg-slate-900 border border-slate-800 rounded-xl"
                      />
                    </ReactFlow>
                  </div>
                </div>
              )}

              {/* ─── SECTION 2: STRUCTURED WRITTEN CHEAT-SHEET NOTES ─── */}
              {activeTab === 'notes' && (
                <div className="space-y-6 animate-fade-in">
                  
                  {/* Executive Summary */}
                  <div className="p-4 rounded-xl bg-indigo-950/20 border border-indigo-900/30 text-indigo-200 text-xs leading-relaxed space-y-1">
                    <strong className="text-white block uppercase tracking-wider text-[10px]">Executive Summary</strong>
                    <p>{selectedNote.summary}</p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                  </div>

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
