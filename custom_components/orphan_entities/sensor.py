"""Sensors: orphaned entities (with their list) and last scan."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import OrphanEntitiesConfigEntry
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
    _unrecorded_attributes = frozenset({"entities", "ignored_integrations", "ignored_entities"})

    @property
    def native_value(self) -> int | None:
        return None if self.scanner.last_scan is None else len(self.scanner.orphans)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "entities": [o.as_dict() for o in self.scanner.orphans],
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
