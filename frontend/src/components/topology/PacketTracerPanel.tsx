'use client';

import React from 'react';
import { DownloadSimpleIcon, XIcon, BroadcastIcon } from '@phosphor-icons/react';
import type { PtExecuteResult } from '@/lib/ptClient';
import { ptDownloadUrl } from '@/lib/ptClient';

export default function PacketTracerPanel({
  isOpen,
  onClose,
  running,
  preparing,
  elapsedSec,
  result,
  errorMessage,
}: {
  isOpen: boolean;
  onClose: () => void;
  running: boolean;
  preparing: boolean;
  elapsedSec: number;
  result: PtExecuteResult | null;
  errorMessage?: string | null;
}) {
  if (!isOpen) return null;

  const devicesOk = (result?.devices || []).filter((d) => d.ok).length;
  const devicesTotal = (result?.devices || []).length;
  const linksOk = (result?.links || []).filter((l) => l.ok).length;
  const linksTotal = (result?.links || []).length;
  const cli = result?.cli_lines || [];
  const cliOk = cli.filter((c) => c.status === 'ok').length;
  const rejected = cli.filter((c) => c.status !== 'ok');
  const downloadId = result?.project_download_id || result?.execution_id;
  const filename = result?.project_filename || (downloadId ? `${downloadId}.pkt` : '');

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4 backdrop-blur-md">
      <div className="report-modal" style={{ maxWidth: '42rem' }}>
        <div className="report-modal__header">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-teal-500/10 p-2">
              <BroadcastIcon size={18} weight="regular" className="text-teal-400" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-white">Packet Tracer</h2>
              <p className="text-[11px] text-zinc-500">Local deploy results</p>
            </div>
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

        <div className="report-modal__body space-y-4 text-sm text-zinc-300">
          {preparing && (
            <p className="text-zinc-400">Preparing configuration… {elapsedSec}s</p>
          )}
          {running && !preparing && (
            <p className="text-zinc-400">Running in Packet Tracer… {elapsedSec}s</p>
          )}

          {!running && !preparing && (
            <>
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Overall status</p>
                <p className={`mt-1 font-medium ${result?.ok ? 'text-teal-400' : 'text-amber-300'}`}>
                  {result?.ok ? 'Success' : 'Failed'}
                  {result?.stage ? ` · ${result.stage}` : ''}
                </p>
                {(errorMessage || result?.message) && (
                  <p className="mt-1 text-xs text-zinc-400">{errorMessage || result?.message}</p>
                )}
                {typeof result?.elapsed_s === 'number' && (
                  <p className="mt-1 text-xs text-zinc-500">Duration: {result.elapsed_s}s</p>
                )}
              </div>

              {(devicesTotal > 0 || linksTotal > 0) && (
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
                    <p className="text-[11px] text-zinc-500">Devices</p>
                    <p className="mt-0.5 text-white">{devicesOk}/{devicesTotal} created</p>
                  </div>
                  <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
                    <p className="text-[11px] text-zinc-500">Links</p>
                    <p className="mt-0.5 text-white">{linksOk}/{linksTotal} created</p>
                  </div>
                </div>
              )}

              {cli.length > 0 && (
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">
                    CLI · {cliOk} accepted · {rejected.length} rejected
                  </p>
                  {rejected.length === 0 ? (
                    <p className="mt-1 text-xs text-zinc-500">No rejected lines.</p>
                  ) : (
                    <ul className="mt-2 max-h-40 space-y-1.5 overflow-y-auto rounded-lg border border-white/10 bg-black/30 p-2 font-mono text-[11px]">
                      {rejected.map((line, i) => (
                        <li key={`${line.device_id}-${i}`} className="text-amber-200/90">
                          <span className="text-zinc-500">[{line.device_id}]</span> {line.line}
                          {line.impact ? (
                            <span className="ml-2 text-zinc-500">({line.impact})</span>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {(result?.pings || []).length > 0 && (
                <div>
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
                    Connectivity tests
                  </p>
                  <div className="overflow-x-auto rounded-lg border border-white/10">
                    <table className="w-full min-w-[28rem] text-left text-[11px]">
                      <thead className="bg-white/[0.04] text-zinc-500">
                        <tr>
                          <th className="px-2 py-1.5 font-medium">Source</th>
                          <th className="px-2 py-1.5 font-medium">Destination</th>
                          <th className="px-2 py-1.5 font-medium">Attempts</th>
                          <th className="px-2 py-1.5 font-medium">Status</th>
                          <th className="px-2 py-1.5 font-medium">Message</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(result?.pings || []).map((p, i) => (
                          <tr key={`${p.source}-${p.destination}-${i}`} className="border-t border-white/5">
                            <td className="px-2 py-1.5 text-zinc-300">{p.source}</td>
                            <td className="px-2 py-1.5 text-zinc-300">{p.destination}</td>
                            <td className="px-2 py-1.5 text-zinc-400">{p.attempts}</td>
                            <td
                              className={`px-2 py-1.5 font-medium ${
                                p.final_status === 'pass' ? 'text-teal-400' : 'text-red-400'
                              }`}
                            >
                              {p.final_status}
                            </td>
                            <td className="max-w-[14rem] truncate px-2 py-1.5 text-zinc-500" title={(p.messages || [])[0]}>
                              {(p.messages || [])[0] || '—'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {downloadId && result?.ok && (
                <div className="flex items-center justify-between gap-3 rounded-lg border border-white/10 bg-white/[0.03] p-3">
                  <div className="min-w-0">
                    <p className="text-[11px] text-zinc-500">Saved project</p>
                    <p className="truncate text-xs text-white">{filename}</p>
                  </div>
                  <a
                    href={ptDownloadUrl(downloadId)}
                    download={filename}
                    className="inline-flex shrink-0 items-center gap-1.5 rounded-md bg-white px-2.5 py-1.5 text-xs font-medium text-zinc-900 hover:bg-zinc-100"
                  >
                    <DownloadSimpleIcon size={13} />
                    Download .pkt
                  </a>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
