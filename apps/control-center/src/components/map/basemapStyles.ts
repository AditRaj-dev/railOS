import type { StyleSpecification } from 'maplibre-gl';

export const OSM_STREET_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    'osm-street': {
      type: 'raster',
      tiles: [
        'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      ],
      tileSize: 256,
      maxzoom: 19,
      attribution: '© OpenStreetMap contributors',
    },
  },
  layers: [
    {
      id: 'osm-street-layer',
      type: 'raster',
      source: 'osm-street',
      minzoom: 0,
      maxzoom: 19,
    },
  ],
};

export interface BasemapPreset {
  id: string;
  label: string;
  description: string;
  style: string | StyleSpecification;
}

export const SATELLITE_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    'esri-satellite': {
      type: 'raster',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      ],
      tileSize: 256,
      maxzoom: 19,
      attribution: 'Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
    },
  },
  layers: [
    {
      id: 'satellite-layer',
      type: 'raster',
      source: 'esri-satellite',
      minzoom: 0,
      maxzoom: 19,
    },
  ],
};

export const BASEMAP_PRESETS: BasemapPreset[] = [
  {
    id: 'street',
    label: 'Street (OSM)',
    description: 'OpenStreetMap standard map with buildings, blocks, roads, and cities',
    style: OSM_STREET_STYLE,
  },
  {
    id: 'satellite',
    label: 'Satellite',
    description: 'High-resolution global satellite and aerial imagery',
    style: SATELLITE_STYLE,
  },
];
