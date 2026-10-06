import streamlit as st
from app.harness.runner import run_research
from app.utils.pdf import create_pdf_buffer

@st.cache_data(show_spinner=False)
def run_graph(topic, mode):
    result = run_research(topic, mode)
    if result.error_code in ("llm_error", "budget_exceeded"):
        # Raising keeps transient failures out of the cache, so a retry really retries
        raise RuntimeError(result.error)
    return result.to_dict()

st.set_page_config(page_title="AI Research Agent", layout="wide")

st.title("🧠 Multi-Agent Research System")

col1, col2 = st.columns([2,1])

with col1:
    topic = st.text_input("Enter topic")

with col2:
    mode = st.selectbox("Depth", ["Basic", "Advanced"])

if st.button("Generate Report"):
    if topic:
        st.info("🛡 Input guard → 🧠 Planner → 🔍 Researcher → ✍️ Writer ⇄ 🧪 Critic → 🛡 Output guard")

        with st.spinner("Running AI pipeline..."):
            try:
                st.session_state["result"] = run_graph(topic, mode)
            except RuntimeError as e:
                st.session_state.pop("result", None)
                st.error(f"The AI service failed, please try again. ({e})")
    else:
        st.warning("Please enter a topic")

if "result" in st.session_state:
    result = st.session_state["result"]

    if result["error"]:
        st.error(f"⛔ {result['error']}")
        st.stop()

    flagged = [e for e in result["guardrail_events"] if e["action"] == "flagged"]
    for e in flagged:
        st.warning(f"⚠️ {e['guard']}: {e['detail']}")

    st.subheader("📄 Report")
    st.markdown(result["final_report"])

    st.code(result["final_report"])

    st.subheader("🔗 Sources")
    for i, url in enumerate(result["sources"], 1):
        st.markdown(f"{i}. {url}")

    with st.expander(f"🛡 Guardrail events ({len(result['guardrail_events'])})"):
        if result["guardrail_events"]:
            st.table(result["guardrail_events"])
        else:
            st.write("No interventions were needed.")

    with st.expander("🔍 Run trace"):
        st.json(result["trace"]["summary"])
        st.table(result["trace"]["spans"])

    pdf_buffer = create_pdf_buffer(result["final_report"])

    st.download_button(
        label="📄 Download Report",
        data=pdf_buffer,
        file_name="report.pdf",
        mime="application/pdf"
    )
