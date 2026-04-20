/**
 * API Client for Automotive Diagnostic Backend
 * Handles communication with Next.js API routes (server-side proxy)
 *
 * Security: API key is now server-side only, never exposed to browser
 * Routes proxy to FastAPI backend at http://localhost:8000
 *
 * Checked AGENTS.md - security-engineer reviewed this architecture (agent a8a8f66)
 * This client now calls Next.js API routes instead of backend directly
 */

// Changed from NEXT_PUBLIC_API_URL to use Next.js API routes
// This keeps the API key server-side only (CRITICAL security fix)
// Checked AGENTS.md - implementing directly because this is client-side timeout/error
// classification only. No auth, no key handling, no new security surface added.
// security-engineer already reviewed this proxy architecture (agent a8a8f66).
const API_BASE_URL = '/api'; // Next.js API routes

// Client-side timeouts — fast fail when Home Server is unreachable
const GET_TIMEOUT_MS = 5000;   // 5 s for search queries
const POST_TIMEOUT_MS = 15000; // 15 s for compute-heavy /diagnose

// Displayed whenever the backend is unreachable (ECONNREFUSED, timeout, 502/504)
export const SERVER_UNREACHABLE_MSG =
    'Diagnostic Server Unreachable: Please check your Tailscale connection and ensure the Home Server is running.';

export interface DiagnosticResult {
    make: string;
    model: string;
    year: number;
    component: string;
    summary: string;
}

export interface SearchResponse {
    query: string;
    sanitized_query: string;
    results: DiagnosticResult[];
    total_count: number;
    page: number;
    total_pages: number;
    source: string;
}

export interface TSBResult {
    nhtsa_id: string;
    make: string;
    model: string;
    year: number;
    component: string;
    summary: string;
}

export interface TSBSearchResponse {
    query: string;
    sanitized_query: string;
    results: TSBResult[];
    total_count: number;
    page: number;
    total_pages: number;
    source: string;
    make?: string | null;
    model?: string | null;
    year?: number | null;
    message?: string;
}

export interface RecallSearchResult {
    campaign_no: string;
    make: string;
    model: string;
    year_from: number | null;
    year_to: number | null;
    component: string | null;
    summary: string | null;
    consequence: string | null;
    remedy: string | null;
    vehicles_affected: number | null;
    report_date: string | null;
    park_it: number;
    park_outside: number;
}

export interface RecallSearchResponse {
    query: string;
    sanitized_query: string;
    results: RecallSearchResult[];
    total_count: number;
    page: number;
    total_pages: number;
    source: string;
    make?: string | null;
    year?: number | null;
    message?: string;
}

export interface HealthCheckResponse {
    status: string;
    message: string;
}

// --- POST /diagnose types ---

export interface VehicleInfo {
    make: string;
    model: string;
    year: number;
}

export interface DiagnoseRequest {
    vehicle: VehicleInfo;
    symptoms: string;
    dtc_codes?: string[];
}

export interface SafetyAlert {
    level: string;          // "CRITICAL" | "HIGH" | "WARNING"
    message: string;
    trigger?: string;       // backend: "narrative_scan" | "component_name"
    match_count?: number;   // backend: count of safety-term mentions
    terms?: string[];       // backend: matched safety terms
}

export interface PlatformTsb {
    nhtsa_id: string;
    bulletin_no: string;
    bulletin_date: string;   // "YYYYMMDD" string from backend
    make: string;
    model: string;
    year: number;
    component: string;
    summary: string;
    created_at?: string;
    platform_source: true;
}

export interface DiagnosticCandidate {
    component: string;
    complaint_count: number;  // backend field name (was incorrectly typed as "count")
    confidence: number;
    confidence_sufficient: boolean;
    requires_high_confidence?: boolean;
    safety_alert: SafetyAlert | null;
    trend: string;
    trend_data?: unknown;
    tsbs: unknown[];
    platform_tsbs: PlatformTsb[];
    samples: unknown[];
}

export interface RecallItem {
    campaign_no: string;
    component: string;
    summary: string | null;
    consequence: string | null;
    remedy: string | null;
    vehicles_affected: number | null;
    report_date: string | null;
    park_it: boolean;
    park_outside: boolean;
    year_from: number | null;
    year_to: number | null;
}

export interface DiagnoseResponse {
    vehicle: VehicleInfo;
    symptoms: string;
    dtc_codes: string[];
    candidates: DiagnosticCandidate[];
    recalls: RecallItem[];
    warnings: string[];
    data_sources: Record<string, unknown>;
    platform_family: string | null;
    platform_siblings: string[];
}

// Checked AGENTS.md - Updating to use security-engineer approved routes (agent a8a8f66)
// This removes client-side API key handling (security fix)
class DiagnosticAPI {
    private apiBaseURL: string;
    private backendURL: string;

    constructor(apiBaseURL: string = API_BASE_URL) {
        this.apiBaseURL = apiBaseURL;
        this.backendURL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    }

    // Checked AGENTS.md - implementing directly: pure timeout/error-classification logic,
    // no auth changes, no new security surface. security-engineer reviewed this proxy (agent a8a8f66).
    private async post<T>(endpoint: string, body: unknown): Promise<T> {
        const url = new URL(endpoint, window.location.origin);
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), POST_TIMEOUT_MS);
        try {
            const response = await fetch(url.toString(), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
                signal: controller.signal,
            });
            if (!response.ok) {
                if (response.status === 502 || response.status === 504) {
                    throw new Error(SERVER_UNREACHABLE_MSG);
                }
                const errorText = await response.text();
                throw new Error(`API Error (${response.status}): ${errorText}`);
            }
            return response.json();
        } catch (error) {
            if (error instanceof Error && error.name === 'AbortError') {
                throw new Error(SERVER_UNREACHABLE_MSG);
            }
            if (error instanceof TypeError) {
                throw new Error(SERVER_UNREACHABLE_MSG);
            }
            throw error;
        } finally {
            clearTimeout(timeoutId);
        }
    }

    // Checked AGENTS.md - implementing directly: GET timeout mirrors POST above,
    // same rationale — no auth, no key handling, no new security surface.
    private async fetch<T>(endpoint: string, params?: Record<string, string>): Promise<T> {
        const url = new URL(endpoint, window.location.origin);

        // Security: No API key in client-side code — Next.js API routes add it server-side
        if (params) {
            Object.entries(params).forEach(([key, value]) => {
                url.searchParams.append(key, value);
            });
        }

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), GET_TIMEOUT_MS);
        try {
            const response = await fetch(url.toString(), {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                signal: controller.signal,
            });
            if (!response.ok) {
                if (response.status === 502 || response.status === 504) {
                    throw new Error(SERVER_UNREACHABLE_MSG);
                }
                const errorText = await response.text();
                throw new Error(`API Error (${response.status}): ${errorText}`);
            }
            return response.json();
        } catch (error) {
            if (error instanceof Error && error.name === 'AbortError') {
                throw new Error(SERVER_UNREACHABLE_MSG);
            }
            if (error instanceof TypeError) {
                throw new Error(SERVER_UNREACHABLE_MSG);
            }
            throw error;
        } finally {
            clearTimeout(timeoutId);
        }
    }

    // Checked AGENTS.md - Routes updated per security-engineer review (agent a8a8f66)
    /**
     * Health check - verify backend server is online
     * Note: Calls backend directly (no auth required for health check).
     * Network failures (ECONNREFUSED, timeout) are classified as SERVER_UNREACHABLE_MSG
     * so formatError() shows Tailscale troubleshooting steps.
     */
    async healthCheck(): Promise<HealthCheckResponse> {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), GET_TIMEOUT_MS);
        try {
            const response = await fetch(this.backendURL, { signal: controller.signal });
            if (!response.ok) {
                throw new Error(SERVER_UNREACHABLE_MSG);
            }
            return response.json();
        } catch (error) {
            if (error instanceof Error && error.message === SERVER_UNREACHABLE_MSG) throw error;
            if (error instanceof Error && error.name === 'AbortError') throw new Error(SERVER_UNREACHABLE_MSG);
            if (error instanceof TypeError) throw new Error(SERVER_UNREACHABLE_MSG);
            throw error;
        } finally {
            clearTimeout(timeoutId);
        }
    }

    /**
     * Search NHTSA complaints database
     * @param query - Search query (vehicle symptoms, DTC codes, components)
     * @param limit - Maximum number of results (default: 20)
     *
     * Security: Routes through Next.js API proxy (/api/search)
     * API key is added server-side, never exposed to browser
     */
    async searchComplaints(query: string, limit: number = 20, page: number = 1): Promise<SearchResponse> {
        return this.fetch<SearchResponse>(`${this.apiBaseURL}/search`, {
            query,
            limit: limit.toString(),
            page: page.toString(),
        });
    }

    // Checked AGENTS.md - implementing directly because this is a pure read-only query
    // parameter extension (no auth, no key handling, no SQL). No new security surface added.
    /**
     * Search Technical Service Bulletins (TSBs)
     * @param query - Search query (may be empty when vehicle filter provided)
     * @param limit - Maximum number of results (default: 20)
     * @param make - Optional vehicle make filter (e.g. 'FORD')
     * @param model - Optional vehicle model filter (e.g. 'F-150')
     * @param year - Optional model year filter
     *
     * Security: Routes through Next.js API proxy (/api/search_tsbs)
     * API key is added server-side, never exposed to browser
     */
    async searchTSBs(
        query: string,
        limit: number = 20,
        page: number = 1,
        make?: string,
        model?: string,
        year?: number,
    ): Promise<TSBSearchResponse> {
        const params: Record<string, string> = { query, limit: limit.toString(), page: page.toString() };
        if (make) params.make = make;
        if (model) params.model = model;
        if (year !== undefined) params.year = year.toString();
        return this.fetch<TSBSearchResponse>(`${this.apiBaseURL}/search_tsbs`, params);
    }

    /**
     * Search NHTSA recalls by keyword and/or vehicle make/year via GET /search_recalls
     */
    async searchRecalls(
        query: string,
        limit: number = 20,
        page: number = 1,
        make?: string,
        year?: number,
    ): Promise<RecallSearchResponse> {
        const params: Record<string, string> = { query, limit: limit.toString(), page: page.toString() };
        if (make) params.make = make;
        if (year !== undefined) params.year = year.toString();
        return this.fetch<RecallSearchResponse>(`${this.apiBaseURL}/search_recalls`, params);
    }

    /**
     * Run a full differential diagnosis via POST /diagnose
     */
    async diagnose(request: DiagnoseRequest): Promise<DiagnoseResponse> {
        return this.post<DiagnoseResponse>(`${this.apiBaseURL}/diagnose`, request);
    }

    /**
     * Format a DiagnoseResponse for terminal display
     */
    formatDiagnosis(response: DiagnoseResponse): string {
        const { vehicle, symptoms, candidates, recalls = [], warnings } = response;
        const vehicleStr = `${vehicle.year} ${vehicle.make} ${vehicle.model}`;

        if (candidates.length === 0 && recalls.length === 0) {
            return `[DIAGNOSIS COMPLETE]\nVehicle: ${vehicleStr}\nSymptoms: ${symptoms}\n\nNo diagnostic candidates found. Try adding more symptom detail or DTC codes.`;
        }

        let out = `[DIAGNOSIS COMPLETE]\nVehicle: ${vehicleStr}\nSymptoms: ${symptoms}\nCandidates Found: ${candidates.length}\n`;

        if (warnings.length > 0) {
            out += `\n⚠️  WARNINGS:\n`;
            warnings.forEach(w => { out += `  ${w}\n`; });
        }

        out += `\n`;

        candidates.forEach((c, idx) => {
            const pct = Math.round(c.confidence * 100);
            const bar = '█'.repeat(Math.round(pct / 10)) + '░'.repeat(10 - Math.round(pct / 10));
            const status = c.confidence_sufficient ? '✓' : '⚠';

            out += `━━━ #${idx + 1}: ${c.component.toUpperCase()} ━━━\n`;
            out += `  Confidence: ${status} ${bar} ${pct}%\n`;
            out += `  Reports: ${c.complaint_count}  |  Trend: ${c.trend}\n`;

            if (c.safety_alert) {
                const icon = c.safety_alert.level === 'CRITICAL' ? '🚨' : '⚠️';
                out += `  ${icon} SAFETY ${c.safety_alert.level}: ${c.safety_alert.message}\n`;
            }

            if (c.tsbs.length > 0) {
                out += `  TSBs: ${c.tsbs.length} relevant bulletin(s) found\n`;
            }

            out += `\n`;
        });

        if (recalls.length > 0) {
            const parkItRecalls = recalls.filter(r => r.park_it);
            out += `━━━ NHTSA RECALLS (${recalls.length} active for this vehicle/year) ━━━\n`;
            if (parkItRecalls.length > 0) {
                out += `  🚨 ${parkItRecalls.length} PARK-IT RECALL(S) — DO NOT DRIVE UNTIL REPAIRED\n`;
            }
            out += `\n`;
            recalls.forEach(r => {
                const parkBadge = r.park_it ? '  🚨 PARK IT  ' : '  ';
                out += `${parkBadge}[${r.campaign_no}] ${r.component}\n`;
                if (r.remedy) {
                    const shortRemedy = r.remedy.length > 110 ? r.remedy.slice(0, 110) + '…' : r.remedy;
                    out += `    Remedy: ${shortRemedy}\n`;
                }
                out += `\n`;
            });
        }

        return out;
    }

    /**
     * Format diagnostic results for display
     */
    formatResults(response: SearchResponse | TSBSearchResponse): string {
        const { query, results, source } = response;
        const totalCount = response.total_count ?? results.length;
        const page = response.page ?? 1;
        const totalPages = response.total_pages ?? 1;

        if (results.length === 0) {
            return `[SEARCH COMPLETE]\nQuery: "${query}"\nSource: ${source}\n\nNo matches found in database.\n\nSuggestion: Try broader search terms or check vehicle details.`;
        }

        const pageInfo = totalPages > 1 ? `  |  Page ${page} of ${totalPages} (${totalCount} total)` : `  |  ${totalCount} total`;
        let output = `[SEARCH COMPLETE]\nQuery: "${query}"\nSource: ${source}\nShowing: ${results.length} results${pageInfo}\n\n`;

        results.forEach((result, idx) => {
            output += `━━━ RESULT ${idx + 1} ━━━\n`;
            output += `Vehicle: ${result.year} ${result.make} ${result.model}\n`;
            output += `Component: ${result.component}\n`;
            output += `Issue: ${result.summary}\n`;

            // Add TSB ID if available
            if ('nhtsa_id' in result) {
                output += `TSB ID: ${result.nhtsa_id}\n`;
            }

            output += `\n`;
        });

        return output;
    }

    formatRecallResults(response: RecallSearchResponse): string {
        const { query, results, source, total_count, page, total_pages, message } = response;
        if (message && results.length === 0) {
            return `[RECALL SEARCH]\nQuery: "${query}"\n\n${message}`;
        }
        if (results.length === 0) {
            return `[RECALL SEARCH]\nQuery: "${query}"\nSource: ${source}\n\nNo matching recalls found.`;
        }
        const pageInfo = (total_pages ?? 1) > 1
            ? `  |  Page ${page} of ${total_pages} (${total_count} total)`
            : `  |  ${total_count} total`;
        let output = `[RECALL SEARCH]\nQuery: "${query}"\nSource: ${source}\nShowing: ${results.length} results${pageInfo}\n\n`;
        results.forEach((r, idx) => {
            const yearRange = r.year_from && r.year_to
                ? `${r.year_from}–${r.year_to}`
                : (r.year_from ?? r.year_to ?? 'N/A');
            const parkFlag = r.park_it ? ' ⚠️ PARK-IT RECALL' : (r.park_outside ? ' ⚠️ PARK OUTSIDE' : '');
            output += `━━━ RECALL ${idx + 1}${parkFlag} ━━━\n`;
            output += `Campaign: ${r.campaign_no}  |  ${r.make} ${r.model} (${yearRange})\n`;
            output += `Component: ${r.component ?? 'N/A'}\n`;
            if (r.summary) output += `Summary: ${r.summary}\n`;
            if (r.consequence) output += `Consequence: ${r.consequence}\n`;
            if (r.remedy) output += `Remedy: ${r.remedy}\n`;
            if (r.vehicles_affected) output += `Vehicles affected: ${r.vehicles_affected.toLocaleString()}\n`;
            output += `\n`;
        });
        return output;
    }

    /**
     * Format errors for display.
     * Server-unreachable errors (502/504/timeout/ECONNREFUSED) get Tailscale-specific guidance.
     */
    // Checked AGENTS.md - implementing directly: pure display formatting, no security surface.
    formatError(error: Error): string {
        if (error.message.startsWith('Diagnostic Server Unreachable')) {
            return (
                `🔌 DIAGNOSTIC SERVER UNREACHABLE\n\n` +
                `${error.message}\n\n` +
                `Troubleshooting:\n` +
                `- Verify Tailscale is connected and active\n` +
                `- Confirm Home Server is running: curl http://localhost:8000/\n` +
                `- Check server logs: tail -f /tmp/backend.log`
            );
        }
        return `⚠️ SYSTEM ERROR ⚠️\n\n${error.message}\n\nTroubleshooting:\n- Verify backend server is running (port 8000)\n- Check API key configuration\n- Confirm network connectivity`;
    }

    /**
     * Fetch distinct makes and models from the complaints database.
     * Returns null on error so callers can fall back to static data silently.
     */
    async fetchVehicles(): Promise<VehicleData | null> {
        try {
            return await this.fetch<VehicleData>(`${this.apiBaseURL}/vehicles`);
        } catch {
            return null;
        }
    }

    /**
     * Fetch distinct years that have complaint data for a given make + model.
     * Returns null on error so callers can fall back to the static year list silently.
     */
    async fetchVehicleYears(make: string, model: string): Promise<number[] | null> {
        try {
            const data = await this.fetch<VehicleYears>(`${this.apiBaseURL}/vehicles/years`, { make, model });
            return data.years;
        } catch {
            return null;
        }
    }
}

export interface VehicleData {
    makes: string[];
    models_by_make: Record<string, string[]>;
}

export interface VehicleYears {
    make: string;
    model: string;
    years: number[];
}

// Export singleton instance
export const api = new DiagnosticAPI();

// --- Vehicle Dashboard ---

export interface DashboardData {
    make: string;
    model: string;
    year: number;
    complaint_count: number;
    tsb_count: number;
    recall_count?: number;
    top_components: Array<{ component: string; count: number }>;
    trend: 'increasing' | 'decreasing' | 'stable';
    trend_current_year_count: number;
    trend_prior_year_count: number;
}

// NOTE: fetchDashboard is a method added to DiagnosticAPI below the class definition patch
// It is defined as a standalone function here for use by VehicleDashboard component
export async function fetchDashboard(make: string, model: string, year: number): Promise<DashboardData | null> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), GET_TIMEOUT_MS);
    try {
        const res = await fetch(
            `/api/vehicle/dashboard?make=${encodeURIComponent(make)}&model=${encodeURIComponent(model)}&year=${year}`,
            { signal: controller.signal, cache: 'no-store' }
        );
        clearTimeout(timeoutId);
        if (!res.ok) return null;
        return (await res.json()) as DashboardData;
    } catch (err) {
        clearTimeout(timeoutId);
        if (err instanceof Error && err.name !== 'AbortError') {
            console.error('fetchDashboard error:', err);
        }
        return null;
    }
}

// --- Component Drill-Down ---

export interface ComplaintItem {
    year: number;
    component: string;
    summary: string;
}

export interface ComponentComplaintsResponse {
    make: string;
    model: string;
    year: number;
    component: string;
    results: ComplaintItem[];
    total_count: number;
    page: number;
    total_pages: number;
}

export async function fetchComponentComplaints(
    make: string, model: string, year: number, component: string, page: number = 1
): Promise<ComponentComplaintsResponse | null> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), GET_TIMEOUT_MS);
    try {
        const params = new URLSearchParams({
            make,
            model,
            year: year.toString(),
            component,
            page: page.toString(),
        });
        const res = await fetch(
            `/api/vehicle/complaints?${params.toString()}`,
            { signal: controller.signal, cache: 'no-store' }
        );
        clearTimeout(timeoutId);
        if (!res.ok) return null;
        return (await res.json()) as ComponentComplaintsResponse;
    } catch (err) {
        clearTimeout(timeoutId);
        if (err instanceof Error && err.name !== 'AbortError') {
            console.error('fetchComponentComplaints error:', err);
        }
        return null;
    }
}

// --- TSB Drill-Down ---

export interface TsbItem {
    bulletin_no: string;
    bulletin_date: string;   // "YYYYMMDD" string from backend
    component: string;
    summary: string;
}

export interface VehicleTsbsResponse {
    make: string;
    model: string;
    year: number;
    results: TsbItem[];
    total_count: number;
    page: number;
    total_pages: number;
}

export async function fetchVehicleTsbs(
    make: string, model: string, year: number, page: number = 1
): Promise<VehicleTsbsResponse | null> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), GET_TIMEOUT_MS);
    try {
        const params = new URLSearchParams({
            make, model, year: year.toString(), page: page.toString(),
        });
        const res = await fetch(
            `/api/vehicle/tsbs?${params.toString()}`,
            { signal: controller.signal, cache: 'no-store' }
        );
        clearTimeout(timeoutId);
        if (!res.ok) return null;
        return (await res.json()) as VehicleTsbsResponse;
    } catch (err) {
        clearTimeout(timeoutId);
        if (err instanceof Error && err.name !== 'AbortError') {
            console.error('fetchVehicleTsbs error:', err);
        }
        return null;
    }
}

// --- Recall Drill-Down ---

export interface RecallItem {
    campaign_no: string;
    component: string;
    summary: string;
    remedy: string;
    park_it: boolean;
}

export interface VehicleRecallsResponse {
    make: string;
    model: string;
    year: number;
    recalls: RecallItem[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

export async function fetchVehicleRecalls(
    make: string, model: string, year: number, page: number = 1
): Promise<VehicleRecallsResponse | null> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), GET_TIMEOUT_MS);
    try {
        const params = new URLSearchParams({
            make, model, year: year.toString(), page: page.toString(),
        });
        const res = await fetch(
            `/api/vehicle/recalls?${params.toString()}`,
            { signal: controller.signal, cache: 'no-store' }
        );
        clearTimeout(timeoutId);
        if (!res.ok) return null;
        return (await res.json()) as VehicleRecallsResponse;
    } catch (err) {
        clearTimeout(timeoutId);
        if (err instanceof Error && err.name !== 'AbortError') {
            console.error('fetchVehicleRecalls error:', err);
        }
        return null;
    }
}

// --- Diagnosis History ---

export interface HistoryEntry {
    id: number;
    created_at: string;
    vin?: string;
    year: number;
    make: string;
    model: string;
    engine?: string;
    symptoms: string;
    dtc_codes: string[];
    findings: string;
    candidate_count: number;
    has_warnings: boolean;
}

export interface HistoryResponse {
    entries: HistoryEntry[];
    total: number;
}

export interface SaveHistoryRequest {
    vin?: string;
    year: number;
    make: string;
    model: string;
    engine?: string;
    symptoms: string;
    dtc_codes: string[];
    findings: string;
    candidate_count: number;
    has_warnings: boolean;
}

export async function fetchHistory(
    make: string,
    model: string,
    year?: number,
    vin?: string,
): Promise<HistoryResponse | null> {
    const params = new URLSearchParams({ make, model });
    if (year !== undefined) params.set('year', String(year));
    if (vin) params.set('vin', vin);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), GET_TIMEOUT_MS);
    try {
        const res = await fetch(`/api/history?${params}`, { signal: controller.signal, cache: 'no-store' });
        clearTimeout(timeoutId);
        if (!res.ok) return null;
        return (await res.json()) as HistoryResponse;
    } catch {
        clearTimeout(timeoutId);
        return null;
    }
}

export async function saveHistory(entry: SaveHistoryRequest): Promise<{ id: number; created_at: string } | null> {
    // Fire-and-forget — never throw, history save must not break diagnosis flow
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), POST_TIMEOUT_MS);
    try {
        const res = await fetch('/api/history', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(entry),
            signal: controller.signal,
        });
        clearTimeout(timeoutId);
        if (!res.ok) return null;
        return (await res.json()) as { id: number; created_at: string };
    } catch {
        clearTimeout(timeoutId);
        return null;
    }
}

// --- Report Generation ---

export interface ReportRequest {
    make: string;
    model: string;
    year_start: number;
    year_end: number;
    no_llm?: boolean;
    no_api?: boolean;
}

export interface ReportResponse {
    content: string;
    filename: string;
    make: string;
    model: string;
    year_start: number;
    year_end: number;
}

const REPORT_TIMEOUT_MS = 185_000;

export async function generateReport(req: ReportRequest): Promise<ReportResponse> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REPORT_TIMEOUT_MS);
    try {
        const res = await fetch('/api/vehicle/report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(req),
            signal: controller.signal,
        });
        clearTimeout(timeoutId);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
            throw new Error((err as { detail?: string }).detail ?? `HTTP ${res.status}`);
        }
        return (await res.json()) as ReportResponse;
    } catch (err) {
        clearTimeout(timeoutId);
        if (err instanceof Error && err.name === 'AbortError') {
            throw new Error('Report generation timed out. Try Fast mode (skip AI polish).');
        }
        throw err;
    }
}

// --- Checklist ---

export interface ChecklistRecall {
    campaign_no: string;
    component: string;
    summary: string;
    park_it: boolean;
    year_from: number | null;
    year_to: number | null;
}

export interface ChecklistSection {
    component: string;
    complaint_count: number;
    checks: string[];
}

export interface ChecklistTsb {
    bulletin_no: string;
    component: string;
    summary: string;
}

export interface ChecklistData {
    make: string;
    model: string;
    year_start: number;
    year_end: number;
    generated_at: string;
    has_park_it: boolean;
    recalls: ChecklistRecall[];
    sections: ChecklistSection[];
    tsbs: ChecklistTsb[];
    standard_checks: string[];
}

export interface ChecklistRequest {
    make: string;
    model: string;
    year_start: number;
    year_end: number;
    generate_pdf?: boolean;
}

export interface ChecklistResponse {
    content: string;
    filename: string;
    make: string;
    model: string;
    year_start: number;
    year_end: number;
    data: ChecklistData;
    pdf_b64?: string;
    pdf_filename?: string;
}

const CHECKLIST_TIMEOUT_MS = 90_000;

export async function generateChecklist(req: ChecklistRequest): Promise<ChecklistResponse> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), CHECKLIST_TIMEOUT_MS);
    try {
        const res = await fetch('/api/vehicle/checklist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(req),
            signal: controller.signal,
        });
        clearTimeout(timeoutId);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
            throw new Error((err as { detail?: string }).detail ?? `HTTP ${res.status}`);
        }
        return (await res.json()) as ChecklistResponse;
    } catch (err) {
        clearTimeout(timeoutId);
        if (err instanceof Error && err.name === 'AbortError') {
            throw new Error('Checklist generation timed out.');
        }
        throw err;
    }
}

// --- VIN Decode ---

export interface VinDecodeResult {
    vin: string;
    valid: boolean;
    year?: number;
    make?: string;
    model?: string;
    engine?: string;
    drive_type?: string;
    body_class?: string;
    trim?: string;
    fuel_type?: string;
    error?: string;
}

export async function fetchVin(vin: string): Promise<VinDecodeResult | null> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), GET_TIMEOUT_MS);
    try {
        const res = await fetch(`/api/vin?vin=${encodeURIComponent(vin)}`, {
            signal: controller.signal,
            cache: 'no-store',
        });
        clearTimeout(timeoutId);
        return (await res.json()) as VinDecodeResult;
    } catch (err) {
        clearTimeout(timeoutId);
        const msg = err instanceof Error && err.name === 'AbortError' ? 'Request timed out' : 'Network error';
        return { vin, valid: false, error: msg };
    }
}
