"""Generates a realistic, messy customer export (synthetic data — no real people).

Simulates what a small online shop sends: a CRM export edited by hand in Excel
for years — duplicates, mixed formats, typos, Excel eating leading zeros.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

SEED = 42
N_CUSTOMERS = 400
OUT = Path(__file__).parent / "data" / "raw" / "klienci_export_crm.xlsx"

MALE = ["Jan", "Piotr", "Krzysztof", "Andrzej", "Tomasz", "Paweł", "Michał", "Marcin", "Jakub", "Łukasz", "Kamil", "Mateusz"]
FEMALE = ["Anna", "Maria", "Katarzyna", "Małgorzata", "Agnieszka", "Barbara", "Ewa", "Magdalena", "Joanna", "Zofia", "Aleksandra", "Natalia"]
SURNAMES = [
    ("Kowalski", "Kowalska"), ("Nowak", "Nowak"), ("Wiśniewski", "Wiśniewska"), ("Wójcik", "Wójcik"),
    ("Kamiński", "Kamińska"), ("Lewandowski", "Lewandowska"), ("Zieliński", "Zielińska"), ("Szymański", "Szymańska"),
    ("Woźniak", "Woźniak"), ("Dąbrowski", "Dąbrowska"), ("Kozłowski", "Kozłowska"), ("Jankowski", "Jankowska"),
    ("Mazur", "Mazur"), ("Krawczyk", "Krawczyk"), ("Piotrowski", "Piotrowska"), ("Grabowski", "Grabowska"),
]
CITIES = {  # canonical name: (postal prefixes, messy spellings seen in the export)
    "Warszawa": (["00", "01", "02", "03", "04"], ["warszawa", "WARSZAWA", "W-wa", "Warszawa ", " warszawa"]),
    "Kraków": (["30", "31"], ["Krakow", "kraków", "KRAKÓW"]),
    "Wrocław": (["50", "51"], ["Wroclaw", "wrocław"]),
    "Poznań": (["60", "61"], ["Poznan", "poznań"]),
    "Gdańsk": (["80"], ["Gdansk", "GDAŃSK"]),
    "Łódź": (["90", "91"], ["Lodz", "łódź", "LODZ"]),
    "Lublin": (["20"], ["lublin"]),
    "Katowice": (["40"], ["katowice", "Katowice "]),
}
DOMAINS = ["gmail.com", "wp.pl", "onet.pl", "o2.pl", "interia.pl"]
DOMAIN_TYPOS = {"gmail.com": "gmial.com", "wp.pl": "wp,pl", "onet.pl": "onet,pl", "interia.pl": "interia,pl", "o2.pl": "o2,pl"}


def ascii_pl(text: str) -> str:
    table = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")
    return text.translate(table)


def make_truth(rng: random.Random) -> list[dict]:
    people, used_emails = [], set()
    for i in range(1, N_CUSTOMERS + 1):
        female = rng.random() < 0.5
        first = rng.choice(FEMALE if female else MALE)
        surname = rng.choice(SURNAMES)[1 if female else 0]
        if female and rng.random() < 0.05:
            surname = f"{surname}-{rng.choice(SURNAMES)[1]}"
        local = ascii_pl(f"{first}.{surname}").lower()
        while (email := f"{local}{rng.randint(1, 999)}@{rng.choice(DOMAINS)}") in used_emails:
            pass
        used_emails.add(email)
        city = rng.choice(list(CITIES))
        people.append({
            "id": f"K{i:04d}",
            "name": f"{first} {surname}",
            "email": email,
            "phone": f"{rng.choice('5678')}{rng.randint(10_000_000, 99_999_999)}",
            "city": city,
            "postal": f"{rng.choice(CITIES[city][0])}{rng.randint(0, 999):03d}",
            "registered": date(2021, 1, 1) + timedelta(days=rng.randint(0, 1400)),
            "orders": round(rng.uniform(0, 8000), 2),
        })
    return people


def mess_name(name: str, rng: random.Random) -> str:
    style = rng.choices(["ok", "upper", "lower", "spaces", "title"], [50, 15, 15, 15, 5])[0]
    if style == "upper":
        name = name.upper()
    elif style == "lower":
        name = name.lower()
    elif style == "spaces":
        name = f"  {name.replace(' ', '   ')} "
    elif style == "title":
        name = f"{rng.choice(['Pan', 'pani', 'Dr'])} {name}"
    return name


def mess_email(email: str, rng: random.Random, destructive: bool) -> str:
    style = rng.choices(["ok", "upper", "spaces", "typo", "broken", "missing"], [55, 15, 10, 10, 5, 5])[0]
    if not destructive and style in {"broken", "missing"}:
        style = "upper"
    local, domain = email.split("@")
    return {
        "ok": email,
        "upper": email.upper() if rng.random() < 0.5 else email.capitalize(),
        "spaces": f" {email}  ",
        "typo": f"{local}@{DOMAIN_TYPOS[domain]}",
        "broken": f"{local}{domain}",
        "missing": rng.choice(["", "brak", "-"]),
    }[style]


def mess_phone(phone: str, rng: random.Random, destructive: bool) -> object:
    style = rng.choices(["plain", "number", "dashes", "intl", "0048", "paren", "short", "missing"], [20, 15, 15, 20, 10, 10, 5, 5])[0]
    if not destructive and style in {"short", "missing"}:
        style = "intl"
    p = phone
    return {
        "plain": p,
        "number": int(p),  # Excel cell typed as a number
        "dashes": f"{p[:3]}-{p[3:6]}-{p[6:]}",
        "intl": f"+48 {p[:3]} {p[3:6]} {p[6:]}",
        "0048": f"0048{p}",
        "paren": f"(48) {p[:3]} {p[3:6]} {p[6:]}",
        "short": p[:5],
        "missing": None,
    }[style]


def mess_postal(postal: str, rng: random.Random) -> object:
    style = rng.choices(["ok", "nodash", "number"], [60, 25, 15])[0]
    if style == "number":
        return int(postal)  # Excel drops leading zeros: 00950 -> 950
    return postal if style == "nodash" else f"{postal[:2]}-{postal[2:]}"


def mess_date(d: date, rng: random.Random, destructive: bool) -> object:
    style = rng.choices(["iso", "dots", "slash", "short", "serial", "excel", "invalid"], [20, 25, 15, 10, 10, 17, 3])[0]
    if not destructive and style == "invalid":
        style = "dots"
    return {
        "iso": d.isoformat(),
        "dots": d.strftime("%d.%m.%Y"),
        "slash": f"{d.day}/{d.month}/{d.year}",
        "short": d.strftime("%d.%m.%y"),
        "serial": (d - date(1899, 12, 30)).days,
        "excel": datetime(d.year, d.month, d.day),
        "invalid": f"{rng.choice([30, 31])}.02.{d.year}",
    }[style]


def mess_amount(value: float, rng: random.Random) -> object:
    whole, frac = f"{value:.2f}".split(".")
    spaced = f"{int(whole):,}".replace(",", " ")
    dotted = f"{int(whole):,}".replace(",", ".")
    style = rng.choices(["number", "zl", "pln", "dotted", "comma", "missing"], [35, 25, 10, 10, 15, 5])[0]
    return {
        "number": value,
        "zl": f"{spaced},{frac} zł",
        "pln": f"PLN {whole}.{frac}",
        "dotted": f"{dotted},{frac}",
        "comma": f"{whole},{frac}",
        "missing": "brak",
    }[style]


def to_row(p: dict, rng: random.Random, destructive: bool = True) -> dict:
    city = p["city"]
    return {
        "ID klienta": p["id"],
        " Imię i nazwisko ": mess_name(p["name"], rng),
        "E-MAIL": mess_email(p["email"], rng, destructive),
        "tel.": mess_phone(p["phone"], rng, destructive),
        "Miasto": rng.choice([city, city, *CITIES[city][1]]),
        "Kod poczt.": mess_postal(p["postal"], rng),
        "Data rej.": mess_date(p["registered"], rng, destructive),
        "Wartość zamówień (PLN)": mess_amount(p["orders"], rng),
    }


def main() -> None:
    rng = random.Random(SEED)
    truth = make_truth(rng)
    rows = [to_row(p, rng) for p in truth]

    # City/postal-code mismatches typed in by hand.
    for row in rng.sample(rows, 6):
        row["Kod poczt."] = f"{rng.choice(['80', '30', '60'])}-{rng.randint(0, 999):03d}"
        row["Miasto"] = "Warszawa"

    # Same customer registered again (new ID, different formatting, a later order sum).
    next_id = N_CUSTOMERS + 1
    for p in rng.sample(truth, 40):
        dup = dict(p, id=f"K{next_id:04d}", registered=p["registered"] + timedelta(days=rng.randint(30, 400)),
                   orders=round(rng.uniform(50, 1500), 2))
        rows.append(to_row(dup, rng, destructive=False))
        next_id += 1

    rows += [dict(r) for r in rng.sample(rows, 12)]   # rows pasted twice
    rows += [{k: None for k in rows[0]} for _ in range(6)]  # empty rows
    rng.shuffle(rows)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_excel(OUT, index=False, sheet_name="Eksport CRM")
    print(f"Wrote {len(rows)} messy rows ({N_CUSTOMERS} real customers) -> {OUT}")


if __name__ == "__main__":
    main()
