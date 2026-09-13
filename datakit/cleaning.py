"""Reusable cleaning helpers for messy Polish business data (Excel / CSV).

Every function takes and returns a pandas Series, so they compose inside
``df.assign(...)`` and can be reused as-is between client jobs.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta

import pandas as pd

NULL_TOKENS = {"", "-", "--", "?", "brak", "n/a", "na", "null", "none", "nan", "nat", "<na>"}

_PL_ASCII = str.maketrans("łŁ", "lL")


# --------------------------------------------------------------------------- text
def strip_accents(text: str) -> str:
    """'Łódź' -> 'Lodz'. Used to build matching keys, never for display."""
    text = text.translate(_PL_ASCII)
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def clean_text(s: pd.Series) -> pd.Series:
    """Trim, collapse inner whitespace and turn placeholder values ('brak', '-') into NA."""
    out = s.astype("string").str.replace(r"\s+", " ", regex=True).str.strip()
    is_null = out.str.lower().isin(NULL_TOKENS).fillna(False).astype(bool)
    return out.mask(is_null)


def normalize_key(s: pd.Series) -> pd.Series:
    """Case-, accent- and punctuation-insensitive key for matching/joining."""
    return clean_text(s).map(
        lambda v: re.sub(r"[^a-z0-9]", "", strip_accents(v).lower()) if pd.notna(v) else pd.NA
    ).astype("string")


TITLES = r"^(pan|pani|p\.|dr|mgr|inż\.?|prof\.?)\s+"


def normalize_person_name(s: pd.Series) -> pd.Series:
    """'  pani ANNA   kowalska-NOWAK ' -> 'Anna Kowalska-Nowak'."""
    out = clean_text(s).str.replace(TITLES, "", regex=True, flags=re.IGNORECASE)
    return out.str.title()


def split_full_name(s: pd.Series) -> pd.DataFrame:
    """Split 'Imię Nazwisko' into two columns (first token = first name)."""
    parts = s.str.split(" ", n=1, expand=True).reindex(columns=[0, 1])
    return pd.DataFrame({"imie": parts[0], "nazwisko": parts[1]}, index=s.index).astype("string")


# --------------------------------------------------------------------------- contact
EMAIL_RE = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}$")
EMAIL_DOMAIN_TYPOS = {
    "gmial.com": "gmail.com", "gmai.com": "gmail.com", "gmail.pl": "gmail.com",
    "gmail,com": "gmail.com", "wp,pl": "wp.pl", "onet,pl": "onet.pl",
    "interia,pl": "interia.pl", "o2,pl": "o2.pl",
}


def _fix_email(value: str) -> str | None:
    value = value.lower().replace(" ", "")
    if "@" in value:
        local, _, domain = value.rpartition("@")
        value = f"{local}@{EMAIL_DOMAIN_TYPOS.get(domain, domain)}"
    return value if EMAIL_RE.match(value) else None


def normalize_email(s: pd.Series) -> pd.Series:
    """Lower-case, drop spaces, fix common domain typos; invalid addresses -> NA."""
    return clean_text(s).map(lambda v: _fix_email(v) if pd.notna(v) else None).astype("string")


def _fix_phone(value: str) -> str | None:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 13 and digits.startswith("0048"):
        digits = digits[4:]
    elif len(digits) == 11 and digits.startswith("48"):
        digits = digits[2:]
    if len(digits) != 9:
        return None
    return f"+48 {digits[:3]} {digits[3:6]} {digits[6:]}"


def normalize_phone_pl(s: pd.Series) -> pd.Series:
    """Any Polish phone notation -> '+48 123 456 789'; anything else -> NA."""
    return clean_text(s).str.replace(r"\.0$", "", regex=True).map(
        lambda v: _fix_phone(v) if pd.notna(v) else None
    ).astype("string")


def normalize_postal_code_pl(s: pd.Series) -> pd.Series:
    """'00950', '00-950' and Excel's '950' (lost leading zeros) -> '00-950'."""
    def fix(value: str) -> str | None:
        raw = value.removesuffix(".0")
        digits = re.sub(r"\D", "", raw)
        if raw.isdigit() and 3 <= len(digits) < 5:  # Excel stored the code as a number
            digits = digits.zfill(5)
        return f"{digits[:2]}-{digits[2:]}" if len(digits) == 5 else None

    return clean_text(s).map(lambda v: fix(v) if pd.notna(v) else None).astype("string")


# --------------------------------------------------------------------------- numbers & dates
def _parse_number(value: str) -> float | None:
    text = re.sub(r"(?i)(zł|pln|zl)", "", value)
    text = re.sub(r"[\s ]", "", text)
    if "," in text and "." in text:  # the right-most separator is the decimal one
        thousands = "." if text.rfind(",") > text.rfind(".") else ","
        text = text.replace(thousands, "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    elif text.count(".") > 1:
        text = text.replace(".", "")
    try:
        return float(text)
    except ValueError:
        return None


def parse_pl_number(s: pd.Series) -> pd.Series:
    """'1 234,50 zł', 'PLN 1.234,50', '1234.5' -> 1234.5 (float); garbage -> NaN."""
    return pd.to_numeric(clean_text(s).map(lambda v: _parse_number(v) if pd.notna(v) else None))


EXCEL_EPOCH = datetime(1899, 12, 30)
_DATE_PATTERNS = [
    (re.compile(r"^\d{4}-\d{1,2}-\d{1,2}$"), "%Y-%m-%d"),
    (re.compile(r"^\d{4}/\d{1,2}/\d{1,2}$"), "%Y/%m/%d"),
    (re.compile(r"^\d{1,2}[./-]\d{1,2}[./-]\d{4}$"), "%d.%m.%Y"),
    (re.compile(r"^\d{1,2}[./-]\d{1,2}[./-]\d{2}$"), "%d.%m.%y"),
]


def _parse_date(value: str) -> datetime | None:
    value = re.sub(r"[ T]\d{1,2}:\d{2}(:\d{2})?$", "", value)  # drop '00:00:00' from Excel dates
    if re.fullmatch(r"\d{5}(\.0)?", value):  # Excel serial number, e.g. 45123
        return EXCEL_EPOCH + timedelta(days=int(float(value)))
    for pattern, fmt in _DATE_PATTERNS:
        if pattern.match(value):
            normalized = re.sub(r"[/-]", ".", value) if fmt.startswith("%d") else value
            try:
                return datetime.strptime(normalized, fmt)
            except ValueError:  # e.g. 31.02.2023
                return None
    return None


def parse_mixed_dates(s: pd.Series) -> pd.Series:
    """Mixed PL date notations + Excel serials -> datetime64. Day-first, as used in Poland."""
    return pd.to_datetime(clean_text(s).map(lambda v: _parse_date(v) if pd.notna(v) else None))


# --------------------------------------------------------------------------- columns
def column_key(name: object) -> str:
    """' Kod poczt. ' -> 'kod_poczt'"""
    return re.sub(r"[^a-z0-9]+", "_", strip_accents(str(name)).lower()).strip("_")


def standardize_columns(df: pd.DataFrame, synonyms: dict[str, list[str]]) -> pd.DataFrame:
    """Rename columns to canonical names using a synonym list; fail loudly if any is missing."""
    lookup = {column_key(alias): canon for canon, aliases in synonyms.items() for alias in [canon, *aliases]}
    renamed = df.rename(columns=lambda c: lookup.get(column_key(c), c))
    missing = set(synonyms) - set(renamed.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}. Found: {list(df.columns)}")
    return renamed[list(synonyms)]


def link_records(df: pd.DataFrame, key_sets: list[list[str]]) -> pd.Series:
    """Group rows that share ANY of the key sets, e.g. same e-mail OR same name + phone.

    Linking is transitive (union-find): A~B by e-mail and B~C by phone puts A, B, C
    in one group, so a duplicate with a broken e-mail is still caught by its phone.
    """
    parent = list(range(len(df)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for cols in key_sets:
        keys = df[cols].reset_index(drop=True)
        complete = keys[keys.notna().all(axis=1)]
        by = cols if len(cols) > 1 else cols[0]
        for positions in complete.groupby(by, sort=False).groups.values():
            root = find(int(positions[0]))
            for pos in positions[1:]:
                parent[find(int(pos))] = root
    return pd.Series([find(i) for i in range(len(df))], index=df.index, name="grupa")


def count_changed(before: pd.Series, after: pd.Series) -> int:
    """How many cells a cleaning step actually changed (NA == NA)."""
    b = before.astype("string").fillna("<NA>")
    a = after.astype("string").fillna("<NA>")
    return int((a != b).sum())
