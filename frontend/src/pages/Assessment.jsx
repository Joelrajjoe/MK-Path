import React, { useState, useEffect } from 'react'
import { useAuth } from '@clerk/react'
import { useLocation } from 'react-router-dom'
import { 
  Award, 
  HelpCircle, 
  Loader2, 
  Sparkles, 
  AlertTriangle, 
  Clock, 
  ThumbsUp, 
  CheckCircle2, 
  XCircle, 
  RefreshCw, 
  BookOpen, 
  ArrowRight,
  TrendingUp,
  Info
} from 'lucide-react'

export default function Assessment() {
  const { getToken } = useAuth()
  const location = useLocation()

  // State variables
  const [concepts, setConcepts] = useState([])
  const [loading, setLoading] = useState(true)
  
  // Quiz Setup States
  const [selectedConceptId, setSelectedConceptId] = useState(
    location.state?.preselectedConceptId || ''
  )

  const [questionCount, setQuestionCount] = useState(5)
  
  // Active Quiz States
  const [quizQuestions, setQuizQuestions] = useState([]) // Sanitized questions
  const [quizActive, setQuizActive] = useState(false)
  const [currentIdx, setCurrentIdx] = useState(0)
  const [selectedOption, setSelectedOption] = useState(null)
  const [confidence, setConfidence] = useState(3) // Default middle confidence
  
  // Timer States
  const [timeSpent, setTimeSpent] = useState(0)
  const [answersSheet, setAnswersSheet] = useState([]) // [{question_id, selected_option_index, confidence, response_time_seconds}]
  
  // Quiz Results States
  const [quizResults, setQuizResults] = useState(null) // API response from submit
  const [submitting, setSubmitting] = useState(false)

  // Fetch concepts list on mount
  useEffect(() => {
    const loadConcepts = async () => {
      try {
        setLoading(true)
        const token = await getToken()
        const res = await fetch('http://localhost:8000/api/concepts', {
          headers: { Authorization: `Bearer ${token}` }
        })
        if (res.ok) {
          const data = await res.json()
          setConcepts(data)
        }
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    loadConcepts()
  }, [getToken])

  // Question response time tracker
  useEffect(() => {
    let interval = null
    if (quizActive && !submitting && !quizResults) {
      interval = setInterval(() => {
        setTimeSpent((t) => t + 1)
      }, 1000)
    } else {
      clearInterval(interval)
    }
    return () => clearInterval(interval)
  }, [quizActive, submitting, quizResults])

  // Reset timer on question change
  useEffect(() => {
    setTimeSpent(0)
    setSelectedOption(null)
    setConfidence(3)
  }, [currentIdx])

  // Start Quiz
  const handleStartQuiz = async () => {
    try {
      setLoading(true)
      const token = await getToken()
      const payload = {
        concept_id: selectedConceptId || null,
        num_questions: questionCount
      }
      
      const res = await fetch('http://localhost:8000/api/assessment/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      })

      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Failed to generate quiz questions')
      }

      const data = await res.json()
      setQuizQuestions(data)
      setAnswersSheet([])
      setCurrentIdx(0)
      setQuizResults(null)
      setQuizActive(true)
    } catch (err) {
      alert(err.message || 'Error creating assessment questions.')
    } finally {
      setLoading(false)
    }
  }

  // Handle Option Select
  const handleSelectOption = (idx) => {
    setSelectedOption(idx)
  }

  // Go to Next Question / Submit Quiz
  const handleNextQuestion = async () => {
    if (selectedOption === null) return

    const activeQuestion = quizQuestions[currentIdx]
    const updatedAnswers = [
      ...answersSheet,
      {
        question_id: activeQuestion._id,
        selected_option_index: selectedOption,
        confidence: parseInt(confidence),
        response_time_seconds: parseFloat(timeSpent)
      }
    ]
    setAnswersSheet(updatedAnswers)

    if (currentIdx < quizQuestions.length - 1) {
      setCurrentIdx((idx) => idx + 1)
    } else {
      // Last question completed, submit quiz attempts
      await handleSubmitQuiz(updatedAnswers)
    }
  }

  // Submit Quiz Attempts
  const handleSubmitQuiz = async (sheet) => {
    try {
      setSubmitting(true)
      const token = await getToken()
      const payload = { attempts: sheet }

      const res = await fetch('http://localhost:8000/api/assessment/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      })

      if (!res.ok) {
        throw new Error('Failed to submit assessment attempts')
      }

      const data = await res.json()
      setQuizResults(data)
    } catch (err) {
      alert(err.message || 'Error submitting assessment sheet.')
    } finally {
      setSubmitting(false)
    }
  }

  // Reset Quiz State
  const handleResetQuiz = () => {
    setQuizQuestions([])
    setAnswersSheet([])
    setCurrentIdx(0)
    setQuizResults(null)
    setQuizActive(false)
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8 h-full overflow-y-auto pr-2 pb-10">
      
      {/* Page Title header */}
      <div className="border-b border-slate-800 pb-4">
        <h2 className="text-sm font-bold text-white uppercase tracking-wider">Adaptive Mastery Assessment</h2>
        <p className="text-xs text-slate-500 mt-0.5">Evaluate and fine-tune your knowledge concepts with confidence-corrected scoring.</p>
      </div>

      {loading && quizQuestions.length === 0 ? (
        // Loading Spinner
        <div className="flex justify-center items-center py-24">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
        </div>
      ) : !quizActive ? (
        // --- STEP 1: Quiz Configuration panel ---
        concepts.length === 0 ? (
          // Zero State Warning
          <div className="border border-slate-800/80 bg-slate-900/10 rounded-2xl p-12 text-center space-y-4">
            <div className="mx-auto w-fit p-4 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-2xl">
              <AlertTriangle className="h-8 w-8" />
            </div>
            <div className="space-y-2 max-w-sm mx-auto">
              <p className="font-bold text-sm text-slate-350">No concepts discovered.</p>
              <p className="text-xs text-slate-500 leading-relaxed">
                Assessments require mapped concepts. Please upload study PDFs in the Materials view and run the Concept Miner first.
              </p>
            </div>
          </div>
        ) : (
          <div className="border border-slate-800 bg-slate-900/10 rounded-2xl p-8 space-y-6 glow-card">
            <div className="flex items-center space-x-3 text-indigo-400 border-b border-slate-800/60 pb-3">
              <Sparkles size={20} />
              <h3 className="font-bold text-white text-sm">Configure Concept Quiz</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              
              {/* Concept Target selector */}
              <div className="space-y-2">
                <label className="text-xs text-slate-400 font-bold block">Target Concept Scope</label>
                <select
                  value={selectedConceptId}
                  onChange={(e) => setSelectedConceptId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-850 hover:border-slate-700 rounded-xl px-4 py-3 text-xs text-white focus:outline-none focus:border-indigo-500 transition"
                >
                  <option value="">All Extracted Concepts (Comprehensive Assessment)</option>
                  {concepts.map((c) => (
                    <option key={c._id} value={c._id}>
                      {c.name} ({c.difficulty})
                    </option>
                  ))}
                </select>
              </div>

              {/* Question Count selector */}
              <div className="space-y-2">
                <label className="text-xs text-slate-400 font-bold block">Number of Questions</label>
                <div className="flex items-center space-x-4">
                  {[5, 10].map((num) => (
                    <button
                      key={num}
                      type="button"
                      onClick={() => setQuestionCount(num)}
                      className={`flex-1 py-3 text-xs font-bold rounded-xl border transition ${
                        questionCount === num
                          ? 'border-indigo-500 bg-indigo-500/5 text-white'
                          : 'border-slate-850 bg-slate-950 text-slate-400 hover:border-slate-700 hover:text-white'
                      }`}
                    >
                      {num} Questions
                    </button>
                  ))}
                </div>
              </div>

            </div>

            {/* Instruction Tip */}
            <div className="flex items-start space-x-3 p-4 rounded-xl bg-indigo-950/10 border border-indigo-900/30 text-indigo-300 text-xs">
              <Info size={16} className="flex-shrink-0 mt-0.5" />
              <div className="space-y-1 leading-relaxed">
                <p className="font-bold">Adaptive Calibration Rules</p>
                <p>
                  Correct answers increase concept difficulty; wrong answers decrease it. Marking higher confidence multiplies score adjustments, penalizing guessed answers that are wrong.
                </p>
              </div>
            </div>

            <button
              onClick={handleStartQuiz}
              className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-xs transition flex items-center justify-center space-x-2 shadow-lg"
            >
              <Sparkles size={14} />
              <span>Start Assessment</span>
            </button>
          </div>
        )
      ) : submitting ? (
        // Submitting status loader
        <div className="flex flex-col items-center justify-center py-24 space-y-4">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
          <p className="text-xs text-slate-400 font-bold">Submitting assessment attempts and calculating mastery updates...</p>
        </div>
      ) : quizResults ? (
        // --- STEP 3: Quiz Review Dashboard ---
        <div className="space-y-8 animate-in fade-in duration-300">
          
          {/* Results Summary Card */}
          <div className="border border-slate-800 bg-slate-900/10 rounded-2xl p-8 flex flex-col md:flex-row items-center justify-between gap-6 glow-card">
            
            <div className="space-y-2 text-center md:text-left">
              <div className="flex items-center justify-center md:justify-start space-x-2 text-indigo-400">
                <Award size={20} />
                <h3 className="font-bold text-white text-sm">Assessment Complete!</h3>
              </div>
              <p className="text-xs text-slate-500 max-w-sm">
                Your concepts database has been updated with confidence-weighted mastery changes.
              </p>
            </div>

            <div className="flex items-center space-x-6">
              {/* Score Percentage meter */}
              <div className="flex flex-col items-center">
                <span className="text-3xl font-black text-white">{quizResults.percentage}%</span>
                <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider mt-1">Total Score</span>
              </div>
              <div className="h-10 w-px bg-slate-800"></div>
              {/* Answer Fraction */}
              <div className="flex flex-col items-center">
                <span className="text-2xl font-extrabold text-indigo-400">
                  {quizResults.correct_answers} <span className="text-xs text-slate-500">/ {quizResults.total_questions}</span>
                </span>
                <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider mt-1.5">Correct Answers</span>
              </div>
            </div>

          </div>

          {/* Detailed Question Review List */}
          <div className="space-y-4">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider pb-1 border-b border-slate-800">
              Question Review & Explanations
            </h4>
            
            {quizResults.review.map((item, idx) => (
              <div key={idx} className="p-6 bg-slate-900/30 border border-slate-800/80 rounded-xl space-y-4 font-sans select-text">
                
                {/* Heading & Score Delta */}
                <div className="flex items-start justify-between space-x-2">
                  <div className="flex items-center space-x-2 text-xs">
                    <span className="font-bold text-slate-500">Question {idx + 1}</span>
                    <span>•</span>
                    <span className="text-indigo-400 font-semibold">{item.concept_name}</span>
                  </div>
                  
                  {/* Mastery feedback */}
                  <span className="text-[9px] bg-slate-850 text-slate-400 border border-slate-800 px-2 py-0.5 rounded font-bold uppercase flex items-center space-x-1">
                    <TrendingUp size={8} className="text-indigo-400" />
                    <span>Mastery: {item.new_mastery_score.toFixed(0)}% ({item.mastery_state})</span>
                  </span>
                </div>

                {/* Question Text */}
                <p className="text-sm font-bold text-white leading-relaxed">{item.question_text}</p>

                {/* Option Buttons */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                  {item.options.map((opt, oidx) => {
                    const isSelected = oidx === item.selected_option_index
                    const isCorrect = oidx === item.correct_option_index
                    
                    let btnStyle = "border-slate-850 bg-slate-950/20 text-slate-400"
                    let icon = null
                    
                    if (isCorrect) {
                      btnStyle = "border-emerald-500/30 bg-emerald-500/5 text-emerald-400"
                      icon = <CheckCircle2 size={12} className="flex-shrink-0" />
                    } else if (isSelected && !isCorrect) {
                      btnStyle = "border-rose-500/30 bg-rose-500/5 text-rose-400"
                      icon = <XCircle size={12} className="flex-shrink-0" />
                    }

                    return (
                      <div 
                        key={oidx}
                        className={`flex items-center justify-between p-3 rounded-lg border text-xs font-semibold ${btnStyle}`}
                      >
                        <span className="truncate">{opt}</span>
                        {icon}
                      </div>
                    )
                  })}
                </div>

                {/* Explanation text */}
                <div className="p-4 bg-slate-950/40 border border-slate-850 rounded-lg text-xs leading-relaxed space-y-1.5">
                  <div className="flex items-center space-x-1.5 text-slate-400 font-bold">
                    <HelpCircle size={12} className="text-indigo-400" />
                    <span>Explanation</span>
                  </div>
                  <p className="text-slate-400">{item.explanation}</p>
                </div>

              </div>
            ))}
          </div>

          <button
            onClick={handleResetQuiz}
            className="w-full py-3 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-xl text-xs transition flex items-center justify-center space-x-2 border border-slate-700"
          >
            <RefreshCw size={12} />
            <span>Retake Another Assessment</span>
          </button>

        </div>
      ) : (
        // --- STEP 2: Active Quiz question card ---
        <div className="border border-slate-800 bg-slate-900/10 rounded-2xl p-8 space-y-6 glow-card animate-in zoom-in-95 duration-200">
          
          {/* Question Index Progress Bar */}
          <div className="space-y-2">
            <div className="flex justify-between items-center text-[10px] text-slate-500 uppercase font-bold tracking-wider">
              <span>Concept Quiz: {quizQuestions[currentIdx]?.concept_name}</span>
              <span className="text-indigo-400">
                Question {currentIdx + 1} of {quizQuestions.length}
              </span>
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
              <div 
                className="bg-indigo-500 h-full rounded-full transition-all duration-300"
                style={{ width: `${((currentIdx + 1) / quizQuestions.length) * 100}%` }}
              ></div>
            </div>
          </div>

          {/* Active Question Title */}
          <div className="space-y-4">
            <div className="flex justify-between items-start">
              <h3 className="text-base font-bold text-white leading-relaxed">
                {quizQuestions[currentIdx]?.question_text}
              </h3>
              
              {/* Question timer */}
              <span className="flex items-center space-x-1 px-2 py-1 bg-slate-850 border border-slate-800 text-[10px] text-slate-400 font-bold rounded-lg flex-shrink-0">
                <Clock size={10} className="text-indigo-400 animate-pulse" />
                <span>{timeSpent}s</span>
              </span>
            </div>

            {/* Options List */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {quizQuestions[currentIdx]?.options.map((opt, oidx) => (
                <button
                  key={oidx}
                  type="button"
                  onClick={() => handleSelectOption(oidx)}
                  className={`p-4 rounded-xl border text-left text-xs font-semibold leading-relaxed transition ${
                    selectedOption === oidx
                      ? 'border-indigo-500 bg-indigo-500/5 text-white glow-indigo'
                      : 'border-slate-850 bg-slate-950/20 text-slate-400 hover:border-slate-700 hover:text-white'
                  }`}
                >
                  {opt}
                </button>
              ))}
            </div>
          </div>

          {/* Confidence Slider */}
          <div className="p-4 bg-slate-950/30 border border-slate-850 rounded-xl space-y-3 font-sans">
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-400 font-bold flex items-center space-x-1.5">
                <ThumbsUp size={12} className="text-indigo-400" />
                <span>Rate your Confidence level</span>
              </span>
              <span className="font-extrabold text-indigo-400">
                {confidence === 1 ? '1 - Pure Guess' 
                  : confidence === 2 ? '2 - Unsure' 
                  : confidence === 3 ? '3 - Moderately Confined' 
                  : confidence === 4 ? '4 - Confident' 
                  : '5 - Absolute Certain'}
              </span>
            </div>
            
            <input 
              type="range"
              min="1"
              max="5"
              step="1"
              value={confidence}
              onChange={(e) => setConfidence(parseInt(e.target.value))}
              className="w-full accent-indigo-500 h-1 bg-slate-800 rounded-lg cursor-pointer"
            />
            
            <div className="flex justify-between text-[10px] text-slate-500 font-bold">
              <span>1 (Guess)</span>
              <span>2</span>
              <span>3</span>
              <span>4</span>
              <span>5 (Certain)</span>
            </div>
          </div>

          {/* Controls Footer */}
          <div className="flex justify-end pt-2">
            <button
              onClick={handleNextQuestion}
              disabled={selectedOption === null}
              className={`px-6 py-3 rounded-xl text-xs font-bold transition flex items-center space-x-1.5 ${
                selectedOption !== null
                  ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg'
                  : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-750'
              }`}
            >
              <span>{currentIdx < quizQuestions.length - 1 ? 'Next Question' : 'Submit Assessment'}</span>
              <ArrowRight size={12} />
            </button>
          </div>

        </div>
      )}
    </div>
  )
}
