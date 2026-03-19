'use client';

// Checked AGENTS.md - implementing directly; pure UI display component, no safety logic, no auth.
// Full-page pre-purchase checklist panel — Carbon-rendered, with PDF download.

import React, { useState, useCallback } from 'react';
import { Select, SelectItem, Button, Tag, Checkbox } from '@carbon/react';
import { Checkmark, Download, DocumentPdf, Warning } from '@carbon/icons-react';
import {
    generateChecklist,
    type ChecklistResponse,
    type ChecklistRecall,
    type ChecklistSection,
    type ChecklistTsb,
} from '../../lib/api';
import { MAKES, YEARS, getModelsForMake } from '../../lib/vehicles';

// ---------------------------------------------------------------------------
// Year range helpers
// ---------------------------------------------------------------------------

const MIN_YEAR = 2005;
const MAX_YEAR = 2025;
const YEAR_OPTIONS = YEARS.filter((y) => y >= MIN_YEAR && y <= MAX_YEAR);

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function RecallsSection({ recalls, hasParkIt }: { recalls: ChecklistRecall[]; hasParkIt: boolean }) {
    if (recalls.length === 0) {
        return (
            <div
                style={{
                    padding: '0.75rem 1rem',
                    background: 'var(--cds-layer-02)',
                    border: '1px solid var(--cds-border-subtle-01)',
                    fontSize: '0.875rem',
                    color: 'var(--cds-text-secondary)',
                }}
            >
                No open recalls found for this vehicle range — always verify VIN at{' '}
                <strong>nhtsa.gov/recalls</strong>
            </div>
        );
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {hasParkIt && (
                <div
                    data-testid="park-it-banner"
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        padding: '0.75rem 1rem',
                        background: '#fff1f1',
                        border: '2px solid #da1e28',
                        color: '#da1e28',
                        fontWeight: 700,
                        fontSize: '0.875rem',
                    }}
                >
                    <Warning size={20} />
                    <span>DO NOT DRIVE: One or more park-it safety recalls are active. Verify VIN at nhtsa.gov/recalls before purchase.</span>
                </div>
            )}
            <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
                    <thead>
                        <tr style={{ background: 'var(--cds-layer-02)' }}>
                            <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left', fontWeight: 600, borderBottom: '1px solid var(--cds-border-subtle-01)', whiteSpace: 'nowrap' }}>Campaign</th>
                            <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left', fontWeight: 600, borderBottom: '1px solid var(--cds-border-subtle-01)' }}>Component</th>
                            <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left', fontWeight: 600, borderBottom: '1px solid var(--cds-border-subtle-01)', whiteSpace: 'nowrap' }}>Years</th>
                            <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left', fontWeight: 600, borderBottom: '1px solid var(--cds-border-subtle-01)', width: '120px' }}>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {recalls.map((r, i) => {
                            const yf = r.year_from;
                            const yt = r.year_to;
                            const affected = yf === yt ? String(yf) : yf && yt ? `${yf}–${yt}` : 'Varies';
                            return (
                                <tr
                                    key={`${r.campaign_no}-${i}`}
                                    style={{
                                        background: r.park_it ? '#fff1f1' : i % 2 === 1 ? 'var(--cds-layer-02)' : 'transparent',
                                        borderBottom: '1px solid var(--cds-border-subtle-01)',
                                    }}
                                >
                                    <td style={{ padding: '0.5rem 0.75rem', whiteSpace: 'nowrap' }}>
                                        {r.campaign_no}
                                        {r.park_it && (
                                            <Tag type="red" size="sm" style={{ marginLeft: '0.5rem' }}>DO NOT DRIVE</Tag>
                                        )}
                                    </td>
                                    <td style={{ padding: '0.5rem 0.75rem' }}>{r.component}</td>
                                    <td style={{ padding: '0.5rem 0.75rem', whiteSpace: 'nowrap' }}>{affected}</td>
                                    <td style={{ padding: '0.5rem 0.75rem' }}>
                                        <Checkbox id={`recall-${r.campaign_no}-${i}`} labelText="Verified" hideLabel={false} />
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function InspectionSection({ section, index }: { section: ChecklistSection; index: number }) {
    return (
        <div
            style={{
                background: 'var(--cds-layer-01)',
                border: '1px solid var(--cds-border-subtle-01)',
                padding: '1rem 1.25rem',
            }}
        >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
                <span
                    style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: '1.5rem',
                        height: '1.5rem',
                        background: '#0f62fe',
                        color: '#fff',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        flexShrink: 0,
                    }}
                >
                    {index}
                </span>
                <span style={{ fontWeight: 600, fontSize: '0.9375rem', color: 'var(--cds-text-primary)' }}>
                    {section.component.charAt(0) + section.component.slice(1).toLowerCase()}
                </span>
                <Tag type="warm-gray" size="sm" style={{ marginLeft: 'auto' }}>
                    {section.complaint_count.toLocaleString()} complaints
                </Tag>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', paddingLeft: '2.25rem' }}>
                {section.checks.map((check, ci) => (
                    <Checkbox
                        key={ci}
                        id={`check-${index}-${ci}`}
                        labelText={check}
                    />
                ))}
            </div>
        </div>
    );
}

function TsbsSection({ tsbs }: { tsbs: ChecklistTsb[] }) {
    if (tsbs.length === 0) {
        return (
            <p style={{ fontSize: '0.875rem', color: 'var(--cds-text-secondary)' }}>
                No specific TSBs found for this model year.
            </p>
        );
    }
    return (
        <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
                <thead>
                    <tr style={{ background: 'var(--cds-layer-02)' }}>
                        <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left', fontWeight: 600, borderBottom: '1px solid var(--cds-border-subtle-01)', whiteSpace: 'nowrap' }}>Bulletin</th>
                        <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left', fontWeight: 600, borderBottom: '1px solid var(--cds-border-subtle-01)' }}>Component</th>
                        <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left', fontWeight: 600, borderBottom: '1px solid var(--cds-border-subtle-01)' }}>Known Issue</th>
                    </tr>
                </thead>
                <tbody>
                    {tsbs.map((t, i) => (
                        <tr
                            key={t.bulletin_no}
                            style={{
                                background: i % 2 === 1 ? 'var(--cds-layer-02)' : 'transparent',
                                borderBottom: '1px solid var(--cds-border-subtle-01)',
                            }}
                        >
                            <td style={{ padding: '0.5rem 0.75rem', whiteSpace: 'nowrap', fontFamily: 'monospace', fontSize: '0.75rem' }}>{t.bulletin_no}</td>
                            <td style={{ padding: '0.5rem 0.75rem' }}>{t.component}</td>
                            <td style={{ padding: '0.5rem 0.75rem', color: 'var(--cds-text-secondary)' }}>{t.summary.length > 100 ? t.summary.slice(0, 100) + '…' : t.summary}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function StandardChecks({ checks }: { checks: string[] }) {
    return (
        <div
            style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                gap: '0.5rem 2rem',
            }}
        >
            {checks.map((check, i) => (
                <Checkbox key={i} id={`std-check-${i}`} labelText={check} />
            ))}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Section header
// ---------------------------------------------------------------------------

function SectionHeader({ children }: { children: React.ReactNode }) {
    return (
        <div
            style={{
                fontSize: '0.75rem',
                fontWeight: 700,
                textTransform: 'uppercase' as const,
                letterSpacing: '0.06em',
                color: '#0f62fe',
                borderBottom: '1px solid var(--cds-border-subtle-01)',
                paddingBottom: '0.5rem',
                marginBottom: '0.75rem',
            }}
        >
            {children}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Rendered checklist (after generation)
// ---------------------------------------------------------------------------

function RenderedChecklist({
    result,
    onDownloadMd,
    onDownloadPdf,
    isPdfLoading,
}: {
    result: ChecklistResponse;
    onDownloadMd: () => void;
    onDownloadPdf: () => void;
    isPdfLoading: boolean;
}) {
    const { data } = result;
    const yearRange = data.year_start === data.year_end
        ? String(data.year_start)
        : `${data.year_start}–${data.year_end}`;

    return (
        <div data-testid="checklist-rendered" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

            {/* Metadata bar */}
            <div
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1rem',
                    padding: '0.75rem 1rem',
                    background: 'var(--cds-layer-02)',
                    border: '1px solid var(--cds-border-subtle-01)',
                    borderLeft: '3px solid #0f62fe',
                    flexWrap: 'wrap',
                }}
            >
                <Checkmark size={16} style={{ color: '#42be65', flexShrink: 0 }} />
                <span style={{ fontWeight: 600, fontSize: '0.9375rem' }}>
                    {yearRange} {data.make.charAt(0) + data.make.slice(1).toLowerCase()} {data.model.charAt(0) + data.model.slice(1).toLowerCase()}
                </span>
                <span style={{ fontSize: '0.8125rem', color: 'var(--cds-text-secondary)' }}>
                    Generated {data.generated_at}
                </span>
                <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <Button
                        kind="ghost"
                        size="sm"
                        renderIcon={Download}
                        iconDescription="Download Markdown"
                        onClick={onDownloadMd}
                        data-testid="download-md-btn"
                    >
                        Download .md
                    </Button>
                    <Button
                        kind="secondary"
                        size="sm"
                        renderIcon={DocumentPdf}
                        iconDescription="Download PDF"
                        onClick={onDownloadPdf}
                        disabled={isPdfLoading}
                        data-testid="download-pdf-btn"
                    >
                        {isPdfLoading ? 'Generating PDF…' : 'Download PDF'}
                    </Button>
                </div>
            </div>

            {/* Recalls */}
            <div>
                <SectionHeader>⚠️ Active Safety Recalls (Verify Completion)</SectionHeader>
                <RecallsSection recalls={data.recalls} hasParkIt={data.has_park_it} />
            </div>

            {/* Inspection priorities */}
            {data.sections.length > 0 && (
                <div>
                    <SectionHeader>🔍 Top Inspection Priorities — Ranked by Complaint Frequency</SectionHeader>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                        {data.sections.map((section, i) => (
                            <InspectionSection key={section.component} section={section} index={i + 1} />
                        ))}
                    </div>
                </div>
            )}

            {/* TSBs */}
            <div>
                <SectionHeader>📋 Technical Service Bulletins to Probe</SectionHeader>
                <TsbsSection tsbs={data.tsbs} />
            </div>

            {/* Standard checks */}
            <div>
                <SectionHeader>✅ Standard Checks — Every Inspection</SectionHeader>
                <StandardChecks checks={data.standard_checks} />
            </div>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

export default function ChecklistPanel() {
    const [make, setMake] = useState('');
    const [model, setModel] = useState('');
    const [yearStart, setYearStart] = useState<number>(2018);
    const [yearEnd, setYearEnd] = useState<number>(2022);
    const [isGenerating, setIsGenerating] = useState(false);
    const [isPdfLoading, setIsPdfLoading] = useState(false);
    const [result, setResult] = useState<ChecklistResponse | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleMakeChange = useCallback((newMake: string) => {
        setMake(newMake);
        setModel('');
        setResult(null);
        setError(null);
    }, []);

    const handleGenerate = useCallback(async () => {
        if (!make || !model) return;
        if (yearStart > yearEnd) {
            setError('Start year must be ≤ end year.');
            return;
        }
        setIsGenerating(true);
        setResult(null);
        setError(null);
        try {
            const res = await generateChecklist({ make, model, year_start: yearStart, year_end: yearEnd });
            setResult(res);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Checklist generation failed.');
        } finally {
            setIsGenerating(false);
        }
    }, [make, model, yearStart, yearEnd]);

    const handleDownloadMd = useCallback(() => {
        if (!result) return;
        const blob = new Blob([result.content], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = result.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }, [result]);

    const handleDownloadPdf = useCallback(async () => {
        if (!make || !model) return;
        setIsPdfLoading(true);
        try {
            const res = await generateChecklist({
                make,
                model,
                year_start: yearStart,
                year_end: yearEnd,
                generate_pdf: true,
            });
            if (res.pdf_b64 && res.pdf_filename) {
                const bytes = Uint8Array.from(atob(res.pdf_b64), (c) => c.charCodeAt(0));
                const blob = new Blob([bytes], { type: 'application/pdf' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = res.pdf_filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                // Update displayed result with any refreshed data
                setResult(res);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'PDF generation failed.');
        } finally {
            setIsPdfLoading(false);
        }
    }, [make, model, yearStart, yearEnd]);

    const handleClear = useCallback(() => {
        setResult(null);
        setError(null);
    }, []);

    const models = make ? getModelsForMake(make) : [];

    return (
        <div data-testid="checklist-panel" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

            {/* Vehicle + year-range selector */}
            <div
                style={{
                    background: 'var(--cds-layer-01)',
                    border: '1px solid var(--cds-border-subtle-01)',
                    padding: '1.5rem',
                }}
            >
                <p
                    style={{
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        letterSpacing: '0.06em',
                        color: 'var(--cds-text-secondary)',
                        marginBottom: '1rem',
                    }}
                >
                    Vehicle Selection
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'flex-end' }}>
                    {/* Make */}
                    <div style={{ flex: '1 1 140px' }}>
                        <Select
                            id="checklist-panel-make"
                            labelText="Make"
                            value={make}
                            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => handleMakeChange(e.target.value)}
                        >
                            <SelectItem value="" text="Select make" />
                            {MAKES.map((m) => <SelectItem key={m} value={m} text={m} />)}
                        </Select>
                    </div>

                    {/* Model */}
                    <div style={{ flex: '1 1 160px' }}>
                        <Select
                            id="checklist-panel-model"
                            labelText="Model"
                            value={model}
                            disabled={!make}
                            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {
                                setModel(e.target.value);
                                setResult(null);
                                setError(null);
                            }}
                        >
                            <SelectItem value="" text={make ? 'Select model' : 'Select make first'} />
                            {models.map((m: string) => <SelectItem key={m} value={m} text={m} />)}
                        </Select>
                    </div>

                    {/* Year start */}
                    <div style={{ flex: '0 1 110px' }}>
                        <Select
                            id="checklist-panel-year-start"
                            labelText="Year — Start"
                            value={String(yearStart)}
                            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setYearStart(Number(e.target.value))}
                        >
                            {YEAR_OPTIONS.map((y) => <SelectItem key={y} value={String(y)} text={String(y)} />)}
                        </Select>
                    </div>

                    {/* Year end */}
                    <div style={{ flex: '0 1 110px' }}>
                        <Select
                            id="checklist-panel-year-end"
                            labelText="Year — End"
                            value={String(yearEnd)}
                            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setYearEnd(Number(e.target.value))}
                        >
                            {YEAR_OPTIONS.map((y) => <SelectItem key={y} value={String(y)} text={String(y)} />)}
                        </Select>
                    </div>

                    {/* Generate button */}
                    <div style={{ flex: '0 0 auto', alignSelf: 'flex-end' }}>
                        <Button
                            kind="primary"
                            onClick={handleGenerate}
                            disabled={!make || !model || isGenerating}
                            renderIcon={Checkmark}
                            iconDescription="Generate checklist"
                            data-testid="generate-checklist-btn"
                        >
                            {isGenerating ? 'Generating…' : 'Generate Checklist'}
                        </Button>
                    </div>

                    {result && (
                        <div style={{ flex: '0 0 auto', alignSelf: 'flex-end' }}>
                            <Button kind="ghost" size="md" onClick={handleClear}>
                                Clear
                            </Button>
                        </div>
                    )}
                </div>
            </div>

            {/* Error */}
            {error && (
                <div
                    style={{
                        padding: '0.75rem 1rem',
                        background: '#2d1b1b',
                        border: '1px solid #fa4d56',
                        color: '#ffb3b8',
                        fontSize: '0.875rem',
                    }}
                >
                    {error}
                </div>
            )}

            {/* Loading */}
            {isGenerating && (
                <div
                    style={{
                        padding: '2rem',
                        textAlign: 'center',
                        color: 'var(--cds-text-secondary)',
                        fontSize: '0.875rem',
                        background: 'var(--cds-layer-01)',
                        border: '1px solid var(--cds-border-subtle-01)',
                    }}
                    data-testid="checklist-loading"
                >
                    <span className="loading-spinner" style={{ marginRight: '0.5rem' }} />
                    Building checklist from NHTSA complaint, recall, and TSB data…
                </div>
            )}

            {/* Rendered result */}
            {result && !isGenerating && (
                <RenderedChecklist
                    result={result}
                    onDownloadMd={handleDownloadMd}
                    onDownloadPdf={handleDownloadPdf}
                    isPdfLoading={isPdfLoading}
                />
            )}
        </div>
    );
}
