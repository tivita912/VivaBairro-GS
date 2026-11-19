"""Fixtures sintéticas locais. Nenhuma voz humana ou modelo real."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import wave

from src.config import PROJECT_ROOT


class LocalFilesTest(unittest.TestCase):
    def setUp(self):
        root = PROJECT_ROOT / ".runtime/tests"
        root.mkdir(parents=True, exist_ok=True)
        self.temporary = TemporaryDirectory(dir=root)
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)

    def wav(self, seconds=0.02, rate=16000, channels=1, width=2):
        path = self.folder / "synthetic.wav"
        with wave.open(str(path), "wb") as stream:
            stream.setnchannels(channels)
            stream.setsampwidth(width)
            stream.setframerate(rate)
            stream.writeframes(b"\x00" * int(seconds * rate) * channels * width)
        return path
