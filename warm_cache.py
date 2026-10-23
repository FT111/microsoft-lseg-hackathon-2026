"""Pre-load every ticker (SEC / Yahoo data, prices, 10-K text, AI business screen) into
data_cache/ so the app opens instantly and the demo works offline.
Usage:  python warm_cache.py                      (all US + UK tickers)
        python warm_cache.py AAPL TSCO.L          (just these)
        python warm_cache.py --committee MSFT     (also run the agent committee)"""
import sys

from shariah import pipeline
from shariah.methodology import STANDARDS
from shariah.universe import UK_UNIVERSE, UNIVERSE

args = sys.argv[1:]
committee = "--committee" in args
tickers = [a for a in args if not a.startswith("--")] or UNIVERSE + UK_UNIVERSE
for t in tickers:
    try:
        line = [f"{t:7}"]
        for std in STANDARDS:
            r = pipeline.screen_one(t, std)
            line.append(f"{std}: {r['verdict']['status']:12}")
        biz = r["business"]
        acts = [(a["category"], a["revenue_share_pct"], a["confidence"]) for a in biz.get("activities", [])]
        print(" ".join(line), r["source"], acts, biz.get("error") or "", flush=True)
        if committee:
            from shariah.agents import committee as c
            for std in STANDARDS:
                c.run_for_ticker(t, std)
            print("        committee cached", flush=True)
    except Exception as e:
        print(f"{t:7} ERROR {type(e).__name__}: {e}"[:200], flush=True)
