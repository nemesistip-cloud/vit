/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        vit: {
          50:  '#f0f4ff',
          100: '#e0e9ff',
          200: '#c1d4ff',
          300: '#93b4ff',
          400: '#5f8aff',
          500: '#3b65ff',
          600: '#2247f5',
          700: '#1a35e1',
          800: '#1c2db6',
          900: '#1c2a8f',
          950: '#131a5a',
        },
        surface: {
          900: '#0a0d14',
          800: '#0f1520',
          700: '#141c2e',
          600: '#1a2540',
          500: '#1f2d50',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 8s linear infinite',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-12px)' },
        },
      },
      backgroundImage: {
        'grid-pattern': 'linear-gradient(rgba(59,101,255,0.07) 1px, transparent 1px), linear-gradient(90deg, rgba(59,101,255,0.07) 1px, transparent 1px)',
        'radial-vit': 'radial-gradient(ellipse at center, rgba(59,101,255,0.15) 0%, transparent 70%)',
      },
      backgroundSize: {
        'grid': '40px 40px',
      },
    },
  },
  plugins: [],
}
