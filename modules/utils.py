import pdfplumber
import pandas as pd
import re
from io import BytesIO
from datetime import datetime

try:
    import fitz  # fallback
except Exception:
    fitz = None


# -------------------- MAIN ENTRY --------------------
def process_pdf_to_df(uploaded_file, return_text=False):
    text, meta = extract_text(uploaded_file)
    if not text.strip():
        df = pd.DataFrame(columns=["Date", "Description", "Debit", "Credit", "Balance", "Type"])
        return (df, text, meta) if return_text else df

    df = parse_kotak_statement(text)
    return (df, text, meta) if return_text else df


# -------------------- TEXT EXTRACTION --------------------
def extract_text(uploaded_file):
    diag = {"engine": "", "pages": 0, "note": ""}
    raw = uploaded_file.read() if hasattr(uploaded_file, "read") else uploaded_file.getvalue()

    try:
        with pdfplumber.open(BytesIO(raw)) as pdf:
            diag["engine"] = "pdfplumber"
            diag["pages"] = len(pdf.pages)
            text = "\n".join([p.extract_text() or "" for p in pdf.pages])
            if text.strip():
                diag["note"] = "Extracted via pdfplumber"
                return text, diag
    except Exception as e:
        diag["note"] = f"pdfplumber failed: {e}"

    if fitz:
        try:
            doc = fitz.open(stream=raw, filetype="pdf")
            diag["engine"] = "pymupdf"
            diag["pages"] = len(doc)
            text = "\n".join([page.get_text('text') for page in doc])
            if text.strip():
                diag["note"] = "Extracted via PyMuPDF"
                return text, diag
        except Exception as e:
            diag["note"] = f"pymupdf failed: {e}"

    diag["note"] = "No text found"
    return "", diag


# -------------------- PARSER --------------------
def parse_kotak_statement(text: str) -> pd.DataFrame:
    """
    Handles lines like:
    02/09/2025 02/09/2025 SALARY CREDIT - ACME CORP 45000 95000 CREDIT
    03/09/2025 03/09/2025 POS PURCHASE - AMAZON -1299 88351 DEBIT
    """

    lines = [
        ln.strip()
        for ln in text.splitlines()
        if re.match(r"^\d{2}/\d{2}/\d{4}", ln)
        and "BALANCE" not in ln.upper()
        and "OPENING" not in ln.upper()
    ]

    data = []
    for ln in lines:
        # normalize spaces
        ln = re.sub(r"\s+", " ", ln).strip()
        parts = ln.split()
        if len(parts) < 6:
            continue

        date = parts[0]
        value_date = parts[1]
        ttype = parts[-1].upper()
        balance = safe_float(parts[-2])

        # extract all numbers
        nums = re.findall(r"-?\d+(?:\.\d+)?", ln)
        if not nums:
            continue

        # last number = balance, second last = amount
        if len(nums) >= 2:
            amount = float(nums[-2])
        else:
            amount = float(nums[-1])

        # determine type by sign or label
        if amount < 0 or "DEBIT" in ttype:
            txn_type = "Debit"
            debit, credit = abs(amount), 0.0
        else:
            txn_type = "Credit"
            debit, credit = 0.0, amount

        # description is between value_date and amount
        desc = " ".join(parts[2:-3]).strip()

        data.append({
            "Date": safe_date(date),
            "Description": desc,
            "Debit": debit,
            "Credit": credit,
            "Balance": balance,
            "Type": txn_type
        })

    df = pd.DataFrame(data)
    if df.empty:
        return pd.DataFrame(columns=["Date", "Description", "Debit", "Credit", "Balance", "Type"])

    # Add combined Amount column for visualization
    df["Amount"] = df["Debit"] + df["Credit"]
    return df


# -------------------- HELPERS --------------------
def safe_date(s):
    for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except:
            pass
    return s


def safe_float(x):
    try:
        return float(str(x).replace(",", ""))
    except:
        return None


def compute_basic_stats(df):
    if df.empty:
        return {"n_txn": 0, "sum_debits": 0.0, "sum_credits": 0.0, "final_balance": 0.0}

    total_debits = df["Debit"].sum()
    total_credits = df["Credit"].sum()
    final_balance = df["Balance"].iloc[-1] if "Balance" in df.columns else 0.0

    return {
        "n_txn": len(df),
        "sum_debits": round(total_debits, 2),
        "sum_credits": round(total_credits, 2),
        "final_balance": round(final_balance, 2),
    }


# -------------------- OFFLINE CHATBOT --------------------
def mini_chatbot(msg: str) -> str:
    msg = msg.lower().strip()
    if "budget" in msg:
        return "Use the 50/30/20 rule: 50% needs, 30% wants, 20% savings."
    if "save" in msg:
        return "Set automatic transfers to your savings account on salary day."
    if "invest" in msg:
        return "Start small SIPs once you’ve built an emergency fund."
    if "credit" in msg:
        return "Pay full dues monthly and keep usage under 30%."
    return "Ask me about budgeting, saving, or investing — I’m your offline FinGenie!"


# -------------------- FINANCE VIDEOS --------------------
def youtube_search_links(topic: str, n=8):
    topic_q = "+".join(topic.split())
    base = "https://www.youtube.com/results?search_query="
    links = [
        ("Search Results", base + topic_q)
    ]
    return links[:n]
