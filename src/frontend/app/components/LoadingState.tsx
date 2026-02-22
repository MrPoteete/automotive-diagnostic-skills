import React from 'react';

export const LoadingState = ({ text = "ANALYZING_DATA_STREAMS" }: { text?: string }) => {
    return (
        <div className="flex flex-col items-center justify-center p-8 space-y-4 font-mono">
            <div className="relative w-64 h-2 bg-cyber-dark border border-cyber-gray/30 overflow-hidden">
                {/* Progress Bar Animation */}
                <div className="absolute top-0 left-0 h-full w-full bg-cyber-blue/50 animate-[shimmer_2s_infinite_linear] origin-left scale-x-30 translate-x-[-100%]" />

                <style jsx>{`
          @keyframes shimmer {
            0% { transform: translateX(-100%); }
            50% { transform: translateX(0%); }
            100% { transform: translateX(100%); }
          }
        `}</style>
            </div>

            <div className="flex items-center gap-2 text-cyber-blue text-xs tracking-widest animate-pulse">
                <span className="w-2 h-2 bg-cyber-blue rounded-full" />
                {text}...
            </div>

            {/* Decorative binary stream */}
            <div className="text-[10px] text-cyber-green/50 max-w-xs text-center overflow-hidden h-4">
                01001001 00100000 01100001 01101101 00100000 01000001 01001001
            </div>
        </div>
    );
};
