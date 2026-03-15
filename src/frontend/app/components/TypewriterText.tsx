"use client";

import React, { useState, useEffect, useRef } from 'react';

interface TypewriterTextProps {
    text: string;
    speed?: number; // ms per char
    onComplete?: () => void;
    className?: string;
}

export const TypewriterText = ({ text, speed = 15, onComplete, className = "" }: TypewriterTextProps) => {
    const [displayedText, setDisplayedText] = useState('');
    const [isComplete, setIsComplete] = useState(false);

    // Fix memory leak: Use ref for onComplete to avoid re-creating effect
    const onCompleteRef = useRef(onComplete);
    useEffect(() => {
        onCompleteRef.current = onComplete;
    }, [onComplete]);

    useEffect(() => {
        setDisplayedText('');
        setIsComplete(false);

        let i = 0;
        const interval = setInterval(() => {
            if (i < text.length) {
                setDisplayedText((prev) => prev + text.charAt(i));
                i++;
            } else {
                clearInterval(interval);
                setIsComplete(true);
                if (onCompleteRef.current) onCompleteRef.current();
            }
        }, speed);

        return () => clearInterval(interval);
    }, [text, speed]); // Removed onComplete from dependencies

    return (
        <div style={{ fontFamily: 'IBM Plex Mono, monospace' }} className={className}>
            {displayedText}
            {!isComplete && (
                <span
                    className="animate-pulse"
                    style={{
                        display: 'inline-block',
                        width: '8px',
                        height: '16px',
                        backgroundColor: '#0f62fe',
                        marginLeft: '2px',
                        verticalAlign: 'middle',
                    }}
                    aria-hidden="true"
                />
            )}
        </div>
    );
};
