import { describe, expect, it, vi } from 'vitest';
import {
  tileToBounds,
  lngLatToTilePixel,
  classifyTile,
  pointInIndia,
  handleClippedRailwayTile,
  CLIPPED_ORM_PROTOCOL,
} from '../tileClipper';

function lngLatToTile(lng: number, lat: number, z: number): [number, number] {
  const n = 1 << z;
  const x = Math.floor(n * ((lng + 180) / 360));
  const clampedLat = Math.max(-85.05112878, Math.min(85.05112878, lat));
  const latRad = (clampedLat * Math.PI) / 180;
  const y = Math.floor((n * (1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI)) / 2);
  return [x, y];
}

describe('tileClipper', () => {
  describe('tileToBounds and lngLatToTilePixel', () => {
    it('computes correct bounds for zoom 0', () => {
      const [west, south, east, north] = tileToBounds(0, 0, 0);
      expect(west).toBe(-180);
      expect(east).toBe(180);
      expect(south).toBeCloseTo(-85.05, 1);
      expect(north).toBeCloseTo(85.05, 1);
    });

    it('projects origin (0, 0) to tile center at zoom 0', () => {
      const [px, py] = lngLatToTilePixel(0, 0, 0, 0, 0, 256);
      expect(px).toBe(128);
      expect(py).toBe(128);
    });
  });

  describe('pointInIndia', () => {
    it('identifies Indian cities as inside India', () => {
      expect(pointInIndia([77.209, 28.6139])).toBe(true); // New Delhi
      expect(pointInIndia([79.0882, 21.1458])).toBe(true); // Nagpur
      expect(pointInIndia([78.4867, 17.385])).toBe(true); // Hyderabad
      expect(pointInIndia([72.8777, 19.076])).toBe(true); // Mumbai
      expect(pointInIndia([80.2707, 13.0827])).toBe(true); // Chennai
    });

    it('identifies foreign cities as outside India', () => {
      expect(pointInIndia([69.1723, 34.5553])).toBe(false); // Kabul, Afghanistan
      expect(pointInIndia([74.3587, 31.5204])).toBe(false); // Lahore, Pakistan
      expect(pointInIndia([67.0011, 24.8607])).toBe(false); // Karachi, Pakistan
      expect(pointInIndia([96.0891, 21.9588])).toBe(false); // Mandalay, Myanmar
      expect(pointInIndia([91.1409, 29.6456])).toBe(false); // Lhasa, China / Tibet
      expect(pointInIndia([90.4125, 23.8103])).toBe(false); // Dhaka, Bangladesh
      expect(pointInIndia([85.324, 27.7172])).toBe(false); // Kathmandu, Nepal
      expect(pointInIndia([79.8612, 6.9271])).toBe(false); // Colombo, Sri Lanka
    });
  });

  describe('classifyTile', () => {
    it('classifies tiles deep in India as inside', () => {
      // Delhi tile at z=9
      const [dx, dy] = lngLatToTile(77.209, 28.6139, 9);
      expect(classifyTile(9, dx, dy)).toBe('inside');

      // Nagpur tile at z=9
      const [nx, ny] = lngLatToTile(79.0882, 21.1458, 9);
      expect(classifyTile(9, nx, ny)).toBe('inside');

      // Hyderabad tile at z=9
      const [hx, hy] = lngLatToTile(78.4867, 17.385, 9);
      expect(classifyTile(9, hx, hy)).toBe('inside');
    });

    it('classifies tiles in neighboring countries as outside', () => {
      // Kabul (Afghanistan)
      const [kx, ky] = lngLatToTile(69.1723, 34.5553, 8);
      expect(classifyTile(8, kx, ky)).toBe('outside');

      // Rawalpindi (Pakistan)
      const [rx, ry] = lngLatToTile(73.0479, 33.5651, 9);
      expect(classifyTile(9, rx, ry)).toBe('outside');

      // Karachi (Pakistan)
      const [kax, kay] = lngLatToTile(67.0011, 24.8607, 8);
      expect(classifyTile(8, kax, kay)).toBe('outside');

      // Mandalay (Myanmar)
      const [mx, my] = lngLatToTile(96.0891, 21.9588, 9);
      expect(classifyTile(9, mx, my)).toBe('outside');

      // Lhasa (China/Tibet)
      const [lx, ly] = lngLatToTile(91.1409, 29.6456, 8);
      expect(classifyTile(8, lx, ly)).toBe('outside');

      // Dhaka (Bangladesh)
      const [bx, by] = lngLatToTile(90.4125, 23.8103, 9);
      expect(classifyTile(9, bx, by)).toBe('outside');
    });

    it('classifies border tiles along frontiers as border', () => {
      // Wagah border tile at z=12
      const [wx, wy] = lngLatToTile(74.5741, 31.6047, 12);
      expect(classifyTile(12, wx, wy)).toBe('border');
    });
  });

  describe('handleClippedRailwayTile', () => {
    it('immediately returns null data for tiles outside India without network request', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch');
      const abortController = new AbortController();

      // Request tile for Kabul (Afghanistan)
      const [kx, ky] = lngLatToTile(69.1723, 34.5553, 8);
      const url = `${CLIPPED_ORM_PROTOCOL}://tiles.openrailwaymap.org/standard/8/${kx}/${ky}.png`;

      const result = await handleClippedRailwayTile({ url }, abortController);
      expect(result).toEqual({ data: null });
      expect(fetchSpy).not.toHaveBeenCalled();

      fetchSpy.mockRestore();
    });

    it('fetches inside tile directly without canvas clipping overhead', async () => {
      const mockBuffer = new ArrayBuffer(8);
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        status: 200,
        arrayBuffer: async () => mockBuffer,
      } as Response);

      const abortController = new AbortController();
      // Delhi tile
      const [dx, dy] = lngLatToTile(77.209, 28.6139, 9);
      const url = `${CLIPPED_ORM_PROTOCOL}://tiles.openrailwaymap.org/standard/9/${dx}/${dy}.png`;

      const result = await handleClippedRailwayTile({ url }, abortController);
      expect(fetchSpy).toHaveBeenCalledTimes(1);
      expect(result.data).toBe(mockBuffer);

      fetchSpy.mockRestore();
    });
  });
});
