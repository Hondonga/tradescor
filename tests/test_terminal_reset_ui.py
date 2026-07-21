"""DOM contracts for the single-structure TradeScor terminal frontend."""

from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DomCounter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = {}
        self.classes = {}
        self.checked = set()

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids[values["id"]] = self.ids.get(values["id"], 0) + 1
            if "checked" in values:
                self.checked.add(values["id"])
        for name in (values.get("class") or "").split():
            self.classes[name] = self.classes.get(name, 0) + 1


def parsed_dom():
    parser = DomCounter()
    parser.feed((ROOT / "templates" / "index.html").read_text(encoding="utf-8"))
    return parser


def test_primary_controls_and_workspaces_are_unique():
    dom = parsed_dom()
    for element_id in ("analyze-button", "symbol", "timeframe", "strategy", "chart"):
        assert dom.ids.get(element_id) == 1
    for class_name in ("app-shell", "app-sidebar", "terminal-toolbar", "chart-workspace", "decision-panel", "page-content"):
        assert dom.classes.get(class_name) == 1


def test_legacy_control_structures_are_absent():
    source = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    for phrase in ("Manual Fetch", "API Protected", "button-option-group", "terminal-top-bar", "assistant-panel"):
        assert phrase not in source


def test_advanced_labels_default_off_and_context_defaults_on():
    dom = parsed_dom()
    assert "show-labels" not in dom.checked
    assert "show-zones" in dom.checked
    assert "show-fvg" in dom.checked


def test_forbidden_user_statuses_are_not_rendered_in_template():
    source = (ROOT / "templates" / "index.html").read_text(encoding="utf-8").upper()
    for phrase in (">WAIT<", ">AVOID<", ">NO TRADE<", ">ENTRY READY<", "NO CLEAN ENTRY"):
        assert phrase not in source


def test_page_layout_does_not_use_absolute_positioning():
    styles = (ROOT / "static" / "style.css").read_text(encoding="utf-8")
    assert "position: absolute" in styles  # chart annotations only
    for selector in (".market-controls", ".session-display", ".decision-panel", ".chart-panel", ".page-heading"):
        block = styles.split(selector, 1)[1].split("}", 1)[0]
        assert "position: absolute" not in block
