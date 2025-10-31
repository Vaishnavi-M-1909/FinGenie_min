import streamlit as st
from modules.utils import process_pdf_to_df, compute_basic_stats, mini_chatbot, youtube_search_links

st.set_page_config(page_title="FinGenie (Lite)", page_icon="💰", layout="wide")
with open("styles/style.css", "r", encoding="utf-8") as css:
    st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)

st.sidebar.image("assets/fingenie_logo.png", width=160)
st.sidebar.markdown("### FinGenie (Lite)")
st.sidebar.caption("Minimal, offline prototype — no paid APIs.")

tab1, tab2, tab3 = st.tabs(["🏠 Dashboard", "💬 AI Chatbot", "🎥 Financial Videos"])

# -------------------- Dashboard --------------------
with tab1:
    st.header("Upload & Quick Analyze")
    force_ocr = st.checkbox("Force OCR (for scanned/image-only PDFs)", value=False)
    uploaded = st.file_uploader("📂 Upload a real bank statement (PDF)", type=["pdf"])

    # Show password field only after a file is uploaded
    password = None
    if uploaded:
        st.info("If your bank PDF is password protected, enter the password below (it will not be saved).")
        password = st.text_input("PDF password (leave blank if none)", type="password")

    if uploaded:
        with st.spinner("Reading your statement..."):
            # pass password through (None if blank)
            pwd = password if password else None
            df, raw_text, meta = process_pdf_to_df(uploaded, return_text=True, force_ocr=force_ocr, password=pwd)

            # Overwrite local pwd variable immediately
            pwd = None
            password = None

        with st.expander("Extraction Debug"):
            st.write(f"Engine: **{meta.get('engine','')}**, Pages: **{meta.get('pages',0)}**")
            st.write(meta.get("note", ""))
            if raw_text and raw_text.strip():
                st.code(raw_text[:1500] + ("..." if len(raw_text) > 1500 else ""), language="text")
            else:
                st.info("No selectable text found. If OCR is off, enable it or verify Tesseract & Poppler are installed.")

        if df.empty:
            st.error("Could not parse any transactions. Try turning on OCR (if scanned) or use a clearer PDF.")
        else:
            st.success("Parsed transactions successfully!")
            stats = compute_basic_stats(df)
            c1, c2, c3 = st.columns(3)
            c1.metric("Transactions", stats["n_txn"])
            c2.metric("Total Debits", f"₹{stats['sum_debits']:,.2f}")
            c3.metric("Total Credits", f"₹{stats['sum_credits']:,.2f}")

            st.subheader("Preview")
            st.dataframe(df.head(100), use_container_width=True)
    else:
        st.info("Upload a PDF statement to get started.")

# -------------------- AI Chatbot --------------------
with tab2:
    st.header("Ask FinGenie")
    st.caption("Tiny offline assistant (no external APIs).")
    q = st.text_input("Ask about budgeting, credit cards, emergency funds, etc.")
    if st.button("Ask"):
        if not q.strip():
            st.warning("Please type a question.")
        else:
            with st.spinner("Thinking..."):
                ans = mini_chatbot(q)
            st.success(ans)

# -------------------- Financial Videos --------------------
with tab3:
    st.header("Personal Finance Videos")
    topic = st.text_input("Topic", value="saving money")
    if st.button("Show Links"):
        links = youtube_search_links(topic, n=8)
        st.write("Here are some quick links (opens in a new tab):")
        for title, url in links:
            st.markdown(f"- [{title}]({url})")
    st.caption("Tip: Change the topic and press **Show Links** to refresh.")
