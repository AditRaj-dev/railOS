# RailOS: OpenRailwayMap Architecture, Indian Railways Track & Station Integration Guide

## Overview

This guide provides a technical deconstruction of [OpenRailwayMap](https://www.openrailwaymap.org), resolves common integration pitfalls (such as the `HTTP 403 Forbidden` error), documents open-source Indian Railways station and track datasets, and supplies ready-to-run scripts for integrating railway visual layers over open maps (**Leaflet**, **MapLibre GL JS**, and **PostGIS/Python**).

---

## 1. OpenRailwayMap Architectural Deconstruction & Debugging

OpenRailwayMap (ORM) renders a worldwide topological view of railway infrastructure derived from OpenStreetMap (OSM) data.

### 1.1 Core Components

* **Frontend Engine:** Leaflet.js (`L.map`, `L.TileLayer`, `L.TileLayer.Grayscale`).
* **Base Layer:** OpenStreetMap standard tiles converted to grayscale via client-side canvas so track colors stand out.
* **Railway Overlay:** Transparent 256×256 PNG raster tiles loaded dynamically based on zoom and viewport coordinates.
* **Coordinate Range:** Global coverage, zoom levels `z=2` through `z=19`.

### 1.2 Tile Server Endpoints & Subdomains

* **Base URL Pattern:**
  ```text
  https://{s}.tiles.openrailwaymap.org/{style}/{z}/{x}/{y}.png
  ```
  Where `{s}` is one of the subdomains: `a`, `b`, or `c` (or bare `tiles.openrailwaymap.org`).

### 1.3 Available Railway Styles (`{style}`)

| Style Identifier | Display Name | Visual & Data Representation |
| :--- | :--- | :--- |
| **`standard`** | Infrastructure | All physical railway tracks (main lines, branch lines, sidings, yards, spurs, crossovers), station platforms, stop positions, and milestones. |
| **`maxspeed`** | Max Speeds | Color-coded speed brackets along track centerlines (e.g. 130 km/h, 110 km/h, 80 km/h, 30 km/h). |
| **`signals`** | Signalling & Protection | Signals, switch indicators, speed boards, mileposts, ETCS/Kavach balises, and automatic train protection assets. |
| **`electrified`** | Electrification | Overhead catenary (OHE), 3rd rail, non-electrified routes, and voltage specifications (e.g. 25 kV 50 Hz AC). |
| **`gauge`** | Track Gauge | Broad Gauge (1676 mm - standard IR mainline), Standard Gauge (1435 mm - Metro/RRTS), Meter Gauge (1000 mm), and Narrow Gauge. |

---

## 2. Debugging Pitfalls & Browser Security

### 2.1 The `HTTP 403 Forbidden` Issue

When attempting to fetch tiles using automated scripts (cURL, Python `urllib`, `requests`) without specific headers, the OpenRailwayMap tile server responds with:

```text
HTTP/1.1 403 Forbidden
```

#### Root Cause: Anti-Hotlinking & Bot Filtering
The tile server requires an active `Referer` or browser `User-Agent`. Automated scraping without a referring origin is throttled or blocked.

#### Verification & Solution:
* **In Web Browsers (Leaflet, MapLibre, React apps):** Browsers automatically supply `Referer: http://localhost:3000` or `Referer: https://yourdomain.com`. The tile server returns:
  ```http
  HTTP/1.1 200 OK
  Content-Type: image/png
  Access-Control-Allow-Origin: *
  ```
* **In Backend Scripts / Proxies:** Always supply a browser `User-Agent` and a non-empty `Referer` header:
  ```python
  headers = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "Referer": "https://www.openrailwaymap.org/"
  }
  ```

---

## 3. Indian Railways Station & Track Datasets

Google Maps does **not** expose railway track vector geometry, station junction topologies, or IR station codes via public APIs. However, complete open-source alternatives are readily available.

### 3.1 All 8,990+ Indian Railways Stations (GeoJSON)

Maintained by the open-source **DataMeet** community:
* **Repository:** [datameet/railways](https://github.com/datameet/railways)
* **Direct GeoJSON URL:** `https://raw.githubusercontent.com/datameet/railways/master/stations.json`
* **Schema per Feature:**
  ```json
  {
    "type": "Feature",
    "geometry": {
      "type": "Point",
      "coordinates": [77.4294, 28.6692]
    },
    "properties": {
      "code": "GZB",
      "name": "Ghaziabad Junction",
      "zone": "NR",
      "state": "Uttar Pradesh",
      "address": "Ghaziabad, Uttar Pradesh"
    }
  }
  ```

### 3.2 Indian Railways Physical Track Geometries

* **Raster Overlay:** OpenRailwayMap tile layer covers the entire Indian subcontinent with high-density track switch details.
* **Vector Track Lines (LineString GeoJSON):** Available via the [Humanitarian Data Exchange (HDX) India Railways](https://data.humdata.org/dataset/hotosm_ind_railways) or extracted directly from OSM using the Overpass API query below.

---

## 4. Implementation Scripts

### 4.1 Standalone Leaflet HTML/JS Map (Interactive Track & Station Visualizer)

A complete single-file dashboard with dark-mode basemap, OpenRailwayMap style toggles, and live searchable Indian Railways stations:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Indian Railways Operations Map</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    html, body, #map { height: 100%; margin: 0; padding: 0; background: #0f1115; font-family: sans-serif; }
    .floating-card {
      position: absolute; top: 16px; left: 16px; z-index: 1000;
      background: rgba(15, 17, 21, 0.92); backdrop-filter: blur(8px);
      color: #e2e8f0; padding: 14px 18px; border-radius: 10px;
      border: 1px solid rgba(255, 255, 255, 0.12);
      box-shadow: 0 8px 24px rgba(0,0,0,0.6); width: 280px;
    }
    .floating-card h2 { margin: 0 0 6px 0; font-size: 15px; color: #38bdf8; }
    .floating-card p { margin: 0 0 12px 0; font-size: 12px; color: #94a3b8; }
    .search-input {
      width: 100%; padding: 8px 10px; box-sizing: border-box;
      background: #1e293b; border: 1px solid #475569; border-radius: 6px;
      color: #fff; font-size: 13px; outline: none; margin-bottom: 10px;
    }
    .search-input:focus { border-color: #38bdf8; }
    .layer-selector {
      width: 100%; padding: 6px 8px; background: #1e293b;
      border: 1px solid #475569; border-radius: 6px; color: #fff; font-size: 13px;
    }
    .leaflet-popup-content-wrapper { background: #1e293b; color: #f8fafc; border-radius: 8px; }
    .leaflet-popup-tip { background: #1e293b; }
  </style>
</head>
<body>
  <div id="map"></div>

  <div class="floating-card">
    <h2>Indian Railways Network</h2>
    <p>Tracks: OpenRailwayMap | Stations: DataMeet</p>
    <input id="stationSearch" class="search-input" type="text" placeholder="Search Code (e.g. NDLS, GZB)..." />
    <label style="font-size: 12px; color: #94a3b8; display: block; margin-bottom: 4px;">Track Layer Style:</label>
    <select id="trackStyle" class="layer-selector">
      <option value="standard" selected>Infrastructure (Tracks/Sidings)</option>
      <option value="maxspeed">Max Speeds</option>
      <option value="signals">Signalling & Safety</option>
      <option value="electrified">Electrification</option>
      <option value="gauge">Track Gauge</option>
    </select>
  </div>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const map = L.map('map', { center: [28.6139, 77.2090], zoom: 8, minZoom: 4, maxZoom: 19 });

    // CARTO Dark Matter Basemap
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; CARTO &copy; OpenStreetMap', subdomains: 'abcd', maxZoom: 19
    }).addTo(map);

    // OpenRailwayMap Overlay
    let currentStyle = 'standard';
    const trackLayer = L.tileLayer(`https://{s}.tiles.openrailwaymap.org/${currentStyle}/{z}/{x}/{y}.png`, {
      attribution: '&copy; OpenRailwayMap', subdomains: ['a', 'b', 'c'], maxZoom: 19, tileSize: 256
    }).addTo(map);

    document.getElementById('trackStyle').addEventListener('change', (e) => {
      currentStyle = e.target.value;
      trackLayer.setUrl(`https://{s}.tiles.openrailwaymap.org/${currentStyle}/{z}/{x}/{y}.png`);
    });

    // Load Indian Railways Stations
    const stationsLayer = L.layerGroup().addTo(map);
    let allStations = [];

    fetch('https://raw.githubusercontent.com/datameet/railways/master/stations.json')
      .then(res => res.json())
      .then(data => {
        allStations = data.features;
        function updateStations() {
          stationsLayer.clearLayers();
          const bounds = map.getBounds();
          const zoom = map.getZoom();

          allStations.forEach(st => {
            const [lon, lat] = st.geometry.coordinates;
            if (bounds.contains([lat, lon])) {
              if (zoom >= 10 || (zoom >= 7 && (st.properties.name.includes('Junction') || st.properties.name.includes('Central')))) {
                const marker = L.circleMarker([lat, lon], {
                  radius: zoom >= 12 ? 6 : 4,
                  fillColor: '#f59e0b', color: '#ffffff', weight: 1.5, opacity: 1, fillOpacity: 0.9
                });
                marker.bindPopup(`
                  <b>${st.properties.name}</b><br/>
                  Code: <b style="color: #f59e0b;">${st.properties.code}</b><br/>
                  Zone: ${st.properties.zone || 'N/A'}<br/>
                  State: ${st.properties.state || 'N/A'}
                `);
                stationsLayer.addLayer(marker);
              }
            }
          });
        }
        map.on('moveend', updateStations);
        updateStations();
      });

    // Station Search Jump
    document.getElementById('stationSearch').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const q = e.target.value.trim().toUpperCase();
        const match = allStations.find(st => st.properties.code.toUpperCase() === q || st.properties.name.toUpperCase().includes(q));
        if (match) {
          const [lon, lat] = match.geometry.coordinates;
          map.flyTo([lat, lon], 14);
        } else {
          alert(`Station "${q}" not found.`);
        }
      }
    });
  </script>
</body>
</html>
```

---

### 4.2 MapLibre GL JS / Next.js Integration (RailOS Control Center Stack)

For integrating directly into the primary frontend at `apps/control-center/src/components/map/GeographicMap.tsx`:

```typescript
import maplibregl from 'maplibre-gl';

export function attachOpenRailwayMapLayer(
  map: maplibregl.Map,
  style: 'standard' | 'maxspeed' | 'signals' | 'electrified' | 'gauge' = 'standard'
) {
  const sourceId = 'openrailwaymap-tiles';
  const layerId = 'openrailwaymap-layer';

  if (!map.getSource(sourceId)) {
    map.addSource(sourceId, {
      type: 'raster',
      tiles: [
        `https://a.tiles.openrailwaymap.org/${style}/{z}/{x}/{y}.png`,
        `https://b.tiles.openrailwaymap.org/${style}/{z}/{x}/{y}.png`,
        `https://c.tiles.openrailwaymap.org/${style}/{z}/{x}/{y}.png`,
      ],
      tileSize: 256,
      minzoom: 2,
      maxzoom: 19,
      attribution: 'Tracks: &copy; <a href="https://www.openrailwaymap.org/">OpenRailwayMap</a>',
    });
  }

  if (!map.getLayer(layerId)) {
    map.addLayer({
      id: layerId,
      type: 'raster',
      source: sourceId,
      paint: {
        'raster-opacity': 0.9,
        'raster-fade-duration': 200,
      },
    });
  }
}
```

---

### 4.3 Python Vector Track Extractor (Overpass API to GeoJSON)

To export railway track vectors for corridor analysis (e.g. Ghaziabad to Aligarh):

```python
import json
import urllib.parse
import urllib.request

def extract_railway_corridor(min_lat: float, min_lon: float, max_lat: float, max_lon: float, output_path: str):
    """
    Queries OpenStreetMap railway tracks for a bounding box
    and exports them as a clean GeoJSON FeatureCollection.
    """
    overpass_query = f"""
    [out:json][timeout:60];
    (
      way["railway"~"^(rail|narrow_gauge|light_rail|subway)$"]({min_lat},{min_lon},{max_lat},{max_lon});
    );
    out body;
    >;
    out skel qt;
    """

    endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
    ]

    data = urllib.parse.urlencode({"data": overpass_query}).encode("utf-8")
    headers = {"User-Agent": "RailOS/1.0 (Track Vector Extractor)"}

    payload = None
    for url in endpoints:
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=45) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                print(f"Success querying {url}")
                break
        except Exception as e:
            print(f"Failed {url}: {e}")

    if not payload:
        raise RuntimeError("All Overpass endpoints were unreachable.")

    elements = payload.get("elements", [])
    nodes = {e["id"]: (e["lon"], e["lat"]) for e in elements if e["type"] == "node"}

    features = []
    for elem in elements:
        if elem.get("type") == "way" and "nodes" in elem:
            coords = [nodes[n] for n in elem["nodes"] if n in nodes]
            if len(coords) >= 2:
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coords
                    },
                    "properties": {
                        "osm_id": elem["id"],
                        **elem.get("tags", {})
                    }
                })

    geojson = {"type": "FeatureCollection", "features": features}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)

    print(f"Exported {len(features)} track features to {output_path}")

if __name__ == "__main__":
    # Ghaziabad (GZB) to Aligarh (ALJN) Corridor BBox
    extract_railway_corridor(27.85, 77.40, 28.75, 78.15, "gzb_aljn_tracks.geojson")
```

---

## 5. Summary Architecture Recommendation

1. **For Interactive Frontend Display:**
   * Overlay **OpenRailwayMap standard raster tiles** on top of a dark basemap (CARTO Dark Matter or OpenFreeMap).
   * Overlay **DataMeet 8,990 Indian Railways stations** as interactive circle markers with tooltips and search.
2. **For RailOS Operations & Maintenance Planning:**
   * Store station points and track line vectors in **PostGIS (SRID 4326)**.
   * Serve high-density vector tiles via **Martin** tile server as defined in `MAP_TECH_STACK.md — RailOS Interactive Railway Map Architecture.md`.
   * Integrate live block schedules and train running status using the scrapers and feeds in `RailOS_Live_Feeds_and_Scraping_Sources.md`.
