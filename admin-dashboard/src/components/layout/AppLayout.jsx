// src/components/layout/AppLayout.jsx
import { Outlet } from 'react-router-dom'
import { Bell, Search } from 'lucide-react'
import Sidebar from './Sidebar'

export default function AppLayout() {
  return (
    <div className="flex h-screen overflow-hidden bg-surface-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden ml-60">
        {/* Top Bar */}
        <header className="h-14 bg-white border-b border-surface-200 flex items-center gap-4 px-6 shrink-0">
          <div className="flex-1 flex items-center gap-2 max-w-sm">
            <div className="relative flex-1">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400" />
              <input className="input pl-9 h-8 text-sm" placeholder="Search riders, vehicles…" />
            </div>
          </div>
          <div className="flex items-center gap-3 ml-auto">
            {/* Live indicator */}
            <div className="flex items-center gap-1.5 text-xs text-surface-500">
              <span className="w-1.5 h-1.5 rounded-full bg-brand-500 animate-pulse-soft" />
              Live
            </div>
            <button className="relative p-2 rounded-xl hover:bg-surface-100 text-surface-500 transition-colors">
              <Bell size={16} />
              <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-red-500 rounded-full" />
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto px-6 py-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
