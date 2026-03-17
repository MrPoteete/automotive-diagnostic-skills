// Checked AGENTS.md - implementing via Gemini delegation per GEMINI_WORKFLOW.md.
// Server-side proxy to backend /vehicle/recalls — mirrors existing proxy patterns.
import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000';
const API_KEY = process.env.API_KEY ?? 'mechanic-secret-key-123';

export async function GET(req: NextRequest) {
    try {
        const { searchParams } = req.nextUrl;
        const make = searchParams.get('make');
        const model = searchParams.get('model');
        const year = searchParams.get('year');
        const page = searchParams.get('page') ?? '1';
        const limit = searchParams.get('limit') ?? '10';

        if (!make || !model || !year) {
            return NextResponse.json({ error: 'make, model, and year are required' }, { status: 400 });
        }

        const backendParams = new URLSearchParams({ make, model, year, page, limit });

        const res = await fetch(
            `${BACKEND_URL}/vehicle/recalls?${backendParams.toString()}`,
            { method: 'GET', headers: { 'X-API-KEY': API_KEY }, cache: 'no-store' }
        );

        if (!res.ok) {
            return NextResponse.json({ error: 'Backend error' }, { status: res.status });
        }
        return NextResponse.json(await res.json());
    } catch (err) {
        console.error('/api/vehicle/recalls error:', err);
        return NextResponse.json({ error: 'Failed to reach backend' }, { status: 500 });
    }
}
