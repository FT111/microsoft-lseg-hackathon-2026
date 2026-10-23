"""Rank Shariah-compliant stocks. Transparent factors only - every score can be
explained in one sentence. This ranks candidates; it does not predict prices.

Factors (each turned into a 0-100 percentile across the passing stocks):
- Momentum      : 12-month return excluding the last month (classic 12-1 momentum)
- Low risk      : lower annualised volatility scores higher
- Drawdown      : smaller worst fall over the past year scores higher
- Compliance headroom : how far the stock sits below the Shariah ratio limits.
  A stock near a limit may turn non-compliant and have to be sold - a real cost
  for a Shariah investor that ordinary screeners ignore.
"""
import numpy as np
import pandas as pd

from . import prices

WEIGHTS = {"momentum": 0.35, "low_risk": 0.25, "drawdown": 0.15, "headroom": 0.25}

# Risk appetite changes what "good" means for this investor.
PROFILES = {
    "Cautious":    {"momentum": 0.15, "low_risk": 0.35, "drawdown": 0.25, "headroom": 0.25},
    "Balanced":    WEIGHTS,
    "Adventurous": {"momentum": 0.55, "low_risk": 0.10, "drawdown": 0.10, "headroom": 0.25},
}


def price_metrics(ticker: str) -> dict:
    s = prices.history(ticker)
    s = s[s.index >= s.index[-1] - pd.Timedelta(days=400)]
    r = s.pct_change().dropna()
    last = s.iloc[-1]
    def ago(days):
        sub = s[s.index <= s.index[-1] - pd.Timedelta(days=days)]
        return sub.iloc[-1] if len(sub) else np.nan
    yr = s[s.index >= s.index[-1] - pd.Timedelta(days=365)]
    return {
        "price": float(last),
        "return_1y": float(last / ago(365) - 1),
        "momentum_12_1": float(ago(30) / ago(365) - 1),
        "volatility": float(r.iloc[-252:].std() * np.sqrt(252)),
        "max_drawdown_1y": float((yr / yr.cummax() - 1).min()),
        "off_52w_high": float(last / yr.max() - 1),
    }


def headroom(verdict: dict, standard_rules: dict) -> float:
    """Smallest distance (as a share of the limit) between a ratio and its limit. 1 = far, 0 = at the limit."""
    base = verdict["ratios"].get(standard_rules["denominator"]) or {}
    gaps = []
    for key in ("debt", "cash", "receivables", "receivables_plus_cash"):
        lim = standard_rules.get(key)
        if lim and key in base:
            gaps.append(max(0.0, 1 - base[key] / lim))
    nc = verdict.get("noncompliant_income_pct")
    if nc is not None:
        gaps.append(max(0.0, 1 - nc / standard_rules["noncompliant_revenue"]))
    return min(gaps) if gaps else np.nan


def rank(passing: dict, standard_rules: dict, weights: dict = WEIGHTS) -> pd.DataFrame:
    """passing: {ticker: screen_result}. Returns one row per stock, best first."""
    rows = []
    for t, res in passing.items():
        try:
            m = price_metrics(t)
        except Exception:
            continue
        m.update({"ticker": t, "company": res["fin"]["name"],
                  "headroom": headroom(res["verdict"], standard_rules)})
        rows.append(m)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    pct = lambda s, asc=True: s.rank(pct=True, ascending=asc) * 100
    df["s_momentum"] = pct(df["momentum_12_1"])
    df["s_low_risk"] = pct(df["volatility"], asc=False)
    df["s_drawdown"] = pct(df["max_drawdown_1y"])          # less negative = better
    df["s_headroom"] = pct(df["headroom"].fillna(0))
    df["score"] = sum(df[f"s_{k}"] * w for k, w in weights.items())
    n = len(df)
    df = df.sort_values("score", ascending=False).reset_index(drop=True)
    df["signal"] = ["Strong candidate" if i < max(1, n // 3) else "Watch" if i < max(2, 2 * n // 3) else "Lower priority"
                    for i in range(n)]
    # a stock about to breach a limit is never a strong candidate
    df.loc[df["headroom"] < 0.15, "signal"] = "Watch - near Shariah limit"
    return df


def reasons(row: pd.Series) -> str:
    bits = [f"12-1m momentum {row['momentum_12_1']:+.0%}",
            f"volatility {row['volatility']:.0%}",
            f"worst 1y fall {row['max_drawdown_1y']:.0%}",
            f"{row['headroom']:.0%} headroom below the nearest Shariah limit" if pd.notna(row["headroom"]) else "headroom unknown"]
    return "; ".join(bits)
