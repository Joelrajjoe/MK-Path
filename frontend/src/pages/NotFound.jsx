import React from 'react'
import { Link } from 'react-router-dom'
import { Home, AlertTriangle } from 'lucide-react'

export default function NotFound() {
  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="text-center space-y-6 max-w-md px-6">
        <div className="inline-flex p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl">
          <AlertTriangle className="h-12 w-12 text-amber-400" />
        </div>
        <div className="space-y-2">
          <h1 className="text-6xl font-extrabold text-white">404</h1>
          <h2 className="text-xl font-bold text-slate-200">Page Not Found</h2>
          <p className="text-slate-400 text-sm leading-relaxed">
            The page you're looking for doesn't exist or has been moved.
          </p>
        </div>
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold px-6 py-3 rounded-xl transition shadow-lg shadow-indigo-900/30"
        >
          <Home size={16} /> Back to Dashboard
        </Link>
      </div>
    </div>
  )
}
