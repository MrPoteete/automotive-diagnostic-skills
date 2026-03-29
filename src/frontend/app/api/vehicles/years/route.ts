// Checked AGENTS.md - implementing directly; server-side proxy, mirrors existing /api/vehicles pattern.
// Boilerplate reviewed by Gemini (gemini-2.5-flash) per GEMINI_WORKFLOW.md.

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000';
const API_KEY = process.env.API_KEY ?? '';

export async function GET(req: NextRequest) {
    const { searchParams } = req.nextUrl;
    const make = searchParams.get('make');
    const model = searchParams.get('model');

    if (!make || !model) {
        return NextResponse.json({ error: 'make and model are required' }, { status: 400 });
    }

    try {
        const url = `${BACKEND_URL}/vehicles/years?make=${encodeURIComponent(make)}&model=${encodeURIComponent(model)}`;
        const res = await fetch(url, {
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
