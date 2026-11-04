# Changelog

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
