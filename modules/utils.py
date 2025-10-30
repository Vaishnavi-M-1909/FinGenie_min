
import pdfplumber
import pandas as pd
import re
from io import BytesIO
from datetime import datetime

# ---------- Minimal PDF -> transactions ----------
def process_pdf_to_df(uploaded_file):
    text = extract_text(uploaded_file)
    if not text.strip():
        return pd.DataFrame(columns=["Date","Description","Amount","Type"])
    return parse_text_to_df(text)

def extract_text(uploaded_file):
    try:
        # uploaded_file can be a BytesIO or UploadedFile; support both
        raw = uploaded_file.read() if hasattr(uploaded_file, "read") else uploaded_file.getvalue()
        with pdfplumber.open(BytesIO(raw)) as pdf:
            chunks = []
            for p in pdf.pages:
                t = p.extract_text() or ""
                chunks.append(t)
            return "\n".join(chunks)
    except Exception as e:
        return ""

def parse_text_to_df(text):
    # Ultra-simplified line parser: look for date, description text, and numbers
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    rows = []
    date_pat = r"(\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b)"
    amt_pat  = r"([+-]?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|[+-]?\d+(?:\.\d{1,2})?)"

    for ln in lines:
        d = re.search(date_pat, ln)
        a = re.findall(amt_pat, ln)
        if d and a:
            # heuristic: last number on the line is likely the amount
            amount_raw = a[-1].replace(",", "")
            try:
                amount = float(amount_raw)
            except:
                continue
            date_str = d.group(1)
            desc = re.sub(date_pat, "", ln).strip()
            # Determine Type by keywords/sign
            lnl = ln.lower()
            ttype = "Credit" if ("credit" in lnl or amount > 0) else "Debit"
            rows.append({
                "Date": safe_date(date_str),
                "Description": desc,
                "Amount": abs(amount),
                "Type": ttype
            })
    df = pd.DataFrame(rows, columns=["Date","Description","Amount","Type"])
    return df

def safe_date(s):
    for fmt in ("%d/%m/%Y","%d-%m-%Y","%d/%m/%y","%d-%m-%y","%m/%d/%Y","%m-%d-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except:
            continue
    return s  # leave as-is if unknown

# ---------- Basic stats ----------
def compute_basic_stats(df):
    if df.empty:
        return {
            "n_txn": 0,
            "sum_debits": 0.0,
            "sum_credits": 0.0
        }
    debits = df.loc[df["Type"]=="Debit", "Amount"].sum()
    credits = df.loc[df["Type"]=="Credit", "Amount"].sum()
    return {
        "n_txn": len(df),
        "sum_debits": float(debits),
        "sum_credits": float(credits)
    }

# ---------- Tiny rule-based chatbot (no external APIs) ----------
def mini_chatbot(message: str) -> str:
    if not message or not message.strip():
        return "Ask me about budgeting, savings, EMIs, credit vs debit, or how to read your statement."
    msg = message.lower().strip()

    # intent: budget
    if any(w in msg for w in ["budget","save","saving","spend less"]):
        return ("Quick tip: Use the 50/30/20 rule — 50% needs, 30% wants, 20% savings/debt payoff. "
                "Automate a fixed transfer to savings on salary day. Track 3 largest categories weekly.")

    # intent: credit card
    if "credit card" in msg or "cc" in msg:
        return ("Credit card hygiene: Pay full balance before due date, keep utilization under 30%, "
                "avoid cash advances, and use statement cycle dates to your advantage.")

    # intent: emergency
    if "emergency" in msg:
        return ("Build an emergency fund worth 3–6 months of core expenses in a high-liquidity account. "
                "Start with 1 month target and scale up.")

    # general
    if any(w in msg for w in ["invest","mutual fund","sip","fd","rd"]):
        return ("Starter investing idea: Begin an SIP in a diversified index or conservative balanced fund "
                "after you’ve built an emergency buffer and cleared high-interest debt.")

    # fallback
    return ("I'm a lightweight offline assistant right now. Ask about budgeting, emergency funds, credit-card tips, "
            "or reading your statement.")

# ---------- YouTube link generator (no scraping) ----------
def youtube_search_links(topic: str, n=8):
    topic_q = "+".join(topic.split())
    url = f"https://www.youtube.com/results?search_query={topic_q}+personal+finance"
    # Provide a few starter channels and the search link
    results = [
        ("Search on YouTube", url),
        ("Practical personal finance videos (CA Rachana Ranade)", "https://www.youtube.com/@CArachana"),
        ("Market Basics – B Wealthy", "https://www.youtube.com/@BWealthy"),
        ("Basics & Behaviors – Pranjal Kamra", "https://www.youtube.com/@PranjalKamra"),
        ("Value Research", "https://www.youtube.com/@ValueResearchOnline"),
        ("Banking/Economy explainers – Think School", "https://www.youtube.com/@ThinkSchoolOfficial"),
    ]
    return results[:n]
