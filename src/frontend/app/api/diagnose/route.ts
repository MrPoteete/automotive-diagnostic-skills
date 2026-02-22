// Checked AGENTS.md - implementing directly because this is a security-critical API proxy.
// Applied same security patterns as proxyHandler.ts (security-engineer reviewed, agent a8a8f66).
// POST proxy for /diagnose — adds server-side API key, never exposes it to the browser.
import { NextRequest, NextResponse } from 'next/server';

// Security: SSRF protection — whitelist allowed backend hosts
const ALLOWED_BACKENDS = [
  'http://localhost:8000',
  'http://127.0.0.1:8000',
  'http://backend:8000', // Docker service name
];

const MAX_SYMPTOMS_LENGTH = 1000;
const REQUEST_TIMEOUT_MS = 30000; // Diagnosis can take longer than a simple FTS search

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  // 1. Validate API key env var
  const API_KEY = process.env.API_KEY;
  if (!API_KEY) {
    console.error('SERVER ERROR: API_KEY environment variable is not set.');
    return NextResponse.json({ error: 'Server configuration error.' }, { status: 500 });
  }

  // 2. SSRF protection
  if (!ALLOWED_BACKENDS.includes(BACKEND_URL)) {
    console.error(`Unauthorized backend URL: ${BACKEND_URL}`);
    return NextResponse.json({ error: 'Backend URL not allowed.' }, { status: 500 });
  }

  // 3. Parse request body
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body.' }, { status: 400 });
  }

  // 4. Validate required fields
  const { vehicle, symptoms, dtc_codes } = body;

  if (!vehicle || typeof vehicle !== 'object' || Array.isArray(vehicle)) {
    return NextResponse.json({ error: 'vehicle is required (object with make, model, year).' }, { status: 400 });
  }
  const v = vehicle as Record<string, unknown>;
  if (!v.make || !v.model || !v.year) {
    return NextResponse.json({ error: 'vehicle must have make, model, and year.' }, { status: 400 });
  }

  if (!symptoms || typeof symptoms !== 'string' || symptoms.trim().length < 3) {
    return NextResponse.json({ error: 'symptoms is required (min 3 chars).' }, { status: 400 });
  }
  if (symptoms.length > MAX_SYMPTOMS_LENGTH) {
    return NextResponse.json(
      { error: `symptoms too long (max ${MAX_SYMPTOMS_LENGTH} chars).` },
      { status: 400 }
    );
  }

  // 5. Proxy to backend with timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const backendResponse = await fetch(`${BACKEND_URL}/diagnose`, {
      method: 'POST',
      headers: {
        'X-API-KEY': API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        vehicle,
        symptoms,
        dtc_codes: Array.isArray(dtc_codes) ? dtc_codes : [],
      }),
      cache: 'no-store',
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!backendResponse.ok) {
      const errorBody = await backendResponse.text();
      console.error(`BACKEND ERROR /diagnose: ${backendResponse.status}. ${errorBody}`);
      return NextResponse.json({ error: 'Backend diagnostic engine failed.' }, { status: 502 });
    }

    const data = await backendResponse.json();
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    clearTimeout(timeoutId);

    if (error instanceof Error && error.name === 'AbortError') {
      console.error(`TIMEOUT: /diagnose exceeded ${REQUEST_TIMEOUT_MS}ms`);
      return NextResponse.json({ error: 'Diagnosis timed out. Try a simpler query.' }, { status: 504 });
    }

    console.error('NETWORK ERROR proxying /diagnose:', error);
    return NextResponse.json({ error: 'Failed to connect to backend.' }, { status: 502 });
  }
}
