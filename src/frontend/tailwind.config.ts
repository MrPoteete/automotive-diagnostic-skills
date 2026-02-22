import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./app/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                cyber: {
                    black: "#050505",
                    dark: "#0a0a14",
                    blue: "#00f0ff",
                    pink: "#ff003c",
                    green: "#39ff14",
                    yellow: "#fcee0a",
                    gray: "#888888",
                    white: "#e0e0e0",
                },
            },
            fontFamily: {
                sans: ["var(--font-rajdhani)", "sans-serif"],
                mono: ["var(--font-roboto-mono)", "monospace"],
                display: ["var(--font-orbitron)", "sans-serif"],
            },
            boxShadow: {
                'neon-blue': '0 0 10px rgba(0, 240, 255, 0.5), 0 0 20px rgba(0, 240, 255, 0.3)',
                'neon-pink': '0 0 10px rgba(255, 0, 60, 0.5), 0 0 20px rgba(255, 0, 60, 0.3)',
            },
            animation: {
                'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                'glitch': 'glitch 1s linear infinite',
            },
            keyframes: {
                glitch: {
                    '2%, 64%': { transform: 'translate(2px,0) skew(0deg)' },
                    '4%, 60%': { transform: 'translate(-2px,0) skew(0deg)' },
                    '62%': { transform: 'translate(0,0) skew(5deg)' },
                },
            },
        },
    },
    plugins: [],
};
export default config;
