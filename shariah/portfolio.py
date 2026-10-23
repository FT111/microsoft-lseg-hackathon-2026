"""Allocation, stress test and purification. Deterministic maths - no LLM - so the
same inputs always give the same answer and every number can be explained."""
import numpy as np
import pandas as pd

from . import prices


def equity_weights(tickers: list[str], cap: float = 0.10, lookback_days: int = 756) -> pd.Series:
    """Inverse-volatility weights (lower-risk stocks get more), capped per holding."""
    vols = {}
    for t in tickers:
        r = prices.history(t).pct_change().dropna().iloc[-lookback_days:]
        if len(r) > 60:
            vols[t] = r.std() * np.sqrt(252)
    if not vols:
        return pd.Series(dtype=float)
    w = 1 / pd.Series(vols)
    w = w / w.sum()
    for _ in range(50):  # redistribute anything above the cap
        over = w > cap
        if not over.any():
            break
        excess = (w[over] - cap).sum()
        w[over] = cap
        under = ~over
        w[under] += excess * w[under] / w[under].sum()
    return w / w.sum()


def build(equity_tickers, amount=100_000, equity_share=0.60, sukuk_share=0.30, sukuk="SPSK", cap=0.10):
    cash_share = 1 - equity_share - sukuk_share
    w = equity_weights(equity_tickers, cap=cap / equity_share if equity_share else cap) * equity_share
    rows = [{"holding": t, "sleeve": "Shariah equities", "weight": float(x)} for t, x in w.items()]
    rows.append({"holding": sukuk, "sleeve": "Sukuk (Islamic bonds)", "weight": sukuk_share})
    rows.append({"holding": "CASH", "sleeve": "Non-interest cash (payout reserve)", "weight": cash_share})
    df = pd.DataFrame(rows)
    df["amount"] = df["weight"] * amount
    return df


def calendar_year_return(ticker: str, year: int) -> float | None:
    if ticker == "CASH":
        return 0.0
    s = prices.history(ticker)
    y = s[s.index.year == year]
    prev = s[s.index.year == year - 1]
    if y.empty or prev.empty:
        return None
    return float(y.iloc[-1] / prev.iloc[-1] - 1)


def stress_test(alloc: pd.DataFrame, years=(2008, 2020, 2022), payout_rate=0.04,
                scholarship_cost=500, amount=100_000) -> pd.DataFrame:
    """Portfolio return in past bad years, and what that means in scholarships.
    Holdings without data for a year (e.g. the sukuk ETF before it existed) use the
    sleeve average of what is available, and are flagged."""
    out = []
    normal_scholarships = int(amount * payout_rate // scholarship_cost)
    for y in years:
        total, missing = 0.0, []
        for _, row in alloc.iterrows():
            r = calendar_year_return(row["holding"], y)
            if r is None:
                missing.append(row["holding"])
                r = 0.0
            total += row["weight"] * r
        end_value = amount * (1 + total)
        out.append({"year": y, "portfolio_return": total, "value_after": end_value,
                    "scholarships": int(end_value * payout_rate // scholarship_cost),
                    "normal_scholarships": normal_scholarships,
                    "missing_data": ", ".join(missing)})
    return pd.DataFrame(out)


def purification(alloc: pd.DataFrame, fin_by_ticker: dict, nc_by_ticker: dict) -> pd.DataFrame:
    """Share of dividends to give to charity = dividend received x non-compliant income share.
    Dividend yield estimated from SEC 'dividends paid' / market cap."""
    rows = []
    for _, row in alloc.iterrows():
        t = row["holding"]
        fin = fin_by_ticker.get(t)
        if not fin or not fin.get("shares_outstanding"):
            continue
        mcap = fin["shares_outstanding"] * prices.last_price(t)
        yld = (fin.get("dividends_paid") or 0) / mcap if mcap else 0
        dividend = row["amount"] * yld
        nc = nc_by_ticker.get(t) or 0
        rows.append({"holding": t, "dividend_yield": yld, "dividend_received": dividend,
                     "noncompliant_share": nc, "to_purify": dividend * nc})
    return pd.DataFrame(rows)
