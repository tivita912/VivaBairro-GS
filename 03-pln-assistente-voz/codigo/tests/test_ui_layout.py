"""Contrato de marcação semântica e associação dos controles."""
from html.parser import HTMLParser
import unittest

from src.config import PROJECT_ROOT


class InterfaceMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = {}
        self.label_targets = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            element_id = attributes["id"]
            if element_id in self.ids:
                raise AssertionError(f"ID repetido: {element_id}")
            self.ids[element_id] = (tag, attributes)
        if tag == "label" and "for" in attributes:
            self.label_targets.append(attributes["for"])


class UILayoutTests(unittest.TestCase):
    def test_sections_controls_and_responsive_css(self):
        ui = InterfaceMarkup()
        ui.feed((PROJECT_ROOT / "web/index.html").read_text(encoding="utf-8-sig"))
        self.assertTrue(all(target in ui.ids for target in ui.label_targets))
        self.assertIn("upload", ui.label_targets)
        for name, tag in {"atendimento": "section", "status": "div", "error": "div",
                          "record": "button", "send": "button", "answer-audio": "audio",
                          "history": "ol", "metrics": "dl"}.items():
            self.assertEqual(ui.ids[name][0], tag)
        self.assertEqual(ui.ids["status"][1]["role"], "status")
        self.assertEqual(ui.ids["error"][1]["role"], "alert")
        self.assertIn("controls", ui.ids["answer-audio"][1])
        css = (PROJECT_ROOT / "web/assets/site.css").read_text(encoding="utf-8-sig")
        self.assertIn(":focus-visible", css)
        self.assertIn("@media", css)
