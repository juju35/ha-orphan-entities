"""Constants for Orphan Entities."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "orphan_entities"
# Same as manifest.json and the card: the card URL carries it, so that browsers load a new release.
VERSION: Final = "1.0.3"

CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_GRACE_PERIOD: Final = "grace_period"
CONF_STALE_HOURS: Final = "stale_hours"
CONF_INCLUDE_UNKNOWN: Final = "include_unknown"
CONF_IGNORED_INTEGRATIONS: Final = "ignored_integrations"
CONF_IGNORED_ENTITIES: Final = "ignored_entities"

# Minutes between two scans.
DEFAULT_SCAN_INTERVAL: Final = 15
MAX_MINUTES: Final = 1440
# Minutes after Home Assistant has started before the first scan: integrations are still setting up their entities.
DEFAULT_GRACE_PERIOD: Final = 10
# Hours an entity still provided by its integration must have been unavailable (or unknown) to be listed. 0: never.
DEFAULT_STALE_HOURS: Final = 24
MAX_STALE_HOURS: Final = 8760
DEFAULT_INCLUDE_UNKNOWN: Final = True

# Why an entity is listed, from the most to the least certain orphan.
REASON_ENTRY_REMOVED: Final = "entry_removed"  # its config entry no longer exists
REASON_INTEGRATION_MISSING: Final = "integration_missing"  # its integration (YAML platform) is not loaded
REASON_NOT_PROVIDED: Final = "not_provided"  # its integration is loaded but no longer creates it
REASON_UNAVAILABLE: Final = "unavailable"  # still provided, unavailable for stale_hours
REASON_UNKNOWN: Final = "unknown"  # still provided, unknown for stale_hours
REASONS: Final = (
    REASON_ENTRY_REMOVED,
    REASON_INTEGRATION_MISSING,
    REASON_NOT_PROVIDED,
    REASON_UNAVAILABLE,
    REASON_UNKNOWN,
)

# Entity domains whose state is "unknown" by design until something happens (never pressed, never activated).
STATELESS_DOMAINS: Final = frozenset(
    {
        "ai_task",
        "assist_satellite",
        "button",
        "conversation",
        "event",
        "input_button",
        "notify",
        "scene",
        "stt",
        "tts",
        "wake_word",
    }
)

SERVICE_SCAN: Final = "scan"
SERVICE_REMOVE: Final = "remove"
SERVICE_IGNORE: Final = "ignore"
ATTR_ENTITIES: Final = "entities"
EVENT_REMOVED: Final = f"{DOMAIN}_removed"

# A removal or an ignore request names at most this many entities.
MAX_BATCH: Final = 1000
# Seconds after an entity registry change before scanning again (several changes come in a burst).
REGISTRY_DEBOUNCE: Final = 10

# The card bundled with the integration, served by Home Assistant and added to the dashboard resources.
CARD_URL: Final = f"/{DOMAIN}/orphan-entities-card.js"
