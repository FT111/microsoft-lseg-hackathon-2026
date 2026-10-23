"""Pre-load every ticker (SEC data, prices, 10-K text, AI business screen) into
data_cache/ so the app opens instantly and the demo works offline.
Usage:  python warm_cache.py            (all tickers)
        python warm_cache.py AAPL JPM   (just these)
        python warm_cache.py --committee MSFT JPM AAPL   (also run the agent committee)"""
import sys

from shariah import edgar, llm, prices, screen
from shariah.methodology import STANDARDS
from shariah.universe import UNIVERSE

args = sys.argv[1:]
committee = "--committee" in args
tickers = [a for a in args if not a.startswith("--")] or UNIVERSE
for t in tickers:
    try:
        prices.history(t)
        fin = edgar.financials(t)
        item1 = edgar.business_section(t)
        biz = llm.business_screen(fin["name"], item1["text"]) if (llm.available() and item1["text"]) else \
            screen.sic_rule(edgar.submissions(t)["sicDescription"])
        line = [f"{t:5}"]
        for std in STANDARDS:
            mcap = None
            if fin.get("shares_outstanding"):
                avg = prices.average_price(t)
                mcap = {"value": fin["shares_outstanding"] * avg["value"]}
            v = screen.verdict(fin, biz, std, mcap)
            line.append(f"{std}: {v['status']:12}")
        acts = [(a["category"], a["revenue_share_pct"], a["confidence"]) for a in biz.get("activities", [])]
        print(" ".join(line), acts, biz.get("error") or "", flush=True)
        if committee and llm.available():
            from shariah.agents import committee as c
            for std in STANDARDS:
                c.run_for_ticker(t, std)
            print(f"      committee cached", flush=True)
    except Exception as e:
        print(f"{t:5} ERROR {type(e).__name__}: {e}"[:200], flush=True)
