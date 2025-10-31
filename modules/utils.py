import pdfplumber
import pandas as pd
import re
from io import BytesIO
from datetime import datetime

try:
    import fitz  # PyMuPDF fallback
except Exception:
    fitz = None

DATE_PATTERNS = [
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    r"\b\d{1,2}-[A-Za-z]{3}-\d{2,4}\b",
]
AMOUNT_PAT = r"(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)"

def process_pdf_to_df(uploaded_file, return_text=False):
    text, meta = extract_text(uploaded_file)
    if not text.strip():
        df = pd.DataFrame(columns=["Date","Description","Amount","Type"])
        return (df, text, meta) if return_text else df
    df = parse_kotak_statement(text)
    return (df, text, meta) if return_text else df

def extract_text(uploaded_file):
    diag = {"engine":"","pages":0,"note":""}
    raw = uploaded_file.read() if hasattr(uploaded_file,"read") else uploaded_file.getvalue()
    try:
        with pdfplumber.open(BytesIO(raw)) as pdf:
            diag["engine"]="pdfplumber"; diag["pages"]=len(pdf.pages)
            text="\n".join([p.extract_text() or "" for p in pdf.pages])
            if text.strip(): return text,diag
    except: pass
    if fitz:
        try:
            doc=fitz.open(stream=raw,filetype="pdf")
            diag["engine"]="pymupdf"; diag["pages"]=len(doc)
            text="\n".join([p.get_text("text") for p in doc])
            return text,diag
        except: pass
    diag["note"]="no selectable text"
    return "",diag

def parse_kotak_statement(text):
    """Parse Kotak dummy statement"""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    rows = []
    for ln in lines:
        if not re.match(r"^\d{2}/\d{2}/\d{4}", ln): 
            continue
        parts = ln.split()
        if len(parts) < 6:
            continue
        try:
            date = parts[0]
            desc = " ".join(parts[2:-3])
            debit, credit, balance, ttype = parts[-4:]
            amt = float(debit.replace("-", "")) if debit.startswith("-") else (float(credit) if credit.replace(".", "", 1).isdigit() else 0)
            ttype = "Debit" if debit.startswith("-") else "Credit" if credit.replace(".", "", 1).isdigit() else "Balance"
            rows.append({"Date": safe_date(date), "Description": desc, "Amount": amt, "Type": ttype})
        except Exception:
            continue
    return pd.DataFrame(rows)

def safe_date(s):
    for fmt in ("%d/%m/%Y","%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except:
            pass
    return s

def compute_basic_stats(df):
    if df.empty:
        return {"n_txn":0,"sum_debits":0.0,"sum_credits":0.0}
    debits=df.loc[df["Type"]=="Debit","Amount"].sum()
    credits=df.loc[df["Type"]=="Credit","Amount"].sum()
    return {"n_txn":len(df),"sum_debits":debits,"sum_credits":credits}

def mini_chatbot(msg:str)->str:
    msg=msg.lower().strip()
    if not msg: return "Ask about budgeting, savings, or investments."
    if "budget" in msg: return "Use 50/30/20 rule: 50% needs, 30% wants, 20% savings."
    if "save" in msg: return "Start an auto-transfer to a savings account on salary day."
    if "invest" in msg: return "Begin SIPs in index funds after emergency fund setup."
    if "credit" in msg: return "Pay credit cards in full before due date."
    return "Try asking about 'saving', 'budget', or 'credit card tips'."

def youtube_search_links(topic:str,n=8):
    topic_q = "+".join(topic.split())
    base = "https://www.youtube.com/results?search_query="
    links=[
        ("Search Results", base + topic_q),
        ("CA Rachana Ranade", "https://www.youtube.com/@CArachana"),
        ("Pranjal Kamra", "https://www.youtube.com/@PranjalKamra"),
        ("Think School", "https://www.youtube.com/@ThinkSchoolOfficial"),
        ("B Wealthy", "https://www.youtube.com/@BWealthy")
    ]
    return links[:n]
