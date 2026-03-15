// Checked AGENTS.md - implementing via Gemini delegation per GEMINI_WORKFLOW.md.
// POST proxy to backend /vehicle/report — follows existing proxy patterns.
import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000';
const API_KEY = process.env.API_KEY ?? 'mechanic-secret-key-123';

export async function POST(req: NextRequest) {
    try {
        const body: unknown = await req.json();
        const res = await fetch(`${BACKEND_URL}/vehicle/report`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-KEY': API_KEY,
            },
            body: JSON.stringify(body),
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
