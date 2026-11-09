# Changelog

## 1.6.1 - 2026-11-09

### Maintenance
- No code change: released again to check the installation from the Marketplace.

## 1.6.0 - 2026-11-09

### Performance
- **Translations load on demand**: in the release zip, the frontend files keep English only (`orphan-entities-card.js` 167 KB → 78 KB) and each other language is its own `<file>.i18n.<lang>.js` file next to them, fetched the first time a card or the panel needs it. Home Assistant loads the card on every dashboard, so each page used to download and parse all 22 languages to use one. The cards and panel are defined once the page's language has arrived (a few milliseconds), so they render translated from the start.

### Maintenance
- The repository keeps every language in the sources: the release runs `scripts/split-frontend.mjs` before building the zip, and the Validate workflow checks the split on a copy (every table is rebuilt from the split files and compared).

## 1.5.0 - 2026-11-08

### What's new
- **Used by, for devices too**: each orphan device lists the automations and scripts that still use it (`used_by` in the `devices` attribute), shown with a **Used by n** badge in the card, and the removal confirmation asks to **Remove anyway** when some are in use. Translated in every language.
- **Remove every orphan device**: `orphan_entities.remove_devices` without `devices` removes every orphan device of the last scan, and the card's **Remove devices** without a selection now does so, including the devices the sensor leaves out; the new `devices_truncated` attribute and a note in the card say how many are left out of the list.

### Fixes
- After a removal, the card's message counts the entities or devices actually removed and those kept because they are no longer orphaned, instead of the number selected.

## 1.4.0 - 2026-11-07

### What's new
- **Orphan devices, one by one**: administrators select devices in the card, then **Ignore** or **Remove devices** act on the selection only (**Remove devices** without a selection still removes them all). The `orphan_entities.ignore` action takes device IDs (`devices`), shown by name in the **Ignored entities** option.
- **Checked again before removal**: `remove` and `remove_devices` classify each entity or device again first, keep the ones no longer orphaned since the scan and return them in `skipped`.
- **Device removal counts its entities**: the entities removed with orphan devices count in `removed` and are in an `orphan_entities_removed` event, and `remove_devices` takes at most 1000 devices at a time.
- **Lighter sensor**: the `entities` and `devices` attributes hold at most 250 items each (the new `truncated` attribute and the card say how many orphans are left out), and the dashboards are read again only when one is saved, not at every scan.
## 1.3.0 - 2026-11-07

### What's new
- **Diagnostics**: *Download diagnostics* on the integration returns its options and the last scan (orphan entities with their reason and what uses them, orphan devices, counts), with config entry titles and any secret redacted.

## 1.2.0 - 2026-11-07

### What's new
- **Used by**: before you remove orphans, the card shows what still uses each one. Every scan looks for the listed entities in the automations, scripts, scenes, groups and dashboards (storage mode) and adds a `used_by` list to each entity of the `entities` attribute. The full card shows an orange **Used by n** badge on those rows: its tooltip lists them, a click opens the list with links to the automation, script and scene editors and to the dashboards. When selected entities are still in use, the removal confirmation says how many and its button becomes **Remove anyway**. YAML dashboards are not scanned and templates are not resolved. Translated in every language.

## 1.1.0 - 2026-11-07

### What's new
- **Orphan devices**: the devices whose integration entries were all removed are listed (`devices` attribute of the orphans sensor) and shown under the entities in the full card, with **Remove devices** (administrators, after a confirmation) that deletes them from the device registry with their entities. New admin action `orphan_entities.remove_devices` (only the devices of the last scan) and event `orphan_entities_devices_removed`. Translated in every language.

## 1.0.7 - 2026-11-07

### Fixes
- `hide_when_empty`: a hidden card shows again while the dashboard is edited and in the card editor's preview, so that it can still be edited (before, it vanished from the editor as soon as nothing was wrong). A hidden card now also tells Lovelace (`card-visibility-changed`), so a sections view drops its slot instead of leaving a gap.

## 1.0.6 - 2026-11-07

### Fixes
- Header: the status pill keeps its text only while the text and the title both fit. On a narrow mini card, *Waiting for the first scan* left "Orp…" of the title; the pill now shows its dot alone (the text stays in its tooltip) whenever its text or the title would be cut, and fits again when the card is resized. The title keeps at least 45 % of the header, the pill at most 60 %.

## 1.0.4 - 2026-11-05

### Fixed
- Mini card: while waiting for the first scan after a start, the chip only says when it is due (*in 9 minutes*, full status in its tooltip) instead of repeating the header's status, which squeezed the title.

## 1.0.3 - 2026-11-05

### What's new
- **Scan now** (button, `orphan_entities.scan` action, the card) no longer waits for the grace period after a start: it scans as soon as Home Assistant is up. Only the automatic scans wait for it.
- While the sensor is unknown after a start, the card says when the first scan is due (*Waiting for the first scan (in 7 minutes)*), from the new `next_scan` attribute of the **Orphaned entities** sensor.

## 1.0.2 - 2026-11-04

### Documentation
- README: images and links use absolute URLs, so the screenshots, icons, badges and links display in HACS (relative paths broke there).
- README: screenshots get a display size, so cards no longer show oversized in HACS and on GitHub.

## 1.0.1 - 2026-11-04

### What's new
- Added Romanian, Danish, Swedish, Bulgarian, Russian, Ukrainian, Hungarian, Slovak, Czech, Slovenian, Latvian and Greek translations: configuration, options, entities, actions, errors and the cards (`ro`, `da`, `sv`, `bg`, `ru`, `uk`, `hu`, `sk`, `cs`, `sl`, `lv`, `el`). The card editor offers the twelve languages.

## 1.0.0 - 2026-11-04

First release.

### What's new
- **Scan** of the entity registry for the entities their integration no longer provides: integration removed (config entry gone), integration not loaded (YAML platform), not provided (restored by Home Assistant), and optionally still provided but unavailable or unknown for too long (24 hours by default). Never during startup, nor during the grace period after it.
- **Orphaned entities** sensor with the list, **Last scan** sensor and **Scan now** button.
- Actions `orphan_entities.scan`, `orphan_entities.remove` (bulk removal from the entity registry, only of listed entities) and `orphan_entities.ignore`, for administrators; `orphan_entities_removed` event.
- **Lovelace card** bundled with the integration: search, integration and reason filters, selection (one by one or every match of the filters), **Remove** and **Ignore** in bulk with a confirmation at the top of the card.
- **Mini card**: the orphans by reason on two lines, with a detail button showing the full card; a reason's chip opens it filtered.
- English, French, German, Spanish, Italian, Dutch, European Portuguese, Polish and Serbian (Cyrillic and Latin).
