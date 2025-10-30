import pdfplumber
import pandas as pd
import re
from io import BytesIO
from datetime import datetime

# Optional fallbacks
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

# For decrypting to bytes for OCR if needed
try:
    from PyPDF2 import PdfReader, PdfWriter
except Exception:
    PdfReader = None
    PdfWriter = None

# OCR lazy imports (only used when OCR requested)
def _lazy_ocr_modules():
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
        return convert_from_bytes, pytesseract
    except Exception:
        return None, None

# ---------- patterns ----------
DATE_PATTERNS = [
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    r"\b\d{1,2}-[A-Za-z]{3}-\d{2,4}\b",
    r"\b[A-Za-z]{3}\s+\d{1,2},\s*\d{4}\b",
]
AMOUNT_PAT = r"([+-]?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|[+-]?\d+(?:\.\d{1,2})?)"
CRDR_PAT = r"\b(CR|CREDIT|Cr|Credit|DR|DEBIT|Dr|Debit)\b"

# ---------- public entry ----------
def process_pdf_to_df(uploaded_file, return_text: bool = False, force_ocr: bool = False, password: str = None):
    """
    uploaded_file: Streamlit uploaded file (file-like)
    password: optional password string (not saved)
    """
    text, meta = extract_text(uploaded_file, force_ocr=force_ocr, password=password)
    if not text.strip():
        empty = pd.DataFrame(columns=["Date", "Description", "Amount", "Type"])
        return (empty, text, meta) if return_text else empty

    bank = detect_bank(text)
    if bank == "kotak":
        df = parse_kotak_statement(text)
    else:
        df = parse_text_generic(text)

    # Overwrite local password variable (best-effort)
    password = None

    return (df, text, meta) if return_text else df

# ---------- extraction ----------
def extract_text(uploaded_file, force_ocr: bool = False, password: str = None):
    """
    Tries:
      1) pdfplumber (with password if provided)
      2) PyMuPDF fallback (with password if provided)
      3) OCR (pytesseract) — if force_ocr True or no selectable text found.
    Returns (text, diagnostics)
    """
    diag = {"engine": "", "pages": 0, "note": ""}
    raw = uploaded_file.read() if hasattr(uploaded_file, "read") else uploaded_file.getvalue()

    # 1) pdfplumber
    try:
        # pdfplumber supports password arg
        with pdfplumber.open(BytesIO(raw), password=password) as pdf:
            diag["engine"] = "pdfplumber"
            diag["pages"] = len(pdf.pages)
            chunks = []
            for p in pdf.pages:
                t = p.extract_text() or ""
                chunks.append(t)
            text = "\n".join(chunks)
            if text.strip():
                diag["note"] = "text extracted (pdfplumber)"
                return text, diag
    except Exception as e:
        diag["note"] = f"pdfplumber error: {e}"

    # 2) PyMuPDF fallback
    if fitz is not None:
        try:
            # PyMuPDF accepts a password via doc.authenticate OR open with stream and password
            # We'll try to open; if encrypted, authenticate
            doc = None
            try:
                doc = fitz.open(stream=raw, filetype="pdf")
                if doc.is_encrypted:
                    if password:
                        ok = doc.authenticate(password)
                        if not ok:
                            raise RuntimeError("PyMuPDF: wrong password")
                    else:
                        raise RuntimeError("PyMuPDF: file is encrypted")
            except Exception:
                # try open with read-only method that accepts a password (older versions may support password param)
                doc = fitz.open(stream=raw, filetype="pdf", password=password)
            diag["engine"] = "pymupdf"
            diag["pages"] = len(doc)
            chunks = []
            for page in doc:
                chunks.append(page.get_text("text") or "")
            text = "\n".join(chunks)
            if text.strip():
                diag["note"] = "text extracted (PyMuPDF)"
                return text, diag
        except Exception as e:
            diag["note"] = (diag.get("note","") + " | pymupdf error: " + str(e))[:1000]

    # 3) OCR fallback (only when forced or when no selectable text)
    convert_from_bytes, pytesseract = _lazy_ocr_modules()
    if (force_ocr or "no text" in diag.get("note","").lower()) and convert_from_bytes and pytesseract:
        # If PDF is encrypted, we must first decrypt into bytes for pdf2image
        dec_bytes = None
        if password and PdfReader is not None:
            try:
                reader = PdfReader(BytesIO(raw))
                if reader.is_encrypted:
                    try:
                        reader.decrypt(password)
                    except Exception:
                        # try with empty or raise
                        pass
                writer = PdfWriter()
                for p in reader.pages:
                    writer.add_page(p)
                out = BytesIO()
                writer.write(out)
                dec_bytes = out.getvalue()
            except Exception as e:
                diag["note"] = (diag.get("note","") + " | PyPDF2 decrypt error: " + str(e))[:1000]
                dec_bytes = None

        source_bytes = dec_bytes if dec_bytes is not None else raw
        try:
            images = convert_from_bytes(source_bytes, dpi=300)
            diag["engine"] = "ocr"
            diag["pages"] = len(images)
            ocr_chunks = []
            for img in images:
                ocr_chunks.append(pytesseract.image_to_string(img, config="--oem 1 --psm 6"))
            text = "\n".join(ocr_chunks)
            if text.strip():
                diag["note"] = "text extracted (OCR)"
                return text, diag
        except Exception as e:
            diag["note"] = (diag.get("note","") + " | OCR error: " + str(e))[:1000]

    diag["engine"] = diag.get("engine") or "none"
    diag["note"] = (diag.get("note", "") + " | no text detected; check OCR dependencies or password").strip()
    return "", diag

# ---------- bank detection ----------
def detect_bank(text: str) -> str:
    t = text.lower()
    if "kotak mahindra bank" in t or (
        "withdrawal amt" in t and "deposit amt" in t and "balance" in t
    ):
        return "kotak"
    return "generic"

# ---------- Kotak-specific parser ----------
def parse_kotak_statement(text: str) -> pd.DataFrame:
    date_head = re.compile(rf"^\s*({'|'.join(DATE_PATTERNS)})")
    lines = [ln.rstrip() for ln in text.splitlines()]

    blocks, cur = [], []
    for ln in lines:
        if date_head.search(ln):
            if cur:
                blocks.append("\n".join(cur))
                cur = []
        cur.append(ln)
    if cur:
        blocks.append("\n".join(cur))

    rows = []
    for blk in blocks:
        dmatch = re.search("|".join(DATE_PATTERNS), blk)
        if not dmatch:
            continue
        date_str = dmatch.group(0)
        one = " ".join(ln.strip() for ln in blk.splitlines())
        nums = re.findall(AMOUNT_PAT, one.replace("₹", "").replace("INR", ""))
        nums = [n for n in nums if n.strip()]
        if not nums:
            continue
        bal_token = nums[-1]
        tail = nums[:-1] if len(nums) > 1 else []
        txn_amount = None
        for tok in reversed(tail):
            try:
                v = float(tok.replace(",", ""))
                if abs(v) > 0:
                    txn_amount = v
                    break
            except:
                continue
        if txn_amount is None:
            try:
                txn_amount = float(bal_token.replace(",", ""))
            except:
                continue
        date_union = "(" + "|".join(DATE_PATTERNS) + ")"
        narration = re.sub(date_union, "", one).strip()
        narration = re.sub(rf"{AMOUNT_PAT}\s*(Cr|DR|CR|Dr)?\s*$", "", narration, flags=re.IGNORECASE).strip(" -:|")
        low = one.lower()
        ttype = "Credit" if re.search(r"\bcr\b|\bcredit\b|\bdeposit\b", low) else "Debit"
        if re.search(r"\bdr\b|\bdebit\b|\bwithdraw", low):
            ttype = "Debit"
        rows.append({
            "Date": safe_date(date_str),
            "Description": narration if narration else "—",
            "Amount": abs(txn_amount),
            "Type": ttype
        })
    return pd.DataFrame(rows, columns=["Date", "Description", "Amount", "Type"])

# ---------- generic fallback ----------
def parse_text_generic(text: str) -> pd.DataFrame:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    rows = []
    date_union = "(" + "|".join(DATE_PATTERNS) + ")"
    for ln in lines:
        d = re.search(date_union, ln)
        if not d:
            continue
        marker = re.search(CRDR_PAT, ln)
        nums = re.findall(AMOUNT_PAT, ln.replace("₹", "").replace("INR", ""))
        if not nums:
            continue
        amount_raw = nums[-1].replace(",", "")
        try:
            amount = float(amount_raw)
        except:
            continue
        date_str = d.group(0)
        desc = re.sub(date_union, "", ln).strip()
        desc = re.sub(rf"{AMOUNT_PAT}\s*(Cr|Dr)?$", "", desc, flags=re.IGNORECASE).strip(" -:|")
        ttype = "Credit" if (marker and marker.group(0).lower().startswith("cr")) or " credit" in ln.lower() else "Debit"
        rows.append({
            "Date": safe_date(date_str),
            "Description": desc if desc else "—",
            "Amount": abs(amount),
            "Type": ttype
        })
    return pd.DataFrame(rows, columns=["Date", "Description", "Amount", "Type"])

# ---------- helpers ----------
def safe_date(s):
    fmts = [
        "%d/%m/%Y","%d-%m-%Y","%d/%m/%y","%d-%m-%y",
        "%m/%d/%Y","%m-%d-%Y",
        "%d-%b-%y","%d-%b-%Y",
        "%b %d, %Y"
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt).date()
        except:
            continue
    return s

def compute_basic_stats(df):
    if df.empty:
        return {"n_txn": 0, "sum_debits": 0.0, "sum_credits": 0.0}
    debits = df.loc[df["Type"] == "Debit", "Amount"].sum()
    credits = df.loc[df["Type"] == "Credit", "Amount"].sum()
    return {"n_txn": int(len(df)), "sum_debits": float(debits), "sum_credits": float(credits)}

# ---------- tiny offline chatbot ----------
def mini_chatbot(message: str) -> str:
    if not message or not message.strip():
        return "Ask me about budgeting, savings, EMIs, credit vs debit, or how to read your statement."
    msg = message.lower().strip()
    if any(w in msg for w in ["budget","save","saving","spend less"]):
        return ("Use the 50/30/20 rule: 50% needs, 30% wants, 20% savings/debt. "
                "Automate savings on salary day and track your top 3 spend categories.")
    if "credit card" in msg or "cc" in msg:
        return ("Pay full before due date, keep utilization <30%, avoid cash advances, align big spends just after statement date.")
    if "emergency" in msg:
        return ("Target 3–6 months of core expenses in high-liquidity. Start with 1 month and scale up.")
    if any(w in msg for w in ["invest","mutual fund","sip","fd","rd"]):
        return ("Start a simple SIP only after building emergency buffer and clearing high-interest debt. Prefer diversified index/balanced funds.")
    return ("I'm a lightweight offline assistant. Ask budgeting, emergency funds, credit-card tips, or reading your statement.")

# ---------- video links (no scraping) ----------
def youtube_search_links(topic: str, n=8):
    topic_q = "+".join(topic.split())
    url = f"https://www.youtube.com/results?search_query={topic_q}+personal+finance"
    results = [
        ("Search on YouTube", url),
        ("CA Rachana Ranade", "https://www.youtube.com/@CArachana"),
        ("B Wealthy", "https://www.youtube.com/@BWealthy"),
        ("Pranjal Kamra", "https://www.youtube.com/@PranjalKamra"),
        ("Value Research", "https://www.youtube.com/@ValueResearchOnline"),
        ("Think School", "https://www.youtube.com/@ThinkSchoolOfficial"),
    ]
    return results[:n]
