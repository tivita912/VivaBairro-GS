import json

from src.config import PROJECT_ROOT
from src.errors import ValidationError
from src.knowledge import KnowledgeBase, TOPICS
from tests.helpers import LocalFilesTest


class KnowledgeTests(LocalFilesTest):
    def test_full_base_has_sources_and_five_topics(self):
        base = KnowledgeBase.load(PROJECT_ROOT / "knowledge/urban_guidance.json")
        self.assertEqual({e.topic for e in base.entries}, TOPICS)
        self.assertIn("https://www.gov.br/", base.context())
        self.assertIn("editorial_guidance", base.context())

    def test_corrupt_missing_and_duplicate_entries(self):
        path = self.folder / "kb.json"
        with self.assertRaises(ValidationError):
            KnowledgeBase.load(path)
        path.write_text("{}")
        with self.assertRaises(ValidationError):
            KnowledgeBase.load(path)
        data = json.loads((PROJECT_ROOT / "knowledge/urban_guidance.json").read_text(encoding="utf-8"))
        data["entries"].append(data["entries"][0])
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValidationError):
            KnowledgeBase.load(path)
