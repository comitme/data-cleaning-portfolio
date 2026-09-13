# Portfolio: czyszczenie i łączenie danych Excel / CSV

[English](README.md) · **Polski**

Porządkuję dane w Excelu i CSV: usuwam duplikaty, ujednolicam formaty i łączę pliki z różnych źródeł
w jedną tabelę, gotową do analizy, importu albo raportu. Pracuję w Pythonie (pandas), a każde zlecenie kończy się:

- **czystym plikiem Excel/CSV**, który otwiera się poprawnie w polskim Excelu,
- **logiem zmian**, czyli co dokładnie i ile zostało poprawione,
- **listą rekordów do sprawdzenia**. Niczego nie usuwam po cichu.

## Projekty

| # | Projekt | Wejście → wynik | Kluczowe techniki |
|---|---|---|---|
| 1 | [Czyszczenie bazy klientów z CRM](01-customer-data-cleaning/README.pl.md) | 458 wierszy z bałaganem → **400 unikalnych klientów** | deduplikacja (e-mail **lub** imię+nazwisko+telefon), telefony, e-maile, kody pocztowe, 6 formatów dat |
| 2 | [Łączenie sprzedaży z 3 oddziałów](02-sales-data-merge/README.pl.md) | 3 pliki w 3 formatach + katalog → **1 tabela, 1200 transakcji** | kodowanie Windows-1250, wykrywanie nagłówka, mapowanie kolumn, sumy kontrolne, raport wieloarkuszowy |

![Projekt 1: przed i po](01-customer-data-cleaning/data/output/przed_po.png)

![Projekt 2: przed i po](02-sales-data-merge/data/output/przed_po.png)

## `datakit`: własna biblioteka funkcji

Rzeczy, które powtarzają się w każdym zleceniu, są wydzielone do [`datakit/`](datakit/) i pokryte testami
(29 testów, `pytest`). Dzięki temu kolejne zlecenie zaczynam od gotowych, sprawdzonych funkcji:

| Funkcja | Co robi |
|---|---|
| `normalize_phone_pl` | `0048 123-456-789` → `+48 123 456 789` |
| `normalize_email` | wielkość liter, spacje, literówki domen (`gmial.com`, `wp,pl`) |
| `normalize_postal_code_pl` | `00950` / `950` → `00-950` |
| `parse_mixed_dates` | `05.03.24`, `5/3/2024`, `2024-03-05`, numer seryjny Excela → data |
| `parse_pl_number` | `1 234,50 zł`, `PLN 1.234,50` → `1234.5` |
| `link_records` | wykrywanie duplikatów po kilku kluczach naraz (union-find) |
| `standardize_columns` | różne nazwy kolumn → jeden schemat; brak kolumny = czytelny błąd |
| `read_csv_smart` / `read_excel_smart` | auto-wykrywanie kodowania, separatora i wiersza nagłówka |
| `write_excel_report` | wieloarkuszowy Excel z pogrubionym, zamrożonym nagłówkiem, filtrem i szerokością kolumn |
| `showcase` | grafiki „przed/po” w stylu arkusza, takie jak powyżej |

## Uruchomienie

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest
python 01-customer-data-cleaning/generate_data.py && python 01-customer-data-cleaning/clean.py
python 02-sales-data-merge/generate_data.py && python 02-sales-data-merge/merge.py
```

> Wszystkie dane w repozytorium są syntetyczne i odtwarzają typowe problemy z prawdziwych plików.
