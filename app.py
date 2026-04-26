"""
MediAssist AI — Clinical Report Summarizer
app.py  |  Main Streamlit UI
"""

import streamlit as st
import pandas as pd
from utils import extract_pdf_text, extract_image_text, parse_lab_values, flag_abnormal, load_sample_reports
from llm import generate_summary, answer_question

# ──────────────────────────────────────────────
#  PAGE CONFIG
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="MediAssist AI",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
#  CUSTOM CSS
# ──────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #f8fafc; }

    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #1e293b; }
    section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }

    /* Cards */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        box-shadow: 0 1px 6px rgba(0,0,0,0.08);
        margin-bottom: 1rem;
    }

    /* Status badges */
    .badge-normal  { background:#dcfce7; color:#166534; padding:3px 10px; border-radius:999px; font-size:0.78rem; font-weight:600; }
    .badge-high    { background:#fee2e2; color:#991b1b; padding:3px 10px; border-radius:999px; font-size:0.78rem; font-weight:600; }
    .badge-low     { background:#fef9c3; color:#854d0e; padding:3px 10px; border-radius:999px; font-size:0.78rem; font-weight:600; }

    /* Chat bubbles */
    .user-msg   { background:#dbeafe; border-radius:12px 12px 2px 12px; padding:0.75rem 1rem; margin:0.5rem 0; max-width:75%; margin-left:auto; }
    .ai-msg     { background:#f1f5f9; border-radius:12px 12px 12px 2px; padding:0.75rem 1rem; margin:0.5rem 0; max-width:75%; }

    /* Section headers */
    h2 { color: #1e293b; }
    h3 { color: #334155; }

    /* Disclaimer */
    .disclaimer {
        background:#fef3c7; border-left:4px solid #f59e0b;
        padding:0.75rem 1rem; border-radius:6px;
        font-size:0.85rem; color:#78350f;
    }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
#  SESSION STATE INIT
# ──────────────────────────────────────────────
for key in ["raw_text", "lab_values", "summary", "chat_history", "file_name"]:
    if key not in st.session_state:
        st.session_state[key] = None if key != "chat_history" else []

# ──────────────────────────────────────────────
#  SIDEBAR
# ──────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/color/96/stethoscope.png", width=60)
    st.markdown("## 🩺 MediAssist AI")
    st.markdown("---")

    st.markdown("### 📋 About")
    st.markdown("""
    Upload any lab report (PDF or image) and get:
    - 🔬 Extracted biomarkers
    - ⚠️ Abnormal value alerts
    - 📝 Plain-language summary
    - 💬 AI-powered Q&A
    """)

    st.markdown("---")
    st.markdown("### ⚙️ Settings")
    show_raw = st.checkbox("Show raw extracted text", value=False)
    st.markdown("---")

    # Sample reports from dataset
    st.markdown("### 📂 Try a Sample Report")
    sample_names = load_sample_reports()
    if sample_names:
        selected_sample = st.selectbox("Select sample", ["None"] + sample_names)
    else:
        selected_sample = "None"
        st.info("Add PDF/image files to `sample_reports/` folder from the Kaggle dataset.")

    st.markdown("---")
    st.markdown("<small style='color:#94a3b8'>⚠️ For educational use only.<br>Not a substitute for medical advice.</small>", unsafe_allow_html=True)

# ──────────────────────────────────────────────
#  MAIN HEADER
# ──────────────────────────────────────────────
st.markdown("# 🩺 MediAssist AI")
st.markdown("#### Clinical Report Summarizer — Upload a lab report to get started")
st.markdown('<div class="disclaimer">⚠️ <strong>Disclaimer:</strong> This tool is for educational purposes only. Always consult a licensed physician for medical decisions.</div>', unsafe_allow_html=True)
st.markdown("")

# ──────────────────────────────────────────────
#  FILE UPLOAD
# ──────────────────────────────────────────────
col_upload, col_info = st.columns([2, 1])

with col_upload:
    uploaded_file = st.file_uploader(
        "📤 Upload your lab report",
        type=["pdf", "png", "jpg", "jpeg"],
        help="Supports PDF and image formats (PNG, JPG)"
    )

with col_info:
    st.markdown("""
    <div class="metric-card">
        <strong>Supported Formats</strong><br>
        📄 PDF lab reports<br>
        🖼️ PNG / JPG images<br><br>
        <strong>Detected Biomarkers</strong><br>
        Hemoglobin · WBC · RBC<br>
        Platelets · Glucose · Cholesterol<br>
        Creatinine · Urea · SGOT · SGPT
    </div>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────
#  PROCESS FILE (uploaded or sample)
# ──────────────────────────────────────────────
process_trigger = uploaded_file is not None or (selected_sample and selected_sample != "None")

if process_trigger:
    # Determine source
    if uploaded_file:
        file_bytes = uploaded_file.read()
        file_name  = uploaded_file.name
        file_type  = uploaded_file.type
    else:
        import os
        sample_path = os.path.join("sample_reports", selected_sample)
        with open(sample_path, "rb") as f:
            file_bytes = f.read()
        file_name = selected_sample
        file_type = "application/pdf" if selected_sample.endswith(".pdf") else "image/png"

    # Only re-process if new file
    if st.session_state.file_name != file_name:
        st.session_state.chat_history = []
        with st.spinner("🔍 Extracting text from report..."):
            if "pdf" in file_type:
                raw_text = extract_pdf_text(file_bytes)
            else:
                raw_text = extract_image_text(file_bytes)

        with st.spinner("🧬 Parsing biomarkers..."):
            lab_values  = parse_lab_values(raw_text)
            flagged     = flag_abnormal(lab_values)

        with st.spinner("✍️ Generating AI summary..."):
            summary = generate_summary(raw_text, flagged)

        # Save to session
        st.session_state.raw_text   = raw_text
        st.session_state.lab_values = flagged
        st.session_state.summary    = summary
        st.session_state.file_name  = file_name

    st.success(f"✅ Report processed: **{file_name}**")
    st.markdown("---")

    # ──────────────────────────────────────────
    #  RAW TEXT (optional)
    # ──────────────────────────────────────────
    if show_raw and st.session_state.raw_text:
        with st.expander("📄 Raw Extracted Text", expanded=False):
            st.text_area("", value=st.session_state.raw_text, height=200, disabled=True)

    # ──────────────────────────────────────────
    #  BIOMARKER TABLE
    # ──────────────────────────────────────────
    st.markdown("## 🔬 Extracted Biomarkers")

    if st.session_state.lab_values:
        df = pd.DataFrame(st.session_state.lab_values)

        # Color-coded status column
        def color_status(val):
            if val == "High":
                return "background-color:#fee2e2; color:#991b1b; font-weight:600"
            elif val == "Low":
                return "background-color:#fef9c3; color:#854d0e; font-weight:600"
            else:
                return "background-color:#dcfce7; color:#166534; font-weight:600"

        styled = df.style.applymap(color_status, subset=["Status"])
        st.dataframe(styled, use_container_width=True, hide_index=True)

        # Quick stat summary
        total   = len(df)
        high    = len(df[df["Status"] == "High"])
        low     = len(df[df["Status"] == "Low"])
        normal  = len(df[df["Status"] == "Normal"])

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Tests", total)
        c2.metric("🔴 High",   high,   delta=f"{high} flagged",   delta_color="inverse")
        c3.metric("🟡 Low",    low,    delta=f"{low} flagged",    delta_color="inverse")
        c4.metric("🟢 Normal", normal)
    else:
        st.warning("⚠️ No standard biomarkers detected in this report. The report may use non-standard formatting.")

    st.markdown("---")

    # ──────────────────────────────────────────
    #  AI SUMMARY
    # ──────────────────────────────────────────
    st.markdown("## 📝 AI-Generated Summary")

    if st.session_state.summary:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #3b82f6;">
            {st.session_state.summary}
        </div>
        """, unsafe_allow_html=True)

        # Download button
        st.download_button(
            label="⬇️ Download Summary as .txt",
            data=st.session_state.summary,
            file_name=f"mediassist_summary_{file_name.split('.')[0]}.txt",
            mime="text/plain"
        )
    else:
        st.info("Summary could not be generated. Check your API key in `.env`.")

    st.markdown("---")

    # ──────────────────────────────────────────
    #  Q&A CHATBOT
    # ──────────────────────────────────────────
    st.markdown("## 💬 Ask About Your Report")
    st.markdown("Ask anything about your lab results in plain language.")

    # Suggested questions
    st.markdown("**💡 Suggested questions:**")
    q_col1, q_col2, q_col3 = st.columns(3)
    suggestions = [
        "What does low hemoglobin mean?",
        "Is my WBC count concerning?",
        "What should I ask my doctor?",
        "What is a normal glucose range?",
        "What foods help improve hemoglobin?",
        "Explain cholesterol in simple terms.",
    ]
    for i, sug in enumerate(suggestions):
        col = [q_col1, q_col2, q_col3][i % 3]
        if col.button(sug, key=f"sug_{i}"):
            st.session_state["prefill_q"] = sug

    # Chat input
    prefill = st.session_state.pop("prefill_q", "") if "prefill_q" in st.session_state else ""
    user_q = st.chat_input("Type your question here...", key="chat_input")
    if prefill:
        user_q = prefill

    # Process question
    if user_q:
        with st.spinner("🤔 Thinking..."):
            answer = answer_question(
                question=user_q,
                report_text=st.session_state.raw_text or "",
                lab_values=st.session_state.lab_values or []
            )
        st.session_state.chat_history.append({"role": "user",      "content": user_q})
        st.session_state.chat_history.append({"role": "assistant", "content": answer})

    # Render chat history
    if st.session_state.chat_history:
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(f'<div class="user-msg">🧑 {msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="ai-msg">🩺 {msg["content"]}</div>', unsafe_allow_html=True)

        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()

# ──────────────────────────────────────────────
#  EMPTY STATE
# ──────────────────────────────────────────────
else:
    st.markdown("""
    <div style="text-align:center; padding: 4rem 2rem; color:#94a3b8;">
        <div style="font-size:5rem">🩺</div>
        <h3 style="color:#64748b;">Upload a lab report to begin</h3>
        <p>Supports CBC reports, blood sugar tests, lipid panels, LFT, KFT and more.</p>
        <p>Or try a sample report from the sidebar →</p>
    </div>
    """, unsafe_allow_html=True)