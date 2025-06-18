#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import psycopg2
import pandas as pd
from io import StringIO

# ── 1) Load env ───────────────────────────────────────────────
load_dotenv()  # reads .env in cwd

HOST     = os.getenv("HOST")
DB_NAME  = os.getenv("DATABASE")
USER     = os.getenv("DB_USER")
PASSWORD = os.getenv("PASSWORD")

CSV_PATH = "tagged_vibes_and_stuff_full.csv"

# ── 2) Read CSV into memory ───────────────────────────────────
df = pd.read_csv(CSV_PATH, dtype=str)  # read everything as string

# Reorder columns exactly as they appear in CSV (id, neighborhood, club_vibes, music_genres)
df = df[["id", "neighborhood", "club_vibes", "music_genres"]]

# ── 3) Connect to Postgres ────────────────────────────────────
conn = psycopg2.connect(
    host=HOST,
    dbname=DB_NAME,
    user=USER,
    password=PASSWORD,
)
cur = conn.cursor()

# ── 4) Create temp table ──────────────────────────────────────
cur.execute("""
CREATE TEMP TABLE tmp_tags (
  id           TEXT PRIMARY KEY,
  neighborhood TEXT,
  club_vibes   TEXT,
  music_genres TEXT
) ON COMMIT DROP;
""")
conn.commit()

# ── 5) COPY the DataFrame into tmp_tags ───────────────────────
# We'll stream it via StringIO for speed
buffer = StringIO()
df.to_csv(buffer, index=False, header=False)
buffer.seek(0)

cur.copy_from(
    file=buffer,
    table="tmp_tags",
    sep=",",
    columns=("id","neighborhood","club_vibes","music_genres")
)
conn.commit()

# ── 6) Update your bars table from tmp_tags ────────────────────
cur.execute("""
UPDATE bars AS b
SET
  neighborhood = t.neighborhood,
  club_vibes   = string_to_array(t.club_vibes, ';'),
  music_genres = string_to_array(t.music_genres, ';')
FROM tmp_tags AS t
WHERE b.id = t.id;
""")
conn.commit()

print(f"✅ Updated {cur.rowcount} rows in bars")

# ── 7) Clean up ────────────────────────────────────────────────
cur.close()
conn.close()