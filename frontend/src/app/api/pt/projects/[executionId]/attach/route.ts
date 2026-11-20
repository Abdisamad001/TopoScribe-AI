import { NextRequest, NextResponse } from 'next/server';
import { ptFetch, ptToken } from '@/lib/ptServer';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type Ctx = { params: Promise<{ executionId: string }> };

export async function POST(req: NextRequest, ctx: Ctx) {
  if (!ptToken()) {
    return NextResponse.json({ detail: 'PACKETTRACER_TOKEN not configured' }, { status: 503 });
  }
  const { executionId } = await ctx.params;
  const safe = executionId.replace(/[^a-zA-Z0-9_-]/g, '');
  if (!safe || safe !== executionId) {
    return NextResponse.json({ detail: 'Invalid execution_id' }, { status: 400 });
  }
  let body: { design_id?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ detail: 'Invalid JSON' }, { status: 400 });
  }
  try {
    const res = await ptFetch(`/api/packettracer/projects/${encodeURIComponent(safe)}/attach`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ design_id: body.design_id }),
    });
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch (e) {
    return NextResponse.json(
      { detail: e instanceof Error ? e.message : 'Backend unreachable' },
      { status: 502 },
    );
  }
}
