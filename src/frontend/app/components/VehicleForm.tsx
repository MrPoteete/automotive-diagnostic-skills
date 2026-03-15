"use client";

// Checked AGENTS.md - implementing directly, UI component with no security/data concerns.
// Carbon Design System rewrite — preserves all accessibility attributes and test contracts.

import React, { useState, useEffect } from 'react';
import { api } from '../../lib/api';
import type { VehicleInfo, VehicleData } from '../../lib/api';
import { MAKES, getModelsForMake } from '../../lib/vehicles';

interface VehicleFormProps {
    onDiagnose: (vehicle: VehicleInfo, symptoms: string, dtcCodes: string[]) => void;
    isProcessing: boolean;
}

const DTC_CODE_PATTERN = /^[PCBU][0-3][0-9A-F]{3}$/i;

/** Year range 2025 → 1990 (descending — mechanics mostly work on recent vehicles) */
const YEARS: number[] = Array.from({ length: 36 }, (_, i) => 2025 - i);

/** Parse a raw DTC code string (comma/space/semicolon-separated) into validated uppercase codes. */
export function parseDtcInput(raw: string): string[] {
    return raw
        .split(/[\s,;]+/)
        .map((c) => c.trim().toUpperCase())
        .filter((c) => DTC_CODE_PATTERN.test(c));
}

export default function VehicleForm({ onDiagnose, isProcessing }: VehicleFormProps) {
    const [year, setYear] = useState('');
    const [make, setMake] = useState('');
    const [model, setModel] = useState('');
    const [symptoms, setSymptoms] = useState('');
    const [dtcInput, setDtcInput] = useState('');
    const [vehicleData, setVehicleData] = useState<VehicleData | null>(null);
    const [availableYears, setAvailableYears] = useState<number[]>([]);

    // Load dynamic vehicle data from DB on mount; fall back to static data if unavailable
    useEffect(() => {
        api.fetchVehicles().then((data) => { if (data) setVehicleData(data); });
    }, []);

    // Fetch available years whenever both make and model are selected
    useEffect(() => {
        if (make && model) {
            api.fetchVehicleYears(make, model).then((years) => {
                setAvailableYears(years ?? []);
                setYear((prev) => (years && years.includes(Number(prev)) ? prev : ''));
            });
        } else {
            setAvailableYears([]);
        }
    }, [make, model]);

    const activeMakes: string[] = vehicleData?.makes ?? MAKES;
    const getModels = (m: string): string[] => vehicleData?.models_by_make[m] ?? getModelsForMake(m);

    const yearOptions = availableYears.length > 0 ? availableYears : YEARS;
    const modelOptions = make ? getModels(make) : [];
    const canSubmit = Boolean(year && make && model && symptoms.trim() && !isProcessing);

    const handleMakeChange = (newMake: string) => {
        setMake(newMake);
        setModel('');
        setYear('');
    };

    const handleModelChange = (newModel: string) => {
        setModel(newModel);
        setYear('');
    };

    const handleSubmit = () => {
        if (!canSubmit) return;
        onDiagnose(
            { make, model, year: parseInt(year, 10) },
            symptoms.trim(),
            parseDtcInput(dtcInput),
        );
        setSymptoms('');
        setDtcInput('');
    };

    return (
        <div className="w-full">
            {/* Row 1: Make / Model / Year selects */}
            <div className="form-row">
                {/* MAKE */}
                <div className="cds--form-item">
                    <label
                        htmlFor="vf-make"
                        className="cds--label"
                    >
                        Make
                    </label>
                    <div className="cds--select">
                        <select
                            id="vf-make"
                            aria-label="MAKE"
                            value={make}
                            onChange={(e) => handleMakeChange(e.target.value)}
                            className="cds--select-input"
                        >
                            <option value="" disabled>Select make</option>
                            {activeMakes.map((opt) => (
                                <option key={opt} value={opt}>{opt}</option>
                            ))}
                        </select>
                        <svg
                            focusable="false"
                            preserveAspectRatio="xMidYMid meet"
                            xmlns="http://www.w3.org/2000/svg"
                            fill="currentColor"
                            width="16"
                            height="16"
                            viewBox="0 0 16 16"
                            aria-hidden="true"
                            className="cds--select__arrow"
                        >
                            <path d="M8 11L3 6 3.7 5.3 8 9.6 12.3 5.3 13 6z" />
                        </svg>
                    </div>
                </div>

                {/* MODEL */}
                <div className="cds--form-item">
                    <label
                        htmlFor="vf-model"
                        className="cds--label"
                    >
                        Model
                    </label>
                    <div className={`cds--select${!make ? ' cds--select--disabled' : ''}`}>
                        <select
                            id="vf-model"
                            aria-label="MODEL"
                            value={model}
                            disabled={!make}
                            onChange={(e) => handleModelChange(e.target.value)}
                            className="cds--select-input"
                        >
                            <option value="" disabled>
                                {make ? 'Select model' : 'Select make first'}
                            </option>
                            {modelOptions.map((opt) => (
                                <option key={opt} value={opt}>{opt}</option>
                            ))}
                        </select>
                        <svg
                            focusable="false"
                            preserveAspectRatio="xMidYMid meet"
                            xmlns="http://www.w3.org/2000/svg"
                            fill="currentColor"
                            width="16"
                            height="16"
                            viewBox="0 0 16 16"
                            aria-hidden="true"
                            className="cds--select__arrow"
                        >
                            <path d="M8 11L3 6 3.7 5.3 8 9.6 12.3 5.3 13 6z" />
                        </svg>
                    </div>
                </div>

                {/* YEAR */}
                <div className="cds--form-item">
                    <label
                        htmlFor="vf-year"
                        className="cds--label"
                    >
                        Year
                    </label>
                    <div className={`cds--select${(!make || !model) ? ' cds--select--disabled' : ''}`}>
                        <select
                            id="vf-year"
                            aria-label="YEAR"
                            value={year}
                            disabled={!make || !model}
                            onChange={(e) => setYear(e.target.value)}
                            className="cds--select-input"
                        >
                            <option value="" disabled>
                                {make && model ? 'Select year' : 'Select make & model first'}
                            </option>
                            {yearOptions.map((opt) => (
                                <option key={opt} value={String(opt)}>{String(opt)}</option>
                            ))}
                        </select>
                        <svg
                            focusable="false"
                            preserveAspectRatio="xMidYMid meet"
                            xmlns="http://www.w3.org/2000/svg"
                            fill="currentColor"
                            width="16"
                            height="16"
                            viewBox="0 0 16 16"
                            aria-hidden="true"
                            className="cds--select__arrow"
                        >
                            <path d="M8 11L3 6 3.7 5.3 8 9.6 12.3 5.3 13 6z" />
                        </svg>
                    </div>
                </div>
            </div>

            {/* Row 2: Symptoms textarea + DTC codes input */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 200px', gap: '1rem', marginBottom: '1rem' }}>
                {/* Symptoms */}
                <div className="cds--form-item">
                    <label htmlFor="vf-symptoms" className="cds--label">
                        Symptoms / Description
                    </label>
                    <div className="cds--text-area__wrapper">
                        <textarea
                            id="vf-symptoms"
                            value={symptoms}
                            onChange={(e) => setSymptoms(e.target.value)}
                            rows={2}
                            placeholder="e.g. engine shaking at idle, transmission slip, stalls on acceleration..."
                            className="cds--text-area"
                            style={{ resize: 'none' }}
                        />
                    </div>
                </div>

                {/* DTC Codes */}
                <div className="cds--form-item">
                    <label htmlFor="vf-dtc" className="cds--label">
                        DTC Codes{' '}
                        <span style={{ fontWeight: 400, color: 'var(--cds-text-secondary)' }}>
                            (optional)
                        </span>
                    </label>
                    <div className="cds--text-input-wrapper">
                        <input
                            id="vf-dtc"
                            type="text"
                            value={dtcInput}
                            onChange={(e) => setDtcInput(e.target.value)}
                            placeholder="P0300, P0301..."
                            className="cds--text-input"
                        />
                    </div>
                </div>
            </div>

            {/* Row 3: Submit button */}
            <button
                type="button"
                onClick={handleSubmit}
                disabled={!canSubmit}
                className="cds--btn cds--btn--primary"
                style={{ width: '100%', maxWidth: '100%', justifyContent: 'center' }}
            >
                {isProcessing ? (
                    <>
                        <span className="loading-spinner" style={{ marginRight: '0.5rem' }} />
                        ANALYZING...
                    </>
                ) : (
                    'INITIATE DIAGNOSTIC SCAN'
                )}
            </button>
        </div>
    );
}
