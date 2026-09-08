'use client';

import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  AlertTriangle,
  FileCheck2,
  CheckCircle2,
  Camera,
  Video,
  Users,
  Plus,
  RefreshCw,
  Lock,
} from 'lucide-react';
import {
  getEvidenceList,
  getEvidenceDetails,
  getSupervisorsList,
  createSupervisorAccount,
  updateSupervisorAreas,
  type EvidenceRecord,
  type SupervisorRecord,
} from '@/lib/api';
import { Modal } from './ui/Modal';
import { EvidenceDetailModal } from './EvidenceDetailModal';

export function EvidenceReviewView() {
  const [activeTab, setActiveTab] = useState<'flagged' | 'timeline' | 'supervisors'>('flagged');
  const [evidenceItems, setEvidenceItems] = useState<EvidenceRecord[]>([]);
  const [supervisors, setSupervisors] = useState<SupervisorRecord[]>([]);
  const [selectedEvidence, setSelectedEvidence] = useState<EvidenceRecord | null>(null);
  const [loading, setLoading] = useState(true);

  // Supervisor creation state
  const [showAddSupervisor, setShowAddSupervisor] = useState(false);
  const [newEmpId, setNewEmpId] = useState('');
  const [newName, setNewName] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newSections, setNewSections] = useState('SEC_KRJ_SMQ, GZB-ALJN');

  const fetchData = async () => {
    try {
      const [evRes, supRes] = await Promise.all([
        getEvidenceList(),
        getSupervisorsList(),
      ]);
      setEvidenceItems(evRes.items || []);
      setSupervisors(supRes.items || []);
    } catch (err) {
      console.error('Failed to fetch evidence data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    setLoading(true);
    fetchData();
  };

  useEffect(() => {
    // Initial load on mount; fetchData's setState calls resolve after the
    // Promise.all await, not synchronously within this effect body.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchData();
  }, []);

  const flaggedItems = evidenceItems.filter(
    (item) => item.status === 'FLAGGED_REVIEW' || item.status === 'DRAFT'
  );
  const verifiedItems = evidenceItems.filter(
    (item) => item.status === 'VERIFIED' || item.status === 'ACCEPTED_EXCEPTION'
  );

  const handleSelectEvidence = async (item: EvidenceRecord) => {
    try {
      const details = await getEvidenceDetails(item.evidenceId);
      setSelectedEvidence(details);
    } catch {
      setSelectedEvidence(item);
    }
  };

  const handleCreateSupervisor = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEmpId || !newName || !newPassword) return;
    try {
      const sections = newSections.split(',').map((s) => s.trim()).filter(Boolean);
      await createSupervisorAccount({
        employeeId: newEmpId,
        name: newName,
        password: newPassword,
        assignedSectionCodes: sections,
      });
      setShowAddSupervisor(false);
      setNewEmpId('');
      setNewName('');
      setNewPassword('');
      await fetchData();
    } catch (err) {
      alert('Failed to create supervisor: ' + String(err));
    }
  };

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-6">
      {/* Header & Stats */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-sky-400" />
            <h1 className="text-xl md:text-2xl font-bold tracking-wide text-white">
              Field Evidence & Verification Triage
            </h1>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Authoritative geotagged media review, cryptographic signature audits, and supervisor jurisdiction.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            className="flex items-center gap-2 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono border border-slate-700 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            REFRESH
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div
          onClick={() => setActiveTab('flagged')}
          className={`cursor-pointer p-4 rounded-lg border transition-all ${
            activeTab === 'flagged'
              ? 'bg-purple-950/40 border-purple-600/80 ring-1 ring-purple-500'
              : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Flagged Exceptions</span>
            <AlertTriangle className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-purple-400 mt-2">
            {flaggedItems.length}
          </div>
          <p className="text-xs text-slate-400 mt-1">Requires Control Officer approval</p>
        </div>

        <div
          onClick={() => setActiveTab('timeline')}
          className={`cursor-pointer p-4 rounded-lg border transition-all ${
            activeTab === 'timeline'
              ? 'bg-emerald-950/40 border-emerald-600/80 ring-1 ring-emerald-500'
              : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Verified Evidence</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-2">
            {verifiedItems.length}
          </div>
          <p className="text-xs text-slate-400 mt-1">Server signed & tamper-proof</p>
        </div>

        <div
          onClick={() => setActiveTab('supervisors')}
          className={`cursor-pointer p-4 rounded-lg border transition-all ${
            activeTab === 'supervisors'
              ? 'bg-sky-950/40 border-sky-600/80 ring-1 ring-sky-500'
              : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase text-slate-400">Active Supervisors</span>
            <Users className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-sky-400 mt-2">
            {supervisors.length}
          </div>
          <p className="text-xs text-slate-400 mt-1">Authorized section rosters</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 gap-6">
        <button
          onClick={() => setActiveTab('flagged')}
          className={`pb-3 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'flagged'
              ? 'border-purple-500 text-purple-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <AlertTriangle className="w-4 h-4" />
          Flagged Review Queue ({flaggedItems.length})
        </button>

        <button
          onClick={() => setActiveTab('timeline')}
          className={`pb-3 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'timeline'
              ? 'border-emerald-500 text-emerald-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <FileCheck2 className="w-4 h-4" />
          Evidence Audit Timeline
        </button>

        <button
          onClick={() => setActiveTab('supervisors')}
          className={`pb-3 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'supervisors'
              ? 'border-sky-500 text-sky-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Users className="w-4 h-4" />
          Supervisor Administration
        </button>
      </div>

      {/* Tab 1: Flagged Queue */}
      {activeTab === 'flagged' && (
        <div className="space-y-4">
          {flaggedItems.length === 0 ? (
            <div className="p-8 text-center rounded-lg border border-slate-800 bg-slate-900/40 text-slate-400">
              <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
              <p className="font-semibold text-white">No Flagged Items in Queue</p>
              <p className="text-xs mt-1">All submitted evidence satisfies authoritative geo-radius and integrity rules.</p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-900/60">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-800/80 text-slate-400 font-mono uppercase border-b border-slate-700">
                  <tr>
                    <th className="p-3">Evidence ID</th>
                    <th className="p-3">Task / Step</th>
                    <th className="p-3">Supervisor</th>
                    <th className="p-3">Geo Verdict</th>
                    <th className="p-3">Distance</th>
                    <th className="p-3">Exception Rationale</th>
                    <th className="p-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 text-slate-200 font-sans">
                  {flaggedItems.map((item) => (
                    <tr key={item.evidenceId} className="hover:bg-slate-800/40 transition-colors">
                      <td className="p-3 font-mono text-purple-400 flex items-center gap-1.5">
                        {item.kind === 'VIDEO' ? <Video className="w-3.5 h-3.5" /> : <Camera className="w-3.5 h-3.5" />}
                        {item.evidenceId.slice(0, 8)}...
                      </td>
                      <td className="p-3">
                        <div className="font-semibold">{item.taskId}</div>
                        <div className="text-[11px] text-slate-400">{item.stepId}</div>
                      </td>
                      <td className="p-3 font-mono">{item.supervisorId}</td>
                      <td className="p-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-purple-900/50 text-purple-300 border border-purple-700">
                          {item.geoVerdict}
                        </span>
                      </td>
                      <td className="p-3 font-mono">
                        {item.distanceToTargetMeters != null
                          ? `${item.distanceToTargetMeters.toFixed(1)} m`
                          : '--'}
                      </td>
                      <td className="p-3 max-w-xs truncate text-slate-300">
                        {item.exceptionReason || item.reviewNotes || 'Outside designated radius'}
                      </td>
                      <td className="p-3 text-right">
                        <button
                          onClick={() => handleSelectEvidence(item)}
                          className="px-2.5 py-1 rounded bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs transition-colors"
                        >
                          Review & Decide
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Timeline */}
      {activeTab === 'timeline' && (
        <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-900/60">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-800/80 text-slate-400 font-mono uppercase border-b border-slate-700">
              <tr>
                <th className="p-3">Status</th>
                <th className="p-3">Evidence ID</th>
                <th className="p-3">Task ID</th>
                <th className="p-3">Supervisor</th>
                <th className="p-3">Capture Time (UTC)</th>
                <th className="p-3">Ed25519 Signature</th>
                <th className="p-3 text-right">Audit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-200">
              {evidenceItems.map((item) => (
                <tr key={item.evidenceId} className="hover:bg-slate-800/40 transition-colors">
                  <td className="p-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase ${
                        item.status === 'VERIFIED'
                          ? 'bg-emerald-900/50 text-emerald-300 border border-emerald-700'
                          : item.status === 'ACCEPTED_EXCEPTION'
                          ? 'bg-sky-900/50 text-sky-300 border border-sky-700'
                          : item.status === 'REJECTED'
                          ? 'bg-red-900/50 text-red-300 border border-red-700'
                          : 'bg-purple-900/50 text-purple-300 border border-purple-700'
                      }`}
                    >
                      {item.status}
                    </span>
                  </td>
                  <td className="p-3 font-mono text-slate-300">{item.evidenceId.slice(0, 12)}...</td>
                  <td className="p-3 font-semibold">{item.taskId}</td>
                  <td className="p-3 font-mono">{item.supervisorId}</td>
                  <td className="p-3 font-mono text-slate-400">{item.captureTimeUtc}</td>
                  <td className="p-3 font-mono text-slate-400">
                    {item.ed25519Signature ? (
                      <span className="text-emerald-400 flex items-center gap-1">
                        <Lock className="w-3 h-3" /> Signed
                      </span>
                    ) : (
                      'Pending'
                    )}
                  </td>
                  <td className="p-3 text-right">
                    <button
                      onClick={() => handleSelectEvidence(item)}
                      className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-sky-400 font-mono text-xs border border-slate-700"
                    >
                      Audit Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab 3: Supervisors */}
      {activeTab === 'supervisors' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-base font-bold text-white">Supervisor Directory & Section Jurisdictions</h2>
            <button
              onClick={() => setShowAddSupervisor(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-sky-600 hover:bg-sky-500 text-white font-semibold text-xs shadow transition-colors"
            >
              <Plus className="w-4 h-4" /> Add Supervisor
            </button>
          </div>

          <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-900/60">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-800/80 text-slate-400 font-mono uppercase border-b border-slate-700">
                <tr>
                  <th className="p-3">Employee ID</th>
                  <th className="p-3">Name</th>
                  <th className="p-3">Authorized Railway Sections</th>
                  <th className="p-3">Status</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-200">
                {supervisors.map((sup) => (
                  <tr key={sup.userId} className="hover:bg-slate-800/40 transition-colors">
                    <td className="p-3 font-mono text-sky-400 font-bold">{sup.employeeId}</td>
                    <td className="p-3 font-semibold">{sup.name}</td>
                    <td className="p-3">
                      <div className="flex flex-wrap gap-1">
                        {sup.assignedSections?.length ? (
                          sup.assignedSections.map((sec: string) => (
                            <span
                              key={sec}
                              className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono text-[10px] text-slate-300"
                            >
                              {sec}
                            </span>
                          ))
                        ) : (
                          <span className="text-slate-500 italic">No sections assigned</span>
                        )}
                      </div>
                    </td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-900/50 text-emerald-300 border border-emerald-700">
                        ACTIVE
                      </span>
                    </td>
                    <td className="p-3 text-right">
                      <button
                        onClick={async () => {
                          const input = prompt(
                            `Update sections for ${sup.name} (comma-separated):`,
                            sup.assignedSections?.join(', ') || ''
                          );
                          if (input !== null) {
                            const list = input.split(',').map((s) => s.trim()).filter(Boolean);
                            await updateSupervisorAreas(sup.userId, list);
                            await fetchData();
                          }
                        }}
                        className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs border border-slate-700"
                      >
                        Edit Sections
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Review / Audit Modal */}
      {selectedEvidence && (
        <EvidenceDetailModal
          evidence={selectedEvidence}
          onClose={() => setSelectedEvidence(null)}
          onReviewed={fetchData}
        />
      )}

      {/* Add Supervisor Modal */}
      {showAddSupervisor && (
        <Modal
          open={showAddSupervisor}
          onClose={() => setShowAddSupervisor(false)}
          title="Create Supervisor Account"
          maxWidthClassName="max-w-md"
        >
          <form onSubmit={handleCreateSupervisor} className="space-y-4">
            <div className="space-y-3 text-xs font-sans">
              <div>
                <label className="block text-slate-400 mb-1">Employee ID</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. EMP906"
                  value={newEmpId}
                  onChange={(e) => setNewEmpId(e.target.value)}
                  className="w-full p-2 rounded bg-slate-950 border border-slate-700 text-white font-mono"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Full Name & Designation</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Vikram Singh (SSE/P-Way)"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="w-full p-2 rounded bg-slate-950 border border-slate-700 text-white"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Initial Password</label>
                <input
                  type="password"
                  required
                  placeholder="Min 8 characters"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full p-2 rounded bg-slate-950 border border-slate-700 text-white"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Assigned Section Codes (comma-separated)</label>
                <input
                  type="text"
                  placeholder="SEC_KRJ_SMQ, GZB-ALJN"
                  value={newSections}
                  onChange={(e) => setNewSections(e.target.value)}
                  className="w-full p-2 rounded bg-slate-950 border border-slate-700 text-white font-mono"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setShowAddSupervisor(false)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300 text-xs"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 rounded bg-sky-600 hover:bg-sky-500 text-white font-semibold text-xs"
              >
                Create Account
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
