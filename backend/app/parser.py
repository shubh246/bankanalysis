import io
import re
from datetime import date, datetime
from typing import Optional

import pandas as pd
import pdfplumber

DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
    "%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
    "%d %b %Y", "%d-%b-%Y", "%d-%b-%y", "%d %B %Y",
    "%b %d, %Y", "%B %d, %Y",
    "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%m/%d/%y",
]

DATE_COL_HINTS = [
    "date", "txn date", "txndate", "value date", "valuedate",
    "transaction date", "post date", "tran date", "trans date", "dt", "booking date"
]
DESC_COL_HINTS = [
    "description", "narration", "particulars", "details", "remarks",
    "transaction details", "chq/ref no", "summary", "tran particulars",
    "transaction description", "notes"
]
DEBIT_COL_HINTS = [
    "debit", "withdrawal", "dr", "withdrawal amt", "withdrawal amt.",
    "debit amount", "withdrawals", "dr amt", "withdrawals (dr)", "debit (dr)"
]
CREDIT_COL_HINTS = [
    "credit", "deposit", "cr", "deposit amt", "deposit amt.",
    "credit amount", "deposits", "cr amt", "deposits (cr)", "credit (cr)"
]
AMOUNT_COL_HINTS = [
    "amount", "amt", "txn amount", "transaction amount",
    "amount(rs.)", "amount (in rs.)", "amount (rs)", "transaction amt"
]
BALANCE_COL_HINTS = [
    "balance", "closing balance", "available balance", "bal",
    "balance(rs.)", "running balance", "balance (in rs.)", "bal (rs)"
]
TYPE_COL_HINTS = [
    "type", "dr/cr", "cr/dr", "indicator", "txn type", "transaction type", "cr/dr ind", "d/c"
]

# Regex patterns to pull a counterparty name out of common bank narration formats
UPI_PATTERN = re.compile(r"\bUPI\b", re.I)
UPI_NAME_PATTERN = re.compile(r"\bUPI[\-/](?:CR|DR)?[\-/]?\d*[\-/]([A-Za-z0-9 .]+?)[\-/]", re.I)
UPI_VPA_PATTERN = re.compile(r"\b([a-zA-Z0-9.\-_]{2,})@([a-zA-Z][a-zA-Z0-9]{1,})\b")

CHANNEL_PATTERNS = [
    ("NEFT", re.compile(r"NEFT[\-/][A-Z0-9]+[\-/]([A-Za-z0-9 .]+?)[\-/]", re.I)),
    ("IMPS", re.compile(r"IMPS[\-/][0-9]+[\-/]([A-Za-z0-9 .]+?)[\-/]", re.I)),
    ("RTGS", re.compile(r"RTGS[\-/][A-Z0-9]+[\-/]([A-Za-z0-9 .]+?)[\-/]", re.I)),
    ("ACH", re.compile(r"ACH[\-/]([A-Za-z0-9 .]+?)[\-/]", re.I)),
    ("POS", re.compile(r"POS[\s\-/]\d*[\s\-/]?([A-Za-z0-9 .]+)", re.I)),
]
ATM_PATTERN = re.compile(r"\b(ATM|CASH WDL|CASH WITHDRAWAL)\b", re.I)
CHQ_PATTERN = re.compile(r"\b(CHQ|CHEQUE|INWARD CHQ|OUTWARD CHQ)\b", re.I)
INT_PATTERN = re.compile(r"\b(INTEREST|INT\.? PAID|CREDIT INTEREST)\b", re.I)


def _clean_number(val) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val) if val == val else None
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "-", "nil", "null", "n/a"):
        return None

    # Remove currency symbols and common labels
    s = re.sub(r"[₹$€£]", "", s)
    s = re.sub(r"\b(rs\.?|inr)\b", "", s, flags=re.I).strip()
    s = s.replace(",", "")

    is_dr = bool(re.search(r"\b(dr)\b", s, re.I)) or s.startswith("-") or (s.startswith("(") and s.endswith(")"))
    is_cr = bool(re.search(r"\b(cr)\b", s, re.I))

    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1]

    s = re.sub(r"\b(dr|cr)\b", "", s, flags=re.I).strip()

    try:
        num = float(s)
    except ValueError:
        return None

    if is_dr:
        return -abs(num)
    if is_cr:
        return abs(num)
    return num


def _parse_date(val) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, (date, datetime)):
        return val.date() if isinstance(val, datetime) else val
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "-", "n/a"):
        return None

    s_clean = s.split()[0] if " " in s and re.search(r"\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}", s) else s

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s_clean, fmt).date()
        except ValueError:
            pass
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass

    try:
        dt = pd.to_datetime(s, dayfirst=True, errors="raise")
        return dt.date()
    except Exception:
        return None


def extract_counterparty(description: str) -> tuple[str, str]:
    """Return (counterparty_name, channel) best-effort guess from a narration string."""
    if not description:
        return ("Unknown", "OTHER")
    desc = description.strip()

    if UPI_PATTERN.search(desc):
        m = UPI_NAME_PATTERN.search(desc)
        if m:
            name = m.group(1).strip(" .-_")
            if name and len(name) > 1:
                return (name.title(), "UPI")
        vpa = UPI_VPA_PATTERN.search(desc)
        if vpa:
            handle = vpa.group(1).strip(" .-_")
            if handle:
                return (handle.title(), "UPI")
        return (desc[:60], "UPI")

    for channel, pattern in CHANNEL_PATTERNS:
        m = pattern.search(desc)
        if m:
            name = m.group(1).strip(" -/").strip()
            if name:
                return (name.title(), channel)
            return (desc[:60], channel)

    if ATM_PATTERN.search(desc):
        return ("ATM Withdrawal", "ATM")
    if CHQ_PATTERN.search(desc):
        return ("Cheque", "CHQ")
    if INT_PATTERN.search(desc):
        return ("Bank Interest", "INTEREST")

    fallback = re.sub(r"\s+", " ", desc)
    return (fallback[:60], "OTHER")


def _find_col(columns: list[str], hints: list[str]) -> Optional[str]:
    lower_map = {c.lower().strip(): c for c in columns}
    for hint in hints:
        if hint in lower_map:
            return lower_map[hint]
    for hint in hints:
        for lc, orig in lower_map.items():
            if hint in lc:
                return orig
    return None


def _normalize_dataframe(df: pd.DataFrame) -> list[dict]:
    df = df.dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]
    cols = list(df.columns)

    date_col = _find_col(cols, DATE_COL_HINTS)
    desc_col = _find_col(cols, DESC_COL_HINTS)
    debit_col = _find_col(cols, DEBIT_COL_HINTS)
    credit_col = _find_col(cols, CREDIT_COL_HINTS)
    amount_col = _find_col(cols, AMOUNT_COL_HINTS) if not (debit_col and credit_col) else None
    balance_col = _find_col(cols, BALANCE_COL_HINTS)
    type_col = _find_col(cols, TYPE_COL_HINTS)

    rows = []
    for _, r in df.iterrows():
        desc = str(r.get(desc_col, "")).strip() if desc_col else ""
        if desc.lower() == "nan":
            desc = ""

        debit = _clean_number(r.get(debit_col)) if debit_col else None
        credit = _clean_number(r.get(credit_col)) if credit_col else None

        if amount_col and debit is None and credit is None:
            amt = _clean_number(r.get(amount_col))
            ind = str(r.get(type_col, "")).strip().lower() if type_col else ""
            if amt is not None:
                is_debit = "dr" in ind or "debit" in ind or amt < 0
                if is_debit:
                    debit = abs(amt)
                else:
                    credit = abs(amt)

        if debit is None and credit is None:
            if not desc:
                continue
            continue

        direction = "debit" if debit else "credit"
        amount = abs(debit) if debit else abs(credit)

        counterparty, channel = extract_counterparty(desc)

        rows.append({
            "date": _parse_date(r.get(date_col)) if date_col else None,
            "description": desc,
            "counterparty": counterparty,
            "channel": channel,
            "debit": debit,
            "credit": credit,
            "amount": amount,
            "direction": direction,
            "balance": _clean_number(r.get(balance_col)) if balance_col else None,
        })
    return rows


def parse_csv(content: bytes) -> list[dict]:
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            df = pd.read_csv(io.BytesIO(content), encoding=encoding)
            return _normalize_dataframe(df)
        except Exception:
            continue
    raise ValueError("Could not parse CSV file. Please check file formatting.")


def parse_excel(content: bytes) -> list[dict]:
    try:
        sheets = pd.read_excel(io.BytesIO(content), sheet_name=None)
    except Exception as e:
        raise ValueError(f"Could not parse Excel file: {e}")

    all_rows: list[dict] = []
    for df in sheets.values():
        try:
            all_rows.extend(_normalize_dataframe(df))
        except Exception:
            continue

    if not all_rows:
        raise ValueError("Could not parse tabular transaction data from this Excel file.")
    return all_rows


def _pad_or_truncate_row(row: list[str], target_len: int) -> list[str]:
    if len(row) == target_len:
        return row
    if len(row) < target_len:
        return row + [""] * (target_len - len(row))
    return row[:target_len]


def _clean_table_matrix(raw_table: list[list]) -> list[list[str]]:
    cleaned = []
    for row in raw_table:
        if not row:
            continue
        cleaned_row = [str(cell or "").replace("\r", "").replace("\n", " ").strip() for cell in row]
        if any(cleaned_row):
            cleaned.append(cleaned_row)
    return cleaned


def _merge_continuation_rows(table: list[list[str]]) -> list[list[str]]:
    if len(table) < 2:
        return table
    header = table[0]
    target_len = len(header)
    cols = [h.lower() for h in header]

    date_idx = next((i for i, c in enumerate(cols) if any(h in c for h in DATE_COL_HINTS)), None)
    desc_idx = next((i for i, c in enumerate(cols) if any(h in c for h in DESC_COL_HINTS)), None)
    num_indices = [i for i, c in enumerate(cols) if any(h in c for h in DEBIT_COL_HINTS + CREDIT_COL_HINTS + AMOUNT_COL_HINTS + BALANCE_COL_HINTS)]

    merged = [header]
    for row in table[1:]:
        row_norm = _pad_or_truncate_row(row, target_len)

        has_date = bool(date_idx is not None and row_norm[date_idx].strip())
        has_nums = any(row_norm[i].strip() for i in num_indices)

        if not has_date and not has_nums and desc_idx is not None and row_norm[desc_idx].strip():
            if len(merged) > 1:
                merged[-1][desc_idx] = (merged[-1][desc_idx] + " " + row_norm[desc_idx]).strip()
                continue

        merged.append(row_norm)
    return merged


def _parse_pdf_text_fallback(pdf: pdfplumber.PDF) -> list[dict]:
    all_text_lines = []
    for page in pdf.pages:
        text = page.extract_text()
        if text:
            all_text_lines.extend(text.splitlines())

    date_regex = re.compile(r"\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{1,2}[\/\-\.][A-Za-z]{3}[\/\-\.]\d{2,4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})\b")
    number_regex = re.compile(r"[\(]?[₹$€£]?\s*[\d,]+\.\d{2}\s*[\)]?\s*(?:Dr|Cr|DR|CR)?", re.I)

    rows = []
    for line in all_text_lines:
        line_str = line.strip()
        date_match = date_regex.search(line_str)
        if not date_match:
            continue

        numbers = number_regex.findall(line_str)
        if not numbers:
            continue

        parsed_date = _parse_date(date_match.group(1))
        narration = date_regex.sub("", line_str)
        narration = number_regex.sub("", narration)
        narration = re.sub(r"\s+", " ", narration).strip()

        cleaned_nums = [_clean_number(n) for n in numbers if _clean_number(n) is not None]
        if not cleaned_nums:
            continue

        amt = abs(cleaned_nums[0])
        balance = abs(cleaned_nums[-1]) if len(cleaned_nums) > 1 else None
        direction = "debit" if any("dr" in n.lower() or "-" in n for n in numbers) else "credit"

        counterparty, channel = extract_counterparty(narration)
        rows.append({
            "date": parsed_date,
            "description": narration,
            "counterparty": counterparty,
            "channel": channel,
            "debit": amt if direction == "debit" else None,
            "credit": amt if direction == "credit" else None,
            "amount": amt,
            "direction": direction,
            "balance": balance,
        })

    return rows


def parse_pdf(content: bytes, password: Optional[str] = None) -> list[dict]:
    try:
        pdf_file = pdfplumber.open(io.BytesIO(content), password=password)
    except Exception as e:
        err = str(e).lower()
        if "password" in err or "encrypted" in err or "protected" in err:
            raise ValueError("This PDF is password-protected. Please provide the correct password.")
        raise ValueError(f"Could not open PDF file: {e}")

    all_rows: list[dict] = []

    with pdf_file as pdf:
        cached_header: Optional[list[str]] = None

        for table_settings in [None, {"vertical_strategy": "text", "horizontal_strategy": "text", "snap_tolerance": 3}]:
            if all_rows:
                break
            for page in pdf.pages:
                try:
                    tables = page.extract_tables(table_settings) if table_settings else page.extract_tables()
                except Exception:
                    continue

                for table in tables:
                    cleaned_table = _clean_table_matrix(table)
                    if not cleaned_table or len(cleaned_table) < 2:
                        continue

                    first_row_str = " ".join([c.lower() for c in cleaned_table[0]])
                    has_header_hints = any(
                        hint in first_row_str
                        for hint in DATE_COL_HINTS + DESC_COL_HINTS + DEBIT_COL_HINTS + CREDIT_COL_HINTS + AMOUNT_COL_HINTS + BALANCE_COL_HINTS
                    )

                    if has_header_hints:
                        tbl_header = cleaned_table[0]
                        tbl_body = cleaned_table[1:]
                        cached_header = tbl_header
                    elif cached_header is not None and len(cleaned_table[0]) == len(cached_header):
                        tbl_header = cached_header
                        tbl_body = cleaned_table
                    else:
                        tbl_header = [f"col_{i}" for i in range(len(cleaned_table[0]))]
                        tbl_body = cleaned_table

                    if not tbl_body:
                        continue

                    merged_table = _merge_continuation_rows([tbl_header] + tbl_body)
                    tbl_header = merged_table[0]
                    tbl_body = merged_table[1:]

                    target_len = len(tbl_header)
                    norm_body = [_pad_or_truncate_row(r, target_len) for r in tbl_body]

                    try:
                        df = pd.DataFrame(norm_body, columns=tbl_header)
                        all_rows.extend(_normalize_dataframe(df))
                    except Exception:
                        continue

        if not all_rows:
            all_rows = _parse_pdf_text_fallback(pdf)

    if not all_rows:
        raise ValueError(
            "Could not parse tabular or transaction data from this PDF statement. "
            "If it is scanned or password protected, please ensure text is selectable or enter the correct password."
        )
    return all_rows


def parse_statement(filename: str, content: bytes, password: Optional[str] = None) -> list[dict]:
    lower = filename.lower()
    if lower.endswith(".csv"):
        rows = parse_csv(content)
    elif lower.endswith(".pdf"):
        rows = parse_pdf(content, password=password)
    elif lower.endswith(".xlsx") or lower.endswith(".xls"):
        rows = parse_excel(content)
    else:
        raise ValueError("Unsupported file type. Please upload a .csv, .xlsx, .xls, or .pdf file.")

    if not rows:
        raise ValueError("No transactions could be parsed from this file.")
    return rows

