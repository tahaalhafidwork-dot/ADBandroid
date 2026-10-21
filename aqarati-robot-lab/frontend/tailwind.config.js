/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: { sans: ['Tajawal', 'Segoe UI', 'Tahoma', 'sans-serif'] },
      boxShadow: { soft: '0 12px 38px rgba(15, 35, 42, .08)' },
    },
  },
  plugins: [],
}

