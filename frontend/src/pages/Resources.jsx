import React, { useState, useEffect } from 'react'
import { useAuth } from '@clerk/react'
import { 
  Sparkles, 
  Loader2, 
  BookOpen, 
  Video, 
  Newspaper, 
  ExternalLink, 
  Award,
  RefreshCw,
  Info
} from 'lucide-react'

export default function Resources() {
  const { getToken } = useAuth()

  const [resources, setResources] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchResources = async () => {
    try {
      setLoading(true)
      const token = await getToken()
      const res = await fetch('http://localhost:8000/api/resources', {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })
      if (res.ok) {
        const data = await res.json()
        setResources(data)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchResources()
  }, [getToken])

  return (
    <div className="max-w-4xl mx-auto space-y-8 h-full overflow-y-auto pr-2 pb-10">
      
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div className="space-y-0.5">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider">Recommended Resources</h2>
          <p className="text-xs text-slate-500">Trust-weighted documentation, guides, and tutorial videos aligned with your weak concepts.</p>
        </div>
        <button 
          onClick={fetchResources}
          className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-bold text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition"
        >
          {loading ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
          <span>Refresh List</span>
        </button>
      </div>

      {loading && resources.length === 0 ? (
        <div className="flex justify-center items-center py-24">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
        </div>
      ) : resources.length === 0 ? (
        // Empty State
        <div className="border border-slate-800 bg-slate-900/30 rounded-2xl p-16 flex flex-col items-center justify-center space-y-4 text-center min-h-[350px] shadow-md glow-card">
          <div className="p-4 bg-indigo-500/10 text-indigo-400 rounded-2xl border border-indigo-500/20">
            <Sparkles className="h-8 w-8" />
          </div>
          <div className="space-y-2 max-w-sm">
            <h3 className="font-bold text-white text-sm">No recommendations available.</h3>
            <p className="text-slate-500 text-xs leading-relaxed">
              Recommended materials target weak spots and unassessed concepts. Start by uploading study materials and taking calibration assessments.
            </p>
          </div>
        </div>
      ) : (
        // Resources grid
        <div className="space-y-6">
          <div className="flex items-start space-x-3 p-4 rounded-xl bg-indigo-950/10 border border-indigo-900/30 text-indigo-300 text-xs">
            <Info size={16} className="flex-shrink-0 mt-0.5" />
            <p className="leading-relaxed">
              These resources have been selected based on concepts you are currently learning, or that have dropped in mastery score due to Spaced Repetition memory decay.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {resources.map((item, idx) => (
              <div 
                key={idx} 
                className="p-5 border border-slate-800 bg-slate-900/20 hover:border-slate-700 rounded-2xl flex flex-col justify-between space-y-4 transition-all glow-card"
              >
                <div className="space-y-3">
                  
                  {/* Category/Type and Trust Score Row */}
                  <div className="flex items-center justify-between text-xs">
                    
                    <span className="flex items-center space-x-1.5 text-slate-400 font-bold bg-slate-900 px-2.5 py-1 rounded-md border border-slate-850">
                      {item.type === 'video' ? (
                        <Video size={12} className="text-violet-400" />
                      ) : item.type === 'documentation' ? (
                        <BookOpen size={12} className="text-indigo-400" />
                      ) : (
                        <Newspaper size={12} className="text-emerald-400" />
                      )}
                      <span className="capitalize">{item.type}</span>
                    </span>

                    <span className="flex items-center space-x-1 font-bold text-indigo-400 text-[10px] uppercase bg-indigo-500/5 px-2.5 py-1 border border-indigo-500/10 rounded-md">
                      <Award size={10} />
                      <span>{item.trust_score}% trust</span>
                    </span>

                  </div>

                  {/* Resource details */}
                  <div className="space-y-1">
                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">
                      Aligns with: {item.concept_name}
                    </span>
                    <h3 className="font-bold text-white text-xs leading-relaxed line-clamp-2">
                      {item.title}
                    </h3>
                  </div>

                  <p className="text-[11px] text-slate-500 font-medium">
                    Published by: <span className="text-slate-400 font-semibold">{item.source}</span>
                  </p>

                </div>

                {/* External link action */}
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full py-2 bg-slate-950 hover:bg-slate-900 border border-slate-800 hover:border-slate-700 text-white font-bold text-xs rounded-xl flex items-center justify-center space-x-2 transition"
                >
                  <span>Study Resource</span>
                  <ExternalLink size={12} />
                </a>

              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
