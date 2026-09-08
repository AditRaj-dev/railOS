import { describe, expect, it, vi } from 'vitest';
import { OPEN_RAILWAY_MAP_LAYER_ID, OPEN_RAILWAY_MAP_SOURCE_ID, ensureOpenRailwayMapOverlay, isOpenRailwayMapError } from '../railwayOverlay';

describe('OpenRailwayMap overlay', () => {
  it('adds the source and layer only once', () => {
    const sources = new Set<string>(); const layers = new Set<string>();
    const map = {
      getSource: vi.fn((id: string) => sources.has(id) ? {} : undefined),
      addSource: vi.fn((id: string) => sources.add(id)),
      getLayer: vi.fn((id: string) => layers.has(id) ? {} : undefined),
      addLayer: vi.fn((layer: { id: string }) => layers.add(layer.id)),
    };
    ensureOpenRailwayMapOverlay(map as never);
    ensureOpenRailwayMapOverlay(map as never);
    expect(map.addSource).toHaveBeenCalledTimes(1);
    expect(map.addLayer).toHaveBeenCalledTimes(1);
    expect(sources.has(OPEN_RAILWAY_MAP_SOURCE_ID)).toBe(true);
    expect(layers.has(OPEN_RAILWAY_MAP_LAYER_ID)).toBe(true);
  });
  it('classifies railway tile errors', () => {
    expect(isOpenRailwayMapError({ sourceId: OPEN_RAILWAY_MAP_SOURCE_ID })).toBe(true);
    expect(isOpenRailwayMapError({ error: { message: '403 from tiles.openrailwaymap.org' } })).toBe(true);
    expect(isOpenRailwayMapError({ error: { message: 'unrelated' } })).toBe(false);
  });
});
