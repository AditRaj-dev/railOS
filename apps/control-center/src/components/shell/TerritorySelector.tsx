'use client';

import React, { Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useRailOSStore } from '@/store/railosStore';
import { useNetworkCatalog } from '@/lib/queries';
import { ChevronDown } from 'lucide-react';

function TerritorySelectorInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const { selectedZone, selectedDivision, selectedSection, setSelectedZone, setSelectedDivision, setSelectedSection } = useRailOSStore();
  const { data: catalog } = useNetworkCatalog();

  const zones = catalog?.zones || [];
  const defaultZone = zones[0]?.code || '';

  const zone = searchParams.get('zone') || selectedZone || defaultZone;
  const currentZoneObj = zones.find(z => z.code === zone || z.zoneId === zone);

  const divisions = catalog?.divisions ? catalog.divisions.filter(d => !currentZoneObj || d.zoneId === currentZoneObj.zoneId) : [];
  const division = searchParams.get('division') || selectedDivision || divisions[0]?.name || '';
  const currentDivObj = divisions.find(d => d.name === division || d.code === division || d.divisionId === division);

  const sections = catalog?.sections ? catalog.sections.filter(s => !currentDivObj || s.divisionId === currentDivObj.divisionId) : [];
  const section = searchParams.get('section') || selectedSection || sections[0]?.code || '';

  const handleZoneChange = (newZone: string) => {
    setSelectedZone(newZone);
    const params = new URLSearchParams(searchParams);
    params.set('zone', newZone);
    params.delete('division');
    params.delete('section');
    router.replace(`?${params.toString()}`);
  };

  const handleDivisionChange = (newDivision: string) => {
    setSelectedDivision(newDivision);
    const params = new URLSearchParams(searchParams);
    params.set('division', newDivision);
    params.delete('section');
    router.replace(`?${params.toString()}`);
  };

  const handleSectionChange = (newSection: string) => {
    setSelectedSection(newSection);
    const params = new URLSearchParams(searchParams);
    params.set('section', newSection);
    router.replace(`?${params.toString()}`);
  };

  return (
    <div className="flex items-center gap-2 text-xs font-mono">
      <div className="flex items-center gap-1">
        <label htmlFor="zone-select" className="text-[var(--text-muted)]">Zone:</label>
        <select
          id="zone-select"
          value={zone}
          onChange={(e) => handleZoneChange(e.target.value)}
          className="px-2 py-1 rounded bg-[var(--bg-elevated)] border border-[var(--border-default)] text-[var(--text-primary)] hover:border-[var(--accent)] focus:outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]/50 cursor-pointer"
        >
          {zones.length > 0 ? (
            zones.map(z => (
              <option key={z.zoneId} value={z.code}>{z.code} ({z.name})</option>
            ))
          ) : (
            <option value="" disabled>No zones available</option>
          )}
        </select>
      </div>

      <div className="flex items-center gap-1">
        <ChevronDown className="w-3 h-3 text-[var(--text-muted)]" />
        <label htmlFor="division-select" className="text-[var(--text-muted)]">Division:</label>
        <select
          id="division-select"
          value={division}
          onChange={(e) => handleDivisionChange(e.target.value)}
          className="px-2 py-1 rounded bg-[var(--bg-elevated)] border border-[var(--border-default)] text-[var(--text-primary)] hover:border-[var(--accent)] focus:outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]/50 cursor-pointer"
        >
          {divisions.length > 0 ? (
            divisions.map(d => (
              <option key={d.divisionId} value={d.name}>{d.name}</option>
            ))
          ) : (
            <option value="" disabled>No divisions available</option>
          )}
        </select>
      </div>

      <div className="flex items-center gap-1">
        <ChevronDown className="w-3 h-3 text-[var(--text-muted)]" />
        <label htmlFor="section-select" className="text-[var(--text-muted)]">Section:</label>
        <select
          id="section-select"
          value={section}
          onChange={(e) => handleSectionChange(e.target.value)}
          className="px-2 py-1 rounded bg-[var(--bg-elevated)] border border-[var(--border-default)] text-[var(--text-primary)] hover:border-[var(--accent)] focus:outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]/50 cursor-pointer"
        >
          {sections.length > 0 ? (
            sections.map(s => (
              <option key={s.sectionId} value={s.code}>{s.name} ({s.code})</option>
            ))
          ) : (
            <option value="" disabled>No sections available</option>
          )}
        </select>
      </div>
    </div>
  );
}

/**
 * useSearchParams() requires a Suspense boundary or it forces a client-side
 * bailout during static prerendering (Next.js "missing-suspense-with-csr-bailout").
 * The fallback mirrors layout dimensions so the shell doesn't jump on hydration.
 */
export function TerritorySelector() {
  return (
    <Suspense fallback={<div className="h-6 w-72" aria-hidden="true" />}>
      <TerritorySelectorInner />
    </Suspense>
  );
}
