import pandas as pd
import re

CATEGORY_RULES = {
    r"salary|income|credit.*acme|refund|parent|fd maturity": "Income / Credits",
    r"swiggy|zomato|restaurant|starbucks": "Food & Drinks",
    r"uber|ola|rapido|paytm": "Transport",
    r"amazon|flipkart|bookstore|clothing": "Shopping",
    r"atm|withdraw": "Cash Withdrawal",
    r"rent": "Rent / Housing",
    r"tax|electricity|lic": "Bills & Utilities",
    r"mutual fund|sip": "Investments",
    r"grocery|grocer": "Groceries",
}

def categorize_transactions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Category"] = "Other"
    for pattern, cat in CATEGORY_RULES.items():
        mask = df["Description"].str.lower().str.contains(pattern)
        df.loc[mask, "Category"] = cat
    return df

def summarize_categories(df: pd.DataFrame):
    spent = df[df["Type"].str.upper().eq("DEBIT")].groupby("Category")["Amount"].sum()
    if spent.empty:
        return {"top_category": None, "max_spent": 0, "summary": {}}
    top_cat = spent.idxmax()
    return {"top_category": top_cat, "max_spent": float(spent.max()), "summary": spent.to_dict()}
