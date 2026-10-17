"""CareerPilot Mini — Streamlit UI.  Run: streamlit run app.py"""
from pathlib import Path

import streamlit as st

from careerpilot.agent import run_agent
from careerpilot.config import get_api_key, get_model_name
from careerpilot.report import build_guide_docx

SAMPLE_DIR = Path(__file__).parent / "sample_data"

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CareerPilot Mini",
    page_icon="🧭",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── font & base ── */
html, body, [class*="css"]  { font-family: 'Inter', sans-serif; }

/* ── hero banner ── */
.hero {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
    border-radius: 16px;
    padding: 2.4rem 2rem 2rem;
    margin-bottom: 1.8rem;
    text-align: center;
    box-shadow: 0 4px 24px rgba(0,0,0,.25);
}
.hero h1 {
    color: #e2e8f0;
    font-size: 2.2rem;
    font-weight: 800;
    margin: 0 0 .4rem;
    letter-spacing: -.5px;
}
.hero p  {
    color: #94a3b8;
    font-size: 1rem;
    margin: 0;
}

/* ── section cards ── */
.card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 1px 6px rgba(0,0,0,.06);
}
.card-title {
    font-size: .7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: #64748b;
    margin-bottom: .6rem;
}

/* ── skill pills ── */
.pill-wrap  { display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .4rem; }
.pill       { border-radius: 999px; padding: .22rem .72rem; font-size: .78rem; font-weight: 600; }
.pill-green { background: #dcfce7; color: #166534; }
.pill-red   { background: #fee2e2; color: #991b1b; }

/* ── topic rows ── */
.topic-row {
    border-left: 4px solid #6366f1;
    padding: .55rem .9rem;
    margin-bottom: .5rem;
    background: #f8fafc;
    border-radius: 0 8px 8px 0;
}
.topic-num  { font-size: .72rem; font-weight: 700; color: #6366f1; text-transform: uppercase; }
.topic-name { font-size: 1rem; font-weight: 700; color: #1e293b; margin: .1rem 0 .2rem; }
.topic-why  { font-size: .83rem; color: #475569; }

/* ── resource cards ── */
.res-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: .65rem .9rem;
    margin-bottom: .45rem;
}
.res-id    { font-size: .68rem; font-weight: 700; color: #6366f1; }
.res-title { font-size: .88rem; font-weight: 600; color: #1e293b; }
.res-meta  { font-size: .75rem; color: #64748b; margin-top: .1rem; }

/* ── strategy list ── */
.strategy-item {
    display: flex; align-items: flex-start; gap: .6rem;
    padding: .45rem 0; border-bottom: 1px solid #f1f5f9;
    font-size: .9rem; color: #334155;
}
.strategy-num {
    min-width: 1.5rem; height: 1.5rem;
    background: #6366f1; color: #fff;
    border-radius: 50%; display: flex;
    align-items: center; justify-content: center;
    font-size: .72rem; font-weight: 700;
}

/* ── question cards ── */
.q-card {
    background: #fefce8;
    border-left: 4px solid #eab308;
    border-radius: 0 8px 8px 0;
    padding: .55rem .9rem;
    margin-bottom: .45rem;
    font-size: .88rem;
    color: #334155;
}
.q-tag { font-size: .7rem; font-weight: 700; color: #a16207; text-transform: uppercase; }

/* ── log badges ── */
.log-row   { display: flex; align-items: center; gap: .5rem; padding: .25rem 0; }
.badge     { border-radius: 6px; padding: .15rem .5rem; font-size: .7rem; font-weight: 700; text-transform: uppercase; }
.b-success { background:#dcfce7; color:#166534; }
.b-failed  { background:#fee2e2; color:#991b1b; }
.b-skipped { background:#f1f5f9; color:#64748b; }
.b-sim     { background:#fef9c3; color:#854d0e; }
.log-step  { font-size: .82rem; color: #1e293b; font-weight: 600; }
.log-kind  { font-size: .75rem; color: #64748b; }
.log-detail{ font-size: .78rem; color: #475569; margin-left: 3.2rem; margin-bottom: .1rem; }

/* ── limitation notes ── */
.limit-note { font-size: .8rem; color: #64748b; padding: .2rem 0; }

/* ── sidebar tweaks ── */
[data-testid="stSidebar"] { background: #f8fafc; }
</style>
""", unsafe_allow_html=True)

# ── hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>🧭 CareerPilot Mini</h1>
  <p>Upload your resume and a job description — get a personalised interview preparation guide.</p>
</div>
""", unsafe_allow_html=True)

# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    st.divider()

    _has_key = bool(get_api_key())

    if _has_key:
        mode_label = "🤖 AI-Enhanced"
        mode_help  = f"Powered by Gemini ({get_model_name()})."
        demo       = False
    else:
        mode_label = "🔬 Smart Analysis"
        mode_help  = "Skills analysis with built-in topic intelligence."
        demo       = True

    st.markdown(f"**Mode:** {mode_label}")
    st.caption(mode_help)
    st.divider()

    use_search = st.checkbox(
        "🔍 Live web search for resources",
        value=True,
        disabled=demo,
        help="Fetches relevant articles and guides via DuckDuckGo (no account needed).",
    ) if _has_key else False

    st.divider()
    use_sample = st.checkbox(
        "📄 Use sample resume & job description",
        help="Loads the built-in fictional resume and job description so you can try immediately.",
    )
    st.divider()
    st.caption("CareerPilot Mini · Resume-based interview prep")

# ── input section ─────────────────────────────────────────────────────────────
if use_sample:
    resume_bytes = (SAMPLE_DIR / "sample_resume.pdf").read_bytes()
    jd_text      = (SAMPLE_DIR / "sample_job_description.txt").read_text(encoding="utf-8")
    with st.expander("Preview sample job description"):
        st.text(jd_text)
else:
    col_a, col_b = st.columns([1, 1], gap="medium")
    with col_a:
        st.markdown("#### 📎 Resume (PDF)")
        uploaded     = st.file_uploader("Upload PDF", type=["pdf"], label_visibility="collapsed")
        resume_bytes = uploaded.getvalue() if uploaded else None
    with col_b:
        st.markdown("#### 📋 Job Description")
        jd_text = st.text_area(
            "Paste the full job posting",
            height=220,
            label_visibility="collapsed",
            placeholder="Paste the full job posting here…",
        )

st.markdown("")
run_btn = st.button("✨ Generate preparation guide", type="primary", use_container_width=True)

# ── agent run ─────────────────────────────────────────────────────────────────
if run_btn:
    if not resume_bytes or not (jd_text or "").strip():
        st.warning("Please provide both a resume and a job description before running.")
    else:
        with st.spinner("Analysing your resume and job description…"):
            st.session_state["result"] = run_agent(
                resume_bytes, jd_text,
                demo=demo,
                use_search=use_search,
            )

# ── results ───────────────────────────────────────────────────────────────────
result = st.session_state.get("result")
if not result:
    st.stop()

if result.error:
    st.error(result.error)
    st.stop()

g = result.guide

# ── optional workflow log ─────────────────────────────────────────────────────
BADGE = {"success": ("b-success", "✓ OK"), "failed": ("b-failed", "✗ Failed"),
         "skipped": ("b-skipped", "– Skipped"), "simulated": ("b-sim", "~ Simulated")}

with st.expander("🔍 Workflow log", expanded=False):
    for s in result.log:
        cls, label = BADGE.get(s["status"], ("b-skipped", s["status"].upper()))
        st.markdown(
            f'<div class="log-row">'
            f'<span class="badge {cls}">{label}</span>'
            f'<span class="log-step">{s["step"]}</span>'
            f'<span class="log-kind">({s["kind"]})</span>'
            f'</div>'
            f'<div class="log-detail">{s["detail"]}</div>',
            unsafe_allow_html=True,
        )

st.divider()

# ── header ────────────────────────────────────────────────────────────────────
st.markdown(f"## 📑 Interview Preparation Guide")
st.caption(f"Role: **{g['job_title']}** · Generated {g['generated_on']}")

# Only show warnings that are genuinely actionable for the user (e.g. bad input).
# Suppress all internal/technical warnings (search failures, date issues, etc.)
_SUPPRESS_PATTERNS = ["search", "api", "key", "date", "resource", "web", "retriev", "verif", "unavail"]
_visible_warnings = [
    w for w in g.get("warnings", [])
    if not any(p in w.lower() for p in _SUPPRESS_PATTERNS)
]
for w in _visible_warnings:
    st.warning(w)

# ── job summary ───────────────────────────────────────────────────────────────
st.markdown("""<div class="card">
  <div class="card-title">Job summary</div>""", unsafe_allow_html=True)
st.markdown(g["job_summary"])
st.markdown("</div>", unsafe_allow_html=True)

# ── skills ────────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2, gap="medium")

with col1:
    st.markdown('<div class="card"><div class="card-title">✅ Matched in your resume</div>'
                '<div class="pill-wrap">', unsafe_allow_html=True)
    if g["matched_skills"]:
        pills = "".join(f'<span class="pill pill-green">{s}</span>' for s in g["matched_skills"])
        st.markdown(pills + '</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<span style="color:#64748b;font-size:.85rem">None detected</span></div></div>',
                    unsafe_allow_html=True)

with col2:
    st.markdown('<div class="card"><div class="card-title">⚠️ Not evidenced in resume</div>'
                '<div class="pill-wrap">', unsafe_allow_html=True)
    if g["missing_skills"]:
        pills = "".join(f'<span class="pill pill-red">{s}</span>' for s in g["missing_skills"])
        st.markdown(pills + '</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<span style="color:#64748b;font-size:.85rem">All skills accounted for</span></div></div>',
                    unsafe_allow_html=True)

# ── topics ────────────────────────────────────────────────────────────────────
st.markdown("### 🎯 Prioritised preparation topics")
res_map = {r["id"]: r for r in g["resources"]}

for i, t in enumerate(g["topics"], 1):
    linked = [res_map[rid] for rid in t["resource_ids"] if rid in res_map]
    link_html = ""
    if linked:
        links = " · ".join(
            f'<a href="{r["url"]}" target="_blank" style="color:#6366f1;font-size:.78rem">[{r["id"]}] {r["title"][:55]}…</a>'
            if len(r["title"]) > 55 else
            f'<a href="{r["url"]}" target="_blank" style="color:#6366f1;font-size:.78rem">[{r["id"]}] {r["title"]}</a>'
            for r in linked
        )
        link_html = f'<div style="margin-top:.35rem">{links}</div>'

    st.markdown(
        f'<div class="topic-row">'
        f'<div class="topic-num">Topic {i}</div>'
        f'<div class="topic-name">{t["topic"]}</div>'
        f'<div class="topic-why">{t["reason"]}</div>'
        f'{link_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

# ── strategy ─────────────────────────────────────────────────────────────────
st.markdown("### 🗺️ Preparation strategy")
st.markdown('<div class="card">', unsafe_allow_html=True)
for i, step in enumerate(g["strategy"], 1):
    st.markdown(
        f'<div class="strategy-item">'
        f'<div class="strategy-num">{i}</div>'
        f'<div>{step}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
st.markdown("</div>", unsafe_allow_html=True)

# ── practice questions ────────────────────────────────────────────────────────
st.markdown("### 💬 Practice questions")
if g["practice_questions"]:
    for q in g["practice_questions"]:
        st.markdown(
            f'<div class="q-card">'
            f'<div class="q-tag">{q["topic"]}</div>'
            f'<div>{q["question"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
else:
    st.caption("Practice questions will appear here once the AI synthesis step runs.")

# ── resources ─────────────────────────────────────────────────────────────────
if g["resources"]:
    st.markdown("### 🔗 Research resources")
    for r in g["resources"]:
        pub = r["published"] or "date unverified"
        st.markdown(
            f'<div class="res-card">'
            f'<div class="res-id">[{r["id"]}] {r["topic"]}</div>'
            f'<div class="res-title"><a href="{r["url"]}" target="_blank" style="color:#1e293b;text-decoration:none">{r["title"]}</a></div>'
            f'<div class="res-meta">📅 {pub} · {r["date_note"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── download ──────────────────────────────────────────────────────────────────
st.divider()
st.download_button(
    label="⬇️ Download guide as Word document",
    data=build_guide_docx(g),
    file_name="Interview_Preparation_Guide.docx",
    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    use_container_width=True,
)

# ── limitations (collapsed) ───────────────────────────────────────────────────
with st.expander("ℹ️ Limitations & notes", expanded=False):
    for note in g["limitations"]:
        st.markdown(f'<div class="limit-note">• {note}</div>', unsafe_allow_html=True)
