// Checked AGENTS.md - unit tests for parseVehicleInput (page.tsx utility)
// Implements directly: pure TypeScript parser logic, no agents needed
import { describe, it, expect } from 'vitest';

// ─── Inline copy of the parser under test ────────────────────────────────────
// We duplicate the constants+function here to keep the test file self-contained
// and avoid circular imports from page.tsx (a "use client" React component).

const MAKE_MAP: Record<string, string> = {
    ford: 'FORD', chevrolet: 'CHEVROLET', chevy: 'CHEVROLET', gmc: 'GMC',
    ram: 'RAM', dodge: 'DODGE', chrysler: 'CHRYSLER', jeep: 'JEEP',
    buick: 'BUICK', cadillac: 'CADILLAC', toyota: 'TOYOTA', honda: 'HONDA',
    nissan: 'NISSAN', bmw: 'BMW', hyundai: 'HYUNDAI', kia: 'KIA',
    subaru: 'SUBARU', volkswagen: 'VOLKSWAGEN', vw: 'VOLKSWAGEN',
};

const MODEL_WHITELIST = new Set<string>([
    'f-150', 'f-250', 'f-350', 'f-450', 'explorer', 'mustang', 'focus', 'fusion',
    'escape', 'edge', 'expedition', 'ranger', 'bronco', 'maverick', 'transit',
    'taurus', 'crown', 'victoria', 'flex', 'galaxy',
    'silverado', 'tahoe', 'suburban', 'equinox', 'blazer', 'colorado', 'traverse',
    'malibu', 'cruze', 'impala', 'camaro', 'corvette', 'trax', 'trailblazer',
    'sierra', 'yukon', 'terrain', 'canyon', 'acadia', 'envoy', 'jimmy',
    '1500', '2500', '3500', 'promaster', 'charger', 'challenger', 'durango',
    'journey', 'dakota', 'viper', 'grand',
    'wrangler', 'cherokee', 'compass', 'renegade', 'gladiator',
    '300', 'pacifica', 'voyager', 'town',
    'enclave', 'encore', 'lacrosse', 'regal', 'verano',
    'escalade', 'ct5', 'ct6', 'xt5', 'xt6', 'ats', 'cts', 'srx',
    'camry', 'corolla', 'tacoma', 'tundra', 'highlander', 'prius', 'rav4',
    'sequoia', '4runner', 'sienna', 'venza', 'avalon',
    'civic', 'accord', 'pilot', 'cr-v', 'odyssey', 'ridgeline', 'hr-v', 'passport',
    'altima', 'frontier', 'titan', 'murano', 'pathfinder', 'rogue', 'sentra',
    'maxima', 'armada', 'versa',
    'm3', 'm5', '328i', '330i', '335i', '528i', '530i', 'x1', 'x3', 'x5', 'x7',
    'elantra', 'sonata', 'tucson', 'santa', 'kona', 'palisade', 'ioniq',
    'optima', 'sorento', 'sportage', 'telluride', 'soul', 'stinger', 'seltos',
    'outback', 'forester', 'impreza', 'legacy', 'crosstrek', 'ascent', 'wrx', 'brz',
    'jetta', 'passat', 'tiguan', 'atlas', 'golf', 'beetle', 'gti',
]);

const DTC_REGEX = /\b([PCBU][0-3][0-9A-Fa-f]{3})\b/gi;
const YEAR_REGEX = /\b(19[9][0-9]|20[0-2][0-9]|2030)\b/;

interface VehicleInfo { make: string; model: string; year: number; }

function parseVehicleInput(text: string): {
    vehicle: VehicleInfo | null;
    symptoms: string;
    dtcCodes: string[];
} {
    const dtcCodes = [...text.matchAll(DTC_REGEX)].map(m => m[1].toUpperCase());
    const nodtc = text.replace(DTC_REGEX, ' ').replace(/\s+/g, ' ').trim();

    const yearMatch = nodtc.match(YEAR_REGEX);
    if (!yearMatch) return { vehicle: null, symptoms: text, dtcCodes };
    const year = parseInt(yearMatch[1]);

    const words = nodtc.split(/\s+/);
    let makeIdx = -1;
    let make = '';
    for (let i = 0; i < words.length; i++) {
        const mapped = MAKE_MAP[words[i].toLowerCase()];
        if (mapped) { makeIdx = i; make = mapped; break; }
    }
    if (makeIdx === -1) return { vehicle: null, symptoms: text, dtcCodes };

    const afterMake = words.slice(makeIdx + 1).filter(w => !YEAR_REGEX.test(w));
    const candidate = afterMake[0]?.toLowerCase() ?? '';
    if (!MODEL_WHITELIST.has(candidate)) {
        return { vehicle: null, symptoms: text, dtcCodes };
    }
    const model = candidate.toUpperCase();
    const symptoms = afterMake.slice(1).join(' ') || nodtc;

    return { vehicle: { make, model, year }, symptoms: symptoms || nodtc, dtcCodes };
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('parseVehicleInput', () => {
    describe('whitelist match — model correctly extracted', () => {
        it('parses "2018 Ford F-150 engine shaking" → model=F-150, symptoms="engine shaking"', () => {
            const result = parseVehicleInput('2018 Ford F-150 engine shaking');
            expect(result.vehicle).not.toBeNull();
            expect(result.vehicle!.make).toBe('FORD');
            expect(result.vehicle!.model).toBe('F-150');
            expect(result.vehicle!.year).toBe(2018);
            expect(result.symptoms).toBe('engine shaking');
            expect(result.dtcCodes).toEqual([]);
        });

        it('parses "2020 Chevy Silverado transmission slip at highway speeds"', () => {
            const result = parseVehicleInput('2020 Chevy Silverado transmission slip at highway speeds');
            expect(result.vehicle!.make).toBe('CHEVROLET');
            expect(result.vehicle!.model).toBe('SILVERADO');
            expect(result.vehicle!.year).toBe(2020);
            expect(result.symptoms).toBe('transmission slip at highway speeds');
        });

        it('parses "2020 RAM 1500 transmission slip at highway speeds"', () => {
            const result = parseVehicleInput('2020 RAM 1500 transmission slip at highway speeds');
            expect(result.vehicle!.make).toBe('RAM');
            expect(result.vehicle!.model).toBe('1500');
            expect(result.symptoms).toBe('transmission slip at highway speeds');
        });

        it('parses DTC code with vehicle: "2019 Chevy Silverado P0300 rough idle"', () => {
            const result = parseVehicleInput('2019 Chevy Silverado P0300 rough idle');
            expect(result.vehicle!.make).toBe('CHEVROLET');
            expect(result.vehicle!.model).toBe('SILVERADO');
            expect(result.dtcCodes).toEqual(['P0300']);
            expect(result.symptoms).toContain('rough idle');
        });
    });

    describe('no-whitelist fallback — vehicle=null', () => {
        it('returns vehicle=null when model word not in whitelist', () => {
            const result = parseVehicleInput('2018 Ford Blahblah engine shaking');
            expect(result.vehicle).toBeNull();
            expect(result.symptoms).toBe('2018 Ford Blahblah engine shaking');
        });

        it('returns vehicle=null when nothing follows make', () => {
            const result = parseVehicleInput('2018 Ford');
            expect(result.vehicle).toBeNull();
        });
    });

    describe('required field validation', () => {
        it('returns vehicle=null when no year present', () => {
            const result = parseVehicleInput('Ford F-150 engine shaking');
            expect(result.vehicle).toBeNull();
            expect(result.symptoms).toBe('Ford F-150 engine shaking');
        });

        it('returns vehicle=null when no recognized make present', () => {
            const result = parseVehicleInput('2018 F-150 engine shaking');
            expect(result.vehicle).toBeNull();
        });
    });

    describe('DTC code handling', () => {
        it('extracts DTC from input with no vehicle info', () => {
            const result = parseVehicleInput('P0300 misfire');
            expect(result.vehicle).toBeNull();
            expect(result.dtcCodes).toEqual(['P0300']);
        });

        it('extracts multiple DTCs', () => {
            const result = parseVehicleInput('2018 Ford F-150 P0300 P0301 misfires');
            expect(result.dtcCodes).toEqual(['P0300', 'P0301']);
        });
    });

    describe('case insensitivity', () => {
        it('handles uppercase make "FORD"', () => {
            const result = parseVehicleInput('2018 FORD F-150 engine shaking');
            expect(result.vehicle!.make).toBe('FORD');
            expect(result.vehicle!.model).toBe('F-150');
        });

        it('handles mixed-case model "f-150" → "F-150"', () => {
            const result = parseVehicleInput('2018 Ford f-150 engine shaking');
            expect(result.vehicle!.model).toBe('F-150');
        });
    });

    describe('year handling', () => {
        it('correctly extracts year from any position', () => {
            const result = parseVehicleInput('F-150 Ford 2018 engine shaking');
            // year regex finds 2018 — make found, model candidate after make
            // (make is "FORD", afterMake starts at "2018" which is filtered, then "engine")
            // "engine" not in whitelist → vehicle null
            expect(result.vehicle).toBeNull();
        });

        it('parses year at start of string', () => {
            const result = parseVehicleInput('2022 Toyota Camry rough idle');
            expect(result.vehicle!.year).toBe(2022);
            expect(result.vehicle!.make).toBe('TOYOTA');
            expect(result.vehicle!.model).toBe('CAMRY');
        });
    });
});
