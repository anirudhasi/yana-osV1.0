// src/pages/Fleet.jsx
import { Truck, Zap, AlertTriangle, Clock, Activity } from 'lucide-react'
import { StatCard, SectionCard, ProgressBar, Badge } from '../components/ui'
import { UtilizationBarChart, FleetDonut, UtilizationTrendChart } from '../components/charts'
import { hubUtilization, fleetStatusBreakdown, utilizationTrend, maintenanceSummary, alertsByType } from '../api/mockData'

export default function Fleet() {
  const totalVehicles = fleetStatusBreakdown.reduce((a, d) => a + d.value, 0)
  const allocated     = fleetStatusBreakdown.find(d => d.name === 'Allocated')?.value || 0
  const available     = fleetStatusBreakdown.find(d => d.name === 'Available')?.value || 0
  const inMaint       = fleetStatusBreakdown.find(d => d.name === 'Maintenance')?.value || 0
  const utilPct       = Math.round(allocated * 100 / totalVehicles)

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <h1 className="font-display text-2xl font-bold text-surface-900">Fleet & Vehicles</h1>
          <p className="text-sm text-surface-500 mt-0.5">{totalVehicles} vehicles across 5 hubs</p>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Total Fleet"       value={totalVehicles}   icon={Truck}         accent="brand"  />
        <StatCard title="Allocated"         value={allocated}       icon={Activity}      accent="blue"   subtitle={`${utilPct}% utilization`} />
        <StatCard title="In Maintenance"    value={inMaint}         icon={AlertTriangle} accent="amber"  />
        <StatCard title="Available Now"     value={available}       icon={Zap}           accent="brand"  />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <SectionCard title="Hub Utilization" subtitle="Allocated vehicles per hub" className="col-span-2">
          <UtilizationBarChart data={hubUtilization} />
          <div className="grid grid-cols-5 gap-3 mt-4">
            {hubUtilization.map(h => (
              <div key={h.hub} className="text-center">
                <div className={`text-lg font-display font-bold ${h.utilization >= 85 ? 'text-brand-600' : h.utilization >= 70 ? 'text-amber-600' : 'text-red-500'}`}>
                  {h.utilization}%
                </div>
                <p className="text-xs text-surface-400 truncate">{h.hub.split(' ')[0]}</p>
                <p className="text-xs text-surface-300">{h.allocated}/{h.capacity}</p>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Fleet Breakdown">
          <FleetDonut data={fleetStatusBreakdown} />
          <div className="space-y-3 mt-3">
            {fleetStatusBreakdown.map(d => (
              <div key={d.name}>
                <ProgressBar value={d.value} max={totalVehicles}
                  label={`${d.name} (${d.value})`}
                  color={d.name === 'Allocated' ? 'brand' : d.name === 'Available' ? 'blue' : d.name === 'Maintenance' ? 'amber' : undefined}
                  showPct />
              </div>
            ))}
          </div>
        </SectionCard>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <SectionCard title="14-Day Utilization Trend">
          <UtilizationTrendChart data={utilizationTrend} />
        </SectionCard>

        <SectionCard title="Active Alerts" subtitle={`${maintenanceSummary.active_alerts} unacknowledged`}>
          <div className="space-y-3">
            {alertsByType.map(a => (
              <div key={a.type} className="flex items-center justify-between p-3 bg-surface-50 rounded-xl">
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${a.severity === 'CRITICAL' ? 'bg-red-600' : a.severity === 'HIGH' ? 'bg-red-400' : 'bg-amber-400'}`} />
                  <span className="text-sm text-surface-700">{a.type}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge status={a.severity} label={a.severity} />
                  <span className="text-sm font-mono font-bold text-surface-600">{a.count}</span>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
