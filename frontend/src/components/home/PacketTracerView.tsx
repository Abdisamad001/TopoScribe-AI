'use client';

import { useEffect, useMemo, useState } from 'react';
import { BookOpenIcon, BroadcastIcon, DownloadSimpleIcon } from '@phosphor-icons/react';
import type { Design } from '@/lib/api';
import { fetchPtStatus, listPtProjects, ptDownloadUrl, type PtProject, type PtStatus } from '@/lib/ptClient';
import { formatDateTime } from '@/lib/formatDate';

const DOCS_URL = 'https://topos.mintlify.site/';

type Row = PtProject & { designName: string };

export default function PacketTracerView({
  designs,
  searchQuery = '',
  onOpenDesign,
}: {
  designs: Design[];
  searchQuery?: string;
  onOpenDesign?: (id: string) => void;
}) {
  const [projects, setProjects] = useState<PtProject[] | null>(null);
  const [status, setStatus] = useState<PtStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    const failSafe = window.setTimeout(() => {
      // Never leave the page on "Loading…" if the API is wedged.
      if (!cancelled) setProjects((prev) => (prev === null ? [] : prev));
    }, 2500);

    listPtProjects()
      .then((rows) => {
        if (!cancelled) setProjects(rows);
      })
      .catch(() => {
        if (!cancelled) setProjects([]);
      })
      .finally(() => window.clearTimeout(failSafe));

    // Optional hint only — must not gate the empty state.
    fetchPtStatus()
      .then((st) => {
        if (!cancelled) setStatus(st);
      })
      .catch(() => {
        if (!cancelled) {
          setStatus({ ready: false, enabled: false, detail: 'Packet Tracer status unavailable' });
        }
      });

    return () => {
      cancelled = true;
      window.clearTimeout(failSafe);
    };
  }, []);

  const designNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const d of designs) map.set(d.id, d.name);
    return map;
  }, [designs]);

  const rows: Row[] = useMemo(() => {
    const list = (projects || [])
      .filter((p) => p.ok && p.has_download)
      .map((p) => ({
        ...p,
        designName: (p.design_id && designNameById.get(p.design_id)) || 'Untitled design',
      }));
    const q = searchQuery.trim().toLowerCase();
    if (!q) return list;
    return list.filter(
      (p) =>
        p.designName.toLowerCase().includes(q) ||
        p.filename.toLowerCase().includes(q) ||
        p.execution_id.toLowerCase().includes(q),
    );
  }, [projects, designNameById, searchQuery]);

  const loading = projects === null;
  const empty = !loading && rows.length === 0;

  return (
    <div className="app-page">
      <div className="app-page__inner">
        <div className="app-page__header">
          <h2 className="app-page__title">Packet Tracer</h2>
          <p className="app-page__subtitle">
            .pkt files from Launch PT, tied to the designs that produced them.
          </p>
        </div>

        {loading && <p className="text-sm text-zinc-500">Loading…</p>}

        {empty && (
          <div className="ui-empty">
            <img src="/No-mcp.svg" alt="" className="ui-empty__art" />
            <p className="ui-empty__title">
              {searchQuery.trim() ? 'No matching Packet Tracer files' : 'No Packet Tracer files yet'}
            </p>
            <p className="ui-empty__text" style={{ maxWidth: '22rem' }}>
              {searchQuery.trim()
                ? `Nothing matches “${searchQuery.trim()}”.`
                : status?.ready === true
                  ? 'Open a design and use Launch PT on a blank canvas.'
                  : 'Launch PT from a design after Packet Tracer + MCP are set up locally.'}
            </p>
            <a
              href={DOCS_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="ui-btn-primary mt-4 px-4"
            >
              <BookOpenIcon size={14} weight="regular" />
              Open documentation
            </a>
          </div>
        )}

        {!loading && rows.length > 0 && (
          <div className="ui-grid ui-grid--3">
            {rows.map((p) => (
              <div key={p.execution_id} className="group ui-card relative p-4">
                <div className="ui-icon-box">
                  <BroadcastIcon size={16} weight="regular" className="text-teal-400" />
                </div>
                <div className="mt-6 min-w-0 pr-2">
                  <h3 className="truncate text-sm font-semibold text-white">{p.designName}</h3>
                  <p className="mt-1 truncate text-xs text-zinc-500">{p.filename}</p>
                  <p className="mt-1 text-xs text-zinc-600">{formatDateTime(p.created_at)}</p>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <a
                    href={ptDownloadUrl(p.execution_id)}
                    download={p.filename}
                    className="inline-flex items-center gap-1.5 rounded-md bg-white px-2.5 py-1.5 text-xs font-medium text-zinc-900 hover:bg-zinc-100"
                  >
                    <DownloadSimpleIcon size={12} />
                    Download .pkt
                  </a>
                  {p.design_id && onOpenDesign && (
                    <button
                      type="button"
                      onClick={() => onOpenDesign(p.design_id!)}
                      className="inline-flex items-center rounded-md border border-white/10 px-2.5 py-1.5 text-xs font-medium text-zinc-300 hover:bg-white/5 hover:text-white"
                    >
                      Open design
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
