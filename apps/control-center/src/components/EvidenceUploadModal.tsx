'use client';

import React, { useEffect, useRef, useState } from 'react';
import {
  Camera,
  Video,
  Upload,
  CheckCircle2,
  AlertTriangle,
  Lock,
} from 'lucide-react';
import { simulateEvidenceUpload, type EvidenceRecord } from '@/lib/api';
import { Modal } from './ui/Modal';

interface EvidenceUploadModalProps {
  onClose: () => void;
  onUploaded: (evidence: EvidenceRecord) => void;
}

export function EvidenceUploadModal({ onClose, onUploaded }: EvidenceUploadModalProps) {
  const [taskId, setTaskId] = useState('ENG-1001');
  const [stepId, setStepId] = useState('stp-ENG-1001-1');
  const [kind, setKind] = useState<'PHOTO' | 'VIDEO'>('PHOTO');
  const [scenario, setScenario] = useState<'COMPLIANT' | 'FLAGGED_GPS' | 'FLAGGED_ACCURACY'>('COMPLIANT');
  const [exceptionReason, setExceptionReason] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileBase64, setFileBase64] = useState<string | null>(null);
  const [readingFile, setReadingFile] = useState(false);
  const readerRef = useRef<FileReader | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const submittingRef = useRef(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ evidence: EvidenceRecord; manifest: Record<string, unknown> } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => () => { readerRef.current?.abort(); }, []);

  const clearFile = () => {
    readerRef.current?.abort();
    readerRef.current = null;
    setSelectedFile(null);
    setFileBase64(null);
    setReadingFile(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    clearFile();
    setError(null);
    if (!file) return;
    setSelectedFile(file);
    const allowed = kind === 'PHOTO' ? ['image/jpeg'] : ['video/mp4'];
    if (!allowed.includes(file.type) || file.size === 0) {
      setError('Choose a non-empty JPEG photo or MP4 video matching the selected media kind.');
      return;
    }
    setReadingFile(true);
    const reader = new FileReader();
    readerRef.current = reader;
    reader.onload = () => {
      if (readerRef.current !== reader) return;
      const base64String = (reader.result as string).split(',')[1];
      setFileBase64(base64String);
      setReadingFile(false);
    };
    reader.onerror = () => {
      if (readerRef.current !== reader) return;
      setReadingFile(false);
      setError('Unable to read this file. Choose the file again or choose another file.');
    };
    reader.readAsDataURL(file);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submittingRef.current || readingFile || (selectedFile && !fileBase64)) return;
    if (scenario !== 'COMPLIANT' && !exceptionReason.trim()) {
      setError('Enter the field exception reason before submitting.');
      return;
    }
    submittingRef.current = true;
    setLoading(true);
    setError(null);
    try {
      const res = await simulateEvidenceUpload({
        taskId,
        stepId: stepId.trim() || undefined,
        kind,
        scenario,
        exceptionReason: scenario !== 'COMPLIANT' ? exceptionReason.trim() : undefined,
        mediaBase64: fileBase64 || undefined,
      });
      setResult(res);
      onUploaded(res.evidence);
    } catch (err) {
      setError(String(err));
    } finally {
      submittingRef.current = false;
      setLoading(false);
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="Upload Field Evidence (Live Verification Simulation)"
      maxWidthClassName="max-w-2xl"
    >
      <div className="space-y-6">
        {result ? (
          <div className="space-y-4" role="status">
            <div
              className={`p-4 rounded-lg border flex items-start gap-3 ${
                result.evidence.status === 'VERIFIED'
                  ? 'bg-emerald-950/40 border-emerald-700/60 text-emerald-300'
                  : 'bg-purple-950/40 border-purple-700/60 text-purple-300'
              }`}
            >
              {result.evidence.status === 'VERIFIED' ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-purple-400 shrink-0 mt-0.5" />
              )}
              <div className="space-y-1">
                <div className="font-bold text-sm">
                  {result.evidence.status === 'VERIFIED'
                    ? 'Evidence Verified & Signed'
                    : 'Evidence Flagged for Control Officer Review'}
                </div>
                <div className="text-xs text-slate-300">
                  ID: <span className="font-mono">{result.evidence.evidenceId}</span> | Geo verdict:{' '}
                  <span className="font-semibold">{result.evidence.geoVerdict}</span> | Distance:{' '}
                  <span className="font-mono">
                    {result.evidence.distanceToTargetMeters != null
                      ? `${result.evidence.distanceToTargetMeters.toFixed(1)}m`
                      : 'N/A'}
                  </span>
                </div>
                {result.evidence.reviewNotes && (
                  <div className="text-xs text-slate-400 italic mt-1">
                    Notes: {result.evidence.reviewNotes}
                  </div>
                )}
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-lg p-3 text-xs space-y-2 font-mono text-slate-300">
              <div className="flex items-center justify-between text-slate-400 border-b border-slate-800 pb-1.5">
                <span className="flex items-center gap-1.5 font-bold">
                  <Lock className="w-3.5 h-3.5 text-sky-400" />
                  Canonical Manifest (Ed25519 Signed)
                </span>
                <span>Version: 1.0</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div>
                  <span className="text-slate-500">SHA-256 Proof:</span>
                  <div className="truncate text-slate-300 font-mono">
                    {result.evidence.proofSha256 || 'N/A'}
                  </div>
                </div>
                <div>
                  <span className="text-slate-500">Signature:</span>
                  <div className="truncate text-slate-300 font-mono">
                    {result.evidence.ed25519Signature || 'Signature unavailable'}
                  </div>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => { setResult(null); clearFile(); setError(null); }}
                className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono border border-slate-700 transition-colors"
              >
                Upload Another
              </button>
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-1.5 rounded bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div role="alert" className="p-3 rounded bg-red-950/60 border border-red-800 text-red-300 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label htmlFor="evidence-task" className="text-xs font-medium text-slate-300">Target Maintenance Task</label>
                <select
                  id="evidence-task"
                  disabled={loading}
                  value={taskId}
                  onChange={(e) => {
                    const tid = e.target.value;
                    setTaskId(tid);
                    if (tid === 'ENG-1001') setStepId('stp-ENG-1001-1');
                    else if (tid === 'SNT-2002') setStepId('stp-SNT-2002-1');
                    else if (tid === 'TRD-3001') setStepId('stp-TRD-3001-1');
                    else if (tid === 'ENG-1004') setStepId('stp-ENG-1004-1');
                    else setStepId('');
                  }}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white focus:ring-1 focus:ring-sky-500 font-mono"
                >
                  <option value="ENG-1001">ENG-1001 (Track Tamping GZB-DER UP)</option>
                  <option value="SNT-2002">SNT-2002 (Dadri Yard Point Machine 14A)</option>
                  <option value="TRD-3001">TRD-3001 (OHE Inspection Feeder GZB)</option>
                  <option value="ENG-1004">ENG-1004 (Khurja Turnout 102B Renewal)</option>
                </select>
              </div>

              <div className="space-y-1">
                <label htmlFor="evidence-step" className="text-xs font-medium text-slate-300">Macro Work Step ID</label>
                <input
                  id="evidence-step"
                  disabled={loading}
                  type="text"
                  value={stepId}
                  onChange={(e) => setStepId(e.target.value)}
                  placeholder="e.g. stp-ENG-1001-1"
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white focus:ring-1 focus:ring-sky-500 font-mono"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-300">Media Kind</label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={loading}
                    aria-pressed={kind === 'PHOTO'}
                    onClick={() => { setKind('PHOTO'); clearFile(); setError(null); }}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded text-xs border transition-colors ${
                      kind === 'PHOTO'
                        ? 'bg-sky-950/60 border-sky-600 text-sky-300 font-semibold'
                        : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Camera className="w-3.5 h-3.5" />
                    PHOTO
                  </button>
                  <button
                    type="button"
                    disabled={loading}
                    aria-pressed={kind === 'VIDEO'}
                    onClick={() => { setKind('VIDEO'); clearFile(); setError(null); }}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded text-xs border transition-colors ${
                      kind === 'VIDEO'
                        ? 'bg-sky-950/60 border-sky-600 text-sky-300 font-semibold'
                        : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Video className="w-3.5 h-3.5" />
                    VIDEO
                  </button>
                </div>
              </div>

              <div className="space-y-1">
                <label htmlFor="evidence-scenario" className="text-xs font-medium text-slate-300">Test Verification Scenario</label>
                <select
                  id="evidence-scenario"
                  disabled={loading}
                  value={scenario}
                  onChange={(e) => setScenario(e.target.value as typeof scenario)}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white focus:ring-1 focus:ring-sky-500 font-mono"
                >
                  <option value="COMPLIANT">Compliant GPS (&lt;100m, Accuracy &lt;15m) → VERIFIED</option>
                  <option value="FLAGGED_GPS">Exceeded Radius (147m &gt; 100m) → FLAGGED_REVIEW</option>
                  <option value="FLAGGED_ACCURACY">Poor GPS Accuracy (65m &gt; 50m) → FLAGGED_REVIEW</option>
                </select>
              </div>
            </div>

            {scenario !== 'COMPLIANT' && (
              <div className="space-y-1">
                <label htmlFor="evidence-exception" className="text-xs font-medium text-amber-300 flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  Field Exception Reason (Required for Flagged Scenarios)
                </label>
                <textarea
                  id="evidence-exception"
                  required
                  disabled={loading}
                  value={exceptionReason}
                  onChange={(e) => setExceptionReason(e.target.value)}
                  placeholder="e.g. Electrical feeder standoff safety line prohibited standing within 100m target zone."
                  rows={2}
                  className="w-full bg-slate-900 border border-amber-900/60 rounded px-2.5 py-1.5 text-xs text-white focus:ring-1 focus:ring-amber-500"
                />
              </div>
            )}

            <div className="space-y-1">
              <label htmlFor="evidence-file" className="text-xs font-medium text-slate-300 flex items-center justify-between">
                <span>Upload Media File (Optional — uses demo sample when omitted)</span>
                {selectedFile && <span className="text-[11px] text-sky-400 font-mono">{selectedFile.name}</span>}
              </label>
              <input
                ref={fileInputRef}
                id="evidence-file"
                disabled={loading}
                type="file"
                accept={kind === 'PHOTO' ? 'image/jpeg' : 'video/mp4'}
                onChange={handleFileChange}
                className="w-full text-xs text-slate-400 file:mr-3 file:py-1 file:px-2.5 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-slate-800 file:text-slate-200 hover:file:bg-slate-700 cursor-pointer border border-slate-800 rounded p-1"
              />
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-slate-800">
              <p className="text-[11px] text-slate-400">
                Runs authoritative 5-stage verification &amp; Ed25519 cryptographic manifest signing.
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono border border-slate-700 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading || readingFile || Boolean(selectedFile && !fileBase64)}
                  className="flex items-center gap-1.5 px-4 py-1.5 rounded bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-xs font-semibold shadow transition-colors"
                >
                  <Upload className="w-3.5 h-3.5" />
                  {loading ? 'Verifying...' : readingFile ? 'Reading file...' : 'Submit Evidence'}
                </button>
              </div>
            </div>
          </form>
        )}
      </div>
    </Modal>
  );
}
