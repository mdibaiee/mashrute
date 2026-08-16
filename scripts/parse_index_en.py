"""Parse the English back-of-book index into a structured entity gazetteer.

The index is unusually rich for our purpose: it carries birth/death years, office
descriptors with their dates, group membership (as sub-entries under a group
headword), and cross-references. We keep all of it, plus every page reference,
so later passes can jump straight to the relevant pages of the body text.

Output: data/derived/index_en.json
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decolumn import decolumn  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EN_PATH = os.path.join(ROOT, "data/raw/book_en.txt")
OUT = os.path.join(ROOT, "data/derived/index_en.json")

INDEX_RANGE = (18191, 19671)
LAST_BODY_PAGE = 342          # notes start at 343

DROP = re.compile(r"^\s*(?:\d{3}\s+Index|Index\s+\d{3}|Index)\s*$")


def clean(s: str) -> str:
    s = s.replace("‘", "'").replace("’", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = re.sub(r"\s+", " ", s).strip()
    return s


# Prefixes that keep their hyphen when a word is broken across lines.
_KEEP_HYPHEN_PREFIX = re.compile(
    r"(?:^|[\s(])(?:al|Al|Anglo|Russo|Franco|Austro|Turko|Indo|pro|anti|non|self|ex|"
    r"vice|co|re|semi|neo|pan|Pan|mid|Sayyid|Abu|Abd|'Abd|Amin|Nasir|Mustawfi)-$")


def _keep_hyphen(prev: str, nxt: str) -> bool:
    """A line-break hyphen is real if it joins proper nouns or a known prefix."""
    if _KEEP_HYPHEN_PREFIX.search(prev):
        return True
    return bool(nxt[:1].isupper() or nxt[:1].isdigit())


def dehyphenate(rows: list[tuple[str, int]]) -> list[str]:
    """Join wrapped continuation lines back into whole entries."""
    entries: list[str] = []
    for text, indent in rows:
        text = clean(text)
        if not text or DROP.match(text):
            continue
        if indent <= 1 or not entries:
            entries.append(text)
        else:
            prev = entries[-1]
            if prev.endswith("-"):
                entries[-1] = prev + text if _keep_hyphen(prev, text) else prev[:-1] + text
            else:
                entries[-1] = prev + " " + text
    return entries


# --------------------------------------------------------------- page refs

_NOTE_RE = re.compile(r"^(\d{3})[n7]?(\d{1,3})$")


def parse_refs(chunk: str) -> tuple[list, list, str]:
    """Pull page and note references off the end of a fragment.

    Returns (pages, notes, residual_text). `pages` entries are ints or
    [start, end] pairs; `notes` are {'page': int, 'note': int}.
    """
    pages: list = []
    notes: list = []
    # references are trailing comma-separated numeric tokens
    toks = [t.strip() for t in chunk.split(",")]
    keep: list[str] = []
    for tok in toks:
        t = tok.strip().rstrip(".")
        if not t:
            continue
        m = re.fullmatch(r"(\d{1,3})\s*[-–]\s*(\d{1,3})", t)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if b < a:                       # "165-66" means 165-166
                b = int(str(a)[:len(str(a)) - len(m.group(2))] + m.group(2))
            pages.append([a, b] if b >= a else a)
            continue
        if re.fullmatch(r"\d{1,3}", t):
            pages.append(int(t))
            continue
        # note references: "365-66n22", "349119"(=349n19), "387753"(=387n53)
        m = re.fullmatch(r"(\d{3})\s*[-–]\s*(\d{1,2})\s*[n71](\d{1,3})", t)
        if m:
            notes.append({"page": int(m.group(1)), "note": int(m.group(3)), "raw": t})
            continue
        m = re.fullmatch(r"(\d{3})\s*[n7](\d{1,3})", t)
        if m:
            notes.append({"page": int(m.group(1)), "note": int(m.group(2)), "raw": t})
            continue
        m = _NOTE_RE.fullmatch(t)
        if m and int(m.group(1)) > LAST_BODY_PAGE:
            # The scan renders the 'n' of "349n19" as 1, 7 or nothing, so the
            # note number is ambiguous; keep the raw token alongside the guess.
            note = m.group(2)
            guess = int(note[1:]) if len(note) == 3 and note[0] in "17" else int(note)
            notes.append({"page": int(m.group(1)), "note": guess,
                          "raw": t, "uncertain": True})
            continue
        keep.append(tok)
    return pages, notes, ", ".join(k for k in keep if k.strip())


def split_top(s: str, sep: str) -> list[str]:
    """Split on `sep` but not inside parentheses."""
    out, depth, buf = [], 0, ""
    for ch in s:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        if ch == sep and depth == 0:
            out.append(buf)
            buf = ""
        else:
            buf += ch
    out.append(buf)
    return [x.strip() for x in out if x.strip()]


# ------------------------------------------------------------- entry parse

SEE_ALSO_RE = re.compile(r"\bsee\s+also\s+", re.I)
SEE_RE = re.compile(r"^\s*see\s+", re.I)
YEARS_RE = re.compile(r"\b(1[6-9]\d{2})\s*[-–]\s*(1[6-9]\d{2}|\d{2})\b")
FLOR_RE = re.compile(r"\b(?:d\.|died)\s*(1[6-9]\d{2})\b", re.I)


def parse_parentheticals(head: str) -> tuple[str, list[str]]:
    """Strip parenthetical qualifiers off a headword, keeping them."""
    parens: list[str] = []
    out, depth, buf = "", 0, ""
    for ch in head:
        if ch == "(":
            depth += 1
            if depth == 1:
                buf = ""
                continue
        elif ch == ")":
            depth -= 1
            if depth == 0:
                parens.append(buf.strip())
                continue
        if depth:
            buf += ch
        else:
            out += ch
    if depth and buf.strip():          # unclosed paren from the scan
        parens.append(buf.strip())
    return re.sub(r"\s+", " ", out).strip(" ,"), parens


def parse_entry(raw: str) -> dict | None:
    text = clean(raw)
    if not text or len(text) < 3:
        return None

    rec: dict = {"raw": text, "see": [], "see_also": [], "subentries": [],
                 "pages": [], "notes": [], "parentheticals": [],
                 "birth_year": None, "death_year": None}

    # A trailing "see also ..." applies to the whole entry. Targets are
    # separated by semicolons -- commas occur inside names ("Dawlatabadi, Yahya").
    m = SEE_ALSO_RE.search(text)
    if m and ":" not in text[:m.start()]:
        tail = text[m.end():]
        rec["see_also"] += [t.strip(" ,;.") for t in tail.split(";") if t.strip(" ,;.")]
        text = text[:m.start()].strip(" ,;")

    # Split headword from the body at the first top-level colon.
    if ":" in text:
        head, body = text.split(":", 1)
        # a colon inside a parenthetical is not the separator
        if head.count("(") != head.count(")"):
            i = text.find(":", text.find(")"))
            head, body = (text[:i], text[i + 1:]) if i > 0 else (text, "")
    else:
        head, body = text, ""

    head, parens = parse_parentheticals(head)
    rec["parentheticals"] = parens

    # dates inside the parentheticals: "(1817-1892)", "(Abbas 'Ali Nuri, 1844-1921)"
    for p in parens:
        ym = YEARS_RE.search(p)
        if ym:
            b, d = ym.group(1), ym.group(2)
            if len(d) == 2:
                d = b[:2] + d
            rec["birth_year"], rec["death_year"] = int(b), int(d)
            break
    if rec["birth_year"] is None:
        ym = YEARS_RE.search(head)
        if ym and "-" in ym.group(0):
            b, d = ym.group(1), ym.group(2)
            if len(d) == 2:
                d = b[:2] + d
            rec["birth_year"], rec["death_year"] = int(b), int(d)
            head = head[:ym.start()].strip(" ,(") + head[ym.end():].strip(" ,)")

    # pages attached directly to the headword
    pages, notes, residual = parse_refs(head)
    rec["pages"] += pages
    rec["notes"] += notes
    head = residual

    # "Advisers, see Foreign advisers"
    parts_head = [p.strip() for p in head.split(",")]
    if len(parts_head) > 1 and SEE_RE.match(parts_head[-1]):
        rec["see"].append(SEE_RE.sub("", parts_head[-1]).strip())
        head = ", ".join(parts_head[:-1])

    rec["headword"] = head.strip(" ,;")

    # ---- body: sub-entries separated by ';'
    if body:
        in_see_also = False
        for part in split_top(body, ";"):
            if SEE_ALSO_RE.match(part):
                rec["see_also"].append(SEE_ALSO_RE.sub("", part).strip(" ,;."))
                in_see_also = True          # "see also" is always last in an index
                continue
            if in_see_also and not re.search(r"\d", part):
                rec["see_also"].append(part.strip(" ,;."))
                continue
            if SEE_RE.match(part):
                rec["see"].append(SEE_RE.sub("", part).strip())
                continue
            p_pages, p_notes, label = parse_refs(part)
            sub_label, sub_parens = parse_parentheticals(label)
            m2 = SEE_ALSO_RE.search(sub_label)
            sub_see_also = []
            if m2:
                sub_see_also = [sub_label[m2.end():].strip(" ,;.")]
                sub_label = sub_label[:m2.start()].strip(" ,;")
            if sub_label or p_pages or p_notes:
                rec["subentries"].append({
                    "label": sub_label.strip(" ,;"),
                    "parentheticals": sub_parens,
                    "pages": p_pages, "notes": p_notes,
                    "see_also": sub_see_also,
                })
    if not rec["headword"]:
        return None
    return rec


def main() -> None:
    lines = open(EN_PATH, encoding="utf-8", errors="replace").read().split("\n")
    rows = decolumn(lines[INDEX_RANGE[0] - 1:INDEX_RANGE[1]], drop=DROP)
    entries = [e for e in (parse_entry(t) for t in dehyphenate(rows)) if e]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(entries, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    n_sub = sum(len(e["subentries"]) for e in entries)
    n_pg = sum(len(e["pages"]) + sum(len(s["pages"]) for s in e["subentries"])
               for e in entries)
    print(f"entries        : {len(entries)}")
    print(f"sub-entries    : {n_sub}")
    print(f"page refs      : {n_pg}")
    print(f"with life dates: {sum(1 for e in entries if e['birth_year'])}")
    print(f"with see-also  : {sum(1 for e in entries if e['see_also'])}")
    print(f"cross-refs only: {sum(1 for e in entries if e['see'] and not e['pages'])}")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
