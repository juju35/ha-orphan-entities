# Changelog

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
