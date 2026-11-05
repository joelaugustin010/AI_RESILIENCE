"""Evidence-grounded disaster information assistant page."""
import streamlit as st

from src.disaster_assistant import KnowledgeBaseError, answer_question, load_knowledge
from src.ui_theme import page_header

page_header(
    "AI RESILIENCE · SOURCE-GROUNDED GUIDANCE",
    "Disaster Intelligence Assistant",
    "Ask about flood preparedness, cyclones, earthquakes, air pollution or compound hazards. "
    "Answers come from a reviewed local knowledge file with official source links.",
    meta=("Phase 2", "Reviewed knowledge base", "Not a live warning"),
    accent="teal",
    key="disaster-assistant",
    image="app/static/images/hero-kerala-ghats.jpg",
)

st.info(
    "Ask about flood preparedness, cyclones, earthquakes, air pollution, or compound hazards. "
    "Answers are retrieved from a reviewed local knowledge file with official source links; "
    "the assistant does not estimate local risk or replace emergency instructions."
)

try:
    topics = load_knowledge()
except KnowledgeBaseError as exc:
    st.error(f"The knowledge base could not be checked: {exc}")
    st.stop()

with st.form("disaster_assistant_form"):
    question = st.text_area(
        "What do you want to understand?",
        placeholder="Example: What should a hospital review before heavy rain and a cyclone?",
        max_chars=1200,
    )
    submitted = st.form_submit_button("Find evidence-based guidance", type="primary")

if submitted:
    result = answer_question(question, topics)
    st.write(result["message"])
    if not result["matched"]:
        st.warning("No answer was invented for this question.")
    for topic in result["topics"]:
        with st.container(border=True):
            st.subheader(topic["title"])
            st.write(topic["summary"])
            st.markdown("**Preparedness and review steps**")
            for action in topic["actions"]:
                st.markdown(f"- {action}")
            st.markdown("**Limitations for AI_RESILIENCE**")
            for limitation in topic["limitations"]:
                st.markdown(f"- {limitation}")
            st.markdown("**Sources**")
            for source in topic["sources"]:
                st.markdown(f"- [{source['publisher']}: {source['title']}]({source['url']})")
    st.warning(
        "For an active emergency, follow current instructions from the relevant authorities. "
        "Do not use this prototype to decide whether to evacuate or to delay seeking help."
    )

with st.expander("How this assistant works"):
    st.markdown(
        "- Searches explicit keywords in a local, version-controlled knowledge file.\n"
        "- Shows the source and known limitations for each matched topic.\n"
        "- Returns no answer when the question does not match the reviewed topics.\n"
        "- Does not use generated probabilities, live feeds, or unverified demonstration rows."
    )
