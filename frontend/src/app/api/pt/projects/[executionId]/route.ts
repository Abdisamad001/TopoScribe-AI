import { NextRequest, NextResponse } from 'next/server';
import { ptFetch, ptToken } from '@/lib/ptServer';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type Ctx = { params: Promise<{ executionId: string }> };

export async function GET(_req: NextRequest, ctx: Ctx) {
  if (!ptToken()) {
    return NextResponse.json({ detail: 'PACKETTRACER_TOKEN not configured' }, { status: 503 });
  }
  const { executionId } = await ctx.params;
  const safe = executionId.replace(/[^a-zA-Z0-9_-]/g, '');
  if (!safe || safe !== executionId) {
    return NextResponse.json({ detail: 'Invalid execution_id' }, { status: 400 });
  }
  try {
    const res = await ptFetch(`/api/packettracer/projects/${encodeURIComponent(safe)}`);
    if (!res.ok) {
      const detail = await res.text().catch(() => 'Download failed');
      return NextResponse.json({ detail }, { status: res.status });
    }
    const buf = await res.arrayBuffer();
    const filename =
      res.headers.get('content-disposition')?.match(/filename="?([^";]+)"?/i)?.[1] ||
      `${safe}.pkt`;
    return new NextResponse(buf, {
      status: 200,
      headers: {
        'Content-Type': 'application/octet-stream',
        'Content-Disposition': `attachment; filename="${filename}"`,
      },
    });
  } catch (e) {
    return NextResponse.json(
      { detail: e instanceof Error ? e.message : 'Backend unreachable' },
      { status: 502 },
    );
  }
}
