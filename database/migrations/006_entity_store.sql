-- Migration 006: per-entity storage.
--
-- Replaces railos_state, which held the ENTIRE application — every asset,
-- ticket, plan, possession and evidence item — as one JSONB blob in a single
-- row, rewritten in full on every mutation. That row was not queryable, not
-- indexable, and made concurrent writes last-writer-wins.
--
-- Each entity now gets its own row. The payload stays JSONB because the domain
-- models are deeply nested Pydantic trees; promote individual fields to
-- generated columns if a query ever needs to filter on them in SQL.

CREATE TABLE IF NOT EXISTS railos_entity (
  collection text        NOT NULL,
  id         text        NOT NULL,
  payload    jsonb       NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (collection, id)
);

CREATE INDEX IF NOT EXISTS idx_railos_entity_collection ON railos_entity (collection);

-- Append-only. The event log was previously rewritten wholesale inside the
-- snapshot on every commit.
CREATE TABLE IF NOT EXISTS railos_event (
  sequence    bigserial   PRIMARY KEY,
  event_id    text        NOT NULL,
  type        text        NOT NULL,
  entity_id   text        NOT NULL,
  actor       text        NOT NULL,
  payload     jsonb       NOT NULL,
  occurred_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_railos_event_entity ON railos_event (entity_id);
CREATE INDEX IF NOT EXISTS idx_railos_event_type ON railos_event (type);

DROP TABLE IF EXISTS railos_state;
