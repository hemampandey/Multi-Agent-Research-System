import streamlit as st
from app.graph import graph
from app.utils.pdf import create_pdf_buffer

@st.cache_data
def run_graph(topic, mode):
    return graph.invoke({
        "topic": topic,
        "mode": mode
    })

st.set_page_config(page_title="AI Research Agent", layout="wide")

st.title("🧠 Multi-Agent Research System")

col1, col2 = st.columns([2,1])

with col1:
    topic = st.text_input("Enter topic")

with col2:
    mode = st.selectbox("Depth", ["Basic", "Advanced"])

if st.button("Generate Report"):
    if topic:
        st.info("🧠 Planner → 🔍 Researcher → ✍️ Writer → 🧪 Critic")

        with st.spinner("Running AI pipeline..."):
            result = run_graph(topic, mode)
        st.session_state["result"] = result
    else:
        st.warning("Please enter a topic")

if "result" in st.session_state:
    result = st.session_state["result"]

    st.subheader("📄 Report")
    st.markdown(result["final_report"])

    st.code(result["final_report"])

    st.subheader("🔗 Sources")
    for i, url in enumerate(result["sources"], 1):
        st.markdown(f"{i}. {url}")

    pdf_buffer = create_pdf_buffer(result["final_report"])

    st.download_button(
        label="📄 Download Report",
        data=pdf_buffer,
        file_name="report.pdf",
        mime="application/pdf"
    )
    