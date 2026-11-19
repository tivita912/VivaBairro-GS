import os
from unittest.mock import patch

from src.config import Settings
from src.errors import ValidationError
from tests.helpers import LocalFilesTest


class ConfigTests(LocalFilesTest):
    @patch.dict(os.environ, {}, clear=True)
    def test_defaults_and_file(self):
        self.assertEqual(Settings.load().port, 7860)
        path = self.folder / "config.env"
        path.write_text("# teste\nVIVABAIRRO_PORT=7861\n", encoding="utf-8")
        self.assertEqual(Settings.load(path).port, 7861)

    @patch.dict(os.environ, {"VIVABAIRRO_PORT": "7862"}, clear=True)
    def test_environment_overrides_file(self):
        path = self.folder / "config.env"
        path.write_text("VIVABAIRRO_PORT=7861", encoding="utf-8")
        self.assertEqual(Settings.load(path).port, 7862)

    def test_invalid_values_fail_clearly(self):
        for values in [{"VIVABAIRRO_PORT": "text"}, {"VIVABAIRRO_PORT": "1"}, {"VIVABAIRRO_UNKNOWN": "1"}]:
            with patch.dict(os.environ, values, clear=True):
                with self.assertRaises(ValidationError):
                    Settings.load()
