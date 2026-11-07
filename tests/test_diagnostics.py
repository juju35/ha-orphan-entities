"""Tests for the Orphan Entities diagnostics."""

from __future__ import annotations

from http import HTTPStatus

from homeassistant.components.diagnostics import REDACTED
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .test_init import RESTORED, _entity, _integration, _scan, _setup


async def test_diagnostics(hass: HomeAssistant, hass_client) -> None:
    """The options and the last scan are returned, the config entry titles (accounts, hosts) redacted."""
    account = _integration(hass, "acme")
    hass.config_entries.async_update_entry(account, title="jane.doe@example.com")
    orphan = _entity(hass, "acme", "old_lamp", STATE_UNAVAILABLE, account, attributes=RESTORED)
    entry = await _setup(hass)
    await _scan(hass)

    assert await async_setup_component(hass, "diagnostics", {})
    client = await hass_client()
    response = await client.get(f"/api/diagnostics/config_entry/{entry.entry_id}")
    assert response.status == HTTPStatus.OK
    data = (await response.json())["data"]

    assert "jane.doe" not in str(data)
    assert data["entry"]["options"] == dict(entry.options)
    assert data["entry"]["title"] == REDACTED
    scanner = data["scanner"]
    assert scanner["ready"] is True
    assert scanner["last_scan"]
    assert scanner["counts"]["not_provided"] == 1
    [item] = scanner["entities"]
    assert item["entity_id"] == orphan
    assert item["reason"] == "not_provided"
    assert item["entry_title"] == REDACTED
    assert item["used_by"] == []
    assert scanner["devices"] == []
