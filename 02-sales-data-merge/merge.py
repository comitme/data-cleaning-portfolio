"""Merges sales exports from three branches (three formats) with the product catalog.

Input : data/raw/sprzedaz_warszawa.csv, sprzedaz_krakow.csv, sprzedaz_gdansk.xlsx, katalog_produktow.xlsx
Output: data/output/sprzedaz_polaczona.csv   (one tidy table, opens correctly in Polish Excel)
        data/output/raport_sprzedazy.xlsx    (data + summaries + unmatched SKUs + data-quality log)
        data/output/raport.md
        data/output/before_after.png + monthly_sales.png          (portfolio visuals, English)
        data/output/przed_po.png + sprzedaz_miesieczna.png        (portfolio visuals, Polish)
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datakit import (  # noqa: E402
    CleaningLog,
    clean_text,
    column_key,
    parse_mixed_dates,
    parse_pl_number,
    read_csv_smart,
    read_excel_smart,
    showcase,
    standardize_columns,
    write_excel_report,
)

HERE = Path(__file__).parent
RAW = HERE / "data" / "raw"
OUT = HERE / "data" / "output"

SCHEMA = {
    "nr_transakcji": ["order_id", "nr paragonu", "nr dokumentu"],
    "data": ["order_date", "data sprzedaży", "data"],
    "sku": ["kod produktu", "sku", "indeks"],
    "ilosc": ["quantity", "ilość", "szt.", "szt"],
    "cena_jedn": ["unit_price", "cena jedn.", "cena brutto", "cena"],
}
BRANCH_COLORS = {"Warszawa": "#2a78d6", "Kraków": "#eb6834", "Gdańsk": "#1baf7a"}  # fixed per branch

TEXT = {
    "en": {
        "card_file": "before_after.png", "chart_file": "monthly_sales.png",
        "eyebrow": "Data merging  ·  Python / pandas",
        "title": "3 branch files, 3 formats  →  1 clean sales table",
        "subtitle": "Encodings, separators, header rows, SKU codes and duplicates reconciled, then joined with the product catalog.",
        "stats": ["files → one table", "transactions", "SKU codes standardized", "control-sum difference"],
        "before": "BEFORE", "before_note": "three exports from three different systems",
        "after": "AFTER", "after_note": "sprzedaz_polaczona.csv — one schema, enriched from the catalog",
        "files": [("sprzedaz_warszawa.csv", "UTF-8 · comma · ISO dates"),
                  ("sprzedaz_krakow.csv", "Windows-1250 · semicolon · “1 234,50 zł” text · TOTAL row"),
                  ("sprzedaz_gdansk.xlsx", "title rows above header · messy SKUs · week exported twice")],
        "gda_cols": ["Receipt", "Sale date", "SKU", "Qty"],
        "after_cols": ["Date", "Branch", "Receipt", "SKU", "Product", "Category", "Qty", "Unit price", "Value (PLN)"],
        "footer": "Synthetic demo data reproducing real export problems   ·   red = problem, green = standardized or added from the catalog",
        "chart_title": "Gross revenue by month and branch — 3 files, 3 formats, one source of truth",
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "branches": {"Warszawa": "Warsaw", "Kraków": "Kraków", "Gdańsk": "Gdańsk"},
        "int": lambda n: f"{n:,}",
        "money2": lambda v: f"{v:,.2f}",
        "money0": lambda v: f"PLN {v:,.0f}",
        "currency_stat": lambda v: f"{v:,.2f} PLN",
    },
    "pl": {
        "card_file": "przed_po.png", "chart_file": "sprzedaz_miesieczna.png",
        "eyebrow": "Łączenie danych  ·  Python / pandas",
        "title": "3 pliki oddziałów, 3 formaty  →  1 czysta tabela",
        "subtitle": "Kodowania, separatory, nagłówki, kody SKU i duplikaty uzgodnione, potem połączone z katalogiem produktów.",
        "stats": ["pliki → jedna tabela", "transakcji", "ujednoliconych kodów SKU", "różnica sumy kontrolnej"],
        "before": "PRZED", "before_note": "trzy eksporty z trzech różnych systemów",
        "after": "PO", "after_note": "sprzedaz_polaczona.csv — jeden schemat, uzupełniony z katalogu",
        "files": [("sprzedaz_warszawa.csv", "UTF-8 · przecinek · daty ISO"),
                  ("sprzedaz_krakow.csv", "Windows-1250 · średnik · „1 234,50 zł” jako tekst · wiersz RAZEM"),
                  ("sprzedaz_gdansk.xlsx", "tytuł nad nagłówkiem · brudne SKU · tydzień 2×")],
        "gda_cols": ["Nr paragonu", "Data sprzedaży", "SKU", "Szt."],
        "after_cols": ["Data", "Oddział", "Nr dok.", "SKU", "Produkt", "Kategoria", "Szt.", "Cena jedn.", "Wartość (zł)"],
        "footer": "Dane syntetyczne odtwarzające problemy z prawdziwych eksportów   ·   czerwone = problem, zielone = ujednolicone lub dodane z katalogu",
        "chart_title": "Przychód brutto wg miesięcy i oddziałów — 3 pliki, 3 formaty, jedno źródło prawdy",
        "months": ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"],
        "branches": {},
        "int": lambda n: f"{n:,}".replace(",", " "),
        "money2": lambda v: f"{v:,.2f}".replace(",", " ").replace(".", ","),
        "money0": lambda v: f"{v:,.0f}".replace(",", " ") + " zł",
        "currency_stat": lambda v: f"{v:,.2f}".replace(",", " ").replace(".", ",") + " zł",
    },
}


def normalize_sku(s: pd.Series) -> pd.Series:
    """'kaw001 ', 'KAW 001', ' KAW-001' -> 'KAW-001'."""
    compact = clean_text(s).str.upper().str.replace(r"[^A-Z0-9]", "", regex=True)
    return compact.str.replace(r"^([A-Z]+)(\d+)$", lambda m: f"{m[1]}-{int(m[2]):03d}", regex=True)


def load_branch(name: str, path: Path, log: CleaningLog) -> tuple[pd.DataFrame, float | None]:
    if path.suffix == ".csv":
        raw, encoding = read_csv_smart(path)
        print(f"{path.name}: kodowanie {encoding}, {len(raw)} wierszy")
    else:
        raw = read_excel_smart(path)
        print(f"{path.name}: nagłówek wykryty automatycznie, {len(raw)} wierszy")

    control_total = None
    first_col = clean_text(raw.iloc[:, 0]).str.upper()
    total_rows = first_col.isin(["RAZEM", "SUMA", "TOTAL"]).fillna(False).astype(bool)
    if total_rows.any():
        control_total = float(parse_pl_number(raw.loc[total_rows].iloc[:, -1]).iloc[0])
        raw = raw.loc[~total_rows]
        log.add(f"{name}: usunięty wiersz podsumowania (RAZEM)", int(total_rows.sum()))

    id_aliases = {column_key(a) for a in ["nr_transakcji", *SCHEMA["nr_transakcji"]]}
    if not any(column_key(c) in id_aliases for c in raw.columns):
        raw = raw.assign(nr_transakcji=pd.NA)  # this system does not export document numbers

    df = standardize_columns(raw, SCHEMA)
    out = pd.DataFrame({
        "oddzial": name,
        "nr_transakcji": clean_text(df["nr_transakcji"]),
        "data": parse_mixed_dates(df["data"]),
        "sku_raw": df["sku"].astype("string"),
        "sku": normalize_sku(df["sku"]),
        "ilosc": parse_pl_number(df["ilosc"]).astype("Int64"),
        "cena_jedn": parse_pl_number(df["cena_jedn"]),
    })
    sku_fixed = int((clean_text(df["sku"]).fillna("") != out["sku"].fillna("")).sum())
    log.add(f"{name}: wczytane transakcje", len(out))
    if sku_fixed:
        log.add(f"{name}: ujednolicone kody SKU", sku_fixed)
    return out, control_total


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    log = CleaningLog()
    frames, controls = [], {}
    for name, file in [("Warszawa", "sprzedaz_warszawa.csv"), ("Kraków", "sprzedaz_krakow.csv"), ("Gdańsk", "sprzedaz_gdansk.xlsx")]:
        frame, control = load_branch(name, RAW / file, log)
        frames.append(frame)
        if control is not None:
            controls[name] = control

    sales = pd.concat(frames, ignore_index=True)
    has_id = sales["nr_transakcji"].notna()
    dupes = sales[has_id].duplicated(subset=["oddzial", "nr_transakcji", "sku"], keep="first")
    sales = sales.drop(index=dupes[dupes].index).reset_index(drop=True)
    log.add("Usunięte zdublowane transakcje (ten sam nr dokumentu wyeksportowany 2x)", int(dupes.sum()))

    bad = sales[["data", "ilosc", "cena_jedn"]].isna().any(axis=1)
    log.add("Wiersze z nieczytelną datą/ilością/ceną", int(bad.sum()))
    sales = sales[~bad].copy()

    catalog = pd.read_excel(RAW / "katalog_produktow.xlsx", dtype=str)
    catalog = standardize_columns(catalog, {"sku": [], "nazwa_produktu": ["nazwa produktu"], "kategoria": [], "cena_katalogowa": ["cena katalogowa"]})
    catalog = catalog.assign(sku=normalize_sku(catalog["sku"]), cena_katalogowa=parse_pl_number(catalog["cena_katalogowa"]))

    sales = sales.merge(catalog, on="sku", how="left", validate="many_to_one", indicator=True)
    sales["w_katalogu"] = sales["_merge"] == "both"
    sales = sales.drop(columns="_merge")
    sales["kategoria"] = sales["kategoria"].fillna("Brak w katalogu")
    sales["wartosc_brutto"] = (sales["ilosc"].astype(float) * sales["cena_jedn"]).round(2)
    sales["rabat"] = (sales["cena_jedn"] < sales["cena_katalogowa"] - 0.005).map({True: "tak", False: "nie"})
    sales["miesiac"] = sales["data"].dt.to_period("M").astype(str)
    sales = sales.sort_values(["data", "oddzial"]).reset_index(drop=True)
    log.add("Transakcje bez dopasowania w katalogu (do wyjaśnienia z klientem)", int((~sales["w_katalogu"]).sum()))
    log.add("Transakcje w pliku wynikowym", len(sales))

    # ---- control totals: does the merged data reproduce the branch's own TOTAL row?
    checks = []
    for branch, expected in controls.items():
        actual = round(sales.loc[sales["oddzial"] == branch, "wartosc_brutto"].sum(), 2)
        checks.append({"oddzial": branch, "suma_z_pliku": expected, "suma_po_scaleniu": actual,
                       "zgodne": "TAK" if abs(expected - actual) < 0.01 else "NIE"})
    checks = pd.DataFrame(checks)

    by_month = sales.pivot_table(index="miesiac", columns="oddzial", values="wartosc_brutto", aggfunc="sum", margins=True, margins_name="RAZEM").round(2).reset_index()
    by_category = sales.pivot_table(index="kategoria", columns="oddzial", values="wartosc_brutto", aggfunc="sum", margins=True, margins_name="RAZEM").round(2).reset_index()
    top = (sales.groupby(["sku", "nazwa_produktu"], dropna=False)
           .agg(sprzedane_szt=("ilosc", "sum"), przychod=("wartosc_brutto", "sum"))
           .sort_values("przychod", ascending=False).head(10).round(2).reset_index())
    unmatched = (sales[~sales["w_katalogu"]].groupby(["oddzial", "sku"])
                 .agg(transakcje=("sku", "size"), wartosc=("wartosc_brutto", "sum")).round(2).reset_index())

    columns = ["data", "miesiac", "oddzial", "nr_transakcji", "sku", "nazwa_produktu", "kategoria", "ilosc", "cena_jedn", "cena_katalogowa", "rabat", "wartosc_brutto"]
    final = sales[columns]
    OUT.mkdir(parents=True, exist_ok=True)
    final.to_csv(OUT / "sprzedaz_polaczona.csv", sep=";", decimal=",", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    write_excel_report({
        "dane": final, "miesiace_x_oddzialy": by_month, "kategorie": by_category, "top10_produktow": top,
        "brak_w_katalogu": unmatched, "sumy_kontrolne": checks, "log_zmian": log.to_frame(),
    }, OUT / "raport_sprzedazy.xlsx")

    sku_fixed = sum(count for step, count in log.entries if "SKU" in step)
    control_diff = float((checks["suma_z_pliku"] - checks["suma_po_scaleniu"]).abs().sum()) if len(checks) else 0.0
    for lang in TEXT:
        render_chart(sales, lang)
        render_card(sales, sku_fixed, control_diff, lang)
    write_report(log, checks, by_month, top, unmatched)
    print(f"Gotowe -> {OUT}")


def render_chart(sales: pd.DataFrame, lang: str) -> None:
    t = TEXT[lang]
    ink, muted, grid, axis, surface = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb"
    monthly = sales.pivot_table(index="miesiac", columns="oddzial", values="wartosc_brutto", aggfunc="sum")
    x = range(len(monthly))

    fig, ax = plt.subplots(figsize=(10, 5.2), facecolor=surface)
    ax.set_facecolor(surface)
    for branch, color in BRANCH_COLORS.items():
        y = monthly[branch]
        label = t["branches"].get(branch, branch)
        ax.plot(x, y, color=color, linewidth=2, marker="o", markersize=7, markeredgecolor=surface, markeredgewidth=2, label=label, zorder=3)
        ax.annotate(f"{label}  {t['money0'](y.iloc[-1])}", (len(monthly) - 1, y.iloc[-1]), xytext=(10, 0),
                    textcoords="offset points", va="center", fontsize=10, color=ink)
    ax.set_xticks(list(x), [t["months"][int(m[-2:]) - 1] + " " + m[:4] for m in monthly.index], color=muted)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: t["money0"](v)))
    ax.tick_params(colors=muted, length=0)
    ax.grid(axis="y", color=grid, linewidth=0.8)
    ax.set_ylim(bottom=0)
    ax.set_xlim(-0.3, len(monthly) - 1 + 1.8)
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(axis)
    ax.set_title(t["chart_title"], loc="left", fontsize=12, fontweight="bold", color=ink, pad=34)
    ax.legend(frameon=False, loc="lower left", ncols=3, bbox_to_anchor=(0, 1.0), labelcolor=muted, borderaxespad=0.2)
    fig.tight_layout()
    fig.savefig(OUT / t["chart_file"], dpi=150, facecolor=surface)
    plt.close(fig)


def render_card(sales: pd.DataFrame, sku_fixed: int, control_diff: float, lang: str) -> None:
    t = TEXT[lang]
    fig = showcase.new_card()
    showcase.card_header(fig, t["eyebrow"], t["title"], t["subtitle"])
    y = showcase.stat_row(fig, 0.80, [
        ("3 → 1", t["stats"][0]), (t["int"](len(sales)), t["stats"][1]),
        (t["int"](sku_fixed), t["stats"][2]), (t["currency_stat"](control_diff), t["stats"][3]),
    ])

    # ---- before: the three raw files as they arrive
    showcase.section_label(fig, y - 0.04, t["before"], t["before_note"], good=False)
    top = y - 0.075
    panels = [(0.05, 0.25), (0.32, 0.36), (0.70, 0.25)]
    for (x, _), (name, note) in zip(panels, t["files"]):
        showcase.file_caption(fig, x, top, name, note)
    panel_top = top - 0.058

    waw = (RAW / "sprzedaz_warszawa.csv").read_text(encoding="utf-8").splitlines()
    krk = (RAW / "sprzedaz_krakow.csv").read_text(encoding="cp1250").replace(" ", " ").splitlines()
    bottoms = [
        showcase.draw_text_file(fig, panel_top, waw[:5], x0=panels[0][0], width=panels[0][1]),
        showcase.draw_text_file(fig, panel_top, [*krk[:3], "…", krk[-1]], x0=panels[1][0], width=panels[1][1],
                                flagged_lines=[4], line_numbers=["1", "2", "3", "", str(len(krk))]),
    ]
    gda = pd.read_excel(RAW / "sprzedaz_gdansk.xlsx", header=None)
    body = gda.iloc[3:7, :4].reset_index(drop=True)
    body[1] = pd.to_datetime(body[1]).dt.strftime("%d.%m.%Y")
    body.columns = t["gda_cols"]
    flags = pd.DataFrame(False, index=body.index, columns=body.columns)
    sku_col = body.columns[2]
    flags[sku_col] = (body[sku_col].astype(str) != normalize_sku(body[sku_col].astype(str)).astype(str)).to_numpy()
    bottoms.append(showcase.draw_sheet(fig, panel_top, body, highlight=flags, x0=panels[2][0], width=panels[2][1],
                                       rows_above_header=[str(gda.iat[0, 0]), ""]))

    # ---- after: one schema for all branches
    bottom = min(bottoms)
    showcase.section_label(fig, bottom - 0.045, t["after"], t["after_note"], good=True)
    picks = []
    for branch, group in sales[sales["w_katalogu"]].groupby("oddzial", sort=False):
        messy = group[group["sku_raw"].fillna("") != group["sku"]]
        n = 2 if branch == "Gdańsk" else 1
        picks.append((messy if len(messy) >= n else group).head(n))
    sample = pd.concat(picks).sort_values("data")
    table = pd.DataFrame({
        "date": sample["data"].dt.strftime("%Y-%m-%d"),
        "branch": sample["oddzial"],
        "receipt": sample["nr_transakcji"].fillna("—"),
        "sku": sample["sku"],
        "product": sample["nazwa_produktu"],
        "category": sample["kategoria"],
        "qty": sample["ilosc"].astype(str),
        "price": sample["cena_jedn"].map(t["money2"]),
        "value": sample["wartosc_brutto"].map(t["money2"]),
    }).reset_index(drop=True)
    table.columns = t["after_cols"]
    flags = pd.DataFrame(False, index=table.index, columns=table.columns)
    flags[table.columns[3]] = (sample["sku_raw"].fillna("") != sample["sku"]).to_numpy()
    flags[table.columns[4]] = True
    flags[table.columns[5]] = True
    showcase.draw_sheet(fig, bottom - 0.08, table, highlight=flags, good=True, max_chars=38)
    showcase.footer(fig, t["footer"])
    showcase.save_card(fig, OUT / t["card_file"])


def md(frame: pd.DataFrame) -> str:
    frame = frame.astype(str)
    header = "| " + " | ".join(map(str, frame.columns)) + " |\n|" + "---|" * frame.shape[1]
    return header + "\n" + "\n".join("| " + " | ".join(r) + " |" for r in frame.values.tolist())


def write_report(log: CleaningLog, checks: pd.DataFrame, by_month: pd.DataFrame, top: pd.DataFrame, unmatched: pd.DataFrame) -> None:
    text = f"""# Raport scalania sprzedaży

## Co zostało zrobione

{log.to_markdown()}

## Sumy kontrolne

{md(checks)}

## Przychód brutto wg miesięcy

{md(by_month)}

## Top 10 produktów

{md(top)}

## SKU spoza katalogu

{md(unmatched)}
"""
    (OUT / "raport.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
