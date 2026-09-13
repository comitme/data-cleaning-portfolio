"""datakit — small, tested toolkit for cleaning and merging messy Excel/CSV data."""
from .cleaning import (
    clean_text,
    column_key,
    count_changed,
    link_records,
    normalize_email,
    normalize_key,
    normalize_person_name,
    normalize_phone_pl,
    normalize_postal_code_pl,
    parse_mixed_dates,
    parse_pl_number,
    split_full_name,
    standardize_columns,
    strip_accents,
)
from .io import CleaningLog, read_csv_smart, read_excel_smart, write_excel_report

from . import showcase  # noqa: E402  (portfolio / client-facing PNG cards)

__all__ = [
    "CleaningLog", "clean_text", "column_key", "count_changed", "link_records", "normalize_email", "normalize_key",
    "normalize_person_name", "normalize_phone_pl", "normalize_postal_code_pl", "parse_mixed_dates",
    "parse_pl_number", "read_csv_smart", "read_excel_smart", "split_full_name", "standardize_columns",
    "strip_accents", "write_excel_report",
]
