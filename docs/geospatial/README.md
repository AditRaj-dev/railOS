# RailOS railway-geometry ingestion

This foundation turns an immutable, bounded Overpass JSON snapshot into two
deterministic artifacts:

- `network.geojson` for geographic rendering and tiling;
- `network.seed.json` for RailOS loaders and later conflation.

The current parser selects only `railway=rail` ways and
`railway=station|halt` nodes. It preserves OSM IDs and tags. It never invents
section IDs, station codes, zone/division membership, or official identifiers.
Imported records default to `planningEnabled: false` until a separately
reviewed conflation record maps them to an authorized RailOS entity.

## Offline verification and normalization

Run these commands from the repository root. They require Python 3.11+ and no
third-party packages or network access.

```powershell
python -m integrations.geospatial verify `
  --source datasets/geospatial/fixtures/overpass-bounded-synthetic.json `
  --manifest datasets/geospatial/fixtures/overpass-bounded-synthetic.manifest.json

python -m integrations.geospatial normalize-overpass `
  --source datasets/geospatial/fixtures/overpass-bounded-synthetic.json `
  --manifest datasets/geospatial/fixtures/overpass-bounded-synthetic.manifest.json `
  --output-dir .tmp/geospatial

python -m pytest tests/test_geospatial_manifest.py tests/test_geospatial_normalize.py tests/test_geospatial_schema.py -q
```

Every production snapshot directory is append-only and contains the payload
plus a manifest with source URI/type, retrieval and source timestamps, SHA-256,
licence/attribution, bbox/query, parser version, synthetic flag, and a concise
provenance label. A corrected capture gets a new `snapshotId`; never edit a
manifest already referenced by normalized output or the database.

## Prototype: bounded Overpass capture

Overpass is appropriate for a small corridor or proof of concept, not for a
national refresh. Define a tight WGS84 bounding box and request only the needed
railway tags. Keep the exact query in the manifest. Save the response before
normalizing it, record the response's `osm3s.timestamp_osm_base` as
`sourceTimestamp`, compute the payload SHA-256, and use the actual retrieval
time with an offset.

Follow the selected Overpass instance's usage policy: identify the application,
throttle manually initiated captures, cache responses, and do not poll it as a
live operational API. Tests always use committed fixtures.

## Bulk import: Geofabrik PBF

For a regional or India-wide refresh, use a published Geofabrik `.osm.pbf`
extract and its companion checksum rather than expanding the Overpass query.
Retain the unmodified download in object storage under its checksum. Record
`source.type: osm-pbf`, the Geofabrik URI, publication timestamp, covered bbox,
licence, attribution, and the exact Osmium filter/extract command in `query`.

A typical staging validation sequence is:

```text
sha256sum india-latest.osm.pbf
osmium fileinfo --extended india-latest.osm.pbf
osmium check-refs india-latest.osm.pbf
osmium extract --bbox=77.43,28.55,78.12,28.70 india-latest.osm.pbf -o corridor.osm.pbf
osmium tags-filter corridor.osm.pbf w/railway=rail n/railway=station,halt -o railway.osm.pbf
```

The committed Python parser does not parse PBF. Production PBF ingestion should
use Osmium/GDAL or osm2pgsql to stage selected features, then map them into the
tables in `database/migrations/004_geospatial_ingestion.sql`. Do not convert a
large PBF through a public Overpass service.

## Licence, attribution, and data boundaries

OpenStreetMap data is licensed under ODbL 1.0. A production map and derived
database must retain the required attribution (normally “© OpenStreetMap
contributors”), link to the copyright/licence information, and satisfy ODbL
share-alike obligations where they apply. Keep attribution in the source
manifest so downstream map responses cannot silently drop it. Obtain legal
review before distributing a derived database.

Red lines:

- OSM is community geometry, not official Indian Railways engineering or
  operational truth.
- Never label OSM `ref` values as official station codes without reviewed,
  separately sourced conflation evidence.
- Do not scrape NTES, CRIS, or third-party railway sites. Live train positions,
  blocks, possessions, and authority data require an authorized integration.
- Do not use imported geometry to authorize movement, protection, isolation,
  or maintenance work.
- Synthetic fixtures must remain visibly labelled synthetic and non-operational.

The UI-ready `provenance.label` is intentionally short; the adjacent
`attribution`, `source`, `licence`, timestamps, and snapshot ID provide the
descriptive detail needed by assistive technology and audit views.
