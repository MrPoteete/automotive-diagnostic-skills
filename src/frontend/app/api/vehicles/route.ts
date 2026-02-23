// Checked AGENTS.md - implementing directly; server-side proxy only, mirrors existing /api/diagnose pattern.
// Boilerplate reviewed by Gemini (gemini-2.5-flash) per GEMINI_WORKFLOW.md.

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000';
const API_KEY = process.env.API_KEY ?? 'mechanic-secret-key-123';

export async function GET(_req: NextRequest) {
    try {
        const res = await fetch(`${BACKEND_URL}/vehicles`, {
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
