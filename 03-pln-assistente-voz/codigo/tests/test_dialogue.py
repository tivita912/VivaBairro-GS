import unittest

from src.config import PROJECT_ROOT
from src.conversation import Conversation
from src.errors import ValidationError
from src.knowledge import KnowledgeBase


class DialogueTests(unittest.TestCase):
    def setUp(self):
        self.base = KnowledgeBase.load(PROJECT_ROOT / "knowledge/urban_guidance.json")
        self.prompt = PROJECT_ROOT / "prompts/system_v1.txt"

    def test_sessions_are_isolated(self):
        one, two = Conversation(), Conversation()
        one.commit("Há uma calçada danificada.", "Descreva o obstáculo.")
        self.assertNotEqual(one.session_id, two.session_id)
        self.assertEqual(two.turns, ())
        messages = two.messages("Onde?", self.base, self.prompt)
        self.assertEqual(len(messages), 2)

    def test_followup_receives_history_in_order(self):
        session = Conversation()
        session.commit("Há um buraco.", "Qual o local aproximado?")
        messages = session.messages("Perto da praça.", self.base, self.prompt)
        self.assertEqual([m.role for m in messages], ["system", "user", "assistant", "user"])
        self.assertEqual(messages[1].content, "Há um buraco.")
        self.assertEqual(messages[-1].content, "Perto da praça.")
        self.assertIn("BASE CURADA", messages[0].content)

    def test_history_keeps_whole_turns(self):
        session = Conversation(max_turns=1)
        session.commit("Primeira pergunta", "Primeira resposta")
        session.commit("Segunda pergunta", "Segunda resposta")
        self.assertEqual(session.turns, (("Segunda pergunta", "Segunda resposta"),))

    def test_clear_rotates_identity(self):
        session = Conversation()
        previous = session.session_id
        session.commit("Pergunta", "Resposta")
        session.clear()
        self.assertEqual(session.turns, ())
        self.assertNotEqual(previous, session.session_id)

    def test_invalid_output_does_not_commit_half_turn(self):
        session = Conversation()
        with self.assertRaises(ValidationError):
            session.commit("Texto", " ")
        self.assertEqual(session.turns, ())

    def test_oversized_input_and_invalid_history_rejected(self):
        with self.assertRaises(ValidationError):
            Conversation().messages("a" * 4001, self.base, self.prompt)
        with self.assertRaises(ValidationError):
            Conversation(max_turns=0)
