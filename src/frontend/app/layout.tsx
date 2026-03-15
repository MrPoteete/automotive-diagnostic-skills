import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import ErrorBoundaryWrapper from "./components/ErrorBoundary";

const ibmPlexSans = IBM_Plex_Sans({
    subsets: ["latin"],
    weight: ["300", "400", "500", "600", "700"],
    variable: "--font-ibm-plex-sans",
    display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
    subsets: ["latin"],
    weight: ["400", "500"],
    variable: "--font-ibm-plex-mono",
    display: "swap",
});

export const metadata: Metadata = {
    title: "Automotive Diagnostic System",
    description: "Professional Automotive Diagnostic Tool — Ford, GM, RAM, Toyota",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en">
            <body className={`${ibmPlexSans.variable} ${ibmPlexMono.variable}`}>
                <ErrorBoundaryWrapper>
                    {children}
                </ErrorBoundaryWrapper>
            </body>
        </html>
    );
}
