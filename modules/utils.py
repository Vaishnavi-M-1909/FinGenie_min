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
    """Extract text and parse transactions from a Kotak-style dummy statement."""
    text, meta = extract_text(uploaded_file)

    if not text.strip():
        df = pd.DataFrame(columns=["Date", "Description", "Amount", "Type"])
        return (df, text, meta) if return_text else df

    df = parse_kotak_statement(text)
    if df.empty:
        meta["note"] = "Parsing returned 0 rows — check extracted text format."
    return (df, text, meta) if return_text else df


# -------------------- PDF TEXT EXTRACTION --------------------
def extract_text(uploaded_file):
    """Extract text using pdfplumber or PyMuPDF."""
    diag = {"engine": "", "pages": 0, "note": ""}
    raw = uploaded_file.read() if hasattr(uploaded_file, "read") else uploaded_file.getvalue()

    # Try pdfplumber first
    try:
        with pdfplumber.open(BytesIO(raw)) as pdf:
            diag["engine"] = "pdfplumber"
            diag["pages"] = len(pdf.pages)
            text = "\n".join([p.extract_text() or "" for p in pdf.pages])
            if text.strip():
                diag["note"] = "Text extracted successfully via pdfplumber"
                return text, diag
    except Exception as e:
        diag["note"] = f"pdfplumber failed: {e}"

    # Try PyMuPDF fallback
    if fitz:
        try:
            doc = fitz.open(stream=raw, filetype="pdf")
            diag["engine"] = "pymupdf"
            diag["pages"] = len(doc)
            text = "\n".join([p.get_text("text") for p in doc])
            if text.strip():
                diag["note"] = "Text extracted successfully via PyMuPDF"
                return text, diag
        except Exception as e:
            diag["note"] = f"pymupdf failed: {e}"

    diag["note"] = "No selectable text detected."
    return "", diag


# -------------------- UNIVERSAL KOTAK PARSER --------------------
def parse_kotak_statement(text: str) -> pd.DataFrame:
    """
    Parses Kotak-style statements like:
    02/09/2025 02/09/2025 SALARY CREDIT - ACME CORP 45000 95000 CREDIT
    03/09/2025 03/09/2025 UPI PAYMENT - SWIGGY 9876543210 -350 94650 DEBIT
    05/09/2025 05/09/2025 AMAZON ONLINE 1250.50 DR 93400.50
    """

    lines = [ln.strip() for ln in text.splitlines() if re.search(r"\d{2}/\d{2}/\d{4}", ln)]
    data = []

    for ln in lines:
        # Skip headers and non-transaction lines
        if any(x in ln.lower() for x in ["date", "opening", "closing", "summary"]):
            continue

        # Normalize whitespace
        ln = re.sub(r"\s+", " ", ln.strip())

        # --- Extract date(s) ---
        dates = re.findall(r"\d{2}/\d{2}/\d{4}", ln)
        if not dates:
            continue
        date = dates[0]

        # --- Extract Type (Credit/Debit/CR/DR) ---
        ttype = "Credit" if re.search(r"\b(CR|CREDIT)\b", ln, re.I) else \
                "Debit" if re.search(r"\b(DR|DEBIT)\b", ln, re.I) else None
        if not ttype:
            continue

        # --- Extract all numbers ---
        nums = re.findall(r"-?\d{1,3}(?:,\d{3})*(?:\.\d+)?", ln)
        nums = [float(n.replace(",", "")) for n in nums]

        if len(nums) == 0:
            continue

        # Amount = last or second-last number depending on CR/DR order
        amount = 0.0
        balance = None

        if len(nums) >= 2:
            # Usually: [... amount balance ...]
            amount, balance = nums[-2], nums[-1]
        else:
            amount = nums[-1]

        # --- Description extraction ---
        desc = re.sub(r"\d{2}/\d{2}/\d{4}", "", ln)
        desc = re.sub(r"-?\d{1,3}(?:,\d{3})*(?:\.\d+)?", "", desc)
        desc = re.sub(r"\b(CREDIT|DEBIT|CR|DR)\b", "", desc, flags=re.I).strip()

        # Skip empty desc
        if not desc:
            continue

        data.append({
            "Date": safe_date(date),
            "Description": desc,
            "Amount": abs(amount),
            "Type": ttype,
            "Balance": balance,
        })

    return pd.DataFrame(data, columns=["Date", "Description", "Amount", "Type", "Balance"])


# -------------------- HELPERS --------------------
def safe_date(s):
    for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except:
            pass
    return s


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


# -------------------- OFFLINE MINI CHATBOT --------------------
def mini_chatbot(msg: str) -> str:
    msg = msg.lower().strip()
    if "budget" in msg:
        return "Try the 50/30/20 rule: 50% needs, 30% wants, 20% savings."
    if "save" in msg:
        return "Set automatic transfers to savings on salary day."
    if "invest" in msg:
        return "Start SIPs after your emergency fund is ready."
    if "credit" in msg:
        return "Pay full dues monthly and limit card usage to 30%."
    return "Ask about budgeting, saving, or investing — I'm your offline FinGenie!"


# -------------------- YOUTUBE LINKS --------------------
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
