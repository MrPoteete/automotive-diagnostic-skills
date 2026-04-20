"use client";

// Checked AGENTS.md - implementing directly, UI orchestration layer.
// Carbon Design System rewrite — preserves all behavioral test contracts.

import React, { useState, useEffect } from 'react';
import { MAKES, YEARS, getModelsForMake } from '../lib/vehicles';
import { TypewriterText } from './components/TypewriterText';
import { LoadingState } from './components/LoadingState';
import VehicleIdentification, { type VehicleIdentity } from './components/VehicleIdentification';
import VehicleDashboard from './components/VehicleDashboard';
import ReportModal from './components/ReportModal';
import DiagnosisHistory from './components/DiagnosisHistory';
import ChecklistPanel from './components/ChecklistPanel';
import { parseDtcInput } from './components/VehicleForm';
import { api, saveHistory, type VehicleInfo, type DiagnoseResponse } from '../lib/api';
import PlatformTsbPanel from './components/PlatformTsbPanel';

// Carbon icon SVG inlines — avoids SCSS import issues in test environment
function IconActivity() {
    return (
        <svg focusable="false" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg"
            fill="currentColor" width="20" height="20" viewBox="0 0 32 32" aria-hidden="true">
            <path d="M28 18h-4.18l-3.1-9.3A1 1 0 0019.77 8a1 1 0 00-.94.72L15 21.34 12.13 10.7A1 1 0 0011.2 10a1 1 0 00-.97.66L7.72 18H4v2h4.28a1 1 0 00.94-.66L11 13.58l2.87 10.72a1 1 0 00.93.7H15a1 1 0 00.95-.68l3.8-12.44 2.31 6.92A1 1 0 0023 19.5h5z" />
        </svg>
    );
}

function IconSearch() {
    return (
        <svg focusable="false" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg"
            fill="currentColor" width="20" height="20" viewBox="0 0 32 32" aria-hidden="true">
            <path d="M29 27.586l-7.552-7.552a11.018 11.018 0 10-1.414 1.414L27.586 29zM4 13a9 9 0 119 9 9.01 9.01 0 01-9-9z" />
        </svg>
    );
}

function IconDatabase() {
    return (
        <svg focusable="false" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg"
            fill="currentColor" width="20" height="20" viewBox="0 0 32 32" aria-hidden="true">
            <path d="M16 2C8.832 2 4 5.14 4 9v14c0 3.86 4.832 7 12 7s12-3.14 12-7V9c0-3.86-4.832-7-12-7zm10 20.5c0 2.36-4.144 5-10 5S6 24.86 6 22.5V20a16.27 16.27 0 0010 3 16.27 16.27 0 0010-3zm0-6c0 2.36-4.144 5-10 5S6 18.86 6 16.5V14a16.27 16.27 0 0010 3 16.27 16.27 0 0010-3zm-10-3C10.144 13.5 6 10.86 6 8.5S10.144 3.5 16 3.5 26 5.14 26 7.5 21.856 13.5 16 13.5z" />
        </svg>
    );
}

function IconDocument() {
    return (
        <svg focusable="false" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg"
            fill="currentColor" width="20" height="20" viewBox="0 0 32 32" aria-hidden="true">
            <path d="M25.7 9.3l-7-7A1 1 0 0018 2H8a2 2 0 00-2 2v24a2 2 0 002 2h16a2 2 0 002-2V10a1 1 0 00-.3-.7zM18 4.4l5.6 5.6H18zM24 28H8V4h8v6a2 2 0 002 2h6z" />
            <path d="M10 22h12v2H10zM10 16h12v2H10z" />
        </svg>
    );
}

function IconWarning() {
    return (
        <svg focusable="false" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg"
            fill="currentColor" width="16" height="16" viewBox="0 0 32 32" aria-hidden="true">
            <path d="M16 2a14 14 0 1014 14A14 14 0 0016 2zm-1 6h2v11h-2zm1 17.25A1.25 1.25 0 1117.25 24 1.25 1.25 0 0116 25.25z" />
        </svg>
    );
}

function IconChecklist() {
    return (
        <svg focusable="false" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg"
            fill="currentColor" width="20" height="20" viewBox="0 0 32 32" aria-hidden="true">
            <path d="M11 14H6a2 2 0 00-2 2v5a2 2 0 002 2h5a2 2 0 002-2v-5a2 2 0 00-2-2zm0 7H6v-5h5zM11 4H6a2 2 0 00-2 2v5a2 2 0 002 2h5a2 2 0 002-2V6a2 2 0 00-2-2zm0 7H6V6h5zM28 6h-2V4h-2v2h-6V4h-2v2h-2v2h2v2h2V8h6v2h2V8h2zM18 14h-2v2h2zM22 14h-2v2h2zM26 14h-2v2h2zM18 18h-2v2h2zM22 18h-2v2h2zM26 18h-2v2h2zM18 22h-2v2h2zM22 22h-2v2h2zM26 22h-2v2h2z" />
        </svg>
    );
}

function IconChevronDown() {
    return (
        <svg focusable="false" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg"
            fill="currentColor" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
            <path d="M8 11L3 6 3.7 5.3 8 9.6 12.3 5.3 13 6z" />
        </svg>
    );
}

type Tab = 'diagnose' | 'database' | 'tsbsearch' | 'recallsearch' | 'prepurchase';

interface NavItem {
    key: Tab;
    label: string;
    icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
    { key: 'diagnose', label: 'Diagnose', icon: <IconActivity /> },
    { key: 'database', label: 'Database', icon: <IconDatabase /> },
    { key: 'tsbsearch', label: 'TSB Search', icon: <IconDocument /> },
    { key: 'recallsearch', label: 'Recall Search', icon: <IconWarning /> },
    { key: 'prepurchase', label: 'Pre-Purchase', icon: <IconChecklist /> },
];

export default function Home() {
    const [activeTab, setActiveTab] = useState<Tab>('diagnose');
    const [systemStatus, setSystemStatus] = useState<'CHECKING' | 'ONLINE' | 'OFFLINE'>('CHECKING');
    const [inputText, setInputText] = useState('');
    const [messages, setMessages] = useState<Array<{ role: 'user' | 'system'; content: string }>>([]);
    const [isProcessing, setIsProcessing] = useState(false);
    const [searchPage, setSearchPage] = useState(1);
    const [searchTotalPages, setSearchTotalPages] = useState(1);
    const [lastSearchQuery, setLastSearchQuery] = useState('');
    const [tsbMake, setTsbMake] = useState('');
    const [tsbModel, setTsbModel] = useState('');
    const [tsbYear, setTsbYear] = useState('');
    const [recallMake, setRecallMake] = useState('');
    const [recallYear, setRecallYear] = useState('');
    const [selectedVehicle, setSelectedVehicle] = useState<VehicleIdentity | null>(null);
    const [symptoms, setSymptoms] = useState('');
    const [dtcInput, setDtcInput] = useState('');
    const [reportModalOpen, setReportModalOpen] = useState(false);
    const [lastDiagnosisResult, setLastDiagnosisResult] = useState<DiagnoseResponse | null>(null);

    // Check backend health on mount
    useEffect(() => {
        const checkHealth = async () => {
            try {
                await api.healthCheck();
                setSystemStatus('ONLINE');
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

    /** Structured diagnostic from VehicleForm */
    const handleDiagnose = async (vehicle: VehicleInfo, symptoms: string, dtcCodes: string[]) => {
        const dtcLabel = dtcCodes.length ? ` [${dtcCodes.join(', ')}]` : '';
        const userQuery = `${vehicle.year} ${vehicle.make} ${vehicle.model} — ${symptoms}${dtcLabel}`;

        setMessages(prev => [...prev, { role: 'user', content: userQuery }]);
        setIsProcessing(true);

        try {
            const diagData = await api.diagnose({ vehicle, symptoms, dtc_codes: dtcCodes });
            const formattedDiagnosis = api.formatDiagnosis(diagData);
            setMessages(prev => [...prev, { role: 'system', content: formattedDiagnosis }]);
            setLastDiagnosisResult(diagData);
            // Fire-and-forget — never block the diagnosis flow
            saveHistory({
                vin: selectedVehicle?.vin,
                year: vehicle.year,
                make: vehicle.make,
                model: vehicle.model,
                engine: selectedVehicle?.engine,
                symptoms,
                dtc_codes: dtcCodes,
                findings: formattedDiagnosis,
                candidate_count: diagData.candidates.length,
                has_warnings: diagData.warnings.length > 0,
            }).catch(() => {});
        } catch (error) {
            setMessages(prev => [
                ...prev,
                { role: 'system', content: api.formatError(error as Error) }
            ]);
        } finally {
            setIsProcessing(false);
        }
    };

    const handleVehicleSelected = (vehicle: VehicleIdentity) => {
        setSelectedVehicle(vehicle);
        setSymptoms('');
        setDtcInput('');
        setLastDiagnosisResult(null);
    };

    const handleSubmitDiagnose = () => {
        if (!selectedVehicle || !symptoms.trim() || isProcessing) return;
        const vehicleInfo: VehicleInfo = {
            make: selectedVehicle.make,
            model: selectedVehicle.model,
            year: selectedVehicle.year,
        };
        handleDiagnose(vehicleInfo, symptoms, parseDtcInput(dtcInput));
    };

    const handleSymptomsKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && e.ctrlKey && !isProcessing) handleSubmitDiagnose();
    };

    const handleTsbMakeChange = (newMake: string) => {
        setTsbMake(newMake);
        setTsbModel('');
        setTsbYear('');
    };

    const handleTsbModelChange = (newModel: string) => {
        setTsbModel(newModel);
        setTsbYear('');
    };

    // Reset pagination when TSB vehicle filters change
    useEffect(() => {
        setSearchPage(1);
        setSearchTotalPages(1);
    }, [tsbMake, tsbModel, tsbYear]);

    // Reset pagination when recall filters change
    useEffect(() => {
        setSearchPage(1);
        setSearchTotalPages(1);
    }, [recallMake, recallYear]);

    /** Free-text search for TSB / complaint / recall queries */
    const handleSearch = async (page: number = 1) => {
        const queryText = page === 1 ? inputText.trim() : lastSearchQuery;
        const isOnTsbTab = activeTab === 'tsbsearch';
        const isOnRecallTab = activeTab === 'recallsearch';
        if (!queryText && !(isOnTsbTab && tsbMake) && !(isOnRecallTab && recallMake)) return;

        if (page === 1) {
            const displayText = queryText
                || (isOnTsbTab ? `[Vehicle: ${tsbMake}${tsbModel ? ' ' + tsbModel : ''}${tsbYear ? ' ' + tsbYear : ''}]` : '')
                || (isOnRecallTab ? `[Recalls: ${recallMake}${recallYear ? ' ' + recallYear : ''}]` : '');
            setMessages(prev => [...prev, { role: 'user', content: displayText }]);
            setInputText('');
            setLastSearchQuery(queryText);
        }
        setIsProcessing(true);

        try {
            let response: string;

            if (isOnRecallTab) {
                const make = recallMake || undefined;
                const yr = recallYear ? parseInt(recallYear, 10) : undefined;
                const recallData = await api.searchRecalls(queryText, 10, page, make, yr);
                setSearchPage(recallData.page ?? 1);
                setSearchTotalPages(recallData.total_pages ?? 1);
                response = api.formatRecallResults(recallData);
            } else {
                const isTsb = queryText.toLowerCase().includes('tsb') || queryText.toLowerCase().includes('bulletin');
                if (isTsb || isOnTsbTab) {
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

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !isProcessing) {
            handleSearch();
        }
    };

    const handleClearDiagnose = () => {
        setSymptoms('');
        setDtcInput('');
        setMessages([]);
        setLastDiagnosisResult(null);
    };

    const handleClearSearch = () => {
        setInputText('');
        setMessages([]);
        setSearchPage(1);
        setSearchTotalPages(1);
        setLastSearchQuery('');
        if (activeTab === 'tsbsearch') {
            setTsbMake('');
            setTsbModel('');
            setTsbYear('');
        }
        if (activeTab === 'recallsearch') {
            setRecallMake('');
            setRecallYear('');
        }
    };

    return (
        <div className="app-shell">

            {/* ── Carbon-style Header ─────────────────────────────────────── */}
            <header
                className="cds--header"
                role="banner"
                aria-label="Automotive Diagnostic System"
            >
                <a className="cds--header__name" href="/" aria-label="Automotive Diagnostic System — Home">
                    <span className="cds--header__name--prefix">ADS&nbsp;</span>
                    Automotive Diagnostic System
                </a>

                {/* System status indicator */}
                <div
                    style={{
                        marginLeft: 'auto',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        paddingRight: '1.5rem',
                        fontSize: '0.875rem',
                        color: '#c6c6c6',
                    }}
                >
                    <span
                        className={`status-dot ${
                            systemStatus === 'ONLINE' ? 'online' :
                            systemStatus === 'OFFLINE' ? 'offline' :
                            'checking'
                        }`}
                        aria-hidden="true"
                    />
                    <span>
                        System{' '}
                        {systemStatus === 'ONLINE' ? 'Online' :
                         systemStatus === 'OFFLINE' ? 'Offline' :
                         'Checking...'}
                    </span>
                </div>
            </header>

            {/* ── Body: side nav + content ─────────────────────────────────── */}
            <div className="app-body">

                {/* ── Side Navigation ───────────────────────────────────────── */}
                <nav className="app-sidenav" aria-label="Main navigation">
                    <ul style={{ listStyle: 'none', margin: 0, padding: '1rem 0' }}>
                        {NAV_ITEMS.map((item) => (
                            <li key={item.key}>
                                <button
                                    type="button"
                                    className={`nav-item${activeTab === item.key ? ' active' : ''}`}
                                    onClick={() => setActiveTab(item.key)}
                                    aria-current={activeTab === item.key ? 'page' : undefined}
                                >
                                    {item.icon}
                                    <span>{item.label}</span>
                                </button>
                            </li>
                        ))}
                    </ul>

                    {/* Safety protocol notice at bottom of nav */}
                    <div
                        style={{
                            marginTop: 'auto',
                            padding: '1rem',
                            borderTop: '1px solid #393939',
                            fontSize: '0.75rem',
                            color: '#8d8d8d',
                        }}
                    >
                        Safety protocols active. CRITICAL systems require confidence &ge; 0.9.
                    </div>
                </nav>

                {/* ── Main Content ──────────────────────────────────────────── */}
                <main className="app-content" id="main-content">

                    {/* OFFLINE BANNER */}
                    {systemStatus === 'OFFLINE' && (
                        <div className="offline-banner" role="alert">
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                                <IconWarning />
                                <strong>Diagnostic Server Unreachable</strong>
                            </div>
                            <p style={{ margin: '0 0 0.75rem', fontSize: '0.875rem', color: '#525252' }}>
                                The backend server could not be reached. Check your network connection and server status below.
                            </p>
                            <ul style={{ fontSize: '0.8125rem', color: '#525252', borderTop: '1px solid #ffb3b8', paddingTop: '0.75rem', paddingLeft: '1.25rem', margin: 0 }}>
                                <li>Verify Tailscale is connected and active</li>
                                <li>
                                    Confirm Home Server is running:{' '}
                                    <code style={{ fontFamily: 'monospace', backgroundColor: '#f4f4f4', padding: '0 4px' }}>
                                        curl http://localhost:8000/
                                    </code>
                                </li>
                                <li>
                                    Check server logs:{' '}
                                    <code style={{ fontFamily: 'monospace', backgroundColor: '#f4f4f4', padding: '0 4px' }}>
                                        tail -f /tmp/backend.log
                                    </code>
                                </li>
                            </ul>
                        </div>
                    )}

                    {/* ── DIAGNOSE TAB ─────────────────────────────────────── */}
                    {activeTab === 'diagnose' && (
                        <div>
                            {/* Page heading */}
                            <div style={{ marginBottom: '1.5rem' }}>
                                <h1 className="cds--productive-heading-04" style={{ marginBottom: '0.5rem' }}>
                                    Vehicle Diagnostic
                                </h1>
                                <p className="cds--body-short-01" style={{ color: 'var(--cds-text-secondary)' }}>
                                    Select a vehicle and describe symptoms to begin a differential diagnosis.
                                </p>
                            </div>

                            {/* Vehicle Identification — VIN or manual entry */}
                            <div
                                style={{
                                    background: 'var(--cds-layer-01)',
                                    border: '1px solid var(--cds-border-subtle-01)',
                                    padding: '1.5rem',
                                    marginBottom: '1rem',
                                }}
                            >
                                <VehicleIdentification
                                    onVehicleSelected={handleVehicleSelected}
                                    isProcessing={isProcessing}
                                />
                            </div>

                            {/* Selected vehicle summary bar */}
                            {selectedVehicle && (
                                <div
                                    style={{
                                        background: 'var(--cds-layer-02)',
                                        border: '1px solid var(--cds-border-subtle-02)',
                                        borderLeft: '3px solid #0f62fe',
                                        padding: '0.75rem 1.5rem',
                                        marginBottom: '1rem',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.75rem',
                                        fontSize: '0.875rem',
                                        color: 'var(--cds-text-primary)',
                                    }}
                                >
                                    <strong>
                                        {selectedVehicle.year} {selectedVehicle.make} {selectedVehicle.model}
                                    </strong>
                                    {selectedVehicle.engine && (
                                        <span style={{ color: 'var(--cds-text-secondary)' }}>· {selectedVehicle.engine}</span>
                                    )}
                                    {selectedVehicle.drive_type && (
                                        <span style={{ color: 'var(--cds-text-secondary)' }}>· {selectedVehicle.drive_type}</span>
                                    )}
                                    {selectedVehicle.vin && (
                                        <span style={{ color: 'var(--cds-text-secondary)', fontFamily: 'monospace', fontSize: '0.75rem' }}>
                                            VIN: {selectedVehicle.vin}
                                        </span>
                                    )}
                                    <button
                                        type="button"
                                        onClick={() => setSelectedVehicle(null)}
                                        style={{
                                            marginLeft: 'auto',
                                            background: 'none',
                                            border: 'none',
                                            color: 'var(--cds-text-secondary)',
                                            cursor: 'pointer',
                                            fontSize: '0.75rem',
                                            padding: '0.25rem 0.5rem',
                                        }}
                                    >
                                        Change
                                    </button>
                                </div>
                            )}

                            {/* Diagnosis History — prior sessions for this vehicle */}
                            {selectedVehicle && (
                                <DiagnosisHistory
                                    make={selectedVehicle.make}
                                    model={selectedVehicle.model}
                                    year={selectedVehicle.year}
                                    vin={selectedVehicle.vin}
                                />
                            )}

                            {/* Vehicle Dashboard — auto-loads stats after vehicle selected */}
                            {selectedVehicle && (
                                <div style={{ marginBottom: '1rem' }}>
                                    <VehicleDashboard
                                        make={selectedVehicle.make}
                                        model={selectedVehicle.model}
                                        year={selectedVehicle.year}
                                        onReportClick={() => setReportModalOpen(true)}
                                    />
                                </div>
                            )}

                            {/* Symptoms + DTC form — only visible once vehicle selected */}
                            {selectedVehicle && (
                                <div
                                    style={{
                                        background: 'var(--cds-layer-01)',
                                        border: '1px solid var(--cds-border-subtle-01)',
                                        padding: '1.5rem',
                                        marginBottom: '2rem',
                                    }}
                                >
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                        <div className="cds--form-item">
                                            <label htmlFor="symptoms-input" className="cds--label">
                                                Symptoms / Complaint Description
                                            </label>
                                            <div className="cds--text-area-wrapper" style={{ width: '100%' }}>
                                                <textarea
                                                    id="symptoms-input"
                                                    className="cds--text-area"
                                                    style={{ width: '100%' }}
                                                    rows={6}
                                                    value={symptoms}
                                                    onChange={(e) => setSymptoms(e.target.value)}
                                                    onKeyDown={handleSymptomsKeyDown}
                                                    placeholder="Describe symptoms in detail. e.g. Rough idle at cold start, surging RPM, check engine light..."
                                                    disabled={isProcessing}
                                                />
                                            </div>
                                            <p className="cds--form__helper-text">Ctrl+Enter to submit</p>
                                        </div>
                                        <div className="cds--form-item">
                                            <label htmlFor="dtc-input" className="cds--label">
                                                DTC Codes (optional)
                                            </label>
                                            <div className="cds--text-input-wrapper" style={{ width: '80%' }}>
                                                <input
                                                    id="dtc-input"
                                                    type="text"
                                                    className="cds--text-input"
                                                    style={{ width: '100%' }}
                                                    value={dtcInput}
                                                    onChange={(e) => setDtcInput(e.target.value.toUpperCase())}
                                                    placeholder="e.g. P0300, P0301, C0034"
                                                    disabled={isProcessing}
                                                />
                                            </div>
                                            <p className="cds--form__helper-text">Separate multiple codes with commas</p>
                                        </div>
                                        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                                            <button
                                                type="button"
                                                onClick={handleSubmitDiagnose}
                                                disabled={!symptoms.trim() || isProcessing}
                                                className="cds--btn cds--btn--primary"
                                            >
                                                {isProcessing ? (
                                                    <>
                                                        <span className="loading-spinner" style={{ marginRight: '0.5rem' }} />
                                                        Analyzing...
                                                    </>
                                                ) : (
                                                    'Run Diagnostic'
                                                )}
                                            </button>
                                            {(symptoms || dtcInput || messages.length > 0) && (
                                                <button
                                                    type="button"
                                                    onClick={handleClearDiagnose}
                                                    disabled={isProcessing}
                                                    className="cds--btn cds--btn--ghost"
                                                    data-testid="clear-diagnose-btn"
                                                >
                                                    Clear
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Diagnostic results */}
                            <div className="message-area">
                                {messages.map((msg, idx) => (
                                    <div key={idx}>
                                        {msg.role === 'user' ? (
                                            <div className="query-bubble">
                                                <div style={{ fontSize: '0.75rem', opacity: 0.8, marginBottom: '0.25rem' }}>
                                                    Query
                                                </div>
                                                {msg.content}
                                            </div>
                                        ) : (
                                            <div className="response-card">
                                                <div style={{
                                                    fontSize: '0.6875rem',
                                                    textTransform: 'uppercase',
                                                    letterSpacing: '0.08em',
                                                    color: '#0f62fe',
                                                    marginBottom: '0.5rem',
                                                    fontFamily: 'inherit',
                                                }}>
                                                    Diagnostic Report
                                                </div>
                                                <TypewriterText text={msg.content} speed={15} />
                                            </div>
                                        )}
                                    </div>
                                ))}

                                {isProcessing && <LoadingState />}
                            </div>

                            {/* Platform Family TSBs — shown after diagnosis when platform data is available */}
                            {!isProcessing &&
                                lastDiagnosisResult?.platform_family &&
                                (
                                    <PlatformTsbPanel
                                        platformFamily={lastDiagnosisResult.platform_family}
                                        platformSiblings={lastDiagnosisResult.platform_siblings ?? []}
                                        candidates={lastDiagnosisResult.candidates}
                                    />
                                )
                            }
                        </div>
                    )}

                    {/* ── DATABASE / TSB / RECALL SEARCH TABS ──────────────── */}
                    {(activeTab === 'database' || activeTab === 'tsbsearch' || activeTab === 'recallsearch') && (
                        <div>
                            {/* Page heading */}
                            <div style={{ marginBottom: '1.5rem' }}>
                                <h1 className="cds--productive-heading-04" style={{ marginBottom: '0.5rem' }}>
                                    {activeTab === 'tsbsearch' ? 'TSB Search' : activeTab === 'recallsearch' ? 'Recall Search' : 'Complaints Database'}
                                </h1>
                                <p className="cds--body-short-01" style={{ color: 'var(--cds-text-secondary)' }}>
                                    {activeTab === 'tsbsearch'
                                        ? 'Search Technical Service Bulletins by keyword and vehicle.'
                                        : activeTab === 'recallsearch'
                                        ? 'Search NHTSA safety recalls by keyword (e.g. "airbag", "fuel pump") and optional vehicle make/year.'
                                        : 'Search NHTSA complaints database for known failure patterns.'}
                                </p>
                            </div>

                            {/* Recall vehicle filter row */}
                            {activeTab === 'recallsearch' && (
                                <div
                                    style={{
                                        background: 'var(--cds-layer-01)',
                                        border: '1px solid var(--cds-border-subtle-01)',
                                        padding: '1.5rem',
                                        marginBottom: '1rem',
                                    }}
                                >
                                    <p className="cds--label" style={{ marginBottom: '0.75rem' }}>
                                        Filter by vehicle (optional)
                                    </p>
                                    <div className="form-row">
                                        {/* RECALL MAKE */}
                                        <div className="cds--form-item">
                                            <label htmlFor="recall-make" className="cds--label">Make</label>
                                            <div className="cds--select">
                                                <select
                                                    id="recall-make"
                                                    aria-label="RECALL MAKE"
                                                    value={recallMake}
                                                    onChange={(e) => setRecallMake(e.target.value)}
                                                    className="cds--select-input"
                                                >
                                                    <option value="">All makes</option>
                                                    {MAKES.map((m) => (
                                                        <option key={m} value={m}>{m}</option>
                                                    ))}
                                                </select>
                                                <svg focusable="false" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" fill="currentColor" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" className="cds--select__arrow"><path d="M8 11L3 6 3.7 5.3 8 9.6 12.3 5.3 13 6z" /></svg>
                                            </div>
                                        </div>

                                        {/* RECALL YEAR */}
                                        <div className="cds--form-item">
                                            <label htmlFor="recall-year" className="cds--label">Year</label>
                                            <div className="cds--select">
                                                <select
                                                    id="recall-year"
                                                    aria-label="RECALL YEAR"
                                                    value={recallYear}
                                                    onChange={(e) => setRecallYear(e.target.value)}
                                                    className="cds--select-input"
                                                >
                                                    <option value="">All years</option>
                                                    {YEARS.map((y) => (
                                                        <option key={y} value={String(y)}>{y}</option>
                                                    ))}
                                                </select>
                                                <svg focusable="false" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" fill="currentColor" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" className="cds--select__arrow"><path d="M8 11L3 6 3.7 5.3 8 9.6 12.3 5.3 13 6z" /></svg>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* TSB vehicle filter row */}
                            {activeTab === 'tsbsearch' && (
                                <div
                                    style={{
                                        background: 'var(--cds-layer-01)',
                                        border: '1px solid var(--cds-border-subtle-01)',
                                        padding: '1.5rem',
                                        marginBottom: '1rem',
                                    }}
                                >
                                    <p className="cds--label" style={{ marginBottom: '0.75rem' }}>
                                        Filter by vehicle (optional)
                                    </p>
                                    <div className="form-row">
                                        {/* TSB MAKE */}
                                        <div className="cds--form-item">
                                            <label htmlFor="tsb-make" className="cds--label">Make</label>
                                            <div className="cds--select">
                                                <select
                                                    id="tsb-make"
                                                    aria-label="TSB MAKE"
                                                    value={tsbMake}
                                                    onChange={(e) => handleTsbMakeChange(e.target.value)}
                                                    className="cds--select-input"
                                                >
                                                    <option value="">All makes</option>
                                                    {MAKES.map((m) => (
                                                        <option key={m} value={m}>{m}</option>
                                                    ))}
                                                </select>
                                                <svg focusable="false" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" fill="currentColor" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" className="cds--select__arrow"><path d="M8 11L3 6 3.7 5.3 8 9.6 12.3 5.3 13 6z" /></svg>
                                            </div>
                                        </div>

                                        {/* TSB MODEL */}
                                        <div className="cds--form-item">
                                            <label htmlFor="tsb-model" className="cds--label">Model</label>
                                            <div className={`cds--select${!tsbMake ? ' cds--select--disabled' : ''}`}>
                                                <select
                                                    id="tsb-model"
                                                    aria-label="TSB MODEL"
                                                    value={tsbModel}
                                                    disabled={!tsbMake}
                                                    onChange={(e) => handleTsbModelChange(e.target.value)}
                                                    className="cds--select-input"
                                                >
                                                    <option value="">{tsbMake ? 'All models' : 'Select make first'}</option>
                                                    {tsbMake && getModelsForMake(tsbMake).map((m: string) => (
                                                        <option key={m} value={m}>{m}</option>
                                                    ))}
                                                </select>
                                                <svg focusable="false" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" fill="currentColor" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" className="cds--select__arrow"><path d="M8 11L3 6 3.7 5.3 8 9.6 12.3 5.3 13 6z" /></svg>
                                            </div>
                                        </div>

                                        {/* TSB YEAR */}
                                        <div className="cds--form-item">
                                            <label htmlFor="tsb-year" className="cds--label">Year</label>
                                            <div className={`cds--select${!tsbModel ? ' cds--select--disabled' : ''}`}>
                                                <select
                                                    id="tsb-year"
                                                    aria-label="TSB YEAR"
                                                    value={tsbYear}
                                                    disabled={!tsbModel}
                                                    onChange={(e) => setTsbYear(e.target.value)}
                                                    className="cds--select-input"
                                                >
                                                    <option value="">{tsbModel ? 'All years' : 'Select model first'}</option>
                                                    {YEARS.map((y) => (
                                                        <option key={y} value={String(y)}>{y}</option>
                                                    ))}
                                                </select>
                                                <svg focusable="false" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" fill="currentColor" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" className="cds--select__arrow"><path d="M8 11L3 6 3.7 5.3 8 9.6 12.3 5.3 13 6z" /></svg>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Search input row */}
                            <div
                                style={{
                                    background: 'var(--cds-layer-01)',
                                    border: '1px solid var(--cds-border-subtle-01)',
                                    padding: '1.5rem',
                                    marginBottom: '1.5rem',
                                }}
                            >
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                    <div className="cds--form-item">
                                        <label htmlFor="search-input" className="cds--label">
                                            {activeTab === 'tsbsearch' ? 'Search TSBs' : activeTab === 'recallsearch' ? 'Search recalls' : 'Search complaints'}
                                        </label>
                                        <div className="cds--text-area-wrapper">
                                            <textarea
                                                id="search-input"
                                                rows={3}
                                                value={inputText}
                                                onChange={(e) => setInputText(e.target.value)}
                                                onKeyDown={handleKeyDown}
                                                placeholder={
                                                    activeTab === 'tsbsearch'
                                                        ? 'SEARCH TSBs: e.g. TSB Ford F-150 transmission...'
                                                        : activeTab === 'recallsearch'
                                                        ? 'SEARCH RECALLS: e.g. airbag, fuel pump, steering...'
                                                        : 'ENTER COMMAND OR SYMPTOMS...'
                                                }
                                                className="cds--text-area"
                                                disabled={isProcessing}
                                            />
                                        </div>
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', alignItems: 'center' }}>
                                        {(inputText || messages.length > 0 || lastSearchQuery || tsbMake || recallMake) && (
                                            <button
                                                type="button"
                                                onClick={handleClearSearch}
                                                disabled={isProcessing}
                                                className="cds--btn cds--btn--ghost"
                                                data-testid="clear-search-btn"
                                            >
                                                Clear
                                            </button>
                                        )}
                                        <button
                                            type="button"
                                            onClick={() => handleSearch()}
                                            disabled={isProcessing}
                                            className="cds--btn cds--btn--primary"
                                            style={{ minWidth: '8rem' }}
                                        >
                                            {isProcessing ? (
                                                <>
                                                    <span className="loading-spinner" style={{ marginRight: '0.5rem' }} />
                                                    Searching...
                                                </>
                                            ) : (
                                                'Search'
                                            )}
                                        </button>
                                    </div>
                                </div>

                                {/* Pagination controls */}
                                {searchTotalPages > 1 && (
                                    <div className="pagination-row">
                                        <button
                                            type="button"
                                            onClick={() => handleSearch(searchPage - 1)}
                                            disabled={searchPage <= 1 || isProcessing}
                                            className="cds--btn cds--btn--ghost cds--btn--sm"
                                        >
                                            PREV
                                        </button>
                                        <span>
                                            PAGE <strong>{searchPage}</strong> / {searchTotalPages}
                                        </span>
                                        <button
                                            type="button"
                                            onClick={() => handleSearch(searchPage + 1)}
                                            disabled={searchPage >= searchTotalPages || isProcessing}
                                            className="cds--btn cds--btn--ghost cds--btn--sm"
                                        >
                                            NEXT
                                        </button>
                                    </div>
                                )}
                            </div>

                            {/* Results area */}
                            <div className="message-area">
                                {messages.map((msg, idx) => (
                                    <div key={idx}>
                                        {msg.role === 'user' ? (
                                            <div className="query-bubble">
                                                <div style={{ fontSize: '0.75rem', opacity: 0.8, marginBottom: '0.25rem' }}>
                                                    Query
                                                </div>
                                                {msg.content}
                                            </div>
                                        ) : (
                                            <div className="response-card">
                                                <div style={{
                                                    fontSize: '0.6875rem',
                                                    textTransform: 'uppercase',
                                                    letterSpacing: '0.08em',
                                                    color: '#0f62fe',
                                                    marginBottom: '0.5rem',
                                                    fontFamily: 'inherit',
                                                }}>
                                                    Search Results
                                                </div>
                                                <TypewriterText text={msg.content} speed={15} />
                                            </div>
                                        )}
                                    </div>
                                ))}

                                {isProcessing && <LoadingState />}
                            </div>
                        </div>
                    )}

                    {/* ── PRE-PURCHASE TAB ─────────────────────────────── */}
                    {activeTab === 'prepurchase' && (
                        <div>
                            <div style={{ marginBottom: '1.5rem' }}>
                                <h1 className="cds--productive-heading-04" style={{ marginBottom: '0.5rem' }}>
                                    Pre-Purchase Inspection
                                </h1>
                                <p className="cds--body-short-01" style={{ color: 'var(--cds-text-secondary)' }}>
                                    Select a vehicle and year range to generate a data-driven inspection checklist based on NHTSA complaints, safety recalls, and TSBs.
                                </p>
                            </div>
                            <ChecklistPanel />
                        </div>
                    )}

                </main>
            </div>

            {/* Report Modal — rendered inside root div so it's always in the tree */}
            {selectedVehicle && (
                <ReportModal
                    make={selectedVehicle.make}
                    model={selectedVehicle.model}
                    year={selectedVehicle.year}
                    isOpen={reportModalOpen}
                    onClose={() => setReportModalOpen(false)}
                />
            )}
        </div>
    );
}
