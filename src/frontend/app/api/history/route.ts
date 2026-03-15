// Checked AGENTS.md - implementing via Gemini delegation per GEMINI_WORKFLOW.md.
// GET + POST proxy for /history — mirrors existing proxy patterns.
import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000';
const API_KEY = process.env.API_KEY ?? 'mechanic-secret-key-123';

export async function GET(req: NextRequest) {
    try {
        const { searchParams } = req.nextUrl;
        const make = searchParams.get('make');
        const model = searchParams.get('model');
        if (!make || !model) {
            return NextResponse.json({ error: 'make and model are required' }, { status: 400 });
        }
        const query = new URLSearchParams({ make, model });
        const year = searchParams.get('year');
        const vin = searchParams.get('vin');
        const limit = searchParams.get('limit');
        if (year) query.set('year', year);
        if (vin) query.set('vin', vin);
        if (limit) query.set('limit', limit);

        const res = await fetch(`${BACKEND_URL}/history?${query}`, {
            headers: { 'X-API-KEY': API_KEY },
            cache: 'no-store',
        });
        if (!res.ok) return NextResponse.json({ error: 'Backend error' }, { status: res.status });
        return NextResponse.json(await res.json());
    } catch {
        return NextResponse.json({ error: 'Failed to reach backend' }, { status: 500 });
    }
}

export async function POST(req: NextRequest) {
    try {
        const body: unknown = await req.json();
        const res = await fetch(`${BACKEND_URL}/history`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-API-KEY': API_KEY },
            body: JSON.stringify(body),
            cache: 'no-store',
        });
        if (!res.ok) return NextResponse.json({ error: 'Backend error' }, { status: res.status });
        return NextResponse.json(await res.json());
    } catch {
        return NextResponse.json({ error: 'Failed to reach backend' }, { status: 500 });
    }
}
