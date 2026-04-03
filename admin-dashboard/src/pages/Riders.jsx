// src/pages/Riders.jsx
import { Users, UserCheck, UserX, Clock, TrendingDown, Download } from 'lucide-react'
import { StatCard, SectionCard } from '../components/ui'
import { RiderGrowthChart, RiderStatusPie } from '../components/charts'
import RidersTable from '../components/tables/RidersTable'
import { riders, riderStats, riderGrowth, riderStatusDist } from '../api/mockData'

export default function Riders() {
  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <h1 className="font-display text-2xl font-bold text-surface-900">Riders</h1>
          <p className="text-sm text-surface-500 mt-0.5">Manage onboarding, KYC, and activation</p>
        </div>
        <button className="btn-ghost text-sm">
          <Download size={14} /> Export CSV
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard title="Total Riders"   value={riderStats.total}         icon={Users}     accent="brand"  />
        <StatCard title="Active"         value={riderStats.active}        icon={UserCheck} accent="brand"  trend={8} />
        <StatCard title="KYC Pending"    value={riderStats.kyc_pending}   icon={Clock}     accent="amber"  />
        <StatCard title="Suspended"      value={riderStats.suspended}     icon={UserX}     accent="red"    />
        <StatCard title="Churn Rate"     value={`${riderStats.churn_rate}%`} icon={TrendingDown} accent="red" subtitle="Last 30 days" />
      </div>

      {/* Growth + Status dist */}
      <div className="grid grid-cols-3 gap-4">
        <SectionCard title="Rider Growth" subtitle="Monthly new vs churned" className="col-span-2">
          <RiderGrowthChart data={riderGrowth} />
        </SectionCard>
        <SectionCard title="Status Distribution" subtitle="Current snapshot">
          <RiderStatusPie data={riderStatusDist} />
          <div className="space-y-1.5 mt-2">
            {riderStatusDist.map(d => (
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

      {/* Full rider table */}
      <SectionCard title="All Riders" subtitle={`${riders.length} riders shown (mock data — connect to /api/v1/riders/)`}>
        <RidersTable data={riders} />
      </SectionCard>
    </div>
  )
}
