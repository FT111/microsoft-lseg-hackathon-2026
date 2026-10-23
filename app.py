"""Shariah AI analyst - Streamlit app.  Run:  streamlit run app.py
Educational hackathon project. Not financial advice. Not a fatwa."""
import json

import pandas as pd
import plotly.express as px
import streamlit as st

from shariah import edgar, llm, portfolio, prices, screen
from shariah.universe import SUKUK_ETF, UNIVERSE

st.set_page_config(page_title="Waqf Analyst", layout="wide")
st.markdown("""<style>
div[data-testid="stMetric"] {border:1px solid #24303d; border-radius:6px; padding:10px 14px;}
.block-container {padding-top:1.5rem;}
</style>""", unsafe_allow_html=True)

st.title("Waqf Analyst")
st.caption("AI-assisted Shariah screening and allocation for a mosque endowment · "
           "Educational hackathon project. Not financial advice. Not a fatwa.")

# ---------------- sidebar: the client ----------------
with st.sidebar:
    st.header("Client")
    amount = st.number_input("Endowment ($)", 10_000, 10_000_000, 100_000, step=10_000)
    standard = st.radio("Screening standard", list(screen.STANDARDS))
    payout = st.slider("Annual payout to scholarships", 0.02, 0.06, 0.04, 0.005, format="%.3f")
    cost = st.number_input("Cost of one scholarship ($)", 100, 10_000, 500, step=100)
    eq = st.slider("Shariah equities", 0.0, 1.0, 0.60, 0.05)
    sk = st.slider("Sukuk", 0.0, 1.0 - eq, min(0.30, 1.0 - eq), 0.05)
    use_llm = st.toggle("Use AI to read 10-Ks", value=llm.available(), disabled=not llm.available(),
                        help="Needs OPENAI_API_KEY in .env. Without it, a rule on the SEC industry code is used.")
    tickers = st.multiselect("Universe", UNIVERSE, default=UNIVERSE)


# ---------------- screening ----------------
@st.cache_data(show_spinner=False)
def screen_one(t: str, std: str, use_ai: bool):
    fin = edgar.financials(t)
    sub = edgar.submissions(t)
    try:
        mcap = (fin["shares_outstanding"] or 0) * prices.last_price(t)
    except Exception:
        mcap = None
    if use_ai:
        item1 = edgar.business_section(t)
        business = llm.business_screen(fin["name"], item1["text"]) if item1["text"] else screen.sic_rule(sub["sicDescription"])
        business["source_url"] = item1.get("url")
    else:
        business = screen.sic_rule(sub["sicDescription"])
        business["source_url"] = (sub.get("latest_10k") or {}).get("url")
    v = screen.verdict(fin, mcap, business, std)
    return {"fin": fin, "sic": sub["sicDescription"], "mcap": mcap, "business": business, "verdict": v}


tab_screen, tab_alloc, tab_stress, tab_ask = st.tabs(["1 · Screening", "2 · Allocation", "3 · Stress test & purification", "4 · Ask"])

results, errors = {}, []
with st.spinner("Screening..."):
    for t in tickers:
        try:
            results[t] = screen_one(t, standard, use_llm)
        except Exception as e:  # keep the demo alive; show what failed
            errors.append(f"{t}: {e}")

with tab_screen:
    rows = []
    for t, r in results.items():
        v, b = r["verdict"], r["business"]
        base = v["ratios"].get(screen.STANDARDS[standard]["denominator"], {})
        rows.append({"Ticker": t, "Company": r["fin"]["name"], "Verdict": v["status"],
                     "Debt": base.get("debt"), "Cash": base.get("cash"),
                     "Non-compliant income": v["noncompliant_income_pct"],
                     "Why": "; ".join(v["reasons"] + v["review"]) or "meets all screens",
                     "Evidence": b.get("evidence", ""), "Method": b.get("method")})
    df = pd.DataFrame(rows)
    c1, c2, c3 = st.columns(3)
    for col, s in zip((c1, c2, c3), ("PASS", "FAIL", "REVIEW")):
        col.metric(s.title(), int((df["Verdict"] == s).sum()) if not df.empty else 0)
    st.dataframe(df, use_container_width=True, hide_index=True, column_config={
        "Debt": st.column_config.NumberColumn(format="percent"),
        "Cash": st.column_config.NumberColumn(format="percent"),
        "Non-compliant income": st.column_config.NumberColumn(format="percent")})
    st.caption(f"Standard: {standard}. Ratios from SEC EDGAR XBRL (latest 10-K). REVIEW = not enough data to decide - "
               "we flag rather than guess.")
    if errors:
        with st.expander(f"{len(errors)} tickers could not be loaded"):
            st.write(errors)

passing = [t for t, r in results.items() if r["verdict"]["status"] == "PASS"]

with tab_alloc:
    if not passing:
        st.info("No stocks pass yet.")
    else:
        alloc = portfolio.build(passing, amount, eq, sk, SUKUK_ETF)
        st.session_state["alloc"] = alloc
        a, b, c = st.columns(3)
        a.metric("Holdings", len(alloc))
        b.metric("Annual payout", f"${amount * payout:,.0f}")
        c.metric("Scholarships / year", int(amount * payout // cost))
        st.plotly_chart(px.sunburst(alloc, path=["sleeve", "holding"], values="amount",
                                    template="plotly_dark"), use_container_width=True)
        st.dataframe(alloc, use_container_width=True, hide_index=True,
                     column_config={"weight": st.column_config.NumberColumn(format="percent"),
                                    "amount": st.column_config.NumberColumn(format="dollar")})
        st.caption("Equities: inverse-volatility weights (calmer stocks get more), max 10% of the fund each. "
                   "Deterministic maths - the AI does not choose the numbers.")

with tab_stress:
    alloc = st.session_state.get("alloc")
    if alloc is not None:
        stt = portfolio.stress_test(alloc, payout_rate=payout, scholarship_cost=cost, amount=amount)
        st.subheader("What a bad year means for scholarships")
        st.dataframe(stt, use_container_width=True, hide_index=True,
                     column_config={"portfolio_return": st.column_config.NumberColumn(format="percent"),
                                    "value_after": st.column_config.NumberColumn(format="dollar")})
        nc = {t: results[t]["verdict"]["noncompliant_income_pct"] for t in passing}
        pur = portfolio.purification(alloc, {t: results[t]["fin"] for t in passing}, nc)
        st.subheader("Purification - dividends to donate")
        if not pur.empty:
            st.metric("To donate this year", f"${pur['to_purify'].sum():,.2f}")
            st.dataframe(pur, use_container_width=True, hide_index=True)

with tab_ask:
    if not llm.available():
        st.info("Add OPENAI_API_KEY to .env to enable the AI coach.")
    else:
        context = {"client": {"type": "UK mosque waqf", "amount": amount, "payout": payout,
                              "scholarship_cost": cost, "standard": standard},
                   "screen": {t: {"status": r["verdict"]["status"], "reasons": r["verdict"]["reasons"],
                                  "review": r["verdict"]["review"], "evidence": r["business"].get("evidence")}
                              for t, r in results.items()},
                   "allocation": st.session_state["alloc"].to_dict("records")
                   if st.session_state.get("alloc") is not None else []}
        system = ("You explain an investment recommendation to the trustees of a mosque endowment. Answer ONLY from "
                  "the JSON context. If the answer is not in it, say so. Plain English, short. Not financial advice.\n"
                  + json.dumps(context, default=str))
        presets = ["Why was this split chosen?", "Which companies failed and why?",
                   "What happens to scholarships in a bad year?", "What would make you change this?"]
        cols = st.columns(len(presets))
        q = None
        for col, p in zip(cols, presets):
            if col.button(p):
                q = p
        q = st.chat_input("Ask about this recommendation") or q
        if q:
            st.chat_message("user").write(q)
            st.chat_message("assistant").write(llm.ask(system, q))
