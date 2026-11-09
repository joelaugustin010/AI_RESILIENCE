"""LLM-powered, RAG-grounded disaster intelligence assistant page.

Answers are generated live by the configured language-model provider.  The page
stores conversation history, streams tokens, shows retrieved project evidence,
and explains configuration or provider errors honestly.  There is no canned
answer fallback.
"""

from __future__ import annotations

import streamlit as st

from src.ui_theme import page_header
from src.disaster_assistant import (
    KnowledgeBaseError,
    LLMConfigurationError,
    LLMRequestError,
    assistant_status,
    load_knowledge,
    prepare_reply,
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    :root {
      --air-forest: #174E55; --air-teal: #299B91; --air-sage: #77B8B2;
      --air-ivory: #F5F7F5; --air-paper: #FFFFFF; --air-charcoal: #17383B;
      --air-muted: #60777A; --air-line: rgba(23,78,85,.16); --air-soft: #DCE7E8;
    }
    html, body, [class*="css"] { font-family: 'Inter', system-ui, -apple-system, sans-serif; }
    .stApp { background: radial-gradient(circle at 100% 0%, rgba(119,184,178,.16) 0, transparent 32rem), linear-gradient(180deg, #F5F7F5 0%, #EFF4F2 100%); color: var(--air-charcoal); }
    .block-container { max-width: 1120px; padding: 2.3rem 2rem 3rem; }
    [data-testid="stHeader"] { background: transparent; }
    /* Keep this page's conversation controls visually aligned with the
       shared Coastal Intelligence navigation instead of overriding it. */
    [data-testid="stSidebar"] {
      background: linear-gradient(180deg, #E7F0EF 0%, #F5F7F5 58%, #FFFFFF 100%);
      border-right: 1px solid rgba(23,78,85,.15);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
      color: #526B6E !important;
    }
    [data-testid="stSidebar"] h3 {
      color: #174E55 !important;
      font-weight: 750;
    }
    [data-testid="stSidebar"] hr { border-color: rgba(23,78,85,.13); }
    [data-testid="stSidebar"] .stButton > button {
      background: rgba(255,255,255,.72);
      border: 1px solid rgba(23,78,85,.16);
      color: #31545A !important;
      text-align: left;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
      background: #DCECE8;
      border-color: rgba(41,155,145,.32);
      color: #174E55 !important;
    }
    h1, h2, h3, h4, p, li, label { color: var(--air-charcoal); }
    h1 { letter-spacing: -.035em; font-weight: 800; }
    /* Shared module hero: preserve high contrast on its dark image-backed surface. */
    .st-key-ar-head-disaster-assistant h1 { color: #f6ffff !important; }
    .st-key-ar-head-disaster-assistant .ar-page-copy { color: #c8dfe2 !important; }
    [data-testid="stChatMessage"] { border: 1px solid var(--air-line); border-radius: 18px; margin: .8rem 0; padding: 1rem 1.1rem; animation: air-rise .32s ease-out both; }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) { background: #DCE7E8; border-color: rgba(23,78,85,.16); margin-left: 12%; }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) { background: var(--air-paper); border-left: 4px solid var(--air-teal); margin-right: 7%; box-shadow: 0 8px 24px rgba(23,78,85,.06); }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] { color: var(--air-charcoal); line-height: 1.75; font-size: .98rem; }
    [data-testid="stChatMessage"] h1, [data-testid="stChatMessage"] h2, [data-testid="stChatMessage"] h3 { color: var(--air-forest); letter-spacing: -.02em; }
    [data-testid="stChatMessage"] code { color: var(--air-forest); background: var(--air-soft); }
    [data-testid="stChatInput"] { background: var(--air-paper); border: 1px solid rgba(23,78,85,.22); border-radius: 16px; box-shadow: 0 8px 24px rgba(41,68,53,.08); }
    [data-testid="stChatInput"] textarea { color: var(--air-charcoal); }
    [data-testid="stChatInput"] textarea::placeholder { color: #708079; opacity: 1; }
    [data-testid="stChatInput"] button { background: var(--air-teal); border: 0; color: white; border-radius: 10px; }
    .air-eyebrow { color: var(--air-teal); font-size: .72rem; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; margin-bottom: .8rem; }
    .air-hero { background: linear-gradient(135deg, #FFFFFF 0%, #DCE7E8 100%); border: 1px solid rgba(23,78,85,.16); border-radius: 24px; padding: 2.3rem 2.5rem 2rem; margin: .4rem 0 1.6rem; }
    .air-hero h2 { color: var(--air-forest); font-size: clamp(1.85rem, 3.5vw, 2.8rem); letter-spacing: -.045em; line-height: 1.08; margin: 0 0 .8rem; }
    .air-hero p { color: #40534a; font-size: 1rem; line-height: 1.7; max-width: 720px; margin: 0; }
    .air-pills { display: flex; flex-wrap: wrap; gap: .55rem; margin-top: 1.35rem; }
    .air-pill { background: rgba(41,155,145,.09); border: 1px solid rgba(23,78,85,.18); border-radius: 999px; color: var(--air-teal); font-size: .78rem; font-weight: 600; padding: .42rem .7rem; }
    .air-status { color: var(--air-teal); font-size: .78rem; font-weight: 700; letter-spacing: .04em; }
    .air-status::before { content: ""; display: inline-block; width: .45rem; height: .45rem; margin-right: .45rem; border-radius: 50%; background: #3d9362; box-shadow: 0 0 0 .22rem rgba(61,147,98,.12); }
    div[data-testid="stExpander"] { background: rgba(255,254,250,.78); border: 1px solid var(--air-line); border-radius: 14px; }
    div[data-testid="stExpander"] p, div[data-testid="stExpander"] li { color: var(--air-charcoal); }
    .stButton > button { border-radius: 11px; transition: transform .18s ease, border-color .18s ease, background .18s ease; }
    .stButton > button:hover { transform: translateY(-1px); border-color: var(--air-teal); background: var(--air-soft); }
    @keyframes air-rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
    @media (max-width: 720px) {
      .block-container { padding: 1.2rem .75rem 2rem; }
      .air-hero { padding: 1.65rem 1.2rem 1.4rem; border-radius: 22px; }
      .air-hero h2 { font-size: 2.15rem; }
      [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) { margin-left: 0; }
      [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) { margin-right: 0; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

page_header(
    "AI RESILIENCE · DISASTER INTELLIGENCE",
    "Environmental Intelligence Assistant",
    "Explore environmental risks, understand disaster vulnerability and discover evidence-based resilience strategies for Kerala.",
    meta=("Kerala & India", "Evidence-aware", "Live generation when configured"),
    accent="teal",
    key="disaster-assistant",
)

try:
    load_knowledge()
except KnowledgeBaseError as exc:
    st.error(f"The reviewed knowledge base could not be loaded: {exc}")
    st.stop()

status = assistant_status()

if "assistant_messages" not in st.session_state:
    st.session_state.assistant_messages = []
if "assistant_pending" not in st.session_state:
    st.session_state.assistant_pending = None

SUGGESTIONS = (
    "What are the major disaster risks in Kerala?",
    "Explain flood vulnerability in Kochi.",
    "What can communities do about industrial air pollution?",
    "How can hospitals prepare for floods?",
    "Explain disaster mitigation to a 10-year-old.",
    "What can the AI_RESILIENCE application do?",
)

EMERGENCY_NOTE = (
    "For an active emergency, call **112** (national emergency response), **108** (ambulance), "
    "or **101** (fire and rescue) now, and follow current KSDMA, IMD and district-administration "
    "instructions. This assistant cannot dispatch help, confirm a rescue, or issue an official warning."
)

# ---------------------------------------------------------------------------
# Configuration gate: never pretend the LLM is available.
# ---------------------------------------------------------------------------
if not status["configured"]:
    st.warning(status["message"])
    st.markdown(
        "The chatbot is **disabled** until a language-model provider is configured. "
        "It will not return canned answers in the meantime."
    )
    with st.expander("Set up the language model", expanded=True):
        st.markdown(status["help"])
    st.warning(EMERGENCY_NOTE)
    st.stop()

st.markdown(
    f'<div class="air-status">ASSISTANT CONNECTED · '
    f'{status["knowledge_topics"]} REVIEWED TOPICS · '
    f'{status["retrieval_chunks"]} PROJECT RECORDS</div>',
    unsafe_allow_html=True,
)

with st.expander("Model, retrieval and safety notes"):
    st.markdown(
        "- **Generation:** every answer is generated live by the configured language model "
        "using the conversation history. There is no fixed response database.\n"
        f"- **RAG:** local TF-IDF retrieval supplies reviewed knowledge and dated module summaries "
        f"from Air Pollution, Disaster Probability, Hospital Vulnerability, Smart Mitigation Design "
        f"and Mitigation Budget. Retrieved sources are shown under each answer.\n"
        "- **Project data limits:** project records may be historical, incomplete or unvalidated. "
        "The assistant is instructed not to present them as live conditions or official forecasts.\n"
        "- **Safety:** active emergencies are directed to 112 / 108 / 101 and official state and "
        "national guidance. The assistant cannot dispatch services.\n"
        "- **Failure policy:** if the provider errors, the page shows the error. It does not "
        "substitute a pre-written answer."
    )

# Conversation actions stay in the page content so the global navigation
# remains identical while moving between workspaces.
conversation_col, action_col = st.columns([3, 1], gap="medium")
with conversation_col:
    st.caption(f"{len(st.session_state.assistant_messages)} messages in this conversation")
with action_col:
    if st.button("New conversation", key="assistant_new_conversation", use_container_width=True):
        st.session_state.assistant_messages = []
        st.session_state.assistant_pending = None
        st.rerun()

if not st.session_state.assistant_messages:
    st.markdown(
        '<div class="air-hero">'
        '<div class="air-eyebrow">READY WHEN YOU ARE</div>'
        '<h2>Turn uncertainty into<br>clearer decisions.</h2>'
        '<p>Ask about hazards, preparedness, mitigation or the AI_RESILIENCE modules. '
        'Every response is generated live and grounded in reviewed project evidence when relevant.</p>'
        '<div class="air-pills"><span class="air-pill">Kerala &amp; India</span>'
        '<span class="air-pill">Floods &amp; landslides</span><span class="air-pill">Hospital resilience</span>'
        '<span class="air-pill">Evidence-aware</span></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="air-section-label">Start with a question</div>', unsafe_allow_html=True)
    prompt_columns = st.columns(2, gap="medium")
    for index, suggestion in enumerate(SUGGESTIONS[:4]):
        with prompt_columns[index % 2]:
            if st.button(suggestion, key=f"welcome_suggestion_{index}", use_container_width=True):
                st.session_state.assistant_pending = suggestion
                st.rerun()

# ---------------------------------------------------------------------------
# Render conversation history
# ---------------------------------------------------------------------------
for message in st.session_state.assistant_messages:
    with st.chat_message(message["role"]):
        st.markdown(message.get("content", ""))
        if message["role"] == "assistant":
            sources = message.get("sources") or []
            evidence = message.get("evidence") or []
            if sources or evidence:
                with st.expander("Retrieved project evidence"):
                    if evidence:
                        st.markdown("**Records used for grounding**")
                        for item in evidence:
                            st.markdown(
                                f"- {item.get('title', 'Project record')} "
                                f"(`{item.get('evidence_status', 'status not stated')}`)"
                            )
                    if sources:
                        st.markdown("**Sources**")
                        for source in sources[:8]:
                            st.markdown(
                                f"- [{source.get('publisher', 'Source')}: "
                                f"{source.get('title', 'Source record')}]({source.get('url', '')})"
                            )
            meta = message.get("meta") or {}
            if meta.get("provider"):
                st.caption("Assistant response · grounded where relevant")

# ---------------------------------------------------------------------------
# Input and streaming response
# ---------------------------------------------------------------------------
typed_prompt = st.chat_input("Ask a disaster, preparedness, or general question…", max_chars=2000)
prompt = typed_prompt or st.session_state.assistant_pending
st.session_state.assistant_pending = None

if prompt:
    question = str(prompt).strip()
    if question:
        history = list(st.session_state.assistant_messages)
        st.session_state.assistant_messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            plan = None
            try:
                plan = prepare_reply(question, history)
            except LLMConfigurationError as exc:
                st.error(f"Language model not configured: {exc}")
                with st.expander("Configuration help", expanded=True):
                    st.markdown(status["help"])
            except Exception as exc:  # defensive: never hide an orchestration bug
                st.error(f"The assistant could not prepare a response: {exc}")

            if plan is not None:
                placeholder = st.empty()
                placeholder.markdown("_Retrieving project evidence and generating an answer…_")
                chunks: list[str] = []
                try:
                    for delta in plan.stream():
                        chunks.append(delta)
                        placeholder.markdown("".join(chunks) + "▌")
                    answer = "".join(chunks).strip()
                    placeholder.markdown(answer)
                    if plan.evidence:
                        st.caption(
                            f"Grounded with {len(plan.evidence)} retrieved project record(s). "
                            "Open the evidence panel below."
                        )
                        with st.expander("Retrieved project evidence"):
                            st.markdown("**Records used for grounding**")
                            for item in plan.evidence:
                                st.markdown(
                                    f"- {item.title} (`{item.evidence_status}`)"
                                )
                            if plan.sources:
                                st.markdown("**Sources**")
                                for source in plan.sources[:8]:
                                    st.markdown(
                                        f"- [{source.get('publisher', 'Source')}: "
                                        f"{source.get('title', 'Source record')}]({source.get('url', '')})"
                                    )
                    st.caption("Assistant response · grounded where relevant")
                    st.session_state.assistant_messages.append(
                        {
                            "role": "assistant",
                            "content": answer,
                            "sources": plan.sources,
                            "evidence": [item.as_dict() for item in plan.evidence],
                            "meta": {"provider": plan.provider, "model": plan.model},
                        }
                    )
                except LLMRequestError as exc:
                    hint = ""
                    if getattr(exc, "status_code", None) == 401:
                        hint = " Check that `LLM_API_KEY` is valid for the selected provider."
                    elif getattr(exc, "status_code", None) == 429:
                        hint = " The provider rate limit or quota was reached. Wait and retry."
                    st.error(f"Language-model request failed: {exc}{hint}")
                    if chunks:
                        st.warning(
                            "The partial text above is incomplete and should not be relied on."
                        )
                    st.info(
                        "No canned answer was substituted. Fix the provider configuration or retry."
                    )
                except Exception as exc:
                    st.error(f"The response stream failed: {exc}")
                    st.info("No canned answer was substituted.")

st.divider()
st.warning(EMERGENCY_NOTE)
