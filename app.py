import streamlit as st
import pandas as pd
from modules.utils import process_pdf_to_df, compute_basic_stats, mini_chatbot, youtube_search_links
from modules.categorize_transactions import categorize_transactions, summarize_categories

# -------------------- Page Setup --------------------
st.set_page_config(page_title="FinGenie (Lite)", page_icon="💰", layout="wide")

# Apply CSS Theme
with open("styles/style.css", "r", encoding="utf-8") as css:
    st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)

# Sidebar
st.sidebar.image("assets/fingenie_logo.png", width=160)
st.sidebar.markdown("### FinGenie (Lite)")
st.sidebar.caption("Smart dummy financial analyzer 💸")

# Tabs
tab1, tab2, tab3 = st.tabs(["🏠 Dashboard", "💬 AI Chatbot", "🎥 Financial Videos"])

# -------------------- Dashboard Tab --------------------
with tab1:
    st.header("Upload & Quick Analyze")

    uploaded = st.file_uploader("📂 Upload your Kotak (dummy) bank statement PDF", type=["pdf"])

    if uploaded:
        with st.spinner("Processing your statement..."):
            df, raw_text, meta = process_pdf_to_df(uploaded, return_text=True)

        # --- Debug Info ---
        with st.expander("Extraction Debug"):
            st.write(f"Engine: **{meta.get('engine', '')}**, Pages: **{meta.get('pages', 0)}**")
            st.write(meta.get("note", ""))
            if raw_text and raw_text.strip():
                st.code(raw_text[:1000] + ("..." if len(raw_text) > 1000 else ""), language="text")
            else:
                st.info("No selectable text found. Try exporting a text-based PDF.")

        # --- Display Results ---
        if df.empty:
            st.error("Could not parse any transactions.")
        else:
            df = categorize_transactions(df)
            st.success("✅ Parsed & categorized successfully!")

            # Summary Metrics
            stats = compute_basic_stats(df)
            cat_summary = summarize_categories(df)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Transactions", stats["n_txn"])
            c2.metric("Total Debits", f"₹{stats['sum_debits']:,.2f}")
            c3.metric("Total Credits", f"₹{stats['sum_credits']:,.2f}")
            c4.metric(
                "Top Category",
                cat_summary["top_category"] or "—",
                f"₹{cat_summary['max_spent']:,.0f}" if cat_summary["max_spent"] else ""
            )

            # Data Table
            st.subheader("📋 Transaction Preview")
            st.dataframe(df.head(50), use_container_width=True)

            # Bar Chart
            st.subheader("💡 Spending by Category")
            if cat_summary["summary"]:
                st.bar_chart(pd.Series(cat_summary["summary"]))
            else:
                st.info("No debit transactions found to chart.")
    else:
        st.info("Upload a PDF statement to begin.")

# -------------------- Chatbot Tab --------------------
with tab2:
    st.header("Ask FinGenie 🤖")
    st.caption("Tiny offline assistant (no API, local logic).")

    q = st.text_input("Ask about budgeting, savings, credit cards, etc.")
    if st.button("Ask"):
        if not q.strip():
            st.warning("Please type a question.")
        else:
            with st.spinner("Thinking..."):
                ans = mini_chatbot(q)
            st.success(ans)

# -------------------- Financial Videos Tab --------------------
with tab3:
    st.header("Financial Insights 🎥")
    topic = st.text_input("Enter a topic", value="saving money")
    if st.button("Search"):
        links = youtube_search_links(topic, n=8)
        st.write("Here are some great personal finance links:")
        for title, url in links:
            st.markdown(f"- [{title}]({url})")
    st.caption("Tip: Try topics like *budgeting*, *mutual funds*, or *credit cards*.")
