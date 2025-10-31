import streamlit as st
import pandas as pd
from modules.utils import process_pdf_to_df, compute_basic_stats, mini_chatbot, youtube_search_links
from modules.categorize_transactions import categorize_transactions, summarize_categories

st.set_page_config(page_title="FinGenie (Lite)", page_icon="💰", layout="wide")

# --- Apply CSS theme ---
with open("styles/style.css", "r", encoding="utf-8") as css:
    st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)

st.sidebar.image("assets/fingenie_logo.png", width=160)
st.sidebar.markdown("### FinGenie (Lite)")
st.sidebar.caption("Smart dummy financial analyzer 💸")

tab1, tab2, tab3 = st.tabs(["🏠 Dashboard", "💬 AI Chatbot", "🎥 Financial Videos"])

# -------------------- Dashboard --------------------
with tab1:
    st.header("Upload & Quick Analyze")

    uploaded = st.file_uploader("📂 Upload your Kotak (dummy) bank statement PDF", type=["pdf"])

    if uploaded:
        with st.spinner("Processing your statement..."):
            df, raw_text, meta = process_pdf_to_df(uploaded, return_text=True)

        with st.expander("Extraction Debug"):
            st.write(f"Engine: **{meta.get('engine','')}**, Pages: **{meta.get('pages',0)}**")
            st.write(meta.get("note", ""))
            if raw_text and raw_text.strip():
                st.code(raw_text[:1000] + ("..." if len(raw_text) > 1000 else ""), language="text")
            else:
                st.info("No selectable text found. Try exporting a text-based PDF.")

        if df.empty:
            st.error("Could not parse any transactions.")
        else:
            df = categorize_transactions(df)
            st.success("Parsed & categorized successfully!")

            stats = compute_basic_stats(df)
            cat_summary = summarize_categories(df)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Transactions", stats["n_txn"])
            c2.metric("Total Debits", f"₹{stats['sum_debits']:,.2f}")
            c3.metric("Total Credits", f"₹{st
