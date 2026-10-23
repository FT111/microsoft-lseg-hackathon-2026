"""One place that screens a stock end to end, so the app, warm_cache.py and the agent
committee all get identical results.

US-listed SEC filers use the filings themselves (edgar.py + AI reading of the 10-K).
Everything else (UK etc.) uses Yahoo Finance's copy of the accounts (yahoo.py) and an
industry rule for business activity - which can only FAIL or NEEDS REVIEW, never PASS,
because no filing text has been read."""
from . import edgar, llm, prices, screen


def on_sec(ticker: str) -> bool:
    try:
        return "." not in ticker and ticker.upper() in edgar.ticker_to_cik()
    except Exception:
        return False


def market_value(fin: dict, ticker: str, fx: float | None = 1.0) -> dict | None:
    """12-month average price x shares outstanding (used by AAOIFI), in the reporting currency.
    None if shares, prices or the exchange rate are missing."""
    shares = fin.get("shares_outstanding")
    if not shares or fx is None:
        return None
    try:
        avg = prices.average_price(ticker)
    except Exception:
        return None
    return {"value": shares * avg["value"] * fx, "average_price": avg["value"], "price_window": (avg["start"], avg["end"]),
            "shares": shares, "shares_source": fin["sources"].get("shares_outstanding"),
            "note": f"12-month average price {avg['value']:,.2f} ({avg['start']} to {avg['end']}) x "
                    f"{shares / 1e9:,.2f}bn shares" + (f" x FX {fx:.4f}" if fx != 1.0 else "")}


def find_missing_figures(ticker: str, fin: dict, use_ai: bool = True) -> dict:
    """Data-finder step of the Shariah compliance check: figures the XBRL data lacks are looked
    up by the AI in the filing text, verified in Python, and marked so no screen can PASS on them."""
    missing = [k for k in edgar.REQUIRED_FOR_SCREENS if k in (fin.get("missing") or [])]
    if not missing or not use_ai or not llm.available() or not fin.get("period_end"):
        return fin
    for annual in (False, True):
        keys = [k for k in missing if (k in edgar.INCOME_KEYS) == annual]
        if not keys:
            continue
        try:
            ft = edgar.financial_text(ticker, fin["period_end"], annual=annual)
            if not ft.get("text"):
                continue
            found = llm.extract_figures(fin["name"], ft["text"], {k: edgar.FIGURE_LABELS[k] for k in keys})
        except Exception as e:
            fin = {**fin, "notes": fin.get("notes", []) + [f"AI figure search failed: {type(e).__name__}"]}
            continue
        if found:
            fin = edgar.apply_extracted(fin, found, ft)
    return fin


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
    if not on_sec(ticker):
        from . import yahoo
        fin = yahoo.company(ticker)
        p = fin.get("profile") or {}
        biz = screen.industry_rule(p.get("sector"), p.get("industry"))
        biz["source_url"] = fin.get("source_url")
        biz["filing_date"] = None
        biz["sic"] = p.get("industry")
        mcap = market_value(fin, ticker, yahoo.reporting_fx(fin)) if fin.get("period_end") else None
        v = screen.verdict(fin, biz, standard, mcap)
        return {"ticker": ticker, "fin": fin, "sic": p.get("industry"), "mcap": mcap, "business": biz, "verdict": v,
                "source": "Yahoo Finance", "profile": p, "currency": p.get("financialCurrency") or p.get("currency") or ""}
    fin = edgar.financials(ticker)
    if fin.get("name", "").isupper():
        fin = {**fin, "name": fin["name"].title()}
    fin = find_missing_figures(ticker, fin, use_ai)
    mcap = market_value(fin, ticker)
    biz = business(ticker, fin, use_ai)
    v = screen.verdict(fin, biz, standard, mcap)
    return {"ticker": ticker, "fin": fin, "sic": biz.get("sic"), "mcap": mcap, "business": biz, "verdict": v,
            "source": "SEC EDGAR", "profile": {"industry": biz.get("sic"), "exchange": "US"}, "currency": "USD"}
