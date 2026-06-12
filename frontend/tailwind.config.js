/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        // MoodMarket brand colors
        bullish:  { DEFAULT: '#10B981', light: '#34D399', dark: '#059669' },
        bearish:  { DEFAULT: '#EF4444', light: '#F87171', dark: '#DC2626' },
        neutral:  { DEFAULT: '#6B7280', light: '#9CA3AF', dark: '#4B5563' },
        warning:  { DEFAULT: '#F59E0B', light: '#FCD34D', dark: '#D97706' },
        signal:   { DEFAULT: '#3B82F6', light: '#60A5FA', dark: '#2563EB' },
        negative: { DEFAULT: '#F43F5E', light: '#FB7185', dark: '#E11D48' },
        hype:     { DEFAULT: '#A855F7', light: '#C084FC', dark: '#9333EA' },
        // Surface layers
        surface: {
          950: '#020617',
          900: '#0f172a',
          800: '#1e293b',
          700: '#334155',
          600: '#475569',
        },
      },
      boxShadow: {
        glass: '0 4px 30px rgba(0,0,0,0.3)',
        card:  '0 1px 3px rgba(0,0,0,0.4), 0 4px 16px rgba(0,0,0,0.3)',
        glow:  { bullish: '0 0 20px rgba(16,185,129,0.25)', bearish: '0 0 20px rgba(239,68,68,0.25)' },
      },
      backdropBlur: { glass: '12px' },
      animation: {
        'fade-in':       'fadeIn 200ms ease-out',
        'slide-up':      'slideUp 250ms ease-out',
        'pulse-bullish': 'pulseBullish 2s ease-in-out infinite',
        'number-change': 'numberChange 300ms ease-out',
        'spin-slow':     'spin 3s linear infinite',
        'glow-bullish':  'glowBullish 2s ease-in-out infinite',
        'glow-bearish':  'glowBearish 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn:       { from: { opacity: 0, transform: 'translateY(4px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        slideUp:      { from: { opacity: 0, transform: 'translateY(12px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        numberChange: { '0%,100%': { color: 'inherit' }, '50%': { color: '#10B981' } },
        pulseBullish: { '0%,100%': { opacity: 1 }, '50%': { opacity: 0.6 } },
        glowBullish:  { '0%,100%': { boxShadow: '0 0 5px rgba(16,185,129,0.2)' }, '50%': { boxShadow: '0 0 20px rgba(16,185,129,0.5)' } },
        glowBearish:  { '0%,100%': { boxShadow: '0 0 5px rgba(239,68,68,0.2)' }, '50%': { boxShadow: '0 0 20px rgba(239,68,68,0.5)' } },
      },
      borderRadius: { card: '12px', badge: '6px' },
      spacing: { 4.5: '18px' },
    },
  },
  plugins: [],
};
