import React, { useState, useEffect } from 'react'
import { useAuth } from '@clerk/react'
import { useNavigate } from 'react-router-dom'
import { 
  Compass, 
  Loader2, 
  MapPin, 
  ArrowUpRight, 
  TrendingUp, 
  AlertCircle, 
  PlayCircle,
  RefreshCw,
  Lock,
  Unlock
} from 'lucide-react'

export default function StudyPath() {
  const { getToken } = useAuth()
  const navigate = useNavigate()

  const [pathItems, setPathItems] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchStudyPath = async () => {
    try {
      setLoading(true)
      const token = await getToken()
      const res = await fetch('http://localhost:8000/api/study-path', {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })
      if (res.ok) {
        const data = await res.json()
        setPathItems(data.ordered_concepts || [])
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStudyPath()
  }, [getToken])

  const handlePracticeConcept = (conceptId) => {
    navigate('/assessment', { state: { preselectedConceptId: conceptId } })
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8 h-full overflow-y-auto pr-2 pb-10">
      
      {/* Page Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div className="space-y-0.5">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider">Adaptive Study Path</h2>
          <p className="text-xs text-slate-500">Ordered roadmap calculated based on mastery decay, prerequisites, and curriculum relevance weights.</p>
        </div>
        <button 
          onClick={fetchStudyPath}
          className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-bold text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition"
        >
          {loading ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
          <span>Re-Plan Path</span>
        </button>
      </div>

      {loading && pathItems.length === 0 ? (
        <div className="flex justify-center items-center py-24">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
        </div>
      ) : pathItems.length === 0 ? (
        // Empty Roadmap panel
        <div className="border border-slate-800 bg-slate-900/10 rounded-2xl p-16 flex flex-col items-center justify-center space-y-4 text-center min-h-[350px] shadow-md glow-card">
          <div className="p-4 bg-indigo-500/10 text-indigo-400 rounded-2xl border border-indigo-500/20">
            <Compass className="h-8 w-8 animate-pulse" />
          </div>
          <div className="space-y-2 max-w-sm">
            <h3 className="font-bold text-white text-sm">Adaptive roadmap is empty.</h3>
            <p className="text-slate-500 text-xs leading-relaxed">
              Ingest materials and test your knowledge. The engine constructs a step-by-step review path prioritized by weak domains and prerequisite maps.
            </p>
          </div>
        </div>
      ) : (
        // Road Map timeline layout
        <div className="relative border-l-2 border-slate-800 ml-6 pl-8 space-y-8 py-2">
          {pathItems.map((item, idx) => {
            const isPrereqWarning = item.reason.toLowerCase().includes('prerequisite')
            const isUnassessed = item.category === 'Not assessed'
            
            // Define styling colors based on category
            const isWeak = item.category === 'Weak'
            const isLearning = item.category === 'Learning'
            const isProficient = item.category === 'Proficient'
            const isMastered = item.category === 'Mastered'

            let badgeStyle = "bg-slate-800 text-slate-400"
            if (isMastered) badgeStyle = "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
            else if (isProficient) badgeStyle = "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
            else if (isLearning) badgeStyle = "bg-amber-500/10 text-amber-400 border border-amber-500/20"
            else if (isWeak) badgeStyle = "bg-rose-500/10 text-rose-400 border border-rose-500/20"

            return (
              <div key={item.concept_id} className="relative group">
                
                {/* Timeline node node connector point */}
                <div className={`absolute -left-[41px] top-1.5 w-6 h-6 rounded-full border-2 bg-slate-950 flex items-center justify-center transition-all ${
                  isPrereqWarning 
                    ? 'border-rose-500 text-rose-500' 
                    : isMastered 
                      ? 'border-emerald-500 text-emerald-500' 
                      : 'border-indigo-500 text-indigo-500'
                }`}>
                  {isPrereqWarning ? <Lock size={10} /> : <Unlock size={10} />}
                </div>

                {/* Timeline Card */}
                <div className={`p-6 border rounded-2xl bg-slate-900/20 transition-all space-y-4 glow-card ${
                  isPrereqWarning 
                    ? 'border-slate-850 opacity-60 hover:opacity-75' 
                    : 'border-slate-800 hover:border-slate-700'
                }`}>
                  
                  {/* Header */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    
                    <div className="space-y-1.5">
                      <div className="flex items-center space-x-2.5">
                        <span className="text-[10px] uppercase font-black text-indigo-400 tracking-widest bg-indigo-500/10 px-2 py-0.5 rounded">
                          Priority {idx + 1}
                        </span>
                        <span className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded ${badgeStyle}`}>
                          {item.category}
                        </span>
                      </div>
                      <h3 className="font-bold text-white text-sm flex items-center space-x-1.5">
                        <span>{item.concept_name}</span>
                      </h3>
                    </div>

                    <div className="flex items-center space-x-4">
                      {/* Mastery percentage */}
                      {!isUnassessed && (
                        <div className="text-right">
                          <div className="text-xs font-black text-white">{item.mastery_score.toFixed(0)}%</div>
                          <div className="text-[9px] text-slate-500 uppercase font-bold tracking-wider">Decayed Mastery</div>
                        </div>
                      )}
                      
                      {/* Practice Trigger */}
                      <button
                        onClick={() => handlePracticeConcept(item.concept_id)}
                        disabled={isPrereqWarning}
                        className={`p-2 rounded-xl transition flex items-center space-x-1.5 text-xs font-bold ${
                          isPrereqWarning
                            ? 'bg-slate-950 text-slate-600 cursor-not-allowed border border-slate-900'
                            : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg'
                        }`}
                      >
                        <PlayCircle size={14} />
                        <span>Assess Topic</span>
                      </button>
                    </div>

                  </div>

                  {/* Optimization Reason */}
                  <div className={`p-3 rounded-lg text-xs leading-relaxed flex items-start space-x-2 border ${
                    isPrereqWarning
                      ? 'bg-rose-950/10 border-rose-900/20 text-rose-350'
                      : 'bg-slate-950/40 border-slate-850 text-slate-400'
                  }`}>
                    {isPrereqWarning ? (
                      <AlertCircle size={14} className="flex-shrink-0 mt-0.5 text-rose-400" />
                    ) : (
                      <TrendingUp size={14} className="flex-shrink-0 mt-0.5 text-indigo-400" />
                    )}
                    <span>{item.reason}</span>
                  </div>

                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
