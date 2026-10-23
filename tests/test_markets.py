"""Muslim-majority market footprint scan - FICTIONAL filing text, no network."""
import unittest
from unittest import mock

from shariah import edgar, markets

TEXT = ("Fictional Widgets Inc. ITEM 1. BUSINESS. We operate assembly plants in Malaysia and Indonesia and sell through "
        "distributors in Saudi Arabia and the UAE. We offer products under the Jordan brand. "
        "Our results could be harmed by sanctions involving Iran or hostilities in Lebanon. "
        "Export control licensing requirements may limit shipments to Egypt.")


class Footprint(unittest.TestCase):
    def setUp(self):
        self.p1 = mock.patch.object(edgar, "submissions", return_value={"latest_10k": {"url": "u", "date": "2026-01-01",
                                                                                        "accession": "FICT-1"}})
        self.p2 = mock.patch.object(edgar, "_filing_text", return_value=TEXT)
        self.p3 = mock.patch("shariah.markets.cached", side_effect=lambda key, produce: produce())
        for p in (self.p1, self.p2, self.p3):
            p.start()

    def tearDown(self):
        for p in (self.p1, self.p2, self.p3):
            p.stop()

    def test_business_sentences_count_and_risk_sentences_do_not(self):
        m = markets.mentions("FICT")
        self.assertEqual(set(m["countries"]), {"Malaysia", "Indonesia", "Saudi Arabia", "United Arab Emirates"})
        self.assertNotIn("Iran", m["countries"])
        self.assertNotIn("Egypt", m["countries"])

    def test_jordan_brand_is_not_a_country(self):
        self.assertNotIn("Jordan", markets.mentions("FICT")["countries"])

    def test_rank_quotes_a_business_sentence(self):
        out = markets.rank(["FICT"])
        self.assertEqual(out[0]["ticker"], "FICT")
        self.assertIn("assembly plants in Malaysia", out[0]["quote"])
        self.assertEqual(out[0]["score"], 8)

    def test_no_filing_means_no_pick(self):
        with mock.patch.object(edgar, "submissions", return_value={"latest_10k": None}):
            self.assertEqual(markets.rank(["NOPE"]), [])
