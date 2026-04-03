// src/pages/Skills.jsx
import { GraduationCap, Star, Flame, Award, BookOpen, Trophy } from 'lucide-react'
import { StatCard, SectionCard, ProgressBar, Avatar } from '../components/ui'
import { skillsOverview, riderStats } from '../api/mockData'

const modules = [
  { title:'App Usage & Navigation',      hi:'ऐप का उपयोग', mandatory:true,  completed:287, total:320, videos:2 },
  { title:'Delivery Etiquette',          hi:'डिलीवरी शिष्टाचार', mandatory:true, completed:241, total:320, videos:3 },
  { title:'Road Safety & Traffic Rules', hi:'सड़क सुरक्षा', mandatory:true,  completed:198, total:320, videos:3 },
  { title:'EV Vehicle Care',             hi:'ईवी देखभाल',  mandatory:true,  completed:172, total:320, videos:2 },
  { title:'Earnings & Wallet',           hi:'कमाई',        mandatory:false, completed:156, total:320, videos:2 },
  { title:'Advanced Riding Skills',      hi:'उन्नत कौशल',  mandatory:false, completed:89,  total:320, videos:4 },
]

export default function Skills() {
  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <h1 className="font-display text-2xl font-bold text-surface-900">Skills & Gamification</h1>
          <p className="text-sm text-surface-500 mt-0.5">Training modules · Points · Badges · Levels</p>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="In Training"     value={riderStats.training}                   icon={GraduationCap} accent="purple" />
        <StatCard title="Mandatory Done"  value={skillsOverview.mandatory_completed}    icon={BookOpen}      accent="brand"  />
        <StatCard title="Avg Level"       value={skillsOverview.avg_level}              icon={Star}          accent="amber"  />
        <StatCard title="Badges Awarded"  value={skillsOverview.badges_awarded}         icon={Award}         accent="blue"   />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <SectionCard title="Module Completion" subtitle="Mandatory first, then optional" className="col-span-2">
          <div className="space-y-5">
            {modules.map(m => (
              <div key={m.title}>
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-surface-800">{m.title}</p>
                      {m.mandatory && (
                        <span className="badge bg-brand-100 text-brand-700 text-xs">Mandatory</span>
                      )}
                    </div>
                    <p className="text-xs text-surface-400 mt-0.5">{m.hi} · {m.videos} videos</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-mono font-bold text-surface-700">{m.completed}/{m.total}</p>
                    <p className="text-xs text-surface-400">{Math.round(m.completed*100/m.total)}%</p>
                  </div>
                </div>
                <ProgressBar value={m.completed} max={m.total}
                  color={m.mandatory ? 'brand' : 'blue'} showPct={false} />
              </div>
            ))}
          </div>
        </SectionCard>

        <div className="space-y-4">
          {/* Leaderboard */}
          <SectionCard title="Leaderboard">
            <div className="space-y-3">
              {skillsOverview.leaderboard_top.map(r => (
                <div key={r.rank} className="flex items-center gap-3 p-2 hover:bg-surface-50 rounded-xl transition-colors">
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                    r.rank===1 ? 'bg-amber-400 text-white' :
                    r.rank===2 ? 'bg-surface-300 text-surface-700' :
                    r.rank===3 ? 'bg-amber-100 text-amber-700' :
                    'bg-surface-100 text-surface-500'
                  }`}>
                    {r.rank===1 ? <Trophy size={12} /> : r.rank}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-surface-800 truncate">{r.name}</p>
                    <p className="text-xs text-surface-400">Level {r.level}</p>
                  </div>
                  <span className="text-sm font-mono font-bold text-brand-600">{r.points.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </SectionCard>

          {/* Badge distribution */}
          <SectionCard title="Badge Distribution">
            {[
              { badge:'Quick Learner', count:89,  color:'bg-purple-100 text-purple-700' },
              { badge:'Consistent',    count:67,  color:'bg-blue-100 text-blue-700' },
              { badge:'Compliant',     count:124, color:'bg-brand-100 text-brand-700' },
              { badge:'Veteran',       count:32,  color:'bg-amber-100 text-amber-700' },
            ].map(b => (
              <div key={b.badge} className="flex items-center justify-between py-2">
                <span className={`badge ${b.color}`}>{b.badge}</span>
                <span className="text-sm font-mono font-bold text-surface-600">{b.count}</span>
              </div>
            ))}
          </SectionCard>

          {/* Level distribution */}
          <SectionCard title="Level Distribution">
            {[
              { level:'Level 1 — Novice',   count:94 },
              { level:'Level 2 — Beginner', count:82 },
              { level:'Level 3 — Learner',  count:57 },
              { level:'Level 4 — Skilled',  count:34 },
              { level:'Level 5 — Expert',   count:18 },
              { level:'Level 6 — Master',   count:5  },
            ].map(l => (
              <div key={l.level} className="mb-2">
                <ProgressBar value={l.count} max={94} label={`${l.level} (${l.count})`} showPct={false} color="brand" />
              </div>
            ))}
          </SectionCard>
        </div>
      </div>
    </div>
  )
}
