"""De-column the two-column back-of-book indexes.

The scans preserve column geometry, so each physical line holds a slice of the
left column and a slice of the right column separated by a wide run of spaces.
We split every line at that gutter, then emit the left column of a page followed
by the right column, restoring reading order.

Indentation is preserved relative to each column's own left margin, so callers
can still tell a headword (flush left) from a wrapped continuation (indented).
"""

from __future__ import annotations

import re


def split_pages(lines: list[str]) -> list[list[str]]:
    """Split on form feeds, which mark page starts in both scans."""
    pages: list[list[str]] = [[]]
    for ln in lines:
        if "\x0c" in ln:
            pages.append([])
            ln = ln.replace("\x0c", " ")
        pages[-1].append(ln)
    return [p for p in pages if any(x.strip() for x in p)]


def _gutter(line: str, hint: int, min_start: int = 18) -> tuple[int, int] | None:
    """Find the whitespace run that separates the columns.

    Prefers the run spanning `hint` (the page's estimated gutter column); falls
    back to the widest run that starts far enough right to not be word spacing.
    """
    all_runs = [(m.start(), m.end()) for m in re.finditer(r"  +", line)]
    # A run straddling the page's gutter column is the separator, however short
    # the left-hand entry happens to be.
    spanning = [r for r in all_runs if r[0] <= hint <= r[1]]
    if spanning:
        return max(spanning, key=lambda r: r[1] - r[0])
    runs = [r for r in all_runs if r[0] >= min_start and r[1] - r[0] >= 3]
    if not runs:
        return None
    return max(runs, key=lambda r: r[1] - r[0])


def _estimate_gutter(page: list[str]) -> int:
    """Estimate the gutter column for a page from its widest whitespace runs."""
    cands: list[int] = []
    for ln in page:
        if len(ln.strip()) < 20:
            continue
        runs = [(m.start(), m.end()) for m in re.finditer(r"  +", ln)
                if m.start() >= 18]
        if runs:
            s, e = max(runs, key=lambda r: r[1] - r[0])
            if e - s >= 3:
                cands.append((s + e) // 2)
    if not cands:
        return 48
    cands.sort()
    return cands[len(cands) // 2]


def decolumn_page(page: list[str], drop: re.Pattern | None = None,
                  rtl: bool = False) -> list[tuple[str, int]]:
    """Return [(text, indent)] for one page, left column then right column.

    `indent` is measured from each column's own margin. For `rtl` (the Persian
    index) the right-hand column is read first.
    """
    hint = _estimate_gutter(page)
    left: list[tuple[str, int]] = []
    right: list[tuple[str, int]] = []
    for ln in page:
        if not ln.strip():
            continue
        if drop and drop.search(ln):
            continue
        g = _gutter(ln, hint)
        if g:
            l_txt, r_txt, r_start = ln[:g[0]], ln[g[1]:], g[1]
        else:
            # No gutter: the line belongs to whichever column it starts in.
            if len(ln) - len(ln.lstrip()) >= hint:
                l_txt, r_txt, r_start = "", ln.strip(), len(ln) - len(ln.lstrip())
            else:
                l_txt, r_txt, r_start = ln, "", 0
        if l_txt.strip():
            left.append((l_txt.rstrip(), len(l_txt) - len(l_txt.lstrip())))
        if r_txt.strip():
            right.append((r_txt.rstrip(), r_start))

    def normalize(col: list[tuple[str, int]]) -> list[tuple[str, int]]:
        if not col:
            return []
        base = min(i for _, i in col)
        return [(t.strip(), i - base) for t, i in col]

    a, b = normalize(left), normalize(right)
    return (b + a) if rtl else (a + b)


def decolumn(lines: list[str], drop: re.Pattern | None = None,
             rtl: bool = False) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for page in split_pages(lines):
        out.extend(decolumn_page(page, drop=drop, rtl=rtl))
    return out


if __name__ == "__main__":
    import sys
    src = open("data/raw/book_en.txt", encoding="utf-8", errors="replace").read().split("\n")
    drop = re.compile(r"^\s*(?:\d{3}\s+Index|Index\s+\d{3})\s*$")
    rows = decolumn(src[18190:19671], drop=drop)
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    for t, i in rows[:n]:
        print(f"{i:>2}| {t}")
    print(f"\n... {len(rows)} rows total")
