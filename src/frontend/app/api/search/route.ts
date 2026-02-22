// Checked AGENTS.md - security-engineer reviewed (agent a8a8f66)
// Gemini Flash boilerplate + Claude security hardening
import { createProxyHandler } from '../utils/proxyHandler';

/**
 * Next.js App Router API Route Handler for `/api/search`.
 * Proxies GET requests to `http://localhost:8000/search`.
 *
 * Accepts query parameters:
 * - `query`: string (required, non-empty, max 500 chars)
 * - `limit`: number (optional, default 20, max 100, must be positive)
 *
 * Security:
 * - Adds `X-API-KEY` header from `process.env.API_KEY` (server-side only)
 * - SSRF protection via backend URL whitelist
 * - Input validation (size limits, type checking)
 * - Request timeout (10 seconds)
 */
export const GET = createProxyHandler({
  backendPath: '/search',
});
