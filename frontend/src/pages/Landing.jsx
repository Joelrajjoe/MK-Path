import React from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@clerk/react'
import { 
  ArrowRight, 
  BookOpen, 
  Cpu, 
  GitMerge, 
  Target, 
  Volume2, 
  ShieldCheck 
} from 'lucide-react'

export default function Landing() {
  const { isSignedIn } = useAuth()

  return (
    <div className="flex flex-col space-y-20 py-8">
      {/* Hero Section */}
      <section className="text-center max-w-4xl mx-auto space-y-6 pt-8">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full border border-indigo-500/20 bg-indigo-500/10 text-indigo-400 text-xs font-semibold uppercase tracking-wider">
          <SparklesIcon className="h-4 w-4" />
          <span>Next-Gen EdTech Research MVP</span>
        </div>
        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-none">
          Adaptive Learning Guided by <br />
          <span className="bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-500 bg-clip-text text-transparent">
            Multimodal Knowledge Graphs
          </span>
        </h1>
        <p className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto font-light leading-relaxed">
          Ingest study materials, extract core concept dependencies with AI, and experience a personalized learning path powered by exam and industry-aligned mastery scoring.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
          {isSignedIn ? (
            <Link
              to="/dashboard"
              className="flex items-center space-x-2 px-6 py-3 font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-md shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/30 transition transform hover:-translate-y-0.5"
            >
              <span>Go to Dashboard</span>
              <ArrowRight size={18} />
            </Link>
          ) : (
            <>
              <Link
                to="/sign-up"
                className="flex items-center space-x-2 px-6 py-3 font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-md shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/30 transition transform hover:-translate-y-0.5"
              >
                <span>Get Started Free</span>
                <ArrowRight size={18} />
              </Link>
              <Link
                to="/sign-in"
                className="px-6 py-3 font-semibold text-slate-300 hover:text-white border border-slate-700 hover:border-slate-500 rounded-md transition"
              >
                Sign In
              </Link>
            </>
          )}
        </div>
      </section>

      {/* Concept Pillars Grid */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto w-full px-4">
        <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/40 backdrop-blur-sm space-y-4 hover:border-slate-700 transition">
          <div className="p-3 bg-indigo-600/10 text-indigo-400 rounded-lg w-fit">
            <Cpu className="h-6 w-6" />
          </div>
          <h3 className="text-xl font-bold text-white">AI Concept Extraction</h3>
          <p className="text-slate-400 text-sm leading-relaxed">
            Upload PDFs to automatically extract core concepts, descriptions, prerequisites, and relationships using validated AI pipeline schemas.
          </p>
        </div>

        <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/40 backdrop-blur-sm space-y-4 hover:border-slate-700 transition">
          <div className="p-3 bg-purple-600/10 text-purple-400 rounded-lg w-fit">
            <GitMerge className="h-6 w-6" />
          </div>
          <h3 className="text-xl font-bold text-white">Interactive Graph</h3>
          <p className="text-slate-400 text-sm leading-relaxed">
            Visualize learning pathways and concept relationships in an interactive node-link interface featuring industry and exam-relevance heatmaps.
          </p>
        </div>

        <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/40 backdrop-blur-sm space-y-4 hover:border-slate-700 transition">
          <div className="p-3 bg-pink-600/10 text-pink-400 rounded-lg w-fit">
            <Target className="h-6 w-6" />
          </div>
          <h3 className="text-xl font-bold text-white">Mastery Assessment</h3>
          <p className="text-slate-400 text-sm leading-relaxed">
            Take confidence-corrected, response-speed tracking quizzes to calculate concept mastery and auto-generate personalized study paths.
          </p>
        </div>
      </section>

      {/* Technical Specifications / Trust Details */}
      <section className="max-w-5xl mx-auto w-full bg-slate-900/20 border border-slate-800/80 rounded-2xl p-8 sm:p-12 flex flex-col md:flex-row items-center justify-between gap-8">
        <div className="space-y-4 max-w-md">
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Security & Identity by Clerk
          </h2>
          <p className="text-slate-400 text-sm leading-relaxed">
            Enjoy industry-leading authentication with secure session token validation on the FastAPI backend. Your credentials are safe, and data belongs securely to your authenticated identity.
          </p>
          <div className="flex items-center space-x-2 text-indigo-400 text-sm font-semibold">
            <ShieldCheck size={18} />
            <span>Atlas Database Protection</span>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4 w-full md:w-auto">
          <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-800 text-center">
            <div className="text-2xl font-bold text-white">Clerk</div>
            <div className="text-xs text-slate-500">Authentication</div>
          </div>
          <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-800 text-center">
            <div className="text-2xl font-bold text-white">MongoDB</div>
            <div className="text-xs text-slate-500">Atlas Storage</div>
          </div>
          <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-800 text-center">
            <div className="text-2xl font-bold text-white">FastAPI</div>
            <div className="text-xs text-slate-500">REST API</div>
          </div>
          <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-800 text-center">
            <div className="text-2xl font-bold text-white">React</div>
            <div className="text-xs text-slate-500">Vite SPA</div>
          </div>
        </div>
      </section>
    </div>
  )
}

function SparklesIcon(props) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
      <path d="m5 3 1 2.5L8.5 6 6 7 5 9.5 4 7 1.5 6 4 5.5z" />
      <path d="m19 17 1 2.5 2.5.5-2.5 1-1 2.5-1-2.5-2.5-1 2.5-1z" />
    </svg>
  )
}
