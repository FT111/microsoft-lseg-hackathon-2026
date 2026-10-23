"""One place that screens a stock end to end, so the app, warm_cache.py and the agent
committee all get identical results."""
from . import edgar, llm, prices, screen


def market_value(fin: dict, ticker: str) -> dict | None:
    """12-month average price x shares outstanding (used by AAOIFI). None if either is missing."""
    shares = fin.get("shares_outstanding")
    if not shares:
        return None
    try:
        avg = prices.average_price(ticker)
    except Exception:
        return None
    return {"value": shares * avg["value"], "average_price": avg["value"], "price_window": (avg["start"], avg["end"]),
            "shares": shares, "shares_source": fin["sources"].get("shares_outstanding"),
            "note": f"12-month average price ${avg['value']:,.2f} ({avg['start']} to {avg['end']}) x "
                    f"{shares / 1e9:,.2f}bn shares"}


def business(ticker: str, fin: dict, use_ai: bool = True) -> dict:
    sub = edgar.submissions(ticker)
    tenk = sub.get("latest_10k") or {}
    if use_ai and llm.available():
        item1 = edgar.business_section(ticker)
        b = llm.business_screen(fin["name"], item1["text"]) if item1.get("text") else \
            {**screen.sic_rule(sub["sicDescription"]), "error": None}
    else:
        b = screen.sic_rule(sub["sicDescription"])
    b["source_url"] = tenk.get("url")
    b["filing_date"] = tenk.get("date")
    b["sic"] = sub.get("sicDescription")
    return b


def screen_one(ticker: str, standard: str, use_ai: bool = True) -> dict:
    fin = edgar.financials(ticker)
    if fin.get("name", "").isupper():
        fin = {**fin, "name": fin["name"].title()}
    mcap = market_value(fin, ticker)
    biz = business(ticker, fin, use_ai)
    v = screen.verdict(fin, biz, standard, mcap)
    return {"ticker": ticker, "fin": fin, "sic": biz.get("sic"), "mcap": mcap, "business": biz, "verdict": v}
