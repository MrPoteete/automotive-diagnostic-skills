'use client';
// Checked AGENTS.md - implementing via Gemini delegation per GEMINI_WORKFLOW.md.

import React, { useState, useEffect } from 'react';
import { Button } from '@carbon/react';
import { Close } from '@carbon/icons-react';
import { fetchVehicleRecalls, type VehicleRecallsResponse } from '../../lib/api';

interface RecallDrillDownProps {
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
                    <div style={{ width: '80px', height: '24px', background: 'var(--cds-layer-02)', borderRadius: '12px', animation: 'pulse 1.5s ease-in-out infinite' }} />
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

export default function RecallDrillDown({ make, model, year, onClose }: RecallDrillDownProps) {
    const [data, setData] = useState<VehicleRecallsResponse | null>(null);
    const [page, setPage] = useState(1);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        setError(null);
        fetchVehicleRecalls(make, model, year, page).then((result) => {
            if (cancelled) return;
            if (result) {
                setData(result);
            } else {
                setError('Could not load recalls.');
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
                    <span style={{ color: 'var(--cds-support-error)', fontWeight: 600 }}>Safety Recalls</span>
                    {' '}— {year} {make.toUpperCase()} {model.toUpperCase()}
                </p>
                <Button
                    kind="ghost"
                    renderIcon={Close}
                    iconDescription="Close recall drill-down"
                    hasIconOnly
                    onClick={onClose}
                    data-testid="close-recall-drilldown-btn"
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
                            No safety recalls found for this vehicle.
                        </p>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                            {data.results.map((item, index) => (
                                <div
                                    key={item.campaign_no}
                                    style={{
                                        display: 'flex',
                                        gap: '0.75rem',
                                        padding: '0.75rem 0',
                                        borderTop: index > 0 ? '1px solid var(--cds-border-subtle-01)' : 'none',
                                        alignItems: 'flex-start',
                                    }}
                                >
                                    {/* Campaign number badge — red if park_it, neutral otherwise */}
                                    <span style={{
                                        background: item.park_it ? 'var(--cds-support-error)' : 'var(--cds-layer-02)',
                                        color: item.park_it ? '#ffffff' : 'var(--cds-text-secondary)',
                                        fontSize: '0.75rem',
                                        fontWeight: 600,
                                        padding: '0.25rem 0.5rem',
                                        borderRadius: '2px',
                                        whiteSpace: 'nowrap',
                                        flexShrink: 0,
                                    }}>
                                        {item.campaign_no}
                                    </span>

                                    {/* Component chip */}
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

                                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
                                        {/* Park-it warning badge */}
                                        {item.park_it && (
                                            <span style={{
                                                display: 'inline-flex',
                                                alignItems: 'center',
                                                gap: '0.25rem',
                                                background: 'var(--cds-support-error)',
                                                color: '#ffffff',
                                                fontSize: '0.6875rem',
                                                fontWeight: 700,
                                                padding: '0.125rem 0.5rem',
                                                borderRadius: '2px',
                                                width: 'fit-content',
                                            }}>
                                                ⚠ Park It
                                            </span>
                                        )}

                                        {/* Summary */}
                                        <p style={{
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

                                        {/* Remedy — truncated at 200 chars */}
                                        {item.remedy && (
                                            <p style={{
                                                fontSize: '0.75rem',
                                                color: 'var(--cds-text-secondary)',
                                                lineHeight: 1.4,
                                                margin: 0,
                                                fontStyle: 'italic',
                                            }}>
                                                <strong style={{ fontStyle: 'normal', color: 'var(--cds-text-primary)' }}>Remedy: </strong>
                                                {item.remedy.length > 200
                                                    ? item.remedy.substring(0, 200) + '…'
                                                    : item.remedy}
                                            </p>
                                        )}
                                    </div>
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
