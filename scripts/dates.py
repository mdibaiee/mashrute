"""Canonical date handling for the project.

POLICY
------
Dates published on the site must be *correct*, not merely faithful to the book.
Both the English original and the Persian translation contain conversion errors,
and the Persian scan adds OCR corruption on top. So:

1. The **Gregorian** date is the anchor. It comes from the book (the English
   original is the more reliable of the two) unless an outside source shows it
   to be wrong, in which case the corrected value is used and the book's value
   is retained in `book_printed` with a note.

2. The **Solar Hijri** date is always COMPUTED from the Gregorian anchor using
   the astronomical (equinox-based, Tehran apparent noon) rule -- the official
   definition of the Iranian calendar. It is never copied from the translation.
   Verified against outside sources:
       7 Oct 1906  = 14 Mehr 1285   (18 Sha'ban 1324)   [fa.wikipedia]
       15 Nov 1909 = 24 Aban 1288                        [fa.wikipedia]
       23 Jun 1908 = 2 Tir 1287                          [well attested]
   The Persian translation runs one day late in 1285, 1286, 1289 and 1290 AP,
   because it used an arithmetic converter whose Nowruz falls a day early.

3. The **Lunar Hijri** date is taken verbatim when the book prints one (those
   come from the primary sources, which were lunar-dated). Otherwise it is
   computed with the tabular Islamic calendar and marked `approximate`, since
   historical Qamari dating was observational and can differ by a day or two.

Every record keeps `book_printed` so a discrepancy can always be audited, and
`discrepancies` lists any disagreement we detected.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calendars import (  # noqa: E402
    GREGORIAN_MONTHS_EN, HIJRI_MONTHS_EN, HIJRI_MONTHS_FA, JALALI_MONTHS_EN,
    JALALI_MONTHS_FA, format_gregorian_fa, gregorian_to_jalali, gregorian_to_jd,
    jd_to_islamic, en_digits_to_fa)

SEASON_FA = {"spring": "بهار", "summer": "تابستان", "fall": "پاییز",
             "winter": "زمستان", "early": "اوایل", "late": "اواخر"}
SEASON_MONTHS = {"spring": (3, 5), "summer": (6, 8), "fall": (9, 11), "winter": (12, 2)}

# Precision vocabulary used throughout the dataset.
PRECISIONS = ("day", "month", "season", "year", "month_range", "range", "unknown")


def _iso(y: int | None, m: int | None, d: int | None) -> str | None:
    if not y:
        return None
    if m and d:
        return f"{y:04d}-{m:02d}-{d:02d}"
    if m:
        return f"{y:04d}-{m:02d}"
    return f"{y:04d}"


def _sort_key(y: int | None, m: int | None, d: int | None,
              season: str | None = None) -> str:
    """Stable chronological sort key, usable even for fuzzy dates."""
    if not y:
        return "9999-99-99"
    if not m and season:
        m = SEASON_MONTHS.get(season, (6, 8))[0]
    return f"{y:04d}-{(m or 0):02d}-{(d or 0):02d}"


def build_date(g_year: int | None,
               g_month: int | None = None,
               g_day: int | None = None,
               precision: str = "day",
               *,
               g_year_end: int | None = None,
               g_month_end: int | None = None,
               g_day_end: int | None = None,
               season: str | None = None,
               season_end: str | None = None,
               book_jalali: dict | None = None,
               book_hijri: dict | None = None,
               book_gregorian_raw: str | None = None,
               note: str | None = None) -> dict:
    """Build the canonical bilingual, multi-calendar date record for one event."""
    rec: dict = {
        "precision": precision,
        "sort_key": _sort_key(g_year, g_month, g_day, season),
        "gregorian": None,
        "jalali": None,
        "hijri": None,
        "end": None,
        "book_printed": {},
        "discrepancies": [],
    }
    if note:
        rec["note"] = note

    if g_year:
        rec["gregorian"] = {
            "year": g_year, "month": g_month, "day": g_day,
            "iso": _iso(g_year, g_month, g_day),
            "display_en": _display_gregorian_en(g_year, g_month, g_day, season),
            "display_fa": _display_gregorian_fa(g_year, g_month, g_day, season),
        }

    # --- Solar Hijri, always computed from the Gregorian anchor -------------
    if g_year and g_month and g_day:
        jy, jm, jd = gregorian_to_jalali(g_year, g_month, g_day)
        rec["jalali"] = _jalali_rec(jy, jm, jd)
    elif g_year and g_month:
        # A Gregorian month spans two Jalali months; give the range.
        j1 = gregorian_to_jalali(g_year, g_month, 1)
        last = _last_day_of_gregorian_month(g_year, g_month)
        j2 = gregorian_to_jalali(g_year, g_month, last)
        rec["jalali"] = _jalali_rec(j1[0], j1[1], None, j2 if j2[:2] != j1[:2] else None)
    elif g_year:
        j1 = gregorian_to_jalali(g_year, 1, 1)
        j2 = gregorian_to_jalali(g_year, 12, 31)
        rec["jalali"] = {
            "year": j1[0], "year_end": j2[0], "month": None, "day": None,
            "precision": "year_range",
            "display_en": f"{j1[0]}-{j2[0]} AP",
            "display_fa": en_digits_to_fa(f"{j1[0]}–{j2[0]} ش"),
        }

    # --- Lunar Hijri: book value preferred, else computed -------------------
    if book_hijri and book_hijri.get("year"):
        rec["hijri"] = {
            "year": book_hijri["year"], "month": book_hijri.get("month"),
            "day": book_hijri.get("day"), "source": "book", "approximate": False,
            "display_en": _display_hijri_en(book_hijri.get("day"),
                                            book_hijri.get("month"), book_hijri["year"]),
            "display_fa": _display_hijri_fa(book_hijri.get("day"),
                                            book_hijri.get("month"), book_hijri["year"]),
        }
    elif g_year and g_month and g_day:
        hy, hm, hd = jd_to_islamic(gregorian_to_jd(g_year, g_month, g_day))
        rec["hijri"] = {
            "year": hy, "month": hm, "day": hd, "source": "computed",
            "approximate": True,
            "display_en": _display_hijri_en(hd, hm, hy),
            "display_fa": _display_hijri_fa(hd, hm, hy),
        }

    # --- end of a range -----------------------------------------------------
    if g_year_end or g_month_end or g_day_end:
        ey = g_year_end or g_year
        em, ed = g_month_end, g_day_end
        rec["end"] = {
            "gregorian": {"year": ey, "month": em, "day": ed, "iso": _iso(ey, em, ed),
                          "display_en": _display_gregorian_en(ey, em, ed, season_end)},
            "jalali": _jalali_rec(*gregorian_to_jalali(ey, em, ed)) if (ey and em and ed) else None,
        }
    if season:
        rec["season"] = season
        rec["season_fa"] = SEASON_FA.get(season)
    if season_end:
        rec["season_end"] = season_end
        rec["season_end_fa"] = SEASON_FA.get(season_end)

    # --- provenance & discrepancy audit -------------------------------------
    if book_gregorian_raw:
        rec["book_printed"]["gregorian_raw"] = book_gregorian_raw
    if book_jalali:
        rec["book_printed"]["jalali"] = book_jalali
        got = rec.get("jalali")
        if got and book_jalali.get("day") and got.get("day"):
            if (book_jalali.get("year"), book_jalali.get("month"), book_jalali.get("day")) \
                    != (got["year"], got["month"], got["day"]):
                rec["discrepancies"].append({
                    "field": "jalali",
                    "book": f"{book_jalali.get('day')} "
                            f"{JALALI_MONTHS_EN[book_jalali['month'] - 1] if book_jalali.get('month') else '?'} "
                            f"{book_jalali.get('year')}",
                    "computed": got["display_en"],
                    "reason": "translation used an arithmetic converter one day early, "
                              "or the scan corrupted a digit",
                })
    if book_hijri:
        rec["book_printed"]["hijri"] = book_hijri
    return rec


def _last_day_of_gregorian_month(y: int, m: int) -> int:
    if m == 12:
        return 31
    return (gregorian_to_jd(y + (m == 12), m % 12 + 1, 1) - gregorian_to_jd(y, m, 1))


def _jalali_rec(jy: int, jm: int, jd: int | None, end: tuple | None = None) -> dict:
    rec = {
        "year": jy, "month": jm, "day": jd,
        "precision": "day" if jd else "month",
        "display_en": (f"{jd} {JALALI_MONTHS_EN[jm - 1]} {jy}" if jd
                       else f"{JALALI_MONTHS_EN[jm - 1]} {jy}"),
        "display_fa": en_digits_to_fa(
            f"{jd} {JALALI_MONTHS_FA[jm - 1]} {jy}" if jd
            else f"{JALALI_MONTHS_FA[jm - 1]} {jy}"),
        "source": "computed",
    }
    if end:
        rec["month_end"] = end[1]
        rec["year_end"] = end[0]
        rec["precision"] = "month_range"
        rec["display_en"] = f"{JALALI_MONTHS_EN[jm - 1]}-{JALALI_MONTHS_EN[end[1] - 1]} {jy}"
        rec["display_fa"] = en_digits_to_fa(
            f"{JALALI_MONTHS_FA[jm - 1]}–{JALALI_MONTHS_FA[end[1] - 1]} {jy}")
    return rec


def _display_gregorian_en(y, m, d, season=None) -> str:
    if season and not m:
        return f"{season.capitalize()} {y}"
    if m and d:
        return f"{GREGORIAN_MONTHS_EN[m - 1]} {d}, {y}"
    if m:
        return f"{GREGORIAN_MONTHS_EN[m - 1]} {y}"
    return str(y)


def _display_gregorian_fa(y, m, d, season=None) -> str:
    if season and not m:
        return en_digits_to_fa(f"{SEASON_FA.get(season, season)} {y}")
    return format_gregorian_fa(y, m, d) if m else en_digits_to_fa(str(y))


def _display_hijri_en(d, m, y) -> str:
    if m and d:
        return f"{d} {HIJRI_MONTHS_EN[m - 1]} {y} AH"
    if m:
        return f"{HIJRI_MONTHS_EN[m - 1]} {y} AH"
    return f"{y} AH"


def _display_hijri_fa(d, m, y) -> str:
    if m and d:
        return en_digits_to_fa(f"{d} {HIJRI_MONTHS_FA[m - 1]} {y} ق")
    if m:
        return en_digits_to_fa(f"{HIJRI_MONTHS_FA[m - 1]} {y} ق")
    return en_digits_to_fa(f"{y} ق")


if __name__ == "__main__":
    import json
    demo = build_date(1906, 10, 7, "day",
                      book_jalali={"year": 1285, "month": 7, "day": 15})
    print(json.dumps(demo, ensure_ascii=False, indent=1))
