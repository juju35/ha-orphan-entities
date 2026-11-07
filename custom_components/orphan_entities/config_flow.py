"""Config flow for Orphan Entities: a single entry, everything in the options."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.loader import async_get_integrations

from .const import (
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
    MAX_MINUTES,
    MAX_STALE_HOURS,
)


def _number(minimum: int, maximum: int, unit: str) -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(min=minimum, max=maximum, step=1, mode=NumberSelectorMode.BOX, unit_of_measurement=unit)
    )


def _multi(options: list[SelectOptionDict] | list[str]) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(options=options, multiple=True, custom_value=True, mode=SelectSelectorMode.DROPDOWN)
    )


async def _schema(hass: HomeAssistant, current: dict[str, Any]) -> vol.Schema:
    """Interval, grace period, stale entities, integrations and entities to ignore."""
    ignored: list[str] = list(current.get(CONF_IGNORED_INTEGRATIONS, []))
    # The integrations that own entities, set up or not.
    domains = {e.platform for e in er.async_get(hass).entities.values() if e.platform != DOMAIN} | set(ignored)
    integrations = await async_get_integrations(hass, domains)
    options = sorted(
        (
            SelectOptionDict(
                value=domain,
                label=f"{getattr(integrations.get(domain), 'name', domain)} ({domain})",
            )
            for domain in domains
        ),
        key=lambda o: o["label"].casefold(),
    )
    entities: list[str] = list(current.get(CONF_IGNORED_ENTITIES, []))
    # Device IDs (ignored orphan devices) share the option: shown with the device's name.
    devices = dr.async_get(hass)
    ignored_items = [
        SelectOptionDict(value=item, label=f"{device.name_by_user or device.name or item} ({item})")
        if (device := devices.async_get(item))
        else SelectOptionDict(value=item, label=item)
        for item in sorted(entities)
    ]
    return vol.Schema(
        {
            vol.Required(CONF_SCAN_INTERVAL, default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): _number(
                1, MAX_MINUTES, "min"
            ),
            vol.Required(CONF_GRACE_PERIOD, default=current.get(CONF_GRACE_PERIOD, DEFAULT_GRACE_PERIOD)): _number(
                0, MAX_MINUTES, "min"
            ),
            vol.Required(CONF_STALE_HOURS, default=current.get(CONF_STALE_HOURS, DEFAULT_STALE_HOURS)): _number(
                0, MAX_STALE_HOURS, "h"
            ),
            vol.Required(
                CONF_INCLUDE_UNKNOWN, default=current.get(CONF_INCLUDE_UNKNOWN, DEFAULT_INCLUDE_UNKNOWN)
            ): BooleanSelector(),
            vol.Optional(CONF_IGNORED_INTEGRATIONS, default=ignored): _multi(options),
            vol.Optional(CONF_IGNORED_ENTITIES, default=entities): _multi(ignored_items),
        }
    )


def _options(user_input: dict[str, Any]) -> dict[str, Any]:
    return {
        CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
        CONF_GRACE_PERIOD: int(user_input[CONF_GRACE_PERIOD]),
        CONF_STALE_HOURS: int(user_input[CONF_STALE_HOURS]),
        CONF_INCLUDE_UNKNOWN: bool(user_input[CONF_INCLUDE_UNKNOWN]),
        CONF_IGNORED_INTEGRATIONS: sorted(
            {d.strip() for d in user_input.get(CONF_IGNORED_INTEGRATIONS, []) if d.strip()}
        ),
        CONF_IGNORED_ENTITIES: sorted(
            {e.strip().lower() for e in user_input.get(CONF_IGNORED_ENTITIES, []) if e.strip()}
        ),
    }


class OrphanEntitiesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="Orphan Entities", data={}, options=_options(user_input))
        return self.async_show_form(step_id="user", data_schema=await _schema(self.hass, {}))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return OrphanEntitiesOptionsFlow()


class OrphanEntitiesOptionsFlow(OptionsFlow):
    """Change the interval, the grace period, the stale entities and what is ignored."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=_options(user_input))
        return self.async_show_form(
            step_id="init", data_schema=await _schema(self.hass, dict(self.config_entry.options))
        )
