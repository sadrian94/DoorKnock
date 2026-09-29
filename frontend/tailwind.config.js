/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#fbf8f3',
          100: '#f5efe4',
          200: '#ebdcc5',
          300: '#dec29f',
          400: '#cfa276',
          500: '#c28654',
          600: '#b47045',
          700: '#965839',
          800: '#794732',
          900: '#643c2c',
        }
      }
    },
  },
  plugins: [],
}
