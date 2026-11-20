import { NextResponse } from 'next/server';
import { ptFetch, ptToken } from '@/lib/ptServer';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET() {
  if (!ptToken()) {
    return NextResponse.json(
      {
        ready: false,
        enabled: false,
        canvas_empty: false,
        detail: 'PACKETTRACER_TOKEN is not set on the Next.js server',
      },
      { status: 200 },
    );
  }
  try {
    const res = await ptFetch('/api/packettracer/status');
    const data = await res.json().catch(() => ({}));
    if (res.status === 404) {
      return NextResponse.json(
        {
          ready: false,
          enabled: false,
          canvas_empty: false,
          detail: 'Packet Tracer integration disabled on backend',
        },
        { status: 200 },
      );
    }
    if (!res.ok) {
      return NextResponse.json(
        {
          ready: false,
          enabled: true,
          canvas_empty: false,
          detail:
            typeof data?.detail === 'string'
              ? data.detail
              : 'Packet Tracer status unavailable',
        },
        { status: 200 },
      );
    }
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      {
        ready: false,
        enabled: true,
        canvas_empty: false,
        detail: 'Backend unreachable',
      },
      { status: 200 },
    );
  }
}
