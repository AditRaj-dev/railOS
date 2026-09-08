import { IconLayer } from '@deck.gl/layers';
import type { PickingInfo } from '@deck.gl/core';
import type { NetworkFeatureProperties, ReportedArea } from '@/types/network';
import { reportedAreaFeature } from './featureAdapters';

const triangleSvg = '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><path fill="white" stroke="white" stroke-width="4" d="M32 5 59 57H5Z"/></svg>';
const triangleAtlas = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(triangleSvg)}`;
const triangleMapping = { triangle: { x: 0, y: 0, width: 64, height: 64, anchorX: 32, anchorY: 32, mask: true } };
type HoverHandler = (info: { object?: NetworkFeatureProperties } | null) => void;
type ClickHandler = (info: { object?: NetworkFeatureProperties }) => void;

function severityColor(report: ReportedArea): [number, number, number, number] {
  if (report.severity === 'CRITICAL') return [239, 68, 68, 255];
  if (report.severity === 'WARNING') return [245, 158, 11, 255];
  return [56, 189, 248, 255];
}

export function buildReportedAreaLayer(
  reports: ReportedArea[],
  selectedReportId?: string,
  onHover?: HoverHandler,
  onClick?: ClickHandler
) {
  return new IconLayer<ReportedArea>({
    id: 'reported-areas',
    data: reports.filter((report) => report.status !== 'CLEARED'),
    iconAtlas: triangleAtlas, iconMapping: triangleMapping,
    getIcon: () => 'triangle', getPosition: (report) => report.coordinates,
    getAngle: (report) => report.bearingDegrees, getColor: severityColor,
    getSize: (report) => report.reportId === selectedReportId ? 26 : 20,
    sizeUnits: 'pixels', billboard: true, pickable: true, autoHighlight: true,
    highlightColor: [255, 255, 255, 255],
    onHover: (info: PickingInfo<ReportedArea>) => onHover?.(info.object ? { object: reportedAreaFeature(info.object) } : null),
    onClick: (info: PickingInfo<ReportedArea>) => {
      if (info.object) onClick?.({ object: reportedAreaFeature(info.object) });
    },
  });
}
