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
                sans: ['Inter', 'sans-serif'],
                display: ['Poppins', 'sans-serif'],
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
            }
        }
    },
    plugins: [],
}
