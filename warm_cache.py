"""Pre-load every ticker (SEC data, prices, 10-K text, AI business screen) into
data_cache/ so the app opens instantly and the demo works offline.
Usage:  python warm_cache.py            (all tickers)
        python warm_cache.py AAPL JPM   (just these)"""
import sys

from shariah import edgar, llm, prices, screen
from shariah.universe import SUKUK_ETF, UNIVERSE

tickers = sys.argv[1:] or UNIVERSE
for t in tickers + ([SUKUK_ETF] if not sys.argv[1:] else []):
    try:
        prices.history(t)
        if t == SUKUK_ETF:
            print(f"{t:5} prices ok"); continue
        fin = edgar.financials(t)
        item1 = edgar.business_section(t)
        biz = llm.business_screen(fin["name"], item1["text"]) if (llm.available() and item1["text"]) else {}
        print(f"{t:5} item1={len(item1['text']):>6} chars  AI: {biz.get('noncompliant_pct')}% "
              f"{biz.get('categories')} [{biz.get('confidence')}] {str(biz.get('evidence'))[:70]!r}")
    except Exception as e:
        print(f"{t:5} ERROR {type(e).__name__}: {e}"[:200])
