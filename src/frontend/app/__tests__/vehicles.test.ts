// Checked AGENTS.md - implementing directly, pure test file
import { describe, it, expect } from 'vitest';
import { MAKES, MAKE_MODELS, MAKE_MAP, getModelsForMake } from '../../lib/vehicles';

describe('vehicles.ts', () => {
    it('MAKES is sorted alphabetically', () => {
        expect(MAKES).toEqual([...MAKES].sort());
    });

    it('MAKES has exactly 17 entries', () => {
        expect(MAKES).toHaveLength(17);
    });

    it('every make in MAKES has at least one model in MAKE_MODELS', () => {
        MAKES.forEach(make => {
            expect(MAKE_MODELS[make], `Models for "${make}" should be defined`).toBeDefined();
            expect(MAKE_MODELS[make].length, `Models for "${make}" should not be empty`).toBeGreaterThan(0);
        });
    });

    it('all models in MAKE_MODELS are non-empty strings', () => {
        for (const make in MAKE_MODELS) {
            MAKE_MODELS[make].forEach(model => {
                expect(typeof model).toBe('string');
                expect(model.length).toBeGreaterThan(0);
            });
        }
    });

    it('MAKE_MAP.chevy returns CHEVROLET', () => {
        expect(MAKE_MAP['chevy']).toBe('CHEVROLET');
    });

    it('MAKE_MAP.vw returns VOLKSWAGEN', () => {
        expect(MAKE_MAP['vw']).toBe('VOLKSWAGEN');
    });

    it('getModelsForMake("FORD") includes F-150 and EXPLORER', () => {
        const fordModels = getModelsForMake('FORD');
        expect(fordModels).toContain('F-150');
        expect(fordModels).toContain('EXPLORER');
    });

    it('getModelsForMake("UNKNOWN") returns []', () => {
        expect(getModelsForMake('UNKNOWN')).toEqual([]);
    });

    it('FORD models are sorted', () => {
        const fordModels = MAKE_MODELS['FORD'];
        expect(fordModels).toEqual([...fordModels].sort());
    });
});
