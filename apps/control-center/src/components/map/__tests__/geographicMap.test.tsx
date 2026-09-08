import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { GeographicMap, isWebGL2Supported } from '../GeographicMap';

describe('isWebGL2Supported', () => {
  const originalWebGL2 = window.WebGL2RenderingContext;
  afterEach(() => {
    window.WebGL2RenderingContext = originalWebGL2;
    vi.restoreAllMocks();
  });
  it('returns false when WebGL2RenderingContext is not defined on window', () => {
    // @ts-expect-error simulating missing WebGL2 context
    delete window.WebGL2RenderingContext;
    expect(isWebGL2Supported()).toBe(false);
  });
  it('returns false when getContext("webgl2") returns null', () => {
    window.WebGL2RenderingContext = function () {} as unknown as typeof WebGL2RenderingContext;
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);
    expect(isWebGL2Supported()).toBe(false);
  });
  it('returns true when WebGL2RenderingContext is available and getContext returns context', () => {
    window.WebGL2RenderingContext = function () {} as unknown as typeof WebGL2RenderingContext;
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation((type: string) => {
      if (type === 'webgl2') return {} as RenderingContext;
      return null;
    });
    expect(isWebGL2Supported()).toBe(true);
  });
});

describe('GeographicMap WebGL2 fallback rendering', () => {
  beforeEach(() => {
    // Simulate non-WebGL2 environment
    // @ts-expect-error delete WebGL2
    delete window.WebGL2RenderingContext;
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });
  it('renders graceful fallback overlay without throwing GPUInitializationError', () => {
    render(<GeographicMap mode="MAINTENANCE" styleUrl="https://demotiles.maplibre.org/style.json" />);
    // Should display the non-crashing WebGL2 fallback banner
    expect(screen.getByText('WebGL2 Acceleration Unavailable')).toBeInTheDocument();
    expect(
      screen.getByText(/WebGL2 is required to render the 3D accelerated geographic map/)
    ).toBeInTheDocument();
  });
  it('still presents keyboard browse map features even without WebGL2', () => {
    render(<GeographicMap mode="MAINTENANCE" styleUrl="https://demotiles.maplibre.org/style.json" />);
    expect(screen.getByText(/Browse map features/)).toBeInTheDocument();
  });
});
