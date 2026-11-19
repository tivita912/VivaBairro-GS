from pathlib import Path
import unittest

from src.errors import ComponentUnavailable
from src.llm import UnconfiguredLLM
from src.speech_text import UnconfiguredSpeechAdapter
from src.stt import UnconfiguredSTT
from src.tts import UnconfiguredTTS


class ContractTests(unittest.TestCase):
    def test_no_silent_mock_or_fallback(self):
        calls = [lambda: UnconfiguredSTT().transcribe(None),
                 lambda: UnconfiguredLLM().generate(()),
                 lambda: UnconfiguredSpeechAdapter().adapt("Texto"),
                 lambda: UnconfiguredTTS().synthesize("Texto", Path("unused"))]
        for call in calls:
            with self.subTest(call=call):
                with self.assertRaises(ComponentUnavailable):
                    call()
