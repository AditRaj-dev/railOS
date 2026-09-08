'use client';

import React, { useState, useMemo } from 'react';
import { useRailOSStore } from '../store/railosStore';
import { useMaintenanceTasks } from '../lib/queries';
import { DepartmentBadge, RiskBadge } from './RailwayComponents';
import { 
  Search, 
  Filter, 
  ArrowUpDown, 
  Wrench, 
  X, 
  Clock, 
  MapPin, 
  ShieldCheck, 
  FileText, 
  AlertOctagon,
  Database
} from 'lucide-react';
import { MaintenanceTask, Department, DefectSeverity, PriorityBand } from '../types/railos';

function mapServerTask(item: any): MaintenanceTask {
  const deptMap: Record<string, Department> = {
    ENGG: 'CIVIL',
    CIVIL: 'CIVIL',
    SNT: 'S_AND_T',
    S_AND_T: 'S_AND_T',
    TRD: 'TRD',
    OPERATING: 'OPERATING',
  };
  const department: Department = deptMap[item.department] || 'CIVIL';
  const sevNum = typeof item.severity === 'number' ? item.severity : 5;
  const severity: DefectSeverity = sevNum >= 8 ? 'CRITICAL' : sevNum >= 5 ? 'HIGH' : 'MEDIUM';
  const riskScore = Math.min(100, sevNum * 10);
  const priorityBand: PriorityBand = sevNum >= 8 ? 'P1_SAFETY_CRITICAL' : sevNum >= 5 ? 'P2_DEFERRED_RISK' : 'P3_ROUTINE';

  return {
    id: item.taskId || item.id,
    taskCode: item.taskId || item.taskCode || 'TSK-00',
    department,
    title: item.title || `${item.taskType || 'Track Maintenance'} on ${item.assetId || 'Corridor'}`,
    assetId: item.assetId || 'AST-01',
    assetName: item.assetName || item.assetId || 'Asset Section',
    sectionId: item.sectionId || 'SEC-01',
    sectionName: item.sectionName || item.sectionId || 'Ghaziabad – Aligarh Section',
    trackId: (item.track === 'UP' || item.track === 'DOWN') ? item.track : 'BOTH',
    severity,
    riskScore,
    priorityBand,
    priorityScore: riskScore,
    dueDate: item.dueMinute ? `T+${Math.round(item.dueMinute / 60)}h` : 'Today',
    estimatedMinutes: item.estimatedDuration || 120,
    blockRequirement: (item.blockType === 'POWER' || item.blockType === 'INTEGRATED') ? item.blockType : 'TRAFFIC',
    status: item.status || 'PENDING',
    crewRequired: item.crewRequired || 12,
    specialMachine: item.machineType || undefined,
    isolationRequired: Boolean(item.requiresPTW || item.oheElementarySection),
    reasons: item.reasons || [
      `Criticality index: ${item.criticality || 5}/10, overdue backlog: ${item.overdueDays || 0} days`,
      item.machineType ? `Deployment machinery: ${item.machineType}` : 'Manual gang deployment required'
    ]
  };
}

export const MaintenanceView: React.FC = () => {
  const { tasks, selectedTaskId, setSelectedTaskId } = useRailOSStore();
  const { data: serverTasksResponse, isLoading: isLoadingServerTasks } = useMaintenanceTasks();

  const isLiveServer = Boolean(serverTasksResponse?.tasks && Array.isArray(serverTasksResponse.tasks) && serverTasksResponse.tasks.length > 0);

  const effectiveTasks: MaintenanceTask[] = useMemo(() => {
    if (isLiveServer && serverTasksResponse?.tasks) {
      return (serverTasksResponse.tasks as any[]).map(mapServerTask);
    }
    return tasks;
  }, [isLiveServer, serverTasksResponse, tasks]);

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDept, setSelectedDept] = useState<'ALL' | 'CIVIL' | 'S_AND_T' | 'TRD'>('ALL');
  const [selectedSeverity, setSelectedSeverity] = useState<'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM'>('ALL');
  const [sortField, setSortField] = useState<'riskScore' | 'priorityScore' | 'estimatedMinutes'>('riskScore');
  const [sortAsc, setSortAsc] = useState(false);

  const selectedTask = effectiveTasks.find(t => t.id === selectedTaskId) || effectiveTasks[0];

  const filteredTasks = effectiveTasks.filter(t => {
    const matchesSearch = t.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          t.taskCode.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          t.sectionName.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesDept = selectedDept === 'ALL' || t.department === selectedDept;
    const matchesSev = selectedSeverity === 'ALL' || t.severity === selectedSeverity;
    return matchesSearch && matchesDept && matchesSev;
  }).sort((a, b) => {
    const valA = a[sortField];
    const valB = b[sortField];
    return sortAsc ? valA - valB : valB - valA;
  });

  return (
    <div className="space-y-4">
      {/* Search & Filter Bar */}
      <div className="p-3 rounded border border-slate-800 bg-slate-900/80 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-1 max-w-md">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input 
              type="text"
              placeholder="Search by code, asset, flaw, or section..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 rounded bg-slate-950 border border-slate-800 text-xs font-mono text-slate-200 focus:outline-none focus:border-sky-500"
            />
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap text-xs font-mono">
          <span className="text-slate-400">DEPT:</span>
          {(['ALL', 'CIVIL', 'S_AND_T', 'TRD'] as const).map(d => (
            <button
              key={d}
              onClick={() => setSelectedDept(d)}
              className={`px-2 py-1 rounded text-[11px] border transition-all ${
                selectedDept === d
                  ? 'text-white border-current'
                  : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-slate-200'
              }`}
              style={selectedDept === d ? { backgroundColor: `var(--status-info-fg)`, color: 'white', borderColor: `var(--status-info-fg)` } : undefined}
            >
              {d}
            </button>
          ))}

          <span className="text-slate-400 ml-2">SEV:</span>
          {(['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'] as const).map(s => (
            <button
              key={s}
              onClick={() => setSelectedSeverity(s)}
              className={`px-2 py-1 rounded text-[11px] border transition-all ${
                selectedSeverity === s
                  ? 'text-white border-current'
                  : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-slate-200'
              }`}
              style={selectedSeverity === s ? { backgroundColor: `var(--status-warning-fg)`, color: 'white', borderColor: `var(--status-warning-fg)` } : undefined}
            >
              {s}
            </button>
          ))}

          {isLiveServer && (
            <span
              className="ml-2 px-2 py-0.5 rounded text-[10px] font-mono font-bold flex items-center gap-1 border"
              style={{
                backgroundColor: `var(--status-ok-bg)`,
                color: `var(--status-ok-fg)`,
                borderColor: `var(--status-ok-border)`,
              }}
            >
              <Database className="w-3 h-3" /> Live Backend ({effectiveTasks.length})
            </span>
          )}
        </div>
      </div>

      {/* Main Grid: Data Table + Detail Drawer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        
        {/* Dense Operational Table */}
        <div className="lg:col-span-8 rounded border border-slate-800 bg-slate-950 overflow-x-auto">
          <table className="w-full text-left border-collapse font-mono text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900 text-slate-400 text-[11px] uppercase tracking-wider">
                <th className="p-3">Task Code</th>
                <th className="p-3">Dept</th>
                <th className="p-3">Asset / Flaw</th>
                <th className="p-3">Section</th>
                <th className="p-3 cursor-pointer hover:text-white" onClick={() => { setSortField('riskScore'); setSortAsc(!sortAsc); }}>
                  <div className="flex items-center gap-1">Risk <ArrowUpDown className="w-3 h-3" /></div>
                </th>
                <th className="p-3">Block Req</th>
                <th className="p-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredTasks.map(t => {
                const isSelected = t.id === selectedTask.id;
                return (
                  <tr
                    key={t.id}
                    onClick={() => setSelectedTaskId(t.id)}
                    className="cursor-pointer transition-colors hover:bg-slate-900/50 border-l-2"
                    style={isSelected ? { backgroundColor: `var(--status-info-bg)`, borderLeftColor: `var(--status-info-fg)` } : { borderLeftColor: 'transparent' }}
                  >
                    <td className="p-3 font-bold" style={{ color: `var(--status-info-fg)` }}>{t.taskCode}</td>
                    <td className="p-3"><DepartmentBadge dept={t.department} /></td>
                    <td className="p-3 max-w-[200px] truncate text-slate-200 font-sans font-medium" title={t.title}>
                      {t.title}
                    </td>
                    <td className="p-3 text-slate-400">{t.sectionName}</td>
                    <td className="p-3"><RiskBadge score={t.riskScore} severity={t.severity} /></td>
                    <td className="p-3 text-slate-300">
                      <span className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-[10px]">
                        {t.blockRequirement} ({t.estimatedMinutes}m)
                      </span>
                    </td>
                    <td className="p-3">
                      <span
                        className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                        style={
                          t.status === 'PENDING'
                            ? {
                                color: `var(--status-warning-text)`,
                                backgroundColor: `var(--status-warning-bg)`,
                              }
                            : {
                                color: `var(--status-ok-text)`,
                                backgroundColor: `var(--status-ok-bg)`,
                              }
                        }
                      >
                        {t.status}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Task Detail Drawer */}
        <div className="lg:col-span-4 rounded border border-slate-800 bg-slate-900/90 p-4 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4" style={{ color: `var(--status-info-fg)` }} />
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-100">
                Task Inspector
              </h3>
            </div>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
              {selectedTask.taskCode}
            </span>
          </div>

          <div className="space-y-3">
            <div>
              <div className="text-sm font-semibold text-white">
                {selectedTask.title}
              </div>
              <div className="flex items-center gap-2 mt-2">
                <DepartmentBadge dept={selectedTask.department} />
                <RiskBadge score={selectedTask.riskScore} severity={selectedTask.severity} />
              </div>
            </div>

            <div className="p-3 rounded border border-slate-800 bg-slate-950 space-y-2 text-xs font-mono">
              <div className="flex justify-between text-slate-400">
                <span>Asset Name:</span>
                <span className="text-slate-200 text-right">{selectedTask.assetName}</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Location:</span>
                <span className="text-slate-200">{selectedTask.sectionName}</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Track Alignment:</span>
                <span className="text-amber-400">{selectedTask.trackId} Track</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Possession Window:</span>
                <span className="text-sky-400">{selectedTask.blockRequirement} ({selectedTask.estimatedMinutes} mins)</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Crew & Machinery:</span>
                <span className="text-slate-200">{selectedTask.crewRequired} Men {selectedTask.specialMachine ? `+ ${selectedTask.specialMachine}` : ''}</span>
              </div>
            </div>

            <div>
              <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-1.5">
                Technical Evidence & Reasons:
              </div>
              <ul className="space-y-1 text-xs text-slate-300 font-sans">
                {selectedTask.reasons.map((r, i) => (
                  <li key={i} className="flex items-start gap-1.5">
                    <span className="text-sky-400 font-bold">•</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="pt-2 border-t border-slate-800">
              <div className="text-[11px] font-mono text-slate-400 mb-1">
                Electrical & Signal Isolation Guard:
              </div>
              <div className="text-xs text-slate-300 p-2 rounded bg-slate-950 border border-slate-800 font-mono">
                {selectedTask.isolationRequired ? (
                  <span className="text-amber-400 flex items-center gap-1.5">
                    <AlertOctagon className="w-3.5 h-3.5" />
                    Mandatory 25kV Traction Cut / S&T Disconnect Required
                  </span>
                ) : (
                  <span className="text-emerald-400 flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    No Traction Isolation Needed
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
