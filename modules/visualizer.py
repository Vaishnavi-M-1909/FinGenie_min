import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

def category_pie(df: pd.DataFrame):
    dd = df[df["Category"] != "Income"]
    if dd.empty:
        dd = df.copy()
    summary = dd.groupby("Category")["Amount"].sum()
    fig, ax = plt.subplots()
    ax.pie(summary, labels=summary.index, autopct="%1.1f%%", startangle=90)
    ax.set_title("Spending Breakdown by Category")
    st.pyplot(fig)

def category_bar(df: pd.DataFrame):
    dd = df[df["Category"] != "Income"]
    if dd.empty:
        dd = df.copy()
    summary = dd.groupby("Category")["Amount"].sum().sort_values(ascending=False)
    fig, ax = plt.subplots()
    summary.plot(kind="bar", ax=ax, color="skyblue")
    ax.set_ylabel("Amount (₹)")
    ax.set_xlabel("Category")
    ax.set_title("Amount by Category")
    plt.xticks(rotation=45, ha="right")
    st.pyplot(fig)
