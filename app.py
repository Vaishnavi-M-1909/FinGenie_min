import streamlit as st
from modules.utils import (
    process_pdf_to_df, compute_basic_stats, categorize_transactions, summarise_categories
)
from modules.visualizer import category_pie, category_bar
from modules.youtube_scraper import yt_search
from modules.chatbot_hf import hf_finance_chatbot, has_hf_token, mini_chatbot_fallback

st.set_page_config(page_title="FinGenie (Lite)", page_icon="💰", layout="wide")
with open("styles/style.css", "r", encoding="utf-8") as css:
    st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)

st.sidebar.image("assets/fingenie_logo.png", width=160)
st.sidebar.markdown("### FinGenie (Lite)")
st.sidebar.caption("Minimal, offline prototype — no paid APIs for core parsing.")

tab1, tab2, tab3 = st.tabs(["🏠 Dashboard", "💬 AI Chatbot", "🎥 Financial Videos"])

# -------------------- Dashboard --------------------
with tab1:
    st.header("Upload & Quick Analyze")
    c1, c2 = st.columns([1,1])
    with c1:
        force_ocr = st.checkbox("Force OCR (for scanned PDFs)", value=False)
    with c2:
        st.caption("If your PDF is password-protected, enter it below. (Never saved.)")
        password = st.text_input("PDF password", type="password", value="")
        password = password or None

    uploaded = st.file_uploader("📂 Upload a real bank statement (PDF)", type=["pdf"])

    if uploaded:
        with st.spinner("Reading your statement..."):
            df, raw_text, meta = process_pdf_to_df(
                uploaded, return_text=True, force_ocr=force_ocr, password=password
            )
            password = None  # best-effort scrub

        with st.expander("Extraction Debug"):
            st.write(f"Engine: **{meta.get('engine','')}**, Pages: **{meta.get('pages',0)}**")
            st.write(meta.get("note", ""))
            if raw_text and raw_text.strip():
                st.code(raw_text[:1500] + ("..." if len(raw_text) > 1500 else ""), language="text")
            else:
                st.info("No selectable text found. Try enabling OCR and ensure Tesseract & Poppler are installed.")

        if df.empty:
            st.error("Could not parse any transactions. Try OCR (if scanned) or a clearer PDF.")
        else:
            st.success("Parsed transactions successfully!")
            stats = compute_basic_stats(df)
            a,b,c = st.columns(3)
            a.metric("Transactions", stats["n_txn"])
            b.metric("Total Debits", f"₹{stats['sum_debits']:,.2f}")
            c.metric("Total Credits", f"₹{stats['sum_credits']:,.2f}")

            # -------- Categorization & charts --------
            df_cat = categorize_transactions(df)
            st.subheader("Category Breakdown (Debits/Spends)")
            st.plotly_chart(category_pie(df_cat), use_container_width=True)
            st.plotly_chart(category_bar(df_cat), use_container_width=True)

            (most_cat, most_amt), (least_cat, least_amt) = summarise_categories(df_cat)
            st.markdown(
                f"**Most spent:** {most_cat or '—'} → ₹{most_amt:,.2f} &nbsp;&nbsp; | &nbsp;&nbsp; "
                f"**Least spent:** {least_cat or '—'} → ₹{least_amt:,.2f}"
            )

            st.subheader("Preview")
            st.dataframe(df_cat.head(100), use_container_width=True)
    else:
        st.info("Upload a PDF statement to get started.")

# -------------------- AI Chatbot --------------------
with tab2:
    st.header("Ask FinGenie")
    if not has_hf_token():
        st.caption("Hugging Face token not set — using lightweight local fallback.")
    q = st.text_input("Ask about budgeting, EMIs, statement insights, etc.")
    if st.button("Ask"):
        if not q.strip():
            st.warning("Please type a question.")
        else:
            with st.spinner("Thinking..."):
                if has_hf_token():
                    answer = hf_finance_chatbot(q)
                else:
                    answer = mini_chatbot_fallback(q)
            st.success(answer)

# -------------------- Financial Videos --------------------
with tab3:
    st.header("Personal Finance Videos (YouTube)")
    topic = st.text_input("Topic", value="saving money for students")
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        shorts_only = st.checkbox("Shorts only", value=False)
    with c2:
        duration = st.selectbox(
            "Duration filter",
            ["Any", "< 5 min", "5–15 min", "15–30 min", "30–60 min", "> 60 min"],
            index=0
        )
    with c3:
        max_results = st.number_input("Max results", min_value=3, max_value=30, value=10, step=1)

    if st.button("Search"):
        with st.spinner("Fetching videos..."):
            items = yt_search(topic, max_results=max_results, shorts_only=shorts_only, duration_filter=duration)
        if not items:
            st.warning("No results found. Try adjusting filters.")
        else:
            for it in items:
                dur = it.get("duration_str") or "—"
                title = it["title"]
                url = it["url"]
                ch = it.get("channel", "Unknown")
                st.markdown(f"- **[{title}]({url})**  · ⏱ {dur} · 👤 {ch}")
    st.caption("Uses yt_dlp under the hood (no official API).")
