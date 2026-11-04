/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        brand: {
          50: '#f0eeff',
          100: '#e4e0ff',
          200: '#ccc5ff',
          300: '#a99cff',
          400: '#8166ff',
          500: '#6c47ff',
          600: '#5c2ef7',
          700: '#4e1ee3',
          800: '#3f18be',
          900: '#361799',
        },
        dark: {
          950: '#0a0a0f',
          900: '#0f0f1a',
          800: '#14141f',
          700: '#1a1a2e',
          600: '#20203a',
        },
      },
    },
  },
  plugins: [],
}
