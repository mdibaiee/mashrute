"""Print a coverage and quality report for the built database."""
import os, sqlite3, sys
DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mashruteh.db")
con = sqlite3.connect(DB)
q = lambda s: con.execute(s).fetchall()
def line(label, val): print(f"  {label:<44} {val}")

print("COUNTS")
for t in ("places","groups","people","events","event_participants","event_groups",
          "event_places","person_groups","person_relations","group_relations"):
    line(t, q(f"select count(*) from {t}")[0][0])

print("\nBILINGUAL COVERAGE")
for t, f in (("people","name_fa"),("groups","name_fa"),("places","name_fa"),("events","title_fa")):
    tot = q(f"select count(*) from {t}")[0][0]
    has = q(f"select count(*) from {t} where {f} is not null and {f}<>''")[0][0]
    line(f"{t}.{f}", f"{has}/{tot}  ({100*has//max(tot,1)}%)")
for t, f in (("people","biography_fa"),("events","summary_fa"),("groups","description_fa")):
    tot = q(f"select count(*) from {t}")[0][0]
    has = q(f"select count(*) from {t} where {f} is not null and {f}<>''")[0][0]
    line(f"{t}.{f}", f"{has}/{tot}")

print("\nDATES")
line("events with a full Gregorian day", q("select count(*) from events where date_g_day is not null")[0][0])
line("events with a computed Solar Hijri date", q("select count(*) from events where date_j_year is not null")[0][0])
line("events with a Lunar Hijri date", q("select count(*) from events where date_h_year is not null")[0][0])
line("  of those, taken from the book", q("select count(*) from events where date_h_source='book'")[0][0])
line("  of those, computed (approximate)", q("select count(*) from events where date_h_source='computed'")[0][0])
line("events where the book's date disagreed", q("select count(*) from events where date_issues_json is not null")[0][0])
line("people with a birth year", q("select count(*) from people where birth_g_year is not null")[0][0])
line("people with a death year", q("select count(*) from people where death_g_year is not null")[0][0])
line("date range", f"{q('select min(date_g_year) from events')[0][0]}–{q('select max(date_g_year) from events')[0][0]}")

print("\nORPHANS (entities with no links — candidates for enrichment)")
line("people in no event and no group", q("""select count(*) from people p where is_historical_actor=1
  and not exists(select 1 from event_participants x where x.person_id=p.id)
  and not exists(select 1 from person_groups x where x.person_id=p.id)""")[0][0])
line("groups in no event with no members", q("""select count(*) from groups g
  where not exists(select 1 from event_groups x where x.group_id=g.id)
  and not exists(select 1 from person_groups x where x.group_id=g.id)""")[0][0])
line("events with no participants and no groups", q("""select count(*) from events e
  where not exists(select 1 from event_participants x where x.event_id=e.id)
  and not exists(select 1 from event_groups x where x.event_id=e.id)""")[0][0])
line("places referenced by nothing", q("""select count(*) from places p
  where not exists(select 1 from event_places x where x.place_id=p.id)
  and not exists(select 1 from groups x where x.place_id=p.id)
  and not exists(select 1 from places x where x.parent_id=p.id)""")[0][0])

print("\nGROUPS BY TYPE")
for t,n in q("select type,count(*) from groups group by type order by 2 desc"): line(t,n)
print("\nEVENTS BY TYPE")
for t,n in q("select type,count(*) from events group by type order by 2 desc"): line(t or "(none)",n)
