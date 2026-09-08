import { addProtocol, type Map, type RasterSourceSpecification } from 'maplibre-gl';
import { CLIPPED_ORM_PROTOCOL, handleClippedRailwayTile } from './tileClipper';

export const OPEN_RAILWAY_MAP_SOURCE_ID = 'openrailwaymap-standard';
export const OPEN_RAILWAY_MAP_LAYER_ID = 'openrailwaymap-standard-raster';
export { CLIPPED_ORM_PROTOCOL };

let protocolRegistered = false;

export function registerClippedRailwayProtocol(): void {
  if (protocolRegistered) return;
  if (typeof window === 'undefined') return;

  try {
    if (typeof addProtocol === 'function') {
      addProtocol(CLIPPED_ORM_PROTOCOL, handleClippedRailwayTile);
      protocolRegistered = true;
    }
  } catch (err) {
    console.warn('[map] Failed to register clipped railway protocol:', err);
  }
}

const source: RasterSourceSpecification = {
  type: 'raster',
  tiles: [
    `${CLIPPED_ORM_PROTOCOL}://tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png`,
  ],
  tileSize: 256,
  minzoom: 2,
  maxzoom: 19,
  attribution: 'Railway data © OpenStreetMap contributors, rendering © OpenRailwayMap',
};

export function ensureOpenRailwayMapOverlay(
  map: Pick<Map, 'getSource' | 'addSource' | 'getLayer' | 'addLayer'>
): void {
  registerClippedRailwayProtocol();

  if (!map.getSource(OPEN_RAILWAY_MAP_SOURCE_ID)) {
    map.addSource(OPEN_RAILWAY_MAP_SOURCE_ID, source);
  }
  if (!map.getLayer(OPEN_RAILWAY_MAP_LAYER_ID)) {
    map.addLayer({
      id: OPEN_RAILWAY_MAP_LAYER_ID,
      type: 'raster',
      source: OPEN_RAILWAY_MAP_SOURCE_ID,
      paint: { 'raster-opacity': 0.92, 'raster-fade-duration': 150 },
    });
  }
}

export function isOpenRailwayMapError(event: unknown): boolean {
  const candidate = event as { sourceId?: string; error?: { message?: string } };
  return (
    candidate?.sourceId === OPEN_RAILWAY_MAP_SOURCE_ID ||
    candidate?.error?.message?.includes('tiles.openrailwaymap.org') === true ||
    candidate?.error?.message?.includes(CLIPPED_ORM_PROTOCOL) === true
  );
}
