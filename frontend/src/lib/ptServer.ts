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

export async function ptFetch(path: string, init?: RequestInit): Promise<Response> {
  const url = `${ptBackendBase()}${path.startsWith('/') ? path : `/${path}`}`;
  const headers = ptHeaders(init?.headers);
  return fetch(url, { ...init, headers, cache: 'no-store' });
}
