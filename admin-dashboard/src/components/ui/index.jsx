// src/components/ui/index.jsx
import { clsx } from 'clsx'
import { Loader2, AlertCircle, TrendingUp, TrendingDown, Minus } from 'lucide-react'

// ── Badge ─────────────────────────────────────────────────────
const badgeColors = {
  ACTIVE:       'bg-brand-100 text-brand-700',
  VERIFIED:     'bg-blue-100 text-blue-700',
  KYC_PENDING:  'bg-amber-100 text-amber-700',
  UNDER_REVIEW: 'bg-amber-100 text-amber-700',
  TRAINING:     'bg-purple-100 text-purple-700',
  SUSPENDED:    'bg-red-100 text-red-700',
  APPLIED:      'bg-surface-100 text-surface-600',
  KYC_FAILED:   'bg-red-100 text-red-700',
  OFFBOARDED:   'bg-surface-200 text-surface-500',
  OPEN:         'bg-blue-100 text-blue-700',
  IN_PROGRESS:  'bg-amber-100 text-amber-700',
  RESOLVED:     'bg-brand-100 text-brand-700',
  ESCALATED:    'bg-red-100 text-red-700',
  CLOSED:       'bg-surface-100 text-surface-500',
  HIGH:         'bg-red-100 text-red-700',
  MEDIUM:       'bg-amber-100 text-amber-700',
  LOW:          'bg-blue-100 text-blue-700',
  CRITICAL:     'bg-red-200 text-red-800',
  AVAILABLE:    'bg-brand-100 text-brand-700',
  ALLOCATED:    'bg-blue-100 text-blue-700',
  MAINTENANCE:  'bg-amber-100 text-amber-700',
}

export function Badge({ status, label, className }) {
  const color = badgeColors[status] || 'bg-surface-100 text-surface-600'
  return (
    <span className={clsx('badge', color, className)}>
      <span className={clsx('w-1.5 h-1.5 rounded-full',
        status === 'ACTIVE' || status === 'RESOLVED' || status === 'AVAILABLE' ? 'bg-brand-500' :
        status === 'SUSPENDED' || status === 'ESCALATED' || status === 'KYC_FAILED' ? 'bg-red-500' :
        'bg-current opacity-60'
      )} />
      {label || status}
    </span>
  )
}

// ── Stat Card ─────────────────────────────────────────────────
export function StatCard({ title, value, subtitle, trend, trendLabel, icon: Icon, accent = 'brand', className }) {
  const accentMap = {
    brand:  { bg: 'bg-brand-50',  icon: 'text-brand-600',  border: 'border-brand-100'  },
    amber:  { bg: 'bg-amber-50',  icon: 'text-amber-600',  border: 'border-amber-100'  },
    red:    { bg: 'bg-red-50',    icon: 'text-red-600',    border: 'border-red-100'    },
    blue:   { bg: 'bg-blue-50',   icon: 'text-blue-600',   border: 'border-blue-100'   },
    purple: { bg: 'bg-purple-50', icon: 'text-purple-600', border: 'border-purple-100' },
  }
  const a = accentMap[accent] || accentMap.brand
  const TrendIcon = trend > 0 ? TrendingUp : trend < 0 ? TrendingDown : Minus
  const trendColor = trend > 0 ? 'text-brand-600' : trend < 0 ? 'text-red-500' : 'text-surface-400'

  return (
    <div className={clsx('card card-hover p-5 animate-slide-up', className)}>
      <div className="flex items-start justify-between mb-3">
        <p className="label">{title}</p>
        {Icon && (
          <div className={clsx('p-2 rounded-xl border', a.bg, a.border)}>
            <Icon size={16} className={a.icon} />
          </div>
        )}
      </div>
      <div className="stat-number mb-1">{value}</div>
      <div className="flex items-center gap-2">
        {subtitle && <p className="text-xs text-surface-500">{subtitle}</p>}
        {trend !== undefined && (
          <span className={clsx('flex items-center gap-0.5 text-xs font-medium', trendColor)}>
            <TrendIcon size={12} />
            {Math.abs(trend)}% {trendLabel || ''}
          </span>
        )}
      </div>
    </div>
  )
}

// ── Section Card ──────────────────────────────────────────────
export function SectionCard({ title, subtitle, action, children, className }) {
  return (
    <div className={clsx('card animate-fade-in', className)}>
      <div className="flex items-center justify-between px-6 py-4 border-b border-surface-100">
        <div>
          <h3 className="section-title">{title}</h3>
          {subtitle && <p className="text-xs text-surface-500 mt-0.5">{subtitle}</p>}
        </div>
        {action}
      </div>
      <div className="p-6">{children}</div>
    </div>
  )
}

// ── Spinner ───────────────────────────────────────────────────
export function Spinner({ size = 20 }) {
  return <Loader2 size={size} className="animate-spin text-brand-500" />
}

// ── Empty State ───────────────────────────────────────────────
export function EmptyState({ title = 'No data', message }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="w-12 h-12 rounded-2xl bg-surface-100 flex items-center justify-center mb-3">
        <AlertCircle size={20} className="text-surface-400" />
      </div>
      <p className="font-medium text-surface-700">{title}</p>
      {message && <p className="text-sm text-surface-400 mt-1 max-w-xs">{message}</p>}
    </div>
  )
}

// ── Progress Bar ──────────────────────────────────────────────
export function ProgressBar({ value, max = 100, color = 'brand', label, showPct = true }) {
  const pct = Math.round((value / max) * 100)
  const colorMap = { brand: 'bg-brand-500', amber: 'bg-amber-500', red: 'bg-red-500', blue: 'bg-blue-500' }
  return (
    <div className="space-y-1">
      {(label || showPct) && (
        <div className="flex justify-between text-xs">
          {label && <span className="text-surface-600">{label}</span>}
          {showPct && <span className="text-surface-500 font-mono">{pct}%</span>}
        </div>
      )}
      <div className="h-1.5 bg-surface-100 rounded-full overflow-hidden">
        <div
          className={clsx('h-full rounded-full transition-all duration-700', colorMap[color] || colorMap.brand)}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
    </div>
  )
}

// ── Avatar / Initials ─────────────────────────────────────────
export function Avatar({ name, size = 'sm' }) {
  const initials = name?.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase() || '?'
  const colors   = ['bg-brand-100 text-brand-700','bg-blue-100 text-blue-700','bg-purple-100 text-purple-700',
                     'bg-amber-100 text-amber-700','bg-pink-100 text-pink-700']
  const color    = colors[(name?.charCodeAt(0) || 0) % colors.length]
  const sizeMap  = { sm: 'w-8 h-8 text-xs', md: 'w-10 h-10 text-sm', lg: 'w-12 h-12 text-base' }
  return (
    <div className={clsx('rounded-full flex items-center justify-center font-display font-bold shrink-0', color, sizeMap[size])}>
      {initials}
    </div>
  )
}
