# Map Data Sources & Basemap Research — RailOS

Research brief only. No application source was modified.

## Executive Summary

1. **No — Google Maps Platform cannot give you railway track geometry.** No Google Maps Platform product (JS API, Static, Places, Routes/Directions, Roads, Map Tiles, Datasets) exposes rail-line vector data. Rail only appears as painted pixels/vector tiles inside Google's own renderer.
2. Even if it did, the ToS forbids extracting it and forbids showing Google content on a non-Google map (i.e., inside MapLibre) — so it's a dead end twice over for RailOS's stack.
3. **Real track geometry for India should come from OpenStreetMap** (`railway=rail` ways, ODbL-licensed), pulled via Overpass for prototyping or a Geofabrik India `.pbf` extract for bulk/offline use. Coverage is good in metro areas, patchier elsewhere — expect manual QA/snapping for a production planning tool.
4. **Basemap: self-hosted Protomaps + PMTiles**, served from static storage (R2/S3/on-prem disk), is the right call given the air-gapped/on-prem control-room requirement — it needs no live tile server and costs near-zero.
5. **The MapLibre-never-paints bug** is almost certainly a Turbopack dev-mode failure to inline `NEXT_PUBLIC_MAP_STYLE_URL` inside the `next/dynamic({ssr:false})` chunk specifically — the string existing in the served JS is not proof it was substituted as a value. Fix: read the env var in the parent (already-inlined) component and pass it down as a prop, rather than reading `process.env` inside the dynamic chunk.

---

## Question 1 — Does Google Maps Platform give you railway track geometry? (No.)

**Definitive answer: No.** Checked every product that could plausibly return line geometry:

- **Maps JavaScript API / Geometry library** — only provides client-side math utilities (encode/decode polylines, spherical geometry helpers) for paths *you already have*. It returns nothing about what's rendered on the base map itself. [Geometry Library docs](https://developers.google.com/maps/documentation/javascript/geometry)
- **Maps Static API** — returns a raster PNG/JPEG image. No vector data, no way to pick out rail pixels as geometry.
- **Places API** — returns POIs (stations as points, if tagged), never line/track geometry.
- **Routes API / Directions (transit mode)** — returns a *computed route polyline* for a specific journey (e.g., "Route from A to B using train X"), encoded via the [polyline algorithm](https://developers.google.com/maps/documentation/routes/polylinedecoder). This is a routing answer for one itinerary, not the underlying rail network graph — you cannot enumerate "all track segments in this bounding box."
- **Roads API** — road-only (snap-to-road, speed limits); explicitly does not cover rail.
- **Map Tiles API (2D and Photorealistic 3D)** — serves pre-rendered raster/vector *tiles* or 3D tilesets for *display*. The vector tiles are for Google's own renderer; there is no documented, supported way to pull discrete "this is a rail LineString" features out of them.
- **Data-driven styling / Datasets API** — lets you *upload your own* data to style Google's map layers on top of Google's basemap. It does not expose Google's own street/rail network back to you.

**Conclusion: rail exists on Google Maps only as rendered pixels/vector-tiles inside Google's own map surface. There is no product, endpoint, or export that hands you rail centerline geometry as GeoJSON/polylines you can own or store.**

### Terms of Service constraints (even hypothetically)

From the [Google Maps Platform Terms of Service](https://cloud.google.com/maps-platform/terms), [Service Specific Terms](https://cloud.google.com/maps-platform/terms/maps-service-terms), and the verbatim clauses reproduced in [Cesium's third-party terms appendix](https://cesium.com/legal/terms-for-google/) (Appendix B-2, "Google Maps Content"):

- **§3.a — No scraping/extraction**: *"You will not export, extract, or otherwise scrape any content provided in or through Google Maps Content for use outside the Google Maps Content."*
- **§3.b — No caching** (beyond narrow exceptions): *"You will not cache Google Maps Content except as expressly permitted under the Maps Service Specific Terms."* Permitted exceptions are limited to caching Place IDs indefinitely and place coordinates for up to 30 days — nothing that covers a persisted track network.
- **§3.c — No derivative content**: *"You will not create content based on Google Maps Content"* — the appendix gives examples explicitly including tracing/digitizing roadways and building 3D/terrain models from Google imagery. Digitizing rail lines off Google imagery would fall squarely under this.
- **§3.e — No use with a non-Google map**: *"You will not use the Google Maps Content with or near a non-Google map in Your Application."* This directly forbids showing any Google Maps content (tiles, Places data, Street View) inside RailOS's MapLibre/deck.gl stack — you cannot even use Google as a decorative reference layer next to MapLibre.

So the ToS blocks the extraction *and* blocks combining Google content with MapLibre at all, independent of whether geometry access existed.

### Pricing / access (for completeness)

Google Maps Platform is pay-as-you-go across ~hundreds of per-SKU prices (roughly $2–$30 per 1,000 requests depending on product), with monthly free-tier allowances, and an API key **tied to an active Cloud Billing account is mandatory** even to stay within the free tier — there is no keyless/anonymous access. ([Woosmap 2026 pricing breakdown](https://www.woosmap.com/blog/google-maps-api-pricing-breakdown), [Radar's 2026 cost analysis](https://radar.com/blog/google-maps-api-cost), [Google's official pricing overview](https://developers.google.com/maps/billing-and-pricing/overview))

**Bottom line for the user's belief**: it is false. Google Maps Platform is not a source of queryable rail geometry, and even the rendered basemap can't legally sit next to MapLibre in this app.

---

## Question 2 — Where real Indian railway geometry actually comes from

### OpenStreetMap via Overpass API — best option for prototyping/targeted pulls

- **License**: ODbL (Open Database License) — share-alike on the *database*, but using it in a product and even modifying/redistributing derived data is allowed as long as you attribute OSM and, if you redistribute the *data itself*, keep it under ODbL (your own application code and rendered output are not required to be open-sourced — only a re-shared derivative database would be).
- **Query syntax** for a bounding box (Overpass QL), e.g. Ghaziabad–Aligarh corridor:
```
[out:json][timeout:60];
(
  way["railway"="rail"](28.30,77.30,27.85,78.20);
  way["railway"="rail"]["service"!~"yard|siding|spur"](28.30,77.30,27.85,78.20);
);
out body;
>;
out skel qt;
```
  (bbox order is `south,west,north,east`). Test interactively at [overpass-turbo.eu](https://overpass-turbo.eu/) before scripting it.
- **Rate limits**: the public Overpass instances (overpass-api.de, kumi.systems) are shared, best-effort, and throttle/reject large or frequent queries — fine for a bounded corridor query like the one above, unsuitable for pulling all-India rail in one shot.
- **Bulk alternative — Geofabrik**: [download.geofabrik.de/asia/india.html](https://download.geofabrik.de/asia/india.html) publishes a daily-updated `india-latest.osm.pbf` (~1.6 GB, full country, all OSM tags) importable with `osmium`/`osmosis`/`osm2pgsql`. This is the right path for a full offline dataset. For an even larger/global need, planet dumps exist at [planet.openstreetmap.org](https://planet.openstreetmap.org/) but are unnecessary here.
- **India-specific coverage quality** (per the [OSM wiki India/Railways page](https://wiki.openstreetmap.org/wiki/India/Railways)): metro/suburban networks (Mumbai, Delhi, Chennai, Kolkata) are mapped well; rural/inter-city trunk lines derive largely from Landsat-traced geometry plus some GPS-trace contributions (e.g., Konkan Railway), and there's a known problematic Vmap0 import in Maharashtra reported "up to 5 km off in places." **Treat OSM rail geometry as good-but-not-survey-grade** — plan for a QA/snapping pass before treating it as authoritative for block planning.
- **Commercial/pilot use**: yes, fully usable — attribution to "© OpenStreetMap contributors" required, and if you redistribute the raw extracted data (not just your rendered app) it stays under ODbL.

### OpenRailwayMap — visualization layer, not a geometry API

- It's a specialized **rendering/style layer on top of OSM data** (signals, electrification, max speed, gauge, etc.), not an independent geometry source — same underlying `railway=*` tags as plain OSM, imported to PostGIS via `osm2pgsql` and served as raster/vector tiles via a Martin-based [tile pipeline](https://github.com/OpenRailwayMap/openrailwaymap-tile-export).
- **Licence**: data is ODbL (same as OSM, since it *is* OSM data); the rendered tiles themselves are CC-BY-SA 2.0.
- **What it gives you**: tile URLs like `https://{s}.tiles.openrailwaymap.org/{style}/{z}/{x}/{y}.png` for visual overlay (electrification/signals styling) — useful as a reference layer, but for RailOS's own geometry you'd still pull the underlying `railway=*` ways from OSM/Overpass/Geofabrik directly, not "through" OpenRailwayMap.

### Indian government / institutional sources — mostly locked or too coarse

- **data.gov.in** — has a ["Railway Network" catalog entry](https://www.data.gov.in/catalog/railway-network) and a Transport GIS dataset, but these are tabular statistics (route-km, track-km by zone/state) rather than line-level geometry suitable for a planning UI. Treat as supplementary reference stats, not a geometry source.
- **Bhuvan (ISRO/NRSC)** — hosts an "Infrastructure (Road & Rail)" thematic layer, explicitly flagged as "version 1.0" quality, intended for national-scale visualization rather than operational segment-level planning. Access is via Bhuvan's own map viewer/WMS, not a clean open bulk-download API, and its terms are more restrictive/institutional than OSM's. ([Bhuvan wiki](https://bhuvan.nrsc.gov.in/wiki/index.php/Bhuvan_2D))
- **RailTel / CRIS / Indian Railways GIS ("Rail Radar"/NTES ecosystem)** — the *official* NTES train-position system (`enquiry.indianrail.gov.in/ntes`) and CRIS-run systems are **not open data**; they are internal/institutional systems with no public bulk export. Third-party wrappers like [RailRadar.in](https://railradar.in/docs) offer a commercial REST API (live running status, PNR, GeoJSON route geometry) built by reverse-engineering/aggregating NTES — useful for live train position, **not** a licensed source of authoritative track infrastructure geometry, and Indian Railways is reported to actively restrict/encrypt structured redistribution of this data. Do not treat this as a stable, licensable geometry source for a commercial product without direct confirmation from CRIS/Indian Railways.
- **GTFS**: Indian Railways does **not** publish an official GTFS or GTFS-Realtime feed. Community efforts have been discussed (see the [datameet mailing list thread](https://groups.google.com/g/datameet/c/UhdKhTADZIo)) but nothing production-grade and officially sanctioned exists as of writing.

**Practical conclusion for Q2**: OpenStreetMap (via Overpass for iteration, Geofabrik `.pbf` for bulk/offline) is the only source that is simultaneously (a) actually open, (b) has usable India coverage, and (c) is legally clean for a commercial/pilot product with simple attribution. Government sources are either too coarse (Bhuvan, data.gov.in) or not open at all (CRIS/NTES).

---

## Question 3 — Basemap / renderer recommendation

| Option | Self-hostable / air-gapped? | Cost | Notes |
|---|---|---|---|
| MapLibre + OpenFreeMap | No (relies on OpenFreeMap's free public instance) | $0 | No API key, but you don't control uptime/rate limits; not viable for air-gapped ops. |
| MapLibre + CARTO basemaps (Dark Matter etc.) | No | Free tier, commercial use allowed with attribution | Good dark styles out of the box; still a hosted dependency. |
| MapTiler | No (cloud) | Paid tiers beyond free quota; OSM Dark style is Cloud-only | Good dark cartography, but another external SaaS dependency and per-request billing. |
| Stadia Maps | No (cloud) | Paid beyond free tier | Similar tradeoffs to MapTiler. |
| Mapbox GL JS v3 | No, and license-incompatible with MapLibre's OSS stack (proprietary token/ToS) | Paid, per-load | Not a fit — RailOS is already on MapLibre/deck.gl; mixing in Mapbox reintroduces the same "content can't roam" ToS problem as Google, at a smaller scale. |
| **Protomaps + PMTiles, self-hosted** | **Yes — this is the point of the format** | Near-zero (a few GB of static file storage; egress-free on Cloudflare R2, or literally a local disk in an air-gapped deployment) | Best fit for a control-room system that must run on-prem/offline. |

### Protomaps + PMTiles, in detail

PMTiles is a single-file, HTTP-range-request-addressable tile archive — the client (MapLibre's `pmtiles://` protocol handler) reads only the byte ranges it needs directly from the file, so **no tile server process is required at all**: a static file host (or literally a file on local disk via a tiny static server, or even `file://` with the right setup) is sufficient. This is exactly the shape needed for an air-gapped rail control system.

Building an India extract:
1. Download the `pmtiles` CLI (single binary) from [Protomaps' GitHub releases](https://github.com/protomaps/go-pmtiles/releases).
2. Protomaps publishes a full-planet basemap PMTiles build daily (~120 GB) at `build.protomaps.com` / [maps.protomaps.com/builds](https://maps.protomaps.com/builds).
3. Extract just India by bounding box **without downloading the planet file** — the CLI does ranged reads against the remote archive:
   ```
   pmtiles extract https://build.protomaps.com/YYYYMMDD.pmtiles india.pmtiles \
     --bbox=68.0,6.5,97.5,37.5 --maxzoom=14
   ```
4. Host `india.pmtiles` on Cloudflare R2 (free egress), any S3-compatible bucket, or a local static file server for the air-gapped case; point MapLibre's style `sources` at it via the `pmtiles://` protocol (`pmtiles://https://.../india.pmtiles` or `pmtiles:///local/path/india.pmtiles`).

Realistic cost: "a few dollars a month, often $0" on R2; for a genuinely air-gapped on-prem deployment, cost is just local disk (a country-sized extract at zoom ≤14 is low single-digit GB). Compare to Google's per-tile-request billing ($1,000s/month at scale) — Protomaps is the only option that matches a control-room's operational constraints.

### MapLibre v6 compatibility

MapLibre GL JS v6 (current major as of this research) has real breaking changes vs v4/v5, per the [official migration guide](https://maplibre.org/maplibre-gl-js/docs/guides/v5-to-v6-migration-guide/) and [GitHub issue #6427](https://github.com/maplibre/maplibre-gl-js/issues/6427):
- **ESM-only distribution** — the UMD bundle is gone; `import maplibregl from 'maplibre-gl'` (default import) breaks — use `import * as maplibregl from 'maplibre-gl'` or named imports.
- **WebGL2 is mandatory** (no WebGL1 fallback) — relevant if the control-room hardware/browser is old or locked down.
- `GeoJSONSource.setData()` signature changed (second `waitForCompletion` param removed, no longer chainable).
- Custom shader `#pragma mapbox` directives must become `#pragma maplibre`.
- `zoomLevelsToOverscale` default changed (4), subtly affecting `queryRenderedFeatures` results at high zoom.

None of these are relevant to *why the basemap fails to paint* (that's a separate root cause below), but worth checking the import statement given the "never even a network request" symptom — a default-import failure under v6's ESM-only build would typically throw a hard error, not silently skip the request, so it's a secondary thing to rule out rather than the primary suspect.

### deck.gl: still the right overlay

`@deck.gl/maplibre`'s `MapboxOverlay` (the module was forked/renamed from `@deck.gl/mapbox` specifically to formalize MapLibre support) documents compatibility with MapLibre v4, v5, and v6 as of the 2026 RFC work on camera-roll synchronization ([deck.gl "What's New"](https://deck.gl/docs/whats-new), [MapboxOverlay docs](https://deck.gl/docs/api-reference/mapbox/mapbox-overlay)). For "thousands of rail segments," deck.gl's `PathLayer`/`GeoJsonLayer` with GPU-side binary attribute upload comfortably outperforms MapLibre's native vector-layer pipeline for frequently-recomputed or dynamically-styled data (e.g., block occupancy state changing color per segment in near-real-time) — that's deck.gl's specific strength. If the rail layer is closer to *static* cartography (rendered once, rarely restyled), plain MapLibre vector tiles from the PMTiles source would be simpler and avoid a second WebGL context. **Recommendation: keep deck.gl for the dynamic operational layers (block state, train positions), and consider moving purely-static reference geometry into the MapLibre vector source directly** — but this is an optimization, not a blocker; thousands of segments is well within deck.gl's comfort zone regardless.

---

## Question 4 — Why the MapLibre basemap never paints

**Most likely root cause: Turbopack dev-mode fails to inline `NEXT_PUBLIC_MAP_STYLE_URL` inside the specific chunk loaded by `next/dynamic(..., { ssr: false })`**, so at runtime `process.env.NEXT_PUBLIC_MAP_STYLE_URL` evaluates to `undefined` inside that component even though the *literal text* "NEXT_PUBLIC_MAP_STYLE_URL" is present somewhere in the served bundle.

Why this fits the exact symptom set:
- `NEXT_PUBLIC_*` inlining is textual substitution of `process.env.NEXT_PUBLIC_MAP_STYLE_URL` at build time — it only works on a **direct, static property access** in code the bundler actually processes as "needs replacing" for *that specific chunk*. There's a documented, reproduced issue where, under Turbopack, `NEXT_PUBLIC_` variables "load fine on the server but do not load at all (undefined) on the client" ([Next.js GitHub discussion #74624](https://github.com/vercel/next.js/discussions/74624)) — and dynamically-imported client-only chunks (exactly the `ssr:false` pattern here) are a separate part of the module graph from the main chunk, making them a plausible place for the substitution to be missed in dev builds.
- **Grepping the served JS chunk for the variable name is not proof it was substituted.** The variable's *name* can legitimately appear in a chunk (e.g. in an unreplaced `process.env.NEXT_PUBLIC_MAP_STYLE_URL` expression that Turbopack failed to rewrite, in a source-map comment, or in an adjacent conditional branch) while the actual runtime value used to construct `new maplibregl.Map({ style: ... })` is `undefined`. This exactly explains "present in the served JS chunk" + "MapLibre never issues a network request for the style URL": **if `style` is `undefined`/falsy, MapLibre never has a URL to fetch, so no request ever fires — it fails silently rather than erroring**, matching the observed behavior precisely.
- **Why deck.gl still renders**: the deck.gl `MapboxOverlay`/GPU canvas is independent of whether the MapLibre base style loaded — it just needs the `Map` instance to exist (for camera sync), not for tiles to have painted. So a `Map` constructed with no/invalid `style` still exists as an object, deck.gl attaches to it fine, and only the basemap tiles are silently absent.

**Contributing/compounding factor — React 19 StrictMode double-mount**: In dev, StrictMode intentionally mounts → cleans up → remounts every component once. If the `useEffect` that creates the `maplibregl.Map` calls `map.remove()` on cleanup and the second mount reuses a container ref or closure state that wasn't fully reset, MapLibre map instances are known to end up in a state where `"Style is not done loading"` errors or silently-broken instances occur on remount ([react-map-gl issue #1122](https://github.com/visgl/react-map-gl/issues/1122), [React StrictMode double-invoke effects issue](https://github.com/facebook/react/issues/25614)). This wouldn't by itself explain "zero network requests ever," but it can compound an already-undefined-style bug by making the *second* (StrictMode-surviving) mount attempt just as broken as the first.

### The fix

1. **Don't read `process.env.NEXT_PUBLIC_MAP_STYLE_URL` inside the `ssr:false` dynamically-imported component.** Read it in the parent component (part of the normally-compiled, correctly-inlined main chunk) and pass it down as a prop:
   ```tsx
   // parent (server or regular client component) — inlined reliably
   const MapView = dynamic(() => import('./MapView'), { ssr: false });
   const styleUrl = process.env.NEXT_PUBLIC_MAP_STYLE_URL; // inlined here
   // ...
   <MapView styleUrl={styleUrl} />
   ```
   ```tsx
   // MapView.tsx — no process.env reference at all
   export default function MapView({ styleUrl }: { styleUrl: string }) {
     useEffect(() => {
       if (!styleUrl) { console.error('styleUrl missing — check env inlining'); return; }
       const map = new maplibregl.Map({ container: ref.current!, style: styleUrl });
       return () => map.remove();
     }, [styleUrl]);
     ...
   }
   ```
2. **Add a runtime assertion**, not a grep-the-bundle check: `console.log('[map] styleUrl =', styleUrl)` inside the effect, right before constructing `new maplibregl.Map(...)`. If this logs `undefined`, the inlining theory is confirmed immediately — trust the running value over static bundle inspection.
3. **Guard StrictMode's double-mount** so the first (thrown-away) mount can't leave the second mount broken — track an `isCancelled`/`initialized` ref and only call `map.remove()` on genuine unmount, or reuse a single map instance across the double-invoke via a ref that survives the dev double-mount.
4. If the issue persists after (1)–(3), fall back to Webpack for `next dev` (drop `--turbopack`) to confirm whether Turbopack itself is the differentiator, and file/check against the open Next.js Turbopack env-inlining discussion linked above for a fix-version.

---

## Recommendation for RailOS

- **Geometry**: Overpass QL for iterative dev/QA (bounding-box pulls per corridor), Geofabrik `india-latest.osm.pbf` for the real bulk dataset feeding the planning database; budget time for a manual snapping/QA pass against known station locations given OSM's rural-coverage caveats.
- **Basemap**: Protomaps + PMTiles, self-hosted (R2/S3 today, local disk for any future air-gapped deployment), replacing both the synthetic `network.json` visualization layer and any dependency on a hosted tile SaaS.
- **Renderer**: keep MapLibre v6 + deck.gl `MapboxOverlay` — it's the correct pairing for dynamic block-state rendering at rail-network scale; just fix the prop-drilling of the style URL per Q4.

## Immediate next step

```bash
# 1. Pull a real Ghaziabad–Aligarh rail extract to replace/validate datasets/network.json
curl -X POST https://overpass-api.de/api/interpreter \
  --data-urlencode 'data=[out:json][timeout:60];
(
  way["railway"="rail"](27.85,77.30,28.30,78.20);
);
out body;
>;
out skel qt;' \
  -o E:/RailOS/datasets/ghaziabad_aligarh_osm_rail.json

# 2. (Bulk path) Get the full India extract for offline processing
curl -O https://download.geofabrik.de/asia/india-latest.osm.pbf

# 3. Build a self-hosted India PMTiles basemap extract (no planet download needed)
pmtiles extract https://build.protomaps.com/$(date +%Y%m%d).pmtiles \
  E:/RailOS/datasets/india_basemap.pmtiles \
  --bbox=68.0,6.5,97.5,37.5 --maxzoom=14
```

Then, in the app: fix the `NEXT_PUBLIC_MAP_STYLE_URL` prop-drilling per Q4 §"The fix" before re-testing the basemap paint issue — that is the blocking bug, independent of which tile source ends up behind it.
