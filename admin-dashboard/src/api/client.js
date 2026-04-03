// src/api/client.js
import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 15000,
})

// Attach JWT token from localStorage
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('yana_admin_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Handle 401 — redirect to login
client.interceptors.response.use(
  (res) => res.data,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('yana_admin_token')
      window.location.href = '/login'
    }
    return Promise.reject(err.response?.data?.error || err.message)
  }
)

// ── Auth ──────────────────────────────────────────────────────
export const authApi = {
  login: (email, password) =>
    client.post('/auth/admin/login', { email, password }),
  me: () => client.get('/auth/me'),
}

// ── Riders ────────────────────────────────────────────────────
export const ridersApi = {
  list:   (params) => client.get('/riders/', { params }),
  get:    (id)     => client.get(`/riders/${id}/`),
  kyc:    (id, data) => client.post(`/riders/${id}/kyc/decide/`, data),
  activate: (id)  => client.post(`/riders/${id}/activate/`),
}

// ── Fleet ─────────────────────────────────────────────────────
export const fleetApi = {
  dashboard: (params) => client.get('/fleet/dashboard/utilization/', { params }),
  hubs:      (params) => client.get('/fleet/hubs/', { params }),
  vehicles:  (params) => client.get('/fleet/vehicles/', { params }),
  allotments: (params) => client.get('/fleet/allotments/', { params }),
  alerts:    (params) => client.get('/fleet/alerts/', { params }),
}

// ── Payments ──────────────────────────────────────────────────
export const paymentsApi = {
  summary:  ()       => client.get('/payments/admin/summary/'),
  wallet:   (id)     => client.get(`/payments/wallets/${id}/`),
  ledger:   (id, p)  => client.get(`/payments/wallets/${id}/ledger/`, { params: p }),
  adjust:   (id, d)  => client.post(`/payments/wallets/${id}/adjust/`, d),
}

// ── Marketplace ───────────────────────────────────────────────
export const marketplaceApi = {
  slots:     (params) => client.get('/marketplace/slots/', { params }),
  fillRates: (params) => client.get('/marketplace/analytics/fill-rates/', { params }),
  dashboard: ()       => client.get('/marketplace/analytics/dashboard/'),
  clients:   ()       => client.get('/marketplace/clients/'),
}

// ── Maintenance ───────────────────────────────────────────────
export const maintenanceApi = {
  logs:    (params) => client.get('/maintenance/logs/', { params }),
  alerts:  (params) => client.get('/maintenance/alerts/', { params }),
  costs:   (params) => client.get('/maintenance/analytics/costs/', { params }),
}

// ── Support ───────────────────────────────────────────────────
export const supportApi = {
  tickets:   (params) => client.get('/support/tickets/all/', { params }),
  analytics: ()       => client.get('/support/analytics/summary/'),
}

export default client
