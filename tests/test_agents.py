"""Agent committee - FICTIONAL data, LLM calls mocked (no network)."""
import unittest
from unittest import mock

from shariah import portfolio
from shariah.agents import analysts, base, committee, evidence, shariah_checker
from shariah.methodology import FAIL, NEEDS_REVIEW, PASS
from shariah.screen import verdict
from tests.fictional import activity, business, fin


def result(fin_kwargs=None, biz=None, std="FTSE Yasaar"):
    f = fin(**(fin_kwargs or {}))
    b = biz or business()
    b.setdefault("source_url", "https://example.com/fictional-10k")
    return {"ticker": "FICT", "fin": f, "business": b, "mcap": None, "verdict": verdict(f, b, std)}


class Gate(unittest.TestCase):
    def test_fail_gate_stops_the_committee(self):
        r = result(biz=business(activity("gambling", None, primary=True)))
        with mock.patch.object(analysts, "bull", side_effect=AssertionError("bull must not run")), \
             mock.patch.object(analysts, "bear", side_effect=AssertionError("bear must not run")), \
             mock.patch.object(analysts, "risk", side_effect=AssertionError("risk must not run")):
            out = committee.run(r)
        self.assertEqual(out["gate"]["status"], FAIL)
        self.assertFalse(out["ran"])

    def test_needs_review_is_conditional_and_not_allocatable(self):
        g = shariah_checker.gate(result({"interest_income": None}))
        self.assertEqual(g["status"], NEEDS_REVIEW)
        self.assertTrue(g["committee_allowed"])
        self.assertFalse(g["allocatable"])

    def test_pass_gate_is_allocatable(self):
        g = shariah_checker.gate(result())
        self.assertEqual(g["status"], PASS)
        self.assertTrue(g["allocatable"])


class Validator(unittest.TestCase):
    FACTS = {"F1": {"label": "Debt ratio", "value": 0.215, "unit": "ratio", "display": "21.5%"},
             "F2": {"label": "Revenue", "value": 4.2e9, "unit": "USD", "display": "$4.2bn"}}

    def test_keeps_supported_claim(self):
        kept, dropped = base.validate_points([{"claim": "Debt is 21.5% of assets on $4.2bn revenue.",
                                               "facts": ["F1", "F2"]}], self.FACTS)
        self.assertEqual(len(kept), 1)
        self.assertEqual(dropped, [])

    def test_drops_invented_number(self):
        kept, dropped = base.validate_points([{"claim": "Revenue will grow 40% next year.", "facts": ["F2"]}], self.FACTS)
        self.assertEqual(kept, [])
        self.assertIn("40%", dropped[0]["why"])

    def test_drops_unknown_or_missing_fact_ids(self):
        kept, dropped = base.validate_points([{"claim": "Strong brand.", "facts": ["F99"]},
                                              {"claim": "Good management.", "facts": []}], self.FACTS)
        self.assertEqual(kept, [])
        self.assertEqual(len(dropped), 2)

    def test_rounding_is_allowed(self):
        self.assertEqual(base.numbers_supported("Debt is about 22% of assets.", self.FACTS), [])


class Audit(unittest.TestCase):
    def setUp(self):
        self.gate = shariah_checker.gate(result())

    def test_rule_checks_remove_forbidden_wording_and_products(self):
        statements = {"BU1": "This stock is halal and safe.", "BE1": "You could buy it on margin.",
                      "RK1": "Volatility is moderate."}
        with mock.patch.object(shariah_checker, "run_agent", return_value={"problems": []}):
            a = shariah_checker.audit(self.gate, statements)
        self.assertIn("BU1", a["removed"])
        self.assertIn("BE1", a["removed"])
        self.assertNotIn("RK1", a["removed"])
        self.assertFalse(a["approved"])

    def test_overclaim_removed_when_gate_is_not_pass(self):
        g = shariah_checker.gate(result({"interest_income": None}))
        with mock.patch.object(shariah_checker, "run_agent", return_value={"problems": []}):
            a = shariah_checker.audit(g, {"BU1": "The company is fully compliant."})
        self.assertIn("BU1", a["removed"])

    def test_llm_audit_problems_are_removed(self):
        with mock.patch.object(shariah_checker, "run_agent", return_value={"problems": [{"id": "BU1", "issue": "x"}]}):
            a = shariah_checker.audit(self.gate, {"BU1": "Compliance risk is nothing to worry about."})
        self.assertIn("BU1", a["removed"])

    def test_unavailable_llm_audit_is_not_approved(self):
        with mock.patch.object(shariah_checker, "run_agent", return_value=None):
            a = shariah_checker.audit(self.gate, {"BU1": "Revenue is steady."})
        self.assertFalse(a["approved"])
        self.assertFalse(a["llm_checked"])


class Committee(unittest.TestCase):
    def test_unreadable_llm_replies_do_not_crash(self):
        with mock.patch.object(base.llm, "ask_json", return_value=None):
            out = committee.run(result())
        self.assertTrue(out["ran"])
        self.assertFalse(out["bull"]["available"])
        self.assertFalse(out["risk"]["available"])
        self.assertFalse(out["audit"]["approved"])

    def test_full_run_with_fictional_replies(self):
        replies = {
            "BULL": {"thesis": "Low debt.", "points": [{"claim": "Debt is 10.0% of assets.", "facts": ["F_DEBT"]}],
                     "what_would_change_my_mind": "Higher debt."},
            "BEAR": {"thesis": "This stock is halal so buy more.", "points": [{"claim": "Sales may fall 50%.",
                                                                              "facts": ["F_DEBT"]}],
                     "what_would_change_my_mind": "x"},
        }
        r = result()
        pack = evidence.build(r)
        debt_id = next(k for k, f in pack.facts.items() if f["label"].startswith("Screen: Debt") and f["unit"] == "ratio"
                       and "limit" not in f["label"])

        def fake(system, payload, max_tokens=1200):
            if "BULL ANALYST" in system or "BEAR ANALYST" in system:
                rep = replies["BULL" if "BULL ANALYST" in system else "BEAR"]
                return {**rep, "points": [{**p, "facts": [debt_id]} for p in rep["points"]]}
            if "RISK REVIEWER" in system:
                return {"stronger_case": "balanced", "unsupported_claims": [], "key_risks": [], "flag": None,
                        "summary_for_investor": "Both sides have a point."}
            return {"problems": []}
        with mock.patch.object(analysts, "run_agent", side_effect=fake), \
             mock.patch.object(shariah_checker, "run_agent", side_effect=fake):
            out = committee.run(r)
        self.assertEqual(len(out["bull"]["points"]), 1)                 # supported claim kept
        self.assertEqual(out["bear"]["points"], [])                     # "50%" invented -> dropped
        self.assertEqual(out["bear"]["thesis"], "")                     # "halal" -> removed by the audit
        self.assertIn("BE0", out["audit"]["removed"])


class Portfolio(unittest.TestCase):
    def test_refuses_anything_that_did_not_pass(self):
        with self.assertRaises(portfolio.NotCompliantError):
            portfolio.build(["AAA", "BBB"], {"AAA": PASS, "BBB": NEEDS_REVIEW})
        with self.assertRaises(portfolio.NotCompliantError):
            portfolio.build(["CCC"], {})


class BusinessReader(unittest.TestCase):
    def test_quotes_are_checked_and_unknown_categories_ignored(self):
        from shariah import llm
        text = "Fictional Corp brews beer and sells widgets. Beer was 12% of revenue."
        reply = {"activities": [{"category": "alcohol", "revenue_share_pct": 12, "min_revenue_share_pct": 12,
                                 "primary_business": False, "evidence": "Beer was 12% of revenue", "confidence": "high"},
                                {"category": "gambling", "revenue_share_pct": 1, "evidence": "invented quote here",
                                 "confidence": "low"},
                                {"category": "space_lasers", "revenue_share_pct": 99, "evidence": "x"}],
                 "main_business": "Beer and widgets.", "main_business_quote": "Fictional Corp brews beer"}
        with mock.patch.object(llm, "ask_json", return_value=reply):
            b = llm.business_screen("Fictional Corp", text)
        cats = {a["category"]: a for a in b["activities"]}
        self.assertEqual(set(cats), {"alcohol", "gambling"})
        self.assertTrue(cats["alcohol"]["quote_verified"])
        self.assertFalse(cats["gambling"]["quote_verified"])
        self.assertTrue(b["main_quote_verified"])


if __name__ == "__main__":
    unittest.main()


class PortfolioCap(unittest.TestCase):
    def test_cap_holds_with_few_stocks_and_rest_is_cash(self):
        import pandas as pd
        fake = pd.Series([100 + i * (1 + (i % 3)) for i in range(400)], dtype=float,
                         index=pd.date_range("2025-01-01", periods=400))   # FICTIONAL prices
        with mock.patch.object(portfolio.prices, "history", return_value=fake):
            alloc = portfolio.build(["AAA", "BBB", "CCC"], {"AAA": PASS, "BBB": PASS, "CCC": PASS}, 100_000)
        eq = alloc[alloc["holding"] != "CASH"]
        self.assertTrue((eq["weight"] <= 0.10 + 1e-9).all())
        self.assertAlmostEqual(alloc["weight"].sum(), 1.0)
        self.assertAlmostEqual(float(alloc.set_index("holding").loc["CASH", "weight"]), 0.70)
