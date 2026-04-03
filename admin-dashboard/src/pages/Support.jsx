// src/pages/Support.jsx
import { HeadphonesIcon, AlertTriangle, CheckCircle2, Clock, Star, MessageSquare } from 'lucide-react'
import { StatCard, SectionCard, Badge, ProgressBar } from '../components/ui'
import { supportSummary, ticketsByCategory } from '../api/mockData'
import { format, subDays } from 'date-fns'

const sampleTickets = [
  { id:'YNA-2025-00089', subject:'Vehicle charging port broken', category:'VEHICLE_ISSUE', status:'ESCALATED', priority:'HIGH',    rider:'Ramesh K.', created: subDays(new Date(),1).toISOString() },
  { id:'YNA-2025-00088', subject:'Wallet balance not updated after top-up', category:'PAYMENT_ISSUE', status:'IN_PROGRESS', priority:'HIGH', rider:'Priya S.', created: subDays(new Date(),1).toISOString() },
  { id:'YNA-2025-00087', subject:'App crashes on vehicle booking screen', category:'APP_ISSUE', status:'OPEN', priority:'MEDIUM', rider:'Suresh Y.', created: subDays(new Date(),2).toISOString() },
  { id:'YNA-2025-00086', subject:'KYC documents rejected — unclear reason', category:'KYC_QUERY', status:'RESOLVED', priority:'MEDIUM', rider:'Amit S.', created: subDays(new Date(),2).toISOString() },
  { id:'YNA-2025-00085', subject:'Customer complained about late delivery', category:'CUSTOMER_COMPLAINT', status:'CLOSED', priority:'LOW', rider:'Deepak M.', created: subDays(new Date(),3).toISOString() },
  { id:'YNA-2025-00084', subject:'Daily rent deducted twice', category:'PAYMENT_ISSUE', status:'ESCALATED', priority:'CRITICAL', rider:'Monika P.', created: subDays(new Date(),0).toISOString() },
  { id:'YNA-2025-00083', subject:'Unable to check-in to Blinkit shift', category:'APP_ISSUE', status:'OPEN', priority:'HIGH', rider:'Vikram T.', created: subDays(new Date(),0).toISOString() },
]

export default function Support() {
  const maxCategory = Math.max(...ticketsByCategory.map(t => t.count))

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <h1 className="font-display text-2xl font-bold text-surface-900">Support & Tickets</h1>
          <p className="text-sm text-surface-500 mt-0.5">SLA tracking · Agent assignment · WhatsApp fallback</p>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Open Tickets"    value={supportSummary.open_tickets}    icon={MessageSquare}  accent="blue"   />
        <StatCard title="SLA Breached"    value={supportSummary.sla_breached}    icon={AlertTriangle}  accent="red"    />
        <StatCard title="Resolved / Week" value={supportSummary.resolved_week}   icon={CheckCircle2}   accent="brand"  />
        <StatCard title="Avg Rating"      value={`${supportSummary.avg_satisfaction}★`} icon={Star}   accent="amber"  />
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* Recent tickets */}
        <SectionCard title="Recent Tickets" subtitle="Latest activity" className="col-span-2">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-surface-100">
                  {['Ticket','Rider','Category','Priority','Status','Created'].map(h => (
                    <th key={h} className="px-3 py-2.5 text-xs font-medium text-surface-500 uppercase tracking-wider whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sampleTickets.map((t, i) => (
                  <tr key={t.id}
                    className={`border-b border-surface-50 hover:bg-surface-50 transition-colors ${i%2===0?'bg-white':'bg-surface-50/30'}`}>
                    <td className="px-3 py-3">
                      <span className="text-xs font-mono font-semibold text-brand-600">{t.id}</span>
                      <p className="text-xs text-surface-500 mt-0.5 max-w-[160px] truncate">{t.subject}</p>
                    </td>
                    <td className="px-3 py-3 text-sm text-surface-600">{t.rider}</td>
                    <td className="px-3 py-3">
                      <span className="text-xs text-surface-500">{t.category.replace('_',' ')}</span>
                    </td>
                    <td className="px-3 py-3"><Badge status={t.priority} label={t.priority} /></td>
                    <td className="px-3 py-3"><Badge status={t.status} label={t.status.replace('_',' ')} /></td>
                    <td className="px-3 py-3 text-xs text-surface-400 whitespace-nowrap">
                      {format(new Date(t.created),'dd MMM')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        {/* Category breakdown */}
        <div className="space-y-4">
          <SectionCard title="By Category">
            <div className="space-y-3">
              {ticketsByCategory.map(c => (
                <div key={c.category}>
                  <ProgressBar
                    value={c.count} max={maxCategory}
                    label={`${c.category.replace('_',' ')} (${c.count})`}
                    color={c.category==='PAYMENT_ISSUE'?'red':c.category==='VEHICLE_ISSUE'?'amber':'blue'}
                    showPct={false} />
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="SLA Performance">
            {[
              { label:'Met',      pct:74, color:'brand' },
              { label:'At Risk',  pct:14, color:'amber' },
              { label:'Breached', pct:12, color:'red'   },
            ].map(s => (
              <div key={s.label} className="mb-3">
                <ProgressBar value={s.pct} max={100} label={`${s.label} — ${s.pct}%`} color={s.color} showPct={false} />
              </div>
            ))}
          </SectionCard>

          <SectionCard title="Queue by Priority">
            <div className="grid grid-cols-2 gap-3">
              {[
                { p:'CRITICAL', count:2, color:'bg-red-600 text-white' },
                { p:'HIGH',     count:11,color:'bg-red-100 text-red-700' },
                { p:'MEDIUM',   count:16,color:'bg-amber-100 text-amber-700' },
                { p:'LOW',      count:5, color:'bg-surface-100 text-surface-600' },
              ].map(s => (
                <div key={s.p} className={`rounded-xl p-3 text-center ${s.color}`}>
                  <p className="text-xl font-display font-bold">{s.count}</p>
                  <p className="text-xs opacity-80">{s.p}</p>
                </div>
              ))}
            </div>
          </SectionCard>
        </div>
      </div>
    </div>
  )
}
