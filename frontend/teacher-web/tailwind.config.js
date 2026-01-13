/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#002FA7', // Klein Blue
          hover: '#00227a',
        },
        secondary: {
          DEFAULT: '#FFD700', // Professional Yellow
          hover: '#e6c200',
        },
        background: '#F8FAFC', // Slate-50
        surface: '#FFFFFF',
        text: {
          main: '#0F172A', // Slate-900
          sub: '#475569', // Slate-600
        },
        border: '#E2E8F0', // Slate-200
      },
      boxShadow: {
        'klein': '0 8px 30px rgb(0 47 167 / 6%)',
      },
      fontFamily: {
        sans: ['Inter', 'Plus Jakarta Sans', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
