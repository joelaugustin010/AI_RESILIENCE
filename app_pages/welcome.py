"""Public-facing welcome cover for the AI RESILIENCE platform."""

import streamlit as st

st.markdown(
    """
    <style>
    .block-container {max-width: 1320px; padding-top: 2rem; padding-bottom: 2.5rem;}
    .ar-cover {
      position:relative; isolation:isolate; overflow:hidden;
      min-height:510px; display:grid; grid-template-columns:minmax(0,1.25fr) minmax(260px,.75fr);
      gap:2rem; align-items:center; padding:clamp(2rem,5vw,4.5rem);
      border:1px solid rgba(139,235,222,.28); border-radius:30px;
      background:linear-gradient(90deg,rgba(4,18,28,.96) 0%,rgba(7,35,47,.78) 58%,rgba(7,34,43,.86) 100%),url('app/static/images/hero-kerala-ghats.jpg') center/cover no-repeat;
      box-shadow:0 28px 80px rgba(0,0,0,.32);
    }
    .ar-cover:before {
      content:""; position:absolute; inset:0; z-index:-1; opacity:.19;
      background-image:linear-gradient(rgba(255,255,255,.12) 1px,transparent 1px),
        linear-gradient(90deg,rgba(255,255,255,.12) 1px,transparent 1px);
      background-size:42px 42px;
      mask-image:linear-gradient(110deg,black,transparent 82%);
    }
    .ar-cover-kicker {color:#9cf4e2;text-transform:uppercase;letter-spacing:.18em;font-size:.76rem;font-weight:850;margin-bottom:1rem;}
    .ar-cover-title {color:#fff!important;font-size:clamp(3rem,7vw,5.8rem)!important;line-height:.96!important;letter-spacing:-.06em!important;font-weight:900!important;margin:0 0 1.15rem!important;}
    .ar-cover-subtitle {color:#d6f5f0;font-size:clamp(1.1rem,2vw,1.45rem);font-weight:650;line-height:1.45;max-width:680px;margin-bottom:1rem;}
    .ar-cover-copy {color:#d0e5e8;font-size:1rem;line-height:1.8;max-width:680px;margin-bottom:1.5rem;}
    .ar-cover-tag {display:inline-block;margin:.2rem .35rem .2rem 0;padding:.42rem .78rem;border:1px solid rgba(255,255,255,.25);border-radius:999px;background:rgba(255,255,255,.09);color:#f0fdfa;font-size:.78rem;}
    .ar-cover-visual {min-height:300px;display:flex;align-items:center;justify-content:center;position:relative;}
    .ar-globe {width:min(29vw,300px);height:min(29vw,300px);min-width:220px;min-height:220px;border-radius:50%;position:relative;border:1px solid rgba(166,243,240,.55);background:radial-gradient(circle at 50% 50%,rgba(69,225,204,.2),rgba(15,70,90,.12) 48%,transparent 70%),repeating-radial-gradient(circle,transparent 0 27px,rgba(166,243,240,.2) 28px 29px),linear-gradient(135deg,rgba(255,255,255,.08),rgba(255,255,255,0));box-shadow:inset 0 0 50px rgba(69,225,204,.12),0 0 65px rgba(69,225,204,.12);}
    .ar-globe:before,.ar-globe:after {content:"";position:absolute;border:1px solid rgba(166,243,240,.28);border-radius:50%;inset:15% 30%;}
    .ar-globe:after {inset:30% 15%;}
    .ar-globe-dot {position:absolute;left:64%;top:28%;width:12px;height:12px;border-radius:50%;background:#a5f3e4;box-shadow:0 0 0 9px rgba(165,243,228,.14),0 0 24px #5eead4;}
    .ar-cover-caption {position:absolute;bottom:4px;color:#b9e8e5;font-size:.7rem;letter-spacing:.17em;text-transform:uppercase;text-align:center;width:100%;}
    .ar-cover-footer {color:#9fbfc6;font-size:.8rem;line-height:1.7;text-align:center;margin-top:1.2rem;}
    .ar-cover-section {margin:1.5rem 0 .45rem;color:#58e1ca;font-size:.74rem;text-transform:uppercase;letter-spacing:.16em;font-weight:850;}
    @media(max-width:760px){.ar-cover{grid-template-columns:1fr;min-height:0;border-radius:20px}.ar-cover-visual{min-height:220px}.ar-globe{width:220px;height:220px}.ar-cover-title{font-size:3.2rem!important}}
    </style>
    <section class="ar-cover">
      <div>
        <div class="ar-cover-kicker">Kochi · Urban resilience intelligence</div>
        <h1 class="ar-cover-title">AI<br>RESILIENCE</h1>
        <div class="ar-cover-subtitle">Building a safer, more resilient Kochi through evidence-led AI.</div>
        <p class="ar-cover-copy">
          Explore how disaster evidence, geographic information and environmental data
          can support better preparedness decisions. Assess multi-hazard scenarios,
          understand uncertainty and discover practical ways to strengthen urban resilience.
        </p>
        <span class="ar-cover-tag">Evidence-first research</span>
        <span class="ar-cover-tag">Multi-hazard assessment</span>
        <span class="ar-cover-tag">Sustainable cities</span>
      </div>
      <div class="ar-cover-visual" aria-hidden="true">
        <div class="ar-globe"><span class="ar-globe-dot"></span></div>
        <div class="ar-cover-caption">Observe · Assess · Prepare</div>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="ar-cover-section">Explore the platform</div>', unsafe_allow_html=True)
st.subheader("From risk information to preparedness decisions")
st.write(
    "Start with the Decision Workflow to assess a hazard scenario, review the evidence "
    "and examine preparedness priorities. You can also explore the Kochi map and the "
    "supporting research workspaces."
)

left, right = st.columns([1, 1], gap="medium")
with left:
    st.page_link(
        "app_pages/decision_workflow.py",
        label="Explore the Decision Workflow",
        icon=":material/arrow_forward:",
        use_container_width=True,
    )
with right:
    st.page_link(
        "app_pages/home.py",
        label="Open the Command Centre",
        icon=":material/dashboard:",
        use_container_width=True,
    )

st.markdown('<div class="ar-cover-footer">A student research prototype · Conceptually aligned with UN Sustainable Development Goals 6, 9, 11 and 13<br>Not an official warning system. For emergencies, follow KSDMA, IMD and district-administration guidance.</div>', unsafe_allow_html=True)
