# Extraction progress

Source: Janet Afary, *The Iranian Constitutional Revolution, 1906–1911* (Columbia
UP 1996) + Persian translation by Reza Rezaei (نشر بیستون 1385).

## Done — machine parsing (`data/derived/`)

| output | what | status |
|---|---|---|
| `chronology.json` | 98 EN entries, 92 FA, 90 aligned bilingual | ✅ |
| `index_en.json` | 897 headwords, 1287 sub-entries, 3896 page refs, 18 life-date pairs | ✅ |
| `index_fa_candidates.json` | 805 Persian headword forms for spelling checks | ✅ |
| `page_map_en.json` | 470 printed pages → line ranges in the scan | ✅ |
| `nowruz_table.json` | the translation's (incorrect) Nowruz convention, for audit | ✅ |

Index entries 860–896 are back-cover blurb, not index content — excluded.

## Calendar policy — settled

Gregorian is the anchor; Solar Hijri is **computed** astronomically, never copied
from the translation (which runs a day late in 1285/1286/1289/1290 AP). Lunar
Hijri verbatim when the book prints it, else computed and flagged approximate.
Verified: 7 Oct 1906 = 14 Mehr 1285 = 18 Sha'ban 1324; 15 Nov 1909 = 24 Aban 1288;
23 Jun 1908 = 2 Tir 1287 = 23 Jumada I 1326. See `docs/DATA_MODEL.md`.

## Curated dataset (`data/extracted/*.jsonl`) — first pass complete

| file | rows | status |
|---|---|---|
| `places.jsonl` | 99 | ✅ first pass |
| `groups.jsonl` | 150 | ✅ first pass |
| `people.jsonl` | 231 | 🟡 core cast done; long tail of index names outstanding |
| `events.jsonl` | 111 | 🟡 chronology + context done; body-derived events outstanding |
| `relations.jsonl` | 399 | 🟡 major links done, thinner on minor figures |

`python3 scripts/build_db.py` builds `mashruteh.db`; `python3 scripts/report.py`
prints coverage. All names are bilingual (100% `name_fa` coverage); prose
(`biography_fa`, `summary_fa`) is partial and is the main translation debt.

### Known gaps, in priority order
1. **101 people and 84 groups have no links yet** — mostly minor index names that
   need an event or membership edge before they earn a page.
2. **`biography_fa` on 198 people, `description_fa` on 58 groups** untranslated.
3. **Body-derived events** — the chronology yields ~100 events; the narrative
   holds several hundred more (guild strikes, provincial risings, individual
   anjuman actions, press prosecutions).
4. **Roster tables not yet mined**: First Majlis guild deputies (EN p. 65–68,
   scan lines 3552–3589) and Second Majlis Democrat deputies (lines 11599+)
   give named deputy lists with constituencies and party.
5. **Lunar Hijri dates are all computed** (±1–2 days). The book prints Qamari
   dates in the notes and body; harvesting those would let us mark them `book`.
6. ~70 modern scholars cited by Afary still to be entered with
   `is_historical_actor = 0` so they stay out of the people directory.

## Body reading passes

Chapters of the English body (`data/raw/book_en.txt`), printed pages:

| # | chapter | pages | status |
|---|---|---|---|
| — | Introduction | 1–14 | ⏳ (theory/historiography only) |
| 1 | From Dependency to Resistance | 17–33 | ✅ |
| 2 | The Tempest of Revolution | 34–58 | ✅ |
| 3 | First Majlis, urban anjumans, Social Democrats | 59–90 | ✅ |
| 4 | Constitutionalism or Shari'at? | 91–118 | ✅ |
| 5 | Press, satire and revolution | 119–145 | ✅ |
| 6 | Peasants, artisans and fishermen | 146–176 | ✅ |
| 7 | Women's anjumans | 177–208 | ✅ |
| 8 | Civil war in Azerbaijan | 211–227 | ✅ |
| 9 | Solidarity of nations: reconquest of Tehran | 228–253 | ⏳ |
| 10 | Second Majlis and the Democrat Party | 257–281 | ⏳ |
| 11 | Assassination, exile, imperialist pressure | 282–303 | ⏳ |
| 12 | Imperialist intervention: "The Strangling of Persia" | 304–342 | ⏳ |

## Verification tooling

- `scripts/fa_lookup.py NAME…` — confirm a Persian spelling occurs in the book
- `scripts/build_page_map.py N` — print printed page N of the English scan
- `python3 scripts/build_db.py` — rebuild `mashruteh.db`, runs a FK check
