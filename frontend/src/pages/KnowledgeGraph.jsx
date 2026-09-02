import React, { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@clerk/react'
import { 
  ReactFlow, 
  MiniMap, 
  Controls, 
  Background, 
  useNodesState, 
  useEdgesState 
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { 
  RefreshCw, 
  Info, 
  Award, 
  Sparkles, 
  Activity, 
  Layers, 
  X, 
  Loader2 
} from 'lucide-react'

export default function KnowledgeGraph() {
  const { getToken } = useAuth()
  
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [loading, setLoading] = useState(true)
  const [selectedNode, setSelectedNode] = useState(null)

  // Fetch graph details
  const fetchGraph = async () => {
    try {
      setLoading(true)
      const token = await getToken()
      const res = await fetch('http://localhost:8000/api/graph', {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })
      if (!res.ok) throw new Error('Failed to retrieve knowledge graph data')
      const data = await res.json()
      
      setNodes(data.nodes || [])
      setEdges(data.edges || [])
      
      // Keep selected node reference active if it still exists
      if (selectedNode) {
        const updated = data.nodes.find(n => n.id === selectedNode.id)
        if (updated) {
          setSelectedNode(updated)
        }
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchGraph()
  }, [getToken])

  // Handle node selection click
  const handleNodeClick = useCallback((event, node) => {
    setSelectedNode(node)
  }, [])

  return (
    <div className="flex h-full relative overflow-hidden">
      
      {/* Left Pane: Main Canvas area */}
      <div className={`flex-1 flex flex-col space-y-4 pr-0 transition-all duration-300 ${selectedNode ? 'lg:mr-[380px] xl:mr-[440px]' : ''}`}>
        
        {/* Graph Toolbar */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 flex-shrink-0">
          <div className="flex flex-col">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">Unified Knowledge Graph</h2>
            <p className="text-xs text-slate-500 mt-0.5">Visual representation of extracted concepts, prerequisites, and mastery progression.</p>
          </div>
          <button 
            onClick={fetchGraph}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-bold text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition"
          >
            {loading ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
            <span>Refresh Graph</span>
          </button>
        </div>

        {/* Graph Canvas Panel */}
        <div className="flex-1 border border-slate-800 bg-slate-950/40 rounded-2xl relative overflow-hidden min-h-[400px]">
          {loading && nodes.length === 0 ? (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-slate-950/50">
              <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
            </div>
          ) : nodes.length === 0 ? (
            // Zero State empty dashboard panel
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-8 space-y-4">
              <div className="p-4 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded-2xl">
                <Layers className="h-8 w-8" />
              </div>
              <div className="space-y-1.5">
                <p className="font-bold text-sm text-slate-300">Your Knowledge Graph is empty.</p>
                <p className="text-xs text-slate-500 max-w-xs leading-relaxed">
                  Knowledge graphs are constructed from concept nodes. Upload a study PDF and trigger AI Concept Miner to populate this canvas.
                </p>
              </div>
            </div>
          ) : (
            // React Flow viewport
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={handleNodeClick}
              fitView
              colorMode="dark"
            >
              <Background color="#334155" gap={16} size={1} />
              <Controls className="bg-slate-900 border border-slate-800 text-white rounded-lg" />
              <MiniMap 
                nodeStrokeColor={(n) => n.style?.border.split(' ')[2] || '#475569'}
                nodeColor={(n) => '#0f172a'}
                maskColor="rgba(15, 23, 42, 0.6)"
                className="bg-slate-900 border border-slate-800 rounded-lg"
              />
            </ReactFlow>
          )}
        </div>
      </div>

      {/* Right Drawer: Concept Node details panel */}
      {selectedNode && (
        <div className="fixed inset-y-0 right-0 z-30 w-full sm:w-[380px] md:w-[420px] bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col animate-in slide-in-from-right duration-300">
          
          {/* Header */}
          <div className="p-5 border-b border-slate-800 bg-slate-950/20 flex items-center justify-between">
            <div className="flex items-center space-x-2.5 truncate">
              <Layers size={18} className="text-indigo-400" />
              <h3 className="font-bold text-white text-sm truncate">{selectedNode.data.name}</h3>
            </div>
            <button 
              onClick={() => setSelectedNode(null)}
              className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
            >
              <X size={16} />
            </button>
          </div>

          {/* Body Content */}
          <div className="flex-1 p-5 overflow-y-auto space-y-6">
            
            {/* Mastery Card */}
            <div className="p-4 bg-slate-950/40 border border-slate-850 rounded-xl space-y-3">
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-400 uppercase font-bold tracking-wider">Concept Mastery</span>
                <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                  selectedNode.data.mastery_state === 'Mastered'
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/10'
                    : selectedNode.data.mastery_state === 'Proficient'
                      ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/10'
                      : selectedNode.data.mastery_state === 'Learning'
                        ? 'bg-amber-500/10 text-amber-400 border border-amber-500/10'
                        : selectedNode.data.mastery_state === 'Weak'
                          ? 'bg-rose-500/10 text-rose-400 border border-rose-500/10'
                          : 'bg-slate-800 text-slate-400'
                }`}>
                  {selectedNode.data.mastery_state}
                </span>
              </div>
              <div className="space-y-1">
                <div className="flex justify-between items-end">
                  <span className="text-xs text-slate-500">Mastery Score</span>
                  <span className="text-lg font-extrabold text-white">
                    {selectedNode.data.mastery_score !== null 
                      ? `${selectedNode.data.mastery_score.toFixed(0)}%` 
                      : 'Unassessed'}
                  </span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div 
                    className="bg-indigo-500 h-full rounded-full transition-all duration-300"
                    style={{ width: `${selectedNode.data.mastery_score || 0}%` }}
                  ></div>
                </div>
              </div>
            </div>

            {/* Description */}
            <div className="space-y-2">
              <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Definition</span>
              <p className="text-xs text-slate-350 leading-relaxed font-medium bg-slate-950/20 p-4 border border-slate-850 rounded-xl">
                {selectedNode.data.description}
              </p>
            </div>

            {/* Relevance & Difficulty scores */}
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-slate-950/20 border border-slate-850 rounded-lg flex flex-col space-y-1">
                <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Difficulty</span>
                <span className="font-extrabold text-white capitalize">{selectedNode.data.difficulty}</span>
              </div>
              <div className="p-3 bg-slate-950/20 border border-slate-850 rounded-lg flex flex-col space-y-1">
                <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Dependencies</span>
                <span className="font-extrabold text-white">{selectedNode.data.prerequisites?.length || 0} reqs</span>
              </div>
            </div>

            {/* In-depth Relevance progress bars */}
            <div className="space-y-4">
              <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Weights & Relevance</span>
              <div className="space-y-3 p-4 bg-slate-950/20 border border-slate-850 rounded-xl">
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400 flex items-center space-x-1.5">
                      <Award size={12} className="text-indigo-400" />
                      <span>Exam Relevance</span>
                    </span>
                    <span className="font-bold text-white">{selectedNode.data.exam_relevance}%</span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div 
                      className="bg-indigo-500 h-full rounded-full" 
                      style={{ width: `${selectedNode.data.exam_relevance}%` }}
                    ></div>
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400 flex items-center space-x-1.5">
                      <Activity size={12} className="text-violet-400" />
                      <span>Industry Relevance</span>
                    </span>
                    <span className="font-bold text-white">{selectedNode.data.industry_relevance}%</span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div 
                      className="bg-violet-500 h-full rounded-full" 
                      style={{ width: `${selectedNode.data.industry_relevance}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>

            {/* Prerequisites */}
            {selectedNode.data.prerequisites && selectedNode.data.prerequisites.length > 0 && (
              <div className="space-y-2">
                <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Required Prerequisites</span>
                <div className="flex flex-wrap gap-2">
                  {selectedNode.data.prerequisites.map((req, idx) => (
                    <span key={idx} className="text-[10px] bg-slate-850 text-slate-350 border border-slate-800 px-2 py-1 rounded-md font-semibold">
                      {req}
                    </span>
                  ))}
                </div>
              </div>
            )}

          </div>
        </div>
      )}
    </div>
  )
}
