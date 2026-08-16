"""Export mashruteh.db to the JSON the Astro site consumes.

One file per collection, plus a prebuilt cross-link index so the site can render
person -> events/groups, group -> people/events and event -> people/groups
without doing joins at build time.

Output: web/src/data/*.json
"""

from __future__ import annotations

import json
import os
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "mashruteh.db")
OUT = os.path.join(ROOT, "web/src/data")


def rows(con: sqlite3.Connection, sql: str, *a) -> list[dict]:
    con.row_factory = sqlite3.Row
    return [dict(r) for r in con.execute(sql, a).fetchall()]


def jloads(v):
    if not v:
        return []
    try:
        return json.loads(v)
    except Exception:
        return []


def main() -> None:
    con = sqlite3.connect(DB)
    os.makedirs(OUT, exist_ok=True)

    people = rows(con, """
        SELECT id, name_en, name_fa, full_name_en, full_name_fa, title_en, title_fa,
               gender, role_en, role_fa, biography_en, biography_fa,
               birth_g_year, birth_iso, birth_display_en, birth_display_fa,
               death_g_year, death_iso, death_display_en, death_display_fa,
               death_cause_en, death_cause_fa, is_historical_actor, is_foreign,
               nationality_en, nationality_fa, book_pages, notes_en, notes_fa
        FROM people ORDER BY name_en""")
    for p in people:
        p["book_pages"] = jloads(p["book_pages"])
        p["is_historical_actor"] = bool(p["is_historical_actor"])
        p["is_foreign"] = bool(p["is_foreign"])

    groups = rows(con, """
        SELECT g.id, g.name_en, g.name_fa, g.short_name_en, g.short_name_fa,
               g.type, g.subtype, g.description_en, g.description_fa,
               g.ideology_en, g.ideology_fa, g.place_id, g.parent_id,
               g.founded_display_en, g.founded_display_fa, g.founded_g_year,
               g.dissolved_display_en, g.dissolved_display_fa, g.dissolved_g_year,
               g.book_pages, pl.name_en AS place_en, pl.name_fa AS place_fa
        FROM groups g LEFT JOIN places pl ON pl.id = g.place_id
        ORDER BY g.name_en""")
    for g in groups:
        g["book_pages"] = jloads(g["book_pages"])

    places = rows(con, """
        SELECT id, name_en, name_fa, type, parent_id, modern_country,
               latitude, longitude, description_en, description_fa
        FROM places ORDER BY name_en""")

    events = rows(con, """
        SELECT id, title_en, title_fa, summary_en, summary_fa, type, significance,
               date_sort, date_precision, date_g_year, date_iso,
               date_display_en, date_display_fa,
               date_j_display_en, date_j_display_fa,
               date_h_display_en, date_h_display_fa, date_h_source,
               date_h_approximate, end_display_en, date_issues_json, book_pages
        FROM events ORDER BY date_sort""")
    for e in events:
        e["book_pages"] = jloads(e["book_pages"])
        e["date_issues"] = jloads(e["date_issues_json"])
        del e["date_issues_json"]
        e["date_h_approximate"] = bool(e["date_h_approximate"])

    # ---------------------------------------------------------------- links
    ep = rows(con, """
        SELECT ep.event_id, ep.person_id, ep.role_en, ep.role_fa, ep.role_type,
               p.name_en, p.name_fa
        FROM event_participants ep JOIN people p ON p.id = ep.person_id""")
    eg = rows(con, """
        SELECT eg.event_id, eg.group_id, eg.role_en, eg.role_fa, eg.role_type,
               g.name_en, g.name_fa, g.type
        FROM event_groups eg JOIN groups g ON g.id = eg.group_id""")
    epl = rows(con, """
        SELECT ev.event_id, ev.place_id, ev.role, pl.name_en, pl.name_fa
        FROM event_places ev JOIN places pl ON pl.id = ev.place_id""")
    pg = rows(con, """
        SELECT pg.person_id, pg.group_id, pg.role_en, pg.role_fa, pg.role_type,
               p.name_en AS person_en, p.name_fa AS person_fa,
               g.name_en AS group_en, g.name_fa AS group_fa, g.type AS group_type
        FROM person_groups pg
        JOIN people p ON p.id = pg.person_id
        JOIN groups g ON g.id = pg.group_id""")
    pr = rows(con, """
        SELECT r.person_a, r.person_b, r.type, r.note_en, r.note_fa,
               a.name_en AS a_en, a.name_fa AS a_fa,
               b.name_en AS b_en, b.name_fa AS b_fa
        FROM person_relations r
        JOIN people a ON a.id = r.person_a JOIN people b ON b.id = r.person_b""")
    gr = rows(con, """
        SELECT r.group_a, r.group_b, r.type, r.note_en, r.note_fa,
               a.name_en AS a_en, a.name_fa AS a_fa,
               b.name_en AS b_en, b.name_fa AS b_fa
        FROM group_relations r
        JOIN groups a ON a.id = r.group_a JOIN groups b ON b.id = r.group_b""")

    def bucket(items, key):
        out: dict[str, list] = {}
        for it in items:
            out.setdefault(it[key], []).append(it)
        return out

    links = {
        "eventPeople": bucket(ep, "event_id"),
        "eventGroups": bucket(eg, "event_id"),
        "eventPlaces": bucket(epl, "event_id"),
        "personEvents": bucket(ep, "person_id"),
        "personGroups": bucket(pg, "person_id"),
        "groupPeople": bucket(pg, "group_id"),
        "groupEvents": bucket(eg, "group_id"),
        "personRelations": bucket(pr, "person_a"),
        "groupRelations": bucket(gr, "group_a"),
    }
    # person relations are conceptually symmetric for display
    for r in pr:
        links["personRelations"].setdefault(r["person_b"], []).append({
            **r, "person_a": r["person_b"], "person_b": r["person_a"],
            "a_en": r["b_en"], "a_fa": r["b_fa"],
            "b_en": r["a_en"], "b_fa": r["a_fa"],
        })

    # Portraits live outside the database: they are fetched from Wikimedia and
    # only the ones that survived validation are published. Keyed by person so
    # the avatar component can look one up without scanning a list.
    portraits = {}
    pfile = os.path.join(ROOT, "data/portraits.jsonl")
    if os.path.exists(pfile):
        with open(pfile, encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                portraits[r["person_id"]] = {
                    "src": r["file"],
                    "page_url": r.get("page_url"),
                    "commons_url": r.get("commons_url"),
                    "license": r.get("license"),
                    "license_url": r.get("license_url"),
                    "artist": r.get("artist"),
                    "confidence": r.get("confidence"),
                }

    counts = {
        "people": len(people), "groups": len(groups), "events": len(events),
        "portraits": len(portraits),
        "places": len(places),
        "relations": len(ep) + len(eg) + len(epl) + len(pg) + len(pr) + len(gr),
    }

    for name, payload in [("people", people), ("groups", groups),
                          ("events", events), ("places", places),
                          ("links", links), ("counts", counts),
                          ("portraits", portraits)]:
        path = os.path.join(OUT, f"{name}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
        print(f"  {name:<10} {len(payload) if hasattr(payload,'__len__') else '':>5}  "
              f"{os.path.getsize(path)/1024:.0f} KB")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
