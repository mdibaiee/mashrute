-- Iranian Constitutional Revolution (1906-1911) — relational dataset
-- Source: Janet Afary, "The Iranian Constitutional Revolution, 1906-1911"
--         (Columbia UP, 1996) and its Persian translation by Reza Rezaei
--         (نشر بیستون, 1385).
--
-- Design notes
-- ------------
-- * Bilingual by construction: every human-readable field exists as *_en and
--   *_fa. A missing translation is NULL, never an English fallback, so the
--   site can tell "not translated" from "same in both".
-- * Dates are stored three ways (Gregorian / Solar Hijri / Lunar Hijri) with an
--   explicit precision, plus a sort key that is safe to ORDER BY even for fuzzy
--   dates. Gregorian is the anchor; Solar Hijri is COMPUTED with the
--   astronomical rule (see scripts/dates.py) rather than copied from the
--   translation, which is a day off in several years. What the book printed is
--   preserved in date_book_json so any correction is auditable.
-- * Every row carries provenance: which book, which pages.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------- sources

CREATE TABLE sources (
    id           TEXT PRIMARY KEY,
    kind         TEXT NOT NULL,             -- book | chronology | index | web
    title_en     TEXT,
    title_fa     TEXT,
    author_en    TEXT,
    author_fa    TEXT,
    citation_en  TEXT,
    citation_fa  TEXT,
    url          TEXT
);

-- ----------------------------------------------------------------- places

CREATE TABLE places (
    id            TEXT PRIMARY KEY,
    name_en       TEXT NOT NULL,
    name_fa       TEXT,
    type          TEXT,                     -- city | town | village | province |
                                            -- country | region | district |
                                            -- building | shrine | quarter | sea
    parent_id     TEXT REFERENCES places(id),
    modern_country TEXT,
    latitude      REAL,
    longitude     REAL,
    description_en TEXT,
    description_fa TEXT,
    book_pages    TEXT,                     -- JSON array of printed page numbers
    wikipedia_en  TEXT,
    wikipedia_fa  TEXT
);

-- ----------------------------------------------------------------- groups

CREATE TABLE groups (
    id            TEXT PRIMARY KEY,
    name_en       TEXT NOT NULL,
    name_fa       TEXT,
    short_name_en TEXT,
    short_name_fa TEXT,
    type          TEXT NOT NULL,            -- see docs/DATA_MODEL.md for the
                                            -- controlled vocabulary
    subtype       TEXT,
    description_en TEXT,
    description_fa TEXT,
    ideology_en   TEXT,
    ideology_fa   TEXT,
    place_id      TEXT REFERENCES places(id),
    parent_id     TEXT REFERENCES groups(id),

    founded_g_year INTEGER, founded_g_month INTEGER, founded_g_day INTEGER,
    founded_iso    TEXT,
    founded_j_year INTEGER, founded_j_month INTEGER, founded_j_day INTEGER,
    founded_display_en TEXT, founded_display_fa TEXT,
    dissolved_g_year INTEGER, dissolved_g_month INTEGER, dissolved_g_day INTEGER,
    dissolved_iso    TEXT,
    dissolved_j_year INTEGER, dissolved_j_month INTEGER, dissolved_j_day INTEGER,
    dissolved_display_en TEXT, dissolved_display_fa TEXT,

    book_pages    TEXT,
    wikipedia_en  TEXT,
    wikipedia_fa  TEXT,
    notes_en      TEXT,
    notes_fa      TEXT
);

-- ----------------------------------------------------------------- people

CREATE TABLE people (
    id            TEXT PRIMARY KEY,
    name_en       TEXT NOT NULL,            -- display name, e.g. "Sattar Khan"
    name_fa       TEXT,                     -- ستارخان
    full_name_en  TEXT,
    full_name_fa  TEXT,
    sort_name_en  TEXT,                     -- "Sattar Khan" -> surname-first form
    sort_name_fa  TEXT,
    title_en      TEXT,                     -- honorific / office title
    title_fa      TEXT,
    gender        TEXT,                     -- male | female | unknown
    role_en       TEXT,                     -- one-line descriptor for listings
    role_fa       TEXT,
    biography_en  TEXT,
    biography_fa  TEXT,

    birth_g_year INTEGER, birth_g_month INTEGER, birth_g_day INTEGER,
    birth_iso    TEXT,    birth_precision TEXT,
    birth_j_year INTEGER, birth_j_month INTEGER, birth_j_day INTEGER,
    birth_display_en TEXT, birth_display_fa TEXT,
    birth_place_id TEXT REFERENCES places(id),

    death_g_year INTEGER, death_g_month INTEGER, death_g_day INTEGER,
    death_iso    TEXT,    death_precision TEXT,
    death_j_year INTEGER, death_j_month INTEGER, death_j_day INTEGER,
    death_display_en TEXT, death_display_fa TEXT,
    death_place_id TEXT REFERENCES places(id),
    death_cause_en TEXT,
    death_cause_fa TEXT,

    -- Afary cites modern historians in the same index as historical actors;
    -- the site must not mix them into the cast of the revolution.
    is_historical_actor INTEGER NOT NULL DEFAULT 1,
    is_foreign          INTEGER NOT NULL DEFAULT 0,
    nationality_en TEXT,
    nationality_fa TEXT,

    book_pages    TEXT,
    wikipedia_en  TEXT,
    wikipedia_fa  TEXT,
    notes_en      TEXT,
    notes_fa      TEXT
);

CREATE TABLE person_aliases (
    id         INTEGER PRIMARY KEY,
    person_id  TEXT NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    lang       TEXT,                        -- en | fa
    kind       TEXT,                        -- title | pen_name | variant |
                                            -- birth_name | transliteration
    UNIQUE (person_id, name, lang)
);

CREATE TABLE group_aliases (
    id         INTEGER PRIMARY KEY,
    group_id   TEXT NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    lang       TEXT,
    kind       TEXT,
    UNIQUE (group_id, name, lang)
);

-- ----------------------------------------------------------------- events

CREATE TABLE events (
    id            TEXT PRIMARY KEY,
    title_en      TEXT NOT NULL,
    title_fa      TEXT,
    summary_en    TEXT,
    summary_fa    TEXT,
    description_en TEXT,
    description_fa TEXT,
    type          TEXT,                     -- controlled vocabulary
    significance  INTEGER,                  -- 1 (major) .. 3 (minor)

    date_sort     TEXT NOT NULL,            -- always safe to ORDER BY
    date_precision TEXT NOT NULL,           -- day|month|season|year|range|unknown
    date_g_year INTEGER, date_g_month INTEGER, date_g_day INTEGER,
    date_iso      TEXT,
    date_j_year INTEGER, date_j_month INTEGER, date_j_day INTEGER,
    date_h_year INTEGER, date_h_month INTEGER, date_h_day INTEGER,
    date_h_source TEXT,                     -- book | computed
    date_h_approximate INTEGER DEFAULT 0,
    date_display_en TEXT, date_display_fa TEXT,
    date_j_display_en TEXT, date_j_display_fa TEXT,
    date_h_display_en TEXT, date_h_display_fa TEXT,

    end_g_year INTEGER, end_g_month INTEGER, end_g_day INTEGER,
    end_iso    TEXT,
    end_j_year INTEGER, end_j_month INTEGER, end_j_day INTEGER,
    end_display_en TEXT, end_display_fa TEXT,

    date_book_json TEXT,                    -- what the book printed
    date_issues_json TEXT,                  -- detected discrepancies
    period_en     TEXT,                     -- e.g. "First Constitutional Period"
    period_fa     TEXT,
    book_pages    TEXT,
    source_id     TEXT REFERENCES sources(id),
    notes_en      TEXT,
    notes_fa      TEXT
);

-- ---------------------------------------------------------- relationships

CREATE TABLE event_places (
    event_id  TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    place_id  TEXT NOT NULL REFERENCES places(id) ON DELETE CASCADE,
    role      TEXT,                         -- primary | secondary | mentioned
    PRIMARY KEY (event_id, place_id)
);

CREATE TABLE event_participants (
    event_id   TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    person_id  TEXT NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    role_en    TEXT,                        -- "led the protest", "was assassinated"
    role_fa    TEXT,
    role_type  TEXT,                        -- leader|participant|victim|perpetrator|
                                            -- signatory|opponent|witness|author
    PRIMARY KEY (event_id, person_id, role_type)
);

CREATE TABLE event_groups (
    event_id  TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    group_id  TEXT NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    role_en   TEXT,
    role_fa   TEXT,
    role_type TEXT,
    PRIMARY KEY (event_id, group_id, role_type)
);

CREATE TABLE person_groups (
    person_id  TEXT NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    group_id   TEXT NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    role_en    TEXT,                        -- "founder", "delegate", "editor"
    role_fa    TEXT,
    role_type  TEXT,                        -- founder|leader|member|affiliate|
                                            -- opponent|representative
    start_g_year INTEGER, start_iso TEXT, start_display_en TEXT, start_display_fa TEXT,
    end_g_year   INTEGER, end_iso   TEXT, end_display_en   TEXT, end_display_fa   TEXT,
    book_pages TEXT,
    note_en    TEXT,
    note_fa    TEXT,
    PRIMARY KEY (person_id, group_id, role_type)
);

CREATE TABLE person_relations (
    person_a  TEXT NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    person_b  TEXT NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    type      TEXT NOT NULL,                -- ally|rival|kin|assassinated|
                                            -- succeeded|mentor|collaborator
    note_en   TEXT,
    note_fa   TEXT,
    PRIMARY KEY (person_a, person_b, type)
);

CREATE TABLE group_relations (
    group_a   TEXT NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    group_b   TEXT NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    type      TEXT NOT NULL,                -- branch_of|allied|opposed|split_from|
                                            -- merged_into|successor
    note_en   TEXT,
    note_fa   TEXT,
    PRIMARY KEY (group_a, group_b, type)
);

-- Free-text passages backing a record, so the site can quote the source.
CREATE TABLE citations (
    id          INTEGER PRIMARY KEY,
    entity_type TEXT NOT NULL,              -- person | group | event | place
    entity_id   TEXT NOT NULL,
    source_id   TEXT REFERENCES sources(id),
    page        INTEGER,
    quote_en    TEXT,
    quote_fa    TEXT
);

-- ------------------------------------------------------------------ index

CREATE INDEX idx_events_sort        ON events(date_sort);
CREATE INDEX idx_events_year        ON events(date_g_year);
CREATE INDEX idx_events_type        ON events(type);
CREATE INDEX idx_people_actor       ON people(is_historical_actor);
CREATE INDEX idx_groups_type        ON groups(type);
CREATE INDEX idx_ep_person          ON event_participants(person_id);
CREATE INDEX idx_ep_event           ON event_participants(event_id);
CREATE INDEX idx_eg_group           ON event_groups(group_id);
CREATE INDEX idx_pg_person          ON person_groups(person_id);
CREATE INDEX idx_pg_group           ON person_groups(group_id);
CREATE INDEX idx_evpl_place         ON event_places(place_id);
CREATE INDEX idx_citations_entity   ON citations(entity_type, entity_id);

-- --------------------------------------------------------------- convenience

CREATE VIEW v_person_event_count AS
SELECT p.id, p.name_en, p.name_fa, COUNT(ep.event_id) AS event_count
FROM people p LEFT JOIN event_participants ep ON ep.person_id = p.id
GROUP BY p.id;

CREATE VIEW v_group_membership AS
SELECT g.id AS group_id, g.name_en AS group_en, g.name_fa AS group_fa,
       p.id AS person_id, p.name_en AS person_en, p.name_fa AS person_fa,
       pg.role_en, pg.role_fa, pg.role_type
FROM person_groups pg
JOIN groups g ON g.id = pg.group_id
JOIN people p ON p.id = pg.person_id;

CREATE VIEW v_timeline AS
SELECT e.id, e.date_sort, e.date_iso, e.date_display_en, e.date_display_fa,
       e.date_j_display_en, e.date_j_display_fa,
       e.title_en, e.title_fa, e.type, e.significance,
       (SELECT COUNT(*) FROM event_participants x WHERE x.event_id = e.id) AS n_people,
       (SELECT COUNT(*) FROM event_groups     x WHERE x.event_id = e.id) AS n_groups
FROM events e
ORDER BY e.date_sort;
