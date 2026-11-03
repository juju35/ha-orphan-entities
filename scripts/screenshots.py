"""Render the Orphan Entities card with mock data and save the README screenshots.

Usage: python scripts/screenshots.py  (needs `pip install playwright` and `playwright install chromium`)
CHROMIUM_PATH=/path/to/chrome to use another browser. The clock is frozen so the durations and "x min ago" stay the same.
Integration logos are not fetched (the reason icon is shown), so the captures don't depend on the network.
Every capture keeps a 16 px frame of the theme background around the card.
A capture is only rewritten when its decoded pixels differ from the file already there (a re-encoded but identical
image is not a change), so an unchanged card never produces a screenshot commit.
"""

import base64
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
CARD_JS = (ROOT / "custom_components/orphan_entities/frontend/orphan-entities-card.js").read_text()
NOW = datetime.fromisoformat("2026-11-04T10:00:00+01:00")
WIDTH = 460

THEMES = {
    "light": {
        "--primary-background-color": "#e8eaed",
        "--secondary-background-color": "#ececec",
        "--card-background-color": "#ffffff",
        "--primary-text-color": "#212121",
        "--secondary-text-color": "#727272",
        "--divider-color": "rgba(0,0,0,.12)",
    },
    "dark": {
        "--primary-background-color": "#111111",
        "--secondary-background-color": "#282828",
        "--card-background-color": "#1c1c1c",
        "--primary-text-color": "#e1e1e1",
        "--secondary-text-color": "#9b9b9b",
        "--divider-color": "rgba(225,225,225,.12)",
    },
}
COMMON = {
    "--primary-color": "#03a9f4",
    "--success-color": "#43a047",
    "--warning-color": "#ffa600",
    "--error-color": "#db4437",
    "--text-primary-color": "#ffffff",
}

# Material Design Icons paths used by the card (from @mdi/js).
ICONS = {
    "broom": "M19.36,2.72L20.78,4.14L15.06,9.85C16.13,11.39 16.28,13.24 15.38,14.44L9.06,8.12C10.26,7.22 12.11,7.37 13.65,8.44L19.36,2.72M5.93,17.57C3.92,15.56 2.69,13.16 2.35,10.92L7.23,8.83L14.67,16.27L12.58,21.15C10.34,20.81 7.94,19.58 5.93,17.57Z",
    "ghost-outline": "M12 2C7.03 2 3 6.03 3 11V22L6 19L9 22L12 19L15 22L18 19L21 22V11C21 6.03 16.97 2 12 2M19 17.17L18 16.17L16.59 17.59L15 19.17L13.41 17.59L12 16.17L10.59 17.59L9 19.17L7.41 17.59L6 16.17L5 17.17V11C5 7.14 8.14 4 12 4S19 7.14 19 11V17.17M11 10C11 11.11 10.11 12 9 12S7 11.11 7 10 7.9 8 9 8 11 8.9 11 10M17 10C17 11.11 16.11 12 15 12S13 11.11 13 10 13.9 8 15 8 17 8.9 17 10Z",
    "refresh": "M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z",
    "magnify": "M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z",
    "check": "M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z",
    "minus": "M19,13H5V11H19V13Z",
    "delete-outline": "M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19M8,9H16V19H8V9M15.5,4L14.5,3H9.5L8.5,4H5V6H19V4H15.5Z",
    "eye-off-outline": "M2,5.27L3.28,4L20,20.72L18.73,22L15.65,18.92C14.5,19.3 13.28,19.5 12,19.5C7,19.5 2.73,16.39 1,12C1.69,10.24 2.79,8.69 4.19,7.46L2,5.27M12,9A3,3 0 0,1 15,12C15,12.35 14.94,12.69 14.83,13L11,9.17C11.31,9.06 11.65,9 12,9M12,4.5C17,4.5 21.27,7.61 23,12C22.18,14.08 20.79,15.88 19,17.19L17.58,15.76C18.94,14.82 20.06,13.54 20.82,12C19.17,8.64 15.76,6.5 12,6.5C10.91,6.5 9.84,6.68 8.84,7L7.3,5.47C8.74,4.85 10.33,4.5 12,4.5M3.18,12C4.83,15.36 8.24,17.5 12,17.5C12.69,17.5 13.37,17.43 14,17.29L11.72,15C10.29,14.85 9.15,13.71 9,12.28L5.6,8.87C4.61,9.72 3.78,10.78 3.18,12Z",
    "close": "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",
    "puzzle-remove-outline": "M13.2 22V21.7C13.2 20.21 12 19 10.5 19C9 19 7.8 20.21 7.8 21.7V22H4C2.9 22 2 21.11 2 20V16.2H2.3C3.79 16.2 5 15 5 13.5S3.79 10.8 2.3 10.8H2V7C2 5.9 2.9 5 4 5H7.04C7.28 3.3 8.74 2 10.5 2S13.72 3.3 13.96 5H17C18.11 5 19 5.9 19 7V10.04C20.7 10.28 22 11.74 22 13.5C22 13.6 22 13.7 21.97 13.79C21.35 13.44 20.67 13.2 19.93 13.08C19.75 12.46 19.18 12 18.5 12H17V7H12V5.5C12 4.67 11.33 4 10.5 4S9 4.67 9 5.5V7H4V9.12C5.76 9.8 7 11.5 7 13.5S5.75 17.2 4 17.88V20H6.12C6.8 18.25 8.5 17 10.5 17C11.47 17 12.37 17.3 13.12 17.81C13.04 18.19 13 18.59 13 19C13 20.1 13.3 21.12 13.81 22H13.2M21.12 15.46L19 17.59L16.88 15.46L15.47 16.88L17.59 19L15.47 21.12L16.88 22.54L19 20.41L21.12 22.54L22.54 21.12L20.41 19L22.54 16.88L21.12 15.46Z",
    "lan-disconnect": "M4,1C2.89,1 2,1.89 2,3V7C2,8.11 2.89,9 4,9H1V11H13V9H10C11.11,9 12,8.11 12,7V3C12,1.89 11.11,1 10,1H4M4,3H10V7H4V3M14,13C12.89,13 12,13.89 12,15V19C12,20.11 12.89,21 14,21H11V23H23V21H20C21.11,21 22,20.11 22,19V15C22,13.89 21.11,13 20,13H14M3.88,13.46L2.46,14.88L4.59,17L2.46,19.12L3.88,20.54L6,18.41L8.12,20.54L9.54,19.12L7.41,17L9.54,14.88L8.12,13.46L6,15.59L3.88,13.46M14,15H20V19H14V15Z",
    "help-circle-outline": "M11,18H13V16H11V18M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,20C7.59,20 4,16.41 4,12C4,7.59 7.59,4 12,4C16.41,4 20,7.59 20,12C20,16.41 16.41,20 12,20M12,6A4,4 0 0,0 8,10H10A2,2 0 0,1 12,8A2,2 0 0,1 14,10C14,12 11,11.75 11,15H13C13,12.75 16,12.5 16,10A4,4 0 0,0 12,6Z",
    "check-circle": "M12 2C6.5 2 2 6.5 2 12S6.5 22 12 22 22 17.5 22 12 17.5 2 12 2M10 17L5 12L6.41 10.59L10 14.17L17.59 6.58L19 8L10 17Z",
    "clock-check-outline": "M23.5 17L18.5 22L15 18.5L16.5 17L18.5 19L22 15.5L23.5 17M13.1 19.9C12.7 20 12.4 20 12 20C7.6 20 4 16.4 4 12S7.6 4 12 4 20 7.6 20 12C20 12.4 20 12.7 19.9 13.1C20.6 13.2 21.2 13.4 21.8 13.7C21.9 13.1 22 12.6 22 12C22 6.5 17.5 2 12 2S2 6.5 2 12C2 17.5 6.5 22 12 22C12.6 22 13.2 21.9 13.7 21.8C13.4 21.3 13.2 20.6 13.1 19.9M15.6 14.1L12.5 12.3V7H11V13L14.5 15.1C14.8 14.7 15.2 14.4 15.6 14.1Z",
    "arrow-expand": "M10,21V19H6.41L10.91,14.5L9.5,13.09L5,17.59V14H3V21H10M14.5,10.91L19,6.41V10H21V3H14V5H17.59L13.09,9.5L14.5,10.91Z",
    "arrow-collapse": "M19.5,3.09L15,7.59V4H13V11H20V9H16.41L20.91,4.5L19.5,3.09M4,13V15H7.59L3.09,19.5L4.5,20.91L9,16.41V20H11V13H4Z",
}

# Minimal stand-ins for Home Assistant's <ha-card> and <ha-icon>.
HA_ELEMENTS = (
    "const ICONS = "
    + json.dumps(ICONS)
    + ";"
    + """
customElements.define("ha-card", class extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" }).innerHTML =
      "<style>:host{display:block;background:var(--card-background-color);border-radius:12px;" +
      "border:1px solid var(--divider-color);color:var(--primary-text-color);overflow:hidden}</style><slot></slot>";
  }
});
customElements.define("ha-icon", class extends HTMLElement {
  static get observedAttributes() { return ["icon"]; }
  connectedCallback() { this._draw(); }
  attributeChangedCallback() { this._draw(); }
  _draw() {
    const path = ICONS[(this.getAttribute("icon") || "").replace("mdi:", "")] || "";
    this.style.display = "inline-flex";
    this.innerHTML = '<svg viewBox="0 0 24 24" style="width:var(--mdc-icon-size,24px);height:var(--mdc-icon-size,24px);fill:currentColor"><path d="' + path + '"/></svg>';
  }
});"""
)

ORPHANS = "sensor.orphan_entities_orphaned_entities"
LAST_SCAN = "sensor.orphan_entities_last_scan"
BUTTON = "button.orphan_entities_scan_now"


def ago(**delta) -> str:
    return (NOW - timedelta(**delta)).isoformat()


def orphan(entity_id, name, platform, reason, device=None, disabled=False, **delta):
    return {
        "entity_id": entity_id,
        "name": name,
        "platform": platform,
        "reason": reason,
        "since": ago(**delta),
        # A YAML platform has no config entry.
        "entry_id": None if reason == "integration_missing" else f"entry_{platform}",
        "entry_title": None if reason == "integration_missing" else platform.replace("_", " ").title(),
        "device": device,
        "disabled": disabled,
    }


# Mock orphans: neutral names, one of each reason.
ORPHANS_LIST = [
    orphan("sensor.old_node_battery", "Old node battery", "zwave_js", "entry_removed", "Old node", True, days=40),
    orphan("switch.pool_pump", "Pool pump", "command_line", "integration_missing", days=12),
    orphan("light.hallway_spot", "Hallway spot", "hue", "not_provided", "Hallway spot", days=9),
    orphan("sensor.hallway_spot_power", "Hallway spot power", "hue", "not_provided", "Hallway spot", days=9),
    orphan("binary_sensor.garage_door", "Garage door", "zha", "unavailable", "Garage door sensor", days=3),
    orphan("sensor.weather_station_uv", "Weather station UV", "netatmo", "unknown", "Weather station", hours=30),
]


def mock_hass(items, removed=3):
    platform = {"platform": "orphan_entities", "device_id": "orphans"}
    return {
        "states": {
            ORPHANS: {
                "entity_id": ORPHANS,
                "state": str(len(items)),
                "attributes": {
                    "entities": items,
                    "removed": removed,
                    "ignored_integrations": ["mobile_app"],
                    "ignored_entities": ["sensor.kept_on_purpose"],
                },
            },
            LAST_SCAN: {"entity_id": LAST_SCAN, "state": ago(minutes=2), "attributes": {}},
            BUTTON: {"entity_id": BUTTON, "state": "unknown", "attributes": {}},
        },
        "entities": {
            ORPHANS: {**platform, "translation_key": "orphans"},
            LAST_SCAN: {**platform, "translation_key": "last_scan"},
            BUTTON: {**platform, "translation_key": "scan"},
        },
        "language": "en",
        "locale": {"language": "en"},
        # An administrator: entities can be selected, removed and ignored.
        "user": {"is_admin": True},
    }


MINI = "orphan-entities-mini-card"
MINI_WIDTH = 400
SELECTED = ["light.hallway_spot", "sensor.hallway_spot_power"]


def both(file, **shot):
    return [{"file": file, "theme": "light", **shot}, {"file": f"{file}-dark", "theme": "dark", **shot}]


SHOTS = [
    *both("card", hass=ORPHANS_LIST),
    # Two entities selected: the actions above the list.
    *both("card-selected", hass=ORPHANS_LIST, select=SELECTED),
    # The confirmation at the top of the card.
    *both("card-confirm", hass=ORPHANS_LIST, select=SELECTED, confirm="remove"),
    # Filtered on a reason.
    *both("card-filtered", hass=ORPHANS_LIST, reason="not_provided"),
    *both("card-ok", hass=[]),
    *both("mini", hass=ORPHANS_LIST, card=MINI, width=MINI_WIDTH),
    *both("mini-ok", hass=[], card=MINI, width=MINI_WIDTH),
    *both("mini-zoom", hass=ORPHANS_LIST, card=MINI, width=MINI_WIDTH, zoom=True),
]


def page_html(theme, width):
    variables = "".join(f"{k}:{v};" for k, v in {**THEMES[theme], **COMMON}.items())
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
:root {{ {variables} }}
body {{ margin: 0; padding: 16px; background: var(--primary-background-color);
       font-family: Roboto, "Segoe UI", Helvetica, Arial, sans-serif; width: {width}px; }}
</style></head><body><div id="root"></div></body></html>"""


MOUNT = """([hass, dark, card, opts]) => {
    const el = document.createElement(card);
    el.setConfig({ type: `custom:${card}` });
    el.hass = { ...hass, themes: { darkMode: dark }, callService: async () => {} };
    document.getElementById("root").appendChild(el);
    // The mini card zoomed in: its detail button clicked with the mouse (no focus ring), the full card shown.
    if (opts.zoom) el.shadowRoot.querySelector(".zoom").dispatchEvent(new MouseEvent("click", { bubbles: true, composed: true, detail: 1 }));
    if (opts.reason) el._reason = opts.reason;
    for (const id of opts.select || []) el._sel.add(id);
    if (opts.confirm) el._confirm = opts.confirm;
    el._sig = null;
    el._render();
}"""


# Decodes two PNGs (base64) in the browser and tells whether their pixels are the same: no image library needed.
SAME_PIXELS = """async ([a, b]) => {
    const decode = async (data) => {
        const img = new Image();
        img.src = "data:image/png;base64," + data;
        await img.decode();
        const canvas = document.createElement("canvas");
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
        const ctx = canvas.getContext("2d", { willReadFrequently: true });
        ctx.drawImage(img, 0, 0);
        return ctx.getImageData(0, 0, canvas.width, canvas.height);
    };
    const [x, y] = [await decode(a), await decode(b)];
    if (x.width !== y.width || x.height !== y.height) return false;
    for (let i = 0; i < x.data.length; i++) if (x.data[i] !== y.data[i]) return false;
    return true;
}"""


def same_pixels(page, new: bytes, path: Path) -> bool:
    """True when `path` exists and holds exactly the pixels of the `new` PNG."""
    if not path.exists():
        return False
    old = path.read_bytes()
    if old == new:
        return True
    return page.evaluate(SAME_PIXELS, [base64.b64encode(new).decode(), base64.b64encode(old).decode()])


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
        for shot in SHOTS:
            page = browser.new_page(device_scale_factor=2, viewport={"width": 1000, "height": 1600})
            page.on("pageerror", lambda err, name=shot["file"]: print(f"{name}: page error: {err}"))
            # No integration logo: the reason's icon, the same on every machine.
            page.route("https://brands.home-assistant.io/**", lambda route: route.abort())
            page.clock.set_fixed_time(NOW.isoformat())
            width = shot.get("width", WIDTH)
            page.set_content(page_html(shot["theme"], width))
            page.add_script_tag(content=HA_ELEMENTS)
            page.add_script_tag(content=CARD_JS)
            card = shot.get("card", "orphan-entities-card")
            opts = {k: shot[k] for k in ("zoom", "select", "confirm", "reason") if k in shot}
            page.evaluate(MOUNT, [mock_hass(shot["hass"]), shot["theme"] == "dark", card, opts])
            page.wait_for_timeout(400)
            box = page.locator("#root").bounding_box()
            clip = {"x": 0, "y": 0, "width": width + 32, "height": int(box["height"] + 0.999) + 32}
            path = ROOT / "screenshots" / f"{shot['file']}.png"
            path.parent.mkdir(exist_ok=True)
            png = page.screenshot(clip=clip, animations="disabled")
            if same_pixels(page, png, path):
                print(f"{path.relative_to(ROOT)} (unchanged)")
            else:
                path.write_bytes(png)
                print(path.relative_to(ROOT))
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
