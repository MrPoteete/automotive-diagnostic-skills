import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

interface CyberButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
    glitch?: boolean;
}

export const CyberButton = ({
    children,
    className,
    variant = 'primary',
    glitch = true,
    ...props
}: CyberButtonProps) => { // Removed React.FC for cleaner functional component definition

    const baseStyles = "relative px-6 py-2 font-bold tracking-widest text-sm uppercase transition-all duration-300 group overflow-hidden font-display disabled:opacity-50 disabled:cursor-not-allowed";

    const variants = {
        primary: "bg-cyber-blue/10 border border-cyber-blue text-cyber-blue hover:bg-cyber-blue hover:text-black hover:shadow-neon-blue",
        secondary: "bg-transparent border border-cyber-gray/50 text-cyber-gray hover:border-cyber-white hover:text-cyber-white",
        danger: "bg-cyber-pink/10 border border-cyber-pink text-cyber-pink hover:bg-cyber-pink hover:text-black hover:shadow-neon-pink",
        ghost: "bg-transparent text-cyber-blue hover:bg-cyber-blue/10 border-transparent",
    };

    return (
        <button
            className={twMerge(baseStyles, variants[variant], className)}
            {...props}
        >
            <span className="relative z-10 flex items-center justify-center gap-2">
                {children}
            </span>

            {/* Glitch Overlay Elements */}
            {glitch && (
                <>
                    <span className="absolute inset-0 bg-white opacity-0 group-hover:opacity-10 transition-opacity duration-75" />
                    <span className="absolute top-0 left-0 w-full h-[1px] bg-current opacity-0 group-hover:opacity-50 group-hover:animate-ping" />
                </>
            )}
        </button>
    );
};
