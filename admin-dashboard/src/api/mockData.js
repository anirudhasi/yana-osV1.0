// src/api/mockData.js
// Realistic mock data matching Yana OS backend schema.
// Replace with real API calls (see src/api/client.js).

import { subDays, format, startOfMonth, eachDayOfInterval } from 'date-fns'

const today = new Date()
const day   = (n) => format(subDays(today, n), 'MMM d')

// ── Revenue & Payments ────────────────────────────────────────
export const revenueData = Array.from({ length: 30 }, (_, i) => ({
  date:       day(29 - i),
  rent:       Math.round(45000 + Math.sin(i * 0.4) * 8000 + Math.random() * 5000),
  incentives: Math.round(12000 + Math.cos(i * 0.3) * 3000 + Math.random() * 2000),
  penalties:  Math.round(2000 + Math.random() * 1500),
}))

export const paymentSummary = {
  total_wallet_balance:  847320,
  rent_collected_today:  124500,
  rent_collected_mtd:    2847600,
  overdue_count:         23,
  overdue_amount:        56800,
  deposits_held:         1240000,
  active_wallets:        412,
}

// ── Fleet Utilization ─────────────────────────────────────────
export const hubUtilization = [
  { hub: 'Delhi North',      city: 'Delhi',     capacity: 50, allocated: 43, available: 5, maintenance: 2, utilization: 86 },
  { hub: 'Delhi South',      city: 'Delhi',     capacity: 40, allocated: 31, available: 7, maintenance: 2, utilization: 77.5 },
  { hub: 'Mumbai Central',   city: 'Mumbai',    capacity: 60, allocated: 54, available: 4, maintenance: 2, utilization: 90 },
  { hub: 'BLR North',        city: 'Bengaluru', capacity: 45, allocated: 38, available: 5, maintenance: 2, utilization: 84.4 },
  { hub: 'BLR South',        city: 'Bengaluru', capacity: 35, allocated: 29, available: 4, maintenance: 2, utilization: 82.9 },
]

export const fleetStatusBreakdown = [
  { name: 'Allocated',    value: 195, color: '#22c55e' },
  { name: 'Available',    value: 25,  color: '#3b82f6' },
  { name: 'Maintenance',  value: 10,  color: '#f59e0b' },
  { name: 'Retired',      value: 4,   color: '#94a3b8' },
]

export const utilizationTrend = Array.from({ length: 14 }, (_, i) => ({
  date:        day(13 - i),
  utilization: Math.round(80 + Math.sin(i * 0.5) * 8 + Math.random() * 5),
}))

// ── Riders ────────────────────────────────────────────────────
export const riders = Array.from({ length: 50 }, (_, i) => {
  const statuses     = ['ACTIVE','ACTIVE','ACTIVE','KYC_PENDING','VERIFIED','SUSPENDED','TRAINING','APPLIED']
  const kycStatuses  = ['VERIFIED','VERIFIED','SUBMITTED','UNDER_REVIEW','PENDING','REJECTED']
  const cities       = ['Delhi','Mumbai','Bengaluru']
  const hubs         = ['Delhi North Hub','Delhi South Hub','Mumbai Central','BLR North Hub','BLR South Hub']
  const names        = ['Ramesh Kumar','Suresh Yadav','Priya Sharma','Amit Singh','Deepak Mehta','Rahul Gupta','Monika Patel','Vikram Tiwari','Arun Nair','Geeta Devi','Sandeep Joshi','Kavita Singh','Raju Mishra','Sunita Devi','Manoj Verma','Pooja Gupta','Dinesh Sharma','Seema Rani','Rajesh Kumar','Anita Kumari']
  const n            = names[i % names.length]
  const status       = statuses[i % statuses.length]
  const kyc          = kycStatuses[i % kycStatuses.length]
  return {
    id:            `rider-${(i+1).toString().padStart(3,'0')}`,
    full_name:     `${n} ${i > 0 ? String.fromCharCode(65 + (i % 26)) : ''}`.trim(),
    phone:         `98765${(40000 + i).toString()}`,
    status,
    kyc_status:    kyc,
    city:          cities[i % 3],
    hub:           hubs[i % 5],
    wallet_balance: status === 'ACTIVE' ? Math.round(200 + Math.random() * 800) : 0,
    reliability_score: status === 'ACTIVE' ? +(6 + Math.random() * 4).toFixed(1) : null,
    created_at:    subDays(today, Math.floor(Math.random() * 90)).toISOString(),
  }
})

export const riderStats = {
  total:        412,
  active:       283,
  verified:     47,
  kyc_pending:  38,
  suspended:    12,
  training:     32,
  churn_rate:   4.2,
  new_this_week: 18,
}

export const riderGrowth = Array.from({ length: 12 }, (_, i) => ({
  month:    format(subDays(today, (11 - i) * 30), 'MMM'),
  riders:   Math.round(180 + i * 22 + Math.random() * 15),
  churned:  Math.round(5 + Math.random() * 8),
}))

export const riderStatusDist = [
  { name: 'Active',       value: 283, color: '#22c55e' },
  { name: 'Verified',     value: 47,  color: '#3b82f6' },
  { name: 'KYC Pending',  value: 38,  color: '#f59e0b' },
  { name: 'Training',     value: 32,  color: '#8b5cf6' },
  { name: 'Suspended',    value: 12,  color: '#ef4444' },
]

// ── Demand / Marketplace ──────────────────────────────────────
export const demandFillRates = [
  { client: 'Blinkit',   slots: 48, filled: 41, partial: 5, unfilled: 2, fill_rate: 85.4, show_up: 91.2 },
  { client: 'BigBasket', slots: 32, filled: 25, partial: 5, unfilled: 2, fill_rate: 78.1, show_up: 88.0 },
  { client: 'JioMart',   slots: 24, filled: 18, partial: 4, unfilled: 2, fill_rate: 75.0, show_up: 86.7 },
  { client: 'Zepto',     slots: 16, filled: 13, partial: 2, unfilled: 1, fill_rate: 81.3, show_up: 92.3 },
]

export const demandTimeline = Array.from({ length: 14 }, (_, i) => ({
  date:      day(13 - i),
  required:  Math.round(80 + Math.random() * 30),
  confirmed: Math.round(60 + Math.random() * 25),
  shown_up:  Math.round(50 + Math.random() * 20),
}))

export const marketplaceSummary = {
  active_slots:     18,
  total_applications: 342,
  confirmed_today:  67,
  fill_rate_avg:    81.2,
  top_client:       'Blinkit',
  earnings_paid_week: 847500,
}

// ── Maintenance ───────────────────────────────────────────────
export const maintenanceSummary = {
  active_alerts:   14,
  critical_alerts: 3,
  in_service:      10,
  cost_this_month: 284500,
  avg_downtime_hrs: 6.2,
  service_due_soon: 8,
}

export const maintenanceCostTrend = Array.from({ length: 6 }, (_, i) => ({
  month:   format(subDays(today, (5 - i) * 30), 'MMM'),
  labour:  Math.round(40000 + Math.random() * 20000),
  parts:   Math.round(25000 + Math.random() * 15000),
}))

export const alertsByType = [
  { type: 'Service Due',       count: 8, severity: 'MEDIUM' },
  { type: 'Battery Degraded',  count: 3, severity: 'HIGH' },
  { type: 'Insurance Expiring',count: 2, severity: 'HIGH' },
  { type: 'PUC Expiring',      count: 1, severity: 'CRITICAL' },
]

// ── Support ───────────────────────────────────────────────────
export const supportSummary = {
  open_tickets:    34,
  in_progress:     18,
  escalated:       5,
  sla_breached:    7,
  resolved_week:   89,
  avg_satisfaction: 4.2,
}

export const ticketsByCategory = [
  { category: 'Vehicle Issue',     count: 42 },
  { category: 'Payment Issue',     count: 31 },
  { category: 'App Issue',         count: 18 },
  { category: 'KYC Query',         count: 14 },
  { category: 'Customer Complaint',count: 11 },
  { category: 'General',           count: 9  },
]

// ── Skills ────────────────────────────────────────────────────
export const skillsOverview = {
  total_riders_in_training: 32,
  mandatory_completed:      247,
  avg_level:               2.8,
  badges_awarded:          312,
  leaderboard_top:         [
    { rank: 1, name: 'Ramesh K.', points: 2480, level: 6 },
    { rank: 2, name: 'Priya S.', points: 2210, level: 6 },
    { rank: 3, name: 'Suresh Y.', points: 1950, level: 5 },
    { rank: 4, name: 'Amit S.',  points: 1720, level: 5 },
    { rank: 5, name: 'Geeta D.', points: 1580, level: 4 },
  ],
}
