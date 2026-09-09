'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Film,
  Camera,
  Video,
  ImageOff,
  RefreshCw,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Search,
} from 'lucide-react';
import { getEvidenceList, type EvidenceRecord } from '@/lib/api';
import { EvidenceDetailModal } from './EvidenceDetailModal';

type KindFilter = 'ALL' | 'PHOTO' | 'VIDEO';
type StatusFilter = 'ALL' | EvidenceRecord['status'];

const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: 'ALL', label: 'All statuses' },
  { value: 'FLAGGED_REVIEW', label: 'Flagged for review' },
  { value: 'VERIFIED', label: 'Verified' },
  { value: 'ACCEPTED_EXCEPTION', label: 'Accepted exception' },
  { value: 'REJECTED', label: 'Rejected' },
  { value: 'VERIFYING', label: 'Verifying' },
  { value: 'UPLOADING', label: 'Uploading' },
  { value: 'UPLOAD_PENDING', label: 'Upload pending' },
  { value: 'DRAFT', label: 'Draft' },
];

const STATUS_BADGE: Record<string, string> = {
  VERIFIED: 'bg-emerald-900/60 text-emerald-300 border-emerald-700',
  ACCEPTED_EXCEPTION: 'bg-sky-900/60 text-sky-300 border-sky-700',
  REJECTED: 'bg-red-900/60 text-red-300 border-red-700',
  FLAGGED_REVIEW: 'bg-purple-900/60 text-purple-300 border-purple-700',
};

function statusBadgeClass(status: string): string {
  return STATUS_BADGE[status] || 'bg-slate-800/80 text-slate-300 border-slate-700';
}

/**
 * Media-first evidence verification dashboard: a visual grid of every
 * captured photo/video, filterable by kind and status, opening the same
 * EvidenceDetailModal used by the triage queue for the accept/reject
 * decision. Complements EvidenceReviewView's table-based workflow view.
 */
export function EvidenceGalleryView() {
  const [items, setItems] = useState<EvidenceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedEvidence, setSelectedEvidence] = useState<EvidenceRecord | null>(null);
  const [kindFilter, setKindFilter] = useState<KindFilter>('ALL');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL');
  const [search, setSearch] = useState('');
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  const fetchData = useCallback(async () => {
    const request = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const res = await getEvidenceList(statusFilter === 'ALL' ? undefined : { status: statusFilter });
      if (request === requestId.current) setItems(res.items || []);
    } catch (err) {
      if (request === requestId.current) setError(`Unable to load evidence: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      if (request === requestId.current) setLoading(false);
    }
  }, [statusFilter]);

  const handleRefresh = () => {
    setLoading(true);
    fetchData();
  };

  useEffect(() => {
    // Reload on filter changes and ignore responses from superseded requests.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchData();
    return () => { requestId.current += 1; };
  }, [fetchData]);

  const photoCount = items.filter((i) => i.kind === 'PHOTO').length;
  const videoCount = items.filter((i) => i.kind === 'VIDEO').length;
  const flaggedCount = items.filter((i) => i.status === 'FLAGGED_REVIEW').length;

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return items.filter((item) => {
      if (kindFilter !== 'ALL' && item.kind !== kindFilter) return false;
      if (q && !item.taskId?.toLowerCase().includes(q) && !item.evidenceId.toLowerCase().includes(q) && !item.supervisorId?.toLowerCase().includes(q)) {
        return false;
      }
      return true;
    });
  }, [items, kindFilter, search]);

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Film className="w-6 h-6 text-sky-400" />
            <h1 className="text-xl md:text-2xl font-bold tracking-wide text-white">
              Evidence Verification — Photos &amp; Videos
            </h1>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Visual media wall of every captured field proof. Click a tile to inspect geospatial and cryptographic integrity.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono border border-slate-700 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            REFRESH
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-lg border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Total Media</span>
            <ShieldCheck className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white mt-2">{items.length}</div>
        </div>
        <div className="p-4 rounded-lg border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Photos</span>
            <Camera className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-sky-400 mt-2">{photoCount}</div>
        </div>
        <div className="p-4 rounded-lg border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Videos</span>
            <Video className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-2">{videoCount}</div>
        </div>
        <div className="p-4 rounded-lg border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Flagged</span>
            <AlertTriangle className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-purple-400 mt-2">{flaggedCount}</div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-3 p-3 rounded border border-slate-800 bg-slate-900/60">
        <div className="flex items-center gap-1.5">
          {(['ALL', 'PHOTO', 'VIDEO'] as KindFilter[]).map((k) => (
            <button
              key={k}
              aria-pressed={kindFilter === k}
              onClick={() => setKindFilter(k)}
              className={`px-2.5 py-1 rounded text-[11px] font-mono font-bold transition-all border ${
                kindFilter === k
                  ? 'bg-sky-600 text-white border-sky-500'
                  : 'bg-slate-800/80 text-slate-400 border-slate-700 hover:text-slate-200'
              }`}
            >
              {k === 'ALL' ? 'All Media' : k === 'PHOTO' ? 'Photos' : 'Videos'}
            </button>
          ))}
        </div>

        <select
          aria-label="Evidence status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
          className="min-h-9 rounded border border-slate-700 bg-slate-950 px-2 text-xs font-mono text-slate-200"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>

        <div className="relative flex-1 min-w-[200px]">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            aria-label="Search evidence"
            type="text"
            placeholder="Search evidence ID, task, or supervisor..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 rounded bg-slate-950 border border-slate-800 text-xs font-mono text-slate-200 focus:outline-none focus:border-sky-500"
          />
        </div>

        <span className="text-[11px] font-mono text-slate-500 ml-auto">
          {filtered.length} of {items.length} shown
        </span>
      </div>

      {/* Media Grid */}
      {loading ? (
        <p role="status" className="text-sm text-slate-300">Loading evidence...</p>
      ) : error ? (
        <div role="alert" className="rounded border border-red-800 p-4 text-sm text-red-300">
          <p>{error}</p>
          <button type="button" onClick={handleRefresh} className="mt-2 underline">Retry loading evidence</button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="p-10 text-center rounded-lg border border-dashed border-slate-800 text-slate-500">
          <ImageOff className="w-8 h-8 mx-auto mb-2 text-slate-600" />
          <p className="text-sm">No media matches the current filters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {filtered.map((item) => (
            <button
              type="button"
              key={item.evidenceId}
              onClick={() => setSelectedEvidence(item)}
              className="group text-left rounded-lg border border-slate-800 bg-slate-900/70 overflow-hidden hover:border-sky-500/60 transition-colors"
            >
              <div className="relative aspect-video bg-slate-950 flex items-center justify-center overflow-hidden">
                {item.proofDownloadUrl ? (
                  item.kind === 'VIDEO' ? (
                    <>
                      <video
                        src={item.proofDownloadUrl}
                        muted
                        preload="metadata"
                        className="w-full h-full object-cover"
                      />
                      <div className="absolute inset-0 flex items-center justify-center bg-black/20 group-hover:bg-black/10 transition-colors">
                        <Video className="w-8 h-8 text-white/90 drop-shadow" />
                      </div>
                    </>
                  ) : (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={item.proofDownloadUrl}
                      alt={`Evidence ${item.evidenceId}`}
                      className="w-full h-full object-cover"
                    />
                  )
                ) : (
                  <div className="flex flex-col items-center gap-1.5 text-slate-600">
                    {item.kind === 'VIDEO' ? <Video className="w-8 h-8" /> : <Camera className="w-8 h-8" />}
                    <span className="text-[10px] font-mono">No preview</span>
                  </div>
                )}

                <span className={`absolute top-1.5 right-1.5 px-1.5 py-0.5 rounded text-[9px] font-mono uppercase border ${statusBadgeClass(item.status)}`}>
                  {item.status === 'VERIFIED' && <CheckCircle2 className="inline w-2.5 h-2.5 mr-0.5 -mt-0.5" />}
                  {item.status === 'REJECTED' && <XCircle className="inline w-2.5 h-2.5 mr-0.5 -mt-0.5" />}
                  {item.status === 'FLAGGED_REVIEW' && <AlertTriangle className="inline w-2.5 h-2.5 mr-0.5 -mt-0.5" />}
                  {item.status.replace('_', ' ')}
                </span>

                <span className="absolute bottom-1.5 left-1.5 px-1.5 py-0.5 rounded bg-slate-950/80 text-[9px] font-mono text-slate-300 flex items-center gap-1">
                  {item.kind === 'VIDEO' ? <Video className="w-2.5 h-2.5" /> : <Camera className="w-2.5 h-2.5" />}
                  {item.kind}
                </span>
              </div>

              <div className="p-2 space-y-0.5">
                <div className="text-[11px] font-mono font-bold text-slate-200 truncate">{item.taskId || item.evidenceId.slice(0, 12)}</div>
                <div className="text-[10px] text-slate-500 font-mono truncate">{item.supervisorId || 'Unknown supervisor'}</div>
              </div>
            </button>
          ))}
        </div>
      )}

      {selectedEvidence && (
        <EvidenceDetailModal
          evidence={selectedEvidence}
          onClose={() => setSelectedEvidence(null)}
          onReviewed={fetchData}
        />
      )}
    </div>
  );
}
