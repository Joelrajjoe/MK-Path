import React, { useState, useEffect, useRef } from 'react'
import { useAuth, useUser } from '@clerk/react'
import {
  Sparkles,
  Send,
  Bot,
  User as UserIcon,
  BookOpen,
  Briefcase,
  Compass,
  AlertCircle,
  HelpCircle,
  Code2,
  ExternalLink,
  Plus,
  Trash2,
  Loader2,
  CheckCircle2,
  RefreshCw,
  Globe,
  Youtube,
  FileText
} from 'lucide-react'
import { API_BASE_URL } from '../config'

export default function PersonalLearningAgent() {
  const { getToken } = useAuth()
  const { user } = useUser()

  const [conversations, setConversations] = useState([])
  const [activeConversationId, setActiveConversationId] = useState(null)
  const [messages, setMessages] = useState([])
  const [inputQuery, setInputQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [fetchingConversations, setFetchingConversations] = useState(true)
  const [includeWeb, setIncludeWeb] = useState(false)
  const [activeIntent, setActiveIntent] = useState('GENERAL')
  const [recommendedAction, setRecommendedAction] = useState(null)

  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    fetchConversations()
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const fetchConversations = async () => {
    try {
      setFetchingConversations(true)
      const token = await getToken()
      const res = await fetch(`${API_BASE_URL}/api/agent/conversations`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setConversations(data)
        if (data.length > 0 && !activeConversationId) {
          loadConversation(data[0]._id || data[0].id)
        }
      }
    } catch (err) {
      console.warn('Failed to load conversations:', err)
    } finally {
      setFetchingConversations(false)
    }
  }

  const loadConversation = async (convId) => {
    try {
      setLoading(true)
      setActiveConversationId(convId)
      const token = await getToken()
      const res = await fetch(`${API_BASE_URL}/api/agent/conversations/${convId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setMessages(data.messages || [])
        setActiveIntent(data.active_intent || 'GENERAL')
      }
    } catch (err) {
      console.warn('Failed to load conversation details:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSendMessage = async (queryText = inputQuery) => {
    if (!queryText.trim() || loading) return

    const userText = queryText.trim()
    setInputQuery('')

    const optimisticUserMsg = {
      role: 'user',
      content: userText,
      timestamp: new Date().toISOString()
    }
    setMessages((prev) => [...prev, optimisticUserMsg])
    setLoading(true)

    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE_URL}/api/agent/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          conversation_id: activeConversationId || undefined,
          message: userText,
          include_web_search: includeWeb
        })
      })

      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Agent response failed')
      }

      const data = await res.json()
      setActiveConversationId(data.conversation_id)
      setActiveIntent(data.intent_detected)
      setMessages((prev) => [...prev, data.message])
      if (data.recommended_next_action) {
        setRecommendedAction(data.recommended_next_action)
      }

      // Refresh conversations list in sidebar
      fetchConversations()
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `⚠️ Consultation Error: ${err.message}`,
          timestamp: new Date().toISOString()
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleStartNewChat = () => {
    setActiveConversationId(null)
    setMessages([])
    setRecommendedAction(null)
    setActiveIntent('GENERAL')
  }

  const handleDeleteConversation = async (convId, e) => {
    e.stopPropagation()
    if (!window.confirm('Delete this conversation history?')) return
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE_URL}/api/agent/conversations/${convId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        setConversations((prev) => prev.filter((c) => (c._id || c.id) !== convId))
        if (activeConversationId === convId) {
          handleStartNewChat()
        }
      }
    } catch (err) {
      console.warn('Failed to delete conversation:', err)
    }
  }

  const suggestionPrompts = [
    { label: '🎯 What should I study today?', text: 'What should I study today based on my active goal and mastery levels?' },
    { label: '💼 Analyze my Backend Engineer skill gaps', text: 'Analyze my skill gaps for a Senior Backend Engineer role and recommend next steps.' },
    { label: '🤖 Explain Transformers & Self-Attention', text: 'Explain the intuition behind self-attention mechanisms in transformers with a code example.' },
    { label: '🌐 What are modern LLM agent trends in 2026?', text: 'What are the current industry standards and design patterns for agentic AI architectures?' }
  ]

  return (
    <div className="flex h-[calc(100vh-80px)] gap-4 animate-fade-in">
      {/* Left Sidebar: Conversation History */}
      <div className="w-72 bg-slate-900/60 border border-slate-800/80 rounded-2xl flex flex-col overflow-hidden hidden md:flex">
        <div className="p-4 border-b border-slate-800/80 flex items-center justify-between">
          <div className="flex items-center space-x-2 text-white font-bold text-sm">
            <Sparkles size={16} className="text-indigo-400" />
            <span>AI Consultations</span>
          </div>
          <button
            onClick={handleStartNewChat}
            className="p-1.5 rounded-lg bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600/30 border border-indigo-500/20 transition cursor-pointer"
            title="Start New Chat"
          >
            <Plus size={14} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-1.5 scrollbar-none">
          {fetchingConversations ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-slate-500" />
            </div>
          ) : conversations.length === 0 ? (
            <div className="text-center py-12 px-4">
              <Bot size={28} className="mx-auto text-slate-600 mb-2" />
              <p className="text-xs text-slate-500">No previous consultations.</p>
            </div>
          ) : (
            conversations.map((c) => {
              const id = c._id || c.id
              const isActive = activeConversationId === id
              return (
                <div
                  key={id}
                  onClick={() => loadConversation(id)}
                  className={`group flex items-center justify-between px-3 py-2.5 rounded-xl text-xs cursor-pointer transition ${
                    isActive
                      ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 font-semibold'
                      : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                  }`}
                >
                  <span className="truncate pr-2">{c.title || 'Consultation Session'}</span>
                  <button
                    onClick={(e) => handleDeleteConversation(id, e)}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:text-rose-400 transition"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* Main Agent Dialogue Area */}
      <div className="flex-1 bg-slate-900/60 border border-slate-800/80 rounded-2xl flex flex-col overflow-hidden">
        {/* Top Header */}
        <div className="p-4 border-b border-slate-800/80 flex items-center justify-between bg-slate-950/20">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-gradient-to-tr from-indigo-500 via-purple-500 to-pink-500 text-white shadow-lg shadow-indigo-500/20">
              <Sparkles size={18} />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-sm font-bold text-white">MK-Path AI Learning & Career Agent</h2>
                <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 uppercase tracking-wider">
                  {activeIntent}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Multi-source intelligence • Grounded in your materials, goals, and mastery state
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setIncludeWeb(!includeWeb)}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition cursor-pointer ${
                includeWeb
                  ? 'bg-sky-500/20 text-sky-300 border-sky-500/40'
                  : 'bg-slate-800/40 text-slate-400 border-slate-700/60 hover:text-slate-200'
              }`}
            >
              <Globe size={13} />
              <span>Web Intel {includeWeb ? 'ON' : 'OFF'}</span>
            </button>
          </div>
        </div>

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-none">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center px-4 max-w-xl mx-auto py-12 space-y-6">
              <div className="p-4 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                <Bot size={36} />
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-bold text-white">Personal AI Learning & Career Advisor</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  I synthesize your uploaded PDFs, YouTube video lectures, prerequisite bottlenecks, and mastery history
                  to guide your daily learning trajectory and career readiness.
                </p>
              </div>

              {/* Quick Prompt Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 w-full text-left">
                {suggestionPrompts.map((s, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(s.text)}
                    className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-indigo-500/40 hover:bg-slate-850 transition cursor-pointer text-xs group"
                  >
                    <p className="font-semibold text-slate-200 group-hover:text-indigo-300 mb-1">{s.label}</p>
                    <p className="text-[11px] text-slate-500 truncate">{s.text}</p>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m, idx) => {
              const isUser = m.role === 'user'
              return (
                <div key={idx} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className={`max-w-[85%] md:max-w-[75%] rounded-2xl p-4 space-y-3 ${
                      isUser
                        ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
                        : 'bg-slate-850 border border-slate-800 text-slate-200 shadow-md'
                    }`}
                  >
                    {/* Header */}
                    <div className="flex items-center space-x-2 text-[11px] opacity-70">
                      {isUser ? <UserIcon size={12} /> : <Bot size={12} />}
                      <span className="font-bold">{isUser ? user?.firstName || 'Learner' : 'MK-Path Agent'}</span>
                    </div>

                    {/* Message Body */}
                    <div className="text-xs md:text-sm leading-relaxed whitespace-pre-wrap font-sans">
                      {m.content}
                    </div>

                    {/* Verifiable Citations */}
                    {m.citations && m.citations.length > 0 && (
                      <div className="pt-2 border-t border-slate-700/50 space-y-1.5">
                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                          Grounded Sources & Citations
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {m.citations.map((c, cIdx) => (
                            <div
                              key={cIdx}
                              className="flex items-center space-x-1 px-2 py-1 rounded bg-slate-900/80 border border-slate-700/60 text-[10px] text-slate-300"
                            >
                              {c.source_type === 'youtube_source' ? (
                                <Youtube size={10} className="text-red-400" />
                              ) : c.source_type === 'learner_material' ? (
                                <FileText size={10} className="text-indigo-400" />
                              ) : (
                                <Globe size={10} className="text-sky-400" />
                              )}
                              <span className="font-medium truncate max-w-[160px]">{c.title}</span>
                              {c.timestamp_formatted && (
                                <span className="text-amber-400 font-mono">[{c.timestamp_formatted}]</span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )
            })
          )}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-slate-850 border border-slate-800 rounded-2xl p-4 flex items-center space-x-2 text-indigo-400 text-xs font-semibold">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Synthesizing multi-source learner intelligence...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-3 border-t border-slate-800/80 bg-slate-950/40">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSendMessage()
            }}
            className="flex items-center space-x-2"
          >
            <input
              type="text"
              placeholder="Ask anything about your study materials, skill gaps, career roadmap, or tech concepts..."
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/60"
            />
            <button
              type="submit"
              disabled={loading || !inputQuery.trim()}
              className="p-3 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white disabled:opacity-40 transition cursor-pointer shadow-md shadow-indigo-500/20"
            >
              <Send size={15} />
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
