// src/App.jsx
import { Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import AppLayout    from './components/layout/AppLayout'
import Login        from './pages/Login'
import Dashboard    from './pages/Dashboard'
import Riders       from './pages/Riders'
import Fleet        from './pages/Fleet'
import Payments     from './pages/Payments'
import Marketplace  from './pages/Marketplace'
import Maintenance  from './pages/Maintenance'
import Skills       from './pages/Skills'
import Support      from './pages/Support'

function RequireAuth({ children }) {
  const token = localStorage.getItem('yana_admin_token')
  if (!token) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#111811',
            color: '#fff',
            borderRadius: '12px',
            fontSize: '13px',
            border: '1px solid rgba(255,255,255,.08)',
          },
          success: { iconTheme: { primary: '#22c55e', secondary: '#fff' } },
          error:   { iconTheme: { primary: '#ef4444', secondary: '#fff' } },
        }}
      />

      <Routes>
        <Route path="/login" element={<Login />} />

        <Route path="/" element={
          <RequireAuth><AppLayout /></RequireAuth>
        }>
          <Route index          element={<Dashboard   />} />
          <Route path="riders"      element={<Riders      />} />
          <Route path="fleet"       element={<Fleet       />} />
          <Route path="payments"    element={<Payments    />} />
          <Route path="marketplace" element={<Marketplace />} />
          <Route path="maintenance" element={<Maintenance />} />
          <Route path="skills"      element={<Skills      />} />
          <Route path="support"     element={<Support     />} />
        </Route>
      </Routes>
    </>
  )
}
