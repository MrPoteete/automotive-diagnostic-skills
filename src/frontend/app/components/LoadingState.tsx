import React from 'react';

export const LoadingState = ({ text = "ANALYZING_DATA_STREAMS" }: { text?: string }) => {
    return (
        <div
            role="status"
            aria-live="polite"
            aria-label={text}
            style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '2rem',
                gap: '1rem',
            }}
        >
            {/* Carbon-style indeterminate progress bar */}
            <div
                style={{
                    width: '16rem',
                    height: '4px',
                    backgroundColor: '#e0e0e0',
                    overflow: 'hidden',
                    position: 'relative',
                }}
                aria-hidden="true"
            >
                <div
                    style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        height: '100%',
                        width: '40%',
                        backgroundColor: '#0f62fe',
                        animation: 'cds-progress-bar 1.4s ease-in-out infinite',
                    }}
                />
                <style>{`
                    @keyframes cds-progress-bar {
                        0%   { transform: translateX(-100%); }
                        60%  { transform: translateX(250%); }
                        100% { transform: translateX(250%); }
                    }
                `}</style>
            </div>

            {/* Status label — tested via getByText(/ANALYZING_DATA_STREAMS/i) */}
            <p
                style={{
                    fontSize: '0.75rem',
                    color: '#525252',
                    letterSpacing: '0.06em',
                    margin: 0,
                }}
            >
                {text}...
            </p>
        </div>
    );
};
