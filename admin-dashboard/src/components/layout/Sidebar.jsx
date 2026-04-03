// src/components/layout/Sidebar.jsx
import { NavLink, useLocation } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  LayoutDashboard, Users, Truck, CreditCard, ShoppingBag,
  Wrench, GraduationCap, HeadphonesIcon, LogOut, Zap, ChevronRight,
} from 'lucide-react'

const nav = [
  { to: '/',            icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/riders',      icon: Users,           label: 'Riders' },
  { to: '/fleet',       icon: Truck,           label: 'Fleet & Vehicles' },
  { to: '/payments',    icon: CreditCard,      label: 'Payments' },
  { to: '/marketplace', icon: ShoppingBag,     label: 'Marketplace' },
  { to: '/maintenance', icon: Wrench,          label: 'Maintenance' },
  { to: '/skills',      icon: GraduationCap,   label: 'Skills' },
  { to: '/support',     icon: HeadphonesIcon,  label: 'Support' },
]

export default function Sidebar() {
  const location = useLocation()

  return (
    <aside className="fixed left-0 top-0 h-screen w-60 flex flex-col bg-surface-950 z-30">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-white/5">
        <div className="w-8 h-8 rounded-xl bg-brand-500 flex items-center justify-center shadow-glow">
          <Zap size={16} className="text-white" />
        </div>
        <div>
          <span className="font-display font-bold text-white text-base leading-none">Yana OS</span>
          <span className="block text-xs text-white/30 mt-0.5">Admin Portal</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-0.5">
        {nav.map(({ to, icon: Icon, label }) => {
          const active = to === '/' ? location.pathname === '/' : location.pathname.startsWith(to)
          return (
            <NavLink key={to} to={to}
              className={clsx('nav-item group',
                active ? 'bg-brand-600/20 text-brand-400' : 'text-white/40 hover:text-white/80 hover:bg-white/5'
              )}>
              <Icon size={16} className={active ? 'text-brand-400' : ''} />
              <span className="flex-1 text-sm">{label}</span>
              {active && <ChevronRight size={12} className="text-brand-400/60" />}
            </NavLink>
          )
        })}
      </nav>

      {/* User */}
      <div className="p-3 border-t border-white/5">
        <div className="flex items-center gap-3 px-2 py-2 rounded-xl hover:bg-white/5 cursor-pointer group transition-colors">
          <div className="w-7 h-7 rounded-lg bg-brand-500/20 border border-brand-500/30 flex items-center justify-center">
            <span className="text-xs font-bold text-brand-400">A</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-white/80 truncate">admin@yana.in</p>
            <p className="text-xs text-white/30">Super Admin</p>
          </div>
          <LogOut size={14} className="text-white/20 group-hover:text-white/50 transition-colors"
            onClick={() => { localStorage.removeItem('yana_admin_token'); window.location.href = '/login' }} />
        </div>
      </div>
    </aside>
  )
}
