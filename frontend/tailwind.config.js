/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Be Vietnam Pro"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      borderRadius: {
        card: '14px',
        control: '10px',
      },
      colors: {
        canvas: {
          dark: '#0B0D12',
          light: '#F8FAFC',
        },
        surface: {
          dark: '#12151C',
          'dark-elevated': '#181C25',
          light: '#FFFFFF',
          'light-elevated': '#F1F5F9',
        },
        accent: {
          indigo: '#6366F1',
          purple: '#8B5CF6',
        },
        credit: {
          amber: '#F59E0B',
        },
        brand: {
          50: '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
        },
      },
      transitionDuration: {
        DEFAULT: '150ms',
      },
    },
  },
  plugins: [],
}
