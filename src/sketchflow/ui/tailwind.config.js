/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#080C14',
        card: '#0F172A',
        cardBorder: 'rgba(255, 255, 255, 0.08)',
        accent: {
          emerald: '#10B981',
          indigo: '#6366F1',
          amber: '#F59E0B',
          cyan: '#06B6D4'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace']
      }
    },
  },
  plugins: [],
}
