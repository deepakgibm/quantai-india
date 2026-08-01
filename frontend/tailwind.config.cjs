/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: 'class',
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
                display: ['Poppins', 'sans-serif'],
                serif: ['Georgia', 'Cambria', 'Times New Roman', 'serif'],
            },
            colors: {
                brand: {
                    50: '#f0f9ff',
                    100: '#e0f2fe',
                    500: '#0ea5e9',
                    600: '#0284c7',
                    700: '#0369a1',
                    900: '#0c4a6e',
                },
                // Landing page design system
                canvas: '#050816',
                card: '#0E1425',
                upstox: '#5d3d90',
                term: {
                    bg: {
                        primary: '#0F172A',
                        secondary: '#111827',
                        tertiary: '#1E293B',
                    },
                    text: {
                        primary: '#F8FAFC',
                        secondary: '#CBD5E1',
                        muted: '#94A3B8',
                    },
                    bullish: '#10B981',
                    bearish: '#EF4444',
                    neutral: '#F59E0B',
                    info: '#3B82F6',
                    accent: '#8B5CF6',
                }
            },
            animation: {
                'float': 'float 6s ease-in-out infinite',
                'float-delayed': 'float 6s ease-in-out 2s infinite',
                'shimmer': 'shimmer 2.5s linear infinite',
                'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
                'spin-slow': 'spin 8s linear infinite',
                'fade-up': 'fadeUp 0.6s ease-out forwards',
                'ticker': 'ticker 30s linear infinite',
            },
            keyframes: {
                float: {
                    '0%, 100%': { transform: 'translateY(0px)' },
                    '50%': { transform: 'translateY(-12px)' },
                },
                shimmer: {
                    '0%': { backgroundPosition: '-200% center' },
                    '100%': { backgroundPosition: '200% center' },
                },
                pulseGlow: {
                    '0%, 100%': { boxShadow: '0 0 20px rgba(96, 165, 250, 0.3)' },
                    '50%': { boxShadow: '0 0 40px rgba(96, 165, 250, 0.6), 0 0 80px rgba(139, 92, 246, 0.3)' },
                },
                fadeUp: {
                    '0%': { opacity: '0', transform: 'translateY(24px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                ticker: {
                    '0%': { transform: 'translateX(0)' },
                    '100%': { transform: 'translateX(-50%)' },
                },
            },
            backgroundImage: {
                'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
                'grid-pattern': "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%2360a5fa' fill-opacity='0.04'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E\")",
            },
            boxShadow: {
                'glow-blue': '0 0 30px rgba(96, 165, 250, 0.25)',
                'glow-purple': '0 0 30px rgba(139, 92, 246, 0.25)',
                'glow-emerald': '0 0 30px rgba(16, 185, 129, 0.25)',
                'card': '0 1px 3px rgba(0,0,0,0.4), 0 8px 24px rgba(0,0,0,0.3)',
                'card-hover': '0 4px 12px rgba(0,0,0,0.5), 0 16px 48px rgba(0,0,0,0.4), 0 0 0 1px rgba(96,165,250,0.2)',
            },
        }
    },
    plugins: [],
}
