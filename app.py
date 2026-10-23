from __future__ import annotations

import streamlit as st


st.set_page_config(
    page_title="Mosaic | Impact portfolio",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root {
        --baltic-blue: #05668d;
        --rich-cerulean: #427aa1;
        --alice-blue: #ebf2fa;
        --ink: #123047;
        --muted: #6e8799;
        --white: #ffffff;
        --line: rgba(5, 102, 141, 0.12);
    }

    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

    html, body, [data-testid="stAppViewContainer"] {
        background: var(--alice-blue);
        color: var(--ink);
        font-family: 'DM Sans', sans-serif;
    }

    [data-testid="stHeader"], [data-testid="stToolbar"],
    [data-testid="stDecoration"], footer { display: none; }

    [data-testid="stAppViewContainer"] > .main {
        padding: 0 4rem 3.5rem;
    }

    .intro-screen {
        position: fixed;
        z-index: 1000;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        background: var(--baltic-blue);
        animation: leave-screen 3.2s cubic-bezier(.77, 0, .18, 1) 1.1s forwards;
        pointer-events: none;
    }

    .intro-screen::after {
        content: "";
        position: absolute;
        top: -8%;
        bottom: -8%;
        right: -8vw;
        width: 18vw;
        opacity: 0;
        background: linear-gradient(90deg, rgba(5, 102, 141, .95), rgba(235, 242, 250, 0));
        filter: blur(22px);
        animation: melt-edge 3.2s cubic-bezier(.77, 0, .18, 1) 1.1s forwards;
    }

    .intro-copy {
        color: var(--alice-blue);
        font-family: 'Space Grotesk', sans-serif;
        font-size: clamp(2.3rem, 7vw, 7.5rem);
        font-weight: 600;
        letter-spacing: -.07em;
        line-height: .92;
        text-align: center;
        animation: intro-copy 3.2s ease-in-out 1.1s forwards;
    }

    @keyframes leave-screen {
        0%, 62% { transform: translateX(0); opacity: 1; }
        83% { transform: translateX(-78%); opacity: .92; }
        100% { transform: translateX(-112%); opacity: 0; }
    }

    @keyframes melt-edge {
        0%, 55% { opacity: 0; transform: translateX(0); }
        74% { opacity: 1; transform: translateX(-4vw); }
        100% { opacity: 0; transform: translateX(-13vw); }
    }

    @keyframes intro-copy {
        0%, 55% { opacity: 1; transform: translateX(0); }
        100% { opacity: 0; transform: translateX(-7vw); }
    }

    .topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        max-width: 1180px;
        margin: 0 auto;
        padding: 2.2rem 0 1.5rem;
    }

    .brand {
        color: var(--baltic-blue);
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.25rem;
        font-weight: 700;
        letter-spacing: -.04em;
    }

    .brand-mark {
        display: inline-grid;
        width: 27px;
        height: 27px;
        margin-right: .45rem;
        place-items: center;
        border-radius: 9px;
        background: var(--baltic-blue);
        color: var(--alice-blue);
        font-size: .9rem;
    }

    .topbar-note {
        color: var(--muted);
        font-size: .82rem;
        letter-spacing: .02em;
    }

    .hero {
        max-width: 1180px;
        margin: 2.6rem auto 3rem;
    }

    .eyebrow {
        color: var(--rich-cerulean);
        font-size: .78rem;
        font-weight: 700;
        letter-spacing: .16em;
        text-transform: uppercase;
    }

    .hero h1 {
        max-width: 720px;
        margin: .65rem 0 .8rem;
        color: var(--ink);
        font-family: 'Space Grotesk', sans-serif;
        font-size: clamp(2.45rem, 5vw, 4.8rem);
        letter-spacing: -.07em;
        line-height: .98;
    }

    .hero p {
        max-width: 560px;
        margin: 0;
        color: var(--muted);
        font-size: 1.04rem;
        line-height: 1.6;
    }

    .section-heading {
        display: flex;
        align-items: end;
        justify-content: space-between;
        margin: 0 0 1rem;
    }

    .section-heading h2 {
        margin: 0;
        color: var(--ink);
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.35rem;
        letter-spacing: -.04em;
    }

    .section-heading span {
        color: var(--muted);
        font-size: .78rem;
    }

    .panel {
        min-height: 310px;
        padding: 1.35rem;
        border: 1px solid var(--line);
        border-radius: 22px;
        background: rgba(255, 255, 255, .68);
        box-shadow: 0 14px 35px rgba(35, 72, 99, .055);
    }

    .panel-label {
        color: var(--muted);
        font-size: .75rem;
        letter-spacing: .08em;
        text-transform: uppercase;
    }

    .total {
        margin: .35rem 0 1.35rem;
        color: var(--ink);
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2rem;
        font-weight: 600;
        letter-spacing: -.06em;
    }

    .chart-layout {
        display: flex;
        align-items: center;
        gap: 1.7rem;
    }

    .pie {
        width: 160px;
        height: 160px;
        flex: 0 0 160px;
        border-radius: 50%;
        background: conic-gradient(
            var(--baltic-blue) 0 32%,
            var(--rich-cerulean) 32% 57%,
            #77a6c2 57% 75%,
            #a8c9df 75% 88%,
            #d2e4ef 88% 100%
        );
        box-shadow: inset 0 0 0 1px rgba(255,255,255,.35);
    }

    .legend { display: grid; gap: .75rem; width: 100%; }
    .legend-row { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
    .legend-name { display: flex; align-items: center; color: var(--ink); font-size: .82rem; }
    .legend-dot { width: 9px; height: 9px; margin-right: .5rem; border-radius: 50%; }
    .legend-value { color: var(--ink); font-size: .82rem; font-weight: 700; }

    .opportunity {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: .2rem 1rem;
        align-items: center;
        padding: 1rem 0;
        border-bottom: 1px solid var(--line);
    }

    .opportunity:last-child { border-bottom: 0; }
    .opportunity-name { color: var(--ink); font-size: .95rem; font-weight: 700; }
    .opportunity-meta { color: var(--muted); font-size: .76rem; }
    .opportunity-score { color: var(--baltic-blue); font-size: .9rem; font-weight: 700; }
    .tag {
        display: inline-block;
        margin-top: .45rem;
        padding: .25rem .55rem;
        border-radius: 999px;
        background: rgba(66, 122, 161, .12);
        color: var(--rich-cerulean);
        font-size: .68rem;
        font-weight: 700;
    }

    .stButton > button {
        border: 1px solid rgba(5, 102, 141, .18);
        border-radius: 999px;
        background: transparent;
        color: var(--baltic-blue);
        font-weight: 700;
    }

    .stButton > button:hover {
        border-color: var(--baltic-blue);
        background: var(--baltic-blue);
        color: var(--alice-blue);
    }

    @media (max-width: 800px) {
        [data-testid="stAppViewContainer"] > .main { padding: 0 1.2rem 2rem; }
        .topbar { padding-top: 1.3rem; }
        .topbar-note { display: none; }
        .chart-layout { flex-direction: column; align-items: flex-start; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="intro-screen" aria-label="Intro">
        <div class="intro-copy">INSERT TEMPLATE here</div>
    </div>
    <div class="topbar">
        <div class="brand"><span class="brand-mark">✦</span>mosaic</div>
        <div class="topbar-note">Emerging markets · impact-led research</div>
    </div>
    <div class="hero">
        <div class="eyebrow">Your portfolio, with purpose</div>
        <h1>Grow capital where progress is happening.</h1>
        <p>A considered view of your investments today, and the opportunities worth watching next.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="section-heading">
        <h2>Current investments</h2>
        <span>Updated just now · $100,000 total</span>
    </div>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([1, 1.35], gap="large")

with left:
    st.markdown(
        """
        <div class="panel">
            <div class="panel-label">Portfolio value</div>
            <div class="total">$100,000.00</div>
            <div class="chart-layout">
                <div class="pie" aria-label="Portfolio allocation chart"></div>
                <div class="legend">
                    <div class="legend-row"><div class="legend-name"><span class="legend-dot" style="background:#05668d"></span>Healthcare</div><div class="legend-value">32%</div></div>
                    <div class="legend-row"><div class="legend-name"><span class="legend-dot" style="background:#427aa1"></span>Clean energy</div><div class="legend-value">25%</div></div>
                    <div class="legend-row"><div class="legend-name"><span class="legend-dot" style="background:#77a6c2"></span>Financial access</div><div class="legend-value">18%</div></div>
                    <div class="legend-row"><div class="legend-name"><span class="legend-dot" style="background:#a8c9df"></span>Infrastructure</div><div class="legend-value">13%</div></div>
                    <div class="legend-row"><div class="legend-name"><span class="legend-dot" style="background:#d2e4ef"></span>Cash</div><div class="legend-value">12%</div></div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with right:
    st.markdown(
        """
        <div class="panel">
            <div class="panel-label">Allocation by theme</div>
            <div class="total">5 positions</div>
            <div class="opportunity"><div><div class="opportunity-name">MediCare Africa</div><div class="opportunity-meta">Healthcare · Kenya</div></div><div class="opportunity-score">+12.4%</div></div>
            <div class="opportunity"><div><div class="opportunity-name">SunGrid Energy</div><div class="opportunity-meta">Clean energy · India</div></div><div class="opportunity-score">+9.8%</div></div>
            <div class="opportunity"><div><div class="opportunity-name">Access Bank</div><div class="opportunity-meta">Financial access · Nigeria</div></div><div class="opportunity-score">+7.1%</div></div>
            <div class="opportunity"><div><div class="opportunity-name">Connecta Mobile</div><div class="opportunity-meta">Infrastructure · Brazil</div></div><div class="opportunity-score">+5.6%</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div class="section-heading" style="margin-top:2.8rem">
        <h2>Potential future investments</h2>
        <span>Matched to your impact themes</span>
    </div>
    """,
    unsafe_allow_html=True,
)

future_columns = st.columns(3, gap="medium")
future_investments = [
    ("Kivu Water", "Water access · Rwanda", "Impact fit 91", "High"),
    ("Nuru Foods", "Food security · Tanzania", "Impact fit 87", "Medium"),
    ("Lumen Health", "Affordable care · Philippines", "Impact fit 84", "Medium"),
]

for column, (name, meta, score, confidence) in zip(future_columns, future_investments):
    with column:
        st.markdown(
            f"""
            <div class="panel" style="min-height:0">
                <div class="opportunity" style="padding-top:0">
                    <div><div class="opportunity-name">{name}</div><div class="opportunity-meta">{meta}</div><span class="tag">{score}</span></div>
                    <div class="opportunity-score">↗</div>
                </div>
                <div class="opportunity-meta" style="padding-top:.9rem">Evidence confidence · <strong style="color:var(--ink)">{confidence}</strong></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("<div style='height:.7rem'></div>", unsafe_allow_html=True)
st.button("Explore all opportunities  →", use_container_width=False)
