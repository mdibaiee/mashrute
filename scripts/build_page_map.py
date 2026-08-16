"""Map printed page numbers to line ranges in the English scan.

The index references printed page numbers, so to pull the passage behind any
index reference we need page -> lines. Pages are delimited by form feeds; the
running head carries the number ("2 Introduction" on versos, "Introduction 3" on
rectos). We read the numbers we can, then check they advance in step with the
physical page sequence and fill the gaps from that offset.

Output: data/derived/page_map_en.json  {page: [start_line, end_line]}  (1-based,
end exclusive) plus helpers used by other scripts.
"""

from __future__ import annotations

import json
import os
import re
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EN_PATH = os.path.join(ROOT, "data/raw/book_en.txt")
OUT = os.path.join(ROOT, "data/derived/page_map_en.json")

VERSO = re.compile(r"^\s*(\d{1,3})\s+[A-Z‘'\"]")          # "2 Introduction"
RECTO = re.compile(r"[A-Za-z’'\"]\s\s*(\d{1,3})\s*$")      # "Introduction   3"


def read_lines(path: str = EN_PATH) -> list[str]:
    return open(path, encoding="utf-8", errors="replace").read().split("\n")


def page_starts(lines: list[str]) -> list[int]:
    return [i for i, l in enumerate(lines) if "\x0c" in l]


def read_running_head(lines: list[str], start: int) -> int | None:
    """Read the printed page number from the running head of a page."""
    for j in range(start, min(start + 3, len(lines))):
        s = lines[j].replace("\x0c", " ")
        if not s.strip():
            continue
        m = VERSO.match(s) or RECTO.search(s)
        if m:
            n = int(m.group(1))
            if 1 <= n <= 460:
                return n
        break
    return None


def _longest_increasing(anchors: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Keep the largest subset whose printed numbers rise with physical order.

    A misread running head ("6" for 146) breaks monotonicity; the true anchors
    form the longest strictly increasing run, so the misreads drop out.
    """
    if not anchors:
        return []
    n = len(anchors)
    best = [1] * n
    prev = [-1] * n
    for i in range(n):
        for j in range(i):
            if anchors[j][1] < anchors[i][1] and best[j] + 1 > best[i]:
                # the offset must also stay plausible
                if abs((anchors[i][1] - anchors[i][0]) - (anchors[j][1] - anchors[j][0])) <= 8:
                    best[i], prev[i] = best[j] + 1, j
    i = max(range(n), key=lambda x: best[x])
    out = []
    while i >= 0:
        out.append(anchors[i])
        i = prev[i]
    return out[::-1]


def build() -> dict[int, list[int]]:
    lines = read_lines()
    starts = page_starts(lines)
    ends = starts[1:] + [len(lines)]

    raw_anchors: list[tuple[int, int]] = []
    for k, s in enumerate(starts):
        n = read_running_head(lines, s)
        if n is not None:
            raw_anchors.append((k, n))
    anchors = _longest_increasing(raw_anchors)
    print(f"running heads read on {len(raw_anchors)}/{len(starts)} pages; "
          f"{len(anchors)} kept as anchors after monotonicity filter")

    # printed number for every physical page, interpolating between anchors
    printed: dict[int, int] = dict(anchors)
    fuzzy = 0
    for (k1, n1), (k2, n2) in zip(anchors, anchors[1:]):
        gap_k, gap_n = k2 - k1, n2 - n1
        for k in range(k1 + 1, k2):
            if gap_k == gap_n:                      # pages line up one-for-one
                printed[k] = n1 + (k - k1)
            else:                                   # unnumbered plates in between
                printed[k] = n1 + round((k - k1) * gap_n / gap_k)
                fuzzy += 1
    off_lo = anchors[0][1] - anchors[0][0]
    off_hi = anchors[-1][1] - anchors[-1][0]
    for k in range(0, anchors[0][0]):
        printed[k] = k + off_lo
    for k in range(anchors[-1][0] + 1, len(starts)):
        printed[k] = k + off_hi

    page_map: dict[int, list[int]] = {}
    for k, (s, e) in enumerate(zip(starts, ends)):
        page_map.setdefault(printed[k], [s + 1, e + 1])
    print(f"pages mapped: {len(page_map)} ({fuzzy} interpolated across "
          f"unnumbered pages)")
    return page_map


def load() -> dict[int, tuple[int, int]]:
    raw = json.load(open(OUT, encoding="utf-8"))
    return {int(k): tuple(v) for k, v in raw.items()}


def page_text(page: int, pmap=None, lines=None, span: int = 0) -> str:
    """Text of a printed page (optionally with `span` pages of context)."""
    pmap = pmap or load()
    lines = lines if lines is not None else read_lines()
    out: list[str] = []
    for p in range(page - span, page + span + 1):
        if p in pmap:
            a, b = pmap[p]
            out.append("\n".join(lines[a - 1:b - 1]).replace("\x0c", ""))
    return "\n".join(out)


if __name__ == "__main__":
    pm = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({str(k): v for k, v in sorted(pm.items())},
              open(OUT, "w", encoding="utf-8"), indent=0)
    print(f"-> {OUT}")
    if len(sys.argv) > 1:
        print("\n" + "=" * 70)
        print(page_text(int(sys.argv[1]), pm)[:2000])
