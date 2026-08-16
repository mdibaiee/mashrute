# Data model

The extraction target is a bilingual (English / Persian) relational dataset about
the Iranian Constitutional Revolution, built from Janet Afary's
*The Iranian Constitutional Revolution, 1906–1911* and its Persian translation.

It is designed for a **static site generator**: build the SQLite file, query it,
emit pages. Three directories of entities — people, groups, events — plus places,
all cross-linked so any page can list the others.

## Files

```
data/raw/         book_en.txt, book.txt          the two scans
data/derived/     machine-parsed from the scans (chronology, index, page map)
data/extracted/   *.jsonl — the curated dataset (the actual deliverable)
mashruteh.db      built by scripts/build_db.py from data/extracted/
```

`data/extracted/*.jsonl` is the source of truth and is hand-verifiable. One JSON
object per line. Records are merged by `id`: a later record with the same `id`
patches the earlier one, so a chapter pass can add detail to an entity that an
earlier pass created.

## Identifiers

Slugs, ASCII, lowercase, hyphenated, derived from the English name:
`sattar-khan`, `tabriz-anjuman`, `bombardment-of-the-majlis-1908`.
Events append the year when a name could repeat. Slugs are stable — the site's
URLs depend on them.

## Bilingual rule

Every human-readable field has an `_en` and a `_fa` form. Never fall back to
English in a `_fa` field; leave it `null` so the site can show "untranslated"
rather than silently mixing scripts.

Persian names come from the Persian translation where it has them (via the
index harvest and body text); where the translation lacks a form, it is supplied
from standard Persian historiography and marked `name_fa_source: "editorial"`.

## Dates

Gregorian is the anchor. Solar Hijri is **computed** with the astronomical rule
(`scripts/dates.py`), never copied from the translation, which runs a day late
in 1285, 1286, 1289 and 1290 AP. Lunar Hijri is taken verbatim when the book
prints one and otherwise computed and flagged `approximate`, because historical
Qamari dating was observational.

Verified against outside sources:

| Gregorian | Solar Hijri | Lunar Hijri | check |
|---|---|---|---|
| 7 Oct 1906 | 14 Mehr 1285 | 18 Sha'ban 1324 | First Majlis opens |
| 15 Nov 1909 | 24 Aban 1288 | — | Second Majlis opens |
| 23 Jun 1908 | 2 Tir 1287 | 23 Jumada I 1326 | Majlis bombarded |

Whatever the book printed is kept in `date_book_json`, and any disagreement is
recorded in `date_issues_json`, so every correction is auditable.

`date_precision` ∈ `day | month | season | year | month_range | range | unknown`.
`date_sort` is always populated and safe to `ORDER BY`.

## Controlled vocabularies

### `groups.type`
| value | meaning |
|---|---|
| `anjuman` | council/society (provincial, municipal, guild, secret) |
| `political_party` | Democrat Party, Moderate Party, Dashnaks, Hnchaks |
| `secret_society` | Secret Center, Revolutionary Committee, secret anjumans |
| `militia` | Mujahidin, Fada'in, resistance forces |
| `religious_community` | Shi'ites, Azali Babis, Baha'is, Jews, Armenians (as confession), Zoroastrians |
| `religious_faction` | constitutionalist vs anti-constitutionalist 'ulama, Akhbari/Usuli schools |
| `ethnic_group` | Azerbaijanis, Armenians, Kurds, Bakhtiaris, Turkmen, Arabs |
| `tribe` | Bakhtiari, Qashqa'i, Shahsavan, Baluch |
| `guild` | asnaf — bakers, grocers, tailors … |
| `state_institution` | Majlis, cabinet, Cossack Brigade, customs administration |
| `foreign_power` | Britain, Russia, Ottoman Empire, Germany |
| `international_org` | Second International, Persia Committee |
| `newspaper` | Sur-i Israfil, Mulla Nasr al-Din, Iran-i Naw … |
| `school` | girls' schools, madrasas |
| `social_class` | merchants, 'ulama, peasants, artisans, workers |
| `womens_organization` | Anjuman of Ladies of the Homeland, women's councils |

### `events.type`
`protest` · `strike` · `sanctuary` (bast) · `assassination` · `execution` ·
`battle` · `siege` · `coup` · `election` · `legislation` · `decree` ·
`treaty` · `publication` · `founding` · `dissolution` · `appointment` ·
`dismissal` · `exile` · `massacre` · `occupation` · `ultimatum` ·
`conference` · `death` · `birth` · `uprising` · `reform` · `other`

### `event_participants.role_type`
`leader` · `participant` · `victim` · `perpetrator` · `signatory` ·
`opponent` · `witness` · `author` · `target` · `mediator`

### `person_groups.role_type`
`founder` · `leader` · `member` · `affiliate` · `representative` ·
`editor` · `opponent` · `patron`

## `is_historical_actor`

Afary's index lists modern historians (Abrahamian, Althusser, Wallerstein,
Skocpol, Keddie …) alongside the revolution's cast. Those rows get
`is_historical_actor = 0` so the site's people directory shows participants,
not the bibliography.

## JSONL record shapes

```jsonc
// people.jsonl
{"id":"sattar-khan","name_en":"Sattar Khan","name_fa":"ستارخان",
 "title_en":"Sardar-i Milli","title_fa":"سردار ملی","gender":"male",
 "role_en":"Leader of the Tabriz resistance","role_fa":"رهبر مقاومت تبریز",
 "birth":{"g_year":1868,"precision":"year"},
 "death":{"g_year":1914,"g_month":11,"g_day":17,"precision":"day"},
 "biography_en":"…","biography_fa":"…",
 "is_historical_actor":true,"book_pages":[211,212,213]}

// groups.jsonl
{"id":"tabriz-anjuman","name_en":"Tabriz Anjuman","name_fa":"انجمن تبریز",
 "type":"anjuman","place_id":"tabriz","founded":{"g_year":1906,"g_month":10,"g_day":7},
 "description_en":"…","description_fa":"…","book_pages":[75,76]}

// events.jsonl  — `date` is passed straight to scripts/dates.build_date()
{"id":"bombardment-of-the-majlis-1908","title_en":"Bombardment of the Majlis",
 "title_fa":"به توپ بستن مجلس","type":"coup","significance":1,
 "date":{"g_year":1908,"g_month":6,"g_day":23,"precision":"day",
         "book_jalali":{"year":1287,"month":4,"day":2}},
 "places":[{"id":"tehran","role":"primary"}],
 "summary_en":"…","summary_fa":"…","book_pages":[117,118]}

// relations.jsonl — discriminated by "rel"
{"rel":"person_group","person_id":"sattar-khan","group_id":"mujahidin",
 "role_type":"leader","role_en":"commander","role_fa":"فرمانده"}
{"rel":"event_participant","event_id":"…","person_id":"…","role_type":"victim",
 "role_en":"assassinated","role_fa":"ترور شد"}
{"rel":"event_group","event_id":"…","group_id":"…","role_type":"participant"}
{"rel":"event_place","event_id":"…","place_id":"…","role":"primary"}
{"rel":"person_relation","person_a":"…","person_b":"…","type":"ally"}
{"rel":"group_relation","group_a":"…","group_b":"…","type":"branch_of"}
```
