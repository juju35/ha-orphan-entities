"""Orphan Entities: list the entities their integration no longer provides, remove them in bulk; bundled card."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import SIGNAL_CONFIG_ENTRY_CHANGED, ConfigEntry, ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import (
    CALLBACK_TYPE,
    CoreState,
    Event,
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from . import system_hub_notice
from .const import (
    ATTR_DEVICES,
    ATTR_ENTITIES,
    CARD_URL,
    CONF_GRACE_PERIOD,
    CONF_IGNORED_ENTITIES,
    CONF_IGNORED_INTEGRATIONS,
    CONF_INCLUDE_UNKNOWN,
    CONF_SCAN_INTERVAL,
    CONF_STALE_HOURS,
    DEFAULT_GRACE_PERIOD,
    DEFAULT_INCLUDE_UNKNOWN,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_STALE_HOURS,
    DOMAIN,
    EVENT_LOVELACE_UPDATED,
    MAX_BATCH,
    REGISTRY_DEBOUNCE,
    SERVICE_IGNORE,
    SERVICE_REMOVE,
    SERVICE_REMOVE_DEVICES,
    SERVICE_SCAN,
    VERSION,
)
from .scanner import OrphanScanner

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BUTTON, Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
ENTITIES_SCHEMA = vol.Schema({vol.Required(ATTR_ENTITIES): vol.All(cv.ensure_list, [cv.entity_id], vol.Length(min=1))})
# Without `devices`: every orphan device of the last scan.
DEVICES_SCHEMA = vol.Schema({vol.Optional(ATTR_DEVICES): vol.All(cv.ensure_list, [cv.string], vol.Length(min=1))})
# Entities, devices or both.
IGNORE_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Optional(ATTR_ENTITIES): vol.All(cv.ensure_list, [cv.entity_id]),
            vol.Optional(ATTR_DEVICES): vol.All(cv.ensure_list, [cv.string]),
        }
    ),
    cv.has_at_least_one_key(ATTR_ENTITIES, ATTR_DEVICES),
)

type OrphanEntitiesConfigEntry = ConfigEntry[OrphanScanner]


def _entry(hass: HomeAssistant) -> OrphanEntitiesConfigEntry:
    entries = [e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED]
    if not entries:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="not_loaded")
    return entries[0]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the card, load it on every dashboard and register the actions (admin: they change the registry)."""
    # The release splits the card translations into <file>.i18n.<lang>.js files (scripts/split-frontend.mjs):
    # served next to the card, which fetches the one it needs. A git checkout has none.
    languages = await hass.async_add_executor_job(_language_files, Path(__file__).parent / "frontend")
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(CARD_URL, str(Path(__file__).parent / "frontend" / "orphan-entities-card.js"), True),
            *(
                StaticPathConfig(
                    f"{CARD_URL.rsplit('/', 1)[0]}/{name}", str(Path(__file__).parent / "frontend" / name), True
                )
                for name in languages
            ),
        ]
    )

    async def _register(_: Event | None = None) -> None:
        if not await _async_register_resource(hass):
            # Dashboard resources in YAML mode: load the card on every page instead.
            add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")

    if hass.state is CoreState.running:
        await _register()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _register)

    async def scan(_call: ServiceCall) -> None:
        # Asked for by the user: scans even within the grace period, only Home Assistant starting refuses.
        if not _entry(hass).runtime_data.async_scan(force=True):
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="starting")

    async def remove(call: ServiceCall) -> ServiceResponse:
        # `skipped`: listed by the last scan but no longer orphaned, kept.
        removed, skipped = _entry(hass).runtime_data.async_remove(call.data[ATTR_ENTITIES])
        return {"removed": removed, "skipped": skipped}

    async def remove_devices(call: ServiceCall) -> ServiceResponse:
        removed, skipped, entities = _entry(hass).runtime_data.async_remove_devices(call.data.get(ATTR_DEVICES))
        return {"removed": removed, "skipped": skipped, "entities": entities}

    async def ignore(call: ServiceCall) -> None:
        entry = _entry(hass)
        entities = set(call.data.get(ATTR_ENTITIES, []))
        devices = set(call.data.get(ATTR_DEVICES, []))
        if len(entities) + len(devices) > MAX_BATCH:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="too_many", translation_placeholders={"max": str(MAX_BATCH)}
            )
        registry = er.async_get(hass)
        if unknown := sorted(e for e in entities if registry.async_get(e) is None):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="not_registered",
                translation_placeholders={"entities": ", ".join(unknown[:10])},
            )
        device_registry = dr.async_get(hass)
        if unknown := sorted(d for d in devices if device_registry.async_get(d) is None):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="device_not_registered",
                translation_placeholders={"devices": ", ".join(unknown[:10])},
            )
        # Device IDs share the ignored entities option: the scan skips a device whose ID is there.
        wanted = entities | devices
        current = set(entry.options.get(CONF_IGNORED_ENTITIES, []))
        if wanted <= current:
            return
        # The options change reloads the entry, which scans again without these entities.
        hass.config_entries.async_update_entry(
            entry, options={**entry.options, CONF_IGNORED_ENTITIES: sorted(current | wanted)}
        )

    async_register_admin_service(hass, DOMAIN, SERVICE_SCAN, scan)
    try:
        async_register_admin_service(
            hass, DOMAIN, SERVICE_REMOVE, remove, ENTITIES_SCHEMA, supports_response=SupportsResponse.OPTIONAL
        )
    except TypeError:
        # Before Home Assistant 2025.1 admin actions can't return a response: the list removed is then not returned.
        async_register_admin_service(hass, DOMAIN, SERVICE_REMOVE, remove, ENTITIES_SCHEMA)
    try:
        async_register_admin_service(
            hass,
            DOMAIN,
            SERVICE_REMOVE_DEVICES,
            remove_devices,
            DEVICES_SCHEMA,
            supports_response=SupportsResponse.OPTIONAL,
        )
    except TypeError:
        async_register_admin_service(hass, DOMAIN, SERVICE_REMOVE_DEVICES, remove_devices, DEVICES_SCHEMA)
    async_register_admin_service(hass, DOMAIN, SERVICE_IGNORE, ignore, IGNORE_SCHEMA)
    return True


def _storage_resources(hass: HomeAssistant) -> Any | None:
    """Return the dashboard resources collection when it is editable from the UI.

    hass.data["lovelace"] is a dict before 2025.2, then a dataclass whose `mode` field became `resource_mode` in 2026.2.
    """
    lovelace = hass.data.get("lovelace")
    if isinstance(lovelace, dict):
        mode, resources = lovelace.get("resource_mode", lovelace.get("mode")), lovelace.get("resources")
    else:
        mode = getattr(lovelace, "resource_mode", getattr(lovelace, "mode", None))
        resources = getattr(lovelace, "resources", None)
    return resources if mode == "storage" else None


async def _async_register_resource(hass: HomeAssistant) -> bool:
    """Add or update the card in Settings → Dashboards → Resources."""
    resources = _storage_resources(hass)
    if resources is None:
        return False
    url = f"{CARD_URL}?v={VERSION}"
    try:
        await resources.async_get_info()  # loads the collection from storage
        existing = [item for item in resources.async_items() if item.get("url", "").split("?")[0] == CARD_URL]
        if not existing:
            await resources.async_create_item({"res_type": "module", "url": url})
            return True
        if existing[0]["url"] != url:
            await resources.async_update_item(existing[0]["id"], {"res_type": "module", "url": url})
        for duplicate in existing[1:]:
            await resources.async_delete_item(duplicate["id"])
    except Exception:  # noqa: BLE001 - never block the integration on the card
        _LOGGER.exception("Could not register the Orphan Entities card as a dashboard resource")
        return False
    return True


async def async_setup_entry(hass: HomeAssistant, entry: OrphanEntitiesConfigEntry) -> bool:
    # Replaced by a System Hub module: a repair while System Hub is set up too.
    entry.async_on_unload(system_hub_notice.async_watch(hass, entry, "Orphan Entities"))
    if hass.state is CoreState.running:
        # async_setup runs once per start: after the entry was removed (which drops the card resource) and
        # added again, the resource has to come back without a restart.
        await _async_register_resource(hass)
    options = entry.options
    grace = timedelta(minutes=int(options.get(CONF_GRACE_PERIOD, DEFAULT_GRACE_PERIOD)))
    scanner = OrphanScanner(
        hass,
        grace,
        int(options.get(CONF_STALE_HOURS, DEFAULT_STALE_HOURS)),
        bool(options.get(CONF_INCLUDE_UNKNOWN, DEFAULT_INCLUDE_UNKNOWN)),
        options.get(CONF_IGNORED_INTEGRATIONS, []),
        options.get(CONF_IGNORED_ENTITIES, []),
    )
    # Set up with Home Assistant already running (added, options changed): no grace period.
    if hass.state is CoreState.running:
        scanner.started_at = dt_util.utcnow() - grace
    entry.runtime_data = scanner

    pending: CALLBACK_TYPE | None = None

    @callback
    def _scan_later(*_: Any) -> None:
        """Scan once a burst of registry or config entry changes is over."""
        nonlocal pending
        if pending is not None:
            pending()

        @callback
        def _run(_now: datetime) -> None:
            nonlocal pending
            pending = None
            scanner.async_scan()

        pending = async_call_later(hass, REGISTRY_DEBOUNCE, _run)

    @callback
    def _cancel() -> None:
        if pending is not None:
            pending()

    entry.async_on_unload(_cancel)
    entry.async_on_unload(hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, _scan_later))
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_CONFIG_ENTRY_CHANGED, _scan_later))

    @callback
    def _dashboard_saved(_event: Event) -> None:
        scanner.async_dashboards_changed()

    entry.async_on_unload(hass.bus.async_listen(EVENT_LOVELACE_UPDATED, _dashboard_saved))

    @callback
    def scheduled(_now: datetime) -> None:
        # Does nothing while Home Assistant is starting or within the grace period.
        scanner.async_scan()

    minutes = int(options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
    entry.async_on_unload(async_track_time_interval(hass, scheduled, timedelta(minutes=minutes)))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    def delayed(_now: datetime) -> None:
        scanner.async_scan()

    @callback
    def first_scan(_hass: HomeAssistant) -> None:
        scanner.async_started()
        if scanner.ready:
            scanner.async_scan()
        else:
            # Right after a start: once the integrations had the grace period to set up their entities.
            entry.async_on_unload(async_call_later(hass, grace, delayed))

    entry.async_on_unload(async_at_started(hass, first_scan))
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: OrphanEntitiesConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: OrphanEntitiesConfigEntry) -> None:
    """Drop the card resource."""
    # Before Home Assistant 2025.3 the entry being removed is still registered while this runs.
    if any(e.entry_id != entry.entry_id for e in hass.config_entries.async_entries(DOMAIN)):
        return
    if (resources := _storage_resources(hass)) is None:
        return
    for item in list(resources.async_items()):
        if item.get("url", "").split("?")[0] == CARD_URL:
            await resources.async_delete_item(item["id"])


async def _async_reload(hass: HomeAssistant, entry: OrphanEntitiesConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _language_files(frontend: Path) -> list[str]:
    """The translation files the release split out of the frontend files, if any."""
    return sorted(p.name for p in frontend.glob("*.i18n.*.js"))
