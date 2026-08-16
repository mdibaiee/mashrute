"""Harvest Persian headword candidates from the Persian index (نمایه).

Unlike the English scan, the Persian one lost the column gutter: both columns
were merged with single spaces and the page-number runs of one column land in
the middle of the other's headwords. A faithful parse is not recoverable.

What IS recoverable is the vocabulary: every Persian headword appears somewhere
in these lines, delimited by runs of Persian digits. We extract those fragments
as *candidates* and give callers a lookup so Persian spellings can be confirmed
against the index and the body text rather than guessed.

Output: data/derived/index_fa_candidates.json
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calendars import fa_digits_to_en  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FA_PATH = os.path.join(ROOT, "data/raw/book.txt")
OUT = os.path.join(ROOT, "data/derived/index_fa_candidates.json")

FA_RANGE = (17175, 18045)

PERSIAN = r"ء-غف-يٱ-ۓ‌"
DIGITS = r"0-9۰-۹٠-٩"
# a fragment of Persian text with no digits in it
FRAG_RE = re.compile(rf"[{PERSIAN}][{PERSIAN}\s.,؛:()»«>\-]*")
NOISE_RE = re.compile(rf"^[\s.,؛:()»«>\-|/{DIGITS}]*$")

# lines that are page furniture rather than index content
DROP_RE = re.compile(rf"^\s*[{DIGITS}]*\s*[|/]\s*(نمایه|نمابه|نمائیه)\s*$|^\s*نمایه\s*$")


def normalize(s: str) -> str:
    s = re.sub(r"[«»\"]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip(" .,؛:-()>")


def harvest() -> dict:
    lines = open(FA_PATH, encoding="utf-8", errors="replace").read().split("\n")
    body = lines[FA_RANGE[0] - 1:FA_RANGE[1]]

    candidates: list[str] = []
    for raw in body:
        if not raw.strip() or DROP_RE.match(raw) or "\x0c" in raw:
            continue
        # Latin-script residue is bibliographic noise from the facing pages
        if len(re.findall(r"[A-Za-z]", raw)) > 6:
            continue
        for frag in FRAG_RE.findall(raw):
            t = normalize(frag)
            if not t or NOISE_RE.match(t):
                continue
            if len(re.findall(rf"[{PERSIAN}]", t)) < 3:
                continue
            candidates.append(t)

    # A headword may be split by an intervening page-number run; keep both the
    # fragments and their concatenations as lookup keys.
    uniq: dict[str, int] = {}
    for c in candidates:
        uniq[c] = uniq.get(c, 0) + 1

    # index by first word so callers can look up a surname quickly
    by_first: dict[str, list[str]] = {}
    for c in uniq:
        head = c.split(" ")[0].strip("،,؛")
        by_first.setdefault(head, []).append(c)

    return {"candidates": sorted(uniq), "counts": uniq, "by_first_word": by_first}


def main() -> None:
    data = harvest()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Persian fragments harvested : {len(data['candidates'])}")
    print(f"distinct first words        : {len(data['by_first_word'])}")
    print(f"-> {OUT}")
    print("\nsample:")
    for c in data["candidates"][:25]:
        print("   ", c)


if __name__ == "__main__":
    main()
