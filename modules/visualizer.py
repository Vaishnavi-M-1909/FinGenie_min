import plotly.express as px
import pandas as pd

def category_pie(df: pd.DataFrame):
    # Only spending categories (exclude Income)
    dd = df[df["Category"] != "Income"]
    if dd.empty:
        dd = df.copy()
    return px.pie(dd, names="Category", values="Amount", title="Spending Breakdown by Category")

def category_bar(df: pd.DataFrame):
    dd = df[df["Category"] != "Income"]
    if dd.empty:
        dd = df.copy()
    summary = dd.groupby("Category")["Amount"].sum().reset_index()
    return px.bar(summary, x="Category", y="Amount", title="Amount by Category")
