"""Daily price history. Yahoo's public chart endpoint (no key), Stooq as backup.
Everything is cached to data_cache/ so the demo runs offline once warmed up."""
import io

import pandas as pd
import requests

from .cache import cached

UA = {"User-Agent": "Mozilla/5.0"}


def _yahoo(ticker: str) -> dict:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=25y&interval=1d&includeAdjustedClose=true"
    j = requests.get(url, headers=UA, timeout=30).json()
    res = j["chart"]["result"][0]
    ts = pd.to_datetime(res["timestamp"], unit="s").strftime("%Y-%m-%d").tolist()
    adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose") or res["indicators"]["quote"][0]["close"]
    pairs = [(d, c) for d, c in zip(ts, adj) if c is not None]
    return {"date": [p[0] for p in pairs], "close": [p[1] for p in pairs], "source": "yahoo"}


def _stooq(ticker: str) -> dict:
    text = requests.get(f"https://stooq.com/q/d/l/?s={ticker.lower()}.us&i=d", headers=UA, timeout=30).text
    if not text.startswith("Date"):
        raise RuntimeError(f"Stooq returned no data for {ticker}")
    df = pd.read_csv(io.StringIO(text))
    return {"date": df["Date"].tolist(), "close": df["Close"].tolist(), "source": "stooq"}


def history(ticker: str, start: str = "2007-01-01") -> pd.Series:
    """Adjusted daily close (dividends reinvested) as a Series indexed by date."""
    def produce():
        try:
            return _yahoo(ticker)
        except Exception:
            if "." in ticker:  # Stooq fallback is US-only here; don't fetch a different company
                raise
            return _stooq(ticker)
    data = cached(f"prices_{ticker}", produce)
    s = pd.Series(data["close"], index=pd.to_datetime(data["date"]), name=ticker).sort_index()
    return s[s.index >= start]


def last_price(ticker: str) -> float:
    return float(history(ticker).iloc[-1])


def average_price(ticker: str, days: int = 365) -> dict:
    """Average daily close over the last `days`, with the window used. Adjusted closes are
    slightly below the prices actually traded (dividends are taken out), which makes the
    market value a little lower and the AAOIFI ratios a little higher - the cautious side."""
    s = history(ticker)
    s = s[s.index >= s.index[-1] - pd.Timedelta(days=days)]
    return {"value": float(s.mean()), "start": s.index[0].strftime("%Y-%m-%d"), "end": s.index[-1].strftime("%Y-%m-%d"),
            "observations": int(len(s))}
