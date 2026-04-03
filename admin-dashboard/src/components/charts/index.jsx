// src/components/charts/index.jsx
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  PieChart, Pie, Cell, RadialBarChart, RadialBar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'

const GRID_COLOR   = '#f0f4f0'
const AXIS_COLOR   = '#9ca3b0'
const TOOLTIP_STYLE = {
  background: '#111811',
  border:     'none',
  borderRadius: 12,
  color: '#fff',
  fontSize: 12,
  padding: '8px 12px',
  boxShadow: '0 8px 24px rgba(0,0,0,.18)',
}

const fmt = (v) => v >= 1_000_000 ? `₹${(v/1_000_000).toFixed(1)}M` :
                   v >= 1_000     ? `₹${(v/1_000).toFixed(0)}K`     : `₹${v}`

// ── Revenue Area Chart ────────────────────────────────────────
export function RevenueChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="gRent" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#22c55e" stopOpacity={0.18} />
            <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="gInc" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.15} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={GRID_COLOR} strokeDasharray="0" vertical={false} />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: AXIS_COLOR }} axisLine={false} tickLine={false} interval={4} />
        <YAxis tickFormatter={(v) => `₹${(v/1000).toFixed(0)}K`} tick={{ fontSize: 11, fill: AXIS_COLOR }} axisLine={false} tickLine={false} width={52} />
        <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v, n) => [fmt(v), n === 'rent' ? 'Daily Rent' : n === 'incentives' ? 'Incentives' : 'Penalties']} />
        <Area type="monotone" dataKey="rent"       stroke="#22c55e" strokeWidth={2} fill="url(#gRent)" dot={false} />
        <Area type="monotone" dataKey="incentives" stroke="#3b82f6" strokeWidth={1.5} fill="url(#gInc)" dot={false} />
        <Area type="monotone" dataKey="penalties"  stroke="#ef4444" strokeWidth={1} fill="none" dot={false} strokeDasharray="4 3" />
      </AreaChart>
    </ResponsiveContainer>
  )
}

// ── Fleet Utilization Bar ─────────────────────────────────────
export function UtilizationBarChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} barSize={24} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={GRID_COLOR} vertical={false} />
        <XAxis dataKey="hub" tick={{ fontSize: 11, fill: AXIS_COLOR }} axisLine={false} tickLine={false}
               tickFormatter={(v) => v.split(' ')[0]} />
        <YAxis tick={{ fontSize: 11, fill: AXIS_COLOR }} axisLine={false} tickLine={false}
               tickFormatter={(v) => `${v}%`} domain={[0, 100]} />
        <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => [`${v}%`, 'Utilization']} />
        <ReferenceLine y={80} stroke="#f59e0b" strokeDasharray="4 2" strokeWidth={1.5} label={{ value: 'Target 80%', position: 'right', fontSize: 10, fill: '#f59e0b' }} />
        <Bar dataKey="utilization" radius={[6, 6, 0, 0]}
             fill="#22c55e"
             label={{ position: 'top', fontSize: 10, fill: AXIS_COLOR, formatter: (v) => `${v}%` }} />
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Vehicle Status Donut ──────────────────────────────────────
export function FleetDonut({ data }) {
  return (
    <ResponsiveContainer width="100%" height={180}>
      <PieChart>
        <Pie data={data} cx="50%" cy="50%" innerRadius={52} outerRadius={76}
             paddingAngle={3} dataKey="value" strokeWidth={0}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v, n) => [v, n]} />
      </PieChart>
    </ResponsiveContainer>
  )
}

// ── Rider Growth Bar ──────────────────────────────────────────
export function RiderGrowthChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} barGap={2} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={GRID_COLOR} vertical={false} />
        <XAxis dataKey="month" tick={{ fontSize: 11, fill: AXIS_COLOR }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: AXIS_COLOR }} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Bar dataKey="riders"  fill="#22c55e" radius={[4,4,0,0]} barSize={20} name="New Riders" />
        <Bar dataKey="churned" fill="#ef4444" radius={[4,4,0,0]} barSize={20} name="Churned" />
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Demand Timeline ───────────────────────────────────────────
export function DemandTimelineChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={GRID_COLOR} vertical={false} />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: AXIS_COLOR }} axisLine={false} tickLine={false} interval={2} />
        <YAxis tick={{ fontSize: 11, fill: AXIS_COLOR }} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Line type="monotone" dataKey="required"  stroke="#94a3b8" strokeWidth={1.5} dot={false} name="Required" />
        <Line type="monotone" dataKey="confirmed" stroke="#22c55e" strokeWidth={2}   dot={false} name="Confirmed" />
        <Line type="monotone" dataKey="shown_up"  stroke="#3b82f6" strokeWidth={1.5} dot={false} name="Shown Up" strokeDasharray="4 2" />
      </LineChart>
    </ResponsiveContainer>
  )
}

// ── Maintenance Cost Stacked Bar ──────────────────────────────
export function MaintenanceCostChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} barSize={32} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={GRID_COLOR} vertical={false} />
        <XAxis dataKey="month" tick={{ fontSize: 11, fill: AXIS_COLOR }} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={(v) => `₹${(v/1000).toFixed(0)}K`} tick={{ fontSize: 11, fill: AXIS_COLOR }} axisLine={false} tickLine={false} width={52} />
        <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => [fmt(v)]} />
        <Bar dataKey="labour" stackId="a" fill="#f59e0b" radius={[0,0,0,0]} name="Labour" />
        <Bar dataKey="parts"  stackId="a" fill="#ef4444" radius={[4,4,0,0]} name="Parts" />
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Rider Status Pie ──────────────────────────────────────────
export function RiderStatusPie({ data }) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie data={data} cx="50%" cy="50%" outerRadius={80}
             paddingAngle={2} dataKey="value" strokeWidth={0}
             label={({ name, percent }) => `${name} ${(percent*100).toFixed(0)}%`}
             labelLine={false}>
          {data.map((entry, i) => <Cell key={i} fill={entry.color} />)}
        </Pie>
        <Tooltip contentStyle={TOOLTIP_STYLE} />
      </PieChart>
    </ResponsiveContainer>
  )
}

// ── Utilization Trend Line ────────────────────────────────────
export function UtilizationTrendChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={100}>
      <AreaChart data={data} margin={{ top: 4, right: 4, left: -32, bottom: 0 }}>
        <defs>
          <linearGradient id="gUtil" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#22c55e" stopOpacity={0.2} />
            <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={GRID_COLOR} vertical={false} />
        <XAxis dataKey="date" tick={{ fontSize: 10, fill: AXIS_COLOR }} axisLine={false} tickLine={false} interval={3} />
        <YAxis tick={{ fontSize: 10, fill: AXIS_COLOR }} axisLine={false} tickLine={false} domain={[60,100]} tickFormatter={(v)=>`${v}%`} />
        <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => [`${v}%`, 'Utilization']} />
        <ReferenceLine y={80} stroke="#f59e0b" strokeDasharray="3 2" strokeWidth={1} />
        <Area type="monotone" dataKey="utilization" stroke="#22c55e" strokeWidth={2} fill="url(#gUtil)" dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  )
}
