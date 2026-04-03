// src/pages/Maintenance.jsx
import { Wrench, AlertTriangle, Clock, IndianRupee, Activity } from 'lucide-react'
import { StatCard, SectionCard, Badge, ProgressBar } from '../components/ui'
import { MaintenanceCostChart } from '../components/charts'
import { maintenanceSummary, maintenanceCostTrend, alertsByType, hubUtilization } from '../api/mockData'

const fmtK = (v) => `₹${(v/1000).toFixed(0)}K`

export default function Maintenance() {
  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <h1 className="font-display text-2xl font-bold text-surface-900">Maintenance</h1>
          <p className="text-sm text-surface-500 mt-0.5">Repair logs · Cost tracking · Service alerts</p>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard title="Active Alerts"   value={maintenanceSummary.active_alerts}    icon={AlertTriangle} accent="red"   />
        <StatCard title="Critical"        value={maintenanceSummary.critical_alerts}  icon={AlertTriangle} accent="red"   />
        <StatCard title="In Service"      value={maintenanceSummary.in_service}       icon={Wrench}        accent="amber" />
        <StatCard title="Cost This Month" value={fmtK(maintenanceSummary.cost_this_month)} icon={IndianRupee} accent="brand" />
        <StatCard title="Avg Downtime"    value={`${maintenanceSummary.avg_downtime_hrs}h`} icon={Clock}     accent="blue" subtitle="per service" />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <SectionCard title="Monthly Cost Breakdown" subtitle="Labour vs Parts">
          <MaintenanceCostChart data={maintenanceCostTrend} />
          <div className="flex gap-6 mt-3">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-amber-500" />
              <span className="text-xs text-surface-500">Labour</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-red-500" />
              <span className="text-xs text-surface-500">Parts</span>
            </div>
          </div>
        </SectionCard>

        <SectionCard title="Alert Breakdown by Type">
          <div className="space-y-4">
            {alertsByType.map(a => (
              <div key={a.type} className="p-3 bg-surface-50 rounded-xl">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-surface-700">{a.type}</span>
                  <Badge status={a.severity} label={a.severity} />
                </div>
                <ProgressBar value={a.count} max={alertsByType.reduce((s,x)=>s+x.count,0)}
                  color={a.severity==='CRITICAL'?'red':a.severity==='HIGH'?'red':'amber'}
                  label={`${a.count} vehicles affected`} />
              </div>
            ))}
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Vehicle Cost Per Hub" subtitle="Total maintenance spend by location">
        <div className="space-y-4">
          {hubUtilization.map((hub, i) => {
            const cost = [84200,62300,118400,73100,51800][i]
            return (
              <div key={hub.hub} className="flex items-center gap-4">
                <div className="w-32 shrink-0">
                  <p className="text-sm font-medium text-surface-700 truncate">{hub.hub}</p>
                  <p className="text-xs text-surface-400">{hub.city}</p>
                </div>
                <div className="flex-1">
                  <ProgressBar value={cost} max={120000} showPct={false} color="amber" />
                </div>
                <span className="text-sm font-mono font-bold text-surface-700 w-16 text-right">{fmtK(cost)}</span>
              </div>
            )
          })}
        </div>
      </SectionCard>
    </div>
  )
}
