"""Button that scans the entity registry now."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import OrphanEntitiesConfigEntry
from .entity import OrphanEntitiesEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OrphanEntitiesConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([ScanButton(entry.runtime_data, entry.entry_id, "scan")])


class ScanButton(OrphanEntitiesEntity, ButtonEntity):
    """Scan now (does nothing while Home Assistant is starting or within the grace period)."""

    async def async_press(self) -> None:
        self.scanner.async_scan()
