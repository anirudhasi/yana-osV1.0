// src/pages/Payments.jsx
import { CreditCard, TrendingUp, AlertCircle, Wallet, ArrowDownCircle, ArrowUpCircle } from 'lucide-react'
import { StatCard, SectionCard, ProgressBar } from '../components/ui'
import { RevenueChart, MaintenanceCostChart } from '../components/charts'
import { revenueData, paymentSummary } from '../api/mockData'

const fmt = (v) => `₹${(v/1000).toFixed(0)}K`
const fmtL = (v) => v >= 100000 ? `₹${(v/100000).toFixed(2)}L` : `₹${(v/1000).toFixed(0)}K`

export default function Payments() {
  const totalRevenue = revenueData.reduce((a, d) => a + d.rent + d.incentives, 0)

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <h1 className="font-display text-2xl font-bold text-surface-900">Payments & Wallet</h1>
          <p className="text-sm text-surface-500 mt-0.5">Double-entry ledger · Razorpay · UPI AutoPay</p>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Rent Collected Today"  value={fmtL(paymentSummary.rent_collected_today)}  icon={CreditCard}     accent="brand"  trend={12} trendLabel="vs yesterday" />
        <StatCard title="Rent MTD"               value={fmtL(paymentSummary.rent_collected_mtd)}   icon={TrendingUp}     accent="brand"  />
        <StatCard title="Total Wallet Balance"   value={fmtL(paymentSummary.total_wallet_balance)} icon={Wallet}         accent="blue"   subtitle={`${paymentSummary.active_wallets} active wallets`} />
        <StatCard title="Overdue Amount"         value={fmtL(paymentSummary.overdue_amount)}       icon={AlertCircle}    accent="red"    subtitle={`${paymentSummary.overdue_count} riders overdue`} />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <SectionCard title="Revenue Trend — 30 Days" subtitle="All payment types" className="col-span-2"
          action={<span className="text-xs font-mono font-bold text-brand-600">{fmtL(totalRevenue)} total</span>}>
          <RevenueChart data={revenueData} />
        </SectionCard>

        <div className="space-y-4">
          {/* Financial summary */}
          <div className="card p-5 space-y-4">
            <p className="label">Financial Summary</p>
            {[
              { label: 'Deposits Held',    value: paymentSummary.deposits_held,         icon: ArrowDownCircle, color: 'text-blue-500' },
              { label: 'Overdue Amount',   value: paymentSummary.overdue_amount,         icon: AlertCircle,    color: 'text-red-500' },
            ].map(s => (
              <div key={s.label} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <s.icon size={14} className={s.color} />
                  <span className="text-sm text-surface-600">{s.label}</span>
                </div>
                <span className="text-sm font-mono font-bold text-surface-800">{fmtL(s.value)}</span>
              </div>
            ))}
          </div>

          {/* Overdue breakdown */}
          <div className="card p-5">
            <p className="label mb-3">Overdue Analysis</p>
            <div className="text-center mb-4">
              <p className="text-3xl font-display font-bold text-red-500">{paymentSummary.overdue_count}</p>
              <p className="text-xs text-surface-400">riders with overdue rent</p>
            </div>
            <ProgressBar value={paymentSummary.overdue_count} max={paymentSummary.active_wallets}
              label={`${((paymentSummary.overdue_count/paymentSummary.active_wallets)*100).toFixed(1)}% of wallets`}
              color="red" />
            <p className="text-xs text-surface-400 mt-2">
              Average overdue: {fmtL(paymentSummary.overdue_amount / paymentSummary.overdue_count)} per rider
            </p>
          </div>

          {/* Collection efficiency */}
          <div className="card p-5">
            <p className="label mb-3">Collection Efficiency</p>
            <div className="space-y-3">
              {[
                { label: 'UPI AutoPay',    pct: 68, color: 'brand' },
                { label: 'Manual Top-up', pct: 22, color: 'blue'  },
                { label: 'Wallet Credit', pct: 10, color: 'purple' },
              ].map(m => (
                <ProgressBar key={m.label} value={m.pct} max={100} label={m.label} color={m.color} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
