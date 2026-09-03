import React, { useState, useEffect } from 'react'
import { useAuth, useUser } from '@clerk/react'
import { 
  Download, 
  FileText, 
  FileSpreadsheet, 
  Printer, 
  Share2, 
  Award, 
  Brain, 
  CheckCircle2, 
  Sparkles, 
  GitBranch, 
  Layers, 
  RotateCw, 
  Clock, 
  ShieldCheck, 
  BookOpen, 
  Calendar,
  ExternalLink,
  ChevronRight,
  TrendingUp,
  FileCode,
  Zap
} from 'lucide-react'

export default function ExportStudio() {
  const { getToken } = useAuth()
  const { user } = useUser()

  const [reportData, setReportData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedFormat, setSelectedFormat] = useState('pdf')
  const [activeTab, setActiveTab] = useState('preview') // 'preview' | 'certificate' | 'cheatsheet'

  useEffect(() => {
    fetchReportData()
  }, [])

  const fetchReportData = async () => {
    setLoading(true)
    setError(null)
    try {
      const token = await getToken()
      const res = await fetch('http://localhost:8000/api/export/curriculum-report', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!res.ok) throw new Error('Failed to compile curriculum export data')
      const data = await res.json()
      setReportData(data)
    } catch (err) {
      console.error('Export fetch failed:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Export handlers
  const handlePrintPDF = () => {
    window.print()
  }

  const handleDownloadJSON = () => {
    if (!reportData) return
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(reportData, null, 2))
    const downloadAnchor = document.createElement('a')
    downloadAnchor.setAttribute("href", dataStr)
    downloadAnchor.setAttribute("download", `MK-Path-Curriculum-Export-${new Date().toISOString().slice(0,10)}.json`)
    document.body.appendChild(downloadAnchor)
    downloadAnchor.click()
    downloadAnchor.remove()
  }

  const handleDownloadCSV = () => {
    if (!reportData?.concepts) return
    const headers = ["Concept ID", "Concept Name", "Difficulty", "Exam Relevance", "Industry Relevance", "Mastery Category", "Mastery Score", "Prerequisites", "Description"]
    const rows = reportData.concepts.map(c => [
      `"${c.id}"`,
      `"${c.name.replace(/"/g, '""')}"`,
      `"${c.difficulty}"`,
      c.exam_relevance,
      c.industry_relevance,
      `"${c.mastery_category}"`,
      c.mastery_score !== null ? c.mastery_score : "N/A",
      `"${(c.prerequisites || []).join('; ')}"`,
      `"${(c.description || '').replace(/"/g, '""')}"`
    ])
    
    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(','), ...rows.map(e => e.join(','))].join('\n')
    const encodedUri = encodeURI(csvContent)
    const link = document.createElement("a")
    link.setAttribute("href", encodedUri)
    link.setAttribute("download", `MK-Path-Concepts-Data-${new Date().toISOString().slice(0,10)}.csv`)
    document.body.appendChild(link)
    link.click()
    link.remove()
  }

  const handleDownloadMarkdownCheatSheet = () => {
    if (!reportData) return
    let md = `# MK-Path Intelligent Curriculum & Concept Cheat-Sheet\n`
    md += `**Generated for:** ${reportData.learner.display_name} (${reportData.learner.email})\n`
    md += `**Date:** ${new Date(reportData.generated_at).toLocaleDateString()}\n`
    md += `**Average Decayed Mastery:** ${reportData.summary.average_mastery}%\n`
    md += `**Total Extracted Concepts:** ${reportData.summary.total_concepts}\n\n`
    md += `---\n\n`
    md += `## 📚 Core Concept Directory & High-Yield Definitions\n\n`
    
    reportData.concepts.forEach((c, idx) => {
      md += `### ${idx + 1}. ${c.name}\n`
      md += `- **Difficulty:** ${c.difficulty.toUpperCase()} | **Exam Weight:** ${c.exam_relevance}% | **Industry Weight:** ${c.industry_relevance}%\n`
      md += `- **Mastery Status:** ${c.mastery_category.toUpperCase()} (${c.mastery_score !== null ? c.mastery_score + '%' : 'Unassessed'})\n`
      if (c.prerequisites?.length > 0) {
        md += `- **Prerequisites:** ${c.prerequisites.join(', ')}\n`
      }
      md += `- **Definition / Core Explanation:**\n  > ${c.description}\n\n`
    })

    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.setAttribute('href', url)
    link.setAttribute('download', `MK-Path-CheatSheet-${new Date().toISOString().slice(0,10)}.md`)
    document.body.appendChild(link)
    link.click()
    link.remove()
  }

  return (
    <div className="space-y-8 animate-fade-in pb-16">
      
      {/* Non-printable Screen Header & Controls */}
      <div className="print:hidden space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-500/20">
              <Download className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white flex items-center gap-2">
                Export & Reporting Studio
                <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  Publication Ready
                </span>
              </h1>
              <p className="text-sm text-slate-400 mt-0.5">
                Generate official curriculum blueprints, printable PDF audit reports, and mastery certificates.
              </p>
            </div>
          </div>

          {/* Quick Action Export Buttons */}
          <div className="flex flex-wrap items-center gap-2.5">
            <button
              onClick={handlePrintPDF}
              className="flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs shadow-md shadow-indigo-600/20 transition-all active:scale-95 cursor-pointer"
            >
              <Printer size={14} />
              <span>Print / Save as PDF</span>
            </button>
            <button
              onClick={handleDownloadCSV}
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-750 border border-slate-700 text-slate-200 font-medium text-xs transition-all cursor-pointer"
            >
              <FileSpreadsheet size={14} className="text-emerald-400" />
              <span>CSV Spreadsheet</span>
            </button>
            <button
              onClick={handleDownloadMarkdownCheatSheet}
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-750 border border-slate-700 text-slate-200 font-medium text-xs transition-all cursor-pointer"
            >
              <FileCode size={14} className="text-purple-400" />
              <span>Markdown Cheat-Sheet</span>
            </button>
            <button
              onClick={handleDownloadJSON}
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-750 border border-slate-700 text-slate-200 font-medium text-xs transition-all cursor-pointer"
            >
              <FileText size={14} className="text-indigo-400" />
              <span>Raw JSON Data</span>
            </button>
          </div>
        </div>

        {/* Studio View Selector Tabs */}
        <div className="flex items-center space-x-2 border-b border-slate-800/80 pb-2">
          <button
            onClick={() => setActiveTab('preview')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              activeTab === 'preview' 
                ? 'bg-indigo-600/15 text-indigo-300 border border-indigo-500/30' 
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Curriculum Blueprint & Audit Report
          </button>
          <button
            onClick={() => setActiveTab('certificate')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              activeTab === 'certificate' 
                ? 'bg-purple-600/15 text-purple-300 border border-purple-500/30' 
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Verified Mastery Certificate
          </button>
          <button
            onClick={() => setActiveTab('cheatsheet')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              activeTab === 'cheatsheet' 
                ? 'bg-emerald-600/15 text-emerald-300 border border-emerald-500/30' 
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            High-Yield Study Cheat-Sheet
          </button>
        </div>
      </div>

      {loading ? (
        <div className="p-20 text-center text-slate-500 space-y-3">
          <RotateCw className="h-8 w-8 animate-spin mx-auto text-indigo-400" />
          <p className="text-sm font-medium">Compiling complete curriculum and graph analytics...</p>
        </div>
      ) : error ? (
        <div className="p-6 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 text-center">
          <p className="font-semibold">{error}</p>
          <button onClick={fetchReportData} className="mt-3 px-4 py-1.5 rounded-lg bg-red-600/20 text-xs font-bold text-red-300">
            Retry Compilation
          </button>
        </div>
      ) : reportData ? (
        <div>
          
          {/* ─── TAB 1: CURRICULUM BLUEPRINT & AUDIT REPORT ─── */}
          {activeTab === 'preview' && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 md:p-12 text-slate-100 shadow-2xl space-y-10 print:bg-white print:text-black print:border-none print:p-0">
              
              {/* Document Header */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-b border-slate-800 print:border-black pb-8">
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-extrabold tracking-widest text-indigo-400 print:text-indigo-800 uppercase">MK-Path Adaptive Learning Framework</span>
                  </div>
                  <h2 className="text-3xl font-black text-white print:text-black tracking-tight">
                    Curriculum Audit & Knowledge Graph Report
                  </h2>
                  <p className="text-xs text-slate-400 print:text-gray-600">
                    Comprehensive breakdown of mined knowledge concepts, prerequisite relationships, and cognitive Bayesian mastery status.
                  </p>
                </div>

                <div className="text-right space-y-1 text-xs text-slate-400 print:text-gray-700 border-l-2 border-indigo-500 pl-4">
                  <div><strong className="text-white print:text-black">Learner:</strong> {reportData.learner.display_name}</div>
                  <div><strong className="text-white print:text-black">Account Email:</strong> {reportData.learner.email}</div>
                  <div><strong className="text-white print:text-black">Compiled At:</strong> {new Date(reportData.generated_at).toLocaleString()}</div>
                  <div><strong className="text-white print:text-black">Gamification Level:</strong> Level {reportData.learner.level} ({reportData.learner.level_name}) • {reportData.learner.xp} XP</div>
                </div>
              </div>

              {/* Executive Summary Metrics Box */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 print:border-gray-300 print:bg-gray-50">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Average Decayed Mastery</span>
                  <div className="text-2xl font-black text-indigo-400 print:text-black mt-1">
                    {reportData.summary.average_mastery}%
                  </div>
                  <span className="text-[10px] text-slate-500">Bayesian Knowledge Tracing</span>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 print:border-gray-300 print:bg-gray-50">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Total Concepts</span>
                  <div className="text-2xl font-black text-white print:text-black mt-1">
                    {reportData.summary.total_concepts}
                  </div>
                  <span className="text-[10px] text-slate-500">Multimodal extracted units</span>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 print:border-gray-300 print:bg-gray-50">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Dependency Edges</span>
                  <div className="text-2xl font-black text-purple-400 print:text-black mt-1">
                    {reportData.summary.total_relationships}
                  </div>
                  <span className="text-[10px] text-slate-500">Prerequisite & build relations</span>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 print:border-gray-300 print:bg-gray-50">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Spaced Active Recall Cards</span>
                  <div className="text-2xl font-black text-emerald-400 print:text-black mt-1">
                    {reportData.summary.total_flashcards}
                  </div>
                  <span className="text-[10px] text-slate-500">SM-2 repetition decks</span>
                </div>
              </div>

              {/* Mastery Distribution Bar */}
              <div className="p-5 rounded-xl bg-slate-950/40 border border-slate-800 print:border-gray-300 space-y-3">
                <div className="flex justify-between items-center text-xs font-bold">
                  <span className="text-slate-300 print:text-black">Mastery Category Breakdown</span>
                  <div className="flex items-center space-x-3 text-[11px]">
                    <span className="text-emerald-400">Mastered: {reportData.summary.category_distribution.mastered || 0}</span>
                    <span className="text-indigo-400">Proficient: {reportData.summary.category_distribution.proficient || 0}</span>
                    <span className="text-amber-400">Learning: {reportData.summary.category_distribution.learning || 0}</span>
                    <span className="text-red-400">Weak: {reportData.summary.category_distribution.weak || 0}</span>
                  </div>
                </div>
                
                <div className="h-2.5 w-full bg-slate-800 rounded-full flex overflow-hidden">
                  {reportData.summary.total_concepts > 0 && (
                    <>
                      <div 
                        className="bg-emerald-500 h-full transition-all"
                        style={{ width: `${((reportData.summary.category_distribution.mastered || 0) / reportData.summary.total_concepts) * 100}%` }}
                        title="Mastered"
                      />
                      <div 
                        className="bg-indigo-500 h-full transition-all"
                        style={{ width: `${((reportData.summary.category_distribution.proficient || 0) / reportData.summary.total_concepts) * 100}%` }}
                        title="Proficient"
                      />
                      <div 
                        className="bg-amber-500 h-full transition-all"
                        style={{ width: `${((reportData.summary.category_distribution.learning || 0) / reportData.summary.total_concepts) * 100}%` }}
                        title="Learning"
                      />
                      <div 
                        className="bg-red-500 h-full transition-all"
                        style={{ width: `${((reportData.summary.category_distribution.weak || 0) / reportData.summary.total_concepts) * 100}%` }}
                        title="Weak"
                      />
                    </>
                  )}
                </div>
              </div>

              {/* Complete Table of Concepts */}
              <div className="space-y-4">
                <h3 className="text-base font-bold text-white print:text-black flex items-center space-x-2">
                  <BookOpen size={18} className="text-indigo-400 print:text-black" />
                  <span>Curriculum Concepts & Mastery Audit</span>
                </h3>

                <div className="overflow-x-auto rounded-xl border border-slate-800 print:border-gray-300">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950/80 print:bg-gray-100 text-slate-400 print:text-black border-b border-slate-800 print:border-gray-300">
                      <tr>
                        <th className="py-3 px-4 font-bold">Concept Name</th>
                        <th className="py-3 px-3 font-bold">Difficulty</th>
                        <th className="py-3 px-3 font-bold">Mastery Score</th>
                        <th className="py-3 px-3 font-bold">Status</th>
                        <th className="py-3 px-3 font-bold">Exam / Industry</th>
                        <th className="py-3 px-4 font-bold">Prerequisites</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 print:divide-gray-200">
                      {reportData.concepts.map((c, idx) => (
                        <tr key={idx} className="hover:bg-slate-850/40 print:hover:bg-transparent">
                          <td className="py-3 px-4 font-semibold text-white print:text-black">
                            {c.name}
                            <div className="text-[10px] text-slate-400 print:text-gray-600 font-normal line-clamp-1 mt-0.5 max-w-sm">
                              {c.description}
                            </div>
                          </td>
                          <td className="py-3 px-3 uppercase text-[10px] font-bold text-slate-400 print:text-gray-700">
                            {c.difficulty}
                          </td>
                          <td className="py-3 px-3 font-bold text-white print:text-black">
                            {c.mastery_score !== null ? `${c.mastery_score}%` : '—'}
                          </td>
                          <td className="py-3 px-3">
                            <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                              c.mastery_category === 'mastered' ? 'bg-emerald-500/10 text-emerald-400' :
                              c.mastery_category === 'proficient' ? 'bg-indigo-500/10 text-indigo-400' :
                              c.mastery_category === 'learning' ? 'bg-amber-500/10 text-amber-400' :
                              c.mastery_category === 'weak' ? 'bg-red-500/10 text-red-400' :
                              'bg-slate-800 text-slate-400'
                            }`}>
                              {c.mastery_category}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-[10px] text-slate-400 print:text-gray-700">
                            {c.exam_relevance}% / {c.industry_relevance}%
                          </td>
                          <td className="py-3 px-4 text-[10px] text-slate-400 print:text-gray-700">
                            {c.prerequisites?.length > 0 ? c.prerequisites.join(', ') : 'None'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Source Ingestion Audit Footer */}
              <div className="pt-6 border-t border-slate-800 print:border-gray-300 text-[11px] text-slate-500 print:text-gray-600 flex flex-col md:flex-row justify-between items-center gap-4">
                <div>
                  Ingested Source Materials: {reportData.materials.map(m => m.title).join(', ') || 'None'}
                </div>
                <div className="flex items-center space-x-2">
                  <ShieldCheck size={14} className="text-indigo-400 print:text-black" />
                  <span>Authenticated & Verified by MK-Path Cognitive Knowledge Engine</span>
                </div>
              </div>
            </div>
          )}

          {/* ─── TAB 2: VERIFIED MASTERY CERTIFICATE ─── */}
          {activeTab === 'certificate' && (
            <div className="max-w-4xl mx-auto bg-gradient-to-b from-slate-900 via-slate-950 to-slate-900 border-4 border-indigo-500/30 rounded-3xl p-10 md:p-16 shadow-2xl relative overflow-hidden print:border-4 print:border-black print:bg-white print:text-black">
              
              {/* Certificate Decorative Background Elements */}
              <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />
              <div className="absolute bottom-0 left-0 w-64 h-64 bg-purple-600/10 rounded-full blur-3xl pointer-events-none" />
              
              <div className="text-center space-y-8 relative z-10">
                <div className="space-y-2">
                  <div className="w-16 h-16 mx-auto rounded-2xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 flex items-center justify-center shadow-lg">
                    <Award size={36} />
                  </div>
                  <span className="text-xs font-bold uppercase tracking-widest text-indigo-400 print:text-indigo-800">
                    Certificate of Knowledge Mastery
                  </span>
                </div>

                <div className="space-y-3">
                  <h1 className="text-3xl md:text-5xl font-extrabold text-white print:text-black tracking-tight">
                    {reportData.learner.display_name}
                  </h1>
                  <p className="text-xs md:text-sm text-slate-400 print:text-gray-600 max-w-xl mx-auto leading-relaxed">
                    has successfully established verifiable concept mastery within the MK-Path Adaptive Cognitive Architecture across all ingested multimodal learning modules.
                  </p>
                </div>

                {/* Score Showcase */}
                <div className="grid grid-cols-3 gap-4 max-w-lg mx-auto py-4 border-y border-slate-800/80 print:border-gray-300">
                  <div>
                    <div className="text-2xl md:text-3xl font-black text-indigo-400 print:text-black">
                      {reportData.summary.average_mastery}%
                    </div>
                    <div className="text-[11px] text-slate-500 font-bold uppercase mt-1">Average Mastery</div>
                  </div>
                  <div>
                    <div className="text-2xl md:text-3xl font-black text-purple-400 print:text-black">
                      {reportData.summary.total_concepts}
                    </div>
                    <div className="text-[11px] text-slate-500 font-bold uppercase mt-1">Concepts Mastered</div>
                  </div>
                  <div>
                    <div className="text-2xl md:text-3xl font-black text-emerald-400 print:text-black">
                      Level {reportData.learner.level}
                    </div>
                    <div className="text-[11px] text-slate-500 font-bold uppercase mt-1">{reportData.learner.level_name}</div>
                  </div>
                </div>

                {/* Sign-off details */}
                <div className="pt-6 flex flex-col md:flex-row items-center justify-between text-xs text-slate-400 print:text-gray-700 gap-6">
                  <div className="text-left">
                    <div className="font-bold text-white print:text-black">MK-Path Core Engine</div>
                    <div className="text-[11px] text-slate-500">Bayesian Cognitive Analytics</div>
                  </div>

                  <div className="text-center font-mono text-[11px] px-4 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-400 print:border-gray-300">
                    ID: MKP-CERT-{reportData.learner.email.slice(0, 4).toUpperCase()}-{new Date().getFullYear()}
                  </div>

                  <div className="text-right">
                    <div className="font-bold text-white print:text-black">{new Date(reportData.generated_at).toLocaleDateString()}</div>
                    <div className="text-[11px] text-slate-500">Date of Verification</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ─── TAB 3: HIGH-YIELD STUDY CHEAT-SHEET ─── */}
          {activeTab === 'cheatsheet' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                    <Zap className="text-amber-400" size={20} />
                    <span>Active Study Cheat-Sheet</span>
                  </h3>
                  <p className="text-xs text-slate-400">Printable, high-density concept flash notes designed for rapid pre-exam review.</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {reportData.concepts.map((c, idx) => (
                  <div 
                    key={idx} 
                    className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all space-y-3 shadow-md"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-extrabold text-indigo-300 bg-indigo-500/10 px-2.5 py-1 rounded-lg border border-indigo-500/20">
                        {idx + 1}. {c.name}
                      </span>
                      <span className="text-[10px] uppercase font-bold text-slate-400">
                        {c.difficulty} • {c.exam_relevance}% Exam
                      </span>
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/40 p-3.5 rounded-xl border border-slate-800/80">
                      {c.description}
                    </p>

                    {c.prerequisites?.length > 0 && (
                      <div className="text-[10px] text-slate-500 flex items-center space-x-1.5 pt-1">
                        <span className="font-semibold text-slate-400">Prerequisites:</span>
                        <span>{c.prerequisites.join(', ')}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>
      ) : null}
    </div>
  )
}
