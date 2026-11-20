import { NextRequest, NextResponse } from 'next/server';
import { ptFetch, ptToken } from '@/lib/ptServer';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(req: NextRequest) {
  if (!ptToken()) {
    return NextResponse.json({ projects: [] }, { status: 200 });
  }
  const designId = req.nextUrl.searchParams.get('design_id');
  const qs = designId ? `?design_id=${encodeURIComponent(designId)}` : '';
  try {
    const res = await ptFetch(`/api/packettracer/projects${qs}`);
    if (res.status === 404) {
      return NextResponse.json({ projects: [] });
    }
    const data = await res.json().catch(() => ({ projects: [] }));
    return NextResponse.json(data, { status: res.ok ? 200 : res.status });
  } catch {
    return NextResponse.json({ projects: [] }, { status: 200 });
  }
}
