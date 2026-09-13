# Raport czyszczenia bazy klientów

## Co zostało zrobione

| Krok | Liczba |
|---|---:|
| Wiersze w pliku wejściowym | 458 |
| Usunięte puste wiersze | 6 |
| Usunięte identyczne wiersze (wklejone dwa razy) | 12 |
| Poprawione imiona i nazwiska (wielkość liter, spacje, tytuły) | 214 |
| Ujednolicone adresy e-mail | 130 |
| Telefony sprowadzone do formatu +48 XXX XXX XXX | 338 |
| Ujednolicone nazwy miast | 205 |
| Poprawione kody pocztowe (w tym utracone zera z Excela) | 192 |
| Daty z różnych formatów zamienione na RRRR-MM-DD | 431 |
| Kwoty tekstowe ('1 234,50 zł') zamienione na liczby | 281 |
| Scalone duplikaty klientów (ten sam e-mail lub imię+nazwisko+telefon) | 40 |
| Klienci w wyniku końcowym | 400 |
| Rekordy oznaczone do ręcznej weryfikacji | 76 |

## Przykład: przed

| imie_nazwisko | email | telefon | miasto | kod_pocztowy | data_rejestracji | wartosc_zamowien_pln |
|---|---|---|---|---|---|---|
| `  Joanna   Jankowska ` | `joanna.jankowska775@gmial.com` | `667063296` | `Katowice ` | `40753` | `2024-08-31 00:00:00` | `6 010,76 zł` |
| `  Zofia   Szymańska-Grabowska ` | `ZOFIA.SZYMANSKA-GRABOWSKA1@ONET.PL` | `65573` | `poznań` | `60940` | `2022-10-25 00:00:00` | `brak` |
| `  Jakub   Szymański ` | `JAKUB.SZYMANSKI97@O2.PL` | `(48) 626 301 180` | `kraków` | `30-063` | `2022-04-01` | `brak` |
| `  Andrzej   Zieliński ` | ` andrzej.zielinski407@wp.pl  ` | `+48 761 091 554` | `Łódź` | `91546` | `45525` | `2.874,08` |
| `  Piotr   Nowak ` | `piotr.nowak829@o2,pl` | `637659807` | `Warszawa ` | `00103` | `2024-05-01` | `268,61` |
| `Barbara Lewandowska` | ` barbara.lewandowska798@interia.pl  ` | `+48 775 579 548` | `Warszawa ` | `00-114` | `2023-01-14 00:00:00` | `7 029,78 zł` |

## Przykład: po

| imie | nazwisko | email | telefon | miasto | kod_pocztowy | data_rejestracji | wartosc_zamowien_pln |
|---|---|---|---|---|---|---|---|
| `Joanna` | `Jankowska` | `joanna.jankowska775@gmail.com` | `+48 667 063 296` | `Katowice` | `40-753` | `2024-08-31` | `6010.76` |
| `Zofia` | `Szymańska-Grabowska` | `zofia.szymanska-grabowska1@onet.pl` | — | `Poznań` | `60-940` | `2022-10-25` | — |
| `Jakub` | `Szymański` | `jakub.szymanski97@o2.pl` | `+48 626 301 180` | `Kraków` | `30-063` | `2022-04-01` | — |
| `Andrzej` | `Zieliński` | `andrzej.zielinski407@wp.pl` | `+48 761 091 554` | `Łódź` | `91-546` | `2024-08-21` | `2874.08` |
| `Piotr` | `Nowak` | `piotr.nowak829@o2.pl` | `+48 637 659 807` | `Warszawa` | `00-103` | `2024-05-01` | `268.61` |
| `Barbara` | `Lewandowska` | `barbara.lewandowska798@interia.pl` | `+48 775 579 548` | `Warszawa` | `00-114` | `2023-01-14` | `7029.78` |

## Do ręcznej weryfikacji (pierwsze 10 z 76)

| id_klienta | imie | nazwisko | do_sprawdzenia |
|---|---|---|---|
| `K0001` | `Jan` | `Woźniak` | `nieprawidłowy data rejestracji: '30.02.2023'` |
| `K0004` | `Mateusz` | `Piotrowski` | `kod 30-344 nie pasuje do miasta Warszawa` |
| `K0007` | `Aleksandra` | `Szymańska` | `nieprawidłowy e-mail: 'aleksandra.szymanska864gmail.com'` |
| `K0010` | `Maria` | `Kamińska` | `nieprawidłowy e-mail: 'maria.kaminska812o2.pl'; nieprawidłowy data rejestracji: '30.02.2022'` |
| `K0019` | `Ewa` | `Krawczyk` | `brak: e-mail` |
| `K0020` | `Magdalena` | `Kamińska` | `brak: telefon` |
| `K0022` | `Ewa` | `Woźniak` | `kod 60-532 nie pasuje do miasta Warszawa` |
| `K0025` | `Łukasz` | `Wiśniewski` | `brak: telefon` |
| `K0039` | `Agnieszka` | `Krawczyk` | `brak: e-mail` |
| `K0050` | `Magdalena` | `Lewandowska` | `kod 30-954 nie pasuje do miasta Warszawa` |
