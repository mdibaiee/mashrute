"""Derive the Nowruz (1 Farvardin) Gregorian date implied by the book's own
dual-dated chronology entries, and compare it with the astronomical rule.

Retroactive Solar-Hijri dates for pre-1925 events are a convention, not an
observation: Iran's official solar calendar dates only from 1925, so every
Solar-Hijri date for our period is a back-conversion. The book's translator used
one convention; the astronomical equinox rule gives another, differing by a day
in some years. To stay internally consistent with our source we adopt the book's
convention, derived here from its own evidence.
"""

from __future__ import annotations

import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calendars import (gregorian_to_jd, jd_to_gregorian, nowruz_jd)  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHRON = os.path.join(ROOT, "data/derived/chronology.json")
OUT = os.path.join(ROOT, "data/derived/nowruz_table.json")

# day-of-year offset of the 1st of each Jalali month (0-based)
MONTH_OFFSET = [0, 31, 62, 93, 124, 155, 186, 216, 246, 276, 306, 336]


def main() -> None:
    entries = json.load(open(CHRON, encoding="utf-8"))
    votes: dict[int, collections.Counter] = collections.defaultdict(collections.Counter)
    evidence: dict[int, list] = collections.defaultdict(list)

    for e in entries:
        g, j = e.get("gregorian") or {}, e.get("jalali")
        if not j or j.get("precision") != "day":
            continue
        if g.get("precision") not in ("day",) or not all(
                g.get(k) for k in ("g_year", "g_month", "g_day")):
            continue
        jy, jm, jd = j["year"], j["month"], j["day"]
        if not (1200 < jy < 1400 and 1 <= jm <= 12 and 1 <= jd <= 31):
            continue
        jdn = gregorian_to_jd(g["g_year"], g["g_month"], g["g_day"])
        nowruz = jdn - (MONTH_OFFSET[jm - 1] + jd - 1)
        votes[jy][nowruz] += 1
        evidence[jy].append((f"{g['g_year']}-{g['g_month']:02d}-{g['g_day']:02d}",
                             f"{jd} m{jm} {jy}", jd_to_gregorian(nowruz)))

    print(f"{'AP':>5} {'book Nowruz':>13} {'astro Nowruz':>13}  votes   note")
    table = {}
    for jy in sorted(votes):
        winner, n = votes[jy].most_common(1)[0]
        total = sum(votes[jy].values())
        astro = nowruz_jd(jy)
        by, bm, bd = jd_to_gregorian(winner)
        ay, am, ad = jd_to_gregorian(astro)
        note = "" if winner == astro else f"differs by {winner - astro:+d} d"
        if n < total:
            note += f"  [conflicting: {dict(collections.Counter({jd_to_gregorian(k)[1:]: v for k, v in votes[jy].items()}))}]"
        print(f"{jy:>5} {by}-{bm:02d}-{bd:02d} {ay}-{am:02d}-{ad:02d}  {n}/{total:<4} {note}")
        table[str(jy)] = {"nowruz_jd": winner,
                          "nowruz_gregorian": f"{by}-{bm:02d}-{bd:02d}",
                          "support": n, "total": total,
                          "astronomical_jd": astro,
                          "delta_days": winner - astro}

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(table, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n-> {OUT}")

    # Show the disagreeing evidence so OCR noise can be told from real convention.
    for jy in sorted(votes):
        if len(votes[jy]) > 1:
            print(f"\nconflicts for {jy} AP:")
            for greg, jal, now in sorted(evidence[jy]):
                print(f"   {greg}  =  {jal:>14}   -> Nowruz {now[0]}-{now[1]:02d}-{now[2]:02d}")


if __name__ == "__main__":
    main()
