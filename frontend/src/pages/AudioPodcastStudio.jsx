import React, { useState, useEffect, useRef } from 'react'
import { useAuth } from '@clerk/react'
import { 
  Headphones, 
  Play, 
  Pause, 
  Square, 
  RotateCcw, 
  Volume2, 
  VolumeX, 
  Sparkles, 
  Radio, 
  Trash2, 
  Clock, 
  Users, 
  MessageSquare, 
  FileText, 
  AlertCircle, 
  CheckCircle2, 
  RotateCw, 
  FastForward,
  SkipForward,
  SkipBack,
  Download,
  Share2
} from 'lucide-react'

export default function AudioPodcastStudio() {
  const { getToken } = useAuth()

  // Data state
  const [podcasts, setPodcasts] = useState([])
  const [materials, setMaterials] = useState([])
  const [selectedPodcast, setSelectedPodcast] = useState(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)

  // Audio Playback state
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTurnIdx, setCurrentTurnIdx] = useState(0)
  const [speechRate, setSpeechRate] = useState(1.0)
  const [isMuted, setIsMuted] = useState(false)
  const [selectedStyle, setSelectedStyle] = useState('dynamic')
  const [selectedMaterialId, setSelectedMaterialId] = useState('')
  const [showGenModal, setShowGenModal] = useState(false)

  // Voice synthesis refs
  const synthRef = useRef(null)
  const activeUtteranceRef = useRef(null)
  const activeTurnRef = useRef(0)

  useEffect(() => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      synthRef.current = window.speechSynthesis
    }
    fetchInitialData()

    return () => {
      stopAudioPlayback()
    }
  }, [])

  useEffect(() => {
    activeTurnRef.current = currentTurnIdx
  }, [currentTurnIdx])

  const fetchInitialData = async () => {
    setLoading(true)
    setError(null)
    try {
      const token = await getToken()
      const headers = { Authorization: `Bearer ${token}` }

      const [podRes, matRes] = await Promise.all([
        fetch('http://localhost:8000/api/podcasts', { headers }),
        fetch('http://localhost:8000/api/materials', { headers })
      ])

      if (matRes.ok) {
        const matData = await matRes.json()
        setMaterials(matData)
        if (matData.length > 0 && !selectedMaterialId) {
          setSelectedMaterialId(matData[0]._id || matData[0].id)
        }
      }

      if (podRes.ok) {
        const podData = await podRes.json()
        setPodcasts(podData)
        if (podData.length > 0) {
          setSelectedPodcast(podData[0])
        }
      }
    } catch (err) {
      console.error('Failed to load podcasts:', err)
      setError('Could not connect to backend.')
    } finally {
      setLoading(false)
    }
  }

  // --- TTS Multi-Speaker Audio Player Logic ---

  const speakTurn = (turnIdx, script) => {
    if (!synthRef.current || !script || turnIdx >= script.length) {
      setIsPlaying(false)
      setCurrentTurnIdx(0)
      return
    }

    synthRef.current.cancel()
    const turn = script[turnIdx]
    const utterance = new SpeechSynthesisUtterance(turn.text)
    
    // Choose voices: distinguish Alex (male/lower) and Sam (female/higher)
    const voices = synthRef.current.getVoices()
    if (voices.length > 0) {
      if (turn.speaker === 'Sam') {
        const femaleVoice = voices.find(v => v.name.toLowerCase().includes('female') || v.name.toLowerCase().includes('zira') || v.name.toLowerCase().includes('samantha') || v.name.toLowerCase().includes('google us english') || v.lang.includes('en'))
        if (femaleVoice) utterance.voice = femaleVoice
        utterance.pitch = (turn.pitch || 1.05) * 1.15
      } else {
        const maleVoice = voices.find(v => v.name.toLowerCase().includes('male') || v.name.toLowerCase().includes('david') || v.name.toLowerCase().includes('alex') || v.lang.includes('en'))
        if (maleVoice) utterance.voice = maleVoice
        utterance.pitch = (turn.pitch || 0.95) * 0.9
      }
    }

    utterance.rate = speechRate * (turn.rate || 1.0)
    utterance.volume = isMuted ? 0 : 1

    utterance.onend = () => {
      if (activeTurnRef.current + 1 < script.length) {
        setCurrentTurnIdx(prev => prev + 1)
        speakTurn(activeTurnRef.current + 1, script)
      } else {
        setIsPlaying(false)
        setCurrentTurnIdx(0)
      }
    }

    utterance.onerror = (e) => {
      console.warn('SpeechSynthesis error:', e)
      setIsPlaying(false)
    }

    activeUtteranceRef.current = utterance
    synthRef.current.speak(utterance)
  }

  const handlePlayToggle = () => {
    if (!selectedPodcast || !selectedPodcast.script || selectedPodcast.script.length === 0) return

    if (isPlaying) {
      synthRef.current?.cancel()
      setIsPlaying(false)
    } else {
      setIsPlaying(true)
      speakTurn(currentTurnIdx, selectedPodcast.script)
    }
  }

  const stopAudioPlayback = () => {
    synthRef.current?.cancel()
    setIsPlaying(false)
    setCurrentTurnIdx(0)
  }

  const handleSkipNext = () => {
    if (!selectedPodcast?.script) return
    const nextIdx = Math.min(currentTurnIdx + 1, selectedPodcast.script.length - 1)
    setCurrentTurnIdx(nextIdx)
    if (isPlaying) {
      speakTurn(nextIdx, selectedPodcast.script)
    }
  }

  const handleSkipPrev = () => {
    if (!selectedPodcast?.script) return
    const prevIdx = Math.max(currentTurnIdx - 1, 0)
    setCurrentTurnIdx(prevIdx)
    if (isPlaying) {
      speakTurn(prevIdx, selectedPodcast.script)
    }
  }

  const handleJumpToTurn = (idx) => {
    setCurrentTurnIdx(idx)
    if (isPlaying) {
      speakTurn(idx, selectedPodcast.script)
    }
  }

  const handleGeneratePodcast = async () => {
    setGenerating(true)
    setError(null)
    setSuccessMsg(null)
    try {
      const token = await getToken()
      const res = await fetch('http://localhost:8000/api/podcasts/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          material_id: selectedMaterialId || undefined,
          style: selectedStyle
        })
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Podcast synthesis failed')

      setSuccessMsg(`Episode "${data.podcast.title}" synthesized successfully! (+20 XP)`)
      setShowGenModal(false)
      await fetchInitialData()
      if (data.podcast) {
        setSelectedPodcast(data.podcast)
        stopAudioPlayback()
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setGenerating(false)
    }
  }

  const handleDeletePodcast = async (podId, e) => {
    e?.stopPropagation()
    if (!window.confirm('Delete this synthesized audio podcast episode?')) return

    try {
      const token = await getToken()
      const res = await fetch(`http://localhost:8000/api/podcasts/${podId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        stopAudioPlayback()
        const remaining = podcasts.filter(p => (p._id || p.id) !== podId)
        setPodcasts(remaining)
        setSelectedPodcast(remaining.length > 0 ? remaining[0] : null)
      }
    } catch (err) {
      console.error('Delete podcast error:', err)
    }
  }

  return (
    <div className="space-y-6 animate-fade-in pb-16">
      
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-tr from-amber-500 via-orange-600 to-red-600 text-white shadow-lg shadow-orange-500/20">
            <Radio className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white flex items-center gap-2">
              Audio Podcast Studio
              <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                NotebookLM-Style Deep Dive
              </span>
            </h1>
            <p className="text-sm text-slate-400 mt-0.5">
              Turn lecture notes and PDFs into captivating two-host AI conversational podcasts with live voice playback.
            </p>
          </div>
        </div>

        <button
          onClick={() => setShowGenModal(true)}
          className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-white font-bold text-xs shadow-md shadow-orange-600/20 active:scale-95 transition-all cursor-pointer"
        >
          <Sparkles size={14} />
          <span>Synthesize New Episode</span>
        </button>
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
          <RotateCw className="h-8 w-8 animate-spin mx-auto text-amber-500" />
          <p className="text-sm font-medium">Loading podcast library...</p>
        </div>
      ) : podcasts.length === 0 ? (
        <div className="p-16 rounded-2xl bg-slate-900/40 border border-dashed border-slate-800 text-center space-y-4">
          <div className="w-16 h-16 rounded-full bg-amber-500/10 text-amber-400 flex items-center justify-center mx-auto shadow-inner">
            <Headphones size={32} />
          </div>
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-white">No Podcast Episodes Generated Yet</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Synthesize a multi-host conversational deep-dive audio overview from your uploaded study materials.
            </p>
          </div>
          <button
            onClick={() => setShowGenModal(true)}
            className="px-5 py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs shadow-lg shadow-amber-600/20 cursor-pointer"
          >
            Synthesize Your First Episode
          </button>
        </div>
      ) : (
        /* Main Two-Column Podcast Player & Script Studio */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Left Column: Episodes Shelf */}
          <div className="lg:col-span-4 space-y-4">
            <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-2xl space-y-3">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
                Episode Library ({podcasts.length})
              </span>

              <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
                {podcasts.map((pod) => {
                  const pId = pod._id || pod.id
                  const isSelected = (selectedPodcast?._id || selectedPodcast?.id) === pId
                  return (
                    <div
                      key={pId}
                      onClick={() => {
                        stopAudioPlayback()
                        setSelectedPodcast(pod)
                      }}
                      className={`p-4 rounded-xl border transition-all cursor-pointer relative group ${
                        isSelected 
                          ? 'bg-gradient-to-r from-amber-950/40 to-orange-950/40 border-amber-500/50 shadow-lg shadow-amber-500/10' 
                          : 'bg-slate-950/40 border-slate-850 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          {pod.episode_duration_est_minutes} min Overview
                        </span>
                        <button
                          onClick={(e) => handleDeletePodcast(pId, e)}
                          className="text-slate-500 hover:text-red-400 p-1 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                          title="Delete Episode"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>

                      <h4 className="text-sm font-bold text-white line-clamp-1">{pod.title}</h4>
                      <p className="text-[11px] text-slate-400 line-clamp-2 mt-1 leading-relaxed">
                        {pod.summary}
                      </p>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Right Column: Audio Stage & Interactive Script */}
          {selectedPodcast && (
            <div className="lg:col-span-8 space-y-6">
              
              {/* ─── AUDIO PLAYER STAGE ─── */}
              <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-amber-950/30 border border-slate-800 shadow-2xl relative overflow-hidden">
                <div className="absolute top-0 right-0 w-64 h-64 bg-amber-500/5 rounded-full blur-3xl pointer-events-none" />

                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-bold text-amber-400 uppercase tracking-wider">
                        {selectedPodcast.material_title || 'Curriculum Overview'}
                      </span>
                      <span className="text-slate-600">•</span>
                      <span className="text-[11px] text-slate-400 flex items-center gap-1">
                        <Users size={12} /> Alex & Sam
                      </span>
                    </div>
                    <h2 className="text-2xl font-black text-white tracking-tight">{selectedPodcast.title}</h2>
                  </div>

                  {/* Speed & Audio controls */}
                  <div className="flex items-center space-x-2 bg-slate-950/80 p-1.5 rounded-xl border border-slate-800">
                    <button
                      onClick={() => setIsMuted(!isMuted)}
                      className="p-2 text-slate-400 hover:text-white transition cursor-pointer"
                      title={isMuted ? "Unmute" : "Mute"}
                    >
                      {isMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
                    </button>
                    <select
                      value={speechRate}
                      onChange={(e) => setSpeechRate(parseFloat(e.target.value))}
                      className="bg-transparent text-xs font-bold text-amber-400 focus:outline-none cursor-pointer"
                    >
                      <option value="0.8">0.8x</option>
                      <option value="1.0">1.0x</option>
                      <option value="1.2">1.2x</option>
                      <option value="1.5">1.5x</option>
                    </select>
                  </div>
                </div>

                {/* Progress Bar & Host Avatars */}
                <div className="py-6 space-y-4">
                  
                  {/* Visual Waveform Animation */}
                  <div className="flex items-center justify-center space-x-1.5 h-12 bg-slate-950/50 rounded-xl border border-slate-800/80 px-4">
                    {Array.from({ length: 32 }).map((_, i) => (
                      <div
                        key={i}
                        className={`w-1 rounded-full transition-all duration-200 ${
                          isPlaying 
                            ? 'bg-gradient-to-t from-amber-500 to-orange-500 animate-pulse' 
                            : 'bg-slate-800 h-2'
                        }`}
                        style={{
                          height: isPlaying ? `${Math.sin(i + currentTurnIdx) * 18 + 24}px` : '6px'
                        }}
                      />
                    ))}
                  </div>

                  {/* Player Controls */}
                  <div className="flex items-center justify-center space-x-4 pt-2">
                    <button
                      onClick={handleSkipPrev}
                      className="p-3 rounded-full bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-750 transition active:scale-95 cursor-pointer"
                      title="Previous Turn"
                    >
                      <SkipBack size={18} />
                    </button>

                    <button
                      onClick={handlePlayToggle}
                      className="p-4 rounded-full bg-gradient-to-tr from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-white shadow-xl shadow-orange-600/30 transition-all active:scale-95 cursor-pointer"
                    >
                      {isPlaying ? <Pause size={24} /> : <Play size={24} className="ml-0.5" />}
                    </button>

                    <button
                      onClick={stopAudioPlayback}
                      className="p-3 rounded-full bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-750 transition active:scale-95 cursor-pointer"
                      title="Stop"
                    >
                      <Square size={18} />
                    </button>

                    <button
                      onClick={handleSkipNext}
                      className="p-3 rounded-full bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-750 transition active:scale-95 cursor-pointer"
                      title="Next Turn"
                    >
                      <SkipForward size={18} />
                    </button>
                  </div>

                  <div className="text-center text-xs text-slate-400 font-mono">
                    Turn {currentTurnIdx + 1} of {selectedPodcast.script?.length || 0}
                  </div>
                </div>
              </div>

              {/* ─── INTERACTIVE CONVERSATION SCRIPT ─── */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <span className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                    <MessageSquare size={14} className="text-amber-400" /> Interactive Dialogue Script
                  </span>
                  <span className="text-[11px] text-slate-500">Click any dialogue line to jump audio</span>
                </div>

                <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
                  {(selectedPodcast.script || []).map((turn, idx) => {
                    const isCurrent = currentTurnIdx === idx && isPlaying
                    const isAlex = turn.speaker === 'Alex'
                    return (
                      <div
                        key={idx}
                        onClick={() => handleJumpToTurn(idx)}
                        className={`p-4 rounded-xl border transition-all cursor-pointer flex items-start gap-3 ${
                          isCurrent 
                            ? 'bg-amber-600/20 border-amber-500 shadow-md shadow-amber-500/10' 
                            : 'bg-slate-950/60 border-slate-850 hover:border-slate-700'
                        }`}
                      >
                        <div 
                          className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold text-white shadow-md ${
                            isAlex ? 'bg-indigo-600' : 'bg-purple-600'
                          }`}
                        >
                          {isAlex ? 'A' : 'S'}
                        </div>

                        <div className="space-y-1 flex-1">
                          <div className="flex items-center justify-between">
                            <span className={`text-xs font-bold ${isAlex ? 'text-indigo-400' : 'text-purple-400'}`}>
                              {turn.speaker} {isAlex ? '(Lead Researcher)' : '(Explorer)'}
                            </span>
                            <span className="text-[10px] text-slate-500 font-mono capitalize">
                              {turn.emotion}
                            </span>
                          </div>

                          <p className={`text-xs leading-relaxed font-normal ${isCurrent ? 'text-white font-medium' : 'text-slate-300'}`}>
                            {turn.text}
                          </p>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

            </div>
          )}

        </div>
      )}

      {/* ─── SYNTHESIZE PODCAST MODAL ─── */}
      {showGenModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-lg w-full space-y-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center space-x-2.5">
                <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  <Radio size={18} />
                </div>
                <h3 className="text-lg font-bold text-white">Synthesize Two-Host Audio Podcast</h3>
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
                  Select Target Source Material
                </label>
                <select
                  value={selectedMaterialId}
                  onChange={(e) => setSelectedMaterialId(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-amber-500"
                >
                  <option value="">General Curriculum Grounding</option>
                  {materials.map(m => (
                    <option key={m._id || m.id} value={m._id || m.id}>{m.title}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Podcast Discussion Tone
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { id: 'dynamic', label: 'Dynamic & Lively', desc: 'Energetic & clear' },
                    { id: 'academic', label: 'Deep Analytical', desc: 'Rigorous insights' },
                    { id: 'exam_prep', label: 'Rapid Exam Prep', desc: 'High yield tips' }
                  ].map((style) => (
                    <button
                      key={style.id}
                      type="button"
                      onClick={() => setSelectedStyle(style.id)}
                      className={`p-2.5 rounded-xl border text-left transition-all cursor-pointer ${
                        selectedStyle === style.id 
                          ? 'bg-amber-600/20 border-amber-500 text-white' 
                          : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:bg-slate-900'
                      }`}
                    >
                      <div className="font-bold text-xs">{style.label}</div>
                      <div className="text-[10px] text-slate-500">{style.desc}</div>
                    </button>
                  ))}
                </div>
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
                onClick={handleGeneratePodcast}
                disabled={generating}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-white font-bold text-xs flex items-center space-x-2 transition-all shadow-md shadow-orange-600/20 disabled:opacity-50 cursor-pointer"
              >
                {generating ? (
                  <>
                    <RotateCw className="h-3.5 w-3.5 animate-spin" />
                    <span>Synthesizing Podcast Episode...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="h-3.5 w-3.5" />
                    <span>Generate Episode</span>
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
