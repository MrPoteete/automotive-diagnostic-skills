import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./app/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            // Carbon Design System handles the primary design tokens.
            // Tailwind is retained for utilities only (e.g. animate-pulse).
        },
    },
    plugins: [],
};

export default config;
