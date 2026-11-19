import unittest

from src.errors import ValidationError
from src.speech_text import PortugueseSpeechAdapter


class SpeechTextTests(unittest.TestCase):
    def setUp(self):
        self.speech = PortugueseSpeechAdapter()

    def test_markdown_emoji_and_link_destination(self):
        result = self.speech.adapt("## Orientações\n- **Leia** [o guia](https://gov.br/rota-2). 🚧\n- Volte depois!!!")
        self.assertIn("Orientações. Leia o guia.", result.text)
        self.assertIn("https dois pontos barra barra gov ponto br barra rota hífen dois", result.text)
        self.assertNotRegex(result.text, r"[#*🚧]|!!!")

    def test_dates_times_numbers_and_acronyms(self):
        original = "A UBS abre às 08:05 em 01/12/2026. A taxa é 12,5% e a tarifa é R$ 21,01."
        result = self.speech.adapt(original)
        self.assertEqual(result.text, "A Unidade Básica de Saúde abre às oito horas e cinco em primeiro de dezembro de dois mil e vinte e seis. "
                                     "A taxa é doze vírgula cinco por cento e a tarifa é vinte e um reais e um centavo.")
        self.assertEqual(result.warnings, ())

    def test_preserves_codes_invalid_date_and_ambiguous_notation(self):
        result = self.speech.adapt("Protocolo AB-0001/2026 e `0054`. Código Z-18. Ligue 156. Use 03/04/25, 31/02/2026 ou 1.234.")
        for token in ("AB-0001/2026", "0054", "Z-18", "156", "03/04/25", "31/02/2026", "1.234"):
            self.assertIn(token, result.text)
        self.assertEqual(len(result.warnings), 1)

    def test_uses_clause_boundary_for_long_sentence_and_informs_when_absent(self):
        clause = "Para que qualquer pessoa consiga descrever com clareza o que está acontecendo na via e reunir todas as informações que serão úteis à equipe encarregada do atendimento"
        result = self.speech.adapt(clause + ", em seguida envie uma foto.")
        self.assertIn(". Em seguida envie", result.text)
        self.assertTrue(self.speech.adapt(" ".join(["palavra"] * 31)).warnings)

    def test_empty_speech_rejected(self):
        for original in ("", "💡"):
            with self.subTest(original=original), self.assertRaises(ValidationError):
                self.speech.adapt(original)

    def test_iso_date_midnight_and_signed_number(self):
        self.assertEqual(self.speech.adapt("Em 2024-02-29 às 00:00, marcou -3 graus.").text,
                         "Em vinte e nove de fevereiro de dois mil e vinte e quatro às zero horas, marcou menos três graus.")

    def test_code_keeps_formatting_and_leading_zeroes(self):
        result = self.speech.adapt("Identificador BR-0042. Use \n```text\n001.042-X\n```\ncomo referência.")
        self.assertIn("BR-0042", result.text)
        self.assertIn("001.042-X", result.text)
        self.assertNotIn("```", result.text)
