"""Generates sales exports from three shop branches that use three different systems
(synthetic data). Each file has its own format — the typical "merge my files" job.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

SEED = 7
RAW = Path(__file__).parent / "data" / "raw"
START, END = date(2025, 1, 1), date(2025, 6, 30)

CATALOG = [
    ("KAW-001", "Kawa ziarnista Brazylia Santos 1 kg", "Kawa", 89.00),
    ("KAW-002", "Kawa ziarnista Etiopia Yirgacheffe 250 g", "Kawa", 42.00),
    ("KAW-003", "Kawa ziarnista Kolumbia Supremo 1 kg", "Kawa", 95.00),
    ("KAW-004", "Kawa mielona Espresso Blend 500 g", "Kawa", 49.00),
    ("KAW-005", "Kawa bezkofeinowa Meksyk 250 g", "Kawa", 39.00),
    ("KAW-006", "Kawa ziarnista Gwatemala Antigua 1 kg", "Kawa", 99.00),
    ("KAW-007", "Kapsułki Lungo 30 szt.", "Kawa", 36.00),
    ("HER-001", "Herbata czarna Assam 100 g", "Herbata", 24.00),
    ("HER-002", "Herbata zielona Sencha 100 g", "Herbata", 29.00),
    ("HER-003", "Herbata biała Pai Mu Tan 50 g", "Herbata", 34.00),
    ("HER-004", "Herbata owocowa Malina-Żurawina 100 g", "Herbata", 19.00),
    ("HER-005", "Yerba Mate Klasyczna 500 g", "Herbata", 32.00),
    ("HER-006", "Matcha ceremonialna 30 g", "Herbata", 69.00),
    ("AKC-001", "Drip V60 ceramiczny", "Akcesoria", 119.00),
    ("AKC-002", "Filtry papierowe V60 100 szt.", "Akcesoria", 25.00),
    ("AKC-003", "Młynek ręczny stalowy", "Akcesoria", 189.00),
    ("AKC-004", "French press 1 l", "Akcesoria", 79.00),
    ("AKC-005", "Kubek termiczny 350 ml", "Akcesoria", 59.00),
    ("AKC-006", "Waga kuchenna z timerem", "Akcesoria", 99.00),
    ("AKC-007", "Czajnik z gęsią szyjką 1 l", "Akcesoria", 149.00),
]
DISCONTINUED = ["KAW-099", "AKC-050"]  # still sold in one branch, missing from the catalog
BRANCHES = {"Warszawa": 520, "Kraków": 380, "Gdańsk": 300}


def transactions(rng: random.Random, n: int) -> list[dict]:
    weights = [5 if sku.startswith("KAW") else 3 if sku.startswith("HER") else 1 for sku, *_ in CATALOG]
    rows = []
    for i in range(n):
        day = START + timedelta(days=rng.randint(0, (END - START).days))
        if rng.random() < 0.015:
            sku, price = rng.choice(DISCONTINUED), 55.0
        else:
            sku, _, _, price = rng.choices(CATALOG, weights)[0]
        if rng.random() < 0.1:
            price = round(price * 0.85, 2)  # promo
        rows.append({"id": i + 1, "date": day, "sku": sku, "qty": rng.choices([1, 2, 3, 4, 6], [55, 25, 10, 6, 4])[0], "price": price})
    return sorted(rows, key=lambda r: r["date"])


def pl_money(value: float) -> str:
    whole, frac = f"{value:.2f}".split(".")
    return f"{int(whole):,}".replace(",", " ") + f",{frac} zł"


def main() -> None:
    rng = random.Random(SEED)
    RAW.mkdir(parents=True, exist_ok=True)

    # Warszawa — web shop platform: UTF-8, comma separator, ISO dates, dot decimals.
    waw = transactions(rng, BRANCHES["Warszawa"])
    pd.DataFrame({
        "order_id": [f"WAW/2025/{r['id']:05d}" for r in waw],
        "order_date": [r["date"].isoformat() for r in waw],
        "sku": [r["sku"] for r in waw],
        "quantity": [r["qty"] for r in waw],
        "unit_price": [f"{r['price']:.2f}" for r in waw],
    }).to_csv(RAW / "sprzedaz_warszawa.csv", index=False, encoding="utf-8")

    # Kraków — old POS system: Windows-1250, semicolons, dd.mm.yyyy, "1 234,50 zł", lower-case SKUs, TOTAL row.
    krk = transactions(rng, BRANCHES["Kraków"])
    names = {sku: name for sku, name, *_ in CATALOG}
    lines = ["Data;Kod produktu;Nazwa towaru;Ilość;Cena jedn.;Wartość"]
    total = 0.0
    for r in krk:
        value = r["qty"] * r["price"]
        total += value
        sku = r["sku"].lower() if rng.random() < 0.6 else r["sku"]
        lines.append(f"{r['date']:%d.%m.%Y};{sku};{names.get(r['sku'], 'Produkt wycofany')};{r['qty']};{pl_money(r['price'])};{pl_money(value)}")
    lines.append(f"RAZEM;;;;;{pl_money(total)}")
    (RAW / "sprzedaz_krakow.csv").write_text("\n".join(lines) + "\n", encoding="cp1250")

    # Gdańsk — manager's Excel: title rows above the header, real Excel dates,
    # inconsistent SKUs ("KAW 001", "kaw001 "), one week exported twice.
    gda = transactions(rng, BRANCHES["Gdańsk"])
    def messy_sku(sku: str) -> str:
        prefix, num = sku.split("-")
        return rng.choice([sku, sku, f"{prefix} {num}", f"{prefix.lower()}{num} ", f" {sku}"])
    body = [[f"GDA-{r['id']:04d}", datetime(r["date"].year, r["date"].month, r["date"].day), messy_sku(r["sku"]), r["qty"], r["price"]] for r in gda]
    overlap = [row for row in body if date(2025, 3, 24) <= row[1].date() <= date(2025, 3, 30)]
    body += [list(row) for row in overlap]
    sheet = [["Raport sprzedaży — oddział Gdańsk", None, None, None, None], [None] * 5,
             ["Nr paragonu", "Data sprzedaży", "SKU", "Szt.", "Cena brutto"], *body]
    pd.DataFrame(sheet).to_excel(RAW / "sprzedaz_gdansk.xlsx", index=False, header=False, sheet_name="Sprzedaż")

    pd.DataFrame(CATALOG, columns=["SKU", "Nazwa produktu", "Kategoria", "Cena katalogowa"]).to_excel(
        RAW / "katalog_produktow.xlsx", index=False)

    print(f"Wrote 3 branch files + catalog -> {RAW}  ({len(overlap)} duplicated rows in Gdańsk)")


if __name__ == "__main__":
    main()
