import React, { useState, useEffect } from 'react'
import { Accessibility as AccessibilityIcon, Volume2, Type, Eye, Keyboard, CheckCircle } from 'lucide-react'

export default function AccessibilityPage() {
  const [ttsEnabled, setTtsEnabled] = useState(() => localStorage.getItem('mkp_tts') === 'true')
  const [ttsRate, setTtsRate] = useState(() => parseFloat(localStorage.getItem('mkp_tts_rate') || '1'))
  const [ttsPitch, setTtsPitch] = useState(1.0)
  const [fontSize, setFontSize] = useState(() => localStorage.getItem('mkp_font_size') || 'medium')
  const [reducedMotion, setReducedMotion] = useState(() => localStorage.getItem('mkp_reduced_motion') === 'true')
  const [highContrast, setHighContrast] = useState(() => localStorage.getItem('mkp_high_contrast') === 'true')
  const [saved, setSaved] = useState(false)
  const [voices, setVoices] = useState([])
  const [selectedVoice, setSelectedVoice] = useState('')

  useEffect(() => {
    const loadVoices = () => {
      const v = window.speechSynthesis?.getVoices() || []
      setVoices(v)
      if (!selectedVoice && v.length > 0) setSelectedVoice(v[0].name)
    }
    loadVoices()
    window.speechSynthesis?.addEventListener('voiceschanged', loadVoices)
    return () => window.speechSynthesis?.removeEventListener('voiceschanged', loadVoices)
  }, [])

  const applyAndSave = () => {
    localStorage.setItem('mkp_tts', ttsEnabled)
    localStorage.setItem('mkp_tts_rate', ttsRate)
    localStorage.setItem('mkp_font_size', fontSize)
    localStorage.setItem('mkp_reduced_motion', reducedMotion)
    localStorage.setItem('mkp_high_contrast', highContrast)
    const fontMap = { small: '13px', medium: '15px', large: '17px', xlarge: '20px' }
    document.documentElement.style.setProperty('--mkp-font-size', fontMap[fontSize] || '15px')
    document.documentElement.classList.toggle('reduce-motion', reducedMotion)
    document.documentElement.classList.toggle('high-contrast', highContrast)
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  const testTts = () => {
    if (!window.speechSynthesis) return
    const utt = new SpeechSynthesisUtterance('MK-Path text-to-speech is working correctly.')
    utt.rate = ttsRate
    utt.pitch = ttsPitch
    const voice = voices.find(v => v.name === selectedVoice)
    if (voice) utt.voice = voice
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(utt)
  }

  return (
    <div className="space-y-8 max-w-3xl mx-auto">
      <div className="flex flex-col space-y-1">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Accessibility & Voice Controls</h1>
        <p className="text-slate-400 text-sm">Configure text-to-speech, font size, motion, and contrast settings.</p>
      </div>

      {/* Text-to-Speech */}
      <Card icon={<Volume2 size={16} />} title="Text-to-Speech" desc="Browser speech synthesis controls">
        <div className="space-y-4">
          <ToggleRow label="Enable Text-to-Speech" checked={ttsEnabled} onChange={setTtsEnabled} />
          {ttsEnabled && (
            <>
              <SliderRow label={`Speech Rate: ${ttsRate}×`} min={0.5} max={2} step={0.1} value={ttsRate} onChange={setTtsRate} />
              <SliderRow label={`Pitch: ${ttsPitch}`} min={0.5} max={2} step={0.1} value={ttsPitch} onChange={setTtsPitch} />
              {voices.length > 0 && (
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Voice</label>
                  <select value={selectedVoice} onChange={e => setSelectedVoice(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white outline-none focus:border-indigo-500">
                    {voices.map(v => <option key={v.name} value={v.name}>{v.name} ({v.lang})</option>)}
                  </select>
                </div>
              )}
              <button onClick={testTts}
                className="text-sm bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-xl font-semibold transition">
                🔊 Test Voice
              </button>
            </>
          )}
        </div>
      </Card>

      {/* Visual */}
      <Card icon={<Type size={16} />} title="Visual Settings" desc="Font size, motion, and contrast">
        <div className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Font Size</label>
            <div className="flex gap-2">
              {['small', 'medium', 'large', 'xlarge'].map(s => (
                <button key={s} onClick={() => setFontSize(s)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
                    fontSize === s ? 'bg-indigo-600 border-indigo-500 text-white' : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-white'
                  }`}>
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                </button>
              ))}
            </div>
          </div>
          <ToggleRow label="Reduced Motion" desc="Disables animations and transitions" checked={reducedMotion} onChange={setReducedMotion} />
          <ToggleRow label="High Contrast Mode" desc="Increases contrast for better visibility" checked={highContrast} onChange={setHighContrast} />
        </div>
      </Card>

      {/* Keyboard Navigation */}
      <Card icon={<Keyboard size={16} />} title="Keyboard Navigation" desc="Available shortcuts">
        <div className="space-y-2">
          {[
            ['Ctrl + K', 'Open global search from anywhere'],
            ['Tab / Shift+Tab', 'Navigate between interactive elements'],
            ['Enter / Space', 'Activate focused button or link'],
            ['Escape', 'Close open modals and dialogs'],
            ['Arrow Keys', 'Navigate options in select menus'],
          ].map(([key, desc]) => (
            <div key={key} className="flex items-center gap-3 py-1.5 border-b border-slate-800/50 last:border-0">
              <kbd className="px-2 py-1 bg-slate-800 border border-slate-700 rounded text-xs font-mono text-slate-300 flex-shrink-0">{key}</kbd>
              <span className="text-xs text-slate-400">{desc}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Save Button */}
      <div className="flex items-center gap-3">
        <button onClick={applyAndSave}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold px-6 py-2.5 rounded-xl transition shadow-lg shadow-indigo-900/30">
          {saved ? <CheckCircle size={15} /> : <AccessibilityIcon size={15} />}
          {saved ? 'Saved!' : 'Apply & Save'}
        </button>
        <p className="text-xs text-slate-500">Settings are stored in your browser's local storage.</p>
      </div>
    </div>
  )
}

function Card({ icon, title, desc, children }) {
  return (
    <div className="border border-slate-800/70 bg-slate-900/30 rounded-2xl p-6 space-y-4">
      <div className="flex items-center gap-2 pb-1 border-b border-slate-800">
        <span className="text-indigo-400">{icon}</span>
        <span className="font-bold text-white text-sm">{title}</span>
        {desc && <span className="text-slate-500 text-xs">· {desc}</span>}
      </div>
      {children}
    </div>
  )
}
function ToggleRow({ label, desc, checked, onChange }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <p className="text-sm font-semibold text-white">{label}</p>
        {desc && <p className="text-xs text-slate-500 mt-0.5">{desc}</p>}
      </div>
      <button onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 rounded-full border-2 transition-colors duration-200 flex-shrink-0 ${checked ? 'bg-indigo-600 border-indigo-500' : 'bg-slate-700 border-slate-600'}`}>
        <span className={`inline-block h-4 w-4 rounded-full bg-white shadow transform transition-transform duration-200 mt-0.5 ${checked ? 'translate-x-5' : 'translate-x-0.5'}`} />
      </button>
    </div>
  )
}
function SliderRow({ label, min, max, step, value, onChange }) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-semibold text-slate-400 uppercase tracking-wide">{label}</label>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        className="w-full accent-indigo-500" />
    </div>
  )
}
