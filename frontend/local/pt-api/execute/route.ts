import { NextRequest, NextResponse } from 'next/server';
import { ptFetch, ptToken } from '@/lib/ptServer';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const maxDuration = 300;

export async function POST(req: NextRequest) {
  if (!ptToken()) {
    return NextResponse.json(
      { ok: false, stage: 'config', message: 'PACKETTRACER_TOKEN is not set on the Next.js server' },
      { status: 503 },
    );
  }
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ ok: false, stage: 'request', message: 'Invalid JSON body' }, { status: 400 });
  }
  try {
    const res = await ptFetch('/api/packettracer/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({
      ok: false,
      stage: 'proxy',
      message: 'Invalid response from backend',
    }));
    return NextResponse.json(data, { status: res.status === 401 ? 401 : res.ok ? 200 : res.status });
  } catch (e) {
    return NextResponse.json(
      {
        ok: false,
        stage: 'proxy',
        message: e instanceof Error ? e.message : 'Backend unreachable',
      },
      { status: 502 },
    );
  }
}
