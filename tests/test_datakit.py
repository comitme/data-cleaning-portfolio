import pandas as pd
import pytest

from datakit import (
    clean_text,
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
)


def values(series: pd.Series) -> list:
    return [None if pd.isna(v) else v for v in series]


def test_clean_text_trims_and_nulls_placeholders():
    s = pd.Series(["  Jan   Kowalski ", "brak", "-", "", None, "ok"])
    assert values(clean_text(s)) == ["Jan Kowalski", None, None, None, None, "ok"]


def test_normalize_key_ignores_case_accents_and_punctuation():
    s = pd.Series(["Łódź", "LODZ ", "łódź!"])
    assert set(normalize_key(s)) == {"lodz"}


def test_person_name_strips_titles_and_fixes_case():
    s = pd.Series(["  pani ANNA   kowalska-NOWAK ", "dr jan nowak"])
    assert values(normalize_person_name(s)) == ["Anna Kowalska-Nowak", "Jan Nowak"]
    assert values(split_full_name(normalize_person_name(s))["nazwisko"]) == ["Kowalska-Nowak", "Nowak"]


@pytest.mark.parametrize("raw, expected", [
    (" Jan.Kowalski@GMAIL.com ", "jan.kowalski@gmail.com"),
    ("anna@gmial.com", "anna@gmail.com"),
    ("ewa@wp,pl", "ewa@wp.pl"),
    ("jan.kowalskigmail.com", None),
    ("brak", None),
])
def test_normalize_email(raw, expected):
    assert values(normalize_email(pd.Series([raw]))) == [expected]


@pytest.mark.parametrize("raw", ["123456789", "123-456-789", "+48 123 456 789", "0048123456789", "(48) 123 456 789", "123456789.0"])
def test_phone_formats_are_unified(raw):
    assert values(normalize_phone_pl(pd.Series([raw]))) == ["+48 123 456 789"]


def test_invalid_phone_is_na():
    assert values(normalize_phone_pl(pd.Series(["12345", "brak"]))) == [None, None]


@pytest.mark.parametrize("raw, expected", [("00950", "00-950"), ("00-950", "00-950"), ("950", "00-950"), ("1234567", None)])
def test_postal_code(raw, expected):
    assert values(normalize_postal_code_pl(pd.Series([raw]))) == [expected]


@pytest.mark.parametrize("raw, expected", [
    ("1 234,50 zł", 1234.5), ("PLN 1.234,50", 1234.5), ("1234.5", 1234.5),
    ("1,234.50", 1234.5), ("99,99", 99.99), ("1.234.567", 1234567.0),
])
def test_parse_pl_number(raw, expected):
    assert parse_pl_number(pd.Series([raw])).iloc[0] == pytest.approx(expected)


def test_parse_pl_number_garbage_is_nan():
    assert parse_pl_number(pd.Series(["abc", "brak"])).isna().all()


def test_parse_mixed_dates():
    s = pd.Series(["2024-03-05", "05.03.2024", "5/3/2024", "05.03.24", "45356", "2024-03-05 00:00:00", "31.02.2023", "jutro"])
    parsed = parse_mixed_dates(s)
    assert (parsed.iloc[:6] == pd.Timestamp("2024-03-05")).all()
    assert parsed.iloc[6:].isna().all()


def test_link_records_is_transitive_and_ignores_missing_keys():
    df = pd.DataFrame({
        "email": ["a@x.pl", "a@x.pl", None, None, None],
        "name": ["jan", "jan", "jan", "ewa", "ewa"],
        "phone": ["111", "222", "222", None, None],
    })
    groups = link_records(df, [["email"], ["name", "phone"]])
    assert groups[0] == groups[1] == groups[2]  # row 2 linked to row 0 through row 1
    assert len({groups[0], groups[3], groups[4]}) == 3  # no phone -> not merged on name alone


def test_standardize_columns_maps_synonyms_and_reports_missing():
    df = pd.DataFrame(columns=[" E-MAIL ", "Kod poczt."])
    out = standardize_columns(df, {"email": ["e-mail"], "kod_pocztowy": ["kod poczt."]})
    assert list(out.columns) == ["email", "kod_pocztowy"]
    with pytest.raises(KeyError):
        standardize_columns(df, {"telefon": ["tel."]})
