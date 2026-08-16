"""Verify Persian spellings against the Persian book.

Used during extraction: before writing a `name_fa`, check that the form actually
occurs in the translation (and how often), and see the variants around it. This
keeps Persian names sourced from the book rather than guessed.

Usage
    python3 scripts/fa_lookup.py ستارخان انجمن‌تبریز        # count occurrences
    python3 scripts/fa_lookup.py -c ستارخان                 # with context lines
    python3 scripts/fa_lookup.py -p "ستار"                  # prefix/substring scan
"""

from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FA_PATH = os.path.join(ROOT, "data/raw/book.txt")

# Characters that vary between Persian and Arabic keyboards / OCR output.
_FOLD = {
    "ك": "ک", "ي": "ی", "ﻯ": "ی", "ی": "ی", "ئ": "ی", "ﻲ": "ی",
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ﺍ": "ا",
    "ة": "ه", "ۀ": "ه", "ه‌": "ه",
    "ؤ": "و", "‌": "", "‏": "", "‎": "",
    "ّ": "", "َ": "", "ِ": "", "ُ": "", "ً": "", "ٍ": "", "ٌ": "", "ْ": "", "ٓ": "",
}


def fold(s: str) -> str:
    """Normalise away orthographic and diacritic variation for matching."""
    for a, b in _FOLD.items():
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


_TEXT: str | None = None
_FOLDED: str | None = None
_LINES: list[str] | None = None


def text() -> str:
    global _TEXT
    if _TEXT is None:
        _TEXT = open(FA_PATH, encoding="utf-8", errors="replace").read()
    return _TEXT


def folded() -> str:
    global _FOLDED
    if _FOLDED is None:
        _FOLDED = fold(text())
    return _FOLDED


def lines() -> list[str]:
    global _LINES
    if _LINES is None:
        _LINES = text().split("\n")
    return _LINES


def count(name: str) -> int:
    """How many times a Persian form occurs, ignoring spacing/diacritic variation."""
    return folded().count(fold(name))


def occurrences(name: str, limit: int = 5) -> list[str]:
    needle = fold(name)
    hits = []
    for ln in lines():
        if needle in fold(ln):
            hits.append(re.sub(r"\s+", " ", ln).strip())
            if len(hits) >= limit:
                break
    return hits


def scan(substr: str, limit: int = 40) -> list[tuple[str, int]]:
    """Distinct word-sequences in the book containing `substr`."""
    needle = fold(substr)
    seen: dict[str, int] = {}
    for ln in lines():
        f = fold(ln)
        if needle not in f:
            continue
        for m in re.finditer(re.escape(needle), f):
            a = f.rfind(" ", 0, max(0, m.start() - 18)) + 1
            b = f.find(" ", m.end() + 18)
            frag = f[a:b if b > 0 else len(f)].strip()
            seen[frag] = seen.get(frag, 0) + 1
    return sorted(seen.items(), key=lambda kv: -kv[1])[:limit]


def check(names: list[str]) -> None:
    for n in names:
        c = count(n)
        flag = "ok " if c else "MISSING"
        print(f"{flag} {c:>4}  {n}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        raise SystemExit(0)
    if args[0] == "-c":
        for n in args[1:]:
            print(f"\n=== {n}  ({count(n)} hits)")
            for h in occurrences(n):
                print("   ", h[:150])
    elif args[0] == "-p":
        for n in args[1:]:
            print(f"\n=== scan {n}")
            for frag, c in scan(n):
                print(f"  {c:>3}  {frag[:110]}")
    else:
        check(args)
