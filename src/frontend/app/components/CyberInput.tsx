import React from 'react';
import { ArrowRight } from 'lucide-react';

interface CyberInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
    onSubmit?: () => void;
    isProcessing?: boolean;
}

export const CyberInput = ({ onSubmit, isProcessing, ...props }: CyberInputProps) => {
    return (
        <div className="relative group w-full">
            {/* Decorative border line */}
            <div className="absolute -inset-0.5 bg-gradient-to-r from-cyber-blue via-cyber-pink to-cyber-blue rounded opacity-30 group-focus-within:opacity-100 transition duration-500 group-focus-within:animate-pulse"></div>

            <div className="relative flex items-center bg-black/90">
                <span className="pl-4 font-mono text-cyber-blue animate-pulse">{'>'}</span>

                <input
                    {...props}
                    className="w-full bg-transparent border-none py-4 px-4 text-cyber-white font-mono focus:ring-0 focus:outline-none placeholder-cyber-gray/50"
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey && onSubmit) {
                            e.preventDefault();
                            onSubmit();
                        }
                    }}
                />

                <button
                    onClick={onSubmit}
                    disabled={isProcessing || !props.value}
                    className="px-6 py-2 m-1 bg-cyber-blue/10 text-cyber-blue border-l border-cyber-gray/30 hover:bg-cyber-blue hover:text-black transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {isProcessing ? (
                        <span className="animate-spin block h-4 w-4 border-2 border-current border-t-transparent rounded-full" />
                    ) : (
                        <ArrowRight className="h-5 w-5" />
                    )}
                </button>
            </div>
        </div>
    );
};
