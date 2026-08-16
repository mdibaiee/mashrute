"""Build mashruteh.db from the curated JSONL in data/extracted/.

Records are merged by id (a later record patches an earlier one), dates are
normalised through scripts/dates.build_date(), then everything is written to a
fresh SQLite file. Re-runnable: the database is rebuilt from scratch each time,
so the JSONL stays the single source of truth.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dates import build_date  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EX = os.path.join(ROOT, "data/extracted")
DB = os.path.join(ROOT, "mashruteh.db")
SCHEMA = os.path.join(ROOT, "schema.sql")


def read_jsonl(name: str) -> list[dict]:
    path = os.path.join(EX, name)
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{name}:{i}: bad JSON — {exc}") from exc
    return out


def merge_by_id(records: list[dict], key: str = "id") -> list[dict]:
    """Later records patch earlier ones; list fields union, scalars overwrite."""
    merged: dict[str, dict] = {}
    order: list[str] = []
    for rec in records:
        rid = rec.get(key)
        if not rid:
            raise SystemExit(f"record without {key}: {rec}")
        if rid not in merged:
            merged[rid] = dict(rec)
            order.append(rid)
            continue
        cur = merged[rid]
        for k, v in rec.items():
            if v is None:
                continue
            if isinstance(v, list) and isinstance(cur.get(k), list):
                seen = {json.dumps(x, sort_keys=True, ensure_ascii=False) for x in cur[k]}
                for item in v:
                    if json.dumps(item, sort_keys=True, ensure_ascii=False) not in seen:
                        cur[k].append(item)
            elif isinstance(v, dict) and isinstance(cur.get(k), dict):
                cur[k].update(v)
            else:
                cur[k] = v
    return [merged[i] for i in order]


def jarr(v) -> str | None:
    return json.dumps(v, ensure_ascii=False) if v else None


def date_cols(spec: dict | None, prefix: str) -> dict:
    """Flatten a date spec into the column set used by `people` / `groups`."""
    if not spec:
        return {}
    d = build_date(spec.get("g_year"), spec.get("g_month"), spec.get("g_day"),
                   spec.get("precision", "day"),
                   book_jalali=spec.get("book_jalali"))
    g, j = d.get("gregorian") or {}, d.get("jalali") or {}
    out = {
        f"{prefix}_g_year": g.get("year"), f"{prefix}_g_month": g.get("month"),
        f"{prefix}_g_day": g.get("day"), f"{prefix}_iso": g.get("iso"),
        f"{prefix}_j_year": j.get("year"), f"{prefix}_j_month": j.get("month"),
        f"{prefix}_j_day": j.get("day"),
        f"{prefix}_display_en": g.get("display_en"),
        f"{prefix}_display_fa": g.get("display_fa"),
    }
    if prefix in ("birth", "death"):
        out[f"{prefix}_precision"] = d.get("precision")
    return out


def event_date_cols(spec: dict | None) -> dict:
    d = build_date(**{k: v for k, v in (spec or {}).items()
                      if k in ("g_year", "g_month", "g_day", "precision",
                               "g_year_end", "g_month_end", "g_day_end",
                               "season", "season_end", "book_jalali",
                               "book_hijri", "book_gregorian_raw", "note")})
    g = d.get("gregorian") or {}
    j = d.get("jalali") or {}
    h = d.get("hijri") or {}
    end = (d.get("end") or {}).get("gregorian") or {}
    endj = (d.get("end") or {}).get("jalali") or {}
    return {
        "date_sort": d["sort_key"], "date_precision": d["precision"],
        "date_g_year": g.get("year"), "date_g_month": g.get("month"),
        "date_g_day": g.get("day"), "date_iso": g.get("iso"),
        "date_j_year": j.get("year"), "date_j_month": j.get("month"),
        "date_j_day": j.get("day"),
        "date_h_year": h.get("year"), "date_h_month": h.get("month"),
        "date_h_day": h.get("day"), "date_h_source": h.get("source"),
        "date_h_approximate": 1 if h.get("approximate") else 0,
        "date_display_en": g.get("display_en"), "date_display_fa": g.get("display_fa"),
        "date_j_display_en": j.get("display_en"), "date_j_display_fa": j.get("display_fa"),
        "date_h_display_en": h.get("display_en"), "date_h_display_fa": h.get("display_fa"),
        "end_g_year": end.get("year"), "end_g_month": end.get("month"),
        "end_g_day": end.get("day"), "end_iso": end.get("iso"),
        "end_j_year": endj.get("year"), "end_j_month": endj.get("month"),
        "end_j_day": endj.get("day"),
        "end_display_en": end.get("display_en"),
        "date_book_json": jarr(d.get("book_printed")),
        "date_issues_json": jarr(d.get("discrepancies")),
    }


def insert(con: sqlite3.Connection, table: str, row: dict) -> None:
    row = {k: v for k, v in row.items() if v is not None}
    cols = ", ".join(row)
    marks = ", ".join("?" * len(row))
    con.execute(f"INSERT OR REPLACE INTO {table} ({cols}) VALUES ({marks})",
                list(row.values()))


def main() -> None:
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    con.executescript(open(SCHEMA, encoding="utf-8").read())

    stats: dict[str, int] = defaultdict(int)

    for rec in merge_by_id(read_jsonl("sources.jsonl")):
        insert(con, "sources", rec)
        stats["sources"] += 1

    for rec in merge_by_id(read_jsonl("places.jsonl")):
        insert(con, "places", {
            "id": rec["id"], "name_en": rec.get("name_en"), "name_fa": rec.get("name_fa"),
            "type": rec.get("type"), "parent_id": rec.get("parent_id"),
            "modern_country": rec.get("modern_country"),
            "latitude": rec.get("latitude"), "longitude": rec.get("longitude"),
            "description_en": rec.get("description_en"),
            "description_fa": rec.get("description_fa"),
            "book_pages": jarr(rec.get("book_pages")),
            "wikipedia_en": rec.get("wikipedia_en"),
            "wikipedia_fa": rec.get("wikipedia_fa"),
        })
        stats["places"] += 1

    for rec in merge_by_id(read_jsonl("groups.jsonl")):
        row = {
            "id": rec["id"], "name_en": rec.get("name_en"), "name_fa": rec.get("name_fa"),
            "short_name_en": rec.get("short_name_en"),
            "short_name_fa": rec.get("short_name_fa"),
            "type": rec.get("type", "other"), "subtype": rec.get("subtype"),
            "description_en": rec.get("description_en"),
            "description_fa": rec.get("description_fa"),
            "ideology_en": rec.get("ideology_en"), "ideology_fa": rec.get("ideology_fa"),
            "place_id": rec.get("place_id"), "parent_id": rec.get("parent_id"),
            "book_pages": jarr(rec.get("book_pages")),
            "wikipedia_en": rec.get("wikipedia_en"),
            "wikipedia_fa": rec.get("wikipedia_fa"),
            "notes_en": rec.get("notes_en"), "notes_fa": rec.get("notes_fa"),
        }
        row.update(date_cols(rec.get("founded"), "founded"))
        row.update(date_cols(rec.get("dissolved"), "dissolved"))
        insert(con, "groups", row)
        stats["groups"] += 1
        for al in rec.get("aliases", []):
            insert(con, "group_aliases", {"group_id": rec["id"], "name": al.get("name"),
                                          "lang": al.get("lang"), "kind": al.get("kind")})

    for rec in merge_by_id(read_jsonl("people.jsonl")):
        row = {
            "id": rec["id"], "name_en": rec.get("name_en"), "name_fa": rec.get("name_fa"),
            "full_name_en": rec.get("full_name_en"),
            "full_name_fa": rec.get("full_name_fa"),
            "sort_name_en": rec.get("sort_name_en"),
            "sort_name_fa": rec.get("sort_name_fa"),
            "title_en": rec.get("title_en"), "title_fa": rec.get("title_fa"),
            "gender": rec.get("gender"),
            "role_en": rec.get("role_en"), "role_fa": rec.get("role_fa"),
            "biography_en": rec.get("biography_en"),
            "biography_fa": rec.get("biography_fa"),
            "birth_place_id": rec.get("birth_place_id"),
            "death_place_id": rec.get("death_place_id"),
            "death_cause_en": rec.get("death_cause_en"),
            "death_cause_fa": rec.get("death_cause_fa"),
            "is_historical_actor": 0 if rec.get("is_historical_actor") is False else 1,
            "is_foreign": 1 if rec.get("is_foreign") else 0,
            "nationality_en": rec.get("nationality_en"),
            "nationality_fa": rec.get("nationality_fa"),
            "book_pages": jarr(rec.get("book_pages")),
            "wikipedia_en": rec.get("wikipedia_en"),
            "wikipedia_fa": rec.get("wikipedia_fa"),
            "notes_en": rec.get("notes_en"), "notes_fa": rec.get("notes_fa"),
        }
        row.update(date_cols(rec.get("birth"), "birth"))
        row.update(date_cols(rec.get("death"), "death"))
        insert(con, "people", row)
        stats["people"] += 1
        for al in rec.get("aliases", []):
            insert(con, "person_aliases", {"person_id": rec["id"], "name": al.get("name"),
                                           "lang": al.get("lang"), "kind": al.get("kind")})

    events = merge_by_id(read_jsonl("events.jsonl"))
    for rec in events:
        row = {
            "id": rec["id"], "title_en": rec.get("title_en"),
            "title_fa": rec.get("title_fa"),
            "summary_en": rec.get("summary_en"), "summary_fa": rec.get("summary_fa"),
            "description_en": rec.get("description_en"),
            "description_fa": rec.get("description_fa"),
            "type": rec.get("type"), "significance": rec.get("significance"),
            "period_en": rec.get("period_en"), "period_fa": rec.get("period_fa"),
            "book_pages": jarr(rec.get("book_pages")),
            "source_id": rec.get("source_id"),
            "notes_en": rec.get("notes_en"), "notes_fa": rec.get("notes_fa"),
        }
        row.update(event_date_cols(rec.get("date")))
        insert(con, "events", row)
        stats["events"] += 1
        for pl in rec.get("places", []):
            insert(con, "event_places", {"event_id": rec["id"], "place_id": pl["id"],
                                         "role": pl.get("role", "primary")})
            stats["event_places"] += 1

    # ------------------------------------------------------------ relations
    tables = {
        "person_group": ("person_groups", ("person_id", "group_id", "role_en",
                                           "role_fa", "role_type", "note_en",
                                           "note_fa")),
        "event_participant": ("event_participants", ("event_id", "person_id",
                                                     "role_en", "role_fa",
                                                     "role_type")),
        "event_group": ("event_groups", ("event_id", "group_id", "role_en",
                                         "role_fa", "role_type")),
        "event_place": ("event_places", ("event_id", "place_id", "role")),
        "person_relation": ("person_relations", ("person_a", "person_b", "type",
                                                 "note_en", "note_fa")),
        "group_relation": ("group_relations", ("group_a", "group_b", "type",
                                               "note_en", "note_fa")),
    }
    for rec in read_jsonl("relations.jsonl"):
        kind = rec.get("rel")
        if kind not in tables:
            raise SystemExit(f"unknown relation kind: {kind}")
        table, cols = tables[kind]
        row = {c: rec.get(c) for c in cols}
        row.setdefault("role_type", rec.get("role_type"))
        if table in ("person_groups", "event_participants", "event_groups") \
                and not row.get("role_type"):
            row["role_type"] = "member" if table == "person_groups" else "participant"
        if table == "person_groups":
            for side in ("start", "end"):
                spec = rec.get(side)
                if spec:
                    d = build_date(spec.get("g_year"), spec.get("g_month"),
                                   spec.get("g_day"), spec.get("precision", "day"))
                    g = d.get("gregorian") or {}
                    row[f"{side}_g_year"] = g.get("year")
                    row[f"{side}_iso"] = g.get("iso")
                    row[f"{side}_display_en"] = g.get("display_en")
                    row[f"{side}_display_fa"] = g.get("display_fa")
            row["book_pages"] = jarr(rec.get("book_pages"))
        insert(con, table, row)
        stats[table] += 1

    for rec in read_jsonl("citations.jsonl"):
        insert(con, "citations", rec)
        stats["citations"] += 1

    con.commit()

    print("Rows written")
    for k in sorted(stats):
        print(f"  {k:<20} {stats[k]:>6}")
    orphans = con.execute("PRAGMA foreign_key_check").fetchall()
    if orphans:
        print(f"\n!! {len(orphans)} foreign-key violations, first 10:")
        for o in orphans[:10]:
            print("   ", o)
    else:
        print("\nforeign keys: OK")
    con.close()
    print(f"-> {DB}")


if __name__ == "__main__":
    main()
