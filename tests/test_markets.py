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


class YahooInterest(unittest.TestCase):
    """Yahoo path: banks use net interest income (FICTIONAL rows)."""

    def test_bank_uses_net_interest(self):
        from shariah import yahoo
        inc = {"Interest Income": {"2025-12-31": 97.0}, "Net Interest Income": {"2025-12-31": 35.0},
               "Total Revenue": {"2025-12-31": 71.0}}
        item, note = yahoo.interest_item(inc, "2025-12-31", "Banks - Diversified")
        self.assertEqual(item["value"], 35.0)
        self.assertIn("net interest income", note)

    def test_gross_interest_above_revenue_means_net_revenue(self):
        from shariah import yahoo
        inc = {"Interest Income": {"2025-12-31": 97.0}, "Net Interest Income": {"2025-12-31": 35.0},
               "Total Revenue": {"2025-12-31": 71.0}}
        self.assertEqual(yahoo.interest_item(inc, "2025-12-31", "Something Else")[0]["value"], 35.0)

    def test_retailer_uses_gross_interest(self):
        from shariah import yahoo
        inc = {"Interest Income": {"2026-02-28": 0.23}, "Net Interest Income": {"2026-02-28": -0.56},
               "Total Revenue": {"2026-02-28": 73.7}}
        item, note = yahoo.interest_item(inc, "2026-02-28", "Grocery Stores")
        self.assertEqual(item["value"], 0.23)
        self.assertIsNone(note)
