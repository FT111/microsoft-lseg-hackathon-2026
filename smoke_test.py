"""Quick check of the data pipeline without the UI:  python smoke_test.py"""
from shariah import edgar, prices, screen, portfolio

for t in ["AAPL", "JPM", "MO", "XOM", "LMT"]:
    fin = edgar.financials(t)
    sub = edgar.submissions(t)
    try:
        mcap = fin["shares_outstanding"] * prices.last_price(t)
    except Exception as e:
        mcap = None
        print("  price error", t, e)
    biz = screen.sic_rule(sub["sicDescription"])
    for std in screen.STANDARDS:
        v = screen.verdict(fin, mcap, biz, std)
        print(f"{t:5} {std[:6]:6} {v['status']:6} {'; '.join(v['reasons'] + v['review'])[:110]}")
    print(f"      sic={sub['sicDescription']!r} debt={fin['total_debt']:.3g} ({fin['sources']['total_debt']}) assets={fin['total_assets']}")

alloc = portfolio.build(["AAPL", "XOM"], 100_000)
print(alloc)
print(portfolio.stress_test(alloc))
