
import streamlit as st
import pandas as pd
from modules.utils import process_pdf_to_df, compute_basic_stats, mini_chatbot, youtube_search_links

st.set_page_config(page_title="FinGenie (Lite)", page_icon="💰", layout="wide")
with open("styles/style.css","r",encoding="utf-8") as css:
    st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)

# Sidebar
st.sidebar.image("assets/fingenie_logo.png", width=160)
st.sidebar.markdown("### FinGenie (Lite)")
st.sidebar.caption("Minimal, offline prototype — no paid APIs.")

tab1, tab2, tab3 = st.tabs(["🏠 Dashboard","💬 AI Chatbot","🎥 Financial Videos"])

# -------------------- Dashboard --------------------
with tab1:
    st.header("Upload & Quick Analyze")
    uploaded = st.file_uploader("📂 Upload a real bank statement (PDF)", type=["pdf"])
    if uploaded:
        with st.spinner("Reading your statement..."):
            df = process_pdf_to_df(uploaded)
        if df.empty:
            st.error("Could not parse any transactions. Try another statement or clearer PDF.")
        else:
            st.success("Parsed transactions successfully!")
            stats = compute_basic_stats(df)
            c1, c2, c3 = st.columns(3)
            c1.metric("Transactions", stats["n_txn"])
            c2.metric("Total Debits", f"₹{stats['sum_debits']:,.2f}")
            c3.metric("Total Credits", f"₹{stats['sum_credits']:,.2f}")

            # Show preview table
            st.subheader("Preview")
            st.dataframe(df.head(50), use_container_width=True)

            # Save for later (optional)
            try:
                df.to_csv("data/processed/last_statement.csv", index=False)
                st.caption("Saved to data/processed/last_statement.csv")
            except Exception:
                pass
    else:
        st.info("Upload a PDF statement to get started.")

# -------------------- AI Chatbot --------------------
with tab2:
    st.header("Ask FinGenie")
    st.caption("This is a tiny offline assistant (no external APIs).")
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
