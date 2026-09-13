"""Cleans and deduplicates a messy CRM customer export.

Input : data/raw/klienci_export_crm.xlsx
Output: data/output/klienci_czyste.xlsx  (clean list + merged duplicates + rows to verify)
        data/output/raport.md             (what was changed, in numbers)
        data/output/before_after.png      (portfolio card, English)
        data/output/przed_po.png          (portfolio card, Polish)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datakit import (  # noqa: E402
    CleaningLog,
    clean_text,
    count_changed,
    link_records,
    normalize_email,
    normalize_key,
    normalize_person_name,
    normalize_phone_pl,
    normalize_postal_code_pl,
    parse_mixed_dates,
    parse_pl_number,
    showcase,
    split_full_name,
    standardize_columns,
    write_excel_report,
)

HERE = Path(__file__).parent
RAW = HERE / "data" / "raw" / "klienci_export_crm.xlsx"
OUT = HERE / "data" / "output"

COLUMNS = {
    "id_klienta": ["id klienta", "id"],
    "imie_nazwisko": ["imię i nazwisko", "klient", "nazwa"],
    "email": ["e-mail", "mail", "adres e-mail"],
    "telefon": ["tel.", "tel", "nr telefonu"],
    "miasto": ["miejscowość"],
    "kod_pocztowy": ["kod poczt.", "kod"],
    "data_rejestracji": ["data rej.", "data rejestracji"],
    "wartosc_zamowien_pln": ["wartość zamówień (pln)", "wartość zamówień"],
}
CITY_ALIASES = {"wwa": "Warszawa", "w-wa": "Warszawa"}
CITY_POSTAL_PREFIX = {
    "Warszawa": ("0",), "Kraków": ("30", "31", "32"), "Wrocław": ("50", "51"), "Poznań": ("60", "61"),
    "Gdańsk": ("80",), "Łódź": ("90", "91", "92", "93", "94"), "Lublin": ("20",), "Katowice": ("40",),
}

CARD_TEXT = {
    "en": {
        "file": "before_after.png",
        "eyebrow": "Data cleaning  ·  Python / pandas",
        "title": "Messy CRM export  →  clean customer list",
        "subtitle": "Duplicates merged; names, phones, e-mails, postal codes, dates and amounts in one consistent format.",
        "stats": ["rows → unique customers", "duplicates merged", "cells standardized", "records flagged for review"],
        "before": "BEFORE", "before_note": "klienci_export_crm.xlsx — exported straight from the CRM",
        "after": "AFTER", "after_note": "klienci_czyste.xlsx — ready to import",
        "before_cols": ["Full name", "E-mail", "Phone", "City", "Postal code", "Registered", "Orders"],
        "after_cols": ["First name", "Last name", "E-mail", "Phone", "City", "Postal code", "Registered", "Orders (PLN)"],
        "footer": "Synthetic demo data reproducing real export problems   ·   “·” = stray space   ·   red = problem, green = fixed",
        "thousands": ",",
    },
    "pl": {
        "file": "przed_po.png",
        "eyebrow": "Czyszczenie danych  ·  Python / pandas",
        "title": "Bałagan z CRM  →  czysta lista klientów",
        "subtitle": "Scalone duplikaty; imiona, telefony, e-maile, kody pocztowe, daty i kwoty w jednym formacie.",
        "stats": ["wierszy → unikalnych klientów", "scalonych duplikatów", "ujednoliconych komórek", "rekordów do weryfikacji"],
        "before": "PRZED", "before_note": "klienci_export_crm.xlsx — eksport prosto z CRM",
        "after": "PO", "after_note": "klienci_czyste.xlsx — gotowe do importu",
        "before_cols": ["Imię i nazwisko", "E-mail", "Telefon", "Miasto", "Kod pocztowy", "Data rej.", "Zamówienia"],
        "after_cols": ["Imię", "Nazwisko", "E-mail", "Telefon", "Miasto", "Kod pocztowy", "Data rej.", "Zamówienia (zł)"],
        "footer": "Dane syntetyczne odtwarzające problemy z prawdziwych eksportów   ·   „·” = zbędna spacja   ·   czerwone = problem, zielone = poprawione",
        "thousands": " ",
    },
}


def normalize_city(s: pd.Series) -> pd.Series:
    canonical = {normalize_key(pd.Series([c])).iloc[0]: c for c in CITY_POSTAL_PREFIX}
    canonical |= {normalize_key(pd.Series([a])).iloc[0]: c for a, c in CITY_ALIASES.items()}
    keys = normalize_key(s)
    return keys.map(canonical).fillna(clean_text(s).str.title()).astype("string")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    log = CleaningLog()
    raw = pd.read_excel(RAW, dtype=str)
    print(f"Wczytano {len(raw)} wierszy z {RAW.name}")
    log.add("Wiersze w pliku wejściowym", len(raw))

    df = standardize_columns(raw, COLUMNS)
    df = df[df.apply(lambda col: clean_text(col)).notna().any(axis=1)]
    log.add("Usunięte puste wiersze", len(raw) - len(df))

    before_exact = len(df)
    df = df.drop_duplicates().copy()
    log.add("Usunięte identyczne wiersze (wklejone dwa razy)", before_exact - len(df))

    source = df.copy()  # kept for the before/after comparison
    clean = pd.DataFrame(index=df.index)
    clean["id_klienta"] = clean_text(df["id_klienta"])
    full_name = normalize_person_name(df["imie_nazwisko"])
    clean[["imie", "nazwisko"]] = split_full_name(full_name)
    clean["email"] = normalize_email(df["email"])
    clean["telefon"] = normalize_phone_pl(df["telefon"])
    clean["miasto"] = normalize_city(df["miasto"])
    clean["kod_pocztowy"] = normalize_postal_code_pl(df["kod_pocztowy"])
    clean["data_rejestracji"] = parse_mixed_dates(df["data_rejestracji"])
    clean["wartosc_zamowien_pln"] = parse_pl_number(df["wartosc_zamowien_pln"]).round(2)

    log.add("Poprawione imiona i nazwiska (wielkość liter, spacje, tytuły)", count_changed(df["imie_nazwisko"], full_name))
    log.add("Ujednolicone adresy e-mail", count_changed(clean_text(df["email"]), clean["email"]))
    log.add("Telefony sprowadzone do formatu +48 XXX XXX XXX", count_changed(clean_text(df["telefon"]), clean["telefon"]))
    log.add("Ujednolicone nazwy miast", count_changed(df["miasto"], clean["miasto"]))
    log.add("Poprawione kody pocztowe (w tym utracone zera z Excela)", count_changed(clean_text(df["kod_pocztowy"]), clean["kod_pocztowy"]))
    log.add("Daty z różnych formatów zamienione na RRRR-MM-DD", int(clean["data_rejestracji"].notna().sum()))
    log.add("Kwoty tekstowe ('1 234,50 zł') zamienione na liczby", int(pd.to_numeric(df["wartosc_zamowien_pln"], errors="coerce").isna().sum()))

    # ---- deduplicate: same e-mail OR same name + phone (transitively)
    for col in ["email", "telefon", "data_rejestracji"]:
        clean[f"_{col}_raw"] = clean_text(df[col])
    clean["_name"] = clean["imie"].str.lower() + " " + clean["nazwisko"].str.lower()
    clean["_key"] = link_records(clean, [["email"], ["_name", "telefon"]])

    grouped = clean.sort_values("data_rejestracji", na_position="last").groupby("_key", sort=False)
    customers = grouped.agg(
        id_klienta=("id_klienta", "first"),
        imie=("imie", "first"),
        nazwisko=("nazwisko", "first"),
        email=("email", "first"),
        telefon=("telefon", "first"),
        miasto=("miasto", "first"),
        kod_pocztowy=("kod_pocztowy", "first"),
        data_rejestracji=("data_rejestracji", "min"),
        wartosc_zamowien_pln=("wartosc_zamowien_pln", lambda x: x.sum(min_count=1)),
        liczba_rekordow=("id_klienta", "size"),
        scalone_id=("id_klienta", lambda x: ", ".join(sorted(x))),
        _email_raw=("_email_raw", "first"),
        _telefon_raw=("_telefon_raw", "first"),
        _data_rejestracji_raw=("_data_rejestracji_raw", "first"),
    ).reset_index(drop=True)
    log.add("Scalone duplikaty klientów (ten sam e-mail lub imię+nazwisko+telefon)", len(clean) - len(customers))

    # ---- rows the client should look at
    def issues(row: pd.Series) -> str:
        found = []
        for col, label in [("email", "e-mail"), ("telefon", "telefon"), ("data_rejestracji", "data rejestracji")]:
            if pd.isna(row[col]):
                raw_value = row[f"_{col}_raw"]
                found.append(f"nieprawidłowy {label}: '{raw_value}'" if pd.notna(raw_value) else f"brak: {label}")
        prefixes = CITY_POSTAL_PREFIX.get(row["miasto"])
        if prefixes and pd.notna(row["kod_pocztowy"]) and not row["kod_pocztowy"].startswith(prefixes):
            found.append(f"kod {row['kod_pocztowy']} nie pasuje do miasta {row['miasto']}")
        return "; ".join(found)

    customers["do_sprawdzenia"] = customers.apply(issues, axis=1)
    customers = customers.drop(columns=[c for c in customers.columns if c.startswith("_")])
    customers = customers.sort_values("id_klienta").reset_index(drop=True)
    to_verify = customers[customers["do_sprawdzenia"] != ""]
    merged = customers[customers["liczba_rekordow"] > 1][["id_klienta", "imie", "nazwisko", "email", "liczba_rekordow", "scalone_id", "wartosc_zamowien_pln"]]
    log.add("Klienci w wyniku końcowym", len(customers))
    log.add("Rekordy oznaczone do ręcznej weryfikacji", len(to_verify))

    final = customers.drop(columns=["scalone_id"])
    write_excel_report(
        {"klienci": final, "scalone_duplikaty": merged, "do_weryfikacji": to_verify, "log_zmian": log.to_frame()},
        OUT / "klienci_czyste.xlsx",
    )
    write_report(log, source, clean, to_verify)
    stats = {
        "rows_in": len(raw), "customers": len(customers), "merged": len(clean) - len(customers),
        "standardized": sum(count for _, count in log.entries[3:10]), "to_verify": len(to_verify),
    }
    for lang in CARD_TEXT:
        render_card(source, clean, stats, lang)
    print(f"Gotowe -> {OUT}")


def sample_rows(source: pd.DataFrame, clean: pd.DataFrame, n: int = 6) -> tuple[pd.DataFrame, pd.DataFrame]:
    messy = source.apply(lambda c: c.astype("string").fillna("") != clean_text(c).fillna("")).sum(axis=1)
    idx = messy.sort_values(ascending=False, kind="stable").index[:n]
    before = source.loc[idx, ["imie_nazwisko", "email", "telefon", "miasto", "kod_pocztowy", "data_rejestracji", "wartosc_zamowien_pln"]]
    after = clean.loc[idx, ["imie", "nazwisko", "email", "telefon", "miasto", "kod_pocztowy", "data_rejestracji", "wartosc_zamowien_pln"]].copy()
    after["data_rejestracji"] = after["data_rejestracji"].dt.strftime("%Y-%m-%d")
    return before.fillna("").astype(str), after.astype("string").fillna("—").astype(str)


def md_table(frame: pd.DataFrame) -> str:
    cells = frame.map(lambda v: f"`{v}`" if v not in ("", "—") else v)
    header = "| " + " | ".join(frame.columns) + " |\n|" + "---|" * frame.shape[1]
    return header + "\n" + "\n".join("| " + " | ".join(r) + " |" for r in cells.values.tolist())


def write_report(log: CleaningLog, source: pd.DataFrame, clean: pd.DataFrame, to_verify: pd.DataFrame) -> None:
    before, after = sample_rows(source, clean)
    text = f"""# Raport czyszczenia bazy klientów

## Co zostało zrobione

{log.to_markdown()}

## Przykład: przed

{md_table(before)}

## Przykład: po

{md_table(after)}

## Do ręcznej weryfikacji (pierwsze 10 z {len(to_verify)})

{md_table(to_verify[["id_klienta", "imie", "nazwisko", "do_sprawdzenia"]].head(10).astype(str))}
"""
    (OUT / "raport.md").write_text(text, encoding="utf-8")


def card_rows(source: pd.DataFrame, clean: pd.DataFrame, n: int = 6):
    """Pick the messiest rows that were fully repaired, with per-cell 'changed' flags."""
    fields = ["email", "telefon", "miasto", "kod_pocztowy", "data_rejestracji", "wartosc_zamowien_pln"]
    after = pd.DataFrame({
        "imie": clean["imie"], "nazwisko": clean["nazwisko"],
        **{c: clean[c] for c in fields[:4]},
        "data_rejestracji": clean["data_rejestracji"].dt.strftime("%Y-%m-%d"),
        "wartosc_zamowien_pln": clean["wartosc_zamowien_pln"].map(lambda v: f"{v:.2f}" if pd.notna(v) else None),
    }, index=clean.index).astype(object)
    raw = source.map(lambda v: "" if pd.isna(v) else str(v))
    target = pd.DataFrame({"imie_nazwisko": after["imie"] + " " + after["nazwisko"], **{c: after[c] for c in fields}})
    changed = raw[target.columns].ne(target.fillna(""))
    same_amount = pd.to_numeric(raw["wartosc_zamowien_pln"], errors="coerce").round(2).eq(clean["wartosc_zamowien_pln"])
    changed["wartosc_zamowien_pln"] &= ~same_amount.fillna(False).astype(bool)

    score = changed.sum(axis=1).where(after.notna().all(axis=1), -1)
    idx = score.sort_values(ascending=False, kind="stable").index[:n]
    flags_before = changed.loc[idx].reset_index(drop=True)
    flags_after = pd.DataFrame({"imie": flags_before["imie_nazwisko"], "nazwisko": flags_before["imie_nazwisko"],
                                **{c: flags_before[c] for c in fields}})
    return raw.loc[idx, target.columns].reset_index(drop=True), after.loc[idx].reset_index(drop=True), flags_before, flags_after


def render_card(source: pd.DataFrame, clean: pd.DataFrame, stats: dict, lang: str) -> None:
    t = CARD_TEXT[lang]
    num = lambda n: f"{n:,}".replace(",", t["thousands"])  # noqa: E731
    before, after, flags_before, flags_after = card_rows(source, clean)

    fig = showcase.new_card()
    showcase.card_header(fig, t["eyebrow"], t["title"], t["subtitle"])
    y = showcase.stat_row(fig, 0.80, [
        (f"{stats['rows_in']} → {stats['customers']}", t["stats"][0]),
        (num(stats["merged"]), t["stats"][1]),
        (num(stats["standardized"]), t["stats"][2]),
        (num(stats["to_verify"]), t["stats"][3]),
    ])
    showcase.section_label(fig, y - 0.04, t["before"], t["before_note"], good=False)
    bottom = showcase.draw_sheet(fig, y - 0.075, before.set_axis(t["before_cols"], axis=1),
                                 highlight=flags_before.set_axis(t["before_cols"], axis=1))
    showcase.section_label(fig, bottom - 0.045, t["after"], t["after_note"], good=True)
    showcase.draw_sheet(fig, bottom - 0.08, after.set_axis(t["after_cols"], axis=1),
                        highlight=flags_after.set_axis(t["after_cols"], axis=1), good=True)
    showcase.footer(fig, t["footer"])
    showcase.save_card(fig, OUT / t["file"])


if __name__ == "__main__":
    main()
