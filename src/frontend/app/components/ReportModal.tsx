'use client';

// Checked AGENTS.md - implementing via Gemini delegation per GEMINI_WORKFLOW.md.
// Pure UI modal — no safety logic, no auth.

import React, { useState, useEffect, useCallback } from 'react';
import { Select, SelectItem, Toggle, Button } from '@carbon/react';
import { Close, Document } from '@carbon/icons-react';
import { generateReport, type ReportRequest, type ReportResponse } from '../../lib/api';

interface ReportModalProps {
    make: string;
    model: string;
    year: number;
    isOpen: boolean;
    onClose: () => void;
}

const MIN_YEAR = 2005;
const MAX_YEAR = 2025;
const YEAR_OPTIONS = Array.from({ length: MAX_YEAR - MIN_YEAR + 1 }, (_, i) => MIN_YEAR + i);

export default function ReportModal({ make, model, year, isOpen, onClose }: ReportModalProps) {
    const [yearStart, setYearStart] = useState(Math.max(year - 2, MIN_YEAR));
    const [yearEnd, setYearEnd] = useState(Math.min(year + 2, MAX_YEAR));
    const [noLlm, setNoLlm] = useState(true);
    const [isGenerating, setIsGenerating] = useState(false);
    const [report, setReport] = useState<ReportResponse | null>(null);
    const [error, setError] = useState<string | null>(null);

    // Reset state on open
    useEffect(() => {
        if (isOpen) {
            setYearStart(Math.max(year - 2, MIN_YEAR));
            setYearEnd(Math.min(year + 2, MAX_YEAR));
            setNoLlm(true);
            setReport(null);
            setError(null);
        }
    }, [isOpen, year]);

    const handleGenerate = useCallback(async () => {
        if (yearStart > yearEnd) {
            setError('Start year must be ≤ end year.');
            return;
        }
        setIsGenerating(true);
        setReport(null);
        setError(null);

        const req: ReportRequest = {
            make,
            model,
            year_start: yearStart,
            year_end: yearEnd,
            no_llm: noLlm,
            no_api: false,
        };

        try {
            const result = await generateReport(req);
            setReport(result);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Report generation failed.');
        } finally {
            setIsGenerating(false);
        }
    }, [make, model, yearStart, yearEnd, noLlm]);

    const handleDownload = useCallback(() => {
        if (!report) return;
        const blob = new Blob([report.content], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = report.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }, [report]);

    if (!isOpen) return null;

    return (
        <div
            style={{
                position: 'fixed', inset: 0, zIndex: 1000,
                background: 'rgba(0,0,0,0.75)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                padding: '1rem',
            }}
            onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
        >
            <div
                style={{
                    width: '100%', maxWidth: '820px', maxHeight: '88vh',
                    background: '#161616',
                    border: '1px solid #393939',
                    display: 'flex', flexDirection: 'column',
                    overflow: 'hidden',
                }}
            >
                {/* Header */}
                <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '1rem 1.5rem',
                    borderBottom: '1px solid #393939',
                    flexShrink: 0,
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Document size={20} />
                        <span style={{ fontSize: '1rem', fontWeight: 600, color: '#f4f4f4' }}>
                            Generate Report — {year} {make} {model}
                        </span>
                    </div>
                    <Button kind="ghost" hasIconOnly renderIcon={Close} iconDescription="Close" onClick={onClose} size="sm" />
                </div>

                {/* Scrollable body */}
                <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

                    {/* Year range */}
                    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                        <div style={{ flex: '1 1 140px' }}>
                            <Select
                                id="report-year-start"
                                labelText="Year Range — Start"
                                value={String(yearStart)}
                                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setYearStart(Number(e.target.value))}
                            >
                                {YEAR_OPTIONS.map((y) => <SelectItem key={y} value={String(y)} text={String(y)} />)}
                            </Select>
                        </div>
                        <div style={{ flex: '1 1 140px' }}>
                            <Select
                                id="report-year-end"
                                labelText="Year Range — End"
                                value={String(yearEnd)}
                                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setYearEnd(Number(e.target.value))}
                            >
                                {YEAR_OPTIONS.map((y) => <SelectItem key={y} value={String(y)} text={String(y)} />)}
                            </Select>
                        </div>
                    </div>

                    {/* AI toggle */}
                    <Toggle
                        id="report-llm-toggle"
                        labelText="AI Polish"
                        labelA="Fast mode — skip AI polish (~5s)"
                        labelB="AI polish enabled (~60s)"
                        toggled={!noLlm}
                        onToggle={() => setNoLlm((v) => !v)}
                    />

                    {/* Generate button */}
                    <Button
                        kind="primary"
                        onClick={handleGenerate}
                        disabled={isGenerating}
                        style={{ width: '100%' }}
                    >
                        {isGenerating ? '⏳ Generating report...' : 'Generate Report'}
                    </Button>

                    {/* Error */}
                    {error && (
                        <div style={{
                            padding: '0.75rem 1rem',
                            background: '#2d1b1b',
                            border: '1px solid #fa4d56',
                            color: '#ffb3b8',
                            fontSize: '0.875rem',
                        }}>
                            {error}
                        </div>
                    )}

                    {/* Report output */}
                    {report && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                            <div style={{
                                background: '#262626',
                                border: '1px solid #393939',
                                padding: '1.25rem',
                                maxHeight: '400px',
                                overflowY: 'auto',
                            }}>
                                <pre style={{
                                    margin: 0,
                                    whiteSpace: 'pre-wrap',
                                    fontFamily: "'IBM Plex Mono', 'Courier New', monospace",
                                    fontSize: '0.8125rem',
                                    lineHeight: 1.6,
                                    color: '#f4f4f4',
                                }}>
                                    {report.content}
                                </pre>
                            </div>
                            <Button kind="ghost" onClick={handleDownload} renderIcon={Document} iconDescription="Download">
                                Download {report.filename}
                            </Button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
