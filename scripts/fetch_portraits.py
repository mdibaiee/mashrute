#!/usr/bin/env python3
"""Find a portrait for each historical actor on Wikipedia / Wikimedia Commons.

The hard part is not fetching but *not* attaching the wrong face to a real
person. A name like "Baqir Khan" or "Amin al-Sultan" matches plenty of modern
articles, so every candidate has to survive validation against Wikidata before
we keep it:

  * the entity must be a human (P31 = Q5);
  * if we know the person's birth/death year from the book, Wikidata must agree
    within a few years;
  * if we know neither, the entity's own dates must fall inside the period the
    book covers, so a living namesake cannot slip through.

Anything that fails is left without a portrait and falls back to the monogram.
Output is data/portraits.jsonl, one record per matched person, carrying the
licence metadata Commons returns so the site can attribute properly.
"""

from __future__ import annotations

import json
import pathlib
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PEOPLE = ROOT / "web" / "src" / "data" / "people.json"
OUT = ROOT / "data" / "portraits.jsonl"
OVERRIDES = ROOT / "data" / "portrait_overrides.json"
IMG_DIR = ROOT / "web" / "public" / "portraits"

UA = "mashruteh-dataset/1.0 (https://github.com/mdibaiee/mashrute) python-urllib"
THUMB_PX = 480

# The book runs from the Qajar period to the aftermath of the revolution. A
# person in it cannot plausibly have been born after 1900 or died after 1980.
BIRTH_RANGE = (1750, 1900)
DEATH_RANGE = (1800, 1985)
YEAR_TOLERANCE = 4


def api(host: str, params: dict) -> dict:
    params = {**params, "format": "json", "formatversion": "2"}
    url = f"https://{host}/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as exc:  # noqa: BLE001 - network flakiness only
            if attempt == 3:
                print(f"  ! {host} {exc}", file=sys.stderr)
                return {}
            time.sleep(1.5 * (attempt + 1))
    return {}


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


# --------------------------------------------------------------------------
# candidate lookup


def titles_for(p: dict) -> list[tuple[str, str]]:
    """(host, title) candidates, most trustworthy first."""
    out = []
    for key, host in (("full_name_en", "en.wikipedia.org"), ("name_en", "en.wikipedia.org"),
                      ("full_name_fa", "fa.wikipedia.org"), ("name_fa", "fa.wikipedia.org")):
        v = (p.get(key) or "").strip()
        if v and (host, v) not in out:
            out.append((host, v))
    return out


def batch_pages(host: str, titles: list[str]) -> dict:
    """Exact-title lookup, following redirects. Returns title -> page dict."""
    found = {}
    for group in chunks(titles, 40):
        d = api(host, {
            "action": "query",
            "titles": "|".join(group),
            "prop": "pageimages|pageprops",
            "pithumbsize": THUMB_PX,
            "redirects": "1",
        })
        q = d.get("query") or {}
        # Map any redirect/normalisation back to what we asked for.
        alias = {}
        for r in q.get("normalized", []) + q.get("redirects", []):
            alias[r["to"]] = alias.get(r["from"], r["from"])
        for page in q.get("pages", []):
            if page.get("missing"):
                continue
            asked = alias.get(page["title"], page["title"])
            found[asked] = page
        time.sleep(0.12)
    return found


def search_page(host: str, term: str) -> dict | None:
    d = api(host, {
        "action": "query",
        "generator": "search",
        "gsrsearch": term,
        "gsrlimit": "3",
        "gsrnamespace": "0",
        "prop": "pageimages|pageprops",
        "pithumbsize": THUMB_PX,
    })
    pages = (d.get("query") or {}).get("pages") or []
    pages.sort(key=lambda p: p.get("index", 99))
    for page in pages:
        if page.get("pageprops", {}).get("wikibase_item"):
            return page
    return None


# --------------------------------------------------------------------------
# validation against Wikidata


def wikidata(ids: list[str]) -> dict:
    out = {}
    for group in chunks(sorted(set(ids)), 40):
        d = api("www.wikidata.org", {
            "action": "wbgetentities",
            "ids": "|".join(group),
            "props": "claims|descriptions",
            "languages": "en|fa",
        })
        out.update(d.get("entities") or {})
        time.sleep(0.12)
    return out


def _year(claim) -> int | None:
    try:
        t = claim["mainsnak"]["datavalue"]["value"]["time"]  # +1868-00-00T00:00:00Z
        sign, rest = t[0], t[1:]
        y = int(rest.split("-")[0])
        return -y if sign == "-" else y
    except Exception:  # noqa: BLE001
        return None


def validate(entity: dict, person: dict) -> tuple[bool, str]:
    claims = entity.get("claims") or {}

    instance = [c["mainsnak"].get("datavalue", {}).get("value", {}).get("id")
                for c in claims.get("P31", [])]
    if "Q5" not in instance:
        return False, "not a human"

    born = next((y for c in claims.get("P569", []) if (y := _year(c))), None)
    died = next((y for c in claims.get("P570", []) if (y := _year(c))), None)

    ours_b, ours_d = person.get("birth_g_year"), person.get("death_g_year")

    if ours_b and born and abs(ours_b - born) > YEAR_TOLERANCE:
        return False, f"birth {born} != ours {ours_b}"
    if ours_d and died and abs(ours_d - died) > YEAR_TOLERANCE:
        return False, f"death {died} != ours {ours_d}"

    # A confirmed year on either side is enough to trust the match.
    if (ours_b and born) or (ours_d and died):
        return True, "life dates agree"

    # Otherwise the entity has to sit inside the book's period on its own.
    if born and not (BIRTH_RANGE[0] <= born <= BIRTH_RANGE[1]):
        return False, f"born {born} outside period"
    if died and not (DEATH_RANGE[0] <= died <= DEATH_RANGE[1]):
        return False, f"died {died} outside period"
    if not born and not died:
        return False, "no dates to check against"
    return True, "period plausible"


# --------------------------------------------------------------------------
# confidence


def confidence(matched_by: str, why: str) -> str:
    """How much the match is worth.

    An exact title hit is strong evidence on its own; a full-text search hit is
    not, because these names are titles of office (Sardar As'ad, Amin al-Dawlah)
    that dozens of unrelated people also held. Search hits are only trusted when
    Wikidata's life dates corroborate the ones we took from the book.
    """
    dates_agree = why == "life dates agree"
    if matched_by == "title" and dates_agree:
        return "high"
    if matched_by == "title" or dates_agree:
        return "medium"
    return "low"


def apply_overrides(records: list[dict]) -> list[dict]:
    """Replace automatic picks with hand-chosen ones.

    Wikipedia's lead image is not always a picture of the subject — for the Bab
    it is a photograph of his shrine — so a curated URL wins outright.
    """
    if not OVERRIDES.exists():
        return records
    spec = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    by_id = {r["person_id"]: r for r in records}
    for pid, o in spec.items():
        if pid.startswith("_"):
            continue
        ext = pathlib.Path(urllib.parse.urlparse(o["url"]).path).suffix.lower() or ".jpg"
        dest = IMG_DIR / f"{pid}{ext}"
        if not download(o["url"], dest):
            print(f"  ! override for {pid} failed to download", file=sys.stderr)
            continue
        rec = by_id.get(pid, {"person_id": pid})
        rec.update({
            "file": f"/portraits/{dest.name}",
            "page_url": o.get("page_url"),
            "commons_file": o.get("commons_file"),
            "matched_by": "override",
            "validation": o.get("why", "hand-picked"),
            "confidence": "high",
        })
        by_id[pid] = rec
        print(f"  override {pid} <- {o['url'].rsplit('/', 1)[-1][:60]}")
    return list(by_id.values())


def winnow(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Drop low-confidence matches, then anything still ambiguous.

    Two of our people resolving to one Wikidata entity means at least one is
    wrong — e.g. a search for a wife returning her husband's article — so unless
    exactly one candidate in the group outranks the rest, none of them is kept.
    """
    kept = [r for r in records if r["confidence"] != "low"]
    dropped = [{**r, "dropped": "low confidence"} for r in records
               if r["confidence"] == "low"]

    by_q: dict[str, list[dict]] = {}
    for r in kept:
        by_q.setdefault(r["wikidata_id"], []).append(r)

    final = []
    rank = {"high": 2, "medium": 1}
    for group in by_q.values():
        if len(group) == 1:
            final.append(group[0])
            continue
        group.sort(key=lambda r: -rank[r["confidence"]])
        if rank[group[0]["confidence"]] > rank[group[1]["confidence"]]:
            final.append(group[0])
            dropped += [{**r, "dropped": "ambiguous entity"} for r in group[1:]]
        else:
            dropped += [{**r, "dropped": "ambiguous entity"} for r in group]
    return final, dropped


# --------------------------------------------------------------------------
# licence metadata + download


def image_meta(files: list[str], host: str = "commons.wikimedia.org") -> dict:
    """File name -> licence metadata.

    Ask the wiki the article came from rather than Commons directly: files
    hosted locally on fa.wikipedia are not on Commons, and for shared files the
    local query resolves through to the Commons record anyway.
    """
    out = {}
    for group in chunks(files, 20):
        d = api(host, {
            "action": "query",
            "titles": "|".join(f"File:{f}" for f in group),
            "prop": "imageinfo",
            "iiprop": "extmetadata|url",
            # No iiextmetadatafilter: restricting the key list makes the API
            # return an empty extmetadata block for files not hosted locally.
        })
        for page in (d.get("query") or {}).get("pages", []):
            info = (page.get("imageinfo") or [{}])[0]
            em = info.get("extmetadata") or {}
            get = lambda k: (em.get(k) or {}).get("value")  # noqa: E731
            # fa.wikipedia returns the localised namespace ("پرونده:"), so the
            # prefix has to be split off rather than sliced at a fixed width.
            name = page["title"].split(":", 1)[-1]
            out[name] = {
                "license": get("LicenseShortName") or get("UsageTerms"),
                "license_url": get("LicenseUrl"),
                "artist": _strip_html(get("Artist")),
                "credit": _strip_html(get("Credit")),
                "descriptionurl": info.get("descriptionurl"),
            }
        time.sleep(0.12)
    return out


def _strip_html(s):
    if not s:
        return None
    import re
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def download(url: str, dest: pathlib.Path) -> bool:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            data = r.read()
    except Exception as exc:  # noqa: BLE001
        print(f"  ! download {exc}", file=sys.stderr)
        return False
    if len(data) < 900:
        return False
    dest.write_bytes(data)
    return True


# --------------------------------------------------------------------------


def main() -> None:
    people = json.loads(PEOPLE.read_text(encoding="utf-8"))
    actors = [p for p in people if p.get("is_historical_actor")]
    print(f"{len(actors)} historical actors")

    # Pass 1 — exact titles, batched per wiki.
    candidates: dict[str, dict] = {}
    for host in ("en.wikipedia.org", "fa.wikipedia.org"):
        wanted = {}
        for p in actors:
            if p["id"] in candidates:
                continue
            for h, t in titles_for(p):
                if h == host:
                    wanted.setdefault(t, []).append(p["id"])
        if not wanted:
            continue
        print(f"pass 1 {host}: {len(wanted)} titles")
        pages = batch_pages(host, list(wanted))
        for title, page in pages.items():
            qid = (page.get("pageprops") or {}).get("wikibase_item")
            if not qid:
                continue
            for pid in wanted[title]:
                candidates.setdefault(pid, {
                    "host": host, "page": page, "qid": qid, "how": "title",
                })
        print(f"  matched {len(candidates)} so far")

    # Pass 2 — full-text search for whoever is still unmatched.
    missing = [p for p in actors if p["id"] not in candidates]
    print(f"pass 2 search: {len(missing)} remaining")
    for i, p in enumerate(missing, 1):
        for host, term in titles_for(p):
            page = search_page(host, term)
            time.sleep(0.15)
            if page:
                candidates[p["id"]] = {
                    "host": host, "page": page,
                    "qid": page["pageprops"]["wikibase_item"], "how": "search",
                }
                break
        if i % 40 == 0:
            print(f"  {i}/{len(missing)} searched, {len(candidates)} candidates")

    print(f"{len(candidates)} candidates before validation")

    # Validate every candidate against Wikidata.
    ents = wikidata([c["qid"] for c in candidates.values()])
    by_id = {p["id"]: p for p in actors}
    kept, rejected = {}, []
    for pid, cand in candidates.items():
        ent = ents.get(cand["qid"])
        if not ent:
            rejected.append((pid, "no wikidata entity"))
            continue
        ok, why = validate(ent, by_id[pid])
        if ok:
            kept[pid] = {**cand, "why": why}
        else:
            rejected.append((pid, why))
    print(f"{len(kept)} validated, {len(rejected)} rejected")

    # Only those with an actual image are worth keeping.
    with_img = {pid: c for pid, c in kept.items() if c["page"].get("thumbnail")}
    print(f"{len(with_img)} of those have a picture")

    # Group by source wiki so locally-hosted files are looked up where they live.
    meta = {}
    for host in {c["host"] for c in with_img.values()}:
        files = [c["page"]["pageimage"] for c in with_img.values()
                 if c["host"] == host and c["page"].get("pageimage")]
        for k, v in image_meta(files, host).items():
            if v.get("license") or k not in meta:
                meta[k] = v

    IMG_DIR.mkdir(parents=True, exist_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for pid, c in sorted(with_img.items()):
        page, thumb = c["page"], c["page"]["thumbnail"]
        fname = page.get("pageimage") or ""
        ext = pathlib.Path(urllib.parse.urlparse(thumb["source"]).path).suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            ext = ".jpg"
        dest = IMG_DIR / f"{pid}{ext}"
        if not dest.exists() and not download(thumb["source"], dest):
            continue
        time.sleep(0.1)
        m = meta.get(fname, {})
        records.append({
            "person_id": pid,
            "file": f"/portraits/{dest.name}",
            "width": thumb.get("width"),
            "height": thumb.get("height"),
            "source_wiki": c["host"],
            "page_title": page["title"],
            "page_url": f"https://{c['host']}/wiki/" + urllib.parse.quote(page["title"].replace(" ", "_")),
            "wikidata_id": c["qid"],
            "commons_file": fname,
            "commons_url": m.get("descriptionurl"),
            "license": m.get("license"),
            "license_url": m.get("license_url"),
            "artist": m.get("artist"),
            "credit": m.get("credit"),
            "matched_by": c["how"],
            "validation": c["why"],
            "confidence": confidence(c["how"], c["why"]),
        })

    records, dropped = winnow(records)
    records = apply_overrides(records)
    for r in sorted(records, key=lambda r: r["person_id"]):
        print(f"  {r['confidence']:6} {r['person_id']:32} <- {r['page_title']}")

    with OUT.open("w", encoding="utf-8") as fh:
        for r in sorted(records, key=lambda r: r["person_id"]):
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nwrote {len(records)} portraits to {OUT.relative_to(ROOT)}")
    print(f"discarded {len(dropped)} unsafe matches:")
    for r in sorted(dropped, key=lambda r: r["person_id"]):
        print(f"  {r['dropped']:18} {r['person_id']:32} <- {r['page_title']}")

    if rejected:
        print("\nrejected (kept as monograms):")
        for pid, why in sorted(rejected)[:40]:
            print(f"  {pid}: {why}")
        if len(rejected) > 40:
            print(f"  … and {len(rejected) - 40} more")


if __name__ == "__main__":
    main()
