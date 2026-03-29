// Checked AGENTS.md - implementing via Gemini delegation per GEMINI_WORKFLOW.md.
// POST proxy to backend /vehicle/report — follows existing proxy patterns.
import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000';
const API_KEY = process.env.API_KEY ?? '';

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
        const data: unknown = await res.json().catch(() => null);
        if (!res.ok) {
            const detail = (data as { detail?: string } | null)?.detail ?? `HTTP ${res.status}`;
            return NextResponse.json({ detail }, { status: res.status });
        }
        return NextResponse.json(data);
    } catch {
        return NextResponse.json({ detail: 'Failed to reach backend — is the server running?' }, { status: 500 });
    }
}
