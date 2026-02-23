"use client";

// Checked AGENTS.md - implementing directly, UI component with no security/data concerns.
// Gemini generated vehicles.ts data module; VehicleForm uses Claude for UI/state logic.
// Dynamic vehicle loading added: fetchVehicles() on mount, static fallback on error.

import React, { useState, useEffect } from 'react';
import { Zap, ChevronDown } from 'lucide-react';
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

function CyberSelect({
    label,
    value,
    onChange,
    options,
    disabled = false,
    placeholder,
}: {
    label: string;
    value: string;
    onChange: (v: string) => void;
    options: (string | number)[];
    disabled?: boolean;
    placeholder: string;
}) {
    return (
        <div className="flex flex-col gap-1">
            <label className="font-mono text-xs text-cyber-gray tracking-widest uppercase">{label}</label>
            <div className="relative">
                <select
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    disabled={disabled}
                    aria-label={label}
                    className="cyber-select w-full appearance-none bg-black/80 border border-cyber-gray/30 text-cyber-white font-mono text-sm px-3 py-2 pr-8 focus:outline-none focus:border-cyber-blue focus:ring-1 focus:ring-cyber-blue/50 hover:border-cyber-blue/50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                    <option value="" disabled>{placeholder}</option>
                    {options.map((opt) => (
                        <option key={opt} value={String(opt)}>{String(opt)}</option>
                    ))}
                </select>
                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-cyber-blue pointer-events-none" />
            </div>
        </div>
    );
}

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

    // Load dynamic vehicle data from DB on mount; fall back to static data if unavailable
    useEffect(() => {
        api.fetchVehicles().then((data) => { if (data) setVehicleData(data); });
    }, []);

    const activeMakes: string[] = vehicleData?.makes ?? MAKES;
    const getModels = (m: string): string[] => vehicleData?.models_by_make[m] ?? getModelsForMake(m);

    const modelOptions = make ? getModels(make) : [];
    const canSubmit = Boolean(year && make && model && symptoms.trim() && !isProcessing);

    const handleMakeChange = (newMake: string) => {
        setMake(newMake);
        setModel(''); // reset model when make changes — prevents cross-make invalid combos
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
        <div className="w-full space-y-3">
            {/* Row 1: Year / Make / Model */}
            <div className="grid grid-cols-3 gap-3">
                <CyberSelect
                    label="YEAR"
                    value={year}
                    onChange={setYear}
                    options={YEARS}
                    placeholder="-- SELECT --"
                />
                <CyberSelect
                    label="MAKE"
                    value={make}
                    onChange={handleMakeChange}
                    options={activeMakes}
                    placeholder="-- SELECT --"
                />
                <CyberSelect
                    label="MODEL"
                    value={model}
                    onChange={setModel}
                    options={modelOptions}
                    disabled={!make}
                    placeholder={make ? '-- SELECT --' : '-- SELECT MAKE FIRST --'}
                />
            </div>

            {/* Row 2: Symptoms + DTC Codes */}
            <div className="flex gap-3">
                <div className="flex-1 flex flex-col gap-1">
                    <label className="font-mono text-xs text-cyber-gray tracking-widest uppercase">
                        SYMPTOMS / DESCRIPTION
                    </label>
                    <div className="relative group">
                        <div className="absolute -inset-0.5 bg-gradient-to-r from-cyber-blue via-cyber-pink to-cyber-blue rounded opacity-0 group-focus-within:opacity-30 transition duration-500" />
                        <textarea
                            value={symptoms}
                            onChange={(e) => setSymptoms(e.target.value)}
                            rows={2}
                            placeholder="e.g. engine shaking at idle, transmission slip, stalls on acceleration..."
                            className="relative w-full bg-black/80 border border-cyber-gray/30 text-cyber-white font-mono text-sm px-3 py-2 focus:outline-none focus:border-cyber-blue focus:ring-1 focus:ring-cyber-blue/50 hover:border-cyber-blue/50 transition-colors placeholder-cyber-gray/50 resize-none"
                        />
                    </div>
                </div>

                <div className="w-44 flex flex-col gap-1">
                    <label className="font-mono text-xs text-cyber-gray tracking-widest uppercase">
                        DTC CODES{' '}
                        <span className="normal-case text-cyber-gray/50 tracking-normal">(optional)</span>
                    </label>
                    <input
                        type="text"
                        value={dtcInput}
                        onChange={(e) => setDtcInput(e.target.value)}
                        placeholder="P0300, P0301..."
                        className="h-full bg-black/80 border border-cyber-gray/30 text-cyber-white font-mono text-sm px-3 py-2 focus:outline-none focus:border-cyber-blue focus:ring-1 focus:ring-cyber-blue/50 hover:border-cyber-blue/50 transition-colors placeholder-cyber-gray/50"
                    />
                </div>
            </div>

            {/* Row 3: Submit */}
            <button
                onClick={handleSubmit}
                disabled={!canSubmit}
                className="w-full px-6 py-3 font-bold tracking-widest text-sm uppercase transition-all duration-300 bg-cyber-blue/10 border border-cyber-blue text-cyber-blue hover:bg-cyber-blue hover:text-black hover:shadow-neon-blue disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-cyber-blue/10 disabled:hover:text-cyber-blue disabled:hover:shadow-none font-display flex items-center justify-center gap-2"
            >
                {isProcessing ? (
                    <>
                        <span className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full" />
                        ANALYZING...
                    </>
                ) : (
                    <>
                        <Zap className="h-4 w-4" />
                        INITIATE DIAGNOSTIC SCAN
                    </>
                )}
            </button>
        </div>
    );
}
