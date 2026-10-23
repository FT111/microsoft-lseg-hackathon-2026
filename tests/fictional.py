"""FICTIONAL test data - made-up companies and numbers, not real financial data."""


def fin(**over):
    """A fictional, clean company: every ratio well inside every limit."""
    base = {"ticker": "FICT", "name": "Fictional Widgets Ltd (FICTIONAL)", "cik": "0000000000", "period_end": "2026-06-30",
            "total_assets": 1000.0, "total_debt": 100.0, "cash_and_interest_bearing": 100.0,
            "long_term_interest_bearing": None, "receivables": 100.0, "revenue": 1000.0, "interest_income": 5.0,
            "shares_outstanding": 10.0, "dividends_paid": 10.0, "stale": False, "notes": [], "items": {},
            "sources": {}, "income_period": ("2025-07-01", "2026-06-30")}
    base.update(over)
    return base


def business(*activities, main_verified=True):
    return {"method": "LLM", "activities": list(activities), "main_business": "Makes fictional widgets.",
            "main_business_quote": "we make fictional widgets", "main_quote_verified": main_verified,
            "evidence": "we make fictional widgets"}


def activity(category, pct, confidence="high", verified=True, primary=False, floor=0.0):
    return {"category": category, "revenue_share_pct": pct, "min_revenue_share_pct": floor, "confidence": confidence,
            "quote_verified": verified, "primary_business": primary, "evidence": "fictional quote"}


MCAP = {"value": 2000.0, "note": "fictional market value"}
