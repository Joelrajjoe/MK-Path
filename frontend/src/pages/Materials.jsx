import React, { useState, useEffect, useRef } from 'react'
import { useAuth } from '@clerk/react'
import { 
  FileText, 
  UploadCloud, 
  Info, 
  AlertTriangle, 
  CheckCircle2, 
  Loader2, 
  Trash2,
  Eye,
  Calendar,
  Layers,
  X,
  Copy,
  Check,
  Sparkles,
  BookOpen,
  Award,
  Activity,
  Image,
  Music,
  Video,
  Clock
} from 'lucide-react'

export default function Materials() {
  const { getToken } = useAuth()
  const fileInputRef = useRef(null)
  
  const [materials, setMaterials] = useState([])
  const [concepts, setConcepts] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploadStatus, setUploadStatus] = useState('idle') // idle, uploading, processing, success, error
  const [uploadError, setUploadError] = useState(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  
  // Drag and drop states
  const [dragActive, setDragActive] = useState(false)
  
  // Text preview drawer states
  const [selectedMaterial, setSelectedMaterial] = useState(null)
  const [copied, setCopied] = useState(false)
  const [activeTab, setActiveTab] = useState('text') // text, concepts
  const [extractStatus, setExtractStatus] = useState('idle') // idle, extracting, success, error
  const [extractError, setExtractError] = useState(null)

  // Fetch materials
  const fetchMaterials = async () => {
    try {
      const token = await getToken()
      const res = await fetch('http://localhost:8000/api/materials', {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })
      if (!res.ok) throw new Error('Failed to retrieve materials')
      const data = await res.json()
      setMaterials(data)
    } catch (err) {
      console.error(err)
    }
  }

  // Fetch concepts
  const fetchConcepts = async () => {
    try {
      const token = await getToken()
      const res = await fetch('http://localhost:8000/api/concepts', {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })
      if (!res.ok) throw new Error('Failed to retrieve concepts')
      const data = await res.json()
      setConcepts(data)
    } catch (err) {
      console.error(err)
    }
  }

  // Delete a material (cascade deletes concepts, questions, attempts, mastery)
  const handleDeleteMaterial = async (e, matId) => {
    e.stopPropagation() // Don't open the drawer
    if (!window.confirm('Delete this material? This will also remove its concepts, questions, and assessment history.')) return
    try {
      const token = await getToken()
      const res = await fetch(`http://localhost:8000/api/materials/${matId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!res.ok) throw new Error('Delete failed')
      // Remove from local state
      setMaterials(prev => prev.filter(m => m._id !== matId))
      setConcepts(prev => prev.filter(c => c.material_id !== matId))
      if (selectedMaterial?._id === matId) setSelectedMaterial(null)
    } catch (err) {
      alert('Failed to delete: ' + err.message)
    }
  }

  // Initial load
  useEffect(() => {
    const initData = async () => {
      setLoading(true)
      await Promise.all([fetchMaterials(), fetchConcepts()])
      setLoading(false)
    }
    initData()
  }, [getToken])

  // Format file size
  const formatBytes = (bytes) => {
    if (!bytes) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  // Handle file upload
  const handleUploadFile = async (file) => {
    if (!file) return
    
    // File validation
    const allowedExtensions = ['.pdf', '.txt', '.png', '.jpg', '.jpeg', '.mp3', '.wav', '.m4a', '.mp4', '.avi', '.webm'];
    const lowerName = file.name.toLowerCase();
    const isAllowed = allowedExtensions.some(ext => lowerName.endsWith(ext));
    if (!isAllowed) {
      setUploadStatus('error')
      setUploadError('Unsupported file format. Accepted types: PDF, TXT, Images, Audio, Video.')
      return
    }

    if (file.size > 25 * 1024 * 1024) {
      setUploadStatus('error')
      setUploadError('File size exceeds the maximum limit of 25MB.')
      return
    }

    try {
      setUploadStatus('uploading')
      setUploadProgress(20)
      setUploadError(null)

      const token = await getToken()
      const formData = new FormData()
      formData.append('file', file)

      setUploadProgress(50)
      setUploadStatus('processing') // File sent to API, backend runs PyMuPDF extraction

      const res = await fetch('http://localhost:8000/api/materials/upload', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`
        },
        body: formData
      })

      setUploadProgress(90)
      
      const data = await res.json()
      
      if (!res.ok) {
        throw new Error(data.detail || 'Upload failed')
      }

      setUploadProgress(100)
      
      if (data.status === 'failed') {
        setUploadStatus('error')
        setUploadError('PDF uploaded but text extraction failed (empty or scanned image-only).')
      } else {
        setUploadStatus('success')
      }
      
      // Refresh list
      await fetchMaterials()
      
      // Reset status after a delay
      setTimeout(() => {
        setUploadStatus('idle')
        setUploadProgress(0)
      }, 3000)

    } catch (err) {
      console.error(err)
      setUploadStatus('error')
      setUploadError(err.message || 'An error occurred during file upload.')
    }
  }

  // Drag handlers
  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleUploadFile(e.dataTransfer.files[0])
    }
  }

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleUploadFile(e.target.files[0])
    }
  }

  const handleCopyText = (text) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Extract concepts trigger
  const handleExtractConcepts = async () => {
    if (!selectedMaterial) return
    try {
      setExtractStatus('extracting')
      setExtractError(null)
      const token = await getToken()
      
      const res = await fetch(`http://localhost:8000/api/materials/${selectedMaterial._id}/extract-concepts`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`
        }
      })
      
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail || 'AI Concept extraction failed')
      }
      
      setExtractStatus('success')
      
      // Refresh concepts list
      await fetchConcepts()
      
      setTimeout(() => {
        setExtractStatus('idle')
      }, 2000)
    } catch (err) {
      console.error(err)
      setExtractStatus('error')
      setExtractError(err.message || 'Failed to extract concepts.')
    }
  }

  // Filter concepts for active material
  const materialConcepts = selectedMaterial 
    ? concepts.filter(c => c.material_id === selectedMaterial._id)
    : []

  return (
    <div className="flex h-full relative overflow-hidden">
      
      {/* Left Pane: Uploader and List */}
      <div className={`flex-1 space-y-8 pr-0 lg:pr-6 transition-all duration-300 ${selectedMaterial ? 'lg:mr-[400px] xl:mr-[480px]' : ''}`}>
        
        {/* Upload Container */}
        <div 
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current.click()}
          className={`border-2 border-dashed rounded-2xl p-10 text-center space-y-4 cursor-pointer transition duration-300 glow-card ${
            dragActive 
              ? 'border-indigo-500 bg-indigo-500/10' 
              : 'border-slate-800 bg-slate-900/20 hover:bg-slate-900/30 hover:border-slate-700'
          }`}
        >
          <input 
            ref={fileInputRef}
            type="file" 
            accept=".pdf,.txt,.png,.jpg,.jpeg,.bmp,.webp,.mp3,.wav,.m4a,.ogg,.flac,.mp4,.avi,.webm,.mkv,.mov"
            className="hidden" 
            onChange={handleFileChange}
          />
          
          <div className="mx-auto w-fit p-4 bg-indigo-500/10 text-indigo-400 rounded-full border border-indigo-500/20">
            {uploadStatus === 'uploading' || uploadStatus === 'processing' ? (
              <Loader2 className="h-8 w-8 animate-spin" />
            ) : (
              <UploadCloud className="h-8 w-8" />
            )}
          </div>

          <div className="space-y-1.5">
            {uploadStatus === 'idle' && (
              <>
                <p className="font-bold text-white text-sm">Drag & drop your study material here, or click to browse</p>
                <p className="text-xs text-slate-500">Supports PDF, TXT, Images (PNG/JPG), Audio (MP3/WAV/M4A), Video (MP4/AVI/WEBM) · Max 25MB</p>
              </>
            )}
            {(uploadStatus === 'uploading' || uploadStatus === 'processing') && (
              <>
                <p className="font-bold text-indigo-400 text-sm">
                  {uploadStatus === 'uploading' ? 'Uploading file bytes...' : 'Extracting PDF layout text...'}
                </p>
                <div className="w-48 mx-auto bg-slate-800 h-1.5 rounded-full overflow-hidden mt-2">
                  <div 
                    className="bg-indigo-500 h-full transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  ></div>
                </div>
              </>
            )}
            {uploadStatus === 'success' && (
              <div className="flex flex-col items-center space-y-1 text-emerald-400">
                <CheckCircle2 size={24} />
                <p className="font-bold text-sm">PDF Processed and Text Extracted!</p>
              </div>
            )}
            {uploadStatus === 'error' && (
              <div className="flex flex-col items-center space-y-1 text-rose-400">
                <AlertTriangle size={24} />
                <p className="font-bold text-sm">Ingestion Failed</p>
                <p className="text-xs text-rose-500 max-w-xs">{uploadError}</p>
              </div>
            )}
          </div>
        </div>

        {/* Ingested List Table */}
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">My Study Materials</h3>
            <span className="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full font-semibold">
              {materials.length} files
            </span>
          </div>

          {loading && materials.length === 0 ? (
            <div className="flex justify-center py-10">
              <Loader2 className="h-6 w-6 animate-spin text-slate-500" />
            </div>
          ) : materials.length === 0 ? (
            <div className="border border-slate-800/80 bg-slate-900/10 rounded-xl p-12 text-center space-y-3">
              <div className="mx-auto w-fit p-3 bg-slate-850 text-slate-500 rounded-lg">
                <FileText className="h-6 w-6" />
              </div>
              <div className="space-y-1">
                <p className="font-bold text-sm text-slate-300">No study materials yet.</p>
                <p className="text-xs text-slate-500 max-w-xs mx-auto">
                  Drag and drop a PDF, text, image, audio, or video file above to start text compilation.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {materials.map((mat) => {
                const getMatIcon = (sourceType) => {
                  switch (sourceType) {
                    case 'txt':
                    case 'text':
                      return <FileText size={18} />
                    case 'image':
                      return <Image size={18} />
                    case 'audio':
                      return <Music size={18} />
                    case 'video':
                      return <Video size={18} />
                    default:
                      return <FileText size={18} />
                  }
                };

                const formatDuration = (secs) => {
                  if (secs === null || secs === undefined) return '';
                  const m = Math.floor(secs / 60);
                  const s = Math.floor(secs % 60);
                  return `${m}:${s.toString().padStart(2, '0')}`;
                };

                return (
                  <div 
                    key={mat._id}
                    onClick={() => {
                      setSelectedMaterial(mat)
                      setActiveTab('text')
                      setExtractStatus('idle')
                    }}
                    className={`group p-4 rounded-xl border transition flex items-center justify-between cursor-pointer ${
                      selectedMaterial?._id === mat._id 
                        ? 'border-indigo-500/50 bg-indigo-500/5 glow-indigo' 
                        : 'border-slate-800/80 bg-slate-900/30 hover:border-slate-700 hover:bg-slate-900/50'
                    }`}
                  >
                    <div className="flex items-center space-x-3 truncate">
                      <div className={`p-2 rounded-lg ${mat.status === 'processed' ? 'bg-indigo-500/10 text-indigo-400' : 'bg-rose-500/10 text-rose-400'}`}>
                        {getMatIcon(mat.source_type)}
                      </div>
                      <div className="flex flex-col truncate">
                        <span className="text-sm font-bold text-white truncate">{mat.file_name}</span>
                        <div className="flex items-center space-x-2 text-[10px] text-slate-500 mt-0.5">
                          <span className="flex items-center space-x-1">
                            <Calendar size={10} />
                            <span>{new Date(mat.created_at).toLocaleDateString()}</span>
                          </span>
                          <span>•</span>
                          <span>{formatBytes(mat.file_size)}</span>
                          {mat.page_count && (
                            <>
                              <span>•</span>
                              <span>{mat.page_count} pages</span>
                            </>
                          )}
                          {mat.duration && (
                            <>
                              <span>•</span>
                              <span className="flex items-center space-x-0.5">
                                <Clock size={10} />
                                <span>{formatDuration(mat.duration)}</span>
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-3">
                      {mat.extraction_method && mat.extraction_method !== 'direct_text' && (
                        <span className="text-[9px] bg-slate-850 text-indigo-300 border border-slate-800 px-1.5 py-0.5 rounded uppercase font-extrabold tracking-wider">
                          {mat.extraction_method}
                        </span>
                      )}
                      {mat.status === 'processed' ? (
                        <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/10 px-2 py-0.5 rounded font-semibold">
                          Processed
                        </span>
                      ) : (
                        <span className="text-[10px] bg-rose-500/10 text-rose-400 border border-rose-500/10 px-2 py-0.5 rounded font-semibold">
                          Failed
                        </span>
                      )}
                      <button className="p-1.5 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition">
                        <Eye size={14} />
                      </button>
                      <button
                        onClick={(e) => handleDeleteMaterial(e, mat._id)}
                        className="p-1.5 hover:bg-red-950/40 rounded-lg text-slate-600 hover:text-red-400 transition opacity-0 group-hover:opacity-100"
                        title="Delete material"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Tip Banner */}
        <div className="flex items-start space-x-3 p-4 rounded-xl bg-indigo-950/10 border border-indigo-900/30 text-indigo-300 text-xs">
          <Info size={16} className="flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-bold">Multimodal Ingestion Pipeline</p>
            <p className="leading-relaxed">
              Once text parsing is complete, click on any material card to review the extracted text layout blocks. Run the AI Concept Miner to extract structured educational nodes.
            </p>
          </div>
        </div>
      </div>

      {/* Right Drawer Panel: Extracted Text & Concept Tabs */}
      {selectedMaterial && (
        <div className="fixed inset-y-0 right-0 z-30 w-full sm:w-[420px] md:w-[480px] bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col animate-in slide-in-from-right duration-300">
          
          {/* Header */}
          <div className="p-5 border-b border-slate-800 bg-slate-950/20 flex items-center justify-between">
            <div className="flex items-center space-x-2.5 truncate">
              <FileText size={18} className="text-indigo-400" />
              <h3 className="font-bold text-white text-sm truncate">{selectedMaterial.file_name}</h3>
            </div>
            <button 
              onClick={() => setSelectedMaterial(null)}
              className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
            >
              <X size={16} />
            </button>
          </div>

          {/* Tabs Bar */}
          <div className="flex border-b border-slate-800 bg-slate-950/30">
            <button
              onClick={() => setActiveTab('text')}
              className={`flex-1 py-3 text-xs font-bold transition border-b-2 ${
                activeTab === 'text' 
                  ? 'border-indigo-500 text-white' 
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              Extracted Text
            </button>
            <button
              onClick={() => setActiveTab('concepts')}
              className={`flex-1 py-3 text-xs font-bold transition border-b-2 flex items-center justify-center space-x-1.5 ${
                activeTab === 'concepts' 
                  ? 'border-indigo-500 text-white' 
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Sparkles size={12} className={activeTab === 'concepts' ? 'text-indigo-400' : 'text-slate-400'} />
              <span>AI Concepts</span>
              {materialConcepts.length > 0 && (
                <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-1.5 py-0.2 rounded-full">
                  {materialConcepts.length}
                </span>
              )}
            </button>
          </div>

          {/* Drawer Body Panel */}
          <div className="flex-1 overflow-y-auto bg-slate-950/50 flex flex-col">
            {activeTab === 'text' ? (
              // --- Tab 1: Raw Text Output ---
              <div className="p-5 font-mono text-xs leading-relaxed text-slate-300 select-text whitespace-pre-wrap flex-1">
                {selectedMaterial.status === 'failed' ? (
                  <div className="flex flex-col items-center justify-center h-full text-center space-y-3 py-20">
                    <AlertTriangle size={32} className="text-rose-400" />
                    <p className="font-sans font-bold text-slate-200">Text Extraction Failed</p>
                    <p className="font-sans text-[11px] text-slate-500 max-w-xs">
                      This document could not be parsed. This occurs if the PDF consists entirely of images (scanned document) and lacks metadata.
                    </p>
                  </div>
                ) : selectedMaterial.raw_text ? (
                  selectedMaterial.raw_text
                ) : (
                  <span className="text-slate-500 italic">No extractable text.</span>
                )}
              </div>
            ) : (
              // --- Tab 2: AI Concepts Miner ---
              <div className="p-5 flex-1 flex flex-col space-y-4">
                {selectedMaterial.status === 'failed' ? (
                  <div className="text-center py-10 space-y-2">
                    <AlertTriangle size={24} className="text-rose-400 mx-auto" />
                    <p className="font-bold text-sm text-slate-300">Extraction Unavailable</p>
                    <p className="text-xs text-slate-500">Cannot extract concepts from a failed document.</p>
                  </div>
                ) : extractStatus === 'extracting' ? (
                  // Loading state
                  <div className="flex-1 flex flex-col items-center justify-center text-center space-y-4 py-20">
                    <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
                    <div className="space-y-1">
                      <p className="font-bold text-sm text-slate-250">Mining Knowledge Concepts...</p>
                      <p className="text-xs text-slate-500 max-w-xs">
                        AI is digesting the document structure, extracting prerequisite mappings, and modeling target scores.
                      </p>
                    </div>
                  </div>
                ) : materialConcepts.length === 0 ? (
                  // Trigger state (if not extracted yet)
                  <div className="flex-1 flex flex-col items-center justify-center text-center space-y-4 py-16">
                    <div className="p-4 bg-indigo-500/10 text-indigo-400 border border-indigo-500/25 rounded-2xl">
                      <Sparkles className="h-8 w-8" />
                    </div>
                    <div className="space-y-2">
                      <p className="font-bold text-sm text-white">Extract Core Study Concepts</p>
                      <p className="text-xs text-slate-550 max-w-xs leading-relaxed">
                        Trigger the multi-provider AI mapping pipeline to parse this material into distinct curriculum concepts and requirements.
                      </p>
                    </div>
                    <button
                      onClick={handleExtractConcepts}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-bold transition flex items-center space-x-1.5"
                    >
                      <Sparkles size={12} />
                      <span>Extract Concepts</span>
                    </button>
                    {extractStatus === 'error' && (
                      <p className="text-[11px] text-rose-400 max-w-xs mt-2">{extractError}</p>
                    )}
                  </div>
                ) : (
                  // Concept Listing
                  <div className="space-y-4">
                    <div className="flex items-center justify-between text-xs text-slate-400 pb-1 border-b border-slate-800">
                      <span className="font-bold uppercase tracking-wider">Concept Catalog</span>
                      <span>{materialConcepts.length} units</span>
                    </div>

                    <div className="space-y-3.5">
                      {materialConcepts.map((c, i) => (
                        <div key={i} className="p-4 bg-slate-900/80 border border-slate-800/80 rounded-xl space-y-3">
                          
                          {/* Name & Difficulty */}
                          <div className="flex items-start justify-between space-x-2">
                            <span className="text-sm font-bold text-white leading-tight">{c.name}</span>
                            <span className={`text-[9px] px-1.5 py-0.5 rounded uppercase font-bold flex-shrink-0 ${
                              c.difficulty === 'basic' 
                                ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/10'
                                : c.difficulty === 'intermediate'
                                  ? 'bg-amber-500/10 text-amber-400 border border-amber-500/10'
                                  : 'bg-rose-500/10 text-rose-400 border border-rose-500/10'
                            }`}>
                              {c.difficulty}
                            </span>
                          </div>

                          {/* Description */}
                          <p className="text-xs text-slate-400 leading-relaxed font-sans">{c.description}</p>

                          {/* Metrics progress bars */}
                          <div className="space-y-2 pt-1 font-sans">
                            {/* Exam Relevance */}
                            <div className="space-y-0.5">
                              <div className="flex justify-between text-[10px] text-slate-500">
                                <span>Exam Relevance</span>
                                <span className="text-slate-400 font-bold">{c.exam_relevance}%</span>
                              </div>
                              <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                                <div 
                                  className="bg-indigo-500 h-full rounded-full" 
                                  style={{ width: `${c.exam_relevance}%` }}
                                ></div>
                              </div>
                            </div>
                            {/* Industry Relevance */}
                            <div className="space-y-0.5">
                              <div className="flex justify-between text-[10px] text-slate-500">
                                <span>Industry Relevance</span>
                                <span className="text-slate-400 font-bold">{c.industry_relevance}%</span>
                              </div>
                              <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                                <div 
                                  className="bg-violet-500 h-full rounded-full" 
                                  style={{ width: `${c.industry_relevance}%` }}
                                ></div>
                              </div>
                            </div>
                          </div>

                          {/* Prerequisites list */}
                          {c.prerequisites && c.prerequisites.length > 0 && (
                            <div className="pt-2 border-t border-slate-850 flex items-center space-x-1.5 flex-wrap">
                              <span className="text-[9px] text-slate-500 uppercase font-semibold">Requires:</span>
                              {c.prerequisites.map((prereq, pidx) => (
                                <span key={pidx} className="text-[9px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded font-medium">
                                  {prereq}
                                </span>
                              ))}
                            </div>
                          )}

                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer controls */}
          {activeTab === 'text' && selectedMaterial.status === 'processed' && selectedMaterial.raw_text && (
            <div className="p-4 border-t border-slate-800 bg-slate-950/20 flex justify-end">
              <button 
                onClick={() => handleCopyText(selectedMaterial.raw_text)}
                className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-bold text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition"
              >
                {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                <span>{copied ? 'Copied' : 'Copy Text'}</span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
