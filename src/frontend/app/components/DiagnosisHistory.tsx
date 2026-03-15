'use client';

// Checked AGENTS.md - implementing via Gemini delegation per GEMINI_WORKFLOW.md.
// Read-only display component — fetches and shows prior diagnosis sessions.

import React, { useState, useEffect } from 'react';
import { Tag } from '@carbon/react';
import { ChevronDown, ChevronRight } from '@carbon/icons-react';
import { fetchHistory, type HistoryEntry } from '../../lib/api';

interface DiagnosisHistoryProps {
    make: string;
    model: string;
    year: number;
    vin?: string;
}

function formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function truncate(text: string, max: number): string {
    return text.length > max ? text.slice(0, max - 1) + '…' : text;
}

export default function DiagnosisHistory({ make, model, year, vin }: DiagnosisHistoryProps) {
    const [entries, setEntries] = useState<HistoryEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [panelOpen, setPanelOpen] = useState(false);
    const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        fetchHistory(make, model, year, vin).then((data) => {
            if (cancelled) return;
            setEntries(data?.entries ?? []);
            setLoading(false);
        });
        return () => { cancelled = true; };
    }, [make, model, year, vin]);

    if (loading || entries.length === 0) return null;

    const toggleEntry = (id: number) => {
        setExpandedIds((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    };

    return (
        <div style={{
            background: 'var(--cds-layer-01)',
            border: '1px solid var(--cds-border-subtle-01)',
            marginBottom: '1rem',
        }}>
            {/* Panel header */}
            <button
                type="button"
                onClick={() => setPanelOpen((v) => !v)}
                style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.75rem 1rem',
                    background: 'none',
                    border: 'none',
                    borderBottom: panelOpen ? '1px solid var(--cds-border-subtle-01)' : 'none',
                    cursor: 'pointer',
                    color: 'var(--cds-text-secondary)',
                    fontSize: '0.75rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    textAlign: 'left',
                }}
            >
                {panelOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                Prior Diagnoses ({entries.length})
            </button>

            {/* Entry list */}
            {panelOpen && (
                <div style={{ padding: '0.5rem 0' }}>
                    {entries.map((entry) => {
                        const isExpanded = expandedIds.has(entry.id);
                        return (
                            <div key={entry.id} style={{ borderBottom: '1px solid var(--cds-border-subtle-01)' }}>
                                {/* Entry row header */}
                                <button
                                    type="button"
                                    onClick={() => toggleEntry(entry.id)}
                                    style={{
                                        width: '100%',
                                        display: 'flex',
                                        alignItems: 'flex-start',
                                        gap: '0.75rem',
                                        padding: '0.625rem 1rem',
                                        background: 'none',
                                        border: 'none',
                                        cursor: 'pointer',
                                        color: 'var(--cds-text-primary)',
                                        fontSize: '0.875rem',
                                        textAlign: 'left',
                                    }}
                                >
                                    <span style={{ color: 'var(--cds-text-secondary)', fontSize: '0.75rem', whiteSpace: 'nowrap', paddingTop: '2px' }}>
                                        {formatDate(entry.created_at)}
                                    </span>
                                    <span style={{ flex: 1 }}>
                                        {truncate(entry.symptoms, 80)}
                                    </span>
                                    <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap', alignItems: 'center' }}>
                                        {entry.dtc_codes.map((code) => (
                                            <Tag key={code} type="gray" size="sm">{code}</Tag>
                                        ))}
                                        {entry.has_warnings && (
                                            <Tag type="red" size="sm">⚠ Warnings</Tag>
                                        )}
                                    </div>
                                    {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                                </button>

                                {/* Expanded findings */}
                                {isExpanded && (
                                    <div style={{ padding: '0 1rem 0.75rem 1rem' }}>
                                        <p style={{ fontSize: '0.75rem', color: 'var(--cds-text-secondary)', marginBottom: '0.5rem' }}>
                                            {entry.candidate_count} candidate{entry.candidate_count !== 1 ? 's' : ''}
                                            {entry.engine ? ` · ${entry.engine}` : ''}
                                        </p>
                                        <pre style={{
                                            margin: 0,
                                            padding: '0.75rem',
                                            background: 'var(--cds-layer-02)',
                                            border: '1px solid var(--cds-border-subtle-01)',
                                            fontFamily: "'IBM Plex Mono', monospace",
                                            fontSize: '0.75rem',
                                            lineHeight: 1.5,
                                            whiteSpace: 'pre-wrap',
                                            color: 'var(--cds-text-primary)',
                                        }}>
                                            {entry.findings}
                                        </pre>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
