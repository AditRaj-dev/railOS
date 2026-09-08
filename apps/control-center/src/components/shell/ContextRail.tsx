'use client';

import React from 'react';
import { useRailOSStore } from '@/store/railosStore';
import { X } from 'lucide-react';

export function ContextRail() {
  const {
    activeDrawer,
    setActiveDrawer,
    selectedBlockId,
    selectedTaskId,
    selectedSectionId
  } = useRailOSStore();

  if (!activeDrawer) {
    return null;
  }

  return (
    <aside className="pointer-events-auto hidden lg:flex flex-col w-80 border-l border-slate-800/90 bg-[var(--bg-surface)] overflow-y-auto max-h-[calc(100dvh-7rem)]">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-800/50 sticky top-0 bg-[var(--bg-surface)] z-10">
        <h2 className="text-sm font-mono font-bold text-slate-100 uppercase tracking-wider">
          {activeDrawer === 'block' && 'Block Details'}
          {activeDrawer === 'task' && 'Task Inspector'}
          {activeDrawer === 'section' && 'Section Profile'}
          {activeDrawer === 'plan' && 'Plan Analysis'}
          {activeDrawer === 'alerts' && 'Alerts & Events'}
        </h2>
        <button
          onClick={() => setActiveDrawer(null)}
          className="p-1 rounded hover:bg-slate-800/60 text-slate-400 hover:text-slate-200 transition-all"
          aria-label="Close context panel"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 p-4 space-y-4">
        {activeDrawer === 'block' && selectedBlockId && (
          <div className="space-y-3 text-xs">
            <div className="space-y-1">
              <div className="text-slate-400">Block ID</div>
              <div className="text-slate-100 font-mono font-bold">{selectedBlockId}</div>
            </div>
            <div className="space-y-1">
              <div className="text-slate-400">Status</div>
              <div className="inline-block px-2 py-1 rounded bg-sky-600/20 text-sky-300 border border-sky-500/50 font-mono text-[10px]">
                PLANNED
              </div>
            </div>
            <div className="space-y-1">
              <div className="text-slate-400">Content</div>
              <div className="p-2 rounded bg-slate-900/40 border border-slate-800/60 text-slate-300">
                Select a block on the map or timeline to view details.
              </div>
            </div>
          </div>
        )}

        {activeDrawer === 'task' && selectedTaskId && (
          <div className="space-y-3 text-xs">
            <div className="space-y-1">
              <div className="text-slate-400">Task ID</div>
              <div className="text-slate-100 font-mono font-bold">{selectedTaskId}</div>
            </div>
            <div className="space-y-1">
              <div className="text-slate-400">Inspector</div>
              <div className="p-2 rounded bg-slate-900/40 border border-slate-800/60 text-slate-300">
                Select a task in maintenance intelligence to view full details.
              </div>
            </div>
          </div>
        )}

        {activeDrawer === 'section' && selectedSectionId && (
          <div className="space-y-3 text-xs">
            <div className="space-y-1">
              <div className="text-slate-400">Section ID</div>
              <div className="text-slate-100 font-mono font-bold">{selectedSectionId}</div>
            </div>
            <div className="space-y-1">
              <div className="text-slate-400">Profile</div>
              <div className="p-2 rounded bg-slate-900/40 border border-slate-800/60 text-slate-300">
                Section details and topology will appear here.
              </div>
            </div>
          </div>
        )}

        {activeDrawer === 'plan' && (
          <div className="space-y-3 text-xs">
            <div className="space-y-1">
              <div className="text-slate-400">Active Plan</div>
              <div className="p-2 rounded bg-slate-900/40 border border-slate-800/60 text-slate-300">
                Plan analysis and comparison data will appear here.
              </div>
            </div>
          </div>
        )}

        {activeDrawer === 'alerts' && (
          <div className="space-y-3 text-xs">
            <div className="space-y-1">
              <div className="text-slate-400">Recent Events</div>
              <div className="p-2 rounded bg-slate-900/40 border border-slate-800/60 text-slate-300">
                No critical alerts at this time.
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
