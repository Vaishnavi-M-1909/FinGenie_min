import pdfplumber
import pandas as pd
import re
from io import BytesIO
from datetime import datetime

try:
    import fitz  # PyMuPDF fallback
except Exception:
    fitz = None


# -------------------- PDF Extraction --------------------
def process_pdf_to_df(uploaded_file, return_text=False):
    """Extract text and parse transactions into a DataFrame."""
    text, meta = extract_text(uploaded_file)

    if not text.strip():
        df = pd.DataFrame(columns=["Date", "Description", "Amount", "Type"])
        return (df, text, meta) if return_text else df

    df = parse_kotak_statement(text)
    return (df, text, meta) if return_text else df


def extract_text(uploaded_file):
    """Try pdfplumber → PyMuPDF to extract text from PDF."""
    diag = {"engine": "", "pages": 0, "note": ""}
    raw = uploaded_file.read() if hasattr(uploaded_file, "read") else uploaded_file.getvalue()

    # --- Try pdfplumber first ---
    try:
        with pdfplumber.open(BytesIO(raw)) as pdf:
            diag["engine"] = "pdfplumber"
            diag["pages"] = len(pdf.pages)
            text = "\n".join([p.extract_text() or "" for p in pdf.pages])
            if text.strip():
                diag["note"] = "text extracted successfully"
                return text, diag
    except Exception as e:
        diag["note"] = f"pdfplumber failed: {e}"

    # --- Try PyMuPDF fallback ---
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


# -------------------- Parser (Kotak Dummy Statement) --------------------
def parse_kotak_statement(text: str) -> pd.DataFrame:
    """
    Parses Kotak-style dummy statements like:
    02/09/2025 02/09/2025 SALARY CREDIT - ACME CORP 45000 95000 CREDIT
    03/09/2025 03/09/2025 UPI PAYMENT - SWIGGY 9876543210 -350 94650 DEBIT
    """

    lines = [ln.strip() for ln in text.splitlines() if re.match(r"^\d{2}/\d{2}/\d{4}", ln)]
    rows = []

    for ln in lines:
        m = re.match(
            r"^(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(.*?)\s+(-?\d+(?:\.\d+)?)\s+([\d\.]+)\s+(CREDIT|DEBIT|BALANCE)",
            ln,
            re.IGNORECASE,
        )
        if not m:
            continue

        date, value_date, desc, amount, balance, ttype = m.groups()
        amount = float(amount)
        ttype = ttype.upper()

        if ttype == "BALANCE":
            continue

        rows.append(
            {
                "Date": safe_date(date),
                "Description": desc.strip(),
                "Amount": abs(amount),
                "Type": "Credit" if ttype == "CREDIT" else "Debit",
                "Balance": float(balance),
            }
        )

    return pd.DataFrame(rows, columns=["Date", "Description", "Amount", "Type", "Balance"])


# -------------------- Helpers --------------------
def safe_date(s):
    """Convert date string safely."""
    for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except:
            pass
    return s


def compute_basic_stats(df):
    """Compute total credits/debits."""
    if df.empty:
        return {"n_txn": 0, "sum_debits": 0.0, "sum_credits": 0.0}

    debits = df.loc[df["Type"] == "Debit", "Amount"].sum()
    credits = df.loc[df["Type"] == "Credit", "Amount"].sum()

    return {
        "n_txn": int(len(df)),
        "sum_debits": float(debits),
        "sum_credits": float(credits),
    }


# -------------------- Offline Chatbot --------------------
def mini_chatbot(msg: str) -> str:
    msg = msg.lower().strip()
    if not msg:
        return "Ask me about budgeting, savings, investments, or reading your statement."
    if "budget" in msg:
        return "Use the 50/30/20 rule: 50% needs, 30% wants, 20% savings."
    if "save" in msg:
        return "Set an auto-transfer to a savings account right after salary credit."
    if "invest" in msg:
        return "Start SIPs in index funds once you have an emergency fund ready."
    if "credit" in msg:
        return "Pay credit cards in full each month. Keep usage under 30%."
    return "Try asking about budgeting, saving, or investment tips!"


# -------------------- Video Links --------------------
def youtube_search_links(topic: str, n=8):
    """Static finance YouTube list."""
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
