import React, { useState, useEffect, useRef } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { UserButton, useUser } from '@clerk/react'
import { 
  BookOpen, 
  LayoutDashboard, 
  FileText, 
  GitBranch, 
  GraduationCap, 
  Compass, 
  Sparkles,
  Award, 
  Settings as SettingsIcon, 
  Accessibility as AccessibilityIcon,
  Search,
  Bell,
  Menu,
  X,
  Trophy,
  ClipboardList,
  User,
  Layers
} from 'lucide-react'

export default function Layout() {
  const { user } = useUser()
  const location = useLocation()
  const navigate = useNavigate()
  const searchRef = useRef(null)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  // Ctrl+K opens search
  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        if (location.pathname !== '/search') {
          navigate('/search')
        } else {
          searchRef.current?.focus()
        }
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [navigate, location.pathname])

  const handleSearch = (e) => {
    if (e.key === 'Enter' && searchQuery.trim().length >= 2) {
      navigate(`/search?q=${encodeURIComponent(searchQuery.trim())}`)
    }
  }

  // Mapping paths to user-facing page titles
  const getPageTitle = (path) => {
    switch (path) {
      case '/dashboard': return 'Dashboard'
      case '/materials': return 'Study Materials'
      case '/knowledge-graph': return 'Interactive Knowledge Graph'
      case '/flashcards': return 'Spaced-Repetition Flashcards'
      case '/assessment': return 'Adaptive Assessment'
      case '/study-path': return 'Personalized Study Path'
      case '/resources': return 'Recommended Resources'
      case '/progress': return 'Learning Progress'
      case '/achievements': return 'Achievements & Badges'
      case '/assignments': return 'Assignments'
      case '/profile': return 'Learner Profile'
      case '/settings': return 'Settings'
      case '/accessibility': return 'Accessibility & Voice Tools'
      case '/search': return 'Search'
      default: return 'MK-Path Framework'
    }
  }

  const primaryNavItems = [
    { to: '/dashboard', label: 'Dashboard', icon: <LayoutDashboard size={18} /> },
    { to: '/materials', label: 'Materials', icon: <FileText size={18} /> },
    { to: '/knowledge-graph', label: 'Knowledge Graph', icon: <GitBranch size={18} /> },
    { to: '/flashcards', label: 'Flashcards', icon: <Layers size={18} /> },
    { to: '/assessment', label: 'Assessment', icon: <GraduationCap size={18} /> },
    { to: '/study-path', label: 'Study Path', icon: <Compass size={18} /> },
    { to: '/assignments', label: 'Assignments', icon: <ClipboardList size={18} /> },
    { to: '/resources', label: 'Resources', icon: <Sparkles size={18} /> },
    { to: '/progress', label: 'Progress', icon: <Award size={18} /> }
  ]

  const secondaryNavItems = [
    { to: '/achievements', label: 'Achievements', icon: <Trophy size={18} /> },
    { to: '/profile', label: 'Profile', icon: <User size={18} /> },
    { to: '/settings', label: 'Settings', icon: <SettingsIcon size={18} /> },
    { to: '/accessibility', label: 'Accessibility', icon: <AccessibilityIcon size={18} /> }
  ]

  const SidebarContent = () => (
    <div className="flex flex-col h-full bg-slate-900 border-r border-slate-800 text-slate-300">
      {/* Brand Logo */}
      <div className="p-6 border-b border-slate-800 flex items-center space-x-3 bg-slate-950/20">
        <div className="p-1.5 rounded-lg bg-indigo-600/10 text-indigo-400 border border-indigo-500/10">
          <BookOpen className="h-6 w-6" />
        </div>
        <span className="font-extrabold text-xl text-white tracking-wider bg-gradient-to-r from-indigo-200 to-slate-200 bg-clip-text text-transparent">
          MK-Path
        </span>
      </div>

      {/* Middle Scrollable Section: Navigation Items */}
      <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto scrollbar-none">
        <p className="px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Navigation</p>
        {primaryNavItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={() => setMobileMenuOpen(false)}
            className={({ isActive }) =>
              `flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-semibold transition ${
                isActive
                  ? 'bg-gradient-to-r from-indigo-900/30 to-purple-900/20 text-indigo-400 border-l-4 border-indigo-500/80 glow-indigo'
                  : 'hover:bg-slate-800/60 hover:text-slate-100'
              }`
            }
          >
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}

        <div className="pt-6 border-t border-slate-800 my-4"></div>
        <p className="px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">System</p>
        {secondaryNavItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={() => setMobileMenuOpen(false)}
            className={({ isActive }) =>
              `flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-semibold transition ${
                isActive
                  ? 'bg-gradient-to-r from-indigo-900/30 to-purple-900/20 text-indigo-400 border-l-4 border-indigo-500/80 glow-indigo'
                  : 'hover:bg-slate-800/60 hover:text-slate-100'
              }`
            }
          >
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* User Profile Footer */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/20 flex items-center justify-between">
        <div className="flex items-center space-x-3 truncate">
          <UserButton afterSignOutUrl="/" />
          <div className="flex flex-col truncate">
            <span className="text-sm font-bold text-white truncate">
              {user?.fullName || user?.username || 'Learner'}
            </span>
            <span className="text-xs text-slate-500 truncate">
              {user?.primaryEmailAddress?.emailAddress || 'active session'}
            </span>
          </div>
        </div>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex font-sans antialiased overflow-hidden">
      {/* 1. Desktop Persistent Sidebar */}
      <aside className="hidden md:block w-72 h-screen flex-shrink-0">
        <SidebarContent />
      </aside>

      {/* 2. Mobile Drawer Overlays */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          {/* Backdrop */}
          <div 
            className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm"
            onClick={() => setMobileMenuOpen(false)}
          ></div>
          {/* Menu Drawer */}
          <div className="relative flex flex-col w-72 max-w-xs h-full bg-slate-900 border-r border-slate-800 shadow-2xl animate-in slide-in-from-left duration-250">
            <button 
              className="absolute top-4 right-4 p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800/80 transition"
              onClick={() => setMobileMenuOpen(false)}
            >
              <X size={20} />
            </button>
            <SidebarContent />
          </div>
        </div>
      )}

      {/* 3. Main Dashboard Workspace */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Top Header Bar */}
        <header className="h-16 border-b border-slate-800/60 bg-slate-900/30 backdrop-blur-md flex items-center justify-between px-6 z-10">
          <div className="flex items-center space-x-4">
            {/* Hamburger Toggle button */}
            <button 
              onClick={() => setMobileMenuOpen(true)}
              className="md:hidden p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition"
            >
              <Menu size={20} />
            </button>
            {/* Dynamic Page Title */}
            <h2 className="text-xl font-extrabold text-white tracking-wide">
              {getPageTitle(location.pathname)}
            </h2>
          </div>

          {/* Search, Notifications & Theme placeholder */}
          <div className="flex items-center space-x-4">
            {/* Glassmorphic Search Bar */}
            <div className="hidden sm:flex items-center relative">
              <Search size={16} className="absolute left-3 text-slate-500" />
              <input 
                ref={searchRef}
                type="text" 
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                onKeyDown={handleSearch}
                onClick={() => { if (location.pathname !== '/search') navigate('/search') }}
                placeholder="Search… (Ctrl+K)" 
                className="w-56 pl-10 pr-4 py-1.5 text-xs bg-slate-950/50 hover:bg-slate-950/80 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-lg text-slate-300 outline-none transition cursor-pointer"
                readOnly={location.pathname !== '/search'}
              />
            </div>
            
            {/* Notifications Alert */}
            <button className="p-2 text-slate-400 hover:text-white bg-slate-800/40 hover:bg-slate-800 border border-slate-800 rounded-lg relative transition">
              <Bell size={18} />
              {/* Glow Badge */}
              <span className="absolute top-1.5 right-1.5 h-2.5 w-2.5 bg-indigo-500 rounded-full border border-slate-900 animate-pulse"></span>
            </button>
          </div>
        </header>

        {/* Dynamic Scrollable Page Content Frame */}
        <main className="flex-grow overflow-y-auto p-6 md:p-8 scroll-smooth bg-radial-at-t from-slate-900/40 via-slate-950 to-slate-950">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
