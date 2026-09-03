import React, { useState, useEffect } from 'react'
import { useAuth } from '@clerk/react'
import { 
  Layers, 
  Sparkles, 
  RotateCw, 
  CheckCircle2, 
  XCircle, 
  Flame, 
  Brain, 
  Clock, 
  Plus, 
  Trash2, 
  ArrowRight, 
  ArrowLeft,
  BookOpen,
  Zap,
  Filter,
  BarChart3,
  Calendar,
  AlertCircle
} from 'lucide-react'

export default function Flashcards() {
  const { getToken } = useAuth()
  
  // State
  const [flashcards, setFlashcards] = useState([])
  const [dueCards, setDueCards] = useState([])
  const [concepts, setConcepts] = useState([])
  const [materials, setMaterials] = useState([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)
  
  // Study / Review Mode
  const [studyMode, setStudyMode] = useState(false)
  const [studyDeck, setStudyDeck] = useState([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isFlipped, setIsFlipped] = useState(false)
  const [studySessionStats, setStudySessionStats] = useState({ reviewed: 0, xpEarned: 0, correct: 0 })
  const [sessionCompleted, setSessionCompleted] = useState(false)
  
  // Filter state
  const [selectedConcept, setSelectedConcept] = useState('all')
  const [selectedState, setSelectedState] = useState('all')
  
  // Generation Modal / Panel state
  const [showGenModal, setShowGenModal] = useState(false)
  const [genSelectedConcepts, setGenSelectedConcepts] = useState([])
  const [cardsPerConcept, setCardsPerConcept] = useState(2)

  useEffect(() => {
    fetchInitialData()
  }, [])

  const fetchInitialData = async () => {
    setLoading(true)
    setError(null)
    try {
      const token = await getToken()
      const headers = { Authorization: `Bearer ${token}` }
      
      const [cardsRes, dueRes, conceptsRes, matsRes] = await Promise.all([
        fetch('http://localhost:8000/api/flashcards', { headers }),
        fetch('http://localhost:8000/api/flashcards/due', { headers }),
        fetch('http://localhost:8000/api/concepts', { headers }),
        fetch('http://localhost:8000/api/materials', { headers })
      ])
      
      if (cardsRes.ok) setFlashcards(await cardsRes.json())
      if (dueRes.ok) setDueCards(await dueRes.json())
      if (conceptsRes.ok) setConcepts(await conceptsRes.json())
      if (matsRes.ok) setMaterials(await matsRes.json())
    } catch (err) {
      console.error('Failed to load flashcard ecosystem:', err)
      setError('Could not connect to the backend server. Please make sure it is running.')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateFlashcards = async () => {
    setGenerating(true)
    setError(null)
    setSuccessMsg(null)
    try {
      const token = await getToken()
      const res = await fetch('http://localhost:8000/api/flashcards/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          concept_ids: genSelectedConcepts.length > 0 ? genSelectedConcepts : undefined,
          cards_per_concept: cardsPerConcept,
          include_scenarios: true
        })
      })
      
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to generate flashcards')
      }
      
      setSuccessMsg(`Successfully generated ${data.count} high-yield active-recall flashcards!`)
      setShowGenModal(false)
      setGenSelectedConcepts([])
      await fetchInitialData()
    } catch (err) {
      setError(err.message)
    } finally {
      setGenerating(false)
    }
  }

  const handleDeleteCard = async (cardId, e) => {
    e?.stopPropagation()
    if (!window.confirm('Are you sure you want to delete this flashcard?')) return
    
    try {
      const token = await getToken()
      const res = await fetch(`http://localhost:8000/api/flashcards/${cardId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        setFlashcards(prev => prev.filter(c => (c._id || c.id) !== cardId))
        setDueCards(prev => prev.filter(c => (c._id || c.id) !== cardId))
      }
    } catch (err) {
      console.error('Delete error:', err)
    }
  }

  // Start Study Session
  const startSession = (cardsToStudy) => {
    if (!cardsToStudy || cardsToStudy.length === 0) return
    setStudyDeck(cardsToStudy)
    setCurrentIndex(0)
    setIsFlipped(false)
    setStudySessionStats({ reviewed: 0, xpEarned: 0, correct: 0 })
    setSessionCompleted(false)
    setStudyMode(true)
  }

  // Submit SM-2 Rating (1: Again, 2: Hard, 3: Good, 4: Easy)
  const handleReviewRating = async (rating) => {
    const currentCard = studyDeck[currentIndex]
    if (!currentCard || actionLoading) return
    
    setActionLoading(true)
    const cardId = currentCard._id || currentCard.id
    
    try {
      const token = await getToken()
      const res = await fetch('http://localhost:8000/api/flashcards/review', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          card_id: cardId,
          rating: rating,
          response_time_seconds: 5.0
        })
      })
      
      const data = await res.json()
      if (res.ok) {
        const isSuccess = data.is_correct
        setStudySessionStats(prev => ({
          reviewed: prev.reviewed + 1,
          xpEarned: prev.xpEarned + (data.xp_earned || 0),
          correct: prev.correct + (isSuccess ? 1 : 0)
        }))
        
        // Progress to next card
        if (currentIndex + 1 < studyDeck.length) {
          setIsFlipped(false)
          setCurrentIndex(prev => prev + 1)
        } else {
          setSessionCompleted(true)
          fetchInitialData() // refresh background state
        }
      }
    } catch (err) {
      console.error('Failed to submit review:', err)
    } finally {
      setActionLoading(false)
    }
  }

  // Filtered Flashcards
  const filteredCards = flashcards.filter(c => {
    if (selectedConcept !== 'all' && c.concept_name !== selectedConcept && c.concept_id !== selectedConcept) {
      return false
    }
    if (selectedState !== 'all' && c.state !== selectedState) {
      return false
    }
    return true
  })

  return (
    <div className="space-y-8 animate-fade-in pb-12">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-500/20">
              <Layers className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white flex items-center gap-2">
                Active Recall & Flashcards
                <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  SM-2 Spaced Repetition
                </span>
              </h1>
              <p className="text-sm text-slate-400 mt-0.5">
                Supercharge long-term memory retention with AI-mined conceptual flashcards.
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
            <span>Generate Flashcards</span>
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

      {/* ─── ACTIVE STUDY SESSION OVERLAY / VIEW ─── */}
      {studyMode ? (
        <div className="max-w-3xl mx-auto space-y-6">
          {!sessionCompleted ? (
            <>
              {/* Session Progress Header */}
              <div className="flex items-center justify-between px-2 text-sm text-slate-400">
                <button 
                  onClick={() => setStudyMode(false)}
                  className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors cursor-pointer"
                >
                  <ArrowLeft size={14} /> Exit Study Session
                </button>
                <div className="flex items-center space-x-4">
                  <span className="font-semibold text-white">
                    Card {currentIndex + 1} of {studyDeck.length}
                  </span>
                  <div className="w-32 bg-slate-800 rounded-full h-2 overflow-hidden">
                    <div 
                      className="bg-indigo-500 h-full transition-all duration-300 rounded-full"
                      style={{ width: `${((currentIndex + 1) / studyDeck.length) * 100}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* 3D Flip Card Container */}
              <div 
                onClick={() => setIsFlipped(!isFlipped)}
                className="relative min-h-[380px] w-full rounded-2xl cursor-pointer select-none transition-all duration-300"
                style={{ perspective: '1000px' }}
              >
                <div 
                  className={`w-full min-h-[380px] rounded-2xl p-8 border transition-all duration-500 flex flex-col justify-between shadow-2xl relative ${
                    isFlipped 
                      ? 'bg-slate-900/95 border-purple-500/30 text-white shadow-purple-500/10' 
                      : 'bg-slate-900/90 border-slate-800 text-white shadow-indigo-500/10 hover:border-slate-700'
                  }`}
                >
                  {/* Card Top Metadata */}
                  <div className="flex items-center justify-between border-b border-slate-800/60 pb-3">
                    <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-slate-800 text-indigo-400 border border-slate-700/50 flex items-center gap-1.5">
                      <Brain size={12} />
                      {studyDeck[currentIndex]?.concept_name || 'Concept'}
                    </span>
                    <span className="text-xs font-medium text-slate-400 flex items-center gap-1">
                      <Clock size={12} />
                      {isFlipped ? 'Answer / Explanation' : 'Click card to flip'}
                    </span>
                  </div>

                  {/* Card Body */}
                  <div className="my-auto py-8 text-center">
                    {!isFlipped ? (
                      <div className="space-y-4">
                        <span className="text-xs font-bold uppercase tracking-widest text-indigo-400/80">Question / Prompt</span>
                        <h2 className="text-xl md:text-2xl font-bold leading-relaxed text-slate-100 max-w-xl mx-auto">
                          {studyDeck[currentIndex]?.front}
                        </h2>
                      </div>
                    ) : (
                      <div className="space-y-4 animate-fade-in text-left">
                        <span className="text-xs font-bold uppercase tracking-widest text-purple-400/80">High-Yield Answer</span>
                        <div className="text-base md:text-lg text-slate-200 leading-relaxed whitespace-pre-line bg-slate-950/40 p-5 rounded-xl border border-slate-800/60">
                          {studyDeck[currentIndex]?.back}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Card Footer Hint */}
                  <div className="text-center pt-3 border-t border-slate-800/60 text-xs text-slate-500 flex items-center justify-center gap-1.5">
                    <RotateCw size={12} className={isFlipped ? 'text-purple-400' : 'text-indigo-400'} />
                    {isFlipped ? 'Select your recall difficulty below' : 'Click anywhere on this card to reveal answer'}
                  </div>
                </div>
              </div>

              {/* SM-2 Recall Rating Controls (Visible when Flipped) */}
              {isFlipped ? (
                <div className="space-y-2 animate-fade-in">
                  <p className="text-center text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Rate Your Active Recall (SM-2 Interval Scheduling)
                  </p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <button
                      onClick={() => handleReviewRating(1)}
                      disabled={actionLoading}
                      className="p-3.5 rounded-xl bg-red-950/30 hover:bg-red-900/40 border border-red-500/30 text-red-300 flex flex-col items-center justify-center transition-all active:scale-95 cursor-pointer"
                    >
                      <span className="font-bold text-sm">1. Again</span>
                      <span className="text-[11px] text-red-400/70 mt-0.5">Reset (1d)</span>
                    </button>
                    
                    <button
                      onClick={() => handleReviewRating(2)}
                      disabled={actionLoading}
                      className="p-3.5 rounded-xl bg-amber-950/30 hover:bg-amber-900/40 border border-amber-500/30 text-amber-300 flex flex-col items-center justify-center transition-all active:scale-95 cursor-pointer"
                    >
                      <span className="font-bold text-sm">2. Hard</span>
                      <span className="text-[11px] text-amber-400/70 mt-0.5">Hesitated (3d)</span>
                    </button>
                    
                    <button
                      onClick={() => handleReviewRating(3)}
                      disabled={actionLoading}
                      className="p-3.5 rounded-xl bg-indigo-950/40 hover:bg-indigo-900/50 border border-indigo-500/30 text-indigo-300 flex flex-col items-center justify-center transition-all active:scale-95 cursor-pointer shadow-lg shadow-indigo-950/50"
                    >
                      <span className="font-bold text-sm">3. Good</span>
                      <span className="text-[11px] text-indigo-400/70 mt-0.5">Accurate (6d)</span>
                    </button>
                    
                    <button
                      onClick={() => handleReviewRating(4)}
                      disabled={actionLoading}
                      className="p-3.5 rounded-xl bg-emerald-950/30 hover:bg-emerald-900/40 border border-emerald-500/30 text-emerald-300 flex flex-col items-center justify-center transition-all active:scale-95 cursor-pointer shadow-lg shadow-emerald-950/50"
                    >
                      <span className="font-bold text-sm">4. Easy</span>
                      <span className="text-[11px] text-emerald-400/70 mt-0.5">Instant (+10 XP)</span>
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex justify-center">
                  <button
                    onClick={() => setIsFlipped(true)}
                    className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm shadow-lg shadow-indigo-600/20 flex items-center space-x-2 transition-all active:scale-95 cursor-pointer"
                  >
                    <span>Show Answer</span>
                    <ArrowRight size={16} />
                  </button>
                </div>
              )}
            </>
          ) : (
            /* Session Completed Summary Screen */
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-8 text-center space-y-6 shadow-2xl animate-scale-in">
              <div className="w-16 h-16 mx-auto rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
                <CheckCircle2 size={36} />
              </div>
              
              <div className="space-y-2">
                <h2 className="text-2xl font-bold text-white">Spaced Repetition Session Completed!</h2>
                <p className="text-slate-400 text-sm max-w-md mx-auto">
                  Your cognitive retention model has been updated. Concepts reviewed have received updated Bayesian mastery scores.
                </p>
              </div>

              <div className="grid grid-cols-3 gap-4 max-w-lg mx-auto">
                <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800/80">
                  <div className="text-2xl font-bold text-white">{studySessionStats.reviewed}</div>
                  <div className="text-xs text-slate-400 mt-1">Cards Reviewed</div>
                </div>
                <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800/80">
                  <div className="text-2xl font-bold text-emerald-400">
                    {studySessionStats.reviewed > 0 ? Math.round((studySessionStats.correct / studySessionStats.reviewed) * 100) : 0}%
                  </div>
                  <div className="text-xs text-slate-400 mt-1">Retention Rate</div>
                </div>
                <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800/80">
                  <div className="text-2xl font-bold text-amber-400 flex items-center justify-center gap-1">
                    <Zap size={18} />
                    +{studySessionStats.xpEarned}
                  </div>
                  <div className="text-xs text-slate-400 mt-1">XP Earned</div>
                </div>
              </div>

              <div className="flex justify-center gap-4 pt-4">
                <button
                  onClick={() => setStudyMode(false)}
                  className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-all shadow-md shadow-indigo-600/20 cursor-pointer"
                >
                  Return to Flashcard Decks
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* ─── FLASHCARD DASHBOARD & DECK VIEW ─── */
        <>
          {/* Quick Stats Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Flashcards</span>
                <p className="text-2xl font-bold text-white mt-1">{flashcards.length}</p>
              </div>
              <div className="p-3 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                <Layers size={22} />
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Due For Review Today</span>
                <p className="text-2xl font-bold text-amber-400 mt-1">{dueCards.length}</p>
              </div>
              <div className="p-3 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <Flame size={22} />
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Mastered Cards</span>
                <p className="text-2xl font-bold text-emerald-400 mt-1">
                  {flashcards.filter(c => c.state === 'mastered').length}
                </p>
              </div>
              <div className="p-3 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 size={22} />
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Concepts Covered</span>
                <p className="text-2xl font-bold text-purple-400 mt-1">
                  {new Set(flashcards.map(c => c.concept_name)).size}
                </p>
              </div>
              <div className="p-3 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
                <Brain size={22} />
              </div>
            </div>
          </div>

          {/* Due Review Spotlight Banner */}
          {dueCards.length > 0 && (
            <div className="p-6 rounded-2xl bg-gradient-to-r from-amber-500/10 via-indigo-500/10 to-purple-500/10 border border-amber-500/20 flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="flex items-center space-x-4">
                <div className="p-3 rounded-xl bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  <Flame size={26} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">
                    {dueCards.length} Spaced Repetition {dueCards.length === 1 ? 'Card is' : 'Cards are'} Due Today!
                  </h3>
                  <p className="text-xs text-slate-300 mt-0.5">
                    Reviewing now prevents forgetting curve decay and strengthens your long-term memory retrieval strength.
                  </p>
                </div>
              </div>

              <button
                onClick={() => startSession(dueCards)}
                className="px-6 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-sm transition-all shadow-lg shadow-amber-500/20 whitespace-nowrap active:scale-95 cursor-pointer"
              >
                Start Spaced Review ({dueCards.length})
              </button>
            </div>
          )}

          {/* Flashcard Library Filter Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-900/40 p-4 rounded-xl border border-slate-800">
            <div className="flex items-center space-x-2 text-sm text-slate-400">
              <Filter size={16} />
              <span className="font-semibold text-slate-200">Filter Library:</span>
            </div>

            <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
              <select
                value={selectedConcept}
                onChange={(e) => setSelectedConcept(e.target.value)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="all">All Concepts ({concepts.length})</option>
                {concepts.map(c => (
                  <option key={c._id || c.id} value={c.name}>{c.name}</option>
                ))}
              </select>

              <select
                value={selectedState}
                onChange={(e) => setSelectedState(e.target.value)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="all">All States</option>
                <option value="new">New</option>
                <option value="learning">Learning</option>
                <option value="review">Review</option>
                <option value="mastered">Mastered</option>
              </select>

              {filteredCards.length > 0 && (
                <button
                  onClick={() => startSession(filteredCards)}
                  className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs flex items-center space-x-1.5 transition-all shadow cursor-pointer ml-auto sm:ml-0"
                >
                  <Brain size={14} />
                  <span>Practice Deck ({filteredCards.length})</span>
                </button>
              )}
            </div>
          </div>

          {/* Flashcard Cards Grid */}
          {loading ? (
            <div className="p-12 text-center text-slate-500 space-y-2">
              <RotateCw className="h-6 w-6 animate-spin mx-auto text-indigo-400" />
              <p className="text-sm">Loading flashcard library...</p>
            </div>
          ) : filteredCards.length === 0 ? (
            <div className="p-12 rounded-2xl bg-slate-900/30 border border-dashed border-slate-800 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-indigo-500/10 text-indigo-400 flex items-center justify-center mx-auto">
                <Layers size={24} />
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-semibold text-white">No flashcards found</h3>
                <p className="text-xs text-slate-400 max-w-sm mx-auto">
                  Generate active recall flashcards from your extracted knowledge concepts to start spaced-repetition training.
                </p>
              </div>
              <button
                onClick={() => setShowGenModal(true)}
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-md shadow-indigo-600/20 cursor-pointer"
              >
                Generate First Flashcard Deck
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredCards.map((card) => {
                const cardId = card._id || card.id
                return (
                  <div
                    key={cardId}
                    className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-all flex flex-col justify-between space-y-4 group relative overflow-hidden"
                  >
                    <div className="space-y-2.5">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 truncate max-w-[180px]">
                          {card.concept_name}
                        </span>
                        
                        <div className="flex items-center space-x-2">
                          <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                            card.state === 'mastered' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                            card.state === 'learning' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                            'bg-slate-800 text-slate-400'
                          }`}>
                            {card.state || 'new'}
                          </span>
                          
                          <button
                            onClick={(e) => handleDeleteCard(cardId, e)}
                            className="text-slate-500 hover:text-red-400 p-1 rounded transition-colors opacity-0 group-hover:opacity-100 cursor-pointer"
                            title="Delete card"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </div>

                      <h4 className="text-sm font-semibold text-slate-100 line-clamp-3 leading-snug">
                        {card.front}
                      </h4>
                    </div>

                    <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500">
                      <div className="flex items-center space-x-2">
                        <span>Ease: {card.ease_factor || 2.5}</span>
                        <span>•</span>
                        <span>Interval: {card.interval_days || 1}d</span>
                      </div>

                      <button
                        onClick={() => startSession([card])}
                        className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1 cursor-pointer"
                      >
                        Study <ArrowRight size={12} />
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </>
      )}

      {/* ─── GENERATE FLASHCARDS MODAL ─── */}
      {showGenModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-lg w-full space-y-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center space-x-2.5">
                <div className="p-2 rounded-lg bg-indigo-600/10 text-indigo-400 border border-indigo-500/20">
                  <Sparkles size={18} />
                </div>
                <h3 className="text-lg font-bold text-white">Generate Conceptual Flashcards</h3>
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
                  Select Concepts to Mine ({concepts.length} Available)
                </label>
                <div className="max-h-48 overflow-y-auto space-y-1.5 bg-slate-950/60 p-2.5 rounded-xl border border-slate-800">
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
                  {genSelectedConcepts.length === 0 ? 'Generating for all top concepts by default' : `Selected ${genSelectedConcepts.length} concepts`}
                </p>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Cards per Concept
                </label>
                <input
                  type="number"
                  min="1"
                  max="5"
                  value={cardsPerConcept}
                  onChange={(e) => setCardsPerConcept(parseInt(e.target.value) || 2)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
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
                onClick={handleGenerateFlashcards}
                disabled={generating || concepts.length === 0}
                className="px-5 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-semibold text-xs flex items-center space-x-2 transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50 cursor-pointer"
              >
                {generating ? (
                  <>
                    <RotateCw className="h-3.5 w-3.5 animate-spin" />
                    <span>Mining Flashcards...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="h-3.5 w-3.5" />
                    <span>Generate Deck</span>
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
