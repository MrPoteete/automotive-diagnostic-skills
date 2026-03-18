'use client';

// Checked AGENTS.md - implementing directly; pure UI modal, no safety logic, no auth.
// Mirrors ReportModal pattern — simpler because checklist needs no LLM toggle.

import React, { useState, useEffect, useCallback } from 'react';
import { Select, SelectItem, Button } from '@carbon/react';
import { Close, Checkmark } from '@carbon/icons-react';
import { generateChecklist, type ChecklistRequest, type ChecklistResponse } from '../../lib/api';

interface ChecklistModalProps {
    make: string;
    model: string;
    year: number;
    isOpen: boolean;
    onClose: () => void;
}

const MIN_YEAR = 2005;
const MAX_YEAR = 2025;
const YEAR_OPTIONS = Array.from({ length: MAX_YEAR - MIN_YEAR + 1 }, (_, i) => MIN_YEAR + i);

export default function ChecklistModal({ make, model, year, isOpen, onClose }: ChecklistModalProps) {
    const [yearStart, setYearStart] = useState(Math.max(year - 2, MIN_YEAR));
    const [yearEnd, setYearEnd] = useState(Math.min(year + 2, MAX_YEAR));
    const [isGenerating, setIsGenerating] = useState(false);
    const [checklist, setChecklist] = useState<ChecklistResponse | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (isOpen) {
            setYearStart(Math.max(year - 2, MIN_YEAR));
            setYearEnd(Math.min(year + 2, MAX_YEAR));
            setChecklist(null);
            setError(null);
        }
    }, [isOpen, year]);

    const handleGenerate = useCallback(async () => {
        if (yearStart > yearEnd) {
            setError('Start year must be ≤ end year.');
            return;
        }
        setIsGenerating(true);
        setChecklist(null);
        setError(null);

        const req: ChecklistRequest = { make, model, year_start: yearStart, year_end: yearEnd };

        try {
            const result = await generateChecklist(req);
            setChecklist(result);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Checklist generation failed.');
        } finally {
            setIsGenerating(false);
        }
    }, [make, model, yearStart, yearEnd]);

    const handleDownload = useCallback(() => {
        if (!checklist) return;
        const blob = new Blob([checklist.content], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = checklist.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }, [checklist]);

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
                data-testid="checklist-modal"
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
                        <Checkmark size={20} />
                        <span style={{ fontSize: '1rem', fontWeight: 600, color: '#f4f4f4' }}>
                            Pre-Purchase Checklist — {year} {make} {model}
                        </span>
                    </div>
                    <Button data-testid="close-checklist-modal" kind="ghost" hasIconOnly renderIcon={Close} iconDescription="Close" onClick={onClose} size="sm" />
                </div>

                {/* Scrollable body */}
                <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

                    {/* Year range */}
                    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                        <div style={{ flex: '1 1 140px' }}>
                            <Select
                                id="checklist-year-start"
                                labelText="Year Range — Start"
                                value={String(yearStart)}
                                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setYearStart(Number(e.target.value))}
                            >
                                {YEAR_OPTIONS.map((y) => <SelectItem key={y} value={String(y)} text={String(y)} />)}
                            </Select>
                        </div>
                        <div style={{ flex: '1 1 140px' }}>
                            <Select
                                id="checklist-year-end"
                                labelText="Year Range — End"
                                value={String(yearEnd)}
                                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setYearEnd(Number(e.target.value))}
                            >
                                {YEAR_OPTIONS.map((y) => <SelectItem key={y} value={String(y)} text={String(y)} />)}
                            </Select>
                        </div>
                    </div>

                    {/* Generate button */}
                    <Button
                        kind="primary"
                        onClick={handleGenerate}
                        disabled={isGenerating}
                        style={{ width: '100%' }}
                    >
                        {isGenerating ? '⏳ Generating checklist...' : 'Generate Checklist'}
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

                    {/* Checklist output */}
                    {checklist && (
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
                                    {checklist.content}
                                </pre>
                            </div>
                            <Button kind="ghost" onClick={handleDownload} renderIcon={Checkmark} iconDescription="Download">
                                Download {checklist.filename}
                            </Button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
