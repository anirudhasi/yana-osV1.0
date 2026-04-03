// src/pages/Marketplace.jsx
import { ShoppingBag, Users, CheckCircle2, TrendingUp, IndianRupee, Clock } from 'lucide-react'
import { StatCard, SectionCard, ProgressBar, Badge } from '../components/ui'
import { DemandTimelineChart } from '../components/charts'
import {
  demandFillRates, demandTimeline, marketplaceSummary, demandTimeline as dt,
} from '../api/mockData'

const fmtL = (v) => v >= 100000 ? `₹${(v/100000).toFixed(2)}L` : `₹${(v/1000).toFixed(0)}K`

function FillRateHeatCell({ value }) {
  const pct = Math.round(value)
  const bg =
    pct >= 90 ? 'bg-brand-500 text-white' :
    pct >= 80 ? 'bg-brand-200 text-brand-800' :
    pct >= 70 ? 'bg-amber-100 text-amber-800' :
    pct >= 60 ? 'bg-orange-100 text-orange-800' :
                'bg-red-100 text-red-700'
  return (
    <span className={`inline-flex items-center justify-center w-16 h-7 rounded-lg text-xs font-mono font-bold ${bg}`}>
      {pct}%
    </span>
  )
}

export default function Marketplace() {
  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <h1 className="font-display text-2xl font-bold text-surface-900">Job Marketplace</h1>
          <p className="text-sm text-surface-500 mt-0.5">Demand slots · Rider matching · Fill rates</p>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Active Slots"      value={marketplaceSummary.active_slots}            icon={ShoppingBag}  accent="brand"  />
        <StatCard title="Confirmed Today"   value={marketplaceSummary.confirmed_today}         icon={CheckCircle2} accent="blue"   />
        <StatCard title="Avg Fill Rate"     value={`${marketplaceSummary.fill_rate_avg}%`}     icon={TrendingUp}   accent="purple" />
        <StatCard title="Earnings This Week" value={fmtL(marketplaceSummary.earnings_paid_week)} icon={IndianRupee} accent="brand" />
      </div>

      {/* Fill Rate Heatmap Table */}
      <SectionCard title="Client Fill Rate Heatmap" subtitle="Last 7 days · by client">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-surface-100">
                {['Client','Total Slots','Filled','Partial','Unfilled','Fill Rate','Show-up Rate'].map(h => (
                  <th key={h} className="px-4 py-3 text-xs font-medium text-surface-500 uppercase tracking-wider whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {demandFillRates.map((row, i) => (
                <tr key={row.client}
                  className={`border-b border-surface-50 hover:bg-surface-50 transition-colors ${i % 2 === 0 ? 'bg-white' : 'bg-surface-50/30'}`}>
                  <td className="px-4 py-3">
                    <span className="font-semibold text-sm text-surface-800">{row.client}</span>
                  </td>
                  <td className="px-4 py-3 text-sm font-mono text-surface-600">{row.slots}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-1 text-sm font-mono text-brand-700">
                      <span className="w-2 h-2 rounded-full bg-brand-500" />{row.filled}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-1 text-sm font-mono text-amber-700">
                      <span className="w-2 h-2 rounded-full bg-amber-400" />{row.partial}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-1 text-sm font-mono text-red-600">
                      <span className="w-2 h-2 rounded-full bg-red-400" />{row.unfilled}
                    </span>
                  </td>
                  <td className="px-4 py-3"><FillRateHeatCell value={row.fill_rate} /></td>
                  <td className="px-4 py-3"><FillRateHeatCell value={row.show_up} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 mt-4 pt-4 border-t border-surface-100">
          <span className="text-xs text-surface-400">Fill Rate Scale:</span>
          {[
            { label:'≥90%', bg:'bg-brand-500 text-white' },
            { label:'80-89%', bg:'bg-brand-200 text-brand-800' },
            { label:'70-79%', bg:'bg-amber-100 text-amber-800' },
            { label:'60-69%', bg:'bg-orange-100 text-orange-800' },
            { label:'<60%', bg:'bg-red-100 text-red-700' },
          ].map(l => (
            <span key={l.label} className={`px-2 py-0.5 rounded text-xs font-medium ${l.bg}`}>{l.label}</span>
          ))}
        </div>
      </SectionCard>

      {/* Timeline + Shift breakdown */}
      <div className="grid grid-cols-3 gap-4">
        <SectionCard title="Rider Attendance Trend" subtitle="Required vs confirmed vs shown up" className="col-span-2">
          <DemandTimelineChart data={demandTimeline} />
          <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-surface-100">
            {[
              { label:'Total Required',  value: dt.reduce((a,d)=>a+d.required,0),  color:'text-surface-600' },
              { label:'Total Confirmed', value: dt.reduce((a,d)=>a+d.confirmed,0), color:'text-brand-600' },
              { label:'Total Shown Up',  value: dt.reduce((a,d)=>a+d.shown_up,0),  color:'text-blue-600' },
            ].map(s => (
              <div key={s.label} className="text-center">
                <p className={`text-2xl font-display font-bold ${s.color}`}>{s.value}</p>
                <p className="text-xs text-surface-400 mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Shift Distribution">
          {[
            { shift:'Morning (06-14)', pct:52, color:'brand' },
            { shift:'Afternoon (14-22)', pct:34, color:'blue' },
            { shift:'Night (22-06)', pct:14, color:'purple' },
          ].map(s => (
            <div key={s.shift} className="mb-4">
              <ProgressBar value={s.pct} max={100} label={s.shift} color={s.color} />
            </div>
          ))}
          <div className="border-t border-surface-100 pt-4 mt-2">
            <p className="label mb-3">Top Earners This Week</p>
            <div className="space-y-2">
              {[
                { name:'Ramesh K.',  earnings: 4200, orders: 120 },
                { name:'Priya S.',   earnings: 3850, orders: 110 },
                { name:'Suresh Y.',  earnings: 3640, orders: 104 },
              ].map((r, i) => (
                <div key={r.name} className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-xs font-bold">
                    {i+1}
                  </span>
                  <span className="flex-1 text-xs text-surface-700">{r.name}</span>
                  <span className="text-xs font-mono text-brand-600 font-bold">₹{r.earnings}</span>
                  <span className="text-xs text-surface-400">{r.orders} orders</span>
                </div>
              ))}
            </div>
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
