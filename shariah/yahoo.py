"""Yahoo Finance (via yfinance): company search and fundamentals for any listed company,
including London (.L) tickers that SEC EDGAR doesn't cover. Free, no key. Cached to
data_cache/ like everything else.

Returns the same dict shape as edgar.financials(), with the same rules: every figure carries
its source row and date, a MISSING figure is None (never 0), and all balance-sheet items come
from one reporting date. Yahoo figures are a data vendor's copy of the accounts, not the
filing itself - the UI says so and links the company's own pages for checking."""
import datetime as dt

from .cache import cached

QUOTE_URL = "https://finance.yahoo.com/quote/{symbol}"
STALE_AFTER_DAYS = 480


def _yf():
    import yfinance  # imported lazily so the US-only path works without it
    return yfinance


def search(query: str, limit: int = 8) -> list[dict]:
    """Listed equities matching a company name or ticker, best match first."""
    q = query.strip()
    if not q:
        return []
    def produce():
        quotes = _yf().Search(q, max_results=limit, news_count=0).quotes
        return [{"symbol": x["symbol"], "name": x.get("longname") or x.get("shortname") or x["symbol"],
                 "exchange": x.get("exchDisp") or x.get("exchange") or ""}
                for x in quotes if x.get("quoteType") == "EQUITY"]
    return cached(f"yahoo_search_{q.lower()}", produce)


def fx_rate(src: str, dst: str) -> float:
    """Units of dst per one unit of src. Handles pence ('GBp'). Cached per day."""
    scale = 1.0
    if src == "GBp":
        src, scale = "GBP", 0.01
    if src == dst:
        return scale
    def produce():
        return float(_yf().Ticker(f"{src}{dst}=X").fast_info["last_price"])
    return scale * cached(f"fx_{src}{dst}_{dt.date.today()}", produce)


def _frame(df) -> dict:
    """{row name: {date: value}} with NaNs dropped, dates as ISO strings."""
    out = {}
    for name, row in df.iterrows():
        vals = {str(k.date()): float(v) for k, v in row.items() if v == v and v is not None}
        if vals:
            out[str(name)] = vals
    return out


def _at(frame: dict, names: list[str], date: str, label: str):
    for n in names:
        v = frame.get(n, {}).get(date)
        if v is not None:
            return {"value": v, "concept": f"Yahoo Finance: {n}", "period_end": date, "label": label}
    return None


def _sum(parts, label):
    parts = [p for p in parts if p]
    if not parts:
        return None
    return {"value": sum(p["value"] for p in parts), "concept": " + ".join(p["concept"] for p in parts),
            "period_end": parts[0]["period_end"], "label": label}


def interest_item(inc: dict, rev_end: str, industry: str | None):
    """Interest income for the revenue period, like-for-like with the revenue figure.
    Banks report revenue net of interest expense, so for them (industry says 'bank', or gross
    interest income is larger than revenue) NET interest income is used. Returns (item, note)."""
    gross = _at(inc, ["Interest Income", "Interest Income Non Operating"], rev_end, "interest income")
    net = _at(inc, ["Net Interest Income"], rev_end, "net interest income")
    rev = _at(inc, ["Total Revenue", "Operating Revenue"], rev_end, "revenue")
    is_bank = "bank" in (industry or "").lower() or (gross and rev and gross["value"] > rev["value"])
    if is_bank and net and net["value"] >= 0:
        return net, ("interest income: net interest income (the company reports revenue net of interest expense, "
                     "so this is the like-for-like share)")
    if gross and gross["value"] >= 0:
        return gross, None
    return None, None


def company(symbol: str, today: str | None = None) -> dict:
    """Profile + the numbers the Shariah screens need, in the company's reporting currency."""
    def produce():
        tk = _yf().Ticker(symbol)
        info = tk.info
        return {"info": {k: info.get(k) for k in ("longName", "shortName", "sector", "industry", "longBusinessSummary",
                                                  "website", "country", "exchange", "currency", "financialCurrency",
                                                  "sharesOutstanding", "currentPrice", "regularMarketPrice")},
                "balance_sheet": _frame(tk.balance_sheet), "income": _frame(tk.income_stmt), "cashflow": _frame(tk.cashflow)}
    raw = cached(f"yahoo_company_v2_{symbol}", produce)
    info, bs, inc, cf = raw["info"], raw["balance_sheet"], raw["income"], raw["cashflow"]

    out = {"ticker": symbol, "name": info.get("longName") or info.get("shortName") or symbol, "cik": None, "notes": []}
    dates = sorted(bs.get("Total Assets", {}), reverse=True)
    if not dates:
        out.update({"period_end": None, "items": {}, "missing": ["balance sheet"], "sources": {}, "stale": True})
        return out
    end = dates[0]
    # Debt WITHOUT lease liabilities, like the SEC path. Yahoo's "Total Debt" includes leases.
    lt = _at(bs, ["Long Term Debt"], end, "long-term debt")
    cur = _at(bs, ["Current Debt"], end, "current debt")
    debt = _sum([lt, cur], "total debt") if (lt or cur) else None
    if debt and not (lt and cur):
        out["notes"].append("only one of long-term / current debt is reported by Yahoo - the other counted as 0")
    cash = _at(bs, ["Cash And Cash Equivalents", "Cash Financial"], end, "cash")
    st = _at(bs, ["Other Short Term Investments"], end, "short-term investments")
    both = _at(bs, ["Cash Cash Equivalents And Short Term Investments"], end, "cash + short-term investments")
    if cash and not st and both and both["value"] > cash["value"]:
        st = {**both, "value": both["value"] - cash["value"], "concept": both["concept"] + " - " + cash["concept"]}
    if cash and not st:
        out["notes"].append("no short-term investments reported by Yahoo - counted as 0")
    items = {
        "total_assets": _at(bs, ["Total Assets"], end, "total assets"),
        "total_debt": debt,
        "cash": cash,
        "short_term_interest_bearing": st,
        "long_term_interest_bearing": _at(bs, ["Available For Sale Securities", "Held To Maturity Securities"], end,
                                          "long-term interest-bearing securities"),
        "receivables": _at(bs, ["Receivables", "Accounts Receivable"], end, "receivables"),
        "cash_and_interest_bearing": _sum([cash, st], "cash + short-term interest-bearing items") if cash else None,
    }
    inc_dates = sorted(inc.get("Total Revenue", {}) or inc.get("Operating Revenue", {}), reverse=True)
    rev_end = inc_dates[0] if inc_dates else None
    items["revenue"] = _at(inc, ["Total Revenue", "Operating Revenue"], rev_end, "revenue") if rev_end else None
    items["interest_income"], note = interest_item(inc, rev_end, info.get("industry")) if rev_end else (None, None)
    if note:
        out["notes"].append(note)
    dv = _at(cf, ["Cash Dividends Paid", "Common Stock Dividend Paid"], rev_end, "dividends paid") if rev_end else None
    items["dividends_paid"] = {**dv, "value": abs(dv["value"])} if dv else None
    sh = info.get("sharesOutstanding")
    items["shares_outstanding"] = {"value": float(sh), "concept": "Yahoo Finance: sharesOutstanding", "period_end": end} if sh else None

    out["period_end"], out["items"] = end, items
    out["missing"] = [k for k in ("total_assets", "total_debt", "cash", "receivables", "revenue", "interest_income",
                                  "shares_outstanding") if not items.get(k)]
    today = today or dt.date.today().isoformat()
    out["stale"] = (dt.date.fromisoformat(today) - dt.date.fromisoformat(end)).days > STALE_AFTER_DAYS
    out["income_period"] = (None, rev_end) if rev_end else None
    for k, v in items.items():
        out[k] = v["value"] if v else None
    out["sources"] = {k: (v["concept"] if v else "not reported") for k, v in items.items()}
    out["profile"] = {k: info.get(k) for k in ("sector", "industry", "longBusinessSummary", "website", "country",
                                                 "exchange", "currency", "financialCurrency")}
    out["price"] = info.get("currentPrice") or info.get("regularMarketPrice")
    out["source_url"] = QUOTE_URL.format(symbol=symbol)
    return out


def reporting_fx(fin: dict) -> float | None:
    """Multiply a quoted price by this to get the reporting currency (e.g. pence -> US dollars for BP)."""
    p = fin.get("profile") or {}
    try:
        return fx_rate(p.get("currency") or "USD", p.get("financialCurrency") or p.get("currency") or "USD")
    except Exception:
        return None
