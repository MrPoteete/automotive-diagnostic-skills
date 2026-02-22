import React from 'react';
import { twMerge } from 'tailwind-merge';

interface ShardCardProps {
    children: React.ReactNode;
    className?: string;
    corner?: 'tr' | 'bl' | 'none'; // Top-Right, Bottom-Left, or None
}

export const ShardCard = ({ children, className, corner = 'tr' }: ShardCardProps) => {
    const clipClass = corner === 'tr' ? 'clip-corner-tr' : corner === 'bl' ? 'clip-corner-bl' : '';

    return (
        <div className={twMerge(
            "relative bg-cyber-dark border border-cyber-gray/20 p-6 shadow-lg backdrop-blur-sm",
            clipClass,
            "before:absolute before:inset-0 before:bg-gradient-to-br before:from-cyber-blue/5 before:to-transparent before:pointer-events-none", // Inner glow
            className
        )}>
            {/* Decorative Corner Accents */}
            {corner === 'tr' && (
                <div className="absolute top-0 right-0 w-16 h-[1px] bg-cyber-blue/50" />
            )}
            {corner === 'bl' && (
                <div className="absolute bottom-0 left-0 w-16 h-[1px] bg-cyber-pink/50" />
            )}

            <div className="relative z-10">
                {children}
            </div>
        </div>
    );
};
