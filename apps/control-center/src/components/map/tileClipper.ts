import { INDIA_BOUNDARY_RINGS } from './indiaBoundary';
import type { RequestParameters } from 'maplibre-gl';

export const CLIPPED_ORM_PROTOCOL = 'clipped-orm';

export interface BoundingBox {
  minLng: number;
  minLat: number;
  maxLng: number;
  maxLat: number;
}

export interface Segment {
  r: number;
  p1: [number, number];
  p2: [number, number];
}

const GRID_SIZE = 1; // 1 degree grid for spatial indexing
let spatialGrid: Map<string, Segment[]> | null = null;
let ringBounds: BoundingBox[] | null = null;

function gridKey(gx: number, gy: number): string {
  return `${gx},${gy}`;
}

export function initSpatialIndex(): { grid: Map<string, Segment[]>; bounds: BoundingBox[] } {
  if (spatialGrid && ringBounds) {
    return { grid: spatialGrid, bounds: ringBounds };
  }

  const grid = new Map<string, Segment[]>();
  const bounds: BoundingBox[] = [];

  for (let r = 0; r < INDIA_BOUNDARY_RINGS.length; r++) {
    const ring = INDIA_BOUNDARY_RINGS[r];
    let minLng = Infinity, maxLng = -Infinity;
    let minLat = Infinity, maxLat = -Infinity;

    for (let i = 0; i < ring.length; i++) {
      const [lng, lat] = ring[i];
      if (lng < minLng) minLng = lng;
      if (lng > maxLng) maxLng = lng;
      if (lat < minLat) minLat = lat;
      if (lat > maxLat) maxLat = lat;
    }

    bounds.push({ minLng, minLat, maxLng, maxLat });

    for (let i = 0; i < ring.length - 1; i++) {
      const p1 = ring[i];
      const p2 = ring[i + 1];
      const segMinLng = Math.min(p1[0], p2[0]);
      const segMaxLng = Math.max(p1[0], p2[0]);
      const segMinLat = Math.min(p1[1], p2[1]);
      const segMaxLat = Math.max(p1[1], p2[1]);

      const gx0 = Math.floor(segMinLng / GRID_SIZE);
      const gx1 = Math.floor(segMaxLng / GRID_SIZE);
      const gy0 = Math.floor(segMinLat / GRID_SIZE);
      const gy1 = Math.floor(segMaxLat / GRID_SIZE);

      const segment: Segment = { r, p1, p2 };

      for (let gx = gx0; gx <= gx1; gx++) {
        for (let gy = gy0; gy <= gy1; gy++) {
          const k = gridKey(gx, gy);
          let list = grid.get(k);
          if (!list) {
            list = [];
            grid.set(k, list);
          }
          list.push(segment);
        }
      }
    }
  }

  spatialGrid = grid;
  ringBounds = bounds;
  return { grid, bounds };
}

export function tileToBounds(z: number, x: number, y: number): [number, number, number, number] {
  const n = 1 << z;
  const west = (x / n) * 360 - 180;
  const east = ((x + 1) / n) * 360 - 180;
  const latRadMin = Math.atan(Math.sinh(Math.PI * (1 - 2 * (y + 1) / n)));
  const latRadMax = Math.atan(Math.sinh(Math.PI * (1 - 2 * y / n)));
  const south = (latRadMin * 180) / Math.PI;
  const north = (latRadMax * 180) / Math.PI;
  return [west, south, east, north];
}

export function lngLatToTilePixel(
  lng: number,
  lat: number,
  z: number,
  tx: number,
  ty: number,
  size = 256
): [number, number] {
  const n = 1 << z;
  const tileX = n * ((lng + 180) / 360);
  const clampedLat = Math.max(-85.05112878, Math.min(85.05112878, lat));
  const latRad = (clampedLat * Math.PI) / 180;
  const tileY = (n * (1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI)) / 2;
  const px = (tileX - tx) * size;
  const py = (tileY - ty) * size;
  return [px, py];
}

function lineSegmentIntersectsBox(
  p1: [number, number],
  p2: [number, number],
  west: number,
  south: number,
  east: number,
  north: number
): boolean {
  const minX = Math.min(p1[0], p2[0]), maxX = Math.max(p1[0], p2[0]);
  const minY = Math.min(p1[1], p2[1]), maxY = Math.max(p1[1], p2[1]);
  if (maxX < west || minX > east || maxY < south || minY > north) return false;
  if (p1[0] >= west && p1[0] <= east && p1[1] >= south && p1[1] <= north) return true;
  if (p2[0] >= west && p2[0] <= east && p2[1] >= south && p2[1] <= north) return true;

  function intersectSegs(
    a1: [number, number],
    a2: [number, number],
    b1: [number, number],
    b2: [number, number]
  ): boolean {
    const d = (b2[1] - b1[1]) * (a2[0] - a1[0]) - (b2[0] - b1[0]) * (a2[1] - a1[1]);
    if (d === 0) return false;
    const ua = ((b2[0] - b1[0]) * (a1[1] - b1[1]) - (b2[1] - b1[1]) * (a1[0] - b1[0])) / d;
    const ub = ((a2[0] - a1[0]) * (a1[1] - b1[1]) - (a2[1] - a1[0]) * (a1[0] - b1[0])) / d;
    return ua >= 0 && ua <= 1 && ub >= 0 && ub <= 1;
  }

  const bl: [number, number] = [west, south];
  const br: [number, number] = [east, south];
  const tr: [number, number] = [east, north];
  const tl: [number, number] = [west, north];

  return (
    intersectSegs(p1, p2, bl, br) ||
    intersectSegs(p1, p2, br, tr) ||
    intersectSegs(p1, p2, tr, tl) ||
    intersectSegs(p1, p2, tl, bl)
  );
}

export function pointInRing(pt: [number, number], ring: [number, number][]): boolean {
  const [x, y] = pt;
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0], yi = ring[i][1];
    const xj = ring[j][0], yj = ring[j][1];
    const intersect = yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

export function pointInIndia(pt: [number, number]): boolean {
  const { bounds } = initSpatialIndex();
  const [lng, lat] = pt;
  for (let r = 0; r < INDIA_BOUNDARY_RINGS.length; r++) {
    const b = bounds[r];
    if (lng < b.minLng || lng > b.maxLng || lat < b.minLat || lat > b.maxLat) continue;
    if (pointInRing(pt, INDIA_BOUNDARY_RINGS[r])) return true;
  }
  return false;
}

export type TileClassification = 'inside' | 'border' | 'outside';

export function classifyTile(z: number, x: number, y: number): TileClassification {
  const [west, south, east, north] = tileToBounds(z, x, y);

  // Quick bounding box rejection for regions outside the Indian subcontinent
  if (east < 68.0 || west > 97.6 || north < 6.5 || south > 37.6) {
    return 'outside';
  }

  const { grid } = initSpatialIndex();
  const gx0 = Math.floor(west / GRID_SIZE);
  const gx1 = Math.floor(east / GRID_SIZE);
  const gy0 = Math.floor(south / GRID_SIZE);
  const gy1 = Math.floor(north / GRID_SIZE);

  let intersects = false;
  for (let gx = gx0; gx <= gx1; gx++) {
    for (let gy = gy0; gy <= gy1; gy++) {
      const list = grid.get(gridKey(gx, gy));
      if (!list) continue;
      for (let s = 0; s < list.length; s++) {
        if (lineSegmentIntersectsBox(list[s].p1, list[s].p2, west, south, east, north)) {
          intersects = true;
          break;
        }
      }
      if (intersects) break;
    }
    if (intersects) break;
  }

  if (intersects) return 'border';

  const center: [number, number] = [(west + east) / 2, (south + north) / 2];
  return pointInIndia(center) ? 'inside' : 'outside';
}

export function clipTileToIndia(
  ctx: CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D,
  z: number,
  tx: number,
  ty: number,
  image: CanvasImageSource,
  tileSize = 256
): void {
  const [west, south, east, north] = tileToBounds(z, tx, ty);
  const margin = Math.max(east - west, north - south) * 0.5;
  const { bounds } = initSpatialIndex();

  ctx.clearRect(0, 0, tileSize, tileSize);
  ctx.save();
  ctx.beginPath();

  for (let r = 0; r < INDIA_BOUNDARY_RINGS.length; r++) {
    const ring = INDIA_BOUNDARY_RINGS[r];
    const bbox = bounds[r];
    if (
      bbox.maxLng < west - margin ||
      bbox.minLng > east + margin ||
      bbox.maxLat < south - margin ||
      bbox.minLat > north + margin
    ) {
      continue;
    }

    for (let i = 0; i < ring.length; i++) {
      const [px, py] = lngLatToTilePixel(ring[i][0], ring[i][1], z, tx, ty, tileSize);
      if (i === 0) {
        ctx.moveTo(px, py);
      } else {
        ctx.lineTo(px, py);
      }
    }
    ctx.closePath();
  }

  ctx.clip();
  ctx.drawImage(image, 0, 0, tileSize, tileSize);
  ctx.restore();
}

export async function handleClippedRailwayTile(
  params: RequestParameters,
  abortController: AbortController
): Promise<{ data: ArrayBuffer | ImageBitmap | null }> {
  const match = params.url.match(/\/(\d+)\/(\d+)\/(\d+)\.png/);
  if (!match) {
    return { data: null };
  }

  const z = parseInt(match[1], 10);
  const x = parseInt(match[2], 10);
  const y = parseInt(match[3], 10);

  const status = classifyTile(z, x, y);

  // Tiles completely outside India are returned as empty (null data)
  // MapLibre treats null data as fully transparent loaded tile with no requests made
  if (status === 'outside') {
    return { data: null };
  }

  const sub = ['a', 'b', 'c'][(x + y) % 3];
  const upstreamUrl = `https://${sub}.tiles.openrailwaymap.org/standard/${z}/${x}/${y}.png`;

  const res = await fetch(upstreamUrl, { signal: abortController.signal });
  if (!res.ok) {
    if (res.status === 404) return { data: null };
    throw new Error(`OpenRailwayMap tile ${z}/${x}/${y} returned HTTP ${res.status}`);
  }

  // Tiles completely inside India are passed through without canvas overhead
  if (status === 'inside') {
    const buffer = await res.arrayBuffer();
    return { data: buffer };
  }

  // Border tiles are clipped to the Indian boundary
  try {
    const blob = await res.blob();
    let imageSource: CanvasImageSource;

    if (typeof createImageBitmap !== 'undefined') {
      imageSource = await createImageBitmap(blob);
    } else if (typeof Image !== 'undefined') {
      imageSource = await new Promise<HTMLImageElement>((resolve, reject) => {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.onload = () => resolve(img);
        img.onerror = reject;
        img.src = URL.createObjectURL(blob);
      });
    } else {
      // In headless environments with no image decode, return raw buffer
      return { data: await blob.arrayBuffer() };
    }

    const canvas =
      typeof OffscreenCanvas !== 'undefined'
        ? new OffscreenCanvas(256, 256)
        : typeof document !== 'undefined'
        ? document.createElement('canvas')
        : null;

    if (!canvas) {
      return { data: await blob.arrayBuffer() };
    }

    canvas.width = 256;
    canvas.height = 256;
    const ctx = canvas.getContext('2d') as CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D | null;
    if (!ctx) {
      return { data: await blob.arrayBuffer() };
    }

    clipTileToIndia(ctx, z, x, y, imageSource, 256);

    if (typeof createImageBitmap !== 'undefined') {
      const bitmap = await createImageBitmap(canvas);
      return { data: bitmap };
    }

    if ('convertToBlob' in canvas) {
      const outBlob = await (canvas as OffscreenCanvas).convertToBlob({ type: 'image/png' });
      return { data: await outBlob.arrayBuffer() };
    }

    if ('toBlob' in canvas) {
      const outBlob = await new Promise<Blob | null>((resolve) =>
        (canvas as HTMLCanvasElement).toBlob(resolve, 'image/png')
      );
      if (outBlob) {
        return { data: await outBlob.arrayBuffer() };
      }
    }

    return { data: await blob.arrayBuffer() };
  } catch (error) {
    console.warn('[map] Border tile clipping fallback for tile', z, x, y, error);
    // On unexpected clipping error, return null to avoid displaying foreign tracks
    return { data: null };
  }
}
