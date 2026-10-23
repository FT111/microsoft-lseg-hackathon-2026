"""Shariah screens - all inputs are FICTIONAL (see tests/fictional.py)."""
import unittest

from shariah.methodology import FAIL, NEEDS_REVIEW, PASS, breaches, worst
from shariah.screen import quote_in_text, verdict
from tests.fictional import MCAP, activity, business, fin

FTSE, AAOIFI = "FTSE Yasaar", "AAOIFI"


def screen_of(v, key):
    return next(s for s in v["screens"] if s["key"] == key)


class Basics(unittest.TestCase):
    def test_clean_fictional_company_passes_both_standards(self):
        for std in (FTSE, AAOIFI):
            v = verdict(fin(), business(), std, MCAP)
            self.assertEqual(v["status"], PASS, (std, v["review"], v["reasons"]))

    def test_worst_status_wins(self):
        self.assertEqual(worst([PASS, NEEDS_REVIEW, PASS]), NEEDS_REVIEW)
        self.assertEqual(worst([PASS, NEEDS_REVIEW, FAIL]), FAIL)
        self.assertEqual(worst([]), NEEDS_REVIEW)

    def test_operators(self):
        self.assertTrue(breaches(1 / 3, 1 / 3, "<"))
        self.assertFalse(breaches(0.30, 0.30, "<="))
        self.assertTrue(breaches(0.3001, 0.30, "<="))

    def test_unknown_standard_rejected(self):
        with self.assertRaises(ValueError):
            verdict(fin(), business(), "Made-up standard")


class FtseThresholds(unittest.TestCase):
    def test_debt_exactly_one_third_fails(self):   # rule 4.3.2 A: "less than 33.333%"
        v = verdict(fin(total_debt=1000 / 3), business(), FTSE)
        self.assertEqual(screen_of(v, "debt")["status"], FAIL)

    def test_debt_in_monitoring_band_needs_review(self):
        v = verdict(fin(total_debt=320.0), business(), FTSE)
        self.assertEqual(screen_of(v, "debt")["status"], NEEDS_REVIEW)

    def test_receivables_plus_cash_at_50_percent_fails(self):
        v = verdict(fin(receivables=400.0, cash_and_interest_bearing=100.0), business(), FTSE)
        self.assertEqual(screen_of(v, "receivables_plus_cash")["status"], FAIL)

    def test_long_term_interest_bearing_securities_push_cash_over_limit(self):
        v = verdict(fin(long_term_interest_bearing=300.0), business(), FTSE)
        self.assertEqual(screen_of(v, "cash")["status"], NEEDS_REVIEW)
        self.assertEqual(v["status"], NEEDS_REVIEW)

    def test_interest_income_counts_towards_noncompliant_income(self):
        # 4% interest + 2% non-permitted activity = 6% > 5%
        v = verdict(fin(interest_income=40.0), business(activity("music", 2.0)), FTSE)
        self.assertEqual(screen_of(v, "noncompliant_income")["status"], FAIL)
        self.assertEqual(v["status"], FAIL)

    def test_interest_income_alone_over_five_percent_fails(self):
        v = verdict(fin(interest_income=60.0), business(), FTSE)
        self.assertEqual(screen_of(v, "noncompliant_income")["status"], FAIL)

    def test_noncompliant_income_exactly_five_percent_passes(self):   # 4.3.2 D: "should not exceed 5%"
        v = verdict(fin(interest_income=50.0), business(), FTSE)
        self.assertEqual(screen_of(v, "noncompliant_income")["status"], PASS)


class AaoifiThresholds(unittest.TestCase):
    def test_debt_exactly_30_percent_of_market_value_passes(self):   # "should not exceed 30%"
        v = verdict(fin(total_debt=600.0), business(), AAOIFI, MCAP)
        self.assertEqual(screen_of(v, "debt")["status"], PASS)

    def test_debt_just_over_30_percent_fails(self):
        v = verdict(fin(total_debt=600.2), business(), AAOIFI, MCAP)
        self.assertEqual(screen_of(v, "debt")["status"], FAIL)

    def test_missing_market_value_needs_review(self):
        v = verdict(fin(), business(), AAOIFI, None)
        self.assertEqual(screen_of(v, "debt")["status"], NEEDS_REVIEW)

    def test_aaoifi_has_no_receivables_screen(self):
        keys = {s["key"] for s in verdict(fin(), business(), AAOIFI, MCAP)["screens"]}
        self.assertNotIn("receivables_plus_cash", keys)


class MissingData(unittest.TestCase):
    def test_missing_receivables_is_not_treated_as_zero(self):
        v = verdict(fin(receivables=None), business(), FTSE)
        self.assertEqual(screen_of(v, "receivables_plus_cash")["status"], NEEDS_REVIEW)
        self.assertEqual(v["status"], NEEDS_REVIEW)

    def test_missing_interest_income_needs_review(self):
        v = verdict(fin(interest_income=None), business(), FTSE)
        self.assertEqual(screen_of(v, "noncompliant_income")["status"], NEEDS_REVIEW)

    def test_missing_cash_needs_review(self):
        v = verdict(fin(cash_and_interest_bearing=None), business(), FTSE)
        self.assertEqual(screen_of(v, "cash")["status"], NEEDS_REVIEW)

    def test_zero_total_assets_does_not_crash(self):
        v = verdict(fin(total_assets=0.0), business(), FTSE)
        self.assertEqual(screen_of(v, "debt")["status"], NEEDS_REVIEW)

    def test_missing_revenue_needs_review(self):
        v = verdict(fin(revenue=None), business(), FTSE)
        self.assertEqual(screen_of(v, "noncompliant_income")["status"], NEEDS_REVIEW)

    def test_stale_data_needs_review(self):
        self.assertEqual(verdict(fin(stale=True), business(), FTSE)["status"], NEEDS_REVIEW)

    def test_no_business_reading_needs_review(self):
        v = verdict(fin(), {"method": "LLM", "activities": [], "error": "AI reply unreadable"}, FTSE)
        self.assertEqual(screen_of(v, "activity")["status"], NEEDS_REVIEW)


class Activities(unittest.TestCase):
    def test_every_ftse_excluded_category_fails_as_main_business(self):
        for cat in ("conventional_finance", "conventional_insurance", "alcohol", "pork", "non_halal_food", "gambling",
                    "cinema", "music", "adult_entertainment", "hotels", "tobacco", "cannabis", "weapons_defence"):
            v = verdict(fin(), business(activity(cat, None, primary=True)), FTSE)
            self.assertEqual(screen_of(v, "activity")["status"], FAIL, cat)

    def test_every_aaoifi_excluded_category_fails_as_main_business(self):
        for cat in ("conventional_finance", "conventional_insurance", "alcohol", "tobacco", "pork", "gambling",
                    "cinema", "music", "adult_entertainment", "hotels", "weapons_defence"):
            v = verdict(fin(), business(activity(cat, None, primary=True)), AAOIFI, MCAP)
            self.assertEqual(screen_of(v, "activity")["status"], FAIL, cat)

    def test_activity_not_on_aaoifi_list_goes_to_review_not_pass(self):
        v = verdict(fin(), business(activity("cannabis", 3.0)), AAOIFI, MCAP)
        self.assertEqual(screen_of(v, "activity")["status"], NEEDS_REVIEW)

    def test_activity_exactly_five_percent_passes(self):
        v = verdict(fin(interest_income=0.0), business(activity("alcohol", 5.0)), FTSE)
        self.assertEqual(screen_of(v, "activity")["status"], PASS)

    def test_activity_over_five_percent_fails(self):
        v = verdict(fin(), business(activity("alcohol", 5.5)), FTSE)
        self.assertEqual(screen_of(v, "activity")["status"], FAIL)

    def test_unverified_quote_needs_review(self):
        v = verdict(fin(), business(activity("gambling", 1.0, verified=False)), FTSE)
        self.assertEqual(screen_of(v, "activity")["status"], NEEDS_REVIEW)

    def test_unknown_share_needs_review(self):
        v = verdict(fin(), business(activity("alcohol", None, confidence="low")), FTSE)
        self.assertEqual(screen_of(v, "activity")["status"], NEEDS_REVIEW)

    def test_stated_floor_fails_even_without_estimate(self):
        v = verdict(fin(), business(activity("weapons_defence", None, floor=27.0)), FTSE)
        self.assertEqual(screen_of(v, "activity")["status"], FAIL)

    def test_low_confidence_small_estimate_needs_review(self):
        v = verdict(fin(), business(activity("music", 8.0, confidence="low")), FTSE)
        self.assertEqual(screen_of(v, "activity")["status"], NEEDS_REVIEW)

    def test_sic_only_reading_cannot_pass(self):
        b = {"method": "SIC rule", "activities": [], "main_quote_verified": False, "evidence": "SIC"}
        self.assertEqual(screen_of(verdict(fin(), b, FTSE), "activity")["status"], NEEDS_REVIEW)


class QuoteCheck(unittest.TestCase):
    TEXT = "Fictional Corp makes  widgets.\nIt also sells “beer” in some stores, about 3% of sales."

    def test_exact_quote_found(self):
        self.assertTrue(quote_in_text('It also sells "beer" in some stores', self.TEXT))

    def test_quote_with_ellipsis(self):
        self.assertTrue(quote_in_text("Fictional Corp makes widgets ... about 3% of sales", self.TEXT))

    def test_paraphrase_rejected(self):
        self.assertFalse(quote_in_text("The company sells alcohol in its shops", self.TEXT))

    def test_too_short_rejected(self):
        self.assertFalse(quote_in_text("beer", self.TEXT))


if __name__ == "__main__":
    unittest.main()
