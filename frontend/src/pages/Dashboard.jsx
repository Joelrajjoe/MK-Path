import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth, useUser } from '@clerk/react'
import { 
  User, 
  Database, 
  Terminal, 
  Activity, 
  AlertTriangle,
  CheckCircle2,
  FilePlus,
  BookOpen,
  ArrowRight,
  Award,
  Shield,
  Flame,
  Zap,
  Target,
  Sparkles,
  Play,
  ExternalLink,
  Mic,
  MicOff,
  Volume2,
  Lock,
  Loader2
} from 'lucide-react'

export default function Dashboard() {
  const { getToken } = useAuth()
  const { user, signOut } = useUser()
  const navigate = useNavigate()

  // State Management
  const [stats, setStats] = useState(null)
  const [resources, setResources] = useState([])
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [demoSeeding, setDemoSeeding] = useState(false)
  const [error, setError] = useState(null)

  // Voice Recognition Accessibility states
  const [isListening, setIsListening] = useState(false)
  const [speechError, setSpeechError] = useState(null)
  const [voiceLog, setVoiceLog] = useState('')
  const [recognition, setRecognition] = useState(null)

  // Fetch Dashboard Stats and health details
  const loadDashboardData = async () => {
    try {
      setLoading(true)
      const token = await getToken()

      // 1. System Health
      const healthRes = await fetch('http://localhost:8000/api/health')
      if (healthRes.ok) {
        const healthData = await healthRes.json()
        setHealth(healthData)
      }

      // 2. Dashboard calculated stats
      const statsRes = await fetch('http://localhost:8000/api/dashboard/stats', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (statsRes.ok) {
        const statsData = await statsRes.json()
        setStats(statsData)
      }

      // 3. Recommended resources catalog list
      const resourcesRes = await fetch('http://localhost:8000/api/resources', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (resourcesRes.ok) {
        const resData = await resourcesRes.json()
        setResources(resData.slice(0, 3)) // top 3
      }

    } catch (err) {
      console.error(err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDashboardData()
  }, [getToken])

  // Browser speech synthesis reader
  const speakText = (text) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel() // Stop any current reading
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.rate = 1.0
      window.speechSynthesis.speak(utterance)
    }
  }

  // Initialize Web Speech API Recognition
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (SpeechRecognition) {
      const rec = new SpeechRecognition()
      rec.continuous = false
      rec.interimResults = false
      rec.lang = 'en-US'

      rec.onstart = () => {
        setIsListening(true)
        setSpeechError(null)
        setVoiceLog('Listening for command...')
      }

      rec.onresult = (event) => {
        const command = event.results[0][0].transcript.toLowerCase().trim()
        setVoiceLog(`Heard: "${command}"`)
        
        if (command.includes('start quiz')) {
          speakText("Starting adaptive concept quiz assessment now.")
          navigate('/assessment')
        } else if (command.includes('show weak concepts') || command.includes('show study path')) {
          speakText("Displaying your study path timeline.")
          navigate('/study-path')
        } else if (command.includes('read question')) {
          speakText("Read question command triggered. Please open the assessment view and select a question.")
        } else {
          setVoiceLog(`Unknown command: "${command}". Try "start quiz" or "show study path".`)
        }
        setIsListening(false)
      }

      rec.onerror = (e) => {
        console.error(e)
        setSpeechError(e.error === 'not-allowed' ? 'Microphone blocked.' : 'Voice recognition error.')
        setIsListening(false)
      }

      rec.onend = () => {
        setIsListening(false)
      }

      setRecognition(rec)
    }
  }, [navigate])

  const toggleSpeech = () => {
    if (!recognition) {
      alert("Browser Speech Recognition is not supported or enabled on this system.")
      return
    }
    if (isListening) {
      recognition.stop()
    } else {
      recognition.start()
    }
  }

  // Load Demo Curriculum Data
  const handleLoadDemo = async () => {
    try {
      setDemoSeeding(true)
      const token = await getToken()
      const res = await fetch('http://localhost:8000/api/demo/load', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        speakText("Demo curriculum data loaded successfully.")
        await loadDashboardData()
      }
    } catch (err) {
      console.error(err)
      alert("Failed to seed demo data.")
    } finally {
      setDemoSeeding(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8 h-full overflow-y-auto pr-2 pb-10 select-text">
      
      {/* Welcome & Clerk Profile bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-b border-slate-800 pb-5">
        <div className="flex items-center space-x-4">
          <img 
            src={user?.imageUrl} 
            alt="User Avatar" 
            className="w-12 h-12 rounded-full border-2 border-indigo-500/20 shadow-md"
          />
          <div>
            <h1 className="text-lg font-black text-white">{user?.fullName || 'Active Learner'}</h1>
            <p className="text-xs text-slate-500 font-medium">Clerk Identity Account Connected</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {/* Accessibility Voice Widget */}
          <div className="flex items-center space-x-2 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-xl">
            <button 
              onClick={toggleSpeech}
              className={`p-1.5 rounded-lg transition focus:ring-2 focus:ring-indigo-500 focus:outline-none ${
                isListening ? 'bg-indigo-650 text-white animate-pulse' : 'hover:bg-slate-800 text-slate-400'
              }`}
              title="Voice commands: 'Start quiz', 'Show study path'"
              aria-label="Toggle speech control recognition accessibility widget"
            >
              {isListening ? <Mic size={14} /> : <MicOff size={14} />}
            </button>
            <span className="text-[10px] text-slate-400 font-bold max-w-[120px] truncate">
              {voiceLog || (recognition ? 'Voice: Ready' : 'Voice: Not Supported')}
            </span>
          </div>

          <button 
            onClick={() => signOut()}
            className="px-3.5 py-2 text-xs font-bold text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-750 border border-slate-700 rounded-xl transition focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            aria-label="Sign out of Clerk Session account"
          >
            Sign Out
          </button>
        </div>
      </div>

      {loading || !stats ? (
        <div className="flex justify-center items-center py-24">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
        </div>
      ) : (
        <>
          {/* Stats Cards Row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            
            {/* 1. Mastery Score */}
            <div className="p-5 bg-slate-900/40 border border-slate-850 rounded-2xl space-y-2 relative overflow-hidden shadow-sm glow-card">
              <span className="text-[10px] text-slate-500 font-black uppercase tracking-wider block">Average Mastery</span>
              <div className="flex justify-between items-baseline pt-1">
                <span className="text-2xl font-black text-white">
                  {stats?.average_mastery !== null ? `${stats.average_mastery.toFixed(0)}%` : '—'}
                </span>
                <span className="text-[10px] bg-slate-850 px-1.5 py-0.5 rounded text-indigo-400 border border-slate-800 font-bold uppercase">
                  {stats?.average_mastery !== null 
                    ? (stats.average_mastery >= 85 ? 'Mastered' 
                      : stats.average_mastery >= 70 ? 'Proficient' 
                      : stats.average_mastery >= 40 ? 'Learning' 
                      : 'Weak')
                    : 'Unassessed'
                  }
                </span>
              </div>
              <Target className="absolute top-2 right-2 text-indigo-500/10 w-16 h-16 pointer-events-none" />
            </div>

            {/* 2. Concepts Count */}
            <div className="p-5 bg-slate-900/40 border border-slate-850 rounded-2xl space-y-2 relative overflow-hidden shadow-sm glow-card">
              <span className="text-[10px] text-slate-500 font-black uppercase tracking-wider block">Concepts Extracted</span>
              <div className="pt-1">
                <span className="text-2xl font-black text-white">{stats?.concepts_count || 0}</span>
                <span className="text-xs text-slate-500 font-semibold ml-1.5">topics mapped</span>
              </div>
              <BookOpen className="absolute top-2 right-2 text-violet-500/10 w-16 h-16 pointer-events-none" />
            </div>

            {/* 3. Streak Days */}
            <div className="p-5 bg-slate-900/40 border border-slate-850 rounded-2xl space-y-2 relative overflow-hidden shadow-sm glow-card">
              <span className="text-[10px] text-slate-500 font-black uppercase tracking-wider block">Study Streak</span>
              <div className="flex justify-between items-baseline pt-1">
                <span className="text-2xl font-black text-white">{stats?.streak_days || 0}</span>
                <span className="text-xs text-slate-500 font-semibold">days active</span>
              </div>
              <Flame className="absolute top-2 right-2 text-amber-500/10 w-16 h-16 pointer-events-none" />
            </div>

            {/* 4. Gamification XP */}
            <div className="p-5 bg-slate-900/40 border border-slate-850 rounded-2xl space-y-2 relative overflow-hidden shadow-sm glow-card">
              <span className="text-[10px] text-slate-500 font-black uppercase tracking-wider block">XP Rank Level</span>
              <div className="flex justify-between items-baseline pt-1">
                <span className="text-2xl font-black text-white">{stats?.xp || 0}</span>
                <span className="text-[10px] bg-slate-850 px-1.5 py-0.5 rounded text-violet-400 border border-slate-800 font-bold uppercase">
                  Level {stats?.level} ({stats?.level_name})
                </span>
              </div>
              <Zap className="absolute top-2 right-2 text-pink-500/10 w-16 h-16 pointer-events-none" />
            </div>

          </div>

          {/* Meaningful Empty State for New Users */}
          {stats?.concepts_count === 0 ? (
            <div className="border border-slate-800 bg-slate-900/10 rounded-2xl p-12 text-center space-y-8 shadow-md glow-card">
              <div className="space-y-3">
                <div className="mx-auto w-fit p-4 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded-2xl">
                  <BookOpen className="h-8 w-8" />
                </div>
                <div className="space-y-1.5 max-w-md mx-auto">
                  <h3 className="font-bold text-sm text-white">Start your learning journey by ingesting study material.</h3>
                  <p className="text-slate-500 text-xs leading-relaxed">
                    Upload a syllabus, textbook, or study PDF to extract concepts and trigger your unified knowledge graph timeline.
                  </p>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row justify-center items-center gap-4 max-w-md mx-auto pt-2">
                <button 
                  onClick={() => navigate('/materials')}
                  className="w-full sm:w-1/2 py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded-xl flex items-center justify-center space-x-2 transition focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                >
                  <FilePlus size={14} />
                  <span>Upload Study PDF</span>
                </button>
                <button 
                  onClick={handleLoadDemo}
                  disabled={demoSeeding}
                  className="w-full sm:w-1/2 py-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-350 font-bold text-xs rounded-xl flex items-center justify-center space-x-2 transition focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                >
                  {demoSeeding ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                  <span>Seed Demo Dataset</span>
                </button>
              </div>
            </div>
          ) : (
            // Layout sections
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              
              {/* Left Column: Progress and weak concepts */}
              <div className="lg:col-span-2 space-y-8">
                
                {/* 1. Learning Progress breakdown */}
                <div className="p-6 border border-slate-800 bg-slate-900/10 rounded-2xl space-y-4 shadow-sm">
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider pb-2 border-b border-slate-850 flex items-center justify-between">
                    <span>Curriculum Coverage</span>
                    <Link to="/knowledge-graph" className="text-[10px] text-indigo-400 hover:text-indigo-300 font-bold flex items-center space-x-1">
                      <span>View Graph Overview</span>
                      <ArrowRight size={10} />
                    </Link>
                  </h3>
                  
                  {/* Mastery percentage bar */}
                  <div className="p-4 bg-slate-950/20 border border-slate-850 rounded-xl space-y-3">
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-slate-400 font-medium">Average Decayed Mastery</span>
                      <span className="font-extrabold text-white">
                        {stats?.average_mastery !== null ? `${stats.average_mastery.toFixed(0)}%` : '0%'}
                      </span>
                    </div>
                    <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                      <div 
                        className="bg-indigo-500 h-full rounded-full transition-all duration-300"
                        style={{ width: `${stats?.average_mastery || 0}%` }}
                      ></div>
                    </div>
                  </div>

                  <div className="text-[10px] text-slate-500 leading-relaxed font-medium bg-slate-950/10 p-3 rounded-lg border border-slate-850">
                    Spaced repetition decays mastery scores daily. Conduct concept assessments to maintain your proficiency levels.
                  </div>
                </div>

                {/* 2. Weak concepts alert block */}
                <div className="p-6 border border-slate-800 bg-slate-900/10 rounded-2xl space-y-4 shadow-sm">
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider pb-2 border-b border-slate-850">
                    Target Weak Areas
                  </h3>

                  {stats?.weak_concepts && stats.weak_concepts.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {stats.weak_concepts.map((item) => (
                        <div 
                          key={item.concept_id} 
                          className="p-4 bg-rose-950/10 border border-rose-900/20 rounded-xl flex justify-between items-center space-x-3 hover:border-rose-900/40 transition cursor-pointer"
                          onClick={() => navigate('/assessment', { state: { preselectedConceptId: item.concept_id } })}
                        >
                          <div className="space-y-0.5">
                            <span className="font-bold text-xs text-white block">{item.concept_name}</span>
                            <span className="text-[9px] text-rose-300 uppercase font-black tracking-wider bg-rose-500/10 px-1.5 py-0.5 rounded border border-rose-500/10">
                              Score: {item.score.toFixed(0)}%
                            </span>
                          </div>
                          <button className="p-1.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 rounded-lg transition">
                            <Play size={10} />
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-4 bg-slate-950/20 border border-slate-850 rounded-xl text-center text-xs text-slate-500">
                      Great work! No weak concepts identified. Maintain study streaks to lock in mastery.
                    </div>
                  )}
                </div>

              </div>

              {/* Right Column: Next session, resources, achievements */}
              <div className="space-y-8">
                
                {/* 1. Spaced Repetition next review session */}
                {stats?.next_session_concept && (
                  <div className="p-6 border border-slate-800 bg-slate-900/10 rounded-2xl space-y-4 shadow-sm">
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider pb-2 border-b border-slate-850">
                      Next Study Session
                    </h3>
                    <div className="p-4 bg-indigo-950/10 border border-indigo-900/20 rounded-xl space-y-3">
                      <div className="space-y-1">
                        <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Concept Target</span>
                        <span className="font-extrabold text-white text-xs block">{stats.next_session_concept.concept_name}</span>
                      </div>
                      <button 
                        onClick={() => navigate('/assessment', { state: { preselectedConceptId: stats.next_session_concept.concept_id } })}
                        className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl flex items-center justify-center space-x-1.5 shadow-md"
                      >
                        <Play size={12} />
                        <span>Start Assessment Review</span>
                      </button>
                    </div>
                  </div>
                )}

                {/* 2. Recommended resources snippet */}
                {resources.length > 0 && (
                  <div className="p-6 border border-slate-800 bg-slate-900/10 rounded-2xl space-y-4 shadow-sm">
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider pb-2 border-b border-slate-850 flex items-center justify-between">
                      <span>Curated Guides</span>
                      <Link to="/resources" className="text-[10px] text-indigo-400 hover:text-indigo-300 font-bold">
                        Browse all
                      </Link>
                    </h3>
                    <div className="space-y-3">
                      {resources.map((res, ridx) => (
                        <a 
                          key={ridx} 
                          href={res.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="flex justify-between items-start p-3 bg-slate-950/20 border border-slate-850 hover:border-slate-700 rounded-xl transition text-xs group"
                        >
                          <div className="space-y-0.5 truncate pr-2">
                            <span className="font-bold text-white truncate block group-hover:text-indigo-300">{res.title}</span>
                            <span className="text-[10px] text-slate-500 font-medium">{res.source} • {res.trust_score}% trust</span>
                          </div>
                          <ExternalLink size={12} className="text-slate-500 mt-0.5 flex-shrink-0" />
                        </a>
                      ))}
                    </div>
                  </div>
                )}

                {/* 3. Achievements list */}
                {stats?.recent_achievements && stats.recent_achievements.length > 0 && (
                  <div className="p-6 border border-slate-800 bg-slate-900/10 rounded-2xl space-y-4 shadow-sm">
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider pb-2 border-b border-slate-850">
                      Recent Achievements
                    </h3>
                    <div className="space-y-2">
                      {stats.recent_achievements.map((ach, aidx) => (
                        <div key={aidx} className="flex items-center space-x-2.5 p-2 bg-slate-950/10 border border-slate-850 rounded-xl">
                          <Shield size={14} className="text-indigo-400 flex-shrink-0" />
                          <span className="text-[10.5px] text-slate-350 font-bold">{ach}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              </div>

            </div>
          )}
        </>
      )}

      {/* Diagnostics panel */}
      {health && (
        <div className="p-6 border border-slate-850 bg-slate-900/10 rounded-2xl space-y-4 select-all">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider pb-2 border-b border-slate-850 flex items-center space-x-1.5">
            <Activity size={12} />
            <span>Infrastructure Status</span>
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-[11px]">
            <div className="flex justify-between items-center bg-slate-950/20 p-2.5 rounded-lg border border-slate-850">
              <span className="text-slate-500">FastAPI API:</span>
              <span className="text-emerald-400 font-bold uppercase">Online</span>
            </div>
            <div className="flex justify-between items-center bg-slate-950/20 p-2.5 rounded-lg border border-slate-850">
              <span className="text-slate-500">Database connection:</span>
              <span className={health.database_online ? "text-emerald-400 font-bold uppercase" : "text-amber-400 font-bold uppercase"}>
                {health.database_online ? 'Atlas Connected' : 'Atlas Offline'}
              </span>
            </div>
            <div className="flex justify-between items-center bg-slate-950/20 p-2.5 rounded-lg border border-slate-850">
              <span className="text-slate-500">System Mode:</span>
              <span className={health.demo_mode ? "text-amber-400 font-bold uppercase" : "text-indigo-400 font-bold uppercase"}>
                {health.demo_mode ? 'Demo Mode Active' : 'Live Production'}
              </span>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}
