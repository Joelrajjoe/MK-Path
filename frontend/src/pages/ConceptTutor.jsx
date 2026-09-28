import React, { useState, useEffect, useRef } from 'react'
import { useAuth, useUser } from '@clerk/react'
import { 
  Bot, 
  Send, 
  Sparkles, 
  Brain, 
  MessageSquare, 
  Trash2, 
  Plus, 
  RotateCw, 
  CheckCircle2, 
  HelpCircle, 
  BookOpen, 
  Compass, 
  Zap, 
  Lightbulb, 
  Check, 
  Copy,
  AlertCircle,
  GraduationCap,
  Code2,
  Terminal,
  ChevronRight
} from 'lucide-react'

// Lightweight Markdown & Code Block Formatter for Rich Chat UI
function FormattedMessage({ content }) {
  if (!content) return null

  // Split code blocks from text
  const parts = content.split(/(```[\s\S]*?```)/g)

  return (
    <div className="space-y-2.5 text-xs text-slate-200 leading-relaxed font-normal">
      {parts.map((part, pIdx) => {
        if (part.startsWith('```') && part.endsWith('```')) {
          const lines = part.slice(3, -3).trim().split('\n')
          const language = lines[0].trim().match(/^[a-zA-Z0-9_-]+$/) ? lines[0].trim() : ''
          const codeBody = language ? lines.slice(1).join('\n') : lines.join('\n')

          return (
            <div key={pIdx} className="my-2.5 rounded-xl border border-slate-700/80 bg-slate-950 overflow-hidden shadow-md">
              <div className="flex items-center justify-between px-3 py-1.5 bg-slate-900 border-b border-slate-800 text-[10px] text-slate-400 font-mono">
                <span className="flex items-center gap-1.5 font-bold uppercase">
                  <Terminal size={12} className="text-indigo-400" />
                  {language || 'Code'}
                </span>
                <button
                  onClick={() => navigator.clipboard.writeText(codeBody)}
                  className="hover:text-white transition flex items-center gap-1"
                >
                  <Copy size={11} /> Copy
                </button>
              </div>
              <pre className="p-3 text-[11px] font-mono text-emerald-300 overflow-x-auto whitespace-pre">
                {codeBody}
              </pre>
            </div>
          )
        }

        // Standard markdown line formatting
        const paragraphs = part.split(/\n\n+/g)
        return paragraphs.map((para, p2Idx) => {
          if (!para.trim()) return null

          // Handle bullet lists
          if (para.trim().startsWith('- ') || para.trim().startsWith('* ') || para.trim().match(/^\d+\.\s/)) {
            const listItems = para.trim().split('\n')
            return (
              <ul key={`${pIdx}-${p2Idx}`} className="space-y-1 my-1 pl-4 list-disc text-slate-300">
                {listItems.map((item, lIdx) => {
                  const itemClean = item.replace(/^[-*\d.]+\s+/, '')
                  return (
                    <li key={lIdx} className="leading-relaxed">
                      <span dangerouslySetInnerHTML={{ __html: formatInlineMarkdown(itemClean) }} />
                    </li>
                  )
                })}
              </ul>
            )
          }

          // Handle Headings (###)
          if (para.startsWith('### ')) {
            return (
              <h4 key={`${pIdx}-${p2Idx}`} className="text-sm font-bold text-indigo-300 pt-1">
                {para.replace(/^###\s+/, '')}
              </h4>
            )
          }
          if (para.startsWith('## ')) {
            return (
              <h3 key={`${pIdx}-${p2Idx}`} className="text-sm font-extrabold text-white pt-1.5">
                {para.replace(/^##\s+/, '')}
              </h3>
            )
          }

          return (
            <p
              key={`${pIdx}-${p2Idx}`}
              className="leading-relaxed text-slate-200"
              dangerouslySetInnerHTML={{ __html: formatInlineMarkdown(para) }}
            />
          )
        })
      })}
    </div>
  )
}

function formatInlineMarkdown(text) {
  if (!text) return ''
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-white">$1</strong>')
    .replace(/\*(.*?)\*/g, '<em class="text-indigo-200">$1</em>')
    .replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded bg-slate-800 text-indigo-300 font-mono text-[11px]">$1</code>')
}

export default function ConceptTutor() {
  const { getToken } = useAuth()
  const { user } = useUser()

  // State
  const [sessions, setSessions] = useState([])
  const [activeSession, setActiveSession] = useState(null)
  const [concepts, setConcepts] = useState([])
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [inputMessage, setInputMessage] = useState('')
  const [selectedConcept, setSelectedConcept] = useState('')
  const [tutorMode, setTutorMode] = useState('socratic') // 'socratic' | 'direct_explainer' | 'exam_coach'
  const [error, setError] = useState(null)
  const [copiedId, setCopiedId] = useState(null)

  const messagesEndRef = useRef(null)

  useEffect(() => {
    fetchInitialData()
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [activeSession?.messages, sending])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const fetchInitialData = async () => {
    setLoading(true)
    setError(null)
    try {
      const token = await getToken()
      const headers = { Authorization: `Bearer ${token}` }

      const [sessRes, concRes] = await Promise.all([
        fetch('http://localhost:8000/api/tutor/sessions', { headers }),
        fetch('http://localhost:8000/api/concepts', { headers })
      ])

      if (concRes.ok) {
        const concData = await concRes.json()
        setConcepts(concData)
        if (concData.length > 0 && !selectedConcept) {
          setSelectedConcept(concData[0].name)
        }
      }

      if (sessRes.ok) {
        const sessData = await sessRes.json()
        setSessions(sessData)
        if (sessData.length > 0) {
          setActiveSession(sessData[0])
        }
      }
    } catch (err) {
      console.error('Failed to load tutor data:', err)
      setError('Could not connect to the backend server.')
    } finally {
      setLoading(false)
    }
  }

  const handleStartNewSession = () => {
    setActiveSession(null)
    setInputMessage('')
  }

  const handleSendMessage = async (e) => {
    e?.preventDefault()
    if (!inputMessage.trim() || sending) return

    const messageText = inputMessage.trim()
    setInputMessage('')
    setSending(true)
    setError(null)

    // Optimistic UI Message
    const tempUserMsg = {
      id: String(Date.now()),
      role: 'user',
      content: messageText,
      timestamp: new Date().toISOString()
    }

    if (activeSession) {
      setActiveSession(prev => ({
        ...prev,
        messages: [...(prev?.messages || []), tempUserMsg]
      }))
    }

    try {
      const token = await getToken()
      const res = await fetch('http://localhost:8000/api/tutor/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          session_id: activeSession?._id || activeSession?.id || undefined,
          concept_name: selectedConcept || undefined,
          message: messageText,
          tutor_mode: tutorMode
        })
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Tutor response failed')

      // Refresh active session
      const sessRes = await fetch(`http://localhost:8000/api/tutor/sessions/${data.session_id}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (sessRes.ok) {
        const fullSess = await sessRes.json()
        setActiveSession(fullSess)
        
        // Update session list
        setSessions(prev => {
          const exists = prev.some(s => (s._id || s.id) === (fullSess._id || fullSess.id))
          if (exists) {
            return prev.map(s => (s._id || s.id) === (fullSess._id || fullSess.id) ? fullSess : s)
          }
          return [fullSess, ...prev]
        })
      }
    } catch (err) {
      console.error('Chat error:', err)
      setError(err.message)
    } finally {
      setSending(false)
    }
  }

  const handleDeleteSession = async (sessId, e) => {
    e?.stopPropagation()
    if (!window.confirm('Delete this tutor conversation?')) return

    try {
      const token = await getToken()
      const res = await fetch(`http://localhost:8000/api/tutor/sessions/${sessId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const remaining = sessions.filter(s => (s._id || s.id) !== sessId)
        setSessions(remaining)
        if ((activeSession?._id || activeSession?.id) === sessId) {
          setActiveSession(remaining.length > 0 ? remaining[0] : null)
        }
      }
    } catch (err) {
      console.error('Delete session error:', err)
    }
  }

  const handleDeleteAllSessions = async () => {
    if (!window.confirm('Delete ALL tutor conversations? This cannot be undone.')) return
    try {
      const token = await getToken()
      const res = await fetch('http://localhost:8000/api/tutor/sessions/all', {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        setSessions([])
        setActiveSession(null)
      }
    } catch (err) {
      console.error('Delete all tutor sessions error:', err)
    }
  }

  const handleCopy = (id, text) => {
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-pink-600 text-white shadow-lg shadow-indigo-500/20">
            <Bot className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white flex items-center gap-2">
              Socratic AI Tutor & Concept Chat
              <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                1-on-1 Inquiry Engine
              </span>
            </h1>
            <p className="text-sm text-slate-400 mt-0.5">
              Conversational tutoring grounded in your uploaded study materials, knowledge graph, and mastery profile.
            </p>
          </div>
        </div>

        {/* Mode Selector */}
        <div className="flex items-center space-x-2 bg-slate-900 p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setTutorMode('socratic')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              tutorMode === 'socratic' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
            }`}
            title="Guides you through inquiry and leading hints"
          >
            Socratic Mode
          </button>
          <button
            onClick={() => setTutorMode('direct_explainer')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              tutorMode === 'direct_explainer' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
            }`}
            title="Provides structural definitions, analogies and code examples"
          >
            Direct Explainer
          </button>
          <button
            onClick={() => setTutorMode('exam_coach')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              tutorMode === 'exam_coach' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
            }`}
            title="Tests edge cases and diagnoses misconceptions"
          >
            Exam Coach
          </button>
        </div>
      </div>

      {/* Main Two-Pane Chat Studio */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[740px]">
        
        {/* Left Column: Session History & Target Concept */}
        <div className="lg:col-span-3 flex flex-col h-full bg-slate-900/70 border border-slate-800 rounded-2xl p-4 space-y-4">
          
          <button
            onClick={handleStartNewSession}
            className="w-full py-2.5 px-3 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold text-xs flex items-center justify-center space-x-2 shadow-md shadow-indigo-600/20 transition-all active:scale-95 cursor-pointer"
          >
            <Plus size={14} />
            <span>New Tutoring Session</span>
          </button>

          {/* Concept Focus Dropdown */}
          <div className="space-y-1.5 pt-2 border-t border-slate-800/80">
            <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
              Subject Focus
            </label>
            <select
              value={selectedConcept}
              onChange={(e) => setSelectedConcept(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="">General Curriculum Grounding</option>
              {concepts.map(c => (
                <option key={c._id || c.id} value={c.name}>{c.name}</option>
              ))}
            </select>
          </div>

          {/* Previous Sessions */}
          <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 pt-2">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                Conversations ({sessions.length})
              </span>
              {sessions.length > 0 && (
                <button
                  onClick={handleDeleteAllSessions}
                  className="text-[10px] text-red-400 hover:text-red-300 font-semibold transition"
                >
                  Clear All
                </button>
              )}
            </div>

            {sessions.length === 0 ? (
              <p className="text-xs text-slate-500 text-center py-6">No previous conversations.</p>
            ) : (
              sessions.map((sess) => {
                const sId = sess._id || sess.id
                const isSelected = (activeSession?._id || activeSession?.id) === sId
                return (
                  <div
                    key={sId}
                    onClick={() => setActiveSession(sess)}
                    className={`p-3 rounded-xl border transition-all cursor-pointer flex items-center justify-between group ${
                      isSelected 
                        ? 'bg-indigo-600/20 border-indigo-500/50 text-white' 
                        : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:bg-slate-900 hover:text-slate-200'
                    }`}
                  >
                    <div className="flex items-center space-x-2 truncate pr-2">
                      <MessageSquare size={13} className={isSelected ? 'text-indigo-400' : 'text-slate-500'} />
                      <span className="text-xs font-semibold truncate">{sess.session_title || 'Session'}</span>
                    </div>

                    <button
                      onClick={(e) => handleDeleteSession(sId, e)}
                      className="text-slate-500 hover:text-red-400 p-1 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                )
              })
            )}
          </div>
        </div>

        {/* Right Column: Interactive Chat Dialogue Stream */}
        <div className="lg:col-span-9 flex flex-col h-full bg-slate-900/90 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
          
          {/* Active Header */}
          <div className="p-4 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-9 h-9 rounded-xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 flex items-center justify-center font-bold text-xs shadow-inner">
                <Bot size={18} />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">
                  {selectedConcept ? `Tutoring: ${selectedConcept}` : 'Socratic Curriculum Mentor'}
                </h3>
                <p className="text-[11px] text-slate-400">
                  Mode: <span className="font-semibold text-indigo-400 capitalize">{tutorMode.replace('_', ' ')}</span> • Grounded in Study Context
                </p>
              </div>
            </div>

            <span className="text-[10px] font-bold px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5">
              <Zap size={12} /> +5 XP per Inquiry
            </span>
          </div>

          {/* Messages Stream */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {(!activeSession || (activeSession.messages || []).length === 0) ? (
              <div className="h-full flex flex-col items-center justify-center text-center space-y-4 max-w-lg mx-auto py-12">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-500/20 via-purple-500/20 to-pink-500/20 border border-indigo-500/30 text-indigo-400 flex items-center justify-center shadow-xl">
                  <Sparkles size={32} />
                </div>
                <div className="space-y-1.5">
                  <h3 className="text-lg font-extrabold text-white">Interactive Socratic Session</h3>
                  <p className="text-xs text-slate-400 leading-relaxed max-w-sm mx-auto">
                    Ask questions, explore edge cases, or request step-by-step conceptual breakdowns on <strong className="text-indigo-300">{selectedConcept || 'your active curriculum'}</strong>.
                  </p>
                </div>

                {/* Quick Prompt Cards */}
                <div className="grid grid-cols-1 gap-2.5 w-full pt-4">
                  <button
                    onClick={() => {
                      setInputMessage(`Why is ${selectedConcept || 'this concept'} designed this way, and what fundamental problem does it solve?`)
                    }}
                    className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 hover:border-indigo-500/40 text-left text-xs text-slate-300 hover:text-white transition flex items-center justify-between group cursor-pointer"
                  >
                    <span>💡 "Why is {selectedConcept || 'this concept'} designed this way?"</span>
                    <ChevronRight size={14} className="text-slate-600 group-hover:text-indigo-400 transition" />
                  </button>
                  <button
                    onClick={() => {
                      setInputMessage(`Give me a practical real-world scenario where ${selectedConcept || 'this concept'} is applied, with potential misconceptions.`)
                    }}
                    className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 hover:border-indigo-500/40 text-left text-xs text-slate-300 hover:text-white transition flex items-center justify-between group cursor-pointer"
                  >
                    <span>🎯 "Show me a real-world scenario and common misconceptions."</span>
                    <ChevronRight size={14} className="text-slate-600 group-hover:text-indigo-400 transition" />
                  </button>
                </div>
              </div>
            ) : (
              activeSession.messages.map((msg, idx) => {
                const isUser = msg.role === 'user'
                return (
                  <div
                    key={msg.id || idx}
                    className={`flex items-start gap-3.5 ${isUser ? 'justify-end' : 'justify-start'}`}
                  >
                    {!isUser && (
                      <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-pink-600 text-white flex items-center justify-center flex-shrink-0 shadow-md">
                        <Bot size={16} />
                      </div>
                    )}

                    <div
                      className={`max-w-3xl rounded-2xl p-4.5 space-y-2 relative group shadow-xl ${
                        isUser
                          ? 'bg-gradient-to-r from-indigo-600 to-indigo-700 text-white rounded-tr-sm border border-indigo-500/30'
                          : 'bg-slate-950/90 border border-slate-800 text-slate-200 rounded-tl-sm'
                      }`}
                    >
                      {isUser ? (
                        <div className="text-xs leading-relaxed whitespace-pre-line font-medium">
                          {msg.content}
                        </div>
                      ) : (
                        <FormattedMessage content={msg.content} />
                      )}

                      {!isUser && (
                        <div className="pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-500">
                          <span className="font-semibold text-slate-400">Socratic Concept Guide</span>
                          <button
                            onClick={() => handleCopy(msg.id || idx, msg.content)}
                            className="hover:text-slate-200 transition cursor-pointer flex items-center gap-1"
                            title="Copy reply"
                          >
                            {copiedId === (msg.id || idx) ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                            <span>{copiedId === (msg.id || idx) ? 'Copied' : 'Copy'}</span>
                          </button>
                        </div>
                      )}
                    </div>

                    {isUser && (
                      <div className="w-8 h-8 rounded-xl bg-slate-800 border border-slate-700 text-slate-200 flex items-center justify-center flex-shrink-0 text-xs font-bold">
                        {user?.firstName?.[0] || 'U'}
                      </div>
                    )}
                  </div>
                )
              })
            )}

            {sending && (
              <div className="flex items-start gap-3.5 justify-start animate-fade-in">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 text-white flex items-center justify-center flex-shrink-0">
                  <Bot size={16} />
                </div>
                <div className="bg-slate-950/90 border border-slate-800 text-slate-400 rounded-2xl rounded-tl-sm p-4 text-xs flex items-center space-x-2 shadow-lg">
                  <RotateCw size={14} className="animate-spin text-indigo-400" />
                  <span>Synthesizing structured Socratic explanation...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Message Input Box */}
          <form onSubmit={handleSendMessage} className="p-4 border-t border-slate-800 bg-slate-950/80">
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder={selectedConcept ? `Ask the Socratic Tutor about ${selectedConcept}...` : "Ask a concept question..."}
                disabled={sending}
                className="flex-1 px-4 py-3.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition shadow-inner"
              />
              <button
                type="submit"
                disabled={!inputMessage.trim() || sending}
                className="px-5 py-3.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 disabled:opacity-40 transition-all active:scale-95 cursor-pointer flex items-center gap-2 font-bold text-xs flex-shrink-0"
              >
                <span>Send</span>
                <Send size={14} />
              </button>
            </div>
          </form>

        </div>

      </div>

    </div>
  )
}
