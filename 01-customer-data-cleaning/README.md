# CRM Customer Database: Cleaning & Deduplication

**English** · [Polski](README.pl.md)

**The problem:** an online shop's CRM customer export had been hand-edited in Excel for years. It couldn't be
imported into the mailing tool, and nobody could say how many customers there really were. The same people
appeared several times, phones and dates came in five different formats, and Excel had stripped the leading zeros
from postal codes.

**The result:** 458 rows became **400 unique customers** in one consistent format. The 76 records that could not be
fixed safely are listed with a plain-language reason. Nothing was deleted silently.

![Before and after](data/output/before_after.png)

## What was fixed

| Problem in the data | Example before | After | Count |
|---|---|---|---:|
| Empty rows | — | removed | 6 |
| Rows pasted twice | identical records | removed | 12 |
| Same customer under different IDs | `K0002` `małgorzata kowalska` `…@interia,pl` and `K0413` `Małgorzata Kowalska` `…@INTERIA.PL` | one customer, earliest sign-up date, order totals summed | 40 |
| Names | `  pani ANNA   kowalska ` | `Anna` / `Kowalska` | 214 |
| Phones | `0048123456789`, `(48) 123 456 789`, `123-456-789` | `+48 123 456 789` | 338 |
| E-mails | ` Jan.Nowak@GMIAL.com ` | `jan.nowak@gmail.com` | 130 |
| Cities | `W-wa`, `KRAKOW`, `Lodz` | `Warszawa`, `Kraków`, `Łódź` | 205 |
| Postal codes | `00950`, `950` (Excel dropped the zeros) | `00-950` | 192 |
| Dates | `05.03.24`, `5/3/2024`, `45356` (Excel serial number) | `2024-03-05` | 431 |
| Amounts | `1 234,50 zł`, `PLN 1.234,50` | `1234.50` (a real number) | 281 |

**How duplicates are detected:** two records are the same customer if they share a normalized e-mail **or** the same
first name, last name and phone. Links are transitive (union-find), so a duplicate with a typo in the e-mail is still
caught through the phone number. A matching name alone is never enough, because two customers called Anna Nowak are
not necessarily the same person.

**Quality control:** anything that cannot be repaired automatically goes to the `do_weryfikacji` (to verify) sheet with
the reason, e.g. `invalid e-mail: 'jan.kowalskigmail.com'` or `postal code 80-123 doesn't match the city Warszawa`.

## Deliverables

| File | Contents |
|---|---|
| [`klienci_czyste.xlsx`](data/output/klienci_czyste.xlsx) | sheets: `klienci` (customers) · `scalone_duplikaty` (merged duplicates) · `do_weryfikacji` (to verify) · `log_zmian` (change log) |
| [`raport.md`](data/output/raport.md) | summary of changes with before/after samples |
| [`before_after.png`](data/output/before_after.png) | the visual comparison above |

The client is Polish, so the delivered files keep Polish column names.

## Run it

```bash
python 01-customer-data-cleaning/generate_data.py   # creates the messy input file
python 01-customer-data-cleaning/clean.py           # cleans it and writes the deliverables
```

> The data is **synthetic**. It was generated with a fixed random seed and reproduces problems found in real
> exports. No real people are included.
