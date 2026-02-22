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
const API_BASE_URL = '/api'; // Next.js API routes

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
    source: string;
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
    samples: unknown[];
}

export interface DiagnoseResponse {
    vehicle: VehicleInfo;
    symptoms: string;
    dtc_codes: string[];
    candidates: DiagnosticCandidate[];
    warnings: string[];
    data_sources: Record<string, unknown>;
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

    private async post<T>(endpoint: string, body: unknown): Promise<T> {
        const url = new URL(endpoint, window.location.origin);
        const response = await fetch(url.toString(), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API Error (${response.status}): ${errorText}`);
        }
        return response.json();
    }

    private async fetch<T>(endpoint: string, params?: Record<string, string>): Promise<T> {
        const url = new URL(endpoint, window.location.origin);

        // Add query parameters
        if (params) {
            Object.entries(params).forEach(([key, value]) => {
                url.searchParams.append(key, value);
            });
        }

        // Security: No API key in client-side code anymore
        // The Next.js API routes add the API key server-side
        const response = await fetch(url.toString(), {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API Error (${response.status}): ${errorText}`);
        }

        return response.json();
    }

    // Checked AGENTS.md - Routes updated per security-engineer review (agent a8a8f66)
    /**
     * Health check - verify backend server is online
     * Note: Calls backend directly (no auth required for health check)
     */
    async healthCheck(): Promise<HealthCheckResponse> {
        const response = await fetch(this.backendURL);
        if (!response.ok) {
            throw new Error(`Backend offline: ${response.status}`);
        }
        return response.json();
    }

    /**
     * Search NHTSA complaints database
     * @param query - Search query (vehicle symptoms, DTC codes, components)
     * @param limit - Maximum number of results (default: 20)
     *
     * Security: Routes through Next.js API proxy (/api/search)
     * API key is added server-side, never exposed to browser
     */
    async searchComplaints(query: string, limit: number = 20): Promise<SearchResponse> {
        return this.fetch<SearchResponse>(`${this.apiBaseURL}/search`, {
            query,
            limit: limit.toString(),
        });
    }

    /**
     * Search Technical Service Bulletins (TSBs)
     * @param query - Search query
     * @param limit - Maximum number of results (default: 20)
     *
     * Security: Routes through Next.js API proxy (/api/search_tsbs)
     * API key is added server-side, never exposed to browser
     */
    async searchTSBs(query: string, limit: number = 20): Promise<TSBSearchResponse> {
        return this.fetch<TSBSearchResponse>(`${this.apiBaseURL}/search_tsbs`, {
            query,
            limit: limit.toString(),
        });
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
        const { vehicle, symptoms, candidates, warnings } = response;
        const vehicleStr = `${vehicle.year} ${vehicle.make} ${vehicle.model}`;

        if (candidates.length === 0) {
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

        return out;
    }

    /**
     * Format diagnostic results for display
     */
    formatResults(response: SearchResponse | TSBSearchResponse): string {
        const { query, results, source } = response;

        if (results.length === 0) {
            return `[SEARCH COMPLETE]\nQuery: "${query}"\nSource: ${source}\n\nNo matches found in database.\n\nSuggestion: Try broader search terms or check vehicle details.`;
        }

        let output = `[SEARCH COMPLETE]\nQuery: "${query}"\nSource: ${source}\nMatches Found: ${results.length}\n\n`;

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

    /**
     * Format errors for display
     */
    formatError(error: Error): string {
        return `⚠️ SYSTEM ERROR ⚠️\n\n${error.message}\n\nTroubleshooting:\n- Verify backend server is running (port 8000)\n- Check API key configuration\n- Confirm network connectivity`;
    }
}

// Export singleton instance
export const api = new DiagnosticAPI();
