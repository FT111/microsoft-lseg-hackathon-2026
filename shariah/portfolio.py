"""Allocation, stress test and purification. Deterministic maths - no LLM - so the
same inputs always give the same answer and every number can be explained.

Every holding must have passed the Shariah screens of the chosen standard: build()
refuses anything else. The only non-equity holding is non-interest-bearing cash."""
import numpy as np
import pandas as pd

from . import prices
from .methodology import METHODOLOGIES, PASS


class NotCompliantError(ValueError):
    """Raised when something that has not passed the Shariah screens is put in a portfolio."""


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
    if cap * len(w) <= 1:         # too few stocks to fill the sleeve under the cap: each gets the cap,
        return pd.Series(cap, index=w.index)   # the rest stays in non-interest-bearing cash
    for _ in range(50):  # redistribute anything above the cap
        over = w > cap + 1e-12
        if not over.any():
            break
        excess = (w[over] - cap).sum()
        w[over] = cap
        under = ~over
        w[under] += excess * w[under] / w[under].sum()
    return w / w.sum()


def build(equity_tickers, statuses: dict, amount=100_000, equity_share=1.0, cap=0.10) -> pd.DataFrame:
    """statuses: {ticker: overall Shariah status}. Every ticker must be PASS."""
    bad = {t: statuses.get(t, "not screened") for t in equity_tickers if statuses.get(t) != PASS}
    if bad:
        raise NotCompliantError("only stocks that PASS every Shariah screen can be held: " +
                                ", ".join(f"{t} ({s})" for t, s in bad.items()))
    w = equity_weights(list(equity_tickers), cap=min(1.0, cap / equity_share) if equity_share else cap) * equity_share
    rows = [{"holding": t, "sleeve": "Shariah-screened equities", "weight": float(x)} for t, x in w.items()]
    rows.append({"holding": "CASH", "sleeve": "Non-interest-bearing cash", "weight": 1 - float(w.sum())})
    df = pd.DataFrame(rows)
    df = df[df["weight"] > 1e-9].reset_index(drop=True)
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


def stress_test(alloc: pd.DataFrame, years=(2008, 2020, 2022), amount=100_000) -> pd.DataFrame:
    """What past bad (and good) years would have done to this portfolio, in money.
    Holdings with no data for a year (e.g. listed later) count as 0% and are flagged."""
    out = []
    for y in years:
        total, missing = 0.0, []
        for _, row in alloc.iterrows():
            r = calendar_year_return(row["holding"], y)
            if r is None:
                missing.append(row["holding"])
                r = 0.0
            total += row["weight"] * r
        out.append({"year": y, "portfolio_return": total, "value_after": amount * (1 + total),
                    "gain_or_loss": amount * total, "no_data_for": ", ".join(missing)})
    return pd.DataFrame(out)


def purification(alloc: pd.DataFrame, fin_by_ticker: dict, nc_by_ticker: dict, standard: str) -> pd.DataFrame:
    """Amount to give to charity, by the chosen standard's method.
    FTSE Yasaar (rule 4.4): dividends received x the company's non-compliant income share.
    AAOIFI (SS 21 clause 3/4/6 via the MSX guide): non-compliant income per share x shares held.
    Where the non-compliant share is unknown the amount is left blank, not guessed."""
    method = METHODOLOGIES[standard]["purification"]["method"]
    rows = []
    for _, row in alloc.iterrows():
        t = row["holding"]
        fin = fin_by_ticker.get(t)
        if t == "CASH" or not fin:
            continue
        price = prices.last_price(t)
        shares_held = row["amount"] / price if price else 0
        nc = nc_by_ticker.get(t)
        sh = fin.get("shares_outstanding")
        mcap = sh * price if sh else None
        yld = (fin.get("dividends_paid") or 0) / mcap if mcap else None
        dividend = row["amount"] * yld if yld is not None else None
        if nc is None:
            amount, note = None, "non-compliant income share unknown"
        elif method == "dividends":
            amount, note = (dividend * nc if dividend is not None else None), "dividends x non-compliant share"
        else:
            rev = fin.get("revenue")
            amount = (nc * rev / sh * shares_held) if (rev and sh) else None
            note = "non-compliant income per share x shares held"
        rows.append({"holding": t, "dividend_yield": yld, "dividend_received": dividend, "noncompliant_share": nc,
                     "to_purify": amount, "method": note})
    return pd.DataFrame(rows)
