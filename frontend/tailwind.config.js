/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}', './lib/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: '#FAFAF8',
        ink: '#171717',
        muted: '#666666',
        line: '#E7E5E0',
        card: '#FFFFFF',
        gold: {
          DEFAULT: '#D9A441',
          soft: '#F5EBD6',
          deep: '#B8862B',
        },
        navy: {
          DEFAULT: '#142033',
          soft: '#E8EBF0',
        },
        alert: {
          DEFAULT: '#A8442A',
          soft: '#F7E9E4',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
      },
      fontSize: {
        // Editorial hierarchy from the UI spec.
        hero: ['clamp(2.125rem, 5vw, 3.75rem)', { lineHeight: '1.05', letterSpacing: '-0.03em' }],
        section: ['clamp(1.5rem, 3vw, 2.25rem)', { lineHeight: '1.15', letterSpacing: '-0.02em' }],
        cardtitle: ['1.1875rem', { lineHeight: '1.3', letterSpacing: '-0.01em' }],
        body: ['1rem', { lineHeight: '1.65' }],
        support: ['0.875rem', { lineHeight: '1.6' }],
        label: ['0.75rem', { lineHeight: '1.4', letterSpacing: '0.08em' }],
      },
      maxWidth: {
        page: '1280px',
        prose: '68ch',
      },
      boxShadow: {
        card: '0 1px 2px rgba(23, 23, 23, 0.03), 0 8px 24px -12px rgba(23, 23, 23, 0.10)',
        lift: '0 2px 4px rgba(23, 23, 23, 0.04), 0 18px 40px -20px rgba(23, 23, 23, 0.18)',
        panel: '0 1px 0 rgba(231, 229, 224, 1)',
      },
      transitionDuration: {
        DEFAULT: '180ms',
      },
      keyframes: {
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'pulse-ring': {
          '0%': { transform: 'scale(0.85)', opacity: '0.7' },
          '70%': { transform: 'scale(1.6)', opacity: '0' },
          '100%': { transform: 'scale(1.6)', opacity: '0' },
        },
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
        'bar-travel': {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(300%)' },
        },
      },
      animation: {
        'fade-up': 'fade-up 240ms cubic-bezier(0.22, 1, 0.36, 1) both',
        'fade-in': 'fade-in 200ms ease-out both',
        'pulse-ring': 'pulse-ring 1.8s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        shimmer: 'shimmer 1.6s infinite',
        'bar-travel': 'bar-travel 1.4s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
