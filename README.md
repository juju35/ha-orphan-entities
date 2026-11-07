# ha-orphan-entities

[![Marketplace](https://img.shields.io/badge/Marketplace-Custom-41BDF5.svg)](https://www.home-assistant.io/integrations/marketplace/)
[![HACS Validation](https://github.com/juju35/ha-orphan-entities/actions/workflows/hacs.yml/badge.svg)](https://github.com/juju35/ha-orphan-entities/actions/workflows/hacs.yml)
[![Validate](https://github.com/juju35/ha-orphan-entities/actions/workflows/validate.yml/badge.svg)](https://github.com/juju35/ha-orphan-entities/actions/workflows/validate.yml)
[![Lint](https://github.com/juju35/ha-orphan-entities/actions/workflows/lint.yml/badge.svg)](https://github.com/juju35/ha-orphan-entities/actions/workflows/lint.yml)
[![Release](https://img.shields.io/github/v/release/juju35/ha-orphan-entities)](https://github.com/juju35/ha-orphan-entities/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/juju35/ha-orphan-entities/blob/main/LICENSE)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/julienstep9)

<p align="center"><img src="https://raw.githubusercontent.com/juju35/ha-orphan-entities/main/custom_components/orphan_entities/brand/icon.png" alt="Orphan Entities" width="120"></p>

Home Assistant integration that tracks the orphaned entities of your entity registry: those their integration no longer provides, and optionally those unavailable or unknown for too long. It comes with a Lovelace card to filter, review and remove them in bulk.

<p align="center">
  <img src="https://raw.githubusercontent.com/juju35/ha-orphan-entities/main/screenshots/card.png" alt="Orphan Entities card with orphaned entities" width="420">
  <img src="https://raw.githubusercontent.com/juju35/ha-orphan-entities/main/screenshots/card-dark.png" alt="Orphan Entities card, dark theme" width="420">
</p>

Removed integrations, renamed devices and old YAML platforms leave entities behind in the registry. Home Assistant shows them one by one as "not provided"; Orphan Entities lists them all, tells you why each one is listed, and removes the ones you select in one go.

[![Open your Home Assistant instance and open a repository inside the Marketplace.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=juju35&repository=ha-orphan-entities&category=integration)

## Features

- **Scan** of the entity registry at a set interval (15 minutes by default), and a few seconds after the registry changes
- **Five reasons**, from the most to the least certain orphan: *Integration removed*, *Integration not loaded*, *Not provided*, then, for entities still provided, *Unavailable* and *Unknown* for longer than a set delay (24 hours by default)
- **Never during startup**: nothing is listed while Home Assistant starts, nor during the grace period after it has started (10 minutes by default), while the integrations set up their entities. The card then says when the first scan is due; **Scan now** does not wait for it
- **Bulk removal** from the entity registry, limited to the listed entities, with a confirmation
- **Used by**: each orphan shows what still uses it (automations, scripts, scenes, groups, dashboards), with links to their editors, and the confirmation warns before removing entities still in use
- **Orphan devices**: devices whose integration entries were all removed, listed under the entities and removed together (with their entities) from the device registry
- **Ignored integrations and entities**, in the options or with the card's **Ignore** button
- **Orphaned entities** sensor with the list, **Last scan** sensor, **Scan now** button
- `orphan_entities.scan`, `orphan_entities.remove`, `orphan_entities.remove_devices` and `orphan_entities.ignore` **actions** for administrators, `orphan_entities_removed` and `orphan_entities_devices_removed` **events**
- **Lovelace card** bundled with the integration: search, integration and reason filters, selection one by one or of every match, **Remove** and **Ignore** in bulk
- **Mini card**: the orphans by reason on two lines, with a detail button showing the full card
- English, French, German, Spanish, Italian, Dutch, European Portuguese, Polish, Serbian (Cyrillic and Latin), Romanian, Danish, Swedish, Bulgarian, Russian, Ukrainian, Hungarian, Slovak, Czech, Slovenian, Latvian and Greek; pt-BR uses the European Portuguese texts

## Prerequisites

- Home Assistant 2024.12 or newer
- Nothing else: the integration only reads Home Assistant's own registries, and its card is installed with it

## Installation

### Via the Marketplace (recommended)

Click the button below to add the repository directly:

[![Add to the Marketplace](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=juju35&repository=ha-orphan-entities&category=integration)

Then click **Install** and restart Home Assistant.

Or manually:

1. Open **Settings → Marketplace → Add from link** (top right; this needs a GitHub account connected)
2. Add `https://github.com/juju35/ha-orphan-entities` — Type: **Integration**
3. Open **Orphan Entities** and click **Install**
4. Restart Home Assistant

### Manual

Copy `custom_components/orphan_entities/` to `/config/custom_components/orphan_entities/`, then restart Home Assistant.

## Configuration

[![Add integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=orphan_entities)

**Settings → Devices & services → Add integration → Orphan Entities**. Change the options later with the **Configure** button.

| Option | Default | Description |
|---|---|---|
| Scan interval | 15 min | Minutes between two scans, from 1 to 1440. The registry is also scanned 10 seconds after it changes |
| Grace period after startup | 10 min | Minutes after Home Assistant has started before the first automatic scan, from 0 to 1440. A scan asked for (button, action) runs at once |
| Stale after | 24 h | Hours an entity still provided by its integration must have been unavailable (or unknown) to be listed, up to 8760. `0` lists only the entities no longer provided |
| Include unknown entities | on | Also list the entities unknown for that long. Buttons, scenes, events and other entities unknown by design are never listed |
| Ignored integrations | none | Integrations whose entities are never listed. The list offers the integrations that own entities; type a domain to add another one |
| Ignored entities | none | Entity IDs never listed. The card's **Ignore** button adds them here |

### What counts as orphaned

| Reason | When |
|---|---|
| Integration removed | The entity belongs to a config entry that no longer exists. Listed even when the entity is disabled |
| Integration not loaded | The entity has no config entry (YAML platform), Home Assistant only restored it, and its integration is not loaded |
| Not provided | Its integration is loaded but no longer creates it: Home Assistant only restored it ("not provided" in Home Assistant) |
| Unavailable | Still provided, `unavailable` for longer than **Stale after** |
| Unknown | Still provided, `unknown` for longer than **Stale after** (with **Include unknown entities**) |

Left out: disabled entities (but those of a removed integration), entities of a disabled integration or of one that failed to set up (they come back with it: that's the job of [Integration Watchdog](https://github.com/juju35/ha-integration-watchdog)), the ignored integrations and entities.

**Orphan devices** are the devices of the device registry whose config entries no longer exist, all of them (a device shared with a live entry is still provided). Removing one deletes it from the device registry with its entities, as Home Assistant does when an integration is removed cleanly.

### Used by

Before you remove an orphan, the integration tells you what still uses it, so that you don't break an automation. At each scan it looks for each listed entity in:

| Where | How | Link in the card |
|---|---|---|
| Automations | Home Assistant's own references of each automation (triggers, conditions, actions) | Automation editor, for automations with an `id` (those made in the UI) |
| Scripts | Same, for each script | Script editor |
| Scenes | The entities each scene sets | Scene editor, for scenes with an `id` |
| Groups | Old-style groups (`group.*`) and group helpers (light, switch, sensor… groups) | — |
| Dashboards | The configuration of each dashboard in storage mode (edited in the UI), searched for the entity ID | The dashboard |

Only the loaded integrations are asked: without automations, for instance, none is listed. Each entity gets a `used_by` list in the `entities` attribute (`type`: `automation`, `script`, `scene`, `group` or `dashboard`, `id`, `name`, `path`: the editor page or dashboard, or `null`).

Limits:

- **YAML dashboards** (and the dashboards of a YAML-mode Lovelace) are not scanned, nor are the YAML files themselves: a card defined there is not found
- **Templates are not resolved**: an entity named only inside a template (`{{ states('sensor.x') }}`), built from a variable, or targeted through an area, device or label is not found
- References are refreshed at each scan (every **Scan interval**, after registry changes, or with **Scan now**): an automation edited since then shows up at the next scan

Removing an entity deletes its entry from the entity registry, as its **Delete** button does in Home Assistant. Its history stays in the database. An *Unavailable* or *Unknown* entity is still provided by its integration: it comes back if the integration creates it again (after a reload or a restart).

### Entities

| Entity | Description |
|---|---|
| `button.orphan_entities_scan_now` | Scans now, even within the grace period (nothing while Home Assistant is starting) |
| `sensor.orphan_entities_orphaned_entities` | Number of orphaned entities (unknown until the first scan). Attributes: `entities` (list of `entity_id`, `name`, `platform`, `reason`, `since`, `entry_id`, `entry_title`, `device`, `disabled`, `used_by`: what still uses it, see [Used by](#used-by)), `next_scan` (end of the grace period after a start, until then), `counts` (per reason), `removed` (since Home Assistant started), `stale_hours`, `include_unknown`, `ignored_integrations`, `ignored_entities`, `devices` (orphan devices: `device_id`, `name`, `manufacturer`, `model`, `entities`, `since`). The lists are not recorded in the database |
| `sensor.orphan_entities_last_scan` | End of the last scan |

### Action `orphan_entities.scan`

Scans the entity registry now, even within the grace period. For administrators. Refused while Home Assistant is starting.

```yaml
action: orphan_entities.scan
```

### Action `orphan_entities.remove`

Removes entities from the entity registry. For administrators. Each one must be in the list of the last scan: otherwise nothing is removed. Returns the entities removed (Home Assistant 2025.1 or newer).

```yaml
action: orphan_entities.remove
data:
  entities:
    - sensor.old_temperature
    - light.old_lamp
```

### Action `orphan_entities.remove_devices`

Removes orphan devices, with their entities. Only the devices of the last scan's `devices` list: any other refuses the request. For administrators.

```yaml
action: orphan_entities.remove_devices
data:
  devices: 3b1f0c2e9d8a4f6b
response_variable: result  # {"removed": ["3b1f0c2e9d8a4f6b"]}
```

### Action `orphan_entities.ignore`

Adds entities to the **Ignored entities** option: they are no longer listed. For administrators.

```yaml
action: orphan_entities.ignore
data:
  entities: sensor.kept_on_purpose
```

### Event `orphan_entities_removed`

Fired after each removal, with `entities`, the entity IDs removed.

Notify when new orphans appear:

```yaml
triggers:
  - trigger: state
    entity_id: sensor.orphan_entities_orphaned_entities
conditions:
  - condition: template
    value_template: >
      {{ trigger.from_state.state | int(0) < trigger.to_state.state | int(0) }}
actions:
  - action: persistent_notification.create
    data:
      title: Orphan Entities
      message: "{{ trigger.to_state.state }} orphaned entities"
```

## Card

The integration serves the **Orphan Entities Card** and adds it to the dashboard resources (or loads it on every page when the resources are managed in YAML): no separate install. Add it from the card picker, or:

```yaml
type: custom:orphan-entities-card
```

| Orphaned entities | Selection | Confirmation |
|---|---|---|
| <img src="https://raw.githubusercontent.com/juju35/ha-orphan-entities/main/screenshots/card.png" alt="Card" width="400"> | <img src="https://raw.githubusercontent.com/juju35/ha-orphan-entities/main/screenshots/card-selected.png" alt="Card, two entities selected" width="400"> | <img src="https://raw.githubusercontent.com/juju35/ha-orphan-entities/main/screenshots/card-confirm.png" alt="Card, confirmation" width="400"> |
| <img src="https://raw.githubusercontent.com/juju35/ha-orphan-entities/main/screenshots/card-dark.png" alt="Card, dark theme" width="400"> | <img src="https://raw.githubusercontent.com/juju35/ha-orphan-entities/main/screenshots/card-selected-dark.png" alt="Card, two entities selected, dark theme" width="400"> | <img src="https://raw.githubusercontent.com/juju35/ha-orphan-entities/main/screenshots/card-confirm-dark.png" alt="Card, confirmation, dark theme" width="400"> |

| Used by | |
|---|---|
| <img src="https://raw.githubusercontent.com/juju35/ha-orphan-entities/main/screenshots/card-used.png" alt="Card, the list of what still uses an entity" width="400"> | <img src="https://raw.githubusercontent.com/juju35/ha-orphan-entities/main/screenshots/card-used-dark.png" alt="Card, the list of what still uses an entity, dark theme" width="400"> |

| Orphan devices | |
|---|---|
| <img src="https://raw.githubusercontent.com/juju35/ha-orphan-entities/main/screenshots/card-devices.png" alt="Card, orphan devices" width="400"> | <img src="https://raw.githubusercontent.com/juju35/ha-orphan-entities/main/screenshots/card-devices-dark.png" alt="Card, orphan devices, dark theme" width="400"> |

| Filtered on a reason | No orphan |
|---|---|
| <img src="https://raw.githubusercontent.com/juju35/ha-orphan-entities/main/screenshots/card-filtered.png" alt="Card filtered" width="400"> | <img src="https://raw.githubusercontent.com/juju35/ha-orphan-entities/main/screenshots/card-ok.png" alt="Card, no orphan" width="400"> |
| <img src="https://raw.githubusercontent.com/juju35/ha-orphan-entities/main/screenshots/card-filtered-dark.png" alt="Card filtered, dark theme" width="400"> | <img src="https://raw.githubusercontent.com/juju35/ha-orphan-entities/main/screenshots/card-ok-dark.png" alt="Card, no orphan, dark theme" width="400"> |

- **Header**: status (*n orphans*, no orphan, waiting for the first scan), time of the last scan and the **Scan now** button. On a narrow card the status takes a second line, shortens, then keeps only its coloured dot
- **Summary**: orphans, removed since Home Assistant started, ignored (listed on hover)
- **Filters**: search on the name, entity ID, integration, device and config entry; integration list; a chip per reason with its count
- **List**: for each entity, its integration's logo, name, entity ID, device, reason and for how long. No longer provided in red, stale in orange. A long list stops at **Rows shown**, then **Show all**
- **Used by**: an entity that an automation, a script, a scene, a group or a dashboard still uses gets an orange **Used by n** badge; its tooltip lists them, a click opens the list under the row, with links to their editors. When some selected entities are still in use, the removal confirmation says how many and asks to **Remove anyway**
- **Selection** (administrators only): click a row to select it; **Select the n shown** selects every entity matching the filters, including those past **Rows shown**. **Ignore** and **Remove** then act on the selection, after a confirmation at the top of the card (Escape cancels). Other users see the list without checkboxes

Every option is in the visual editor:

| Option | Default | Description |
|---|---|---|
| `entity` | found automatically | The **Orphaned entities** sensor |
| `title` | Orphan Entities | Card title |
| `show_stats` | `true` | Summary tiles |
| `show_filters` | `true` | Search, integration and reason filters |
| `max_rows` | `25` | Rows shown before **Show all**, from 1 to 500 |
| `scan_button` | `true` | **Scan now** button in the header. It presses the button entity, so any user who sees the card can scan |
| `hide_when_empty` | `false` | Hide the card while there is no orphan (always shown while editing the dashboard) |
| `language` | Home Assistant's | `en`, `fr`, `de`, `es`, `it`, `nl`, `pt`, `pl`, `sr`, `sr-Latn`, `ro`, `da`, `sv`, `bg`, `ru`, `uk`, `hu`, `sk`, `cs`, `sl`, `lv` or `el` |

### Mini card

`custom:orphan-entities-mini-card` shows the essentials on two lines: the icon, title, **Scan now** button and status, then a chip per reason with its count (*Not provided · 2*) and the time of the last scan. Search for **Orphan Entities Mini Card** when adding a card, or in YAML:

```yaml
type: custom:orphan-entities-mini-card
```

| Orphaned entities | No orphan | Zoomed in |
|---|---|---|
| <img src="https://raw.githubusercontent.com/juju35/ha-orphan-entities/main/screenshots/mini.png" alt="Mini card" width="400"> | <img src="https://raw.githubusercontent.com/juju35/ha-orphan-entities/main/screenshots/mini-ok.png" alt="Mini card, no orphan" width="400"> | <img src="https://raw.githubusercontent.com/juju35/ha-orphan-entities/main/screenshots/mini-zoom.png" alt="Mini card zoomed in" width="386"> |
| <img src="https://raw.githubusercontent.com/juju35/ha-orphan-entities/main/screenshots/mini-dark.png" alt="Mini card, dark theme" width="400"> | <img src="https://raw.githubusercontent.com/juju35/ha-orphan-entities/main/screenshots/mini-ok-dark.png" alt="Mini card, no orphan, dark theme" width="400"> | <img src="https://raw.githubusercontent.com/juju35/ha-orphan-entities/main/screenshots/mini-zoom-dark.png" alt="Mini card zoomed in, dark theme" width="386"> |

- The **detail** button (top right) switches the card to the full [card](#card), with the same options, and back, as does a click anywhere else on the page
- A reason's chip opens the full card filtered on that reason
- In a Sections view the card takes 6 columns by default, its minimum

It takes every option of the full card (they set its detail view), plus:

| Option | Default | Description |
|---|---|---|
| `zoom` | `true` | **Detail** button showing the full card. `false` removes it |

## How it works

At each interval, and 10 seconds after the last change of the entity registry or of a config entry, the integration goes through the entity registry, reads each entity's config entry and state, and classifies it. It then asks the automations, scripts, scenes and groups which listed entities they use, and searches the dashboards in storage mode for them (read once from storage, then from memory, after the scan). Entities only restored by Home Assistant carry `restored: true` in their state: their integration didn't create them. No automatic scan runs before Home Assistant has fully started and the grace period has passed; a scan asked for with the button or the action only waits for the start.

To debug:

```yaml
logger:
  logs:
    custom_components.orphan_entities: debug
```

## Development

```bash
pip install -r requirements_test.txt && pytest
node --test test/*.test.mjs        # card
python scripts/screenshots.py      # README screenshots (Playwright)
```

### Releasing

1. Bump the version in `custom_components/orphan_entities/manifest.json`, `const.py` (`VERSION`) and the card (`ORPHAN_ENTITIES_CARD_VERSION`)
2. Add a `## <version>` section at the top of [CHANGELOG.md](https://github.com/juju35/ha-orphan-entities/blob/main/CHANGELOG.md)
3. Push to `main`: the **Release** workflow creates the tag and the GitHub release with the changelog section as notes

## Translations

The integration and its card follow the language of Home Assistant. Currently supported:

| Language | Code |
|---|---|
| English | `en` |
| Français | `fr` |
| Deutsch | `de` |
| Español | `es` |
| Italiano | `it` |
| Nederlands | `nl` |
| Português (Portugal) | `pt` |
| Português (Brasil) | `pt-BR` (pt-BR uses the European Portuguese texts) |
| Polski | `pl` |
| Română | `ro` |
| Dansk | `da` |
| Svenska | `sv` |
| Български | `bg` |
| Русский | `ru` |
| Українська | `uk` |
| Magyar | `hu` |
| Slovenčina | `sk` |
| Čeština | `cs` |
| Slovenščina | `sl` |
| Latviešu | `lv` |
| Ελληνικά | `el` |
| Српски | `sr` |
| Srpski (latinica) | `sr-Latn` |

Contributions for additional languages are welcome!

## License

[MIT](https://github.com/juju35/ha-orphan-entities/blob/main/LICENSE)

## Support

If you find this project useful, you can support its development:

<a href="https://buymeacoffee.com/julienstep9"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me a Coffee" height="50"></a>
