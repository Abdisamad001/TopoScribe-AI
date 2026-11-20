/** Browser-safe Packet Tracer client (talks only to Next.js /api/pt/*). */

export type PtStatus = {
  ready: boolean;
  enabled?: boolean;
  canvas_empty?: boolean;
  user_devices?: number;
  detail?: string;
};

export type PtProject = {
  execution_id: string;
  design_id: string | null;
  ok: boolean;
  stage: string;
  message: string;
  filename: string;
  created_at: string;
  has_download: boolean;
};

export type PtExecuteResult = {
  execution_id: string;
  ok: boolean;
  stage?: string;
  message?: string;
  devices?: Array<{
    node_id: string;
    label?: string;
    pt_name: string;
    pt_model: string;
    ok: boolean;
    detail?: string;
  }>;
  links?: Array<{
    link_id?: string;
    a_id: string;
    a_port: string;
    b_id: string;
    b_port: string;
    cable_type: string;
    ok: boolean;
    detail?: string;
  }>;
  cli_lines?: Array<{
    device_id: string;
    line: string;
    status: string;
    impact?: string;
    detail?: string;
  }>;
  pings?: Array<{
    source: string;
    destination: string;
    attempts: number;
    final_status: string;
    messages?: string[];
  }>;
  project_download_id?: string;
  project_filename?: string;
  name_map?: Record<string, string>;
  elapsed_s?: number;
  raw_notes?: string[];
};

export async function fetchPtStatus(): Promise<PtStatus> {
  const res = await fetch('/api/pt/status', { cache: 'no-store' });
  return res.json();
}

export async function executePt(body: {
  topology: unknown;
  cisco_configs: Record<string, string>;
  configurations?: Record<string, unknown>;
  execution_id: string;
  design_id?: string | null;
  design_name?: string | null;
}): Promise<PtExecuteResult> {
  const res = await fetch('/api/pt/execute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => null);
  if (!data || typeof data !== 'object') {
    return { execution_id: body.execution_id, ok: false, stage: 'proxy', message: 'Invalid response' };
  }
  return data as PtExecuteResult;
}

export async function listPtProjects(designId?: string | null): Promise<PtProject[]> {
  const qs = designId ? `?design_id=${encodeURIComponent(designId)}` : '';
  const res = await fetch(`/api/pt/projects${qs}`, { cache: 'no-store' });
  const data = await res.json().catch(() => ({ projects: [] }));
  return Array.isArray(data?.projects) ? data.projects : [];
}

export async function attachPtProject(executionId: string, designId: string): Promise<void> {
  await fetch(`/api/pt/projects/${encodeURIComponent(executionId)}/attach`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ design_id: designId }),
  });
}

export function ptDownloadUrl(executionId: string): string {
  return `/api/pt/projects/${encodeURIComponent(executionId)}`;
}

export function newExecutionId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID().replace(/-/g, '');
  }
  return `pt${Date.now().toString(16)}${Math.random().toString(16).slice(2, 10)}`;
}
