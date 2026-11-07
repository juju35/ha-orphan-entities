"""Find the orphaned entities in the entity registry, and remove them."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    EVENT_DEVICES_REMOVED,
    EVENT_REMOVED,
    MAX_BATCH,
    REASON_ENTRY_REMOVED,
    REASON_INTEGRATION_MISSING,
    REASON_NOT_PROVIDED,
    REASON_UNAVAILABLE,
    REASON_UNKNOWN,
    REASONS,
    STATELESS_DOMAINS,
)
from .references import async_dashboards, find_references

_LOGGER = logging.getLogger(__name__)


def _entry_ids(device: dr.DeviceEntry) -> list[str]:
    """Config entries of a device: its single `config_entry_id` since 2026.8, its `config_entries` set before."""
    if hasattr(device, "config_entry_id"):
        return [device.config_entry_id] if device.config_entry_id else []
    return list(device.config_entries)


@dataclass(frozen=True, slots=True)
class OrphanDevice:
    """A device of the registry whose integration entries were all removed: nothing will ever provide it again."""

    device_id: str
    name: str
    manufacturer: str | None
    model: str | None
    entities: int
    since: datetime | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "entities": self.entities,
            "since": self.since.isoformat() if self.since else None,
        }


@dataclass(frozen=True, slots=True)
class Orphan:
    """An entity of the registry that its integration no longer provides (or that has been stale for too long)."""

    entity_id: str
    name: str
    platform: str
    reason: str
    since: datetime | None
    entry_id: str | None
    entry_title: str | None
    device: str | None
    disabled: bool
    device_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "platform": self.platform,
            "reason": self.reason,
            "since": self.since.isoformat() if self.since else None,
            "entry_id": self.entry_id,
            "entry_title": self.entry_title,
            "device": self.device,
            "disabled": self.disabled,
        }


class OrphanScanner:
    """Lists the orphaned entities on demand and keeps the last result for the entities and the card."""

    def __init__(
        self,
        hass: HomeAssistant,
        grace_period: timedelta,
        stale_hours: int,
        include_unknown: bool,
        ignored_integrations: Iterable[str],
        ignored_entities: Iterable[str],
    ) -> None:
        self.hass = hass
        self.grace_period = grace_period
        self.stale = timedelta(hours=stale_hours) if stale_hours > 0 else None
        self.stale_hours = stale_hours
        self.include_unknown = include_unknown
        self.ignored_integrations = frozenset(ignored_integrations) - {DOMAIN}
        self.ignored_entities = frozenset(ignored_entities)
        # When Home Assistant started: no scan before started_at + grace_period. Set by async_setup_entry.
        self.started_at: datetime | None = None
        self.orphans: list[Orphan] = []
        self.devices: list[OrphanDevice] = []
        self.last_scan: datetime | None = None
        self.removed = 0
        # What still uses each orphan ({entity_id: [automation, script, scene, group or dashboard]}), found at each
        # scan; the dashboards (read asynchronously) are those of the previous scan until they have been read again.
        self.references: dict[str, list[dict[str, Any]]] = {}
        self._dashboards: list[dict[str, Any]] = []
        self._generation = 0
        self._listeners: list[Callable[[], None]] = []

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    @callback
    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    @property
    def ready(self) -> bool:
        """Home Assistant is running and its integrations had the grace period to set up their entities."""
        return (
            self.hass.state is CoreState.running
            and self.started_at is not None
            and dt_util.utcnow() >= self.started_at + self.grace_period
        )

    @property
    def next_scan(self) -> datetime | None:
        """End of the grace period, while the first automatic scan is still waiting for it."""
        if self.ready or self.started_at is None:
            return None
        return self.started_at + self.grace_period

    @callback
    def async_started(self) -> None:
        """Home Assistant has started: the grace period starts now; the sensor shows when the first scan is due."""
        if self.started_at is None:
            self.started_at = dt_util.utcnow()
        self._notify()

    @callback
    def async_scan(self, *, force: bool = False) -> bool:
        """Scan the entity registry; False (nothing done) while Home Assistant is starting.

        Automatic scans also wait for the grace period; `force` (a scan the user asked for) does not.
        """
        if self.hass.state is not CoreState.running or (not force and not self.ready):
            return False
        now = dt_util.utcnow()
        registry = er.async_get(self.hass)
        devices = dr.async_get(self.hass)
        loaded = self.hass.config.components
        found: list[Orphan] = []
        for e in list(registry.entities.values()):
            if e.platform == DOMAIN or e.platform in self.ignored_integrations or e.entity_id in self.ignored_entities:
                continue
            reason, since = self._classify(e, loaded, now)
            if reason is None:
                continue
            entry = self.hass.config_entries.async_get_entry(e.config_entry_id) if e.config_entry_id else None
            device = devices.async_get(e.device_id) if e.device_id else None
            state = self.hass.states.get(e.entity_id)
            found.append(
                Orphan(
                    entity_id=e.entity_id,
                    name=e.name
                    or e.original_name
                    or (state.attributes.get("friendly_name") if state else None)
                    or e.entity_id.split(".", 1)[1],
                    platform=e.platform,
                    reason=reason,
                    since=since,
                    entry_id=e.config_entry_id,
                    entry_title=entry.title if entry else None,
                    device=(device.name_by_user or device.name) if device else None,
                    disabled=e.disabled_by is not None,
                    device_id=e.device_id,
                )
            )
        found.sort(key=lambda o: (REASONS.index(o.reason), o.platform, o.entity_id))
        self.orphans = found
        self.devices = self._orphan_devices(registry, devices)
        self.last_scan = now
        self.references = find_references(self.hass, (o.entity_id for o in found), self._dashboards)
        self._notify()
        self._generation += 1
        self.hass.async_create_task(self._async_dashboard_references(self._generation))
        return True

    async def _async_dashboard_references(self, generation: int) -> None:
        """Read the dashboards again, then update the references if they changed (a newer scan wins)."""
        dashboards = await async_dashboards(self.hass)
        if generation != self._generation:
            return
        self._dashboards = dashboards
        references = find_references(self.hass, (o.entity_id for o in self.orphans), dashboards)
        if references != self.references:
            self.references = references
            self._notify()

    def _classify(self, e: er.RegistryEntry, loaded: set[str], now: datetime) -> tuple[str | None, datetime | None]:
        """Why `e` is listed (and since when), or (None, None)."""
        changed = getattr(e, "modified_at", None) or getattr(e, "created_at", None)
        if e.config_entry_id:
            entry = self.hass.config_entries.async_get_entry(e.config_entry_id)
            if entry is None:
                # Left behind by a removed integration: listed even when disabled.
                return REASON_ENTRY_REMOVED, changed
            if entry.disabled_by is not None or entry.state is not ConfigEntryState.LOADED:
                # A disabled or failing integration: its entities come back with it (Integration Watchdog's job).
                return None, None
        if e.disabled_by is not None:
            return None, None
        state = self.hass.states.get(e.entity_id)
        if state is None or state.attributes.get("restored") is True:
            since = state.last_changed if state else changed
            if not e.config_entry_id and e.platform not in loaded:
                return REASON_INTEGRATION_MISSING, since
            return REASON_NOT_PROVIDED, since
        if self.stale is None or now - state.last_changed < self.stale:
            return None, None
        if state.state == STATE_UNAVAILABLE:
            return REASON_UNAVAILABLE, state.last_changed
        if self.include_unknown and state.state == STATE_UNKNOWN and e.domain not in STATELESS_DOMAINS:
            return REASON_UNKNOWN, state.last_changed
        return None, None

    def _orphan_devices(self, registry: er.EntityRegistry, devices: dr.DeviceRegistry) -> list[OrphanDevice]:
        """Devices tied to config entries that no longer exist, every one of them (a device shared with a live
        entry is still provided). Their entities, if any, are listed above as `entry_removed`."""
        found: list[OrphanDevice] = []
        # Iterating the registry gives the device entries since 2026.11 (their IDs before): both are handled.
        for item in list(devices.devices):
            device = devices.async_get(item) if isinstance(item, str) else item
            if device is None:
                continue
            entry_ids = _entry_ids(device)
            if not entry_ids or any(self.hass.config_entries.async_get_entry(entry_id) for entry_id in entry_ids):
                continue
            if device.id in self.ignored_entities:
                continue
            found.append(
                OrphanDevice(
                    device_id=device.id,
                    name=device.name_by_user or device.name or device.model or device.id,
                    manufacturer=device.manufacturer,
                    model=device.model,
                    entities=len(er.async_entries_for_device(registry, device.id, include_disabled_entities=True)),
                    since=getattr(device, "modified_at", None) or getattr(device, "created_at", None),
                )
            )
        return sorted(found, key=lambda d: d.name.casefold())

    @callback
    def async_remove_devices(self, device_ids: Iterable[str]) -> list[str]:
        """Remove listed orphan devices (and their entities) from the registries; refuses the request if one isn't."""
        wanted = list(dict.fromkeys(device_ids))
        if not wanted:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_devices")
        listed = {d.device_id for d in self.devices}
        if unknown := [d for d in wanted if d not in listed]:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="not_orphan_device",
                translation_placeholders={"devices": ", ".join(unknown[:10])},
            )
        registry = dr.async_get(self.hass)
        removed: list[str] = []
        for device_id in wanted:
            if registry.async_get(device_id) is None:
                continue
            # The entity registry drops the device's entities with it.
            registry.async_remove_device(device_id)
            removed.append(device_id)
        _LOGGER.info("Removed %d orphaned devices: %s", len(removed), ", ".join(removed))
        self.hass.bus.async_fire(EVENT_DEVICES_REMOVED, {"devices": removed})
        self.devices = [d for d in self.devices if d.device_id not in removed]
        gone = set(removed)
        self.orphans = [o for o in self.orphans if o.device_id not in gone]
        self._notify()
        return removed

    @callback
    def async_remove(self, entity_ids: Iterable[str]) -> list[str]:
        """Remove listed entities from the entity registry; refuses the whole request if one isn't listed."""
        wanted = list(dict.fromkeys(entity_ids))
        if not wanted:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_entities")
        if len(wanted) > MAX_BATCH:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="too_many", translation_placeholders={"max": str(MAX_BATCH)}
            )
        listed = {o.entity_id for o in self.orphans}
        if unknown := [e for e in wanted if e not in listed]:
            # Only what the last scan listed can go: never an entity the user didn't see as an orphan.
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="not_orphan",
                translation_placeholders={"entities": ", ".join(unknown[:10])},
            )
        registry = er.async_get(self.hass)
        removed: list[str] = []
        for entity_id in wanted:
            if registry.async_get(entity_id) is None:
                continue
            # Home Assistant drops the restored placeholder state with the registry entry.
            registry.async_remove(entity_id)
            removed.append(entity_id)
        _LOGGER.info("Removed %d orphaned entities: %s", len(removed), ", ".join(removed))
        self.removed += len(removed)
        self.hass.bus.async_fire(EVENT_REMOVED, {"entities": removed})
        # The list is refreshed at once, even within the grace period (only what was listed is gone).
        self.orphans = [o for o in self.orphans if o.entity_id not in removed]
        self._notify()
        return removed

    def counts(self) -> dict[str, int]:
        counts = dict.fromkeys(REASONS, 0)
        for o in self.orphans:
            counts[o.reason] += 1
        return counts
