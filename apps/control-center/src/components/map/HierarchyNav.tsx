'use client';

import React, { useState, useCallback, useMemo } from 'react';
import { ChevronDown, ChevronRight, Search, MapPin, Lock } from 'lucide-react';
import type {
  RailwayZone,
  RailwayDivision,
  RailwaySection,
  NetworkFeatureProperties,
} from '@/types/network';

interface SelectionState {
  zoneId?: string;
  divisionId?: string;
  sectionId?: string;
}

interface HierarchyNavProps {
  zones: RailwayZone[];
  divisions: RailwayDivision[];
  sections: RailwaySection[];
  selection?: SelectionState;
  onSelect?: (entity: NetworkFeatureProperties) => void;
}

export const HierarchyNav: React.FC<HierarchyNavProps> = ({
  zones,
  divisions,
  sections,
  selection,
  onSelect,
}) => {
  const [expandedZones, setExpandedZones] = useState<Set<string>>(new Set());
  const [expandedDivisions, setExpandedDivisions] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');

  const toggleZoneExpand = useCallback((zoneId: string) => {
    setExpandedZones((prev) => {
      const next = new Set(prev);
      if (next.has(zoneId)) {
        next.delete(zoneId);
      } else {
        next.add(zoneId);
      }
      return next;
    });
  }, []);

  const toggleDivisionExpand = useCallback((divisionId: string) => {
    setExpandedDivisions((prev) => {
      const next = new Set(prev);
      if (next.has(divisionId)) {
        next.delete(divisionId);
      } else {
        next.add(divisionId);
      }
      return next;
    });
  }, []);

  const handleZoneSelect = useCallback(
    (zone: RailwayZone) => {
      if (onSelect) {
        onSelect({
          id: zone.zoneId,
          entityType: 'zone',
          zoneId: zone.zoneId,
          name: zone.name,
          code: zone.code,
          metrics: zone.metrics,
          planningEnabled: zone.planningEnabled,
          synthetic: zone.provenance?.synthetic ?? true,
        });
      }
      if (!expandedZones.has(zone.zoneId)) {
        toggleZoneExpand(zone.zoneId);
      }
    },
    [onSelect, expandedZones, toggleZoneExpand]
  );

  const handleDivisionSelect = useCallback(
    (division: RailwayDivision) => {
      if (onSelect) {
        onSelect({
          id: division.divisionId,
          entityType: 'division',
          divisionId: division.divisionId,
          zoneId: division.zoneId,
          name: division.name,
          code: division.code,
          metrics: division.metrics,
          planningEnabled: division.planningEnabled,
          synthetic: division.provenance?.synthetic ?? true,
        });
      }
      if (!expandedDivisions.has(division.divisionId)) {
        toggleDivisionExpand(division.divisionId);
      }
    },
    [onSelect, expandedDivisions, toggleDivisionExpand]
  );

  const handleSectionSelect = useCallback(
    (section: RailwaySection) => {
      if (onSelect) {
        onSelect({
          id: section.sectionId,
          entityType: 'section',
          sectionId: section.sectionId,
          divisionId: section.divisionId,
          zoneId: section.zoneId,
          name: section.name,
          code: section.code,
          metrics: section.metrics,
          planningEnabled: section.planningEnabled,
          synthetic: section.provenance?.synthetic ?? true,
        });
      }
    },
    [onSelect]
  );

  const filteredZones = useMemo(() => {
    if (!searchQuery.trim()) {
      return zones;
    }
    const query = searchQuery.toLowerCase();
    return zones.filter(
      (z) =>
        z.name.toLowerCase().includes(query) ||
        z.code.toLowerCase().includes(query) ||
        divisions.some(
          (d) =>
            d.zoneId === z.zoneId &&
            (d.name.toLowerCase().includes(query) || d.code.toLowerCase().includes(query))
        ) ||
        sections.some(
          (s) =>
            s.zoneId === z.zoneId &&
            (s.name.toLowerCase().includes(query) || s.code.toLowerCase().includes(query))
        )
    );
  }, [zones, divisions, sections, searchQuery]);

  const selectedZone = zones.find((z) => z.zoneId === selection?.zoneId);
  const selectedDivision = divisions.find((d) => d.divisionId === selection?.divisionId);
  const selectedSection = sections.find((s) => s.sectionId === selection?.sectionId);

  return (
    <div className="flex flex-col h-full bg-slate-950 border-r border-slate-800">
      {/* Breadcrumbs */}
      {(selectedZone || selectedDivision || selectedSection) && (
        <div className="p-3 border-b border-slate-800 space-y-1">
          <div className="text-xs font-mono uppercase tracking-wide text-slate-500">
            Selection Path
          </div>
          <div className="text-xs font-mono text-slate-400 break-words">
            {selectedZone?.code}
            {selectedDivision && ` / ${selectedDivision.code}`}
            {selectedSection && ` / ${selectedSection.code}`}
          </div>
        </div>
      )}

      {/* Search */}
      <div className="p-3 border-b border-slate-800">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-slate-600" />
          <input
            type="text"
            placeholder="Search zones, divisions, sections…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 bg-slate-900 border border-slate-800 rounded text-xs text-slate-300 placeholder-slate-600 font-mono focus:outline-none focus:border-sky-600 focus:ring-1 focus:ring-sky-600/50"
            aria-label="Search railway hierarchy"
          />
        </div>
      </div>

      {/* Hierarchy Tree */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-2 space-y-0.5">
          {filteredZones.length === 0 ? (
            <div className="p-3 text-xs text-slate-500 font-mono text-center">No zones found</div>
          ) : (
            filteredZones.map((zone) => {
              const zoneDivisions = divisions.filter((d) => d.zoneId === zone.zoneId);
              const isZoneExpanded = expandedZones.has(zone.zoneId);
              const isZoneSelected = selection?.zoneId === zone.zoneId && !selection?.divisionId;

              return (
                <div key={zone.zoneId}>
                  <button
                    onClick={() => handleZoneSelect(zone)}
                    className={`w-full text-left px-2 py-1.5 rounded text-xs font-mono transition-all flex items-center gap-2 ${
                      isZoneSelected
                        ? 'bg-sky-600/20 text-sky-400 border border-sky-600/50'
                        : 'text-slate-400 hover:bg-slate-900 hover:text-slate-300'
                    }`}
                    aria-label={`${zone.name} (${zone.code})${isZoneExpanded ? ', expanded' : ''}`}
                  >
                    <ChevronRight
                      className={`w-3.5 h-3.5 flex-shrink-0 transition-transform ${isZoneExpanded ? 'rotate-90' : ''}`}
                    />
                    <MapPin className="w-3 h-3 flex-shrink-0 text-slate-600" />
                    <div className="flex-1 truncate">
                      <span className="font-bold">{zone.code}</span>
                      <span className="text-slate-600"> {zone.name}</span>
                    </div>
                    {!zone.planningEnabled && (
                      <Lock className="w-3 h-3 flex-shrink-0 text-slate-700" />
                    )}
                  </button>

                  {/* Division List */}
                  {isZoneExpanded && zoneDivisions.length > 0 && (
                    <div className="ml-2 pl-2 border-l border-slate-800 space-y-0.5 mt-0.5">
                      {zoneDivisions.map((division) => {
                        const divisionSections = sections.filter(
                          (s) => s.divisionId === division.divisionId
                        );
                        const isDivisionExpanded = expandedDivisions.has(division.divisionId);
                        const isDivisionSelected =
                          selection?.divisionId === division.divisionId && !selection?.sectionId;

                        return (
                          <div key={division.divisionId}>
                            <button
                              onClick={() => handleDivisionSelect(division)}
                              className={`w-full text-left px-2 py-1.5 rounded text-xs font-mono transition-all flex items-center gap-2 ${
                                isDivisionSelected
                                  ? 'bg-sky-600/20 text-sky-400 border border-sky-600/50'
                                  : 'text-slate-400 hover:bg-slate-900 hover:text-slate-300'
                              }`}
                              aria-label={`${division.name} (${division.code})${isDivisionExpanded ? ', expanded' : ''}`}
                            >
                              <ChevronRight
                                className={`w-3.5 h-3.5 flex-shrink-0 transition-transform ${isDivisionExpanded ? 'rotate-90' : ''}`}
                              />
                              <div className="flex-1 truncate">
                                <span className="font-bold">{division.code}</span>
                                <span className="text-slate-600"> {division.name}</span>
                              </div>
                              {!division.planningEnabled && (
                                <Lock className="w-3 h-3 flex-shrink-0 text-slate-700" />
                              )}
                            </button>

                            {/* Section List */}
                            {isDivisionExpanded && divisionSections.length > 0 && (
                              <div className="ml-2 pl-2 border-l border-slate-800 space-y-0.5 mt-0.5">
                                {divisionSections.map((section) => {
                                  const isSectionSelected = selection?.sectionId === section.sectionId;

                                  return (
                                    <button
                                      key={section.sectionId}
                                      onClick={() => handleSectionSelect(section)}
                                      className={`w-full text-left px-2 py-1.5 rounded text-xs font-mono transition-all flex items-center gap-2 ${
                                        isSectionSelected
                                          ? 'bg-sky-600/20 text-sky-400 border border-sky-600/50'
                                          : 'text-slate-400 hover:bg-slate-900 hover:text-slate-300'
                                      }`}
                                      aria-label={`${section.name} (${section.code})`}
                                    >
                                      <div className="w-3.5 flex-shrink-0" />
                                      <div className="flex-1 truncate">
                                        <span className="font-bold">{section.code}</span>
                                        <span className="text-slate-600">
                                          {' '}
                                          {section.fromStation}–{section.toStation}
                                        </span>
                                      </div>
                                      {!section.planningEnabled && (
                                        <Lock className="w-3 h-3 flex-shrink-0 text-slate-700" />
                                      )}
                                    </button>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Summary */}
      {selectedSection && (
        <div className="p-3 border-t border-slate-800 bg-slate-900/50 space-y-2">
          <div className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wide">
            {selectedSection.name}
          </div>
          <div className="grid grid-cols-2 gap-2 text-[10px] font-mono text-slate-400">
            <div>
              <span className="text-sky-400 font-bold">{selectedSection.metrics.pendingMaintenanceCount}</span>{' '}
              Tasks
            </div>
            <div>
              <span className="text-amber-400 font-bold">{selectedSection.metrics.criticalDefectCount}</span>{' '}
              Critical
            </div>
            <div>
              <span className="text-emerald-400 font-bold">
                {selectedSection.metrics.assetAvailability.toFixed(0)}%
              </span>{' '}
              Available
            </div>
            <div>
              <span className="text-orange-400 font-bold">{selectedSection.metrics.trafficPressure}</span>{' '}
              Pressure
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
