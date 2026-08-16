"""Parse the 'Chronology of the Major Events' from both the English original and
the Persian translation, then align them entry-by-entry.

Output: data/derived/chronology.json  — a list of aligned entries, each with the
English and Persian text plus every date the book itself prints (Gregorian,
Solar Hijri, and Lunar Hijri where given).

The two chronologies are translations of one another and run in the same order,
so alignment is by sequence, verified by comparing the parsed Gregorian dates.
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calendars import (EN_MONTHS, FA_GREGORIAN_MONTH_ALIASES,  # noqa: E402
                       FA_HIJRI_MONTH_ALIASES, FA_JALALI_MONTH_ALIASES,
                       fa_digits_to_en)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EN_PATH = os.path.join(ROOT, "data/raw/book_en.txt")
FA_PATH = os.path.join(ROOT, "data/raw/book.txt")
OUT_PATH = os.path.join(ROOT, "data/derived/chronology.json")

EN_RANGE = (393, 594)      # 1-based inclusive line numbers
FA_RANGE = (16024, 16303)  # ends where the bibliography (کتاب شناسی) begins

# ------------------------------------------------------------------ English

EN_MONTH_RE = (r"(?:Januaty|January|Janua|Februaty|February|Febmary|Febraury|March|Matrch|"
               r"April|Aptil|Apri|May|June|July|August|Augus|September|Sept|Septembet|"
               r"October|Octobet|November|Novembet|December|Decembet)")
EN_SEASONS = {"summer": "summer", "fall": "fall", "winter": "winter", "spring": "spring",
              "late": "late", "early": "early"}
# A year, allowing the scan's habit of rendering '19' as 'ig'/'1g'/'i9'.
EN_YEAR_RE = re.compile(r"(?<![\dA-Za-z])((?:1[89]|ig|1g|i9|I9)\d{2})(?![\d])")
_EN_HEAD_WORDS = re.compile(
    rf"(?i)\b(?:{EN_MONTH_RE}|summer|fall|winter|spring|late|early|and|to|or)\b\.?")


def _en_head_is_date(prefix: str) -> bool:
    p = _EN_HEAD_WORDS.sub(" ", prefix)
    p = re.sub(r"[\d\s,;.\-–—_’'‘\"()]+", "", p)
    return p == ""
EN_PAGE_RE = re.compile(r"^\s*(?:xv|xvi|xvii|xviii|xix|xx|xxi|xxii)\s|Chronology of the Major Events")
EN_PERIOD_RE = re.compile(r"^\s*(First|Second)\s+Constitutional\s+Period", re.I)
EN_MINOR_RE = re.compile(r"^\s*(Period of Lesser Autocracy|Minor Autocracy)", re.I)


def read_lines(path: str) -> list[str]:
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read().split("\n")


def clean_ocr_en(s: str) -> str:
    s = s.replace("‘", "'").replace("’", "'")
    s = re.sub(r"\s+", " ", s).strip()
    # 'The -> The  (OCR renders a leading quote before capital T)
    s = re.sub(r"^'(The|A|An)\b", r"\1", s)
    s = re.sub(r"\bi9(\d\d)\b", r"19\1", s)
    s = re.sub(r"\b1g(\d\d)\b", r"19\1", s)
    s = re.sub(r"\big(\d\d)\b", r"19\1", s)
    s = re.sub(r"\bIran\b", "Iran", s)
    s = re.sub(r"\btran\b", "Iran", s)
    s = re.sub(r"\bMailis\b", "Majlis", s)
    s = re.sub(r"\bMaijlis\b", "Majlis", s)
    s = re.sub(r"\bMajis\b", "Majlis", s)
    s = re.sub(r"\bahouse\b", "a house", s)
    s = re.sub(r"\baconstitution\b", "a constitution", s)
    s = re.sub(r"\ba(?=[a-z]{4,}\b)", "a ", s) if False else s
    s = re.sub(r"\s+([,.;:])", r"\1", s)
    return s.strip()


def parse_en_period(tag: str):
    """Parse an English date string into structured Gregorian components."""
    t = clean_ocr_en(tag)
    t = t.rstrip(" .,_")
    years = re.findall(r"\b(1[89]\d\d)\b", t)
    out: dict = {"raw_en": t}
    # explicit day: "January 22, 1905"
    m = re.match(rf"^({EN_MONTH_RE})\.?\s+(\d{{1,2}})\s*,?\s*(1[89]\d\d)$", t)
    if m:
        out.update(precision="day", g_year=int(m.group(3)),
                   g_month=EN_MONTHS[m.group(1).lower().rstrip('.')],
                   g_day=int(m.group(2)))
        return out
    # month + year: "May 1904"
    m = re.match(rf"^({EN_MONTH_RE})\.?,?\s+(1[89]\d\d)$", t)
    if m:
        out.update(precision="month", g_year=int(m.group(2)),
                   g_month=EN_MONTHS[m.group(1).lower().rstrip('.')])
        return out
    # month range in one year: "March-April 1905"
    m = re.match(rf"^({EN_MONTH_RE})\s*[-–—]\s*({EN_MONTH_RE})\.?,?\s+(1[89]\d\d)$", t)
    if m:
        out.update(precision="month_range", g_year=int(m.group(3)),
                   g_month=EN_MONTHS[m.group(1).lower()],
                   g_month_end=EN_MONTHS[m.group(2).lower()],
                   g_year_end=int(m.group(3)))
        return out
    # season(s): "Summer-Fall 1907", "Summer 1907"
    m = re.match(r"^(Summer|Fall|Winter|Spring)(?:\s*[-–—]\s*(Summer|Fall|Winter|Spring))?\s+(1[89]\d\d)$", t)
    if m:
        out.update(precision="season", g_year=int(m.group(3)),
                   season=m.group(1), season_end=m.group(2))
        return out
    # cross-year range: "December 1911-January 1912"
    m = re.match(rf"^({EN_MONTH_RE})\s*(\d{{1,2}})?,?\s*(1[89]\d\d)\s*[-–—]\s*({EN_MONTH_RE})\s*(\d{{1,2}})?,?\s*(1[89]\d\d)$", t)
    if m:
        out.update(precision="range", g_year=int(m.group(3)),
                   g_month=EN_MONTHS[m.group(1).lower()],
                   g_day=int(m.group(2)) if m.group(2) else None,
                   g_year_end=int(m.group(6)),
                   g_month_end=EN_MONTHS[m.group(4).lower()],
                   g_day_end=int(m.group(5)) if m.group(5) else None)
        return out
    # bare year
    if re.match(r"^1[89]\d\d$", t):
        out.update(precision="year", g_year=int(t))
        return out
    if years:
        out.update(precision="unparsed_year", g_year=int(years[0]))
    else:
        out.update(precision="unparsed")
    return out


def parse_en_chronology() -> list[dict]:
    lines = read_lines(EN_PATH)[EN_RANGE[0] - 1:EN_RANGE[1]]
    entries: list[dict] = []
    current: dict | None = None
    period = None
    for raw in lines:
        if not raw.strip():
            continue
        if EN_PAGE_RE.search(raw):
            continue
        if EN_PERIOD_RE.match(raw) or EN_MINOR_RE.match(raw):
            period = clean_ocr_en(raw)
            continue
        ym = EN_YEAR_RE.search(raw)
        if ym and ym.start() <= 44 and _en_head_is_date(raw[:ym.start()]):
            if current:
                entries.append(current)
            end = ym.end()
            # extend across a range tail: "December 1911-January 1912"
            tail = re.match(rf"\s*[-–—]\s*(?:{EN_MONTH_RE})?\.?\s*\d{{0,2}},?\s*"
                            rf"(?:1[89]|ig|1g|i9)\d{{2}}", raw[end:], re.I)
            if tail:
                end += tail.end()
            current = {"date_raw_en": clean_ocr_en(raw[:end]),
                       "text_en": clean_ocr_en(raw[end:].lstrip(" .,_")),
                       "period_en": period}
        elif current is not None:
            current["text_en"] = clean_ocr_en(current["text_en"] + " " + raw)
    if current:
        entries.append(current)
    for e in entries:
        e["date_en"] = parse_en_period(e["date_raw_en"])
    return entries


# ------------------------------------------------------------------ Persian

FA_GREG_MONTHS = "|".join(sorted(FA_GREGORIAN_MONTH_ALIASES, key=len, reverse=True))
FA_JAL_MONTHS = "|".join(sorted(FA_JALALI_MONTH_ALIASES, key=len, reverse=True))
FA_HIJ_MONTHS = "|".join(sorted(FA_HIJRI_MONTH_ALIASES, key=len, reverse=True))

# leading OCR bullet junk: "07 ", "0 ", "2 ", "۲ ", "۱٩ ", "| ", "7 " ...
FA_BULLET_RE = re.compile(r"^[\s‌]*(?:[|:•]\s*)?(?:[0-9۰-۹٠-٩]{1,3}(?=\s)\s*)?[\s.\-–|]*")
FA_PAGE_RE = re.compile(r"^\s*[0-9۰-۹٠-٩]*\s*[|/]\s*(تقویم|تفویم|نمایه|نمابه|کتاب)")
FA_PERIOD_RE = re.compile(r"^\s*(مشروط[هةٌۀ]?\s*(اول|دوم)|استبداد\s*صغیر)\s*[:：]")

FA_D = r"[0-9۰-۹٠-٩]"
# A four-digit Gregorian year in any mix of Latin/Persian/Arabic-Indic digits.
FA_YEAR_RE = re.compile(rf"(?<!{FA_D})([1۱١][89۸۹٨٩]{FA_D}{{2}})(?!{FA_D})")

FA_SEASONS = {
    "بهار": "spring", "تابستان": "summer", "پاییز": "fall", "پاييز": "fall",
    "زمستان": "winter", "اوایل": "early", "اواخر": "late", "اوآخر": "late",
    "پائیز": "fall",
}
_FA_HEAD_WORDS = sorted(list(FA_GREGORIAN_MONTH_ALIASES) + list(FA_SEASONS),
                        key=len, reverse=True)
_FA_JUNK_RE = re.compile(r"(?:\bتا\b|[0-9۰-۹٠-٩\s\-–—.,،؛:/\\|()\[\]‌])+")


def _fa_head_is_date(prefix: str) -> bool:
    """True if everything before the year looks like day/month/season tokens only."""
    p = prefix
    for w in _FA_HEAD_WORDS:
        p = p.replace(w, " ")
    p = p.replace("تا", " ")
    p = _FA_JUNK_RE.sub("", p)
    return len(p) <= 1


def normalize_fa(s: str) -> str:
    s = s.replace("‌", "‌")
    s = re.sub(r"[«»\"]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _fa_int(x) -> int | None:
    if x is None:
        return None
    x = fa_digits_to_en(str(x)).strip()
    return int(x) if x.isdigit() else None


def parse_fa_bracket_dates(text: str) -> dict:
    """Extract the Solar-Hijri (and Lunar-Hijri) dates the translator put in [...]."""
    out: dict = {}
    for br in re.findall(r"\[([^\]]*)\]", text):
        b = fa_digits_to_en(br)
        is_lunar = bool(re.search(r"ه\s*\.?\s*ق|هق|قمری", b))
        months = FA_HIJRI_MONTH_ALIASES if is_lunar else FA_JALALI_MONTH_ALIASES
        pat = FA_HIJ_MONTHS if is_lunar else FA_JAL_MONTHS
        key = "hijri" if is_lunar else "jalali"
        m = re.search(rf"(?:(\d{{1,2}})\s*)?({pat})\s*(\d{{3,4}})", b)
        if m:
            rec = {"raw": normalize_fa(br), "month": months[m.group(2)],
                   "year": int(m.group(3)),
                   "day": int(m.group(1)) if m.group(1) else None}
            rec["precision"] = "day" if rec["day"] else "month"
            out[key] = rec
            continue
        m = re.search(r"^\s*(\d{3,4})\s*(?:[-–—]\s*(\d{3,4}))?\s*(?:ه\s*\.?\s*ق\.?)?\s*$", b)
        if m:
            out[key] = {"raw": normalize_fa(br), "year": int(m.group(1)),
                        "year_end": int(m.group(2)) if m.group(2) else None,
                        "precision": "year"}
    return out


def parse_fa_date_head(head: str) -> dict:
    """Parse the Gregorian date that opens a Persian chronology entry."""
    out: dict = {"raw_fa": normalize_fa(head)}
    # locate month/season tokens with their positions
    toks: list[tuple[int, str, str]] = []
    for w in _FA_HEAD_WORDS:
        start = 0
        while True:
            i = head.find(w, start)
            if i < 0:
                break
            kind = "season" if w in FA_SEASONS else "month"
            toks.append((i, kind, w))
            start = i + len(w)
    # drop tokens contained inside a longer token at the same place
    toks.sort(key=lambda t: (t[0], -len(t[2])))
    kept: list[tuple[int, str, str]] = []
    for t in toks:
        if kept and t[0] < kept[-1][0] + len(kept[-1][2]):
            continue
        kept.append(t)
    months = [t for t in kept if t[1] == "month"]
    seasons = [t for t in kept if t[1] == "season"]
    year_m = FA_YEAR_RE.search(head)
    out["g_year"] = _fa_int(year_m.group(1)) if year_m else None
    # day numbers: 1-2 digit runs that are not part of the year
    days = [(m.start(), _fa_int(m.group(0)))
            for m in re.finditer(rf"(?<!{FA_D}){FA_D}{{1,2}}(?!{FA_D})", head)]
    days = [(p, v) for p, v in days if v and 1 <= v <= 31]
    if months:
        out["g_month"] = FA_GREGORIAN_MONTH_ALIASES[months[0][2]]
        before = [v for p, v in days if p < months[0][0]]
        after_first = [v for p, v in days
                       if months[0][0] < p < (months[1][0] if len(months) > 1
                                              else (year_m.start() if year_m else len(head)))]
        if before:
            out["g_day"] = before[-1]
        elif after_first:
            out["g_day"] = after_first[0]
        if len(months) > 1:
            out["g_month_end"] = FA_GREGORIAN_MONTH_ALIASES[months[1][2]]
            tail = [v for p, v in days
                    if months[1][0] > p > months[0][0]] or \
                   [v for p, v in days if p > months[1][0] and
                    (not year_m or p < year_m.start())]
            if tail:
                out["g_day_end"] = tail[-1]
    if seasons:
        out["season"] = FA_SEASONS[seasons[0][2]]
        if len(seasons) > 1:
            out["season_end"] = FA_SEASONS[seasons[1][2]]
    if out.get("g_day"):
        out["precision"] = "day"
    elif out.get("g_month_end"):
        out["precision"] = "month_range"
    elif out.get("g_month"):
        out["precision"] = "month"
    elif out.get("season"):
        out["precision"] = "season"
    elif out.get("g_year"):
        out["precision"] = "year"
    else:
        out["precision"] = "unparsed"
    return out


_FA_MIDLINE_RE = re.compile(
    rf"(?<=\S)\s+(?=(?:[0-9۰-۹٠-٩]{{1,2}}\s*)?(?:{FA_GREG_MONTHS})\s*"
    rf"[0-9۰-۹٠-٩]{{0,2}}\s*[1۱١][89۸۹٨٩][0-9۰-۹٠-٩]{{2}}\s*[\[(]\s*"
    rf"[0-9۰-۹٠-٩\s]{{0,4}}(?:{FA_JAL_MONTHS}))")


def _fa_split_midline(lines: list[str]) -> list[str]:
    """A new chronology entry sometimes begins mid-line in the scan; split those."""
    out: list[str] = []
    for ln in lines:
        if FA_PERIOD_RE.match(FA_BULLET_RE.sub("", ln)):
            out.append(ln)          # period headers carry two dates; never split
            continue
        parts = _FA_MIDLINE_RE.split(ln)
        out.extend(parts if len(parts) > 1 else [ln])
    return out


def parse_fa_chronology() -> list[dict]:
    lines = _fa_split_midline(read_lines(FA_PATH)[FA_RANGE[0] - 1:FA_RANGE[1]])
    entries: list[dict] = []
    current: dict | None = None
    period = None
    for raw in lines:
        if not raw.strip():
            continue
        if FA_PAGE_RE.match(raw) or raw.strip() in ("تقویم رویدادها", "تفویم رویدادها",
                                                    "کتاب شناسی"):
            continue
        stripped = FA_BULLET_RE.sub("", raw)
        if FA_PERIOD_RE.match(stripped):
            period = normalize_fa(stripped)
            continue
        ym = FA_YEAR_RE.search(stripped)
        is_start = bool(ym and ym.start() <= 32 and _fa_head_is_date(stripped[:ym.start()]))
        if is_start:
            if current:
                entries.append(current)
            head, rest = stripped[:ym.end()], stripped[ym.end():]
            current = {"date_raw_fa": normalize_fa(head),
                       "rest_fa": normalize_fa(rest),
                       "period_fa": period,
                       "_head": head}
        elif current is not None:
            current["rest_fa"] = normalize_fa(current["rest_fa"] + " " + raw)
    if current:
        entries.append(current)

    for e in entries:
        full = e["date_raw_fa"] + " " + e["rest_fa"]
        dates = parse_fa_bracket_dates(full)
        text = e["rest_fa"]
        m = re.match(r"^\s*[\[(]?\s*(\[[^\]]*\]\s*)+", text)
        if m:
            text = text[m.end():]
        else:
            # bracket may be unbalanced from OCR: drop up to the first ']'
            b = text.find("]")
            if 0 <= b <= 40:
                text = text[b + 1:]
        e["text_fa"] = normalize_fa(text)
        d = parse_fa_date_head(e.pop("_head"))
        d["jalali"] = dates.get("jalali")
        d["hijri"] = dates.get("hijri")
        e["date_fa"] = d
    return entries


# ---------------------------------------------------------------- Alignment

def _score(e: dict, f: dict) -> float:
    """Compatibility of an English and a Persian chronology entry."""
    de, df = e["date_en"], f["date_fa"]
    ye, yf = de.get("g_year"), df.get("g_year")
    if ye is None or yf is None or ye != yf:
        return -1.0
    s = 2.0
    me, mf = de.get("g_month"), df.get("g_month")
    if me and mf:
        s += 2.0 if me == mf else -3.0
    dd, dfd = de.get("g_day"), df.get("g_day")
    if dd and dfd:
        s += 1.0 if dd == dfd else -0.25   # Persian day digits are often mangled
    return s


def align(en: list[dict], fa: list[dict]) -> list[dict]:
    """Global sequence alignment (Needleman-Wunsch). Both chronologies list the
    same events in the same order, so a monotone alignment is exactly right."""
    GAP = -1.0
    n, m = len(en), len(fa)
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    bt = [[0] * (m + 1) for _ in range(n + 1)]   # 0=diag 1=up(en gap) 2=left(fa gap)
    for i in range(1, n + 1):
        dp[i][0] = dp[i - 1][0] + GAP
        bt[i][0] = 1
    for j in range(1, m + 1):
        dp[0][j] = dp[0][j - 1] + GAP
        bt[0][j] = 2
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            diag = dp[i - 1][j - 1] + _score(en[i - 1], fa[j - 1])
            up = dp[i - 1][j] + GAP
            left = dp[i][j - 1] + GAP
            best = max(diag, up, left)
            dp[i][j] = best
            bt[i][j] = 0 if best == diag else (1 if best == up else 2)
    out: list[dict] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and bt[i][j] == 0:
            out.append(_merge(en[i - 1], fa[j - 1])); i -= 1; j -= 1
        elif i > 0 and (j == 0 or bt[i][j] == 1):
            out.append(_merge(en[i - 1], None)); i -= 1
        else:
            out.append(_merge(None, fa[j - 1])); j -= 1
    out.reverse()
    return out


def _matches(e: dict | None, f: dict | None) -> bool:
    """Year + month must agree. The day is NOT compared: the Persian scan
    frequently mangles the day digit (bullet glyphs collide with it), so the
    English date is treated as authoritative and mismatches are flagged."""
    if not e or not f:
        return False
    de, df = e["date_en"], f["date_fa"]
    if de.get("g_year") != df.get("g_year"):
        return False
    if de.get("g_month") and df.get("g_month") and de["g_month"] != df["g_month"]:
        return False
    return True


def _merge(e: dict | None, f: dict | None) -> dict:
    rec: dict = {
        "text_en": e["text_en"] if e else None,
        "text_fa": f["text_fa"] if f else None,
        "date_raw_en": e["date_raw_en"] if e else None,
        "date_raw_fa": f["date_raw_fa"] if f else None,
        "period_en": e.get("period_en") if e else None,
        "period_fa": f.get("period_fa") if f else None,
        "gregorian": {}, "jalali": None, "hijri": None,
        "aligned": bool(e and f),
    }
    de = e["date_en"] if e else {}
    df = f["date_fa"] if f else {}
    g = {k: de.get(k) for k in ("g_year", "g_month", "g_day", "g_year_end",
                                "g_month_end", "g_day_end", "precision", "season", "season_end")}
    for k in ("g_year", "g_month", "g_day", "g_month_end", "g_day_end"):
        if g.get(k) is None and df.get(k) is not None:
            g[k] = df[k]
    rec["gregorian"] = {k: v for k, v in g.items() if v is not None}
    rec["jalali"] = df.get("jalali")
    rec["hijri"] = df.get("hijri")
    return rec


def main() -> None:
    en = parse_en_chronology()
    fa = parse_fa_chronology()
    merged = align(en, fa)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, ensure_ascii=False, indent=1)
    both = sum(1 for m in merged if m["aligned"])
    print(f"English entries : {len(en)}")
    print(f"Persian entries : {len(fa)}")
    print(f"Merged records  : {len(merged)}  (aligned both languages: {both})")
    print(f"with jalali date: {sum(1 for m in merged if m['jalali'])}")
    print(f"with hijri  date: {sum(1 for m in merged if m['hijri'])}")
    print(f"-> {OUT_PATH}")


if __name__ == "__main__":
    main()
