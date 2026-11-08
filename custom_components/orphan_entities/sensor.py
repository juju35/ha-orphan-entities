"""Sensors: orphaned entities (with their list) and last scan."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import OrphanEntitiesConfigEntry
from .const import MAX_LISTED
from .entity import OrphanEntitiesEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OrphanEntitiesConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    s = entry.runtime_data
    async_add_entities([OrphansSensor(s, entry.entry_id, "orphans"), LastScanSensor(s, entry.entry_id, "last_scan")])


class OrphansSensor(OrphanEntitiesEntity, SensorEntity):
    """Number of orphaned entities, listed in the attributes."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    # Rewritten at every scan and possibly long: kept out of the recorder database.
    _unrecorded_attributes = frozenset(
        {"entities", "devices", "next_scan", "ignored_integrations", "ignored_entities", "truncated"}
    )

    @property
    def native_value(self) -> int | None:
        return None if self.scanner.last_scan is None else len(self.scanner.orphans)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        orphans, devices = self.scanner.orphans, self.scanner.devices
        return {
            # Each with what still uses it (`used_by`): automations, scripts, scenes, groups, dashboards. Capped: the
            # attributes go to every open dashboard at each change.
            "entities": [
                {**o.as_dict(), "used_by": self.scanner.references.get(o.entity_id, [])} for o in orphans[:MAX_LISTED]
            ],
            "devices": [d.as_dict() for d in devices[:MAX_LISTED]],
            # How many orphan entities `entities` leaves out (0: complete).
            "truncated": max(0, len(orphans) - MAX_LISTED),
            # End of the grace period after a start (None once it is over): the card says when the first scan is due.
            "next_scan": self.scanner.next_scan.isoformat() if self.scanner.next_scan else None,
            "counts": self.scanner.counts(),
            "removed": self.scanner.removed,
            "stale_hours": self.scanner.stale_hours,
            "include_unknown": self.scanner.include_unknown,
            "ignored_integrations": sorted(self.scanner.ignored_integrations),
            "ignored_entities": sorted(self.scanner.ignored_entities),
        }


class LastScanSensor(OrphanEntitiesEntity, SensorEntity):
    """End of the last scan."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> datetime | None:
        return self.scanner.last_scan
