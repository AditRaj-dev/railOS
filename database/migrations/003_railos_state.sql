CREATE TABLE IF NOT EXISTS railos_state (
  namespace text NOT NULL,
  key text NOT NULL,
  payload jsonb NOT NULL,
  version bigint NOT NULL DEFAULT 1,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(namespace,key)
);
