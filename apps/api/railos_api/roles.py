"""Role definitions, aliases, and normalisation for RailOS.

Standardises on a single role vocabulary across the API, auth boundaries,
and statutory authorities under Indian Railways rules (G&SR / ACTM / SEM / IRPWM).
"""

from __future__ import annotations

OPERATIONAL_ROLES: frozenset[str] = frozenset({
    "ADMIN",
    "CONTROL_OFFICER",
    "PLANNER",
    "ENGINEERING",
    "SIGNAL_TELECOM",
    "TRACTION",
    "FIELD_SUPERVISOR",
    "MANAGEMENT",
    "STATION_MASTER",   # endorses T/351, closes the block on station instrument
    "TPC",              # Traction Power Controller: issues/cancels ETR-3 / PTW
})

ROLE_ALIASES: dict[str, str] = {
    "SUPERVISOR": "FIELD_SUPERVISOR",
    "DISPATCHER": "CONTROL_OFFICER",
    "INSPECTOR": "MANAGEMENT",
}


def normalize_role(raw: str | None) -> str:
    """Normalise any role string or legacy alias into canonical OPERATIONAL_ROLES."""
    if not raw:
        return ""
    cleaned = raw.strip().upper()
    return ROLE_ALIASES.get(cleaned, cleaned)
