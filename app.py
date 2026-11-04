"""AI RESILIENCE prototype entry point and shared navigation."""

import streamlit as st


st.set_page_config(
    page_title="AI RESILIENCE | Kochi Climate Intelligence",
    page_icon=":material/shield:",
    layout="wide",
)

pages = {
    "Explore": [
        st.Page(
            "app_pages/decision_workflow.py",
            title="Decision Workflow",
            icon=":material/assignment_turned_in:",
        ),
        st.Page(
            "app_pages/disaster_assistant.py",
            title="Disaster Intelligence Assistant",
            icon=":material/psychology_alt:",
        ),
        st.Page(
            "app_pages/kochi_map.py",
            title="Kochi Map",
            icon=":material/map:",
        ),
        st.Page(
            "app_pages/air_pollution.py",
            title="Air Pollution",
            icon=":material/factory:",
        ),
        st.Page(
            "app_pages/data_readiness.py",
            title="Data Readiness",
            icon=":material/fact_check:",
        ),
        st.Page(
            "app_pages/hazard_model_lab.py",
            title="Hazard Model Lab",
            icon=":material/model_training:",
        ),
        st.Page(
            "app_pages/hospital_vulnerability.py",
            title="Hospital Vulnerability",
            icon=":material/local_hospital:",
        ),
        st.Page(
            "app_pages/compound_scenario.py",
            title="Cyclone + Flood",
            icon=":material/thunderstorm:",
        ),
        st.Page(
            "app_pages/disaster_probability.py",
            title="Disaster Probability",
            icon=":material/analytics:",
        ),
    ],
    "Home": [
        st.Page(
            "app_pages/home.py",
            title="Command Centre",
            icon=":material/dashboard:",
        ),
    ],
    "Plan": [
        st.Page(
            "app_pages/mitigation_planner.py",
            title="Mitigation Budget",
            icon=":material/account_balance_wallet:",
        ),
        st.Page(
            "app_pages/smart_mitigation_design.py",
            title="Smart Mitigation Design Studio",
            icon=":material/engineering:",
        ),
    ],
}

page = st.navigation(pages, position="top")

# A lightweight visual system shared by every page. Keep this CSS local to the
# Streamlit app so the deployment needs no external assets or build step.
st.markdown(
    """
    <style>
:root {
 --ar-bg:#061522; --ar-panel:#102b3c; --ar-ink:#e7f5f5; --ar-muted:#a7c1c8;
 --ar-teal:#42e0c1; --ar-cyan:#56c8e8; --ar-border:rgba(130,190,199,.24);
}
html,body,[data-testid="stAppViewContainer"] {background:#061522 !important;}
.stApp {color:var(--ar-ink)!important;background:
 radial-gradient(ellipse at 8% 4%,rgba(28,190,169,.19),transparent 31rem),
 radial-gradient(ellipse at 92% 12%,rgba(47,137,190,.17),transparent 34rem),
 radial-gradient(ellipse at 52% 100%,rgba(34,116,115,.11),transparent 38rem),
 repeating-radial-gradient(ellipse at 85% 18%,transparent 0 34px,rgba(126,208,202,.035) 35px 36px,transparent 37px 72px),
 linear-gradient(145deg,#061522 0%,#0a2030 48%,#071925 100%)!important;background-attachment:fixed!important;}
.block-container{padding-top:1.45rem;padding-bottom:3.5rem;max-width:1500px;}
[data-testid="stHeader"],[data-testid="stToolbar"]{background:rgba(6,21,34,.76)!important;}
[data-testid="stSidebar"]{background:rgba(7,25,39,.96)!important;border-right:1px solid var(--ar-border);}
[data-testid="stSidebar"] *{color:var(--ar-ink);}
[data-testid="stAppViewContainer"]>.main,[data-testid="stMain"]{background:transparent!important;}
h1,h2,h3,h4,h5,h6{color:#effafa!important;letter-spacing:-.025em;}
p,li,label,.stMarkdown,.stCaption,[data-testid="stWidgetLabel"]{color:#c5dadd;}
[data-testid="stMetric"]{background:linear-gradient(145deg,rgba(17,48,66,.96),rgba(10,34,49,.96))!important;border:1px solid var(--ar-border)!important;padding:1rem 1.05rem;border-radius:17px;box-shadow:0 18px 48px rgba(0,0,0,.22);}
[data-testid="stMetricLabel"]{color:#9fc0c8!important;}[data-testid="stMetricValue"]{color:#f0ffff!important;font-weight:780;}
[data-testid="stMetricDelta"]{color:var(--ar-teal)!important;}
[data-testid="stExpander"]{background:rgba(12,35,51,.72)!important;border:1px solid var(--ar-border)!important;border-radius:15px;}
[data-testid="stExpander"] summary,[data-testid="stExpander"] summary p{color:#e5f4f4!important;}
[data-baseweb="select"]>div,[data-baseweb="input"]>div,[data-baseweb="textarea"]>div,[data-testid="stDateInput"] input,[data-testid="stNumberInput"] input,[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea{background:#102b3c!important;color:#eaf7f7!important;border-color:rgba(130,190,199,.34)!important;border-radius:11px!important;}
[data-baseweb="popover"],[data-baseweb="menu"],[role="listbox"]{background:#102b3c!important;color:#eaf7f7!important;}
[data-baseweb="menu"] *,[role="option"]{color:#eaf7f7!important;}
[data-testid="stRadio"] label,[data-testid="stCheckbox"] label{color:#d5e7e8!important;}
[data-testid="stDataFrame"],[data-testid="stTable"]{border:1px solid var(--ar-border);border-radius:13px;overflow:hidden;background:rgba(12,35,51,.8);}
[data-testid="stTabs"] button{color:#a9c9ce!important;}
[data-testid="stTabs"] button[aria-selected="true"]{color:#58e1c5!important;border-bottom-color:#42e0c1!important;}
div.stButton>button,div.stDownloadButton>button{border-radius:11px;font-weight:700;min-height:2.7rem;border:1px solid rgba(91,223,200,.42);background:linear-gradient(110deg,#126a70,#147c83);color:#f4ffff!important;}
div.stButton>button:hover,div.stDownloadButton>button:hover{border-color:#7bf0d7;background:linear-gradient(110deg,#16817e,#168b91);color:#fff!important;}
hr{border-color:rgba(130,190,199,.22)!important;}a{color:#62dfd0!important;}
.ar-hero{position:relative;overflow:hidden;border-radius:25px;padding:clamp(1.5rem,3vw,2.6rem);margin:.25rem 0 1.25rem;color:#fff;background:linear-gradient(118deg,#092032 0%,#07516a 55%,#087e78 100%);border:1px solid rgba(120,220,208,.25);box-shadow:0 22px 54px rgba(0,0,0,.26);}
.ar-hero:after{content:"";position:absolute;width:310px;height:310px;right:-95px;top:-155px;border-radius:50%;border:1px solid rgba(255,255,255,.22);box-shadow:0 0 0 34px rgba(255,255,255,.045),0 0 0 70px rgba(255,255,255,.035);}
.ar-eyebrow{color:#8cf3df;text-transform:uppercase;letter-spacing:.15em;font-size:.76rem;font-weight:800;margin-bottom:.8rem;}
.ar-hero h1{color:white;font-size:clamp(2.1rem,4vw,3.35rem);line-height:1.05;margin:0 0 .8rem;}
.ar-hero p{color:#d9f3f1;font-size:1.04rem;max-width:760px;line-height:1.65;margin:0;}
.ar-chip{display:inline-block;margin-top:1.25rem;margin-right:.4rem;border:1px solid rgba(255,255,255,.28);background:rgba(255,255,255,.10);color:#fff;padding:.35rem .7rem;border-radius:999px;font-size:.78rem;}
.ar-section-label{color:#55e1ca;font-size:.76rem;text-transform:uppercase;letter-spacing:.12em;font-weight:800;margin-bottom:.25rem;}

/* Readability guard for native Streamlit text blocks.
   Keep custom HTML hero/cards untouched; only style standard rendered statements. */
[data-testid="stMarkdownContainer"] > p,
[data-testid="stMarkdownContainer"] > ul,
[data-testid="stMarkdownContainer"] > ol,
[data-testid="stMarkdownContainer"] > blockquote,
[data-testid="stMarkdownContainer"] > h1,
[data-testid="stMarkdownContainer"] > h2,
[data-testid="stMarkdownContainer"] > h3,
[data-testid="stMarkdownContainer"] > h4,
[data-testid="stMarkdownContainer"] > h5,
[data-testid="stMarkdownContainer"] > h6 {
  color: #dcebed !important;
}
[data-testid="stMarkdownContainer"] > ul li,
[data-testid="stMarkdownContainer"] > ol li,
[data-testid="stMarkdownContainer"] > blockquote p {
  color: #dcebed !important;
}
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p,
.stCaption,
.stCaption p {
  color: #b9d0d5 !important;
}
[data-testid="stAlert"] [data-testid="stMarkdownContainer"] p,
[data-testid="stAlert"] [data-testid="stMarkdownContainer"] li {
  color: #e3f0f2 !important;
}
[data-testid="stMarkdownContainer"] > blockquote {
  border-left-color: #42e0c1 !important;
}
[data-testid="stMarkdownContainer"] > pre,
[data-testid="stMarkdownContainer"] > p code {
  color: #eaf7f7 !important;
  background: rgba(18, 48, 65, .92) !important;
}
[data-testid="stMarkdownContainer"] > table th,
[data-testid="stMarkdownContainer"] > table td {
  color: #dcebed !important;
}

@media(max-width:640px){.block-container{padding-left:1rem;padding-right:1rem;}.ar-hero{border-radius:18px;}}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{scroll-behavior:auto!important;transition-duration:.01ms!important;}}
</style>
    """,
    unsafe_allow_html=True,
)
if not st.session_state.get("ar_entered_platform", False):
    st.markdown(
        """
        <style>
        [data-testid="stNavigation"] { display: none !important; }
        .block-container { max-width: 1320px; padding-top: 2.4rem; }
        .ar-cover { position:relative; overflow:hidden; min-height:590px; display:flex; flex-direction:column; justify-content:center; padding:clamp(2rem,6vw,5.4rem); border:1px solid rgba(125,224,215,.24); border-radius:30px; background:radial-gradient(circle at 82% 25%,rgba(57,209,195,.24),transparent 24rem),radial-gradient(circle at 12% 92%,rgba(40,133,180,.22),transparent 28rem),linear-gradient(125deg,#061522 0%,#0b3044 52%,#075b62 100%); box-shadow:0 30px 90px rgba(0,0,0,.32); }
        .ar-cover:before { content:""; position:absolute; inset:0; opacity:.3; background:repeating-linear-gradient(0deg,transparent 0 39px,rgba(156,225,224,.10) 40px),repeating-linear-gradient(90deg,transparent 0 39px,rgba(156,225,224,.10) 40px); mask-image:linear-gradient(90deg,transparent,black); pointer-events:none; }
        .ar-cover:after { content:""; position:absolute; width:420px;height:420px;right:-100px;top:8%;border:1px solid rgba(132,235,221,.35);border-radius:50%;box-shadow:0 0 0 38px rgba(132,235,221,.045),0 0 0 82px rgba(132,235,221,.035),0 0 0 130px rgba(132,235,221,.025); pointer-events:none; }
        .ar-cover-content { position:relative;z-index:1;max-width:780px; }
        .ar-cover-kicker { color:#8cf3df;font-size:.78rem;font-weight:800;letter-spacing:.19em;text-transform:uppercase;margin-bottom:1.3rem; }
        .ar-cover h1 { color:#f4ffff!important;font-size:clamp(2.8rem,7vw,5.7rem);line-height:.98;letter-spacing:-.055em;margin:0 0 1.15rem; }
        .ar-cover h1 span { color:#63e5d0; }
        .ar-cover-lead { color:#d7eeee;font-size:clamp(1.05rem,2vw,1.3rem);line-height:1.65;max-width:700px; }
        .ar-cover-meta { display:flex;flex-wrap:wrap;gap:.6rem;margin-top:1.7rem; }
        .ar-cover-meta span { color:#e4f8f5;border:1px solid rgba(190,245,235,.25);background:rgba(255,255,255,.07);padding:.48rem .8rem;border-radius:999px;font-size:.78rem; }
        .ar-cover-foot { position:relative;z-index:1;display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap;margin-top:3.5rem;padding-top:1.2rem;border-top:1px solid rgba(210,245,240,.18);color:#a9c9ce;font-size:.78rem;letter-spacing:.04em; }
        div.stButton > button { min-height:3.2rem;padding:0 1.6rem;font-size:1rem;border-radius:13px; }
        @media(max-width:640px){.ar-cover{min-height:620px;border-radius:20px;padding:1.6rem}.ar-cover:after{right:-260px;top:10%}.ar-cover-foot{margin-top:2rem}}
        </style>
        <section class="ar-cover">
          <div class="ar-cover-content">
            <div class="ar-cover-kicker">KOCHI · CLIMATE INTELLIGENCE · SDG 11 + SDG 13</div>
            <h1>AI <span>RESILIENCE</span></h1>
            <p class="ar-cover-lead"><strong>Building safer, smarter, more resilient cities.</strong><br>
            An AI-assisted urban disaster-risk assessment and climate resilience platform for Kochi — bringing hazard evidence, exposure insights and practical response priorities into one place.</p>
            <div class="ar-cover-meta">
              <span>Evidence-led risk assessment</span><span>Multi-hazard intelligence</span><span>Action-oriented planning</span>
            </div>
          </div>
          <div class="ar-cover-foot">
            <span>INTELLIGENT CITIES · RESILIENT FUTURES</span>
            <span>SCENARIO ASSESSMENT · NOT AN EMERGENCY WARNING SYSTEM</span>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Explore the Platform  →", type="primary", use_container_width=False):
        st.session_state["ar_entered_platform"] = True
        st.rerun()
    st.stop()

st.markdown(
    """
    <div style="display:flex;align-items:center;gap:.55rem;margin:.1rem 0 1rem;color:#a7c1c8;font-size:.82rem">
      <span style="display:inline-block;width:.55rem;height:.55rem;border-radius:50%;background:#42e0c1"></span>
      <span><strong style="color:#e7f5f5">AI RESILIENCE</strong> · KOCHI CLIMATE INTELLIGENCE · INTELLIGENT CITIES, RESILIENT FUTURES</span>
    </div>
    """,
    unsafe_allow_html=True,
)

page.run()
