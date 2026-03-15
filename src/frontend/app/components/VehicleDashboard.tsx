'use client';

// Checked AGENTS.md - implementing via Gemini delegation per GEMINI_WORKFLOW.md.
// Read-only display component — no safety logic, no auth.

import React, { useState, useEffect } from 'react';
import { Button } from '@carbon/react';
import { Document } from '@carbon/icons-react';
import { fetchDashboard, type DashboardData } from '../../lib/api';

interface VehicleDashboardProps {
    make: string;
    model: string;
    year: number;
    onReportClick: () => void;
}

const TREND_COLOR = {
    increasing: '#fa4d56',
    decreasing: '#42be65',
    stable: '#8d8d8d',
} as const;

const TREND_ARROW = {
    increasing: '↑',
    decreasing: '↓',
    stable: '→',
} as const;

function StatTile({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div
            style={{
                flex: '1 1 180px',
                background: 'var(--cds-layer-01)',
                border: '1px solid var(--cds-border-subtle-01)',
                padding: '1.25rem 1.5rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem',
            }}
        >
            <span style={{ fontSize: '0.75rem', color: 'var(--cds-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                {label}
            </span>
            {children}
        </div>
    );
}

function LoadingSkeleton() {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
                {[0, 1, 2, 3].map((i) => (
                    <div
                        key={i}
                        style={{
                            flex: '1 1 180px',
                            height: '100px',
                            background: 'var(--cds-layer-01)',
                            border: '1px solid var(--cds-border-subtle-01)',
                            animation: 'pulse 1.5s ease-in-out infinite',
                        }}
                    />
                ))}
            </div>
            <div
                style={{
                    height: '160px',
                    background: 'var(--cds-layer-01)',
                    border: '1px solid var(--cds-border-subtle-01)',
                    animation: 'pulse 1.5s ease-in-out infinite',
                }}
            />
        </div>
    );
}

export default function VehicleDashboard({ make, model, year, onReportClick }: VehicleDashboardProps) {
    const [data, setData] = useState<DashboardData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        setError(null);
        setData(null);

        fetchDashboard(make, model, year).then((result) => {
            if (cancelled) return;
            if (result) {
                setData(result);
            } else {
                setError('Could not load vehicle data.');
            }
            setLoading(false);
        });

        return () => { cancelled = true; };
    }, [make, model, year]);

    if (loading) return <LoadingSkeleton />;

    if (error) {
        return (
            <p style={{ fontSize: '0.75rem', color: 'var(--cds-text-secondary)', padding: '0.5rem 0' }}>
                {error}
            </p>
        );
    }

    if (!data) return null;

    const trendColor = TREND_COLOR[data.trend];
    const trendArrow = TREND_ARROW[data.trend];
    const diff = data.trend_current_year_count - data.trend_prior_year_count;
    const diffLabel = diff === 0 ? 'Stable' : `${diff > 0 ? '+' : ''}${diff.toLocaleString()} vs prior year`;
    const maxCount = data.top_components[0]?.count || 1;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>

            {/* ── Stat Tiles ────────────────────────────────────────── */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>

                <StatTile label="Complaints">
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
                        <span style={{ fontSize: '2rem', fontWeight: 600, color: 'var(--cds-text-primary)', lineHeight: 1 }}>
                            {data.complaint_count.toLocaleString()}
                        </span>
                        <span style={{ fontSize: '1.25rem', color: trendColor }}>{trendArrow}</span>
                    </div>
                </StatTile>

                <StatTile label="TSBs">
                    <span style={{ fontSize: '2rem', fontWeight: 600, color: 'var(--cds-text-primary)', lineHeight: 1 }}>
                        {data.tsb_count.toLocaleString()}
                    </span>
                </StatTile>

                <StatTile label="Year-over-Year Trend">
                    <span style={{ fontSize: '1.25rem', fontWeight: 600, color: trendColor, lineHeight: 1.2 }}>
                        {trendArrow} {diffLabel}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--cds-text-secondary)' }}>
                        {data.trend_current_year_count.toLocaleString()} this year · {data.trend_prior_year_count.toLocaleString()} prior
                    </span>
                </StatTile>

                <StatTile label="Report">
                    <Button
                        kind="tertiary"
                        size="sm"
                        renderIcon={Document}
                        iconDescription="Generate report"
                        onClick={onReportClick}
                    >
                        Generate Report
                    </Button>
                </StatTile>

            </div>

            {/* ── Top Components Bar ────────────────────────────────── */}
            {data.top_components.length > 0 && (
                <div
                    style={{
                        background: 'var(--cds-layer-01)',
                        border: '1px solid var(--cds-border-subtle-01)',
                        padding: '1.25rem 1.5rem',
                    }}
                >
                    <p style={{ fontSize: '0.75rem', color: 'var(--cds-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1rem' }}>
                        Top Reported Components
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                        {data.top_components.map((item) => (
                            <div key={item.component} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                <span style={{
                                    fontSize: '0.75rem',
                                    color: 'var(--cds-text-primary)',
                                    minWidth: '180px',
                                    whiteSpace: 'nowrap',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                }}>
                                    {item.component}
                                </span>
                                <div style={{ flex: 1, height: '8px', background: 'var(--cds-layer-02)', borderRadius: '2px', overflow: 'hidden' }}>
                                    <div style={{
                                        width: `${(item.count / maxCount) * 100}%`,
                                        height: '100%',
                                        background: '#0f62fe',
                                        borderRadius: '2px',
                                    }} />
                                </div>
                                <span style={{ fontSize: '0.75rem', color: 'var(--cds-text-secondary)', minWidth: '48px', textAlign: 'right' }}>
                                    {item.count.toLocaleString()}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
