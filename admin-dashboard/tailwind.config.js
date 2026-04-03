/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans:    ['DM Sans', 'system-ui', 'sans-serif'],
        mono:    ['JetBrains Mono', 'monospace'],
        display: ['Syne', 'sans-serif'],
      },
      colors: {
        brand: {
          50:  '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
          950: '#052e16',
        },
        surface: {
          0:   '#ffffff',
          50:  '#f8faf8',
          100: '#f0f4f0',
          200: '#e4ebe4',
          300: '#d1dcd1',
          400: '#9fb19f',
          500: '#6d846d',
          600: '#4d614d',
          700: '#314031',
          800: '#1a221a',
          900: '#111811',
          950: '#080c08',
        },
        accent: {
          amber:  '#f59e0b',
          red:    '#ef4444',
          blue:   '#3b82f6',
          purple: '#8b5cf6',
        },
      },
      boxShadow: {
        'card':  '0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04)',
        'card-hover': '0 4px 16px rgba(0,0,0,.08), 0 2px 4px rgba(0,0,0,.04)',
        'glow':  '0 0 0 3px rgba(34,197,94,.2)',
      },
      animation: {
        'fade-in':    'fadeIn .3s ease forwards',
        'slide-up':   'slideUp .35s cubic-bezier(.16,1,.3,1) forwards',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn:    { from: { opacity: 0 },                    to: { opacity: 1 } },
        slideUp:   { from: { opacity: 0, transform: 'translateY(12px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        pulseSoft: { '0%,100%': { opacity: 1 }, '50%': { opacity: .6 } },
      },
    },
  },
  plugins: [],
}
