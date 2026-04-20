'use client';

// Checked AGENTS.md - implementing via Gemini delegation per GEMINI_WORKFLOW.md.
// Two-path vehicle identification: VIN decode OR manual year/make/model.
// No safety logic, no auth — pure UI component.

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { TextInput, Button, Tag, InlineNotification, Select, SelectItem } from '@carbon/react';
import { Search, Checkmark } from '@carbon/icons-react';

import { fetchVin, api, type VinDecodeResult } from '../../lib/api';
import { MAKES, getModelsForMake } from '../../lib/vehicles';

export interface VehicleIdentity {
    vin?: string;
    year: number;
    make: string;
    model: string;
    engine?: string;
    engine_model?: string;
    transmission_model?: string;
    drive_type?: string;
}

interface VehicleIdentificationProps {
    onVehicleSelected: (vehicle: VehicleIdentity) => void;
    isProcessing?: boolean;
}

const LOCAL_STORAGE_KEY = 'recent_vehicles';
const MAX_RECENT = 10;
const STATIC_YEARS: number[] = Array.from({ length: 36 }, (_, i) => 2025 - i);

function saveRecent(vehicle: VehicleIdentity): void {
    try {
        const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
        const existing: VehicleIdentity[] = raw ? (JSON.parse(raw) as VehicleIdentity[]) : [];
        const deduped = vehicle.vin
            ? existing.filter((v) => v.vin !== vehicle.vin)
            : existing.filter(
                  (v) => !(v.year === vehicle.year && v.make === vehicle.make && v.model === vehicle.model)
              );
        localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify([vehicle, ...deduped].slice(0, MAX_RECENT)));
    } catch {
        // localStorage unavailable — ignore
    }
}

export default function VehicleIdentification({ onVehicleSelected, isProcessing = false }: VehicleIdentificationProps) {
    // VIN path
    const [vinInput, setVinInput] = useState('');
    const [vinResult, setVinResult] = useState<VinDecodeResult | null>(null);
    const [vinError, setVinError] = useState<string | null>(null);
    const [isDecoding, setIsDecoding] = useState(false);

    // Manual path
    const [manualMake, setManualMake] = useState('');
    const [manualModel, setManualModel] = useState('');
    const [manualYear, setManualYear] = useState('');
    const [availableModels, setAvailableModels] = useState<string[]>([]);
    const [availableYears, setAvailableYears] = useState<number[]>([]);
    const [manualError, setManualError] = useState<string | null>(null);

    // Recent vehicles
    const [recentVehicles, setRecentVehicles] = useState<VehicleIdentity[]>([]);

    const yearFetchRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    // Load recent vehicles on mount
    useEffect(() => {
        try {
            const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
            if (raw) setRecentVehicles(JSON.parse(raw) as VehicleIdentity[]);
        } catch {
            // ignore
        }
    }, []);

    // Update models when make changes
    useEffect(() => {
        setAvailableModels(manualMake ? getModelsForMake(manualMake) : []);
        setManualModel('');
        setManualYear('');
        setAvailableYears([]);
    }, [manualMake]);

    // Fetch years when make+model set
    useEffect(() => {
        if (yearFetchRef.current) clearTimeout(yearFetchRef.current);
        if (!manualMake || !manualModel) {
            setAvailableYears([]);
            return;
        }
        yearFetchRef.current = setTimeout(async () => {
            const years = await api.fetchVehicleYears(manualMake, manualModel);
            setAvailableYears(years ?? []);
        }, 300);
        return () => {
            if (yearFetchRef.current) clearTimeout(yearFetchRef.current);
        };
    }, [manualMake, manualModel]);

    const handleVinChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        setVinInput(e.target.value.toUpperCase().slice(0, 17));
        setVinResult(null);
        setVinError(null);
    }, []);

    const handleDecodeVin = useCallback(async () => {
        if (vinInput.length !== 17) {
            setVinError('VIN must be exactly 17 characters.');
            return;
        }
        setIsDecoding(true);
        setVinError(null);
        setVinResult(null);
        const result = await fetchVin(vinInput);
        setIsDecoding(false);
        if (!result) {
            setVinError('Network error — could not reach VIN decoder.');
            return;
        }
        setVinResult(result);
        if (result.valid && result.year && result.make && result.model) {
            const identity: VehicleIdentity = {
                vin: result.vin,
                year: result.year,
                make: result.make,
                model: result.model,
                engine: result.engine,
                engine_model: result.engine_model,
                transmission_model: result.transmission_model,
                drive_type: result.drive_type,
            };
            saveRecent(identity);
            setRecentVehicles((prev) => {
                const deduped = prev.filter((v) => v.vin !== identity.vin);
                return [identity, ...deduped].slice(0, MAX_RECENT);
            });
            onVehicleSelected(identity);
        } else {
            setVinError(result.error ?? 'VIN decode failed.');
        }
    }, [vinInput, onVehicleSelected]);

    const handleManualSelect = useCallback(() => {
        setManualError(null);
        if (!manualYear || !manualMake || !manualModel) {
            setManualError('Please select Year, Make, and Model.');
            return;
        }
        const identity: VehicleIdentity = {
            year: Number(manualYear),
            make: manualMake,
            model: manualModel,
        };
        saveRecent(identity);
        setRecentVehicles((prev) => {
            const deduped = prev.filter(
                (v) => !(v.year === identity.year && v.make === identity.make && v.model === identity.model)
            );
            return [identity, ...deduped].slice(0, MAX_RECENT);
        });
        onVehicleSelected(identity);
    }, [manualYear, manualMake, manualModel, onVehicleSelected]);

    const handleRecentClick = useCallback(
        (vehicle: VehicleIdentity) => {
            // Populate manual fields for visibility
            setManualMake(vehicle.make);
            setManualModel(vehicle.model);
            setManualYear(String(vehicle.year));
            setVinInput(vehicle.vin ?? '');
            setVinResult(null);
            setVinError(null);
            setManualError(null);
            onVehicleSelected(vehicle);
        },
        [onVehicleSelected]
    );

    const yearOptions = availableYears.length > 0 ? availableYears : STATIC_YEARS;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

            {/* ── Path 1: VIN ─────────────────────────────────────── */}
            <section>
                <p style={{ fontSize: '0.75rem', color: '#8d8d8d', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Identify by VIN
                </p>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-end' }}>
                    <div style={{ flex: 1 }}>
                        <TextInput
                            id="vin-input"
                            labelText="VIN (17 characters)"
                            placeholder="e.g. 1C4PJMCB8JD123456"
                            value={vinInput}
                            onChange={handleVinChange}
                            maxLength={17}
                            disabled={isDecoding || isProcessing}
                            invalid={!!vinError}
                            invalidText={vinError ?? ''}
                        />
                    </div>
                    <Button
                        kind="primary"
                        size="md"
                        onClick={handleDecodeVin}
                        disabled={vinInput.length !== 17 || isDecoding || isProcessing}
                        renderIcon={Search}
                        iconDescription="Decode VIN"
                    >
                        {isDecoding ? 'Decoding…' : 'Decode'}
                    </Button>
                </div>

                {vinResult?.valid && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.75rem' }}>
                        {vinResult.year && <Tag type="green">{vinResult.year}</Tag>}
                        {vinResult.make && <Tag type="blue">{vinResult.make}</Tag>}
                        {vinResult.model && <Tag type="purple">{vinResult.model}</Tag>}
                        {vinResult.engine && <Tag type="teal">{vinResult.engine}</Tag>}
                        {vinResult.drive_type && <Tag type="magenta">{vinResult.drive_type}</Tag>}
                        {vinResult.trim && <Tag type="cyan">{vinResult.trim}</Tag>}
                        {vinResult.fuel_type && <Tag type="warm-gray">{vinResult.fuel_type}</Tag>}
                    </div>
                )}

                {vinError && (
                    <div style={{ marginTop: '0.75rem' }}>
                        <InlineNotification
                            kind="error"
                            subtitle={vinError}
                            title="VIN Decode Failed — "
                            lowContrast
                        />
                    </div>
                )}
            </section>

            {/* ── OR Divider ───────────────────────────────────────── */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <div style={{ flex: 1, height: '1px', background: '#393939' }} />
                <span style={{ fontSize: '0.75rem', color: '#6f6f6f', letterSpacing: '0.1em' }}>OR</span>
                <div style={{ flex: 1, height: '1px', background: '#393939' }} />
            </div>

            {/* ── Path 2: Manual ──────────────────────────────────── */}
            <section>
                <p style={{ fontSize: '0.75rem', color: '#8d8d8d', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Manual Entry
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    <Select
                        id="manual-make"
                        labelText="Make"
                        value={manualMake}
                        onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setManualMake(e.target.value)}
                        disabled={isProcessing}
                    >
                        <SelectItem value="" text="Select make" />
                        {MAKES.map((m) => <SelectItem key={m} value={m} text={m} />)}
                    </Select>

                    <Select
                        id="manual-model"
                        labelText="Model"
                        value={manualModel}
                        onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setManualModel(e.target.value)}
                        disabled={!manualMake || isProcessing}
                    >
                        <SelectItem value="" text={manualMake ? 'Select model' : 'Select make first'} />
                        {availableModels.map((m) => <SelectItem key={m} value={m} text={m} />)}
                    </Select>

                    <Select
                        id="manual-year"
                        labelText="Year"
                        value={manualYear}
                        onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setManualYear(e.target.value)}
                        disabled={!manualMake || isProcessing}
                    >
                        <SelectItem value="" text={manualMake ? 'Select year' : 'Select make first'} />
                        {yearOptions.map((y) => <SelectItem key={y} value={String(y)} text={String(y)} />)}
                    </Select>

                    <Button
                        kind="secondary"
                        size="md"
                        onClick={handleManualSelect}
                        disabled={!manualYear || !manualMake || !manualModel || isProcessing}
                        renderIcon={Checkmark}
                        iconDescription="Select vehicle"
                    >
                        Select Vehicle
                    </Button>

                    {manualError && (
                        <InlineNotification
                            kind="error"
                            subtitle={manualError}
                            title="Selection Error — "
                            lowContrast
                        />
                    )}
                </div>
            </section>

            {/* ── Recent Vehicles ──────────────────────────────────── */}
            {recentVehicles.length > 0 && (
                <section>
                    <p style={{ fontSize: '0.75rem', color: '#8d8d8d', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        Recent Vehicles
                    </p>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                        {recentVehicles.map((v, i) => (
                            <button
                                key={i}
                                onClick={() => handleRecentClick(v)}
                                style={{
                                    background: 'none',
                                    border: '1px solid #525252',
                                    borderRadius: '1rem',
                                    padding: '0.25rem 0.75rem',
                                    fontSize: '0.75rem',
                                    color: '#c6c6c6',
                                    cursor: 'pointer',
                                    lineHeight: 1.5,
                                }}
                                type="button"
                            >
                                {v.year} {v.make} {v.model}
                                {v.vin ? ` · ${v.vin.slice(-6)}` : ''}
                            </button>
                        ))}
                    </div>
                </section>
            )}
        </div>
    );
}
