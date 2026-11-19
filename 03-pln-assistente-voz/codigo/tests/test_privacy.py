from dataclasses import replace
import unittest

from src.errors import ConsentRequired
from src.privacy import Consent


class PrivacyTests(unittest.TestCase):
    def test_default_is_not_consent(self):
        with self.assertRaises(ConsentRequired):
            Consent().require()

    def test_external_is_separate(self):
        Consent.grant().require()
        with self.assertRaises(ConsentRequired):
            Consent.grant().require(external=True)
        Consent.grant(external_text=True).require(external=True)

    def test_outdated_notice_requires_new_decision(self):
        with self.assertRaises(ConsentRequired):
            replace(Consent.grant(), notice_version="old").require()

    def test_checkbox_without_timestamp_is_insufficient(self):
        with self.assertRaises(ConsentRequired):
            Consent(accepted=True).require()
