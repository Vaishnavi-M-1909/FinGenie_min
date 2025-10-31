import pdfplumber
import pandas as pd
import re
from io import BytesIO
from datetime import datetime

try:
    import fitz  # PyMuPDF fallback
except Exception:
    fitz = None


# -------------------- MAIN ENTRY --------------------
def process_pdf_to_df(uploaded_file, return_text=False):
    """Extract text and parse Kotak dummy statement PDF."""
    text, meta = extract_text(uploaded_file)

    if not text.strip():
        df = pd.DataFrame(columns=["Date", "Description", "Amount", "Type"])
        return (df, text, meta) if return_text else df

    df = parse_kotak_statement(text)
    return (df, text, meta) if return_text else df


# -------------------- PDF TEXT EXTRACTION --------------------
def extract_text(uploaded_file):
    """Extract selectable text using pdfplumber, fallback to PyMuPDF."""
    diag = {"engine": "", "pages": 0, "note": ""}
    raw = uploaded_file.read() if hasattr(uploaded_file, "read") else uploaded_file.getvalue()

    try:
        with pdfplumber.open(BytesIO(raw)) as pdf:
            diag["engine"] = "pdfplumber"
            diag["pages"] = len(pdf.pages)
            text = "\n".join([page.extract_text() or "" for page in pdf.pages])
            if text.strip():
                diag["note"] = "text extracted successfully"
                return text, diag
    except Exception as e:
        diag["note"] = f"pdfplumber failed: {e}"

    if fitz:
        try:
            doc = fitz.open(stream=raw, filetype="pdf")
            diag["engine"] = "pymupdf"
            diag["pages"] = len(doc)
            text = "\n".join([page.get_text("text") for page in doc])
            if text.strip():
                diag["note"] = "text extracted via PyMuPDF"
                return text, diag
        except Exception as e:
            diag["note"] = f"pymupdf failed: {e}"

    diag["note"] = "no selectable text detected"
    return "", diag


# -------------------- KOTAK PARSER (DUMMY FORMAT) --------------------
def parse_kotak_statement(text: str) -> pd.DataFrame:
    """
    Works for PDFs like:
    Date  ValueDate  Description  Debit  Credit  Balance  Type
    Example:
    02/09/2025 02/09/2025 SALARY CREDIT - ACME CORP 45000 95000 CREDIT
    03/09/2025 03/09/2025 UPI PAYMENT - SWIGGY -350 94650 DEBIT
    """

    lines = [ln.strip() for ln in text.splitlines() if re.match(r"^\d{2}/\d{2}/\d{4}", ln)]
    rows = []

    for ln in lines:
        # Split the line safely — multiple spaces possible
        parts = re.split(r"\s{2,}|\t+", ln.strip())

        # Sometimes Kotak statements use single spaces; fallback split
        if len(parts) < 5:
            parts = ln.split()

        if len(parts) < 6:
            continue

        # Extract fields
        date = parts[0]
        value_date = parts[1]

        # Description is everything between value_date and the last 3 columns
        desc = " ".join(parts[2:-3]).strip()

        # Last three columns are usually debit/credit, balance, type
        tail = parts[-3:]
        debit_or_credit, balance, ttype = tail

        # Identify amount
        amt = 0.0
        try:
            amt = float(debit_or_credit.replace(",", ""))
        except:
            # Try if amount is missing or negative sign separated
            amt_match = re.search(r"-?\d+\.?\d*", debit_or_credit)
            if amt_match:
                amt = float(amt_match.group(0))

        # Identify type
        ttype = ttype.strip().upper()
        if ttype == "BALANCE":
            continue
        txn_type = "Credit" if ttype == "CREDIT" else "Debit"

        # Absolute amount for analytics
        rows.append(
            {
                "Date": safe_date(date),
                "Description": desc,
                "Amount": abs(amt),
                "Type": txn_type,
                "Balance": try_float(balance),
            }
        )

    df = pd.DataFrame(rows, columns=["Date", "Description", "Amount", "Type", "Balance"])
    return df


# -------------------- HELPERS --------------------
def safe_date(s):
    for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except:
            pass
    return s


def try_float(x):
    try:
        return float(str(x).replace(",", ""))
    except:
        return None


def compute_basic_stats(df):
    if df.empty:
        return {"n_txn": 0, "sum_debits": 0.0, "sum_credits": 0.0}
    debits = df.loc[df["Type"] == "Debit", "Amount"].sum()
    credits = df.loc[df["Type"] == "Credit", "Amount"].sum()
    return {
        "n_txn": int(len(df)),
        "sum_debits": float(debits),
        "sum_credits": float(credits),
    }


# -------------------- OFFLINE CHATBOT --------------------
def mini_chatbot(msg: str) -> str:
    msg = msg.lower().strip()
    if not msg:
        return "Ask me about budgeting, savings, or investments!"
    if "budget" in msg:
        return "Try the 50/30/20 rule: 50% needs, 30% wants, 20% savings."
    if "save" in msg:
        return "Set automatic transfers to your savings account on salary day."
    if "invest" in msg:
        return "Start small SIPs once you’ve built an emergency fund."
    if "credit" in msg:
        return "Pay full dues monthly and keep credit usage under 30%."
    return "I'm your offline FinGenie! Ask about budgeting, saving, or investing."


# -------------------- FINANCE VIDEO LINKS --------------------
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
