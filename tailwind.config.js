/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ['selector', '[data-theme="dark"]'],
  content: [
    "./docs/**/*.{html,js,json}",
    "./autonomous_job_agent/web/templates/**/*.html",
    "./autonomous_job_agent/web/static/**/*.js"
  ],
  safelist: [
    'bg-emerald-500/20', 'text-emerald-400', 'border-emerald-500/40',
    'bg-amber-500/20', 'text-amber-300', 'border-amber-500/40',
    'bg-blue-500/20', 'text-blue-400', 'border-blue-500/30',
    'bg-purple-500/20', 'text-purple-400', 'border-purple-500/30',
    'bg-red-500/20', 'text-red-400', 'border-red-500/30',
    'bg-indigo-500/20', 'text-indigo-400', 'border-indigo-500/30',
    'bg-gray-800', 'bg-gray-900', 'bg-gray-950', 'text-white', 'text-gray-200', 'text-gray-300', 'text-gray-400',
    'hidden', 'block', 'flex', 'inline-flex', 'grid', 'space-y-4', 'space-y-6', 'active', 'animate-spin', 'animate-pulse'
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      }
    },
  },
  plugins: [],
}
