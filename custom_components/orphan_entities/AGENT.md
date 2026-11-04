# Orphan Entities — Agent Context

## Purpose
Home Assistant custom integration that lists the entities of the entity registry that their integration no longer provides (or that have been unavailable/unknown for too long), so that they can be removed in bulk. It bundles a Lovelace card (filters, selection, bulk remove/ignore) and a mini card.

## Architecture

```
custom_components/orphan_entities/
├── __init__.py      # Static path + dashboard resource for the card, admin actions scan/remove/ignore, entry setup, interval, debounced rescan on entity registry / config entry changes, first scan after the grace period
├── scanner.py       # OrphanScanner: classify registry entries (reason + since), remove listed entities, counts
├── config_flow.py   # Single entry; options: scan_interval, grace_period, stale_hours (0 = off), include_unknown, ignored_integrations, ignored_entities
├── button.py        # button.*_scan_now
├── sensor.py        # orphans (count + entities/counts/removed/stale_hours/include_unknown/ignored_*), last_scan
├── entity.py        # Shared service device, listener on OrphanScanner
├── frontend/orphan-entities-card.js   # custom:orphan-entities-card + custom:orphan-entities-mini-card (subclass: compact view, detail button toggling the full view)
├── const.py / icons.json / services.yaml / translations/{en,fr,de,es,it,nl,pt,pt-BR,pl,sr,sr-Latn,ro,da,sv,bg,ru,uk,hu,sk,cs,sl,lv,el}.json / brand/
```

## Rules
- Reasons, in this order (`REASONS`): `entry_removed` (config_entry_id set, entry gone; listed even if the entity is disabled), `integration_missing` (no config entry, restored or no state, platform not in `hass.config.components`), `not_provided` (restored or no state, integration loaded), `unavailable` / `unknown` (state not restored, unchanged for `stale_hours`; `unknown` only with `include_unknown` and not for `STATELESS_DOMAINS`).
- Skipped: this domain, ignored integrations (platform) and entities, disabled entities (but `entry_removed`), entities of a disabled config entry or of one not LOADED (setup retry/error: Integration Watchdog's job, they come back with it).
- Never during startup: `async_scan` returns False unless `CoreState.running` and `now >= started_at + grace_period`. `started_at` is set when HA starts (`async_at_started`), or `now - grace` when the entry is set up with HA already running; the first scan is scheduled at the end of the grace period.
- Scans are synchronous (`@callback`, no await): no lock. Rescan `REGISTRY_DEBOUNCE` s after the last entity registry or config entry change, and every `scan_interval`.
- `remove` only removes entities of the last scan's list: any other refuses the whole request (`not_orphan`). Home Assistant drops the restored placeholder state with the registry entry. Fires `orphan_entities_removed`, updates the list at once. `ignore` adds to the `ignored_entities` option (entry reload).
- The card finds its entities by `platform` and `translation_key` in `hass.entities` (entity ID suffix as fallback). Only administrators get checkboxes and actions (admin actions). Filters, selection, confirmation and "show all" live on the card instance and are part of its render signature; the selection drops entities no longer listed.
- Card served at `/orphan_entities/orphan-entities-card.js`, added to the dashboard resources (storage mode) or loaded with `add_extra_js_url` (YAML mode); `_storage_resources()` handles the dict / dataclass (`mode`, then `resource_mode`) variants. Removing the entry drops the resource.

## Release
Bump `version` in manifest.json, `VERSION` in const.py and `ORPHAN_ENTITIES_CARD_VERSION` in the card, and add its CHANGELOG.md section; pushing to main publishes `vX.Y.Z` with `orphan_entities.zip` when that tag doesn't exist yet. Rerun notes with the "Update release notes" workflow (input `tag`).

## Tests
`pip install -r requirements_test.txt && pytest` (registry entities + `MockConfigEntry` with mock domains: a real domain would be loaded). Card: `node --test test/*.test.mjs` (the card file is evaluated in a `vm` context with stubs; compare its objects with `plain()`). Screenshots: `python scripts/screenshots.py` (Playwright, mock data with neutral names, English, brand images blocked, 16 px frame).
