"""Dump a range of printed pages from the English scan, cleaned for reading.

    python3 scripts/pages.py 17 33
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_page_map import load, read_lines

RUNNING_HEAD = re.compile(r"^\s*(?:\d{1,3}\s+[A-Z].{0,60}|.{0,60}[a-z]\s\s+\d{1,3})\s*$")

def dump(a, b):
    pmap, lines = load(), read_lines()
    out = []
    for p in range(a, b + 1):
        if p not in pmap:
            continue
        s, e = pmap[p]
        out.append(f"\n<<<PAGE {p}>>>")
        for ln in lines[s - 1:e - 1]:
            ln = ln.replace("\x0c", "").rstrip()
            if not ln.strip():
                continue
            if RUNNING_HEAD.match(ln) and len(ln.strip()) < 64:
                continue
            out.append(ln.strip())
    return "\n".join(out)

if __name__ == "__main__":
    print(dump(int(sys.argv[1]), int(sys.argv[2])))
