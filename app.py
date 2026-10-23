"""Shariah AI analyst - Streamlit app.  Run:  streamlit run app.py
Educational hackathon project. Not financial advice. Not a fatwa."""
import html
import json

import pandas as pd
import plotly.express as px
import streamlit as st

from shariah import llm, pipeline, portfolio, signals
from shariah.agents import committee
from shariah.methodology import FAIL, METHODOLOGIES, NEEDS_REVIEW, PASS, STANDARDS
from shariah.universe import UNIVERSE

st.set_page_config(page_title="Halal Stock Analyst", page_icon="✦", layout="wide")

# Look and feel follows the team's "Amanat" mock: Alice-blue page, Baltic-blue accents,
# white rounded cards, DM Sans body + Space Grotesk headings.
BLUES = ["#05668d", "#427aa1", "#77a6c2", "#a8c9df", "#d2e4ef", "#0b3c5d", "#5c95b8", "#8fb8d2",
         "#034b68", "#9fc2d8", "#2f6f95", "#bcd6e6"]
SIGNAL_COLOURS = {"Strong candidate": "#05668d", "Watch": "#77a6c2", "Lower priority": "#a8c9df",
                  "Watch - near Shariah limit": "#c8553d"}
STATUS_LABEL = {PASS: "✅ PASS", FAIL: "❌ FAIL", NEEDS_REVIEW: "🔎 NEEDS REVIEW"}
STATUS_ICON = {PASS: "✅", FAIL: "❌", NEEDS_REVIEW: "🔎"}

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root {--baltic:#05668d; --cerulean:#427aa1; --alice:#ebf2fa; --ink:#123047; --muted:#6e8799;
       --line:rgba(5,102,141,.12); --pass:#2a9d8f; --fail:#c8553d; --review:#c9971c;}
html, body, [data-testid="stAppViewContainer"] {background:var(--alice); color:var(--ink); font-family:'DM Sans',sans-serif;}
[data-testid="stHeader"] {background:transparent;}
[data-testid="stDecoration"], footer {display:none;}
.block-container {padding-top:1rem; max-width:1240px;}
h1, h2, h3 {font-family:'Space Grotesk',sans-serif !important; letter-spacing:-.04em; color:var(--ink);}

[data-testid="stSidebar"] {background:#ffffff; border-right:1px solid var(--line);}
[data-testid="stSidebar"] h2 {font-size:1.15rem;}

.topbar {display:flex; align-items:center; justify-content:space-between; padding:.6rem 0 0;}
.brand {color:var(--baltic); font-family:'Space Grotesk',sans-serif; font-size:1.25rem; font-weight:700; letter-spacing:-.04em;}
.brand-mark {display:inline-grid; width:27px; height:27px; margin-right:.45rem; place-items:center; border-radius:9px;
             background:var(--baltic); color:var(--alice); font-size:.9rem;}
.topbar-note {color:var(--muted); font-size:.8rem;}
.hero {margin:1.8rem 0 1.8rem; animation:arrive .9s cubic-bezier(.22,1,.36,1) both;}
.eyebrow {color:var(--cerulean); font-size:.78rem; font-weight:700; letter-spacing:.16em; text-transform:uppercase;}
.hero h1 {max-width:760px; margin:.5rem 0 .7rem; font-size:clamp(2.2rem,4.4vw,3.9rem); letter-spacing:-.06em; line-height:1; padding:0;}
.hero p {max-width:620px; margin:0; color:var(--muted); font-size:1.03rem; line-height:1.6;}
@keyframes arrive {from {opacity:0; transform:translateY(18px);} to {opacity:1; transform:none;}}

.section-heading {display:flex; align-items:end; justify-content:space-between; margin:2rem 0 .8rem;}
.section-title {font-family:'Space Grotesk',sans-serif; font-size:1.4rem; font-weight:600; letter-spacing:-.04em; color:var(--ink);}
.section-heading span {color:var(--muted); font-size:.8rem;}

.stats {display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:1rem;}
@media (min-width:1100px) {.stats.five {grid-template-columns:repeat(5,1fr);}}
.card {padding:1.15rem 1.3rem; border:1px solid var(--line); border-radius:22px; background:rgba(255,255,255,.75);
       box-shadow:0 14px 35px rgba(35,72,99,.055);}
.label {color:var(--muted); font-size:.72rem; letter-spacing:.08em; text-transform:uppercase;}
.big {margin:.3rem 0 .15rem; font-family:'Space Grotesk',sans-serif; font-size:1.8rem; font-weight:600; letter-spacing:-.05em;}
.sub {color:var(--muted); font-size:.8rem; line-height:1.45;}
.good {color:var(--pass);} .bad {color:var(--fail);}

.row {display:grid; grid-template-columns:1fr auto; gap:.15rem 1rem; align-items:center; padding:.85rem 0; border-bottom:1px solid var(--line);}
.row:last-child {border-bottom:0;}
.name {font-size:.95rem; font-weight:700;}
.meta {color:var(--muted); font-size:.78rem;}
.score {color:var(--baltic); font-weight:700;}
.tag {display:inline-block; margin-top:.45rem; padding:.22rem .6rem; border-radius:999px; font-size:.7rem; font-weight:700;
      background:rgba(66,122,161,.12); color:var(--cerulean);}
.tag.warn {background:rgba(200,85,61,.12); color:var(--fail);}

/* Streamlit containers made with key="panel_*" render as cards */
[class*="st-key-panel"] {padding:1.2rem 1.3rem; border:1px solid var(--line); border-radius:22px; background:rgba(255,255,255,.75);
                         box-shadow:0 14px 35px rgba(35,72,99,.055);}

.stTabs [data-baseweb="tab-list"] {gap:.4rem; border-bottom:0;}
.stTabs [data-baseweb="tab"] {padding:.45rem 1rem; border-radius:999px !important; background:rgba(255,255,255,.7); border:1px solid var(--line);}
.stTabs button[role="tab"] {border-radius:999px !important; padding:.45rem 1rem !important;}
.stTabs [aria-selected="true"] {background:var(--baltic); color:#fff !important;}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {display:none;}

.stButton > button {border:1px solid rgba(5,102,141,.18); border-radius:999px; background:var(--cerulean); color:var(--alice) !important; font-weight:700;}
.stButton > button:hover {border-color:var(--baltic); background:var(--baltic);}
[data-testid="stDataFrame"] {border-radius:14px; overflow:hidden;}
.disclaimer {margin-top:2.5rem; color:var(--muted); font-size:.75rem; text-align:center;}
</style>""", unsafe_allow_html=True)


def card(label: str, value: str, sub: str = "", cls: str = "") -> str:
    return (f'<div class="card"><div class="label">{label}</div><div class="big {cls}">{value}</div>'
            f'<div class="sub">{sub}</div></div>')


def heading(title: str, note: str = "") -> None:
    st.markdown(f'<div class="section-heading"><div class="section-title">{title}</div><span>{note}</span></div>', unsafe_allow_html=True)


def styled(fig, height=340):
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="DM Sans, sans-serif", color="#123047"), height=height,
                      margin=dict(l=10, r=10, t=10, b=10), legend_title_text="")
    return fig


st.markdown("""<style>
.gate {padding:1rem 1.2rem; border-radius:18px; margin:.4rem 0 1rem; border:1px solid var(--line); background:#fff;}
.gate.PASS {border-left:6px solid var(--pass);} .gate.FAIL {border-left:6px solid var(--fail);}
.gate.NEEDS {border-left:6px solid var(--review);}
.gate .t {font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:1.1rem;}
.fact {display:inline-block; margin:.15rem .25rem 0 0; padding:.1rem .45rem; border-radius:8px; font-size:.7rem;
       background:rgba(66,122,161,.10); color:var(--cerulean);}
.removed {color:var(--muted); text-decoration:line-through; font-size:.85rem;}
</style>""", unsafe_allow_html=True)


def card(label: str, value: str, sub: str = "", cls: str = "") -> str:
    return (f'<div class="card"><div class="label">{label}</div><div class="big {cls}">{value}</div>'
            f'<div class="sub">{sub}</div></div>')


def heading(title: str, note: str = "") -> None:
    st.markdown(f'<div class="section-heading"><div class="section-title">{title}</div><span>{note}</span></div>', unsafe_allow_html=True)


def styled(fig, height=340):
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="DM Sans, sans-serif", color="#123047"), height=height,
                      margin=dict(l=10, r=10, t=10, b=10), legend_title_text="")
    return fig


def pct(v):
    return "-" if v is None else f"{v:.1%}"


# ---------------- sidebar: the client ----------------
with st.sidebar:
    st.markdown('<div class="brand"><span class="brand-mark">✦</span>Your plan</div>', unsafe_allow_html=True)
    st.caption("Tell us about you - everything on the page updates as you change these.")
    amount = st.number_input("How much are you investing? ($)", 1_000, 10_000_000, 100_000, step=5_000)
    risk = st.radio("How much ups and downs can you live with?", list(signals.PROFILES), index=1, horizontal=True,
                    help="Cautious favours steadier stocks; Adventurous favours stronger recent momentum.")
    top_n = st.slider("How many stocks to hold", 3, 20, 10)
    standard = st.radio("Shariah screening standard", STANDARDS, index=0,
                        help="Each standard is applied on its own - their rules are never mixed. FTSE Yasaar measures "
                             "ratios against total assets; AAOIFI against 12-month average market value.")
    with st.expander("More options"):
        eq = st.slider("Share in Shariah-screened stocks", 0.5, 1.0, 1.0, 0.05,
                       help="The rest is held as non-interest-bearing cash.")
        use_llm = st.toggle("Use AI to read annual reports (10-Ks)", value=llm.available(), disabled=not llm.available(),
                            help="Needs OPENAI_API_KEY in .env. Without it, only the SEC industry code is checked and "
                                 "most companies go to NEEDS REVIEW.")
        tickers = st.multiselect("Stocks to consider", UNIVERSE, default=UNIVERSE)


# ---------------- screening ----------------
@st.cache_data(show_spinner=False)
def screen_one(t: str, std: str, use_ai: bool):
    return pipeline.screen_one(t, std, use_ai)


@st.cache_data(show_spinner=False)
def metrics_for(t: str):
    return signals.price_metrics(t)


results, errors = {}, []
with st.spinner("Checking companies against the Shariah screens..."):
    for t in tickers:
        try:
            results[t] = screen_one(t, standard, use_llm)
        except Exception as e:  # keep the demo alive; show what failed
            errors.append(f"{t}: {type(e).__name__}: {e}")

statuses = {t: r["verdict"]["status"] for t, r in results.items()}
counts = {s: sum(v == s for v in statuses.values()) for s in STATUS_LABEL}
passing = [t for t, s in statuses.items() if s == PASS]
ranking = signals.rank({t: results[t] for t in passing}, signals.PROFILES[risk]) if passing else pd.DataFrame()
picks = [] if ranking.empty else ranking[~ranking["signal"].str.startswith("Watch - near")]["ticker"].head(top_n).tolist()
holdings = picks or ([] if ranking.empty else ranking["ticker"].head(top_n).tolist())

alloc = stt = pur = None
if holdings:
    try:
        alloc = portfolio.build(holdings, statuses, amount, eq)
        stt = portfolio.stress_test(alloc, amount=amount)
        nc = {t: results[t]["verdict"]["noncompliant_income_pct"] for t in holdings}
        pur = portfolio.purification(alloc, {t: results[t]["fin"] for t in holdings}, nc, standard)
    except portfolio.NotCompliantError as e:
        errors.append(str(e))
        alloc = None
    except Exception as e:
        errors.append(f"portfolio: {e}")

meth = METHODOLOGIES[standard]

# ---------------- header + "your plan" summary ----------------
st.markdown(f"""
<div class="topbar"><div class="brand"><span class="brand-mark">✦</span>Halal Stock Analyst</div>
<div class="topbar-note">Educational project · Not financial advice · Not a fatwa</div></div>
<div class="hero"><div class="eyebrow">Your plan, screened for Shariah</div>
<h1>Shariah screening, explained.</h1>
<p>We check {len(results)} US companies against the <b>{html.escape(meth['name'])}</b> rules, rank only the ones that
pass every screen for a <b>{risk.lower()}</b> investor, and show what that means for your ${amount:,.0f} - with the
evidence behind every result.</p></div>
""", unsafe_allow_html=True)

heading("Your plan at a glance", f"{standard} · {risk} profile")
worst_year = stt.loc[stt["portfolio_return"].idxmin()] if stt is not None and not stt.empty else None
to_purify = pur["to_purify"].dropna().sum() if pur is not None and not pur.empty else 0.0
unknown_purify = int(pur["to_purify"].isna().sum()) if pur is not None and not pur.empty else 0
cards = [
    card("Invested", f"${amount:,.0f}", f"{eq:.0%} Shariah-screened stocks" + (f" · {1 - eq:.0%} non-interest cash" if eq < 1 else "")),
    card("Pass every screen", f"{counts[PASS]} of {len(results)}",
         f"{counts[FAIL]} fail · {counts[NEEDS_REVIEW]} need a person to check"),
    card("Stocks in your plan", str(len(holdings)), "Only PASS stocks · max 10% in any one"),
    card(f"In a bad year ({int(worst_year['year'])})" if worst_year is not None else "In a bad year",
         f"${worst_year['value_after']:,.0f}" if worst_year is not None else "-",
         f"{worst_year['gain_or_loss']:+,.0f} vs today" if worst_year is not None else "Not enough price history",
         "bad" if worst_year is not None and worst_year["gain_or_loss"] < 0 else ""),
    card("Give to charity this year", f"${to_purify:,.2f}",
         "Purification" + (f" · {unknown_purify} holding(s) unknown" if unknown_purify else "")),
]
st.markdown(f'<div class="stats five">{"".join(cards)}</div>', unsafe_allow_html=True)

if alloc is not None:
    heading("Where your money goes", "Calmer stocks get more")
    left, right = st.columns([1, 1.2], gap="large")
    with left, st.container(key="panel_donut"):
        st.markdown(f'<div class="label">Portfolio value</div><div class="big">${amount:,.0f}</div>', unsafe_allow_html=True)
        names = {r["ticker"]: r["company"] for _, r in ranking.iterrows()} if not ranking.empty else {}
        donut = alloc.assign(label=alloc["holding"].map(lambda h: names.get(h, h)))
        fig = px.pie(donut, names="label", values="amount", hole=.62, color_discrete_sequence=BLUES)
        fig.update_traces(textinfo="none", hovertemplate="%{label}<br>$%{value:,.0f} (%{percent})<extra></extra>")
        fig.update_layout(legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center", yanchor="top"))
        st.plotly_chart(styled(fig, 460), width="stretch")
    with right, st.container(key="panel_top"):
        st.markdown(f'<div class="label">Top picks for a {risk.lower()} investor</div>', unsafe_allow_html=True)
        rows = []
        for _, r in ranking.head(5).iterrows():
            share = alloc.set_index("holding")["amount"].get(r["ticker"])
            rows.append(f'<div class="row"><div><div class="name">{html.escape(r["company"])}</div>'
                        f'<div class="meta">{r["ticker"]} · {r["return_1y"]:+.0%} over the past year'
                        + (f" · ${share:,.0f} in your plan" if share else "") + '</div>'
                        f'<span class="tag{" warn" if r["signal"].startswith("Watch - near") else ""}">{r["signal"]}</span></div>'
                        f'<div class="score">{r["score"]:.0f}/100</div></div>')
        st.markdown("".join(rows) or '<div class="sub">No compliant stocks to rank yet.</div>', unsafe_allow_html=True)
elif not passing:
    st.info("No company passes every screen of this standard, so there is nothing to invest in yet.")

# ---------------- details ----------------
heading("Explore the details", "Every number can be traced to its source")
tab_screen, tab_committee, tab_picks, tab_alloc, tab_stress, tab_ask, tab_method = st.tabs(
    ["Shariah check", "Investment committee", "Stock picks", "Your portfolio", "Bad years & charity",
     "Ask the analyst", "Methodology"])


def screen_cell(v, key):
    s = next((x for x in v["screens"] if x["key"] == key), None)
    if s is None:
        return "n/a"
    return f"{STATUS_ICON[s['status']]} {pct(s['value'])}"


with tab_screen:
    rows = []
    for t, r in results.items():
        v, b = r["verdict"], r["business"]
        row = {"Ticker": t, "Company": r["fin"]["name"], "Result": STATUS_LABEL[v["status"]],
               "Activities": screen_cell(v, "activity")}
        for rule in meth["ratios"]:
            row[rule["label"]] = screen_cell(v, rule["key"])
        row["Interest + non-compliant income"] = screen_cell(v, "noncompliant_income")
        row["Why"] = "; ".join(v["reasons"] + v["review"]) or "meets every screen"
        row["Evidence (10-K quote)"] = b.get("evidence", "")
        row["Checked by"] = b.get("method")
        row["Balance sheet date"] = v.get("period_end")
        rows.append(row)
    df = pd.DataFrame(rows)
    show = st.segmented_control("Show", ["All"] + list(STATUS_LABEL.values()), default="All", key="screen_filter")
    if show and show != "All" and not df.empty:
        df = df[df["Result"] == show]
    st.dataframe(df, width="stretch", hide_index=True)
    st.caption(f"Standard: {meth['source']}. Ratios from SEC EDGAR XBRL, all from one balance-sheet date. "
               "NEEDS REVIEW means a rule could not be checked with the data available - we flag it rather than guess.")

    if results:
        with st.container(key="panel_company"):
            st.subheader("Company detail")
            pick = st.selectbox("Company", list(results), key="detail_pick",
                                format_func=lambda t: f"{t} · {results[t]['fin']['name']} · {statuses[t]}")
            r = results[pick]
            v, b, fin = r["verdict"], r["business"], r["fin"]
            det = pd.DataFrame([{"Screen": s["label"], "Rule": f"{s['clause']}: {s['rule_text']}",
                                 "Value": pct(s["value"]), "Limit": f"{s['op']} {s['limit']:.3%}" if s["limit"] else "-",
                                 "Status": STATUS_LABEL[s["status"]], "Note": s["note"]} for s in v["screens"]])
            st.dataframe(det, width="stretch", hide_index=True)
            items = fin.get("items") or {}
            inputs = pd.DataFrame([{"Item": k.replace("_", " "), "Value": (f"${it['value'] / 1e9:,.2f}bn" if it and k !=
                                    "shares_outstanding" else f"{it['value'] / 1e9:,.3f}bn shares" if it else "not reported"),
                                    "SEC XBRL concept": it["concept"] if it else "-",
                                    "Period": (f"{it.get('period_start', '')} to {it['period_end']}" if it and it.get("period_start")
                                               else (it or {}).get("period_end", "-"))} for k, it in items.items()])
            st.dataframe(inputs, width="stretch", hide_index=True)
            if r.get("mcap"):
                st.caption("Market value (AAOIFI): " + r["mcap"]["note"])
            for note in fin.get("notes", []):
                st.caption("Note: " + note)
            for a in b.get("activities", []):
                ok = "verified in the filing" if a.get("quote_verified") else "NOT found in the filing - ignored as evidence"
                share = (f"~{a['revenue_share_pct']:.0f}%" if a.get("revenue_share_pct") is not None else "share unknown")
                st.markdown(f"**{a['category'].replace('_', ' ')}** ({share}, {a.get('confidence')} confidence, quote {ok}): "
                            f"“{html.escape(a.get('evidence', ''))}”")
            if b.get("source_url"):
                st.markdown(f"Source: [10-K filed {b.get('filing_date')}]({b['source_url']}) · "
                            f"[SEC XBRL data](https://data.sec.gov/api/xbrl/companyfacts/CIK{fin['cik']}.json)")
    if errors:
        with st.expander(f"{len(errors)} items could not be loaded"):
            st.write(errors)


def show_points(case, title):
    st.markdown(f"**{title}**")
    if not case or not case.get("available"):
        st.caption("This agent was unavailable.")
        return
    if case.get("thesis"):
        st.markdown(case["thesis"])
    for p in case.get("points", []):
        chips = "".join(f'<span class="fact" title="{html.escape(str(facts.get(i, {}).get("source", "")))}">'
                        f'{i}: {html.escape(facts.get(i, {}).get("label", "")[:40])} = '
                        f'{html.escape(str(facts.get(i, {}).get("display", ""))[:40])}</span>' for i in p["facts"])
        st.markdown(f"- {html.escape(p['claim'])}<br>{chips}", unsafe_allow_html=True)
    if case.get("change"):
        st.caption("What would change this view: " + case["change"])


with tab_committee:
    st.caption("Four agents, in order of priority: the **Shariah Compliance Checker** decides first and audits last; "
               "the Bull and Bear analysts argue independently; the Risk reviewer weighs both. Only the Shariah "
               "Checker can affect whether a stock is held - and only by excluding it.")
    if not results:
        st.info("Screen some companies first.")
    elif not llm.available():
        st.info("Add OPENAI_API_KEY to .env to run the committee. The Shariah gate below still works without it.")
    if results:
        order = sorted(results, key=lambda t: (statuses[t] != PASS, t))
        cpick = st.selectbox("Company", order, key="committee_pick",
                             format_func=lambda t: f"{t} · {results[t]['fin']['name']} · {statuses[t]}")
        r = results[cpick]
        from shariah.agents import shariah_checker
        g = shariah_checker.gate(r)
        cls = "NEEDS" if g["status"] == NEEDS_REVIEW else g["status"]
        items_html = "".join(f"<li>{html.escape(x)}</li>" for x in g["reasons"] + g["review"])
        st.markdown(f'<div class="gate {cls}"><div class="label">1 · Shariah Compliance Checker - gate</div>'
                    f'<div class="t">{STATUS_LABEL[g["status"]]} under {html.escape(g["standard"])}</div>'
                    f'<div class="sub">{html.escape(g["banner"])}</div><ul class="sub">{items_html}</ul></div>',
                    unsafe_allow_html=True)
        if g["status"] == FAIL:
            st.markdown("The committee does not meet for excluded companies.")
        elif llm.available() and st.button(f"Convene the committee for {cpick}"):
            pos = alloc.set_index("holding").loc[cpick].to_dict() if alloc is not None and cpick in set(alloc["holding"]) else None
            rr = ranking.set_index("ticker").loc[cpick].to_dict() if not ranking.empty and cpick in set(ranking["ticker"]) else None
            try:
                m = metrics_for(cpick)
            except Exception:
                m = None
            with st.spinner("Bull and Bear are arguing, the Risk reviewer is weighing up, the Shariah Checker is auditing..."):
                st.session_state[f"committee_{cpick}_{standard}"] = committee.run(
                    r, m, rr, pos, stt.to_dict("records") if stt is not None else None)
        res = st.session_state.get(f"committee_{cpick}_{standard}")
        if res and res.get("ran"):
            facts = res["facts"]
            c1, c2 = st.columns(2, gap="large")
            with c1, st.container(key="panel_bull"):
                show_points(res["bull"], "2 · Bull analyst - the case for")
            with c2, st.container(key="panel_bear"):
                show_points(res["bear"], "3 · Bear analyst - the case against")
            rk = res["risk"]
            with st.container(key="panel_risk"):
                st.markdown("**4 · Risk reviewer**" + (f" · flag: `{rk['flag']}`" if rk.get("flag") else ""))
                if not rk.get("available"):
                    st.caption("The risk reviewer was unavailable.")
                else:
                    if rk.get("summary"):
                        st.markdown(rk["summary"])
                    for p in rk["key_risks"]:
                        st.markdown(f"- {html.escape(p['claim'])} ({', '.join(p['facts'])})")
                    if rk.get("stronger_case"):
                        st.caption(f"Stronger case on the evidence: {rk['stronger_case']}")
                    if rk.get("unsupported_claims"):
                        st.caption("Claims the reviewer found unsupported: " + "; ".join(rk["unsupported_claims"]))
            a = res["audit"]
            if a["approved"]:
                st.success("1 · Shariah Compliance Checker - audit: every statement approved.")
            elif not a["llm_checked"]:
                st.warning("1 · Shariah Compliance Checker - audit: rule checks ran, but the AI audit was unavailable. "
                           "Treat the statements above with care.")
            if a["removed"]:
                st.warning(f"1 · Shariah Compliance Checker - audit removed {len(a['removed'])} statement(s):")
                for sid, why in a["removed"].items():
                    st.markdown(f'<div class="removed">{html.escape(a["removed_text"].get(sid, ""))}</div>'
                                f'<div class="sub">{html.escape("; ".join(why))}</div>', unsafe_allow_html=True)
            dropped = (res["bull"]["dropped"] + res["bear"]["dropped"] + res["risk"]["dropped"])
            if dropped:
                with st.expander(f"{len(dropped)} claim(s) removed by the evidence check (no valid source or invented numbers)"):
                    for d in dropped:
                        st.markdown(f"- {html.escape(d['text'])} - _{html.escape(d['why'])}_")
            with st.expander("Evidence pack the agents were given"):
                st.dataframe(pd.DataFrame([{"ID": k, **{c: f[c] for c in ("label", "display", "source", "period")}}
                                           for k, f in facts.items()]), width="stretch", hide_index=True)
            st.caption(res["disclaimer"])

with tab_picks:
    if ranking.empty:
        st.info("No stock passes every screen of this standard, so there is nothing to rank.")
    else:
        st.plotly_chart(styled(px.bar(ranking, x="ticker", y="score", color="signal",
                                      color_discrete_map=SIGNAL_COLOURS,
                                      labels={"ticker": "", "score": "Score (0-100)"})), width="stretch")
        show = ranking[["ticker", "company", "signal", "score", "price", "return_1y", "momentum_12_1",
                        "volatility", "max_drawdown_1y", "headroom"]]
        st.dataframe(show, width="stretch", hide_index=True, column_config={
            "ticker": "Ticker", "company": "Company", "signal": "Signal",
            "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.0f"),
            "price": st.column_config.NumberColumn("Price", format="dollar"),
            "return_1y": st.column_config.NumberColumn("1-year return", format="percent"),
            "momentum_12_1": st.column_config.NumberColumn("Momentum", format="percent"),
            "volatility": st.column_config.NumberColumn("Volatility", format="percent"),
            "max_drawdown_1y": st.column_config.NumberColumn("Worst fall (1y)", format="percent"),
            "headroom": st.column_config.NumberColumn("Room below Shariah limit", format="percent")})
        st.caption("Only stocks that PASS every screen are ranked. Score = momentum + steadiness + smaller falls + room "
                   "below the Shariah limits, weighted for your risk appetite. A stock close to a limit may have to be "
                   "sold if it breaches it. This ranks candidates; it does not predict prices.")

with tab_alloc:
    if alloc is None:
        st.info("No stocks pass every screen yet.")
    else:
        st.plotly_chart(styled(px.sunburst(alloc, path=["sleeve", "holding"], values="amount",
                                           color_discrete_sequence=BLUES), 420), width="stretch")
        st.dataframe(alloc, width="stretch", hide_index=True, column_order=["holding", "sleeve", "weight", "amount"],
                     column_config={"holding": "Holding", "sleeve": "Type",
                                    "weight": st.column_config.NumberColumn("Share", format="percent"),
                                    "amount": st.column_config.NumberColumn("Amount", format="dollar")})
        st.caption("Every holding passed every screen of the selected standard - the portfolio code refuses anything "
                   "else. Inverse-volatility weights (calmer stocks get more), max 10% each. Any remainder is "
                   "non-interest-bearing cash. Deterministic maths - the AI does not choose the numbers.")

with tab_stress:
    if stt is None:
        st.info("Build a portfolio first.")
    else:
        st.subheader(f"What past years would have done to your ${amount:,.0f}")
        year_cards = [card(str(int(y["year"])), f"${y['value_after']:,.0f}",
                           f"{y['gain_or_loss']:+,.0f} ({y['portfolio_return']:+.0%})"
                           + (f"<br>No data for {html.escape(y['no_data_for'])}" if y["no_data_for"] else ""),
                           "good" if y["gain_or_loss"] >= 0 else "bad") for _, y in stt.iterrows()]
        st.markdown(f'<div class="stats">{"".join(year_cards)}</div>', unsafe_allow_html=True)
        st.caption("2008: financial crisis · 2020: Covid crash and recovery · 2022: rate-rise sell-off. "
                   "Holdings that didn't exist yet count as 0%.")
        st.subheader("Purification - the share to give to charity")
        st.caption(f"{standard} method ({meth['purification']['clause']}): {meth['purification']['text']}")
        if pur is not None and not pur.empty:
            st.dataframe(pur, width="stretch", hide_index=True, column_config={
                "holding": "Holding",
                "dividend_yield": st.column_config.NumberColumn("Dividend yield", format="percent"),
                "dividend_received": st.column_config.NumberColumn("Dividends you'd receive", format="dollar"),
                "noncompliant_share": st.column_config.NumberColumn("Non-compliant income", format="percent"),
                "to_purify": st.column_config.NumberColumn("To donate", format="dollar"), "method": "How"})
            if unknown_purify:
                st.caption("Blank 'To donate' means the non-compliant income share is unknown - it is not guessed.")
        else:
            st.info("Nothing to purify.")

with tab_ask:
    if not llm.available():
        st.info("Add OPENAI_API_KEY to .env to enable the AI coach.")
    else:
        context = {"investor": {"type": "individual Muslim investor", "amount": amount, "risk_appetite": risk,
                                "standard": standard},
                   "screen": {t: {"status": r["verdict"]["status"], "reasons": r["verdict"]["reasons"],
                                  "needs_review": r["verdict"]["review"], "evidence": r["business"].get("evidence")}
                              for t, r in results.items()},
                   "stock_ranking": ranking.drop(columns=[c for c in ranking.columns if c.startswith("s_")]).to_dict("records") if not ranking.empty else [],
                   "allocation": alloc.to_dict("records") if alloc is not None else []}
        system = ("You explain a Shariah-screened stock recommendation to an everyday Muslim investor. Answer ONLY from "
                  "the JSON context. If the answer is not in it, say so. Plain English, short. Never call a company "
                  "halal or haram - passing screens is not a religious ruling. Not financial advice.\n"
                  + json.dumps(context, default=str))
        presets = ["Which stocks look strongest and why?", "Why was this split chosen?", "Which companies failed and why?",
                   "What would a bad year do to my money?", "What would make you change this?"]
        st.caption("Try a question, or type your own below. Answers come only from the results on this page.")
        cols = st.columns(len(presets))
        q = None
        for col, p in zip(cols, presets):
            if col.button(p, width="stretch"):
                q = p
        q = st.chat_input("Ask about this recommendation") or q
        if q:
            st.chat_message("user").write(q)
            with st.spinner("Thinking..."):
                st.chat_message("assistant").write(llm.ask(system, q))

with tab_method:
    st.subheader(meth["name"])
    st.markdown(f"Source: [{meth['source']}]({meth['url']}) · checked {meth['verified_on']}")
    st.caption(meth["verification_note"])
    act = meth["activity"]
    st.markdown(f"**Business activities ({act['clause']})** - {act['text']} (limit {act['op']} {act['limit']:.0%}):")
    st.markdown("\n".join(f"- {g}" for g in act["groups"]))
    st.markdown("**Financial ratios**")
    st.dataframe(pd.DataFrame([{"Clause": r["clause"], "Screen": r["label"], "Rule (quoted)": r["text"],
                                "Pass if": f"value {r['op']} {r['limit']:.3%}"} for r in meth["ratios"]]
                              + [{"Clause": meth["income"]["clause"], "Screen": "Interest + non-compliant income",
                                  "Rule (quoted)": meth["income"]["text"],
                                  "Pass if": f"value {meth['income']['op']} {meth['income']['limit']:.0%}"}]),
                 width="stretch", hide_index=True)
    st.markdown("**How the app applies it - and its limits**")
    st.markdown("""
- Each standard is applied on its own; their rules are never combined.
- Ratios are calculated in Python from SEC EDGAR XBRL data. All balance-sheet items come from one reporting date.
- "Cash and interest-bearing items" = cash + short-term investments. Long-term interest-bearing securities are
  shown separately; if including them breaks a limit, the screen is NEEDS REVIEW.
- Interest income counts towards the non-compliant income limit. If a company doesn't tag interest income in its
  SEC data, that screen is NEEDS REVIEW.
- Any required figure that is missing gives NEEDS REVIEW - never a 0 or a guess.
- Business activities are read by AI from the latest 10-K (Item 1 plus every sentence in the filing that mentions a
  screened activity). Every quote is checked word-for-word against the filing; unmatched quotes are ignored.
- FTSE's quarter-on-quarter monitoring band (31.667%-35%) needs past quarters, which the app does not check:
  passing values inside the band go to NEEDS REVIEW.
- AAOIFI market value = 12-month average adjusted share price x shares outstanding.
- Passing these screens is not a religious ruling or a guarantee of compliance.
""")

st.markdown('<div class="disclaimer">Educational hackathon project (Microsoft × LSEG 2026). Not financial advice. '
            'Not a fatwa - this is the evidence a Shariah scholar would review, not a ruling.</div>', unsafe_allow_html=True)
