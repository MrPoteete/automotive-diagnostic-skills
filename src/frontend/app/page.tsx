"use client";

import React, { useState, useEffect } from 'react';
import { Terminal, ShieldAlert, Zap, Search, Activity, Cpu } from 'lucide-react';
import { CyberButton } from './components/CyberButton';
import { ShardCard } from './components/ShardCard';
import { TypewriterText } from './components/TypewriterText';
import { LoadingState } from './components/LoadingState';
import { CyberInput } from './components/CyberInput';
import { api, type VehicleInfo } from '../lib/api';

// Known vehicle makes (normalized to NHTSA uppercase format)
const MAKE_MAP: Record<string, string> = {
    ford: 'FORD', chevrolet: 'CHEVROLET', chevy: 'CHEVROLET', gmc: 'GMC',
    ram: 'RAM', dodge: 'DODGE', chrysler: 'CHRYSLER', jeep: 'JEEP',
    buick: 'BUICK', cadillac: 'CADILLAC', toyota: 'TOYOTA', honda: 'HONDA',
    nissan: 'NISSAN', bmw: 'BMW', hyundai: 'HYUNDAI', kia: 'KIA',
    subaru: 'SUBARU', volkswagen: 'VOLKSWAGEN', vw: 'VOLKSWAGEN',
};

const DTC_REGEX = /\b([PCBU][0-3][0-9A-Fa-f]{3})\b/gi;
const YEAR_REGEX = /\b(19[9][0-9]|20[0-2][0-9]|2030)\b/;

function parseVehicleInput(text: string): {
    vehicle: VehicleInfo | null;
    symptoms: string;
    dtcCodes: string[];
} {
    // Extract DTC codes
    const dtcCodes = [...text.matchAll(DTC_REGEX)].map(m => m[1].toUpperCase());
    const nodtc = text.replace(DTC_REGEX, ' ').replace(/\s+/g, ' ').trim();

    // Extract year
    const yearMatch = nodtc.match(YEAR_REGEX);
    if (!yearMatch) return { vehicle: null, symptoms: text, dtcCodes };
    const year = parseInt(yearMatch[1]);

    // Find make
    const words = nodtc.split(/\s+/);
    let makeIdx = -1;
    let make = '';
    for (let i = 0; i < words.length; i++) {
        const mapped = MAKE_MAP[words[i].toLowerCase()];
        if (mapped) { makeIdx = i; make = mapped; break; }
    }
    if (makeIdx === -1) return { vehicle: null, symptoms: text, dtcCodes };

    // Model = next 1–2 words after make; symptoms = remainder
    const afterMake = words.slice(makeIdx + 1).filter(w => !YEAR_REGEX.test(w));
    const model = afterMake.slice(0, 2).join(' ').toUpperCase() || 'UNKNOWN';
    const symptoms = afterMake.slice(2).join(' ') || nodtc;

    return { vehicle: { make, model, year }, symptoms: symptoms || nodtc, dtcCodes };
}

export default function Home() {
    const [activeTab, setActiveTab] = useState('diagnose');
    const [systemStatus, setSystemStatus] = useState('CHECKING');
    const [inputText, setInputText] = useState('');
    const [messages, setMessages] = useState<Array<{ role: 'user' | 'system', content: string }>>([
        { role: 'system', content: 'NEURAL LINK ESTABLISHED. CHECKING BACKEND CONNECTION...' }
    ]);
    const [isProcessing, setIsProcessing] = useState(false);

    // Check backend health on mount
    useEffect(() => {
        const checkHealth = async () => {
            try {
                const health = await api.healthCheck();
                setSystemStatus('ONLINE');
                setMessages(prev => [
                    ...prev,
                    { role: 'system', content: `✓ Backend connection verified: ${health.message}\n\nReady for diagnostic queries.` }
                ]);
            } catch (error) {
                setSystemStatus('OFFLINE');
                setMessages(prev => [
                    ...prev,
                    { role: 'system', content: api.formatError(error as Error) }
                ]);
            }
        };

        checkHealth();
    }, []);

    const handleSend = async () => {
        if (!inputText.trim()) return;

        const userQuery = inputText.trim();

        setMessages(prev => [...prev, { role: 'user', content: userQuery }]);
        setInputText('');
        setIsProcessing(true);

        try {
            const { vehicle, symptoms, dtcCodes } = parseVehicleInput(userQuery);

            let response: string;

            if (vehicle) {
                // Full differential diagnosis via POST /diagnose
                const diagData = await api.diagnose({
                    vehicle,
                    symptoms,
                    dtc_codes: dtcCodes,
                });
                response = api.formatDiagnosis(diagData);
            } else if (
                userQuery.toLowerCase().includes('tsb') ||
                userQuery.toLowerCase().includes('bulletin')
            ) {
                // TSB keyword search (no vehicle parsed)
                const tsbData = await api.searchTSBs(userQuery, 10);
                response = api.formatResults(tsbData);
            } else {
                // General NHTSA complaint search fallback
                const complaintData = await api.searchComplaints(userQuery, 10);
                response = api.formatResults(complaintData);
            }

            setMessages(prev => [...prev, { role: 'system', content: response }]);
        } catch (error) {
            setMessages(prev => [
                ...prev,
                { role: 'system', content: api.formatError(error as Error) }
            ]);
        } finally {
            setIsProcessing(false);
        }
    };

    return (
        <main className="flex h-screen w-full flex-col font-sans text-cyber-white p-2 overflow-hidden">

            {/* HUD HEADER */}
            <header className="flex h-16 w-full items-center justify-between border-b border-cyber-gray/30 bg-cyber-dark/50 px-6 backdrop-blur-md shrink-0">
                <div className="flex items-center gap-4">
                    <Cpu className="h-8 w-8 text-cyber-blue animate-pulse" />
                    <h1 className="text-3xl font-display font-bold tracking-widest text-cyber-blue glitch-text" data-text="AUTODIAGNOSYS_V3">
                        AUTODIAGNOSYS<span className="text-xs align-top opacity-50">_V3</span>
                    </h1>
                </div>
                <div className="flex items-center gap-6 font-mono text-sm">
                    <div className="flex items-center gap-2">
                        <span className={`h-2 w-2 rounded-full animate-pulse ${
                            systemStatus === 'ONLINE' ? 'bg-cyber-green' :
                            systemStatus === 'OFFLINE' ? 'bg-cyber-pink' :
                            'bg-cyber-yellow'
                        }`}></span>
                        <span className={
                            systemStatus === 'ONLINE' ? 'text-cyber-green' :
                            systemStatus === 'OFFLINE' ? 'text-cyber-pink' :
                            'text-cyber-yellow'
                        }>SYSTEM {systemStatus}</span>
                    </div>
                    <div className="text-cyber-gray">PING: 24ms</div>
                    <div className="text-cyber-blue border border-cyber-blue/30 px-2 py-0.5 rounded">NET: SECURE</div>
                </div>
            </header>

            <div className="flex flex-1 overflow-hidden mt-2 gap-2 relative z-10">

                {/* SIDEBAR NAVIGATION */}
                <aside className="w-16 md:w-64 flex flex-col border-r border-cyber-gray/30 bg-cyber-dark/30 clip-corner-bl backdrop-blur-sm">
                    <nav className="flex flex-col gap-2 p-2">
                        {['Diagnose', 'Database', 'TSB Search', 'Settings'].map((item, idx) => {
                            const isActive = activeTab === item.toLowerCase().replace(' ', '');
                            return (
                                <button
                                    key={item}
                                    onClick={() => setActiveTab(item.toLowerCase().replace(' ', ''))}
                                    className={`
                      group relative flex items-center justify-start gap-3 p-3 text-left transition-all
                      border border-transparent hover:border-cyber-blue/50 hover:bg-cyber-blue/10
                      ${isActive ? 'bg-cyber-blue/10 border-l-2 border-l-cyber-blue text-cyber-blue' : 'text-cyber-gray'}
                    `}
                                >
                                    {idx === 0 && <Activity className="h-5 w-5" />}
                                    {idx === 1 && <Terminal className="h-5 w-5" />}
                                    {idx === 2 && <Search className="h-5 w-5" />}
                                    {idx === 3 && <Zap className="h-5 w-5" />}

                                    <span className="hidden md:block font-bold tracking-wider font-display uppercase">{item}</span>

                                    {/* Hover Glitch Decorative */}
                                    <div className="absolute right-0 top-0 h-full w-1 bg-cyber-blue opacity-0 transition-opacity group-hover:opacity-100"></div>
                                </button>
                            )
                        })}
                    </nav>

                    <div className="mt-auto p-4 border-t border-cyber-gray/20">
                        <div className="bg-cyber-pink/10 border border-cyber-pink/50 p-2 text-xs font-mono text-cyber-pink animate-pulse-slow flex items-center gap-2">
                            <ShieldAlert className="h-4 w-4" />
                            SAFETY PROTOCOLS ACTIVE
                        </div>
                    </div>
                </aside>

                {/* MAIN STAGE */}
                <section className="flex-1 flex flex-col gap-4 relative overflow-hidden">

                    {/* CONTENT AREA */}
                    <div className="flex-1 p-4 overflow-y-auto custom-scrollbar space-y-6">

                        {/* WELCOME CARD */}
                        <ShardCard corner="tr" className="mb-6 group">
                            <div className="absolute top-0 right-0 p-2 text-cyber-gray font-mono text-xs">ID: 9942-ALPHA</div>
                            <h2 className="text-2xl font-display text-cyber-white mb-2">NEURAL LINK ESTABLISHED</h2>
                            <p className="text-cyber-gray font-mono max-w-2xl mb-6">
                                Ready for input. connection to vehicle database authorized.
                                Please describe the symptoms or enter DTC codes to begin analysis.
                            </p>

                            <div className="flex gap-4">
                                <CyberButton variant="primary" onClick={() => setInputText("2018 Ford F-150 transmission shudder")}>INITIATE SCAN</CyberButton>
                                <CyberButton variant="secondary" onClick={() => setInputText("TSB Chevrolet Silverado")}>SEARCH TSBs</CyberButton>
                            </div>
                        </ShardCard>

                        {/* CHAT INTERFACE */}
                        <div className="flex flex-col gap-6 pb-20">
                            {messages.map((msg, idx) => (
                                <div key={idx} className={`max-w-3xl ${msg.role === 'user' ? 'self-end' : 'self-start'}`}>

                                    {msg.role === 'user' ? (
                                        <ShardCard corner="bl" className="bg-cyber-blue/5 border-cyber-blue/30 text-right">
                                            <p className="font-mono text-cyber-blue text-xs mb-1">USER_COMMAND</p>
                                            <p className="font-sans text-lg">{msg.content}</p>
                                        </ShardCard>
                                    ) : (
                                        <div className="relative pl-4">
                                            <div className="absolute left-0 top-0 bottom-0 w-1 bg-cyber-green/50"></div>
                                            <div className="bg-cyber-dark border border-cyber-gray/20 p-4 shadow-lg">
                                                <p className="font-mono text-cyber-green text-xs mb-2">SYSTEM_RESPONSE // AGENT: CLAUDE</p>
                                                <TypewriterText text={msg.content} speed={15} />
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ))}

                            {isProcessing && <LoadingState />}
                        </div>

                    </div>

                    {/* INPUT AREA */}
                    <div className="p-4 bg-cyber-dark/80 backdrop-blur border-t border-cyber-gray/30 shrink-0">
                        <CyberInput
                            value={inputText}
                            onChange={(e) => setInputText(e.target.value)}
                            onSubmit={handleSend}
                            isProcessing={isProcessing}
                            placeholder="ENTER COMMAND OR SYMPTOMS..."
                        />
                    </div>

                </section>

            </div>
        </main>
    );
}
