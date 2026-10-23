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


def ohlc(ticker: str) -> pd.DataFrame:
    """Daily open/high/low/close/volume for the last 5 years, for candlestick charts.
    Unadjusted prices in the listing currency (attrs['currency'], e.g. 'GBp' for London)."""
    def produce():
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=5y&interval=1d"
        res = requests.get(url, headers=UA, timeout=30).json()["chart"]["result"][0]
        q = res["indicators"]["quote"][0]
        return {"date": pd.to_datetime(res["timestamp"], unit="s").strftime("%Y-%m-%d").tolist(),
                **{k: q[k] for k in ("open", "high", "low", "close", "volume")},
                "currency": res["meta"].get("currency")}
    d = cached(f"ohlc_{ticker}", produce)
    df = pd.DataFrame({k: d[k] for k in ("open", "high", "low", "close", "volume")},
                      index=pd.to_datetime(d["date"])).dropna()
    df.attrs["currency"] = d.get("currency")
    return df
