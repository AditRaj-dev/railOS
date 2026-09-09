-- users.role CHECK listed only 4 of the 9 UserRole values, so creating a
-- CONTROL_OFFICER / STATION_MASTER / TPC / ENGINEERING / SIGNAL_TELECOM
-- account failed with a 500 (CheckViolation). Widen it to the enum.
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE users ADD CONSTRAINT users_role_check CHECK (role IN (
  'SUPERVISOR', 'ADMIN', 'DISPATCHER', 'INSPECTOR',
  'STATION_MASTER', 'TPC', 'CONTROL_OFFICER', 'ENGINEERING', 'SIGNAL_TELECOM'
));
