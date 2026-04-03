// src/pages/Login.jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Zap, Eye, EyeOff, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Login() {
  const [email, setEmail]       = useState('admin@yana.in')
  const [password, setPassword] = useState('Admin@123')
  const [showPwd, setShowPwd]   = useState(false)
  const [loading, setLoading]   = useState(false)
  const navigate                = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    try {
      // Real API call
      // const res = await authApi.login(email, password)
      // localStorage.setItem('yana_admin_token', res.data.tokens.access_token)

      // Demo: accept seeded credentials
      if (email === 'admin@yana.in' && password === 'Admin@123') {
        localStorage.setItem('yana_admin_token', 'demo_token_super_admin')
        toast.success('Welcome back, Super Admin')
        navigate('/')
      } else {
        throw new Error('Invalid credentials')
      }
    } catch {
      toast.error('Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-surface-950 flex items-center justify-center p-4">
      {/* Background grid */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.02)_1px,transparent_1px)] bg-[size:48px_48px]" />

      <div className="relative w-full max-w-sm">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-brand-600 flex items-center justify-center shadow-glow mb-4">
            <Zap size={28} className="text-white" />
          </div>
          <h1 className="font-display text-3xl font-bold text-white">Yana OS</h1>
          <p className="text-surface-500 text-sm mt-1">Admin Portal</p>
        </div>

        {/* Card */}
        <div className="bg-surface-900 border border-white/8 rounded-2xl p-8 shadow-2xl">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-surface-400 mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl bg-surface-800 border border-white/8 text-white text-sm
                           focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500/40
                           placeholder:text-surface-600 transition-all"
                placeholder="admin@yana.in"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-surface-400 mb-1.5">Password</label>
              <div className="relative">
                <input
                  type={showPwd ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-2.5 pr-10 rounded-xl bg-surface-800 border border-white/8 text-white text-sm
                             focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500/40
                             placeholder:text-surface-600 transition-all"
                  placeholder="Password"
                  required
                />
                <button type="button" onClick={() => setShowPwd(!showPwd)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-500 hover:text-surface-300 transition-colors">
                  {showPwd ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={loading}
              className="w-full py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-sm font-semibold
                         transition-all disabled:opacity-60 flex items-center justify-center gap-2 mt-2">
              {loading && <Loader2 size={15} className="animate-spin" />}
              {loading ? 'Signing in…' : 'Sign In'}
            </button>
          </form>

          {/* Demo credentials hint */}
          <div className="mt-5 p-3 bg-surface-800 rounded-xl">
            <p className="text-xs text-surface-500 mb-2 font-medium">Demo Accounts</p>
            {[
              { email:'admin@yana.in', role:'Super Admin', pwd:'Admin@123' },
              { email:'ops@yana.in',   role:'Hub Ops',    pwd:'Ops@123'   },
              { email:'sales@yana.in', role:'Sales',      pwd:'Sales@123' },
            ].map(u => (
              <button key={u.email}
                onClick={() => { setEmail(u.email); setPassword(u.pwd) }}
                className="w-full text-left px-2 py-1.5 rounded-lg hover:bg-surface-700 transition-colors group">
                <span className="text-xs text-surface-300 group-hover:text-white transition-colors">{u.email}</span>
                <span className="text-xs text-surface-600 ml-2">{u.role}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
