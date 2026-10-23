"""AMANAT - Shariah stock screening for everyday Muslim investors.  Run:  streamlit run app.py
Two pages: check any listed company (UK first), or build a screened portfolio.
Educational hackathon project. Not financial advice. Not a fatwa."""
import html
import json

import pandas as pd
import plotly.express as px
import streamlit as st

from shariah import llm, pipeline, portfolio, prices, signals, yahoo
from shariah.agents import committee, shariah_checker
from shariah.methodology import FAIL, METHODOLOGIES, NEEDS_REVIEW, PASS, STANDARDS
from shariah.universe import UK_UNIVERSE, UNIVERSE

st.set_page_config(page_title="AMANAT · Halal investing", page_icon="☾", layout="wide")

# Look and feel follows the team's "Amanat" mock: Alice-blue page, Baltic-blue accents,
# white rounded cards, DM Sans body + Space Grotesk headings.
BLUES = ["#05668d", "#427aa1", "#77a6c2", "#a8c9df", "#d2e4ef", "#0b3c5d", "#5c95b8", "#8fb8d2",
         "#034b68", "#9fc2d8", "#2f6f95", "#bcd6e6"]
SIGNAL_COLOURS = {"Strong candidate": "#05668d", "Watch": "#77a6c2", "Lower priority": "#a8c9df",
                  "Watch - near Shariah limit": "#c8553d"}
STATUS_LABEL = {PASS: "✅ Pass", FAIL: "❌ Fail", NEEDS_REVIEW: "🔎 Needs review"}
STATUS_CLASS = {PASS: "pass", FAIL: "fail", NEEDS_REVIEW: "review"}
STATUS_ICON = {PASS: "✅", FAIL: "❌", NEEDS_REVIEW: "🔎"}
MARKETS = {"UK · London Stock Exchange": {"cur": "£", "universe": UK_UNIVERSE, "label": "UK (FTSE 100)"},
           "US · New York": {"cur": "$", "universe": UNIVERSE, "label": "US"}}
POPULAR = {"UK · London Stock Exchange": ["Tesco", "AstraZeneca", "Unilever", "HSBC", "Diageo", "BP", "Rightmove"],
           "US · New York": ["Apple", "Microsoft", "Nvidia", "JPMorgan", "Coca-Cola", "Tesla"]}

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
.brand-mark {position:relative; display:inline-block; width:27px; height:27px; margin-right:.45rem; vertical-align:middle;
              background:var(--baltic); clip-path:polygon(50% 0,91% 14%,86% 66%,71% 86%,50% 100%,29% 86%,14% 66%,9% 14%);}
.brand-mark::before {content:""; position:absolute; top:6px; left:6px; width:14px; height:14px; border-radius:50%; background:var(--alice);}
.brand-mark::after {content:""; position:absolute; top:4px; left:11px; width:14px; height:14px; border-radius:50%; background:var(--baltic);}
.brand.word {letter-spacing:.08em;}
.topbar-note {color:var(--muted); font-size:.8rem;}
.hero {margin:1.6rem 0 1.4rem; animation:arrive .9s cubic-bezier(.22,1,.36,1) both;}
.eyebrow {color:var(--cerulean); font-size:.78rem; font-weight:700; letter-spacing:.16em; text-transform:uppercase;}
.hero h1 {max-width:760px; margin:.5rem 0 .7rem; font-size:clamp(2.2rem,4.4vw,3.9rem); letter-spacing:-.06em; line-height:1; padding:0;}
.hero p {max-width:640px; margin:0; color:var(--muted); font-size:1.03rem; line-height:1.6;}
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
.good {color:var(--pass);} .bad {color:var(--fail);} .warn-text {color:#9a7210;}

.row {display:grid; grid-template-columns:1fr auto; gap:.15rem 1rem; align-items:center; padding:.85rem 0; border-bottom:1px solid var(--line);}
.row:last-child {border-bottom:0;}
.name {font-size:.95rem; font-weight:700;}
.meta {color:var(--muted); font-size:.78rem;}
.score {color:var(--baltic); font-weight:700;}
.tag {display:inline-block; margin-top:.45rem; padding:.22rem .6rem; border-radius:999px; font-size:.7rem; font-weight:700;
      background:rgba(66,122,161,.12); color:var(--cerulean);}
.tag.warn {background:rgba(200,85,61,.12); color:var(--fail);}

/* company report */
.report-head {display:flex; justify-content:space-between; align-items:flex-start; gap:1.5rem; flex-wrap:wrap;}
.report-name {font-family:'Space Grotesk',sans-serif; font-size:2rem; font-weight:600; letter-spacing:-.05em; line-height:1.1;}
.verdict {padding:.55rem 1.1rem; border-radius:999px; font-weight:700; font-size:1rem; white-space:nowrap;}
.verdict.pass {background:rgba(42,157,143,.14); color:var(--pass);}
.verdict.fail {background:rgba(200,85,61,.13); color:var(--fail);}
.verdict.review {background:rgba(201,151,28,.15); color:#9a7210;}
.why {margin-top:1rem; font-size:1rem; line-height:1.55;}
.ratio {padding:.75rem 0; border-bottom:1px solid var(--line);}
.ratio:last-child {border-bottom:0;}
.ratio-top {display:flex; justify-content:space-between; gap:1rem; font-size:.9rem;}
.ratio-top b {font-weight:700;}
.bar {position:relative; height:9px; margin:.45rem 0 .3rem; border-radius:999px; background:rgba(5,102,141,.09); overflow:hidden;}
.fill {height:100%; border-radius:999px; background:var(--pass);}
.fill.over {background:var(--fail);} .fill.review {background:var(--review);}
.quote {margin:.6rem 0; padding:.6rem .9rem; border-left:3px solid var(--cerulean); background:rgba(66,122,161,.06); border-radius:0 12px 12px 0;}
.limits li {margin:.25rem 0; color:var(--muted); font-size:.85rem;}

/* committee */
.gate {padding:1rem 1.2rem; border-radius:18px; margin:.4rem 0 1rem; border:1px solid var(--line); background:#fff;}
.gate.pass {border-left:6px solid var(--pass);} .gate.fail {border-left:6px solid var(--fail);} .gate.review {border-left:6px solid var(--review);}
.gate .t {font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:1.1rem;}
.fact {display:inline-block; margin:.15rem .25rem 0 0; padding:.1rem .45rem; border-radius:8px; font-size:.7rem;
       background:rgba(66,122,161,.10); color:var(--cerulean);}
.removed {color:var(--muted); text-decoration:line-through; font-size:.85rem;}
.agent-title {font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:1.05rem; margin-bottom:.3rem;}

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


def big_money(cur: str, x: float) -> str:
    for div, suffix in ((1e12, "tn"), (1e9, "bn"), (1e6, "m")):
        if abs(x) >= div:
            return f"{cur}{x / div:,.1f}{suffix}"
    return f"{cur}{x:,.0f}"


def pct(v) -> str:
    return "-" if v is None else f"{v:.1%}"


def nice(category: str) -> str:
    return category.replace("_", " ")


# ---------------- sidebar: the client ----------------
with st.sidebar:
    st.markdown('<div class="brand"><span class="brand-mark" aria-hidden="true"></span>Your plan</div>', unsafe_allow_html=True)
    st.caption("Tell us about you - everything on the page updates as you change these.")
    market = st.radio("Market", list(MARKETS), help="Search covers any listed company; this sets the "
                      "portfolio's stock list and currency.")
    C = MARKETS[market]["cur"]
    amount = st.number_input(f"How much are you investing? ({C})", 1_000, 10_000_000, 100_000, step=5_000)
    risk = st.radio("How much ups and downs can you live with?", list(signals.PROFILES), index=1, horizontal=True,
                    help="Cautious favours steadier stocks; Adventurous favours stronger recent momentum.")
    top_n = st.slider("How many stocks to hold", 3, 20, 10)
    standard = st.radio("Shariah screening standard", STANDARDS, index=0,
                        help="Each standard is applied on its own - their rules are never mixed. FTSE Yasaar measures "
                             "ratios against total assets; AAOIFI against 12-month average market value.")
    with st.expander("More options"):
        eq = st.slider("Share in Shariah-screened stocks", 0.5, 1.0, 1.0, 0.05,
                       help="The rest is held as non-interest-bearing cash.")
        use_llm = st.toggle("Use AI to read US annual reports (10-Ks)", value=llm.available(), disabled=not llm.available(),
                            help="Needs OPENAI_API_KEY in .env. Without it, only the industry code is checked and most "
                                 "companies need a person to review them.")
        tickers = st.multiselect("Stocks to consider", MARKETS[market]["universe"], default=MARKETS[market]["universe"])
meth = METHODOLOGIES[standard]


# ---------------- screening (shared by both pages) ----------------
@st.cache_data(show_spinner=False)
def screen_one(t: str, std: str, use_ai: bool):
    return pipeline.screen_one(t, std, use_ai)


@st.cache_data(show_spinner=False)
def metrics_for(t: str):
    return signals.price_metrics(t)


def plain_why(v: dict) -> str:
    """One friendly sentence saying what the result means."""
    if v["status"] == PASS:
        return f"Meets every {html.escape(standard)} screen we can check. That is not a religious ruling - it means the " \
               f"numbers and the annual report raise no flag under this standard."
    if v["status"] == FAIL:
        fails = [s for s in v["screens"] if s["status"] == FAIL]
        return "Excluded under this standard because: " + html.escape("; ".join(s["label"].lower() + (f" is {s['value']:.1%}"
                                                                                                        if s.get("value") is not None else "")
                                                                                 + (f" (limit {s['op']} {s['limit']:.1%})" if s.get("limit") else "")
                                                                                 for s in fails)) + "."
    revs = [s for s in v["screens"] if s["status"] == NEEDS_REVIEW]
    return "A person needs to check before this could be held: " + html.escape("; ".join(s["label"].lower() for s in revs)) + "."


# ---------------- header + page switch ----------------
st.markdown("""<div class="topbar"><div class="brand word"><span class="brand-mark" aria-hidden="true"></span>AMANAT</div>
<div class="topbar-note">Educational project · Not financial advice · Not a fatwa</div></div>""", unsafe_allow_html=True)
page = st.segmented_control("Page", ["🔎 Check a company", "📊 Build my portfolio"], default="🔎 Check a company",
                            key="page", label_visibility="collapsed") or "🔎 Check a company"


# ================= the investment committee (used on both pages) =================
def fact_chips(ids, facts) -> str:
    return "".join(f'<span class="fact" title="{html.escape(str(facts.get(i, {}).get("source", "")))}">'
                   f'{html.escape(facts.get(i, {}).get("label", "")[:38])}: '
                   f'{html.escape(str(facts.get(i, {}).get("display", ""))[:30])}</span>' for i in ids)


def show_case(case, title, facts):
    st.markdown(f'<div class="agent-title">{title}</div>', unsafe_allow_html=True)
    if not case or not case.get("available"):
        st.caption("This analyst was unavailable.")
        return
    if case.get("thesis"):
        st.markdown(case["thesis"])
    for p in case.get("points", []):
        st.markdown(f"- {html.escape(p['claim'])}<br>{fact_chips(p['facts'], facts)}", unsafe_allow_html=True)
    if case.get("change"):
        st.caption("What would change this view: " + case["change"])


def render_committee(r: dict, key: str, position=None, rank_row=None, stress=None) -> None:
    """Gate banner (always), then the four-agent discussion on request."""
    t, v = r["ticker"], r["verdict"]
    g = shariah_checker.gate(r)
    cls = STATUS_CLASS[g["status"]]
    items = "".join(f"<li>{html.escape(x)}</li>" for x in (g["reasons"] + g["review"])[:6])
    st.markdown(f'<div class="gate {cls}"><div class="label">Step 1 · Shariah compliance check (decides first, audits last)</div>'
                f'<div class="t">{STATUS_LABEL[g["status"]]} under {html.escape(g["standard"])}</div>'
                f'<div class="sub">{html.escape(g["banner"])}</div><ul class="sub">{items}</ul></div>', unsafe_allow_html=True)
    if g["status"] == FAIL:
        st.caption("Excluded companies are not discussed further - the compliance check has the final word.")
        return
    if not llm.available():
        st.info("Add OPENAI_API_KEY to .env to let the analysts discuss this company.")
        return
    skey = f"committee_{t}_{standard}"
    if st.button("Ask the investment committee", key=f"btn_{key}", help="Two analysts argue for and against, a risk "
                 "reviewer weighs them, and the Shariah checker audits every sentence. About 20 seconds."):
        try:
            m = metrics_for(t)
        except Exception:
            m = None
        with st.spinner("The analysts are reading the evidence..."):
            st.session_state[skey] = committee.run(r, m, rank_row, position, stress)
    res = st.session_state.get(skey)
    if not res or not res.get("ran"):
        return
    facts = res["facts"]
    c1, c2 = st.columns(2, gap="large")
    with c1:
        show_case(res["bull"], "Step 2 · The case for holding it", facts)
    with c2:
        show_case(res["bear"], "Step 3 · The case against", facts)
    rk = res["risk"]
    st.markdown('<div class="agent-title">Step 4 · Risk check</div>', unsafe_allow_html=True)
    if not rk.get("available"):
        st.caption("The risk reviewer was unavailable.")
    else:
        if rk.get("flag"):
            st.markdown(f'<span class="tag warn">Flag: {html.escape(rk["flag"])}</span>', unsafe_allow_html=True)
        if rk.get("summary"):
            st.markdown(rk["summary"])
        for p in rk["key_risks"]:
            st.markdown(f"- {html.escape(p['claim'])}<br>{fact_chips(p['facts'], facts)}", unsafe_allow_html=True)
        if rk.get("unsupported_claims"):
            st.caption("Claims the reviewer found unsupported: " + "; ".join(rk["unsupported_claims"]))
    a = res["audit"]
    if a["approved"]:
        st.success("Step 5 · Shariah audit: every statement above was checked and approved.")
    elif not a["llm_checked"]:
        st.warning("Step 5 · Shariah audit: the rule checks ran, but the AI audit was unavailable. Read the statements with care.")
    if a["removed"]:
        st.warning(f"Step 5 · Shariah audit removed {len(a['removed'])} statement(s) that broke the rules:")
        for sid, why in a["removed"].items():
            st.markdown(f'<div class="removed">{html.escape(a["removed_text"].get(sid, ""))}</div>'
                        f'<div class="sub">{html.escape("; ".join(why))}</div>', unsafe_allow_html=True)
    dropped = res["bull"]["dropped"] + res["bear"]["dropped"] + res["risk"]["dropped"]
    if dropped:
        with st.expander(f"{len(dropped)} claim(s) removed because they cited no evidence or used numbers not in it"):
            for d in dropped:
                st.markdown(f"- {html.escape(d['text'])} - _{html.escape(d['why'])}_")
    with st.expander("The evidence the analysts were allowed to use"):
        st.dataframe(pd.DataFrame([{"Fact": f["label"], "Value": f["display"], "Source": f["source"], "Period": f["period"]}
                                   for f in facts.values()]), width="stretch", hide_index=True)
    st.caption(res["disclaimer"])


# ================= page 1: check any company =================
def ratio_row(s: dict, source: str) -> str:
    label, value, limit = s["label"], s.get("value"), s.get("limit")
    lim_txt = f"limit {s['op']} {limit:.1%}" if limit else ""
    if value is None:
        return (f'<div class="ratio"><div class="ratio-top"><b>{html.escape(label)}</b><span class="warn-text">🔎 no data · {lim_txt}</span></div>'
                f'<div class="meta">{html.escape(s.get("note") or source or "not reported")}</div></div>')
    cls = {PASS: "good", FAIL: "bad", NEEDS_REVIEW: "warn-text"}[s["status"]]
    fill = {PASS: "", FAIL: " over", NEEDS_REVIEW: " review"}[s["status"]]
    width = min(value / limit, 1.0) * 100 if limit else 0
    note = s.get("note") or source or ""
    return (f'<div class="ratio"><div class="ratio-top"><b>{html.escape(label)}</b>'
            f'<span class="{cls}">{value:.1%} · {lim_txt} {STATUS_ICON[s["status"]]}</span></div>'
            f'<div class="bar"><div class="fill{fill}" style="width:{width:.0f}%"></div></div>'
            f'<div class="meta">{html.escape(note[:220])}</div></div>')


def company_report(symbol: str, exchange: str) -> None:
    with st.spinner(f"Checking {symbol}..."):
        r = screen_one(symbol, standard, use_llm)
    fin, v, b, p = r["fin"], r["verdict"], r["business"], r.get("profile") or {}
    cur = r.get("currency") or ""
    meta = " · ".join(html.escape(str(x)) for x in (symbol, exchange or p.get("exchange"), p.get("industry"), p.get("country")) if x)

    with st.container(key="panel_report_head"):
        st.markdown(f'<div class="report-head"><div><div class="label">Shariah screen · {html.escape(standard)}</div>'
                    f'<div class="report-name">{html.escape(fin["name"])}</div><div class="meta">{meta}</div></div>'
                    f'<div class="verdict {STATUS_CLASS[v["status"]]}">{STATUS_LABEL[v["status"]]}</div></div>'
                    f'<div class="why">{plain_why(v)}</div>', unsafe_allow_html=True)

    left, right = st.columns([1.15, 1], gap="large")
    with left, st.container(key="panel_ratios"):
        denom = meth["ratios"][0]["denominator"].replace("_", " ")
        st.markdown(f'<div class="label">Financial screens · share of {denom}</div>', unsafe_allow_html=True)
        rows = []
        for s in v["screens"]:
            if s["key"] == "activity":
                continue
            if s["key"] == "freshness":
                rows.append(f'<div class="ratio"><div class="ratio-top"><b>Data freshness</b><span class="warn-text">🔎</span></div>'
                            f'<div class="meta">{html.escape(s["note"])}</div></div>')
                continue
            src_key = {"debt": "total_debt", "cash": "cash_and_interest_bearing", "receivables_plus_cash": "receivables",
                       "noncompliant_income": "interest_income"}.get(s["key"], "")
            rows.append(ratio_row(s, fin["sources"].get(src_key, "")))
        st.markdown("".join(rows), unsafe_allow_html=True)
        st.caption(f"Figures in {cur}, balance sheet dated {fin.get('period_end') or 'unknown'}. "
                   + (f"Market value {big_money('', r['mcap']['value'])} {cur} ({r['mcap']['note']})." if r.get("mcap") and
                      meth["ratios"][0]["denominator"] == "market_cap" else ""))

    with right, st.container(key="panel_business"):
        act = next(s for s in v["screens"] if s["key"] == "activity")
        st.markdown(f'<div class="label">Business activity · {STATUS_ICON[act["status"]]} {act["status"].title()}</div>',
                    unsafe_allow_html=True)
        acts = b.get("activities") or []
        if not acts:
            st.markdown("**No excluded activity found**" + (" in the annual report." if b.get("method") == "LLM" else
                                                           " in the industry classification."))
        for a in acts:
            share = (f"~{a['revenue_share_pct']:.0f}% of revenue" if a.get("revenue_share_pct") is not None else
                     f"at least {a['min_revenue_share_pct']:.0f}% of revenue" if a.get("min_revenue_share_pct") else
                     "share of revenue not stated")
            head = f"**{nice(a['category']).capitalize()}** · {share}" + (" · main business" if a.get("primary_business") else "")
            st.markdown(head)
            if a.get("evidence"):
                tick = "✓ quote found in the filing" if a.get("quote_verified") else "✗ quote NOT found in the filing - not used as evidence"
                st.markdown(f'<div class="quote">{html.escape(str(a["evidence"])[:400])}<div class="meta">{tick}</div></div>',
                            unsafe_allow_html=True)
        if act.get("note"):
            st.caption(act["note"])
        st.caption("Checked by: " + {"LLM": "AI reading of the latest annual report, every quote verified in Python",
                                     "SIC rule": "SEC industry code only", "Industry rule": "Yahoo Finance industry only"}
                   .get(b.get("method"), str(b.get("method"))))
        if b.get("main_business") and b.get("method") == "LLM":
            st.caption("What the company does: " + b["main_business"])
        if p.get("longBusinessSummary"):
            with st.expander("What the company does"):
                st.write(p["longBusinessSummary"])

    try:
        hist = prices.history(symbol)
        hist = hist[hist.index >= hist.index[-1] - pd.Timedelta(days=5 * 365)]
        with st.container(key="panel_price"):
            st.markdown('<div class="label">Share price · last 5 years</div>', unsafe_allow_html=True)
            fig = px.area(hist.rename("price").reset_index(), x="index", y="price", labels={"index": "", "price": ""},
                          color_discrete_sequence=[BLUES[0]])
            fig.update_traces(line_width=2, fillcolor="rgba(5,102,141,.08)")
            st.plotly_chart(styled(fig, 220), width="stretch")
    except Exception:
        pass

    with st.container(key="panel_ai"):
        st.markdown('<div class="label">AI investment committee</div>', unsafe_allow_html=True)
        st.caption("Four AI agents, in a fixed order. The Shariah compliance check decides first and audits everything "
                   "at the end; the analysts can only explain, never change a result. Every claim must point to a fact "
                   "shown on this page.")
        render_committee(r, key=f"report_{symbol}")

    limits = ["This is research support, not a fatwa - a Shariah scholar makes the ruling.",
              f"Standard applied: {meth['source']} (checked {meth['verified_on']}). {meth['verification_note']}"]
    if fin.get("missing"):
        limits.append("Not reported in the data we have: " + ", ".join(nice(m) for m in fin["missing"]) +
                      " - those screens need a person to check.")
    limits += [n for n in fin.get("notes", [])]
    if r["source"] == "Yahoo Finance":
        limits += ["Figures are Yahoo Finance's copy of the accounts, not the filing itself - check the company's annual report.",
                   "Business activity is judged from the industry classification only: it can exclude a company, but it "
                   "cannot confirm one as clear, so non-US companies need a person to check that screen."]
    else:
        limits += ["Figures come straight from the company's SEC filings (XBRL), all from one balance-sheet date."]
    links = " · ".join(f"[{t}]({u})" for t, u in (("Filing / data source", b.get("source_url") or fin.get("source_url")),
                                                  ("Company website", p.get("website")),
                                                  ("Methodology", meth["url"])) if u)
    with st.expander("Sources and limitations"):
        st.markdown(f"**Source:** {r['source']}" + (f" · {links}" if links else ""))
        st.markdown('<ul class="limits">' + "".join(f"<li>{html.escape(x)}</li>" for x in limits) + "</ul>",
                    unsafe_allow_html=True)
        items = fin.get("items") or {}
        if items:
            st.dataframe(pd.DataFrame([{"Item": nice(k), "Value": (f"{it['value'] / 1e9:,.2f}bn {cur}" if it and k !=
                                        "shares_outstanding" else f"{it['value'] / 1e9:,.3f}bn shares" if it else "not reported"),
                                        "Source row / concept": it["concept"] if it else "-",
                                        "Period end": (it or {}).get("period_end", "-")} for k, it in items.items()]),
                         width="stretch", hide_index=True)


if page.startswith("🔎"):
    st.markdown("""<div class="hero"><div class="eyebrow">Shariah screening for UK investors</div>
<h1>Is it halal to invest in?</h1>
<p>Search any listed company. We check what it does and how it's financed against the Shariah rules,
and show you the evidence behind every answer.</p></div>""", unsafe_allow_html=True)
    q = st.text_input("Search any listed company", placeholder="Company name or ticker - e.g. Tesco, AstraZeneca, Apple",
                      key="query")
    quick = st.pills("Popular", POPULAR[market], key=f"quick_{market}", label_visibility="collapsed")
    q = q.strip() or quick or ""
    if not q:
        st.caption("Try one of the popular companies above, or type any name or ticker.")
    else:
        try:
            matches = yahoo.search(q)
        except Exception as e:
            matches = []
            st.error(f"Search is unavailable right now ({e}). Try a ticker such as TSCO.L.")
        if q.upper() == q and " " not in q and not any(m["symbol"] == q.upper() for m in matches):
            matches.insert(0, {"symbol": q.upper(), "name": q.upper(), "exchange": ""})
        if market.startswith("UK"):  # London listings first for UK investors
            matches.sort(key=lambda m: not m["symbol"].endswith(".L"))
        if not matches:
            st.warning(f"No listed company found for “{q}”.")
        else:
            labels = [f'{m["name"]} · {m["symbol"]}' + (f' · {m["exchange"]}' if m["exchange"] else "") for m in matches]
            i = st.selectbox("Which one?", range(len(matches)), format_func=lambda k: labels[k], key=f"pick_{q}")
            try:
                company_report(matches[i]["symbol"], matches[i]["exchange"])
            except Exception as e:
                st.error(f"Couldn't load the figures for {matches[i]['symbol']}: {e}")


# ================= page 2: build a portfolio =================
else:
    results, errors = {}, []
    with st.spinner("Checking companies against the Shariah screens..."):
        for t in tickers:
            try:
                results[t] = screen_one(t, standard, use_llm)
            except Exception as e:  # keep the demo alive; show what failed
                errors.append(f"{t}: {type(e).__name__}: {e}")

    statuses = {t: r["verdict"]["status"] for t, r in results.items()}
    counts = {s: sum(x == s for x in statuses.values()) for s in STATUS_LABEL}
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

    st.markdown(f"""<div class="hero"><div class="eyebrow">Your plan, screened for Shariah</div>
<h1>Halal investing, explained.</h1>
<p>We check {len(results)} {MARKETS[market]["label"]} companies against the {html.escape(standard)} rules, rank only the ones
that pass every screen for a <b>{risk.lower()}</b> investor, and show what that means for your {C}{amount:,.0f} - with the
evidence behind every result.</p></div>""", unsafe_allow_html=True)

    heading("Your plan at a glance", f"{standard} standard · {risk} profile")
    worst = stt.loc[stt["portfolio_return"].idxmin()] if stt is not None and not stt.empty else None
    to_purify = pur["to_purify"].dropna().sum() if pur is not None and not pur.empty else 0.0
    unknown_purify = int(pur["to_purify"].isna().sum()) if pur is not None and not pur.empty else 0
    cards = [
        card("Invested", f"{C}{amount:,.0f}", f"{eq:.0%} Shariah-screened stocks" + (f" · {1 - eq:.0%} non-interest cash" if eq < 1 else "")),
        card("Pass every screen", f"{counts[PASS]} of {len(results)}",
             f"{counts[FAIL]} fail · {counts[NEEDS_REVIEW]} need a person to check"),
        card("Stocks in your plan", str(len(holdings)), "Only passing stocks · max 10% in any one"),
        card(f"In a bad year ({int(worst['year'])})" if worst is not None else "In a bad year",
             f"{C}{worst['value_after']:,.0f}" if worst is not None else "-",
             f"{worst['gain_or_loss']:+,.0f} vs today" if worst is not None else "Not enough price history",
             "bad" if worst is not None and worst["gain_or_loss"] < 0 else ""),
        card("Give to charity this year", f"{C}{to_purify:,.2f}",
             "Purification" + (f" · {unknown_purify} holding(s) unknown" if unknown_purify else "")),
    ]
    st.markdown(f'<div class="stats five">{"".join(cards)}</div>', unsafe_allow_html=True)

    if alloc is not None:
        heading("Where your money goes", "Calmer stocks get more")
        left, right = st.columns([1, 1.2], gap="large")
        with left, st.container(key="panel_donut"):
            st.markdown(f'<div class="label">Portfolio value</div><div class="big">{C}{amount:,.0f}</div>', unsafe_allow_html=True)
            names = {r["ticker"]: r["company"] for _, r in ranking.iterrows()} if not ranking.empty else {}
            donut = alloc.assign(label=alloc["holding"].map(lambda h: names.get(h, h)))
            fig = px.pie(donut, names="label", values="amount", hole=.62, color_discrete_sequence=BLUES)
            fig.update_traces(textinfo="none", hovertemplate=f"%{{label}}<br>{C}%{{value:,.0f}} (%{{percent}})<extra></extra>")
            fig.update_layout(legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center", yanchor="top"))
            st.plotly_chart(styled(fig, 460), width="stretch")
        with right, st.container(key="panel_top"):
            st.markdown(f'<div class="label">Top picks for a {risk.lower()} investor</div>', unsafe_allow_html=True)
            rows = []
            for _, r in ranking.head(5).iterrows():
                share = alloc.set_index("holding")["amount"].get(r["ticker"])
                rows.append(f'<div class="row"><div><div class="name">{html.escape(r["company"])}</div>'
                            f'<div class="meta">{r["ticker"]} · {r["return_1y"]:+.0%} over the past year'
                            + (f" · {C}{share:,.0f} in your plan" if share else "") + '</div>'
                            f'<span class="tag{" warn" if r["signal"].startswith("Watch - near") else ""}">{r["signal"]}</span></div>'
                            f'<div class="score">{r["score"]:.0f}/100</div></div>')
            st.markdown("".join(rows) or '<div class="sub">No passing stocks to rank yet.</div>', unsafe_allow_html=True)
    elif not passing:
        st.info("No company in this list passes every screen of this standard, so there is nothing to invest in yet. "
                "Non-US companies always need a person to confirm the business-activity screen.")

    # ---------------- details ----------------
    money = st.column_config.NumberColumn  # £ has no built-in format, so label the currency in the header
    money_fmt = "dollar" if C == "$" else "localized"
    heading("Explore the details", "Every number can be traced to its source")
    tab_screen, tab_picks, tab_alloc, tab_stress, tab_ask, tab_method = st.tabs(
        ["Shariah check", "Stock picks", "Your portfolio", "Bad years & charity", "Ask the analyst", "Methodology"])

    def cell(v, key):
        s = next((x for x in v["screens"] if x["key"] == key), None)
        return "n/a" if s is None else f"{STATUS_ICON[s['status']]} {pct(s['value'])}"

    with tab_screen:
        rows = []
        for t, r in results.items():
            v, b = r["verdict"], r["business"]
            row = {"Ticker": t, "Company": r["fin"]["name"], "Result": STATUS_LABEL[v["status"]], "Activities": cell(v, "activity")}
            for rule in meth["ratios"]:
                row[rule["label"]] = cell(v, rule["key"])
            row["Interest + non-compliant income"] = cell(v, "noncompliant_income")
            row["Why"] = "; ".join(v["reasons"] + v["review"]) or "meets every screen"
            row["Evidence"] = b.get("evidence", "")
            row["Data"] = r["source"]
            rows.append(row)
        df = pd.DataFrame(rows)
        show = st.segmented_control("Show", ["All"] + list(STATUS_LABEL.values()), default="All", key="screen_filter")
        if show and show != "All" and not df.empty:
            df = df[df["Result"] == show]
        st.dataframe(df, width="stretch", hide_index=True)
        st.caption(f"Standard: {meth['source']}. US companies: SEC EDGAR filings. UK companies: Yahoo Finance's copy of the "
                   "accounts. \"Needs review\" means a rule could not be checked with the data available - we flag it rather than guess.")
        if results:
            with st.container(key="panel_company"):
                st.markdown('<div class="label">Look closer at one company</div>', unsafe_allow_html=True)
                order = sorted(results, key=lambda t: (statuses[t] != PASS, statuses[t] != NEEDS_REVIEW, t))
                cpick = st.selectbox("Company", order, key="committee_pick",
                                     format_func=lambda t: f"{t} · {results[t]['fin']['name']} · {statuses[t]}")
                r = results[cpick]
                pos = alloc.set_index("holding").loc[cpick].to_dict() if alloc is not None and cpick in set(alloc["holding"]) else None
                rr = ranking.set_index("ticker").loc[cpick].to_dict() if not ranking.empty and cpick in set(ranking["ticker"]) else None
                render_committee(r, key=f"portfolio_{cpick}", position=pos, rank_row=rr,
                                 stress=stt.to_dict("records") if stt is not None else None)
        if errors:
            with st.expander(f"{len(errors)} items could not be loaded"):
                st.write(errors)

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
                "price": money("Price" if C == "$" else "Price (pence)", format="dollar" if C == "$" else "%.1f"),
                "return_1y": st.column_config.NumberColumn("1-year return", format="percent"),
                "momentum_12_1": st.column_config.NumberColumn("Momentum", format="percent"),
                "volatility": st.column_config.NumberColumn("Volatility", format="percent"),
                "max_drawdown_1y": st.column_config.NumberColumn("Worst fall (1y)", format="percent"),
                "headroom": st.column_config.NumberColumn("Room below Shariah limit", format="percent")})
            st.caption("Only stocks that pass every screen are ranked. Score = momentum + steadiness + smaller falls + room "
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
                                        "amount": money(f"Amount ({C})", format=money_fmt)})
            st.caption("Every holding passed every screen of the selected standard - the portfolio code refuses anything "
                       "else. Inverse-volatility weights (calmer stocks get more), max 10% each; any remainder is "
                       "non-interest-bearing cash. Deterministic maths - the AI does not choose the numbers.")

    with tab_stress:
        if stt is None:
            st.info("Build a portfolio first.")
        else:
            st.subheader(f"What past years would have done to your {C}{amount:,.0f}")
            year_cards = [card(str(int(y["year"])), f"{C}{y['value_after']:,.0f}",
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
                    "dividend_received": money(f"Dividends you'd receive ({C})", format=money_fmt),
                    "noncompliant_share": st.column_config.NumberColumn("Non-compliant income", format="percent"),
                    "to_purify": money(f"To donate ({C})", format=money_fmt), "method": "How"})
                if unknown_purify:
                    st.caption("Blank 'To donate' means the non-compliant income share is unknown - it is not guessed.")
            else:
                st.info("Nothing to purify.")

    with tab_ask:
        if not llm.available():
            st.info("Add OPENAI_API_KEY to .env to enable the AI coach.")
        else:
            context = {"investor": {"type": "individual Muslim investor", "market": market, "currency": C,
                                    "amount": amount, "risk_appetite": risk, "standard": standard},
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
        st.markdown("**Financial screens**")
        st.dataframe(pd.DataFrame([{"Clause": r["clause"], "Screen": r["label"], "Rule (quoted)": r["text"],
                                    "Pass if": f"value {r['op']} {r['limit']:.3%}"} for r in meth["ratios"]]
                                  + [{"Clause": meth["income"]["clause"], "Screen": "Interest + non-compliant income",
                                      "Rule (quoted)": meth["income"]["text"],
                                      "Pass if": f"value {meth['income']['op']} {meth['income']['limit']:.0%}"}]),
                     width="stretch", hide_index=True)
        st.markdown("""**How the app applies it - and its limits**
- Each standard is applied on its own; their rules are never combined.
- Ratios are calculated in Python. US figures come from SEC EDGAR XBRL; UK figures from Yahoo Finance's copy of the accounts.
  All balance-sheet items come from one reporting date.
- "Cash and interest-bearing items" = cash + short-term investments. Long-term interest-bearing securities are shown
  separately; if including them breaks a limit, the screen needs review.
- Interest income counts towards the non-compliant income limit. If it is not reported, that screen needs review.
- Any required figure that is missing gives "needs review" - never a 0 or a guess.
- US business activities are read by AI from the latest 10-K (Item 1 plus every sentence in the filing that mentions a
  screened activity). Every quote is checked word-for-word against the filing; unmatched quotes are ignored.
  UK business activities use the industry classification only, which can exclude but never clear a company.
- FTSE's quarter-on-quarter monitoring band (31.667%-35%) needs past quarters, which the app does not check:
  passing values inside the band need review.
- AAOIFI market value = 12-month average share price x shares outstanding, converted to the reporting currency.
- Passing these screens is not a religious ruling or a guarantee of compliance.""")

st.markdown('<div class="disclaimer">Educational hackathon project (Microsoft × LSEG 2026). Not financial advice. '
            'Not a fatwa - this is the evidence a Shariah scholar would review, not a ruling.</div>', unsafe_allow_html=True)
