"""Environmental intelligence landing page for AI_RESILIENCE."""

from __future__ import annotations

import streamlit as st


st.markdown(
    """
    <style>
    .ar-home-hero { position:relative; isolation:isolate; overflow:hidden; min-height:clamp(560px,66vh,760px); display:flex; align-items:flex-end; padding:clamp(1.5rem,5vw,4.3rem); margin:.2rem 0 2rem; border-radius:30px; color:#fff; background:linear-gradient(90deg,rgba(8,30,27,.94),rgba(8,35,34,.55) 58%,rgba(8,35,34,.18)),url('app/static/videos/kochi-hero-poster.jpg') center/cover; box-shadow:0 26px 70px rgba(21,70,53,.22); }
    .ar-home-hero:before { content:""; position:absolute; inset:0; z-index:-1; background:linear-gradient(90deg,rgba(5,24,22,.9),rgba(5,24,22,.36) 62%,rgba(5,24,22,.55)),linear-gradient(180deg,transparent 38%,rgba(5,24,22,.72)); }
    .ar-home-hero-content { position:relative; z-index:3; max-width:780px; animation:home-rise .6s ease-out both; }
    .ar-home-video { position:absolute; inset:0; z-index:-3; width:100%; height:100%; object-fit:cover; object-position:center; filter:saturate(.9) contrast(1.04); transition:opacity 1.4s ease-in-out; }
    .ar-home-video-caption { position:absolute; right:1.4rem; bottom:1.3rem; z-index:3; color:rgba(235,250,241,.78); font-size:.68rem; letter-spacing:.11em; text-transform:uppercase; }
    .ar-home-kicker,.ar-home-overline { text-transform:uppercase; letter-spacing:.16em; font-size:.71rem; font-weight:800; }
    .ar-home-kicker { color:#b9e8d2; margin-bottom:1rem; }
    .ar-home-photo { position:absolute; inset:0; z-index:-2; background-position:center; background-size:cover; opacity:0; transform:scale(1.045); animation:ar-photo-cycle 40s linear infinite; will-change:opacity,transform; }
    .ar-home-photo:nth-of-type(2) { animation-delay:-5s; }
    .ar-home-photo:nth-of-type(3) { animation-delay:-10s; }
    .ar-home-photo:nth-of-type(4) { animation-delay:-15s; }
    .ar-home-photo:nth-of-type(5) { animation-delay:-20s; }
    .ar-home-photo:nth-of-type(6) { animation-delay:-25s; }
    .ar-home-photo:nth-of-type(7) { animation-delay:-30s; }
    .ar-home-photo:nth-of-type(8) { animation-delay:-35s; }
    .ar-home-photo.is-active { opacity:1; }
    .ar-home-hero .ar-home-title { color:#fff!important; font-size:clamp(52px,10vw,118px)!important; font-weight:900!important; letter-spacing:-.075em!important; line-height:.88!important; text-shadow:0 5px 28px rgba(0,0,0,.32); margin:0 0 1rem!important; }
    .ar-home-lede { color:#e5f2e9; max-width:650px; font-size:clamp(1rem,1.8vw,1.23rem); line-height:1.7; margin:0 0 1.4rem; }
    .ar-home-support { color:rgba(239,251,243,.9); max-width:620px; font-size:clamp(.92rem,1.35vw,1.08rem); line-height:1.65; margin:-.65rem 0 1.5rem; }
    .ar-home-pills { display:flex; flex-wrap:wrap; gap:.5rem; }
    .ar-home-pill { padding:.42rem .72rem; border-radius:999px; color:#edfff5; border:1px solid rgba(212,247,227,.28); background:rgba(13,55,45,.45); backdrop-filter:blur(8px); font-size:.78rem; }
    .ar-home-section { margin:2.2rem 0; }
    .ar-home-overline { color:#247a65; margin-bottom:.35rem; }
    .ar-home-section h2 { color:#203c35!important; margin:0 0 .45rem!important; font-size:clamp(1.45rem,3vw,2.15rem)!important; letter-spacing:-.04em!important; }
    .ar-home-section-copy { color:#5d756c; max-width:760px; line-height:1.65; margin:0 0 1.1rem; }
    .ar-domain-card { min-height:248px; overflow:hidden; position:relative; display:flex; flex-direction:column; justify-content:flex-end; padding:1.15rem; border-radius:19px; color:#fff; background:linear-gradient(180deg,rgba(7,24,22,.02),rgba(7,25,23,.88)),var(--domain-image) center/cover; box-shadow:0 12px 30px rgba(24,73,55,.12); transition:transform .2s ease,box-shadow .2s ease; }
    .ar-domain-card:hover { transform:translateY(-4px); box-shadow:0 20px 40px rgba(24,73,55,.2); }
    .ar-domain-card h3 { color:#fff!important; font-size:1.08rem; margin:0 0 .25rem; }
    .ar-domain-card p { color:#e4f4ea!important; font-size:.82rem; line-height:1.45; margin:0; }
    .ar-domain-icon { font-size:1.45rem; margin-bottom:auto; }
    .ar-domain-link { margin-top:.7rem; color:#c8f2dc!important; font-weight:750; font-size:.78rem; }
    .ar-spotlight { display:grid; grid-template-columns:1.2fr .8fr; gap:1rem; }
    .ar-spotlight-card { border:1px solid rgba(33,91,69,.16); border-radius:20px; padding:1.25rem; background:rgba(255,255,255,.78); box-shadow:0 9px 26px rgba(24,73,55,.06); }
    .ar-spotlight-card h3 { color:#173f35!important; margin:0 0 .45rem; }
    .ar-spotlight-card p,.ar-spotlight-card li { color:#5d756c; line-height:1.6; }
    .ar-action { border-radius:23px; padding:clamp(1.2rem,3vw,2rem); color:#eefaf1; background:linear-gradient(125deg,#173f35,#247a65 62%,#3b8d7a); }
    .ar-action h2 { color:#fff!important; margin-top:0!important; }
    .ar-action p { color:#d8eee0; line-height:1.65; max-width:760px; }
    .ar-transparency { display:flex; align-items:center; justify-content:space-between; gap:1rem; border:1px solid rgba(33,91,69,.16); border-radius:16px; padding:1rem 1.1rem; background:rgba(255,255,255,.55); }
    .ar-transparency strong { color:#173f35; }
    .ar-transparency span { color:#5d756c; font-size:.84rem; }
    .ar-sdg-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.85rem; margin-top:1rem; }
    .ar-sdg-card { position:relative; overflow:hidden; min-height:150px; padding:1.05rem 1.1rem 1rem; border-radius:20px; color:#fff; background:linear-gradient(135deg,var(--sdg-deep),var(--sdg-light)); box-shadow:0 12px 28px rgba(24,73,55,.12); transition:transform .2s ease,box-shadow .2s ease; }
    .ar-sdg-card:hover { transform:translateY(-4px); box-shadow:0 18px 36px rgba(24,73,55,.2); }
    .ar-sdg-card:after { content:""; position:absolute; width:130px; height:130px; right:-35px; top:-52px; border-radius:50%; background:rgba(255,255,255,.16); }
    .ar-sdg-number { position:relative; z-index:1; font-size:1.65rem; font-weight:900; letter-spacing:-.06em; }
    .ar-sdg-label { position:relative; z-index:1; display:block; margin-top:.18rem; font-size:.82rem; font-weight:850; letter-spacing:.03em; }
    .ar-sdg-copy { position:relative; z-index:1; margin:.55rem 0 0; color:rgba(255,255,255,.88); font-size:.78rem; line-height:1.45; }
    .ar-sdg-note { margin:.9rem 0 0; color:#5d756c; font-size:.78rem; line-height:1.55; }
    .ar-module-note { margin:0 0 1rem; padding:.78rem 1rem; border-left:4px solid #299b91; border-radius:0 14px 14px 0; color:#365b50; background:linear-gradient(90deg,rgba(41,155,145,.1),rgba(255,255,255,.45)); line-height:1.55; }
    @keyframes home-rise { from{opacity:0;transform:translateY(14px)} to{opacity:1;transform:none} }
    @keyframes ar-photo-cycle { 0%,12%{opacity:1;transform:scale(1)} 20%,100%{opacity:0;transform:scale(1.045)} }
    @media(max-width:760px){.ar-home-hero{min-height:560px;border-radius:22px}.ar-home-video-caption{right:1rem;bottom:1rem}.ar-spotlight{grid-template-columns:1fr}.ar-transparency{align-items:flex-start;flex-direction:column}.ar-sdg-grid{grid-template-columns:1fr 1fr}}
    @media(max-width:480px){.ar-sdg-grid{grid-template-columns:1fr}}
    @media(prefers-reduced-motion:reduce){.ar-home-video{display:none}.ar-home-photo{animation:none!important;opacity:0!important;transform:none!important}.ar-home-photo:first-of-type{opacity:1!important}.ar-home-hero-content,.ar-domain-card{animation:none;transition:none}}
    </style>
    <link rel="preload" as="image" href="app/static/images/kochi/waterfront.jpg">
    <div class="ar-home">
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <section class="ar-home-hero" aria-label="AI RESILIENCE environmental intelligence">
      <div class="ar-home-photo is-active" style="background-image:url('app/static/images/kochi/waterfront.jpg')" aria-hidden="true"></div>
      <div class="ar-home-photo" style="background-image:url('app/static/images/kochi/backwaters.jpg')" aria-hidden="true"></div>
      <div class="ar-home-photo" style="background-image:url('app/static/images/kochi/mangalavanam.jpg')" aria-hidden="true"></div>
      <div class="ar-home-photo" style="background-image:url('app/static/images/kochi/fishing-nets.jpg')" aria-hidden="true"></div>
      <div class="ar-home-photo" style="background-image:url('app/static/images/kochi/coast.jpg')" aria-hidden="true"></div>
      <div class="ar-home-photo" style="background-image:url('app/static/images/kochi/water-metro.jpg')" aria-hidden="true"></div>
      <div class="ar-home-photo" style="background-image:url('app/static/images/kochi/industrial-coast.jpg')" aria-hidden="true"></div>
      <div class="ar-home-photo" style="background-image:url('app/static/images/kochi/maradu.jpg')" aria-hidden="true"></div>
      <video class="ar-home-video" id="ar-hero-video" autoplay muted playsinline preload="metadata" poster="app/static/videos/kochi-hero-poster.jpg" aria-hidden="true">
        <source src="app/static/videos/kochi-chinese-fishing-nets-480p.webm" type="video/webm">
      </video>
      <div class="ar-home-hero-content">
        <div class="ar-home-kicker">Kerala · Kochi · Evidence-led resilience</div>
        <h1 class="ar-home-title">AI<br>RESILIENCE</h1>
        <p class="ar-home-lede">Understanding our environment. Protecting our future.</p>
        <p class="ar-home-support">Explore environmental signals, understand disaster vulnerability and turn trusted evidence into practical resilience decisions for Kerala.</p>
        <div class="ar-home-pills"><span class="ar-home-pill">Environmental intelligence</span><span class="ar-home-pill">Multi-hazard context</span><span class="ar-home-pill">Transparent evidence</span></div>
      </div>
      <div class="ar-home-video-caption" id="ar-hero-caption">Fort Kochi · Chinese fishing nets · CC BY 3.0</div>
    </section>
    <script>
    (() => {
      const video = document.getElementById('ar-hero-video');
      const caption = document.getElementById('ar-hero-caption');
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
      if (!video) return;
      const sequence = [
        ['app/static/videos/kochi-chinese-fishing-nets-480p.webm', 'Fort Kochi · Chinese fishing nets · CC BY 3.0'],
        ['app/static/videos/vembanad-boat-480p.webm', 'Vembanad Lake · Kerala backwaters · CC BY-SA 3.0'],
        ['app/static/videos/kerala-flood-2018-480p.webm', 'Kerala flood context · Angamaly · CC BY-SA 4.0']
      ];
      let index = 0;
      const advance = () => {
        index = (index + 1) % sequence.length;
        video.style.opacity = '0';
        window.setTimeout(() => {
          video.src = sequence[index][0];
          caption.textContent = sequence[index][1];
          video.load();
          video.play().catch(() => {});
          video.style.opacity = '1';
        }, 1400);
      };
      video.addEventListener('ended', advance);
      video.addEventListener('error', () => { video.style.opacity = '0'; });
    })();
    </script>
    """,
    unsafe_allow_html=True,
)

st.markdown('<section class="ar-home-section"><div class="ar-home-overline">Explore the intelligence platform</div><h2>One landscape. Many ways to understand it.</h2><p class="ar-home-section-copy">Move from environmental observation to scenario assessment, evidence review and practical planning through the existing AI_RESILIENCE workspaces.</p><div class="ar-module-note"><strong>Choose your starting point:</strong> monitor a signal, inspect a place, ask the assistant, or test a documented hazard workflow.</div></section>', unsafe_allow_html=True)

domains = [
    ("🌬️", "Air & atmosphere", "Review monitored air-quality evidence, pollutant context and research readiness.", "kochi/coast.jpg", "app_pages/air_pollution.py", ":material/air:"),
    ("🌊", "Water & flood risk", "Explore Kochi layers, flood context and the evidence behind water-related risk.", "kochi/backwaters.jpg", "app_pages/kochi_map.py", ":material/water:"),
    ("🌿", "Climate & ecosystems", "Connect climate context, land, biodiversity and resilience planning questions.", "kochi/mangalavanam.jpg", "app_pages/disaster_probability.py", ":material/eco:"),
    ("🏥", "Public health", "Review hospital vulnerability and accessibility evidence for critical facilities.", "kochi/water-metro.jpg", "app_pages/hospital_vulnerability.py", ":material/local_hospital:"),
    ("⛰️", "Hazards & scenarios", "Assess hazards transparently and inspect uncertainty before interpreting outputs.", "kochi/maradu.jpg", "app_pages/decision_workflow.py", ":material/landslide:"),
    ("🛠️", "Mitigation & action", "Turn evidence into budget-aware mitigation concepts and planning workflows.", "kochi/industrial-coast.jpg", "app_pages/mitigation_planner.py", ":material/engineering:"),
    ("🧠", "AI disaster assistant", "Ask natural-language questions grounded in reviewed project evidence and visible sources.", "kochi/fishing-nets.jpg", "app_pages/disaster_assistant.py", ":material/psychology_alt:"),
    ("🧪", "Hazard model lab", "Inspect model inputs, readiness gates and limitations across the available hazard workflows.", "kochi/industrial-coast.jpg", "app_pages/hazard_model_lab.py", ":material/model_training:"),
    ("🌧️", "Compound hazards", "Explore cyclone and flood scenario context while keeping assumptions and uncertainty visible.", "kochi/waterfront.jpg", "app_pages/compound_scenario.py", ":material/thunderstorm:"),
]
for start in range(0, len(domains), 3):
    columns = st.columns(3, gap="medium")
    for column, (icon, title, copy, image, route, page_icon) in zip(columns, domains[start:start + 3]):
        with column:
            route_name = route.rsplit("/", 1)[-1].removesuffix(".py")
            st.markdown(f'<article class="ar-domain-card" style="--domain-image:url(\'app/static/images/{image}\')"><div class="ar-domain-icon">{icon}</div><h3>{title}</h3><p>{copy}</p><a class="ar-domain-link" href="/{route_name}">Explore workspace →</a></article>', unsafe_allow_html=True)
            st.page_link(route, label=f"Open {title}", icon=page_icon, use_container_width=True)

st.markdown('<section class="ar-home-section"><div class="ar-home-overline">Kerala environmental spotlight</div><h2>Start with place, context and evidence.</h2></section>', unsafe_allow_html=True)
left, right = st.columns((1.15, .85), gap="large")
with left:
    st.markdown('<div class="ar-spotlight-card"><h3>Ernakulam and Kochi</h3><p>The application brings together local maps, hazard scenarios, air-quality evidence, hospital context and mitigation planning. Use each module to understand what is known, what is estimated and where evidence is still missing.</p><ul><li>Explore spatial layers and their validation notes.</li><li>Review source-backed hazard and air-quality context.</li><li>Use the assistant for natural-language questions grounded in reviewed project records.</li></ul></div>', unsafe_allow_html=True)
with right:
    st.markdown('<div class="ar-spotlight-card"><h3>Evidence before certainty</h3><p>Historical observations, research baselines and scenario outputs are not official warnings or live measurements. The platform keeps provenance, limitations and validation status visible alongside the analysis.</p></div>', unsafe_allow_html=True)

st.markdown('<section class="ar-home-section"><div class="ar-action"><div class="ar-home-overline" style="color:#b9e8d2">From insight to action</div><h2>Plan for a more resilient tomorrow.</h2><p>Build a scenario, inspect its evidence gate, compare mitigation options and record the assumptions behind a decision. For active emergencies, follow current official guidance from KSDMA, IMD and local authorities.</p></div></section>', unsafe_allow_html=True)
st.markdown('<section class="ar-home-section"><div class="ar-home-overline">Sustainable development</div><h2>Six goals. Six practical pathways.</h2><p class="ar-home-section-copy">The platform connects local environmental evidence with themes that matter for healthier communities, resilient infrastructure, climate action and protected ecosystems. These are thematic contributions—not official certification, partnerships or impact claims.</p></section>', unsafe_allow_html=True)
sdgs = [
    ("SDG 3", "Good Health & Well-being", "Hospital vulnerability and preparedness context", "#b73543", "#e76f51"),
    ("SDG 6", "Clean Water & Sanitation", "Flood, drainage and water-related evidence", "#146c94", "#2aa7c9"),
    ("SDG 9", "Industry & Infrastructure", "Infrastructure context and mitigation planning", "#a65d16", "#d68b2d"),
    ("SDG 11", "Sustainable Cities", "Kochi mapping and urban resilience workflows", "#b64b25", "#db7b3d"),
    ("SDG 13", "Climate Action", "Climate and hazard questions with uncertainty visible", "#4f7d38", "#79a94b"),
    ("SDG 15", "Life on Land", "Wetlands, green spaces and ecosystem context", "#3a6b3d", "#72a85b"),
]
st.markdown('<div class="ar-sdg-grid">' + ''.join(f'<article class="ar-sdg-card" style="--sdg-deep:{deep};--sdg-light:{light}"><div class="ar-sdg-number">{number}</div><span class="ar-sdg-label">{label}</span><p class="ar-sdg-copy">{copy}</p></article>' for number, label, copy, deep, light in sdgs) + '</div><p class="ar-sdg-note">AI_RESILIENCE does not report official SDG indicator progress. Any impact claim requires independently sourced measurements and documented methods.</p>', unsafe_allow_html=True)

st.markdown('<section class="ar-home-section"><div class="ar-transparency"><div><strong>Data &amp; Model Transparency</strong><br><span>Inspect dataset quality, provenance, coverage, validation and known limitations.</span></div></div></section>', unsafe_allow_html=True)
st.page_link("app_pages/data_readiness.py", label="Explore data quality and model readiness", icon=":material/fact_check:", use_container_width=False)
st.markdown('</div>', unsafe_allow_html=True)
