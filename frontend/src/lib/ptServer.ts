/** Server-only Packet Tracer proxy helpers. Never import from client components. */

const BACKEND =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'http://127.0.0.1:8000';

export function ptBackendBase(): string {
  return BACKEND.replace(/\/$/, '');
}

export function ptToken(): string {
  return (process.env.PACKETTRACER_TOKEN || '').trim();
}

export function ptHeaders(extra?: HeadersInit): Headers {
  const headers = new Headers(extra);
  const token = ptToken();
  if (token) headers.set('X-PT-Token', token);
  return headers;
}

function backendTimeout(ms: number): AbortSignal {
  if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
    return AbortSignal.timeout(ms);
  }
  const ctrl = new AbortController();
  setTimeout(() => ctrl.abort(), ms);
  return ctrl.signal;
}

export async function ptFetch(path: string, init?: RequestInit): Promise<Response> {
  const url = `${ptBackendBase()}${path.startsWith('/') ? path : `/${path}`}`;
  const headers = ptHeaders(init?.headers);
  // Default short timeout so a wedged uvicorn cannot freeze Next /api/pt/* forever.
  const timeoutMs = path.includes('/execute') ? 900_000 : path.includes('/status') ? 25_000 : 8_000;
  const signal = init?.signal ?? backendTimeout(timeoutMs);
  return fetch(url, { ...init, headers, cache: 'no-store', signal });
}
