# RailOS API

Run from the repository root with `python -m uvicorn railos_api.main:app --app-dir apps/api`.
The default backend is a thread-safe deterministic in-memory store. Every seed and adapter
response is labelled `synthetic: true` / `Synthetic Hackathon Simulation`.

Headers: `X-RailOS-User`, `X-RailOS-Role`, and optional `Idempotency-Key`.
PostgreSQL is selected explicitly with `RAILOS_STORAGE_BACKEND=postgres`; a missing or
invalid PostgreSQL configuration must be surfaced to the deployment rather than falling back.
