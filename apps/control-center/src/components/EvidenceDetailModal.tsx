'use client';

import React, { useState } from 'react';
import { Camera, CheckCircle2, Lock, MapPin, XCircle } from 'lucide-react';
import { reviewEvidence, type EvidenceRecord } from '@/lib/api';
import { Modal } from './ui/Modal';

interface EvidenceDetailModalProps {
  evidence: EvidenceRecord;
  onClose: () => void;
  /** Called after a successful ACCEPT/REJECT decision so the caller can refetch its list. */
  onReviewed: () => void;
}

/**
 * Shared evidence audit dialog: media preview, geospatial + cryptographic
 * integrity grid, and the Control Officer accept/reject decision form when
 * the item is FLAGGED_REVIEW. Used by both the triage queue and the media
 * verification gallery so the two dashboards stay behaviorally identical.
 */
export function EvidenceDetailModal({ evidence, onClose, onReviewed }: EvidenceDetailModalProps) {
  const [reviewNotes, setReviewNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDecision = async (decision: 'ACCEPT' | 'REJECT') => {
    if (submitting || !reviewNotes.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await reviewEvidence(evidence.evidenceId, decision, reviewNotes.trim());
      onReviewed();
      onClose();
    } catch (err) {
      setError('Failed to submit review. Your rationale is preserved; retry the decision. ' + String(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal open onClose={onClose} title={`Evidence Audit: ${evidence.evidenceId}`} maxWidthClassName="max-w-3xl">
      <div className="space-y-6">
        {/* Media Preview Box */}
        <div className="space-y-2">
          <div className="text-xs font-mono uppercase text-slate-400">Captured Media Proof</div>
          <div className="relative bg-slate-950 border border-slate-800 rounded-lg p-3 flex flex-col items-center justify-center min-h-48">
            {evidence.proofDownloadUrl ? (
              evidence.kind === 'VIDEO' ? (
                <video
                  src={evidence.proofDownloadUrl}
                  controls
                  className="max-h-64 rounded border border-slate-800"
                />
              ) : (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={evidence.proofDownloadUrl}
                  alt="Proof derivative"
                  className="max-h-64 object-contain rounded border border-slate-800"
                />
              )
            ) : (
              <div className="text-center p-6 text-slate-400">
                <Camera className="w-10 h-10 mx-auto text-slate-600 mb-2" />
                <p className="font-mono text-xs">Simulated Presigned Evidence Media</p>
                <p className="text-[11px] text-slate-500 mt-1">
                  Permanent Railblock watermark strip embedded in proof derivative
                </p>
              </div>
            )}

            {/* Simulated Permanent Watermark Strip */}
            <div className="w-full mt-3 p-2 bg-slate-900/90 border border-sky-500/40 rounded font-mono text-[10px] text-sky-300 flex flex-wrap justify-between gap-2">
              <span>RAILBLOCK PROOF // {evidence.evidenceId.slice(0, 8)}</span>
              <span>UTC: {evidence.captureTimeUtc}</span>
              <span>
                LAT: {evidence.startLatitude?.toFixed(5)} LON:{' '}
                {evidence.startLongitude?.toFixed(5)} (±{evidence.gpsAccuracyMeters}m)
              </span>
              <span>VERDICT: {evidence.geoVerdict}</span>
            </div>
          </div>
        </div>

        {/* Geospatial and Cryptographic Audit Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
          <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 space-y-2">
            <div className="text-slate-400 font-bold uppercase flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-sky-400" /> Geospatial Verification
            </div>
            <div>Distance to Target: {evidence.distanceToTargetMeters?.toFixed(1) || '--'} m</div>
            <div>GPS Accuracy: ±{evidence.gpsAccuracyMeters} m</div>
            <div>
              Verdict:{' '}
              <span className="text-purple-400 font-bold">{evidence.geoVerdict}</span>
            </div>
            {evidence.exceptionReason && (
              <div className="mt-2 text-slate-300 font-sans italic bg-slate-900 p-2 rounded border border-slate-800">
                &quot;{evidence.exceptionReason}&quot;
              </div>
            )}
          </div>

          <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 space-y-2">
            <div className="text-slate-400 font-bold uppercase flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-emerald-400" /> Cryptographic Integrity
            </div>
            <div className="truncate">
              Original SHA-256: <span className="text-slate-300">{evidence.originalSha256 || 'Unavailable'}</span>
            </div>
            <div className="truncate">
              Proof SHA-256: <span className="text-slate-300">{evidence.proofSha256 || 'Unavailable'}</span>
            </div>
            <div>
              Ed25519 Canonical Signature:{' '}
              {evidence.ed25519Signature ? (
                <span className="text-emerald-400 font-bold">SIGNATURE PRESENT</span>
              ) : (
                <span className="text-amber-400">PENDING SIGNATURE</span>
              )}
            </div>
          </div>
        </div>

        {/* Control Officer Decision Actions (if flagged) */}
        {evidence.status === 'FLAGGED_REVIEW' && (
          <div className="p-4 bg-purple-950/30 border border-purple-800/60 rounded-lg space-y-3">
            <label htmlFor="evidence-review-notes" className="block text-xs font-bold font-mono text-purple-300 uppercase">
              Control Officer Decision & Mandatory Rationale
            </label>
            {error && <p role="alert" className="text-sm text-red-300">{error}</p>}
            <textarea
              id="evidence-review-notes"
              required
              disabled={submitting}
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              placeholder="Enter mandatory operational justification for accepting or rejecting this evidence exception..."
              className="w-full p-2.5 rounded bg-slate-950 border border-slate-700 text-slate-200 text-xs font-sans focus:outline-none focus:border-purple-500 min-h-20"
            />

            <div className="flex justify-end gap-3 pt-2">
              <button
                disabled={submitting || !reviewNotes.trim()}
                onClick={() => handleDecision('REJECT')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-red-600/80 hover:bg-red-600 disabled:opacity-50 text-white font-semibold text-xs transition-colors"
              >
                <XCircle className="w-4 h-4" /> Reject (Mandate Retake)
              </button>

              <button
                disabled={submitting || !reviewNotes.trim()}
                onClick={() => handleDecision('ACCEPT')}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-semibold text-xs transition-colors shadow"
              >
                <CheckCircle2 className="w-4 h-4" /> Accept Exception
              </button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
