"""Diagnostics: the entry's options and the last scan, with personal data redacted."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import (
    CONF_ACCESS_TOKEN,
    CONF_ADDRESS,
    CONF_API_KEY,
    CONF_EMAIL,
    CONF_HOST,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_PASSWORD,
    CONF_TOKEN,
    CONF_URL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant

from . import OrphanEntitiesConfigEntry

# Config entry titles are often an account (email, username) or a host: redacted with the usual secrets.
TO_REDACT = {
    CONF_ACCESS_TOKEN,
    CONF_ADDRESS,
    CONF_API_KEY,
    CONF_EMAIL,
    CONF_HOST,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_PASSWORD,
    CONF_TOKEN,
    CONF_URL,
    CONF_USERNAME,
    "entry_title",
    "plate",
    "title",
    "tracking_number",
    "vin",
}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: OrphanEntitiesConfigEntry) -> dict[str, Any]:
    scanner = entry.runtime_data
    return async_redact_data(
        {
            "entry": {"title": entry.title, "data": dict(entry.data), "options": dict(entry.options)},
            "scanner": {
                "ready": scanner.ready,
                "started_at": scanner.started_at.isoformat() if scanner.started_at else None,
                "next_scan": scanner.next_scan.isoformat() if scanner.next_scan else None,
                "last_scan": scanner.last_scan.isoformat() if scanner.last_scan else None,
                "removed": scanner.removed,
                "counts": scanner.counts(),
                "entities": [
                    {**o.as_dict(), "used_by": scanner.references.get(o.entity_id, [])} for o in scanner.orphans
                ],
                "devices": [d.as_dict() for d in scanner.devices],
            },
        },
        TO_REDACT,
    )
