// Checked AGENTS.md - implementing via Gemini delegation per GEMINI_WORKFLOW.md.
// Server-side proxy to backend /vin/decode — mirrors existing /api/vehicles pattern.
import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000';
const API_KEY = process.env.API_KEY ?? '';

export async function GET(req: NextRequest) {
    try {
        const vin = req.nextUrl.searchParams.get('vin');
        if (!vin) {
            return NextResponse.json({ error: 'vin parameter is required' }, { status: 400 });
        }
        const res = await fetch(`${BACKEND_URL}/vin/decode?vin=${encodeURIComponent(vin)}`, {
            method: 'GET',
            headers: { 'X-API-KEY': API_KEY },
            cache: 'no-store',
        });
        if (!res.ok) {
            return NextResponse.json({ error: 'Backend error' }, { status: res.status });
        }
        return NextResponse.json(await res.json());
    } catch {
        return NextResponse.json({ error: 'Failed to reach backend' }, { status: 500 });
    }
}
