/** Vehicle data — centralized make/model registry for AUTODIAGNOSYS. Checked AGENTS.md - implementing directly, pure data module. */

/**
 * Raw data for makes and their models, before sorting.
 * Models are stored as uppercase strings.
 */
const MAKE_MODELS_RAW_DATA = {
    FORD: ['F-150', 'F-250', 'F-350', 'F-450', 'EXPLORER', 'MUSTANG', 'FOCUS', 'FUSION', 'ESCAPE', 'EDGE', 'EXPEDITION', 'RANGER', 'BRONCO', 'MAVERICK', 'TRANSIT', 'TAURUS', 'FLEX'],
    CHEVROLET: ['SILVERADO', 'TAHOE', 'SUBURBAN', 'EQUINOX', 'BLAZER', 'COLORADO', 'TRAVERSE', 'MALIBU', 'CRUZE', 'IMPALA', 'CAMARO', 'CORVETTE', 'TRAX', 'TRAILBLAZER'],
    GMC: ['SIERRA', 'YUKON', 'TERRAIN', 'CANYON', 'ACADIA', 'ENVOY'],
    RAM: ['1500', '2500', '3500', 'PROMASTER'],
    DODGE: ['CHARGER', 'CHALLENGER', 'DURANGO', 'JOURNEY', 'DAKOTA', 'VIPER'],
    JEEP: ['WRANGLER', 'CHEROKEE', 'COMPASS', 'RENEGADE', 'GLADIATOR'],
    CHRYSLER: ['300', 'PACIFICA', 'VOYAGER'],
    BUICK: ['ENCLAVE', 'ENCORE', 'LACROSSE', 'REGAL', 'VERANO'],
    CADILLAC: ['ESCALADE', 'CT5', 'CT6', 'XT5', 'XT6', 'ATS', 'CTS', 'SRX'],
    TOYOTA: ['CAMRY', 'COROLLA', 'TACOMA', 'TUNDRA', 'HIGHLANDER', 'PRIUS', 'RAV4', 'SEQUOIA', '4RUNNER', 'SIENNA', 'VENZA', 'AVALON'],
    HONDA: ['CIVIC', 'ACCORD', 'PILOT', 'CR-V', 'ODYSSEY', 'RIDGELINE', 'HR-V', 'PASSPORT'],
    NISSAN: ['ALTIMA', 'FRONTIER', 'TITAN', 'MURANO', 'PATHFINDER', 'ROGUE', 'SENTRA', 'MAXIMA', 'ARMADA', 'VERSA'],
    BMW: ['M3', 'M5', '328I', '330I', '335I', '528I', '530I', 'X1', 'X3', 'X5', 'X7'],
    HYUNDAI: ['ELANTRA', 'SONATA', 'TUCSON', 'SANTA FE', 'KONA', 'PALISADE', 'IONIQ'],
    KIA: ['OPTIMA', 'SORENTO', 'SPORTAGE', 'TELLURIDE', 'SOUL', 'STINGER', 'SELTOS'],
    SUBARU: ['OUTBACK', 'FORESTER', 'IMPREZA', 'LEGACY', 'CROSSTREK', 'ASCENT', 'WRX', 'BRZ'],
    VOLKSWAGEN: ['JETTA', 'PASSAT', 'TIGUAN', 'ATLAS', 'GOLF', 'BEETLE', 'GTI'],
};

/**
 * A record mapping NHTSA uppercase make names to a sorted array of their model names (uppercase).
 * @example
 * MAKE_MODELS.FORD // ['BRONCO', 'EDGE', 'ESCAPE', ...]
 */
export const MAKE_MODELS: Record<string, string[]> = {};
for (const make in MAKE_MODELS_RAW_DATA) {
    if (Object.prototype.hasOwnProperty.call(MAKE_MODELS_RAW_DATA, make)) {
        MAKE_MODELS[make] = [...MAKE_MODELS_RAW_DATA[make as keyof typeof MAKE_MODELS_RAW_DATA]].sort();
    }
}

/**
 * An array of all supported NHTSA uppercase make names, sorted alphabetically.
 * @example
 * MAKES // ['BMW', 'BUICK', 'CADILLAC', ...]
 */
export const MAKES: string[] = Object.keys(MAKE_MODELS).sort();

/**
 * A record mapping lowercase aliases to their official NHTSA uppercase make names.
 * Useful for normalizing user input from free-text fallback.
 * @example
 * MAKE_MAP.chevy // 'CHEVROLET'
 */
export const MAKE_MAP: Record<string, string> = {
    ford: 'FORD',
    chevrolet: 'CHEVROLET',
    chevy: 'CHEVROLET',
    gmc: 'GMC',
    ram: 'RAM',
    dodge: 'DODGE',
    chrysler: 'CHRYSLER',
    jeep: 'JEEP',
    buick: 'BUICK',
    cadillac: 'CADILLAC',
    toyota: 'TOYOTA',
    honda: 'HONDA',
    nissan: 'NISSAN',
    bmw: 'BMW',
    hyundai: 'HYUNDAI',
    kia: 'KIA',
    subaru: 'SUBARU',
    volkswagen: 'VOLKSWAGEN',
    vw: 'VOLKSWAGEN',
};

/**
 * Retrieves a sorted list of models for a given make.
 * @param make - NHTSA uppercase make name (e.g. 'FORD')
 * @returns Sorted array of uppercase model names, or [] if make not found.
 */
export function getModelsForMake(make: string): string[] {
    return MAKE_MODELS[make] ?? [];
}
