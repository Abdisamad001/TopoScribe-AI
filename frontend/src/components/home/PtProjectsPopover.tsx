'use client';

import { useEffect, useState } from 'react';
import { BroadcastIcon, DownloadSimpleIcon, XIcon } from '@phosphor-icons/react';
import { listPtProjects, ptDownloadUrl, type PtProject } from '@/lib/ptClient';

function formatWhen(iso: string): string {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString();
  } catch {
    return iso;
  }
}

export default function PtProjectsPopover({
  designId,
  designName,
  onClose,
}: {
  designId: string;
  designName: string;
  onClose: () => void;
}) {
  const [projects, setProjects] = useState<PtProject[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    const failSafe = window.setTimeout(() => {
      if (!cancelled) setProjects((prev) => (prev === null ? [] : prev));
    }, 2500);
    listPtProjects(designId)
      .then((rows) => {
        if (!cancelled) setProjects(rows);
      })
      .catch(() => {
        if (!cancelled) setProjects([]);
      })
      .finally(() => window.clearTimeout(failSafe));
    return () => {
      cancelled = true;
      window.clearTimeout(failSafe);
    };
  }, [designId]);

  return (
    <div className="ui-backdrop" onClick={onClose}>
      <div className="ui-dialog" style={{ maxWidth: '28rem' }} onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold tracking-tight text-white">Packet Tracer projects</h3>
            <p className="mt-1 text-sm text-zinc-400 truncate">{designName}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-md p-1.5 text-zinc-400 hover:bg-white/5 hover:text-white"
          >
            <XIcon size={16} />
          </button>
        </div>

        <div className="mt-4 max-h-72 space-y-2 overflow-y-auto">
          {projects === null && <p className="text-sm text-zinc-500">Loading…</p>}
          {projects && projects.length === 0 && (
            <p className="text-sm text-zinc-500">No saved Packet Tracer runs for this design.</p>
          )}
          {projects?.map((p) => (
            <div
              key={p.execution_id}
              className="flex items-center justify-between gap-3 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2.5"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-1.5 text-xs font-medium text-white">
                  <BroadcastIcon size={12} className="shrink-0 text-teal-400" />
                  <span className="truncate">{p.filename}</span>
                </div>
                <p className="mt-0.5 text-[11px] text-zinc-500">
                  {formatWhen(p.created_at)}
                  {' · '}
                  <span className={p.ok ? 'text-teal-400' : 'text-amber-300'}>
                    {p.ok ? 'Success' : 'Failed'}
                  </span>
                </p>
              </div>
              {p.has_download && (
                <a
                  href={ptDownloadUrl(p.execution_id)}
                  download={p.filename}
                  onClick={(e) => e.stopPropagation()}
                  className="inline-flex shrink-0 items-center gap-1 rounded-md border border-white/10 px-2 py-1 text-[11px] font-medium text-zinc-300 hover:bg-white/5 hover:text-white"
                >
                  <DownloadSimpleIcon size={12} />
                  .pkt
                </a>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
