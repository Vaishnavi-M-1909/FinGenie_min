import pdfplumber
import pandas as pd
import re
from io import BytesIO
from datetime import datetime

try:
    import fitz  # optional fallback
except Exception:
    fitz = None


# -------------------- MAIN ENTRY --------------------
def process_pdf_to_df(uploaded_file, return_text=False):
    """Extract text and parse Kotak bank statement (dummy version)."""
    text, meta = extract_text(uploaded_file)
    if not text.strip():
        df = pd.DataFrame(columns=["Date", "Description", "Amount", "Type"])
        return (df, text, meta) if return_text else df

    df = parse_kotak_statement(text)
    return (df, text, meta) if return_text else df


# -------------------- TEXT EXTRACTION --------------------
def extract_text(uploaded_file):
    """Extract text using pdfplumber or PyMuPDF."""
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


# -------------------- PARSER (WORKS FOR YOUR KOTAK PDF) --------------------
def parse_kotak_statement(text):
    """
    Parses dummy Kotak bank statement lines like:
    02/09/2025 02/09/2025 SALARY CREDIT - ACME CORP 45000 95000 CREDIT
    03/09/2025 03/09/2025 UPI PAYMENT - SWIGGY 9876543210 -350 94650 DEBIT
    """
    lines = [
        ln.strip()
        for ln in text.splitlines()
        if re.match(r"^\d{2}/\d{2}/\d{4}", ln) and "BALANCE" not in ln.upper()
    ]

    data = []
    for ln in lines:
        ln = re.sub(r"\s+", " ", ln).strip()

        # Extract date fields
        parts = ln.split()
        if len(parts) < 6:
            continue

        date = parts[0]
        value_date = parts[1]
        ttype = parts[-1].upper()
        balance = safe_float(parts[-2])

        # Credit/Debit amount detection
        debit, credit = 0.0, 0.0
        if ttype == "DEBIT":
            # second last numeric before balance
            amt_match = re.findall(r"-?\d+(?:\.\d+)?", ln)
            debit = abs(float(amt_match[-2])) if len(amt_match) >= 2 else 0.0
        elif ttype == "CREDIT":
            amt_match = re.findall(r"-?\d+(?:\.\d+)?", ln)
            credit = abs(float(amt_match[-2])) if len(amt_match) >= 2 else 0.0

        # Description between dates and amounts
        desc = " ".join(parts[2:-3])
        desc = desc.replace("  ", " ").strip()

        # Determine Amount and Type
        amount = credit if credit > 0 else debit
        txn_type = "Credit" if credit > 0 else "Debit"

        data.append(
            {
                "Date": safe_date(date),
                "Description": desc,
                "Amount": amount,
                "Type": txn_type,
                "Balance": balance,
            }
        )

    return pd.DataFrame(data, columns=["Date", "Description", "Amount", "Type", "Balance"])


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
        return {"n_txn": 0, "sum_debits": 0.0, "sum_credits": 0.0}

    total_debits = df.loc[df["Type"] == "Debit", "Amount"].sum()
    total_credits = df.loc[df["Type"] == "Credit", "Amount"].sum()

    return {
        "n_txn": len(df),
        "sum_debits": round(total_debits, 2),
        "sum_credits": round(total_credits, 2),
    }


# -------------------- MINI OFFLINE CHATBOT --------------------
def mini_chatbot(msg: str) -> str:
    msg = msg.lower().strip()
    if "budget" in msg:
        return "Try 50/30/20 rule: 50% needs, 30% wants, 20% savings."
    if "save" in msg:
        return "Set auto-transfer to your savings on salary day."
    if "invest" in msg:
        return "Start small SIPs once your emergency fund is ready."
    if "credit" in msg:
        return "Pay full credit card dues monthly. Keep usage <30%."
    return "Ask me about budgeting, saving, or investing!"


# -------------------- FINANCE VIDEOS --------------------
def youtube_search_links(topic: str, n=8):
    topic_q = "+".join(topic.split())
    base = "https://www.youtube.com/results?search_query="
    links = [
        ("Search Results", base + topic_q),
        ("CA Rachana Ranade", "https://www.youtube.com/@CArachana"),
        ("Pranjal Kamra", "https://www.youtube.com/@PranjalKamra"),
        ("Think School", "https://www.youtube.com/@ThinkSchoolOfficial"),
        ("B Wealthy", "https://www.youtube.com/@BWealthy"),
        ("Value Research", "https://www.youtube.com/@ValueResearchOnline"),
    ]
    return links[:n]
