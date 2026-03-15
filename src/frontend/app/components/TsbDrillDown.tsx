'use client';
// Checked AGENTS.md - implementing via Gemini delegation per GEMINI_WORKFLOW.md.

import React, { useState, useEffect } from 'react';
import { Button } from '@carbon/react';
import { Close } from '@carbon/icons-react';
import { fetchVehicleTsbs, type VehicleTsbsResponse } from '../../lib/api';

interface TsbDrillDownProps {
    make: string;
    model: string;
    year: number;
    onClose: () => void;
}

function LoadingSkeleton() {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {[...Array(5)].map((_, i) => (
                <div key={i} style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <div style={{ width: '60px', height: '24px', background: 'var(--cds-layer-02)', borderRadius: '12px', animation: 'pulse 1.5s ease-in-out infinite' }} />
                    <div style={{ width: '120px', height: '20px', background: 'var(--cds-layer-02)', borderRadius: '4px', animation: 'pulse 1.5s ease-in-out infinite' }} />
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        <div style={{ height: '1rem', width: '80%', background: 'var(--cds-layer-02)', borderRadius: '4px', animation: 'pulse 1.5s ease-in-out infinite' }} />
                        <div style={{ height: '1rem', width: '60%', background: 'var(--cds-layer-02)', borderRadius: '4px', animation: 'pulse 1.5s ease-in-out infinite' }} />
                    </div>
                </div>
            ))}
        </div>
    );
}

function formatTsbDate(dateStr: string): string {
    if (!dateStr || dateStr.length !== 8) return dateStr ?? '';
    const year = parseInt(dateStr.substring(0, 4), 10);
    const month = parseInt(dateStr.substring(4, 6), 10);
    const date = new Date(year, month - 1, 1);
    return date.toLocaleString('default', { month: 'short', year: 'numeric' });
}

export default function TsbDrillDown({ make, model, year, onClose }: TsbDrillDownProps) {
    const [data, setData] = useState<VehicleTsbsResponse | null>(null);
    const [page, setPage] = useState(1);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        setError(null);
        fetchVehicleTsbs(make, model, year, page).then((result) => {
            if (cancelled) return;
            if (result) {
                setData(result);
            } else {
                setError('Could not load TSBs.');
            }
            setLoading(false);
        });
        return () => { cancelled = true; };
    }, [make, model, year, page]);

    const handlePrev = () => setPage(p => Math.max(1, p - 1));
    const handleNext = () => setPage(p => Math.min(data?.total_pages ?? p, p + 1));

    return (
        <div style={{ background: 'var(--cds-layer-01)', border: '1px solid var(--cds-border-subtle-01)', padding: '1.25rem 1.5rem' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <p style={{ fontSize: '0.75rem', color: 'var(--cds-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', margin: 0 }}>
                    <span style={{ color: 'var(--cds-interactive)', fontWeight: 600 }}>Technical Service Bulletins</span>
                    {' '}— {year} {make.toUpperCase()} {model.toUpperCase()}
                </p>
                <Button
                    kind="ghost"
                    renderIcon={Close}
                    iconDescription="Close TSB drill-down"
                    hasIconOnly
                    onClick={onClose}
                    data-testid="close-tsb-drilldown-btn"
                />
            </div>

            {loading && <LoadingSkeleton />}

            {error && (
                <p style={{ fontSize: '0.75rem', color: 'var(--cds-support-error)', padding: '0.5rem 0' }}>{error}</p>
            )}

            {!loading && !error && data && (
                <>
                    {data.results.length === 0 ? (
                        <p style={{ fontSize: '0.875rem', color: 'var(--cds-text-secondary)', textAlign: 'center', padding: '2rem 0' }}>
                            No TSBs found for this vehicle.
                        </p>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                            {data.results.map((item, index) => (
                                <div
                                    key={item.bulletin_no}
                                    style={{
                                        display: 'flex',
                                        gap: '0.75rem',
                                        padding: '0.75rem 0',
                                        borderTop: index > 0 ? '1px solid var(--cds-border-subtle-01)' : 'none',
                                        alignItems: 'flex-start',
                                    }}
                                >
                                    <span style={{
                                        background: 'var(--cds-layer-02)',
                                        color: 'var(--cds-text-secondary)',
                                        fontSize: '0.75rem',
                                        fontWeight: 600,
                                        padding: '0.25rem 0.5rem',
                                        borderRadius: '2px',
                                        whiteSpace: 'nowrap',
                                        flexShrink: 0,
                                    }}>
                                        {formatTsbDate(item.bulletin_date)}
                                    </span>
                                    <span style={{
                                        background: 'var(--cds-layer-02)',
                                        color: 'var(--cds-text-secondary)',
                                        fontSize: '0.75rem',
                                        padding: '0.125rem 0.375rem',
                                        borderRadius: '2px',
                                        whiteSpace: 'nowrap',
                                        maxWidth: '200px',
                                        overflow: 'hidden',
                                        textOverflow: 'ellipsis',
                                        flexShrink: 0,
                                    }}>
                                        {item.component}
                                    </span>
                                    <p style={{
                                        flex: 1,
                                        fontSize: '0.875rem',
                                        color: 'var(--cds-text-primary)',
                                        lineHeight: 1.4,
                                        margin: 0,
                                        display: '-webkit-box',
                                        WebkitLineClamp: 2,
                                        WebkitBoxOrient: 'vertical',
                                        overflow: 'hidden',
                                    }}>
                                        {item.summary}
                                    </p>
                                </div>
                            ))}
                        </div>
                    )}

                    {data.total_pages > 1 && (
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem', borderTop: '1px solid var(--cds-border-subtle-01)', paddingTop: '1rem' }}>
                            <span style={{ fontSize: '0.75rem', color: 'var(--cds-text-secondary)' }}>
                                Page {data.page} of {data.total_pages} ({data.total_count.toLocaleString()} results)
                            </span>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <Button kind="ghost" size="sm" onClick={handlePrev} disabled={page === 1}>Prev</Button>
                                <Button kind="ghost" size="sm" onClick={handleNext} disabled={page >= data.total_pages}>Next</Button>
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
