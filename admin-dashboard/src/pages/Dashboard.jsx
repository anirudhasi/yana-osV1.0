// src/pages/Dashboard.jsx
import { Users, Truck, CreditCard, ShoppingBag, TrendingUp, AlertTriangle, Zap } from 'lucide-react'
import { StatCard, SectionCard, Badge, ProgressBar } from '../components/ui'
import { RevenueChart, FleetDonut, UtilizationTrendChart, DemandTimelineChart } from '../components/charts'
import {
  revenueData, paymentSummary, hubUtilization, fleetStatusBreakdown,
  utilizationTrend, riderStats, marketplaceSummary, maintenanceSummary,
  demandTimeline, supportSummary, skillsOverview,
} from '../api/mockData'

const fmt = (v) => `₹${v >= 100000 ? (v/100000).toFixed(1)+'L' : (v/1000).toFixed(0)+'K'}`

export default function Dashboard() {
  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="page-header">
        <div>
          <h1 className="font-display text-2xl font-bold text-surface-900 flex items-center gap-2">
            <Zap size={22} className="text-brand-500" />
            Yana OS Control Tower
          </h1>
          <p className="text-sm text-surface-500 mt-0.5">Real-time fleet + rider + demand overview</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-surface-400 bg-surface-100 px-3 py-1.5 rounded-full">
          <span className="w-1.5 h-1.5 bg-brand-500 rounded-full animate-pulse-soft" />
          Live · Updated just now
        </div>
      </div>

      {/* Key metrics row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Active Riders"     value={riderStats.active.toLocaleString()}    icon={Users}       accent="brand"  trend={8}  trendLabel="vs last week" subtitle={`${riderStats.total} total`} />
        <StatCard title="Fleet Utilization" value={`${hubUtilization.reduce((a,h)=>a+h.utilization,0)/hubUtilization.length|0}%`} icon={Truck} accent="blue"  trend={3} trendLabel="vs yesterday" subtitle="234 vehicles active" />
        <StatCard title="Rent Today"        value={fmt(paymentSummary.rent_collected_today)} icon={CreditCard} accent="brand" trend={12} trendLabel="vs yesterday" subtitle={`${fmt(paymentSummary.rent_collected_mtd)} MTD`} />
        <StatCard title="Demand Fill Rate"  value={`${marketplaceSummary.fill_rate_avg}%`} icon={ShoppingBag} accent="purple" trend={-2} trendLabel="vs last week" subtitle={`${marketplaceSummary.active_slots} active slots`} />
      </div>

      {/* Revenue chart + Fleet donut */}
      <div className="grid grid-cols-3 gap-4">
        <SectionCard title="Revenue — Last 30 Days" subtitle="Rent · Incentives · Penalties"
          className="col-span-2"
          action={<span className="text-xs font-mono font-semibold text-brand-600">{fmt(revenueData.reduce((a,d)=>a+d.rent+d.incentives,0))}</span>}>
          <RevenueChart data={revenueData} />
          <div className="flex items-center gap-6 mt-4">
            {[{color:'bg-brand-500',label:'Daily Rent'},{color:'bg-blue-500',label:'Incentives'},{color:'bg-red-400',label:'Penalties'}].map(l=>(
              <div key={l.label} className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${l.color}`} />
                <span className="text-xs text-surface-500">{l.label}</span>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Vehicle Status" subtitle="234 total vehicles">
          <FleetDonut data={fleetStatusBreakdown} />
          <div className="space-y-2 mt-2">
            {fleetStatusBreakdown.map(d => (
              <div key={d.name} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full" style={{ background: d.color }} />
                  <span className="text-xs text-surface-600">{d.name}</span>
                </div>
                <span className="text-xs font-mono font-semibold text-surface-700">{d.value}</span>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>

      {/* Hub utilization + Alerts + Demand */}
      <div className="grid grid-cols-3 gap-4">

        {/* Hub Utilization */}
        <SectionCard title="Hub Utilization" subtitle="Across all cities">
          <div className="space-y-4">
            {hubUtilization.map(hub => (
              <div key={hub.hub}>
                <div className="flex justify-between mb-1.5">
                  <div>
                    <p className="text-sm font-medium text-surface-800 leading-none">{hub.hub}</p>
                    <p className="text-xs text-surface-400 mt-0.5">{hub.city} · {hub.allocated}/{hub.capacity} vehicles</p>
                  </div>
                  <span className={`text-sm font-mono font-bold ${hub.utilization >= 85 ? 'text-brand-600' : hub.utilization >= 70 ? 'text-amber-600' : 'text-red-500'}`}>
                    {hub.utilization}%
                  </span>
                </div>
                <ProgressBar value={hub.utilization} max={100}
                  color={hub.utilization >= 85 ? 'brand' : hub.utilization >= 70 ? 'amber' : 'red'} showPct={false} />
              </div>
            ))}
          </div>
        </SectionCard>

        {/* Demand Timeline */}
        <SectionCard title="Demand vs Actual" subtitle="14-day rider attendance">
          <DemandTimelineChart data={demandTimeline} />
          <div className="grid grid-cols-3 gap-2 mt-4">
            {[
              { label: 'Required', value: demandTimeline.reduce((a,d)=>a+d.required,0), color: 'text-surface-500' },
              { label: 'Confirmed', value: demandTimeline.reduce((a,d)=>a+d.confirmed,0), color: 'text-brand-600' },
              { label: 'Shown Up', value: demandTimeline.reduce((a,d)=>a+d.shown_up,0), color: 'text-blue-600' },
            ].map(s => (
              <div key={s.label} className="text-center">
                <p className={`text-lg font-display font-bold ${s.color}`}>{s.value}</p>
                <p className="text-xs text-surface-400">{s.label}</p>
              </div>
            ))}
          </div>
        </SectionCard>

        {/* Quick status panel */}
        <div className="space-y-3">
          {/* Maintenance alerts */}
          <div className="card p-4">
            <div className="flex items-center justify-between mb-3">
              <p className="label">Maintenance Alerts</p>
              <span className="badge bg-red-100 text-red-700">{maintenanceSummary.active_alerts} open</span>
            </div>
            <div className="space-y-2">
              {[
                { label: 'Critical',     count: maintenanceSummary.critical_alerts, color: 'text-red-600' },
                { label: 'In Service',   count: maintenanceSummary.in_service,      color: 'text-amber-600' },
                { label: 'Due Soon',     count: maintenanceSummary.service_due_soon,color: 'text-surface-500' },
              ].map(a => (
                <div key={a.label} className="flex justify-between">
                  <span className="text-xs text-surface-500">{a.label}</span>
                  <span className={`text-xs font-bold font-mono ${a.color}`}>{a.count}</span>
                </div>
              ))}
            </div>
            <div className="border-t border-surface-100 mt-3 pt-3">
              <p className="text-xs text-surface-400">Cost this month</p>
              <p className="text-lg font-display font-bold text-surface-900">{fmt(maintenanceSummary.cost_this_month)}</p>
            </div>
          </div>

          {/* Support tickets */}
          <div className="card p-4">
            <div className="flex items-center justify-between mb-3">
              <p className="label">Support</p>
              {supportSummary.sla_breached > 0 && (
                <span className="badge bg-red-100 text-red-700">
                  <AlertTriangle size={10} />
                  {supportSummary.sla_breached} SLA breach
                </span>
              )}
            </div>
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'Open',       value: supportSummary.open_tickets,  color: 'text-blue-600' },
                { label: 'Escalated',  value: supportSummary.escalated,     color: 'text-red-600' },
                { label: 'Resolved/w', value: supportSummary.resolved_week, color: 'text-brand-600' },
                { label: 'Avg Rating', value: `${supportSummary.avg_satisfaction}★`, color: 'text-amber-600' },
              ].map(s => (
                <div key={s.label} className="bg-surface-50 rounded-lg p-2 text-center">
                  <p className={`text-base font-display font-bold ${s.color}`}>{s.value}</p>
                  <p className="text-xs text-surface-400">{s.label}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Skills leaderboard */}
          <div className="card p-4">
            <p className="label mb-3">Skills Leaderboard</p>
            <div className="space-y-2">
              {skillsOverview.leaderboard_top.slice(0,3).map(r => (
                <div key={r.rank} className="flex items-center gap-2">
                  <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold
                    ${r.rank===1?'bg-amber-400 text-white':r.rank===2?'bg-surface-300 text-surface-700':'bg-amber-100 text-amber-700'}`}>
                    {r.rank}
                  </span>
                  <span className="flex-1 text-xs text-surface-700">{r.name}</span>
                  <span className="text-xs font-mono font-bold text-brand-600">{r.points}pts</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Fleet utilization trend */}
      <SectionCard title="Utilization Trend" subtitle="14-day fleet utilization %, target 80%">
        <UtilizationTrendChart data={utilizationTrend} />
      </SectionCard>
    </div>
  )
}
