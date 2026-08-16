"""Harvest Lunar-Hijri (Qamari) dates from the Persian translation.

The English original converted every date to the Gregorian calendar. The Persian
translation, working from Persian primary sources, prints the Qamari date
alongside it in brackets — 388 times. Those are the dates the sources themselves
used, so harvesting them lets us replace computed (approximate) lunar dates with
attested ones.

Typical forms in the scan:
    ۳۱ ژوئية ۱۹۰۹ [۱۳ رجب ۱۳۲۷ هق./۹ مرداد ۱۲۸۸]
    اوت ۱۹۰۶ [جمادی‌الثانی ۱۳۲۴ هق. / مرداد ۱۲۸۵]
    ۱۹۰۷ [۱۳۲۵ هق./ ۱۲۸۶]

Output: data/derived/hijri_dates.json — a list of
    {gregorian: {...}, hijri: {...}, jalali: {...}, context: "..."}
keyed so build_hijri_index() can look a Gregorian date up directly.
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calendars import (FA_GREGORIAN_MONTH_ALIASES, FA_HIJRI_MONTH_ALIASES,  # noqa: E402
                       FA_JALALI_MONTH_ALIASES, fa_digits_to_en)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FA_PATH = os.path.join(ROOT, "data/raw/book.txt")
OUT = os.path.join(ROOT, "data/derived/hijri_dates.json")

D = r"[0-9۰-۹٠-٩]"
GREG = "|".join(sorted(FA_GREGORIAN_MONTH_ALIASES, key=len, reverse=True))
HIJ = "|".join(sorted(FA_HIJRI_MONTH_ALIASES, key=len, reverse=True))
JAL = "|".join(sorted(FA_JALALI_MONTH_ALIASES, key=len, reverse=True))

# A Gregorian date immediately followed by a bracket containing a Qamari date.
PAT = re.compile(
    rf"(?P<greg>(?:(?P<gd>{D}{{1,2}})\s*)?(?:(?P<gm>{GREG})\s*)?"
    rf"(?P<gy>[1۱١][89۸۹٨٩]{D}{{2}}))"
    rf"\s*[\[\(](?P<body>[^\]\)]{{0,90}}?(?:هق|ه\s*\.?\s*ق|قمری)[^\]\)]{{0,60}})[\]\)]"
)

HIJ_RE = re.compile(rf"(?:(?P<hd>{D}{{1,2}})\s*)?(?P<hm>{HIJ})\s*(?P<hy>{D}{{3,4}})")
HIJ_YEAR_ONLY = re.compile(rf"(?<!{D})(?P<hy>1[23][0-9۰-۹٠-٩]{{2}}|[۱١][۲۳٢٣]{D}{{2}})(?!{D})")
JAL_RE = re.compile(rf"(?:(?P<jd>{D}{{1,2}})\s*)?(?P<jm>{JAL})\s*(?P<jy>{D}{{4}})")


def _i(x):
    if x is None:
        return None
    v = fa_digits_to_en(str(x)).strip()
    return int(v) if v.isdigit() else None


def harvest() -> list[dict]:
    text = open(FA_PATH, encoding="utf-8", errors="replace").read()
    text = re.sub(r"[ \t]+", " ", text)
    out: list[dict] = []
    for m in PAT.finditer(text):
        gy, gm, gd = _i(m.group("gy")), m.group("gm"), _i(m.group("gd"))
        if not gy or not (1800 < gy < 1930):
            continue
        body = m.group("body")

        hm = HIJ_RE.search(body)
        hijri = None
        if hm:
            hy = _i(hm.group("hy"))
            if hy and 1200 < hy < 1400:
                hijri = {"year": hy, "month": FA_HIJRI_MONTH_ALIASES[hm.group("hm")],
                         "day": _i(hm.group("hd")),
                         "precision": "day" if _i(hm.group("hd")) else "month"}
        if hijri is None:
            ym = HIJ_YEAR_ONLY.search(body)
            if ym:
                hy = _i(ym.group("hy"))
                if hy and 1200 < hy < 1400:
                    hijri = {"year": hy, "month": None, "day": None,
                             "precision": "year"}
        if hijri is None:
            continue

        jal = None
        jm_ = JAL_RE.search(body)
        if jm_:
            jy = _i(jm_.group("jy"))
            if jy and 1200 < jy < 1400:
                jal = {"year": jy, "month": FA_JALALI_MONTH_ALIASES[jm_.group("jm")],
                       "day": _i(jm_.group("jd"))}

        out.append({
            "gregorian": {"year": gy,
                          "month": FA_GREGORIAN_MONTH_ALIASES[gm] if gm else None,
                          "day": gd},
            "hijri": hijri,
            "jalali": jal,
            "raw": re.sub(r"\s+", " ", m.group(0)).strip(),
        })
    return out


def build_index(records: list[dict]) -> dict:
    """Map an ISO-ish Gregorian key to the best attested Hijri date."""
    idx: dict[str, dict] = {}
    for r in records:
        g, h = r["gregorian"], r["hijri"]
        if g["month"] and g["day"]:
            key = f"{g['year']:04d}-{g['month']:02d}-{g['day']:02d}"
        elif g["month"]:
            key = f"{g['year']:04d}-{g['month']:02d}"
        else:
            key = f"{g['year']:04d}"
        prev = idx.get(key)
        # prefer the most precise attestation
        rank = {"day": 3, "month": 2, "year": 1}
        if not prev or rank[h["precision"]] > rank[prev["hijri"]["precision"]]:
            idx[key] = r
    return idx


def main() -> None:
    recs = harvest()
    idx = build_index(recs)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"records": recs, "index": idx}, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    byprec: dict[str, int] = {}
    for r in recs:
        byprec[r["hijri"]["precision"]] = byprec.get(r["hijri"]["precision"], 0) + 1
    print(f"Qamari dates harvested : {len(recs)}")
    print(f"  by precision         : {byprec}")
    print(f"unique Gregorian keys  : {len(idx)}")
    print(f"  full-day keys        : {sum(1 for k in idx if len(k) == 10)}")
    print(f"-> {OUT}")
    print("\nsample:")
    for r in recs[:8]:
        print("   ", r["raw"][:80])


if __name__ == "__main__":
    main()
