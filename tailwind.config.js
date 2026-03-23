/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./templates/**/*.html",
    "./static/**/*.js"
  ],
  theme: {
    extend: {
      colors: {
        navy: {
            900: '#001F3F',
            800: '#002952',
            700: '#003366',
        },
        platinum: {
            100: '#FAFAFA',
            200: '#E0E0E0',
            300: '#B0B0B0',
        },
        dark: {
            900: '#0A0F1A',
            800: '#131824',
        }
      },
      fontFamily: {
        'inter': ['Inter', 'sans-serif'],
      }
    }
  },
  plugins: [],
}
