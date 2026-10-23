"""Quick check of the data pipeline without the UI:  python smoke_test.py
Uses real SEC / price data (cached in data_cache/). Unit tests: python -m unittest discover -s tests -t ."""
from shariah import pipeline, portfolio
from shariah.methodology import PASS, STANDARDS

passed = {}
for t in ["MSFT", "AAPL", "JPM", "MO", "LMT", "MRK"]:
    for std in STANDARDS:
        r = pipeline.screen_one(t, std)
        v = r["verdict"]
        print(f"{t:5} {std:12} {v['status']:13} {'; '.join(v['reasons'] + v['review'])[:120]}")
        if v["status"] == PASS and std == STANDARDS[0]:
            passed[t] = PASS
    print(f"      balance sheet {r['fin']['period_end']} · missing: {r['fin']['missing'] or 'none'}")

if passed:
    alloc = portfolio.build(list(passed), passed, 100_000)
    print(alloc)
    print(portfolio.stress_test(alloc))
