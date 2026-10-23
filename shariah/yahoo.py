"""Yahoo Finance (via yfinance): company search and fundamentals for any listed company,
including London (.L) tickers that SEC EDGAR doesn't cover. Free, no key. Cached to
data_cache/ like everything else.

Returns the same dict shape as edgar.financials() so screen.verdict() works unchanged.
Yahoo figures are a data vendor's copy of the accounts, not the filing itself - the UI
says so and links the company's own reports for checking."""
import datetime as dt

from .cache import cached

QUOTE_URL = "https://finance.yahoo.com/quote/{symbol}"


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


def _pick(df, names):
    """Latest non-empty value of the first row name that exists. -> (value, row name, period end)."""
    for n in names:
        if n in df.index:
            s = df.loc[n].dropna()
            if len(s):
                return float(s.iloc[0]), n, str(s.index[0].date())
    return None, None, None


def company(symbol: str) -> dict:
    """Profile + the numbers the Shariah screens need, in the company's reporting currency."""
    def produce():
        tk = _yf().Ticker(symbol)
        info = tk.info
        bs, inc, cf = tk.balance_sheet, tk.income_stmt, tk.cashflow
        out = {"ticker": symbol, "name": info.get("longName") or info.get("shortName") or symbol, "sources": {}}

        out["total_assets"], out["sources"]["total_assets"], out["period_end"] = _pick(bs, ["Total Assets"])
        debt, c, _ = _pick(bs, ["Total Debt"])
        out["total_debt"], out["sources"]["total_debt"] = debt or 0, c or "not reported"
        cash, c, _ = _pick(bs, ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"])
        out["cash_and_interest_bearing"], out["sources"]["cash_and_interest_bearing"] = cash or 0, c or "not reported"
        rec, c, _ = _pick(bs, ["Receivables", "Accounts Receivable"])
        out["receivables"], out["sources"]["receivables"] = rec or 0, c or "not reported"
        out["revenue"], out["sources"]["revenue"], _ = _pick(inc, ["Total Revenue", "Operating Revenue"])
        ii, c, _ = _pick(inc, ["Interest Income", "Interest Income Non Operating"])
        out["interest_income"], out["sources"]["interest_income"] = ii or 0, c or "not reported"
        dv, c, _ = _pick(cf, ["Cash Dividends Paid", "Common Stock Dividend Paid"])
        out["dividends_paid"], out["sources"]["dividends_paid"] = abs(dv or 0), c or "not reported"
        out["shares_outstanding"] = info.get("sharesOutstanding")
        out["sources"]["shares_outstanding"] = "sharesOutstanding"

        out["profile"] = {k: info.get(k) for k in ("sector", "industry", "longBusinessSummary", "website",
                                                     "country", "exchange", "currency", "financialCurrency")}
        out["price"] = info.get("currentPrice") or info.get("regularMarketPrice")
        out["source_url"] = QUOTE_URL.format(symbol=symbol)
        return out
    fin = cached(f"yahoo_company_{symbol}", produce)

    # Market cap in the reporting currency, so AAOIFI's market-cap ratios compare like with like
    # (e.g. BP: price in pence, accounts in US dollars).
    p = fin["profile"]
    try:
        fin["market_cap"] = (fin["shares_outstanding"] * fin["price"] *
                             fx_rate(p.get("currency") or "USD", p.get("financialCurrency") or p.get("currency") or "USD"))
    except Exception:
        fin["market_cap"] = None
    return fin
