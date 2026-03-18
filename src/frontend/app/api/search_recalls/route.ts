// Checked AGENTS.md - mirrors search_tsbs proxy pattern; read-only GET proxy, no new security surface.
import { createProxyHandler } from '../utils/proxyHandler';

/**
 * Next.js App Router API Route Handler for `/api/search_recalls`.
 * Proxies GET requests to `http://localhost:8000/search_recalls`.
 *
 * Accepts query parameters:
 * - `query`: string (keyword search)
 * - `make`: string (optional vehicle make filter)
 * - `year`: number (optional model year filter)
 * - `limit`: number (optional, default 20)
 * - `page`: number (optional, default 1)
 */
export const GET = createProxyHandler({
  backendPath: '/search_recalls',
  allowEmptyQuery: true,
});
