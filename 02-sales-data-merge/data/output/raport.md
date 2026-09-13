# Raport scalania sprzedaży

## Co zostało zrobione

| Krok | Liczba |
|---|---:|
| Warszawa: wczytane transakcje | 520 |
| Kraków: usunięty wiersz podsumowania (RAZEM) | 1 |
| Kraków: wczytane transakcje | 380 |
| Kraków: ujednolicone kody SKU | 214 |
| Gdańsk: wczytane transakcje | 307 |
| Gdańsk: ujednolicone kody SKU | 133 |
| Usunięte zdublowane transakcje (ten sam nr dokumentu wyeksportowany 2x) | 7 |
| Wiersze z nieczytelną datą/ilością/ceną | 0 |
| Transakcje bez dopasowania w katalogu (do wyjaśnienia z klientem) | 16 |
| Transakcje w pliku wynikowym | 1200 |

## Sumy kontrolne

| oddzial | suma_z_pliku | suma_po_scaleniu | zgodne |
|---|---|---|---|
| Kraków | 40147.75 | 40147.75 | TAK |

## Przychód brutto wg miesięcy

| miesiac | Gdańsk | Kraków | Warszawa | RAZEM |
|---|---|---|---|---|
| 2025-01 | 5645.55 | 7547.25 | 11027.75 | 24220.55 |
| 2025-02 | 6763.1 | 5409.5 | 7105.0 | 19277.6 |
| 2025-03 | 4691.25 | 6209.35 | 10625.15 | 21525.75 |
| 2025-04 | 6550.05 | 6177.1 | 6822.65 | 19549.8 |
| 2025-05 | 5920.2 | 8283.75 | 9745.25 | 23949.2 |
| 2025-06 | 3408.1 | 6520.8 | 10755.1 | 20684.0 |
| RAZEM | 32978.25 | 40147.75 | 56080.9 | 129206.9 |

## Top 10 produktów

| sku | nazwa_produktu | sprzedane_szt | przychod |
|---|---|---|---|
| KAW-003 | Kawa ziarnista Kolumbia Supremo 1 kg | 194 | 18073.75 |
| KAW-006 | Kawa ziarnista Gwatemala Antigua 1 kg | 144 | 13988.7 |
| KAW-001 | Kawa ziarnista Brazylia Santos 1 kg | 157 | 13719.35 |
| HER-006 | Matcha ceremonialna 30 g | 130 | 8794.05 |
| KAW-002 | Kawa ziarnista Etiopia Yirgacheffe 250 g | 197 | 8229.9 |
| AKC-007 | Czajnik z gęsią szyjką 1 l | 52 | 7748.0 |
| KAW-005 | Kawa bezkofeinowa Meksyk 250 g | 196 | 7497.75 |
| KAW-004 | Kawa mielona Espresso Blend 500 g | 149 | 7212.8 |
| AKC-003 | Młynek ręczny stalowy | 37 | 6993.0 |
| KAW-007 | Kapsułki Lungo 30 szt. | 176 | 6217.2 |

## SKU spoza katalogu

| oddzial | sku | transakcje | wartosc |
|---|---|---|---|
| Gdańsk | AKC-050 | 1 | 55.0 |
| Gdańsk | KAW-099 | 1 | 55.0 |
| Kraków | AKC-050 | 2 | 220.0 |
| Kraków | KAW-099 | 5 | 321.75 |
| Warszawa | AKC-050 | 2 | 275.0 |
| Warszawa | KAW-099 | 5 | 550.0 |
