"""Tests for Orphan Entities."""

from __future__ import annotations

import inspect
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import voluptuous as vol
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events, async_fire_time_changed

from custom_components.orphan_entities.const import (
    CARD_URL,
    CONF_GRACE_PERIOD,
    CONF_IGNORED_ENTITIES,
    CONF_IGNORED_INTEGRATIONS,
    CONF_INCLUDE_UNKNOWN,
    CONF_SCAN_INTERVAL,
    CONF_STALE_HOURS,
    DOMAIN,
    EVENT_REMOVED,
    REGISTRY_DEBOUNCE,
)

ORPHANS = "sensor.orphan_entities_orphaned_entities"
LAST_SCAN = "sensor.orphan_entities_last_scan"
BUTTON = "button.orphan_entities_scan_now"
OPTIONS = {
    CONF_SCAN_INTERVAL: 15,
    CONF_GRACE_PERIOD: 10,
    CONF_STALE_HOURS: 24,
    CONF_INCLUDE_UNKNOWN: True,
    CONF_IGNORED_INTEGRATIONS: [],
    CONF_IGNORED_ENTITIES: [],
}
# Admin actions return a response from Home Assistant 2025.1.
RESPONSE = "supports_response" in inspect.signature(async_register_admin_service).parameters
RESTORED = {"restored": True, "supported_features": 0}


def _integration(
    hass: HomeAssistant, domain: str, state: ConfigEntryState = ConfigEntryState.LOADED
) -> MockConfigEntry:
    entry = MockConfigEntry(domain=domain, title=domain.title())
    entry.add_to_hass(hass)
    entry.mock_state(hass, state)
    return entry


def _entity(
    hass: HomeAssistant,
    platform: str,
    key: str,
    value: str | None,
    entry: MockConfigEntry | None = None,
    domain: str = "sensor",
    attributes: dict | None = None,
    **kwargs,
) -> str:
    """A registry entity of `platform`, with the state `value` (None: no state)."""
    entity = er.async_get(hass).async_get_or_create(
        domain, platform, key, config_entry=entry, suggested_object_id=key, **kwargs
    )
    if value is not None:
        hass.states.async_set(entity.entity_id, value, attributes)
    return entity.entity_id


async def _setup(hass: HomeAssistant, **options) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, options={**OPTIONS, **options})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _scan(hass: HomeAssistant) -> dict[str, str]:
    """Scan now; {entity_id: reason} of the listed entities."""
    await hass.services.async_call(DOMAIN, "scan", {}, blocking=True)
    await hass.async_block_till_done()
    return _listed(hass)


def _listed(hass: HomeAssistant) -> dict[str, str]:
    return {e["entity_id"]: e["reason"] for e in hass.states.get(ORPHANS).attributes["entities"]}


async def test_config_flow(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_SCAN_INTERVAL: 30,
            CONF_GRACE_PERIOD: 5,
            CONF_STALE_HOURS: 0,
            CONF_INCLUDE_UNKNOWN: False,
            CONF_IGNORED_INTEGRATIONS: ["zha", "mqtt", " "],
            CONF_IGNORED_ENTITIES: ["Sensor.Kept ", "sensor.kept", ""],
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"] == {
        CONF_SCAN_INTERVAL: 30,
        CONF_GRACE_PERIOD: 5,
        CONF_STALE_HOURS: 0,
        CONF_INCLUDE_UNKNOWN: False,
        CONF_IGNORED_INTEGRATIONS: ["mqtt", "zha"],
        CONF_IGNORED_ENTITIES: ["sensor.kept"],
    }


async def test_single_instance(hass):
    await _setup(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] is FlowResultType.ABORT


async def test_options_flow(hass):
    entry = await _setup(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {**OPTIONS, CONF_STALE_HOURS: 48, CONF_IGNORED_INTEGRATIONS: ["acme"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options[CONF_STALE_HOURS] == 48
    assert entry.state is ConfigEntryState.LOADED
    attrs = hass.states.get(ORPHANS).attributes
    assert attrs["ignored_integrations"] == ["acme"]
    assert attrs["stale_hours"] == 48


async def test_reasons(hass: HomeAssistant, freezer: FrozenDateTimeFactory):
    """Each kind of orphan is listed with its reason; live, disabled and failing entities are not."""
    acme = _integration(hass, "acme")
    failing = _integration(hass, "gamma", ConfigEntryState.SETUP_RETRY)
    gone = _integration(hass, "delta")
    removed = _entity(hass, "delta", "old_node", None, gone, disabled_by=er.RegistryEntryDisabler.USER)
    # The integration removed without its entities (a registry left behind).
    hass.config_entries._entries.pop(gone.entry_id)

    live = _entity(hass, "acme", "lamp", "21", acme)
    not_provided = _entity(hass, "acme", "old_lamp", STATE_UNAVAILABLE, acme, attributes=RESTORED)
    no_state = _entity(hass, "acme", "never_added", None, acme)
    yaml_missing = _entity(hass, "old_yaml", "pump", STATE_UNAVAILABLE, attributes=RESTORED)
    retrying = _entity(hass, "gamma", "plug", STATE_UNAVAILABLE, failing, attributes=RESTORED)
    disabled = _entity(hass, "acme", "disabled", None, acme, disabled_by=er.RegistryEntryDisabler.USER)
    stale = _entity(hass, "acme", "dead", STATE_UNAVAILABLE, acme)
    unknown = _entity(hass, "acme", "never_reported", STATE_UNKNOWN, acme)
    button = _entity(hass, "acme", "identify", STATE_UNKNOWN, acme, domain="button")
    recent = _entity(hass, "acme", "flaky", STATE_UNAVAILABLE, acme)

    freezer.tick(timedelta(hours=25))
    # Back for a moment, then down again: unavailable for less than the stale delay.
    hass.states.async_set(recent, "on")
    hass.states.async_set(recent, STATE_UNAVAILABLE)
    await _setup(hass)

    listed = _listed(hass)
    assert listed == {
        removed: "entry_removed",
        yaml_missing: "integration_missing",
        not_provided: "not_provided",
        no_state: "not_provided",
        stale: "unavailable",
        unknown: "unknown",
    }
    for entity_id in (live, retrying, disabled, button, recent):
        assert entity_id not in listed
    state = hass.states.get(ORPHANS)
    assert state.state == "6"
    assert state.attributes["counts"] == {
        "entry_removed": 1,
        "integration_missing": 1,
        "not_provided": 2,
        "unavailable": 1,
        "unknown": 1,
    }
    item = next(e for e in state.attributes["entities"] if e["entity_id"] == not_provided)
    assert item["platform"] == "acme"
    assert item["entry_title"] == "Acme"
    assert item["since"]
    assert next(e for e in state.attributes["entities"] if e["entity_id"] == removed)["disabled"] is True
    assert hass.states.get(LAST_SCAN).state != STATE_UNKNOWN


async def test_stale_options(hass: HomeAssistant, freezer: FrozenDateTimeFactory):
    acme = _integration(hass, "acme")
    stale = _entity(hass, "acme", "dead", STATE_UNAVAILABLE, acme)
    unknown = _entity(hass, "acme", "never_reported", STATE_UNKNOWN, acme)
    freezer.tick(timedelta(hours=2))
    await _setup(hass, **{CONF_STALE_HOURS: 1, CONF_INCLUDE_UNKNOWN: False})
    assert _listed(hass) == {stale: "unavailable"}
    assert unknown not in _listed(hass)


async def test_stale_disabled(hass: HomeAssistant, freezer: FrozenDateTimeFactory):
    acme = _integration(hass, "acme")
    _entity(hass, "acme", "dead", STATE_UNAVAILABLE, acme)
    not_provided = _entity(hass, "acme", "old", STATE_UNAVAILABLE, acme, attributes=RESTORED)
    freezer.tick(timedelta(days=30))
    await _setup(hass, **{CONF_STALE_HOURS: 0})
    assert _listed(hass) == {not_provided: "not_provided"}


async def test_ignored(hass: HomeAssistant):
    acme = _integration(hass, "acme")
    beta = _integration(hass, "beta")
    kept = _entity(hass, "acme", "kept", STATE_UNAVAILABLE, acme, attributes=RESTORED)
    other = _entity(hass, "acme", "other", STATE_UNAVAILABLE, acme, attributes=RESTORED)
    _entity(hass, "beta", "plug", STATE_UNAVAILABLE, beta, attributes=RESTORED)
    await _setup(hass, **{CONF_IGNORED_INTEGRATIONS: ["beta"], CONF_IGNORED_ENTITIES: [kept]})
    assert _listed(hass) == {other: "not_provided"}


async def test_no_scan_while_starting(hass: HomeAssistant, freezer: FrozenDateTimeFactory):
    """Nothing is listed while Home Assistant starts nor during the grace period after it has started."""
    acme = _integration(hass, "acme")
    orphan = _entity(hass, "acme", "old", STATE_UNAVAILABLE, acme, attributes=RESTORED)
    hass.set_state(CoreState.starting)
    await _setup(hass)
    assert hass.states.get(ORPHANS).state == STATE_UNKNOWN
    assert hass.states.get(ORPHANS).attributes["next_scan"] is None
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "scan", {}, blocking=True)
    await hass.services.async_call("button", "press", {"entity_id": BUTTON}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get(ORPHANS).state == STATE_UNKNOWN

    hass.set_state(CoreState.running)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()
    # The sensor says when the first scan is due (end of the grace period), and the registry changes wait for it.
    assert hass.states.get(ORPHANS).attributes["next_scan"] == (dt_util.utcnow() + timedelta(minutes=10)).isoformat()
    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(ORPHANS).state == STATE_UNKNOWN

    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert _listed(hass) == {orphan: "not_provided"}
    assert hass.states.get(ORPHANS).attributes["next_scan"] is None


async def test_manual_scan_within_grace_period(hass: HomeAssistant):
    """A scan the user asks for (button, action) runs within the grace period: only the start refuses it."""
    acme = _integration(hass, "acme")
    orphan = _entity(hass, "acme", "old", STATE_UNAVAILABLE, acme, attributes=RESTORED)
    hass.set_state(CoreState.starting)
    await _setup(hass)
    hass.set_state(CoreState.running)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()
    assert hass.states.get(ORPHANS).state == STATE_UNKNOWN

    await hass.services.async_call("button", "press", {"entity_id": BUTTON}, blocking=True)
    await hass.async_block_till_done()
    assert _listed(hass) == {orphan: "not_provided"}
    assert hass.states.get(ORPHANS).attributes["next_scan"] is not None

    hass.states.async_set(orphan, "on")
    await hass.services.async_call(DOMAIN, "scan", {}, blocking=True)
    await hass.async_block_till_done()
    assert _listed(hass) == {}


async def test_scheduled_scan_and_registry_changes(hass: HomeAssistant, freezer: FrozenDateTimeFactory):
    acme = _integration(hass, "acme")
    await _setup(hass)
    assert hass.states.get(ORPHANS).state == "0"

    # A new orphan is found by the next scan...
    orphan = _entity(hass, "acme", "old", STATE_UNAVAILABLE, acme, attributes=RESTORED)
    freezer.tick(timedelta(seconds=REGISTRY_DEBOUNCE))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    # ...the registry change already triggered one.
    assert _listed(hass) == {orphan: "not_provided"}

    hass.states.async_set(orphan, "on")
    freezer.tick(timedelta(minutes=15))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert _listed(hass) == {}


async def test_remove(hass: HomeAssistant):
    acme = _integration(hass, "acme")
    a = _entity(hass, "acme", "a", STATE_UNAVAILABLE, acme, attributes=RESTORED)
    b = _entity(hass, "acme", "b", STATE_UNAVAILABLE, acme, attributes=RESTORED)
    live = _entity(hass, "acme", "live", "on", acme)
    await _setup(hass)
    events = async_capture_events(hass, EVENT_REMOVED)

    # An entity that isn't listed refuses the whole request.
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "remove", {"entities": [a, live]}, blocking=True)
    assert er.async_get(hass).async_get(a) is not None

    if RESPONSE:
        response = await hass.services.async_call(
            DOMAIN, "remove", {"entities": [a, b, a]}, blocking=True, return_response=True
        )
        assert response == {"removed": [a, b]}
    else:
        await hass.services.async_call(DOMAIN, "remove", {"entities": [a, b, a]}, blocking=True)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    assert registry.async_get(a) is None
    assert registry.async_get(b) is None
    assert registry.async_get(live) is not None
    # The restored placeholder states are gone with them.
    assert hass.states.get(a) is None
    assert events[0].data == {"entities": [a, b]}
    state = hass.states.get(ORPHANS)
    assert state.state == "0"
    assert state.attributes["removed"] == 2


async def test_remove_validation(hass: HomeAssistant):
    await _setup(hass)
    for entities in ([], ["not an id"]):
        with pytest.raises(vol.Invalid):
            await hass.services.async_call(DOMAIN, "remove", {"entities": entities}, blocking=True)


async def test_ignore(hass: HomeAssistant):
    acme = _integration(hass, "acme")
    a = _entity(hass, "acme", "a", STATE_UNAVAILABLE, acme, attributes=RESTORED)
    b = _entity(hass, "acme", "b", STATE_UNAVAILABLE, acme, attributes=RESTORED)
    entry = await _setup(hass)
    await hass.services.async_call(DOMAIN, "ignore", {"entities": [a]}, blocking=True)
    await hass.async_block_till_done()
    assert entry.options[CONF_IGNORED_ENTITIES] == [a]
    assert entry.state is ConfigEntryState.LOADED
    assert _listed(hass) == {b: "not_provided"}
    # The entity stays in the registry.
    assert er.async_get(hass).async_get(a) is not None

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "ignore", {"entities": ["sensor.nowhere"]}, blocking=True)


async def test_actions_not_loaded(hass: HomeAssistant):
    entry = await _setup(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    for service, data in (("scan", {}), ("remove", {"entities": ["sensor.a"]}), ("ignore", {"entities": ["sensor.a"]})):
        with pytest.raises(ServiceValidationError) as err:
            await hass.services.async_call(DOMAIN, service, data, blocking=True)
        assert err.value.translation_key == "not_loaded"


async def test_unload(hass):
    entry = await _setup(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


def _resources(hass: HomeAssistant):
    """The Lovelace resources collection: hass.data["lovelace"] is a dict before 2025.2, a dataclass after."""
    lovelace = hass.data["lovelace"]
    return lovelace["resources"] if isinstance(lovelace, dict) else lovelace.resources


def _card_urls(resources) -> list[str]:
    return [i["url"] for i in resources.async_items() if i["url"].split("?")[0] == CARD_URL]


async def test_card_is_served(hass: HomeAssistant, hass_client):
    await _setup(hass)
    client = await hass_client()
    response = await client.get(CARD_URL)
    assert response.status == 200
    assert "orphan-entities-card" in await response.text()


async def test_card_resource_back_after_remove_and_add(hass: HomeAssistant):
    assert await async_setup_component(hass, "lovelace", {})
    resources = _resources(hass)
    entry = await _setup(hass)
    assert len(_card_urls(resources)) == 1

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert _card_urls(resources) == []

    await _setup(hass)
    assert len(_card_urls(resources)) == 1


@pytest.mark.parametrize(
    ("key", "container"),
    [("mode", dict), ("resource_mode", dict), ("mode", SimpleNamespace), ("resource_mode", SimpleNamespace)],
)
async def test_card_resource_with_lovelace_data_variants(hass: HomeAssistant, key: str, container: type):
    assert await async_setup_component(hass, "lovelace", {})
    resources = _resources(hass)
    hass.data["lovelace"] = container(**{key: "storage", "resources": resources, "dashboards": {}})
    entry = await _setup(hass)
    assert len(_card_urls(resources)) == 1
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert _card_urls(resources) == []


async def test_card_resource_yaml_mode_untouched(hass: HomeAssistant):
    from homeassistant.components.lovelace.resources import ResourceYAMLCollection  # noqa: PLC0415

    assert await async_setup_component(hass, "lovelace", {})
    hass.data["lovelace"] = {"mode": "yaml", "resources": ResourceYAMLCollection([]), "dashboards": {}}
    with patch("custom_components.orphan_entities.add_extra_js_url") as add_js:
        await _setup(hass)
        await hass.async_block_till_done()
    add_js.assert_called_once()


async def test_orphan_devices(hass: HomeAssistant):
    """A device whose config entries are all gone is listed and can be removed, with its entities."""
    from homeassistant.exceptions import ServiceValidationError
    from homeassistant.helpers import device_registry as dr

    live = _integration(hass, "acme")
    gone = _integration(hass, "delta")
    devices = dr.async_get(hass)
    old = devices.async_get_or_create(config_entry_id=gone.entry_id, identifiers={("delta", "1")}, name="Old hub")
    kept = devices.async_get_or_create(config_entry_id=live.entry_id, identifiers={("acme", "1")}, name="Lamp")
    node = _entity(hass, "delta", "node", None, gone, device_id=old.id)
    hass.config_entries._entries.pop(gone.entry_id)
    await _setup(hass)
    await _scan(hass)

    attributes = hass.states.get(ORPHANS).attributes
    assert [(d["device_id"], d["name"], d["entities"]) for d in attributes["devices"]] == [(old.id, "Old hub", 1)]
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "remove_devices", {"devices": [kept.id]}, blocking=True)
    # Without return_response: before Home Assistant 2025.1 admin actions can't return one.
    await hass.services.async_call(DOMAIN, "remove_devices", {"devices": [old.id]}, blocking=True)
    await hass.async_block_till_done()
    assert devices.async_get(old.id) is None
    assert devices.async_get(kept.id) is not None
    assert er.async_get(hass).async_get(node) is None
    assert hass.states.get(ORPHANS).attributes["devices"] == []
    assert node not in _listed(hass)
