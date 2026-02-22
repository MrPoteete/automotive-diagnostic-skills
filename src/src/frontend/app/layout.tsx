import type { Metadata } from "next";
import { Rajdhani, Orbitron, Roboto_Mono } from "next/font/google";
import "./globals.css";
import ErrorBoundaryWrapper from "./components/ErrorBoundary";

const rajdhani = Rajdhani({
    subsets: ["latin"],
    weight: ["300", "400", "500", "600", "700"],
    variable: "--font-rajdhani",
});

const orbitron = Orbitron({
    subsets: ["latin"],
    variable: "--font-orbitron",
});

const robotoMono = Roboto_Mono({
    subsets: ["latin"],
    variable: "--font-roboto-mono",
});

export const metadata: Metadata = {
    title: "AutoDiagnostix | AI Neural Interface",
    description: "Advanced Automotive Diagnostic System",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" className="dark">
            <body className={`${rajdhani.variable} ${orbitron.variable} ${robotoMono.variable} bg-cyber-black text-cyber-white antialiased overflow-hidden`}>
                <div className="fixed inset-0 pointer-events-none z-50 scanlines opacity-20"></div>
                <div className="fixed inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-cyber-dark/50 via-cyber-black/80 to-cyber-black pointer-events-none -z-10"></div>
                <ErrorBoundaryWrapper>
                    {children}
                </ErrorBoundaryWrapper>
            </body>
        </html>
    );
}
