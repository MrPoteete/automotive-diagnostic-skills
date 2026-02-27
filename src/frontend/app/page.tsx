"use client";

// Checked AGENTS.md - implementing directly, UI orchestration layer.
// VehicleForm and vehicles.ts data module handle structured vehicle input.

import React, { useState, useEffect } from 'react';
import { Terminal, ShieldAlert, Zap, Search, Activity, Cpu, ChevronDown } from 'lucide-react';
import { MAKES, getModelsForMake, YEARS } from '../lib/vehicles';
import { CyberButton } from './components/CyberButton';
import { ShardCard } from './components/ShardCard';
import { TypewriterText } from './components/TypewriterText';
import { LoadingState } from './components/LoadingState';
import { CyberInput } from './components/CyberInput';
import VehicleForm from './components/VehicleForm';
import { api, type VehicleInfo } from '../lib/api';

export default function Home() {
    const [activeTab, setActiveTab] = useState('diagnose');
    const [systemStatus, setSystemStatus] = useState('CHECKING');
    const [inputText, setInputText] = useState('');
    const [messages, setMessages] = useState<Array<{ role: 'user' | 'system', content: string }>>([
        { role: 'system', content: 'NEURAL LINK ESTABLISHED. CHECKING BACKEND CONNECTION...' }
    ]);
    const [isProcessing, setIsProcessing] = useState(false);
    const [searchPage, setSearchPage] = useState(1);
    const [searchTotalPages, setSearchTotalPages] = useState(1);
    const [lastSearchQuery, setLastSearchQuery] = useState('');
    const [tsbMake, setTsbMake] = useState('');
    const [tsbModel, setTsbModel] = useState('');
    const [tsbYear, setTsbYear] = useState('');

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

    /** Structured diagnostic from VehicleForm — bypasses text parsing entirely. */
    const handleDiagnose = async (vehicle: VehicleInfo, symptoms: string, dtcCodes: string[]) => {
        const dtcLabel = dtcCodes.length ? ` [${dtcCodes.join(', ')}]` : '';
        const userQuery = `${vehicle.year} ${vehicle.make} ${vehicle.model} — ${symptoms}${dtcLabel}`;

        setMessages(prev => [...prev, { role: 'user', content: userQuery }]);
        setIsProcessing(true);

        try {
            const diagData = await api.diagnose({ vehicle, symptoms, dtc_codes: dtcCodes });
            setMessages(prev => [...prev, { role: 'system', content: api.formatDiagnosis(diagData) }]);
        } catch (error) {
            setMessages(prev => [
                ...prev,
                { role: 'system', content: api.formatError(error as Error) }
            ]);
        } finally {
            setIsProcessing(false);
        }
    };

    const handleTsbMakeChange = (newMake: string) => {
        setTsbMake(newMake); setTsbModel(''); setTsbYear('');
    };
    const handleTsbModelChange = (newModel: string) => {
        setTsbModel(newModel); setTsbYear('');
    };

    // Reset pagination when TSB vehicle filters change
    useEffect(() => {
        setSearchPage(1); setSearchTotalPages(1);
    }, [tsbMake, tsbModel, tsbYear]);

    /** Free-text search for TSB / complaint queries (non-diagnose tabs). */
    const handleSearch = async (page: number = 1) => {
        const queryText = page === 1 ? inputText.trim() : lastSearchQuery;
        const isOnTsbTab = activeTab === 'tsbsearch';
        // Allow empty query on TSB tab when a vehicle make is selected
        if (!queryText && !(isOnTsbTab && tsbMake)) return;

        if (page === 1) {
            const displayText = queryText || `[Vehicle: ${tsbMake}${tsbModel ? ' ' + tsbModel : ''}${tsbYear ? ' ' + tsbYear : ''}]`;
            setMessages(prev => [...prev, { role: 'user', content: displayText }]);
            setInputText('');
            setLastSearchQuery(queryText);
        }
        setIsProcessing(true);

        try {
            let response: string;
            const isTsb = queryText.toLowerCase().includes('tsb') || queryText.toLowerCase().includes('bulletin');

            if (isTsb || isOnTsbTab) {
                // Vehicle filter args only apply on TSB Search tab
                const make = isOnTsbTab ? (tsbMake || undefined) : undefined;
                const model = isOnTsbTab ? (tsbModel || undefined) : undefined;
                const yr = isOnTsbTab && tsbYear ? parseInt(tsbYear, 10) : undefined;
                const tsbData = await (make
                    ? api.searchTSBs(queryText, 10, page, make, model, yr)
                    : api.searchTSBs(queryText, 10, page));
                setSearchPage(tsbData.page ?? 1);
                setSearchTotalPages(tsbData.total_pages ?? 1);
                response = api.formatResults(tsbData);
            } else {
                const complaintData = await api.searchComplaints(queryText, 10, page);
                setSearchPage(complaintData.page ?? 1);
                setSearchTotalPages(complaintData.total_pages ?? 1);
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
                            const tabKey = item.toLowerCase().replace(' ', '');
                            const isActive = activeTab === tabKey;
                            return (
                                <button
                                    key={item}
                                    onClick={() => setActiveTab(tabKey)}
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

                        {/* OFFLINE BANNER — shown when backend is unreachable */}
                        {systemStatus === 'OFFLINE' && (
                            <div className="border border-cyber-pink/70 bg-cyber-pink/10 p-4 font-mono text-sm shadow-lg">
                                <div className="flex items-center gap-2 mb-3">
                                    <ShieldAlert className="h-5 w-5 text-cyber-pink shrink-0" />
                                    <span className="text-cyber-pink font-bold tracking-widest uppercase">Diagnostic Server Unreachable</span>
                                </div>
                                <p className="text-cyber-gray mb-3">
                                    Please check your Tailscale connection and ensure the Home Server is running.
                                </p>
                                <div className="border-t border-cyber-pink/30 pt-3 space-y-1 text-xs text-cyber-gray">
                                    <p className="text-cyber-yellow font-bold mb-1 tracking-wider">TROUBLESHOOTING:</p>
                                    <p>›&nbsp; Verify Tailscale is connected and active</p>
                                    <p>›&nbsp; Confirm Home Server is running: <code className="text-cyber-white bg-black/50 px-1">curl http://localhost:8000/</code></p>
                                    <p>›&nbsp; Check server logs: <code className="text-cyber-white bg-black/50 px-1">tail -f /tmp/backend.log</code></p>
                                </div>
                            </div>
                        )}

                        {/* WELCOME CARD */}
                        <ShardCard corner="tr" className="mb-6 group">
                            <div className="absolute top-0 right-0 p-2 text-cyber-gray font-mono text-xs">ID: 9942-ALPHA</div>
                            <h2 className="text-2xl font-display text-cyber-white mb-2">NEURAL LINK ESTABLISHED</h2>
                            <p className="text-cyber-gray font-mono max-w-2xl mb-6">
                                {activeTab === 'diagnose'
                                    ? 'Select year, make, and model below, then describe symptoms to begin differential diagnosis.'
                                    : 'Ready for input. Describe symptoms or search TSBs using the command input below.'}
                            </p>

                            <div className="flex gap-4">
                                <CyberButton variant="primary" onClick={() => setActiveTab('diagnose')}>INITIATE SCAN</CyberButton>
                                <CyberButton variant="secondary" onClick={() => {
                                    setActiveTab('tsbsearch');
                                    setInputText('TSB ');
                                }}>SEARCH TSBs</CyberButton>
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

                    {/* INPUT AREA — VehicleForm for Diagnose tab, CyberInput for all others */}
                    <div className="p-4 bg-cyber-dark/80 backdrop-blur border-t border-cyber-gray/30 shrink-0">
                        {activeTab === 'diagnose' ? (
                            <VehicleForm onDiagnose={handleDiagnose} isProcessing={isProcessing} />
                        ) : (
                            <div className="flex flex-col gap-2">
                                {/* TSB vehicle filter row — only on TSB Search tab */}
                                {activeTab === 'tsbsearch' && (
                                    <div className="grid grid-cols-3 gap-2">
                                        {/* MAKE */}
                                        <div className="relative">
                                            <select
                                                aria-label="TSB MAKE"
                                                value={tsbMake}
                                                onChange={e => handleTsbMakeChange(e.target.value)}
                                                className="cyber-select w-full appearance-none bg-black/80 border border-cyber-gray/30 text-cyber-white font-mono text-xs px-2 py-2 pr-7 focus:outline-none focus:border-cyber-blue"
                                            >
                                                <option value="">-- MAKE --</option>
                                                {MAKES.map(m => <option key={m} value={m}>{m}</option>)}
                                            </select>
                                            <ChevronDown className="absolute right-1.5 top-1/2 -translate-y-1/2 h-3 w-3 text-cyber-blue pointer-events-none" />
                                        </div>
                                        {/* MODEL */}
                                        <div className="relative">
                                            <select
                                                aria-label="TSB MODEL"
                                                value={tsbModel}
                                                disabled={!tsbMake}
                                                onChange={e => handleTsbModelChange(e.target.value)}
                                                className="cyber-select w-full appearance-none bg-black/80 border border-cyber-gray/30 text-cyber-white font-mono text-xs px-2 py-2 pr-7 focus:outline-none focus:border-cyber-blue disabled:opacity-40 disabled:cursor-not-allowed"
                                            >
                                                <option value="">{tsbMake ? '-- MODEL --' : '-- SELECT MAKE --'}</option>
                                                {getModelsForMake(tsbMake).map(m => <option key={m} value={m}>{m}</option>)}
                                            </select>
                                            <ChevronDown className="absolute right-1.5 top-1/2 -translate-y-1/2 h-3 w-3 text-cyber-blue pointer-events-none" />
                                        </div>
                                        {/* YEAR */}
                                        <div className="relative">
                                            <select
                                                aria-label="TSB YEAR"
                                                value={tsbYear}
                                                disabled={!tsbModel}
                                                onChange={e => setTsbYear(e.target.value)}
                                                className="cyber-select w-full appearance-none bg-black/80 border border-cyber-gray/30 text-cyber-white font-mono text-xs px-2 py-2 pr-7 focus:outline-none focus:border-cyber-blue disabled:opacity-40 disabled:cursor-not-allowed"
                                            >
                                                <option value="">{tsbModel ? '-- YEAR --' : '-- SELECT MODEL --'}</option>
                                                {YEARS.map(y => <option key={y} value={String(y)}>{y}</option>)}
                                            </select>
                                            <ChevronDown className="absolute right-1.5 top-1/2 -translate-y-1/2 h-3 w-3 text-cyber-blue pointer-events-none" />
                                        </div>
                                    </div>
                                )}
                                <CyberInput
                                    value={inputText}
                                    onChange={(e) => setInputText(e.target.value)}
                                    onSubmit={handleSearch}
                                    isProcessing={isProcessing}
                                    placeholder={
                                        activeTab === 'tsbsearch'
                                            ? 'SEARCH TSBs: e.g. TSB Ford F-150 transmission...'
                                            : 'ENTER COMMAND OR SYMPTOMS...'
                                    }
                                />
                                {searchTotalPages > 1 && (
                                    <div className="flex items-center justify-between font-mono text-xs text-cyber-gray border border-cyber-gray/20 px-3 py-1.5">
                                        <button
                                            onClick={() => handleSearch(searchPage - 1)}
                                            disabled={searchPage <= 1 || isProcessing}
                                            className="text-cyber-blue hover:text-cyber-white disabled:opacity-30 disabled:cursor-not-allowed tracking-widest uppercase"
                                        >
                                            ← PREV
                                        </button>
                                        <span className="text-cyber-gray">
                                            PAGE <span className="text-cyber-white">{searchPage}</span> / {searchTotalPages}
                                        </span>
                                        <button
                                            onClick={() => handleSearch(searchPage + 1)}
                                            disabled={searchPage >= searchTotalPages || isProcessing}
                                            className="text-cyber-blue hover:text-cyber-white disabled:opacity-30 disabled:cursor-not-allowed tracking-widest uppercase"
                                        >
                                            NEXT →
                                        </button>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                </section>

            </div>
        </main>
    );
}
