#!/usr/bin/env python3
import os
import csv
import psycopg2
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────
# 1) Load environment variables from .env
load_dotenv()
HOST     = os.getenv("HOST")
DB_NAME  = os.getenv("DATABASE")
USER     = os.getenv("DB_USER")
PASSWORD = os.getenv("PASSWORD")
CSV_PATH = "tagged_vibes_and_stuff_full.csv"

# ─────────────────────────────────────────────────────────────
# 2) Connect to your Postgres database
conn = psycopg2.connect(
    host=HOST,
    dbname=DB_NAME,
    user=USER,
    password=PASSWORD,
)
cur = conn.cursor()

# ─────────────────────────────────────────────────────────────
# 3) Fetch all bar primary keys in order (so we can update by sequence)
cur.execute("SELECT id FROM bars ORDER BY id;")
bar_ids = [row[0] for row in cur.fetchall()]

# ─────────────────────────────────────────────────────────────
# 4) Open your tagged CSV (must be in same order as bars)
with open(CSV_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for bar_id, row in zip(bar_ids, reader):
        # Read raw semicolon-delimited strings
        raw_neighborhood = row.get("neighborhood", "") or ""
        raw_vibes        = row.get("club_vibes", "") or ""
        raw_genres       = row.get("music_genres", "") or ""

        # Clean up stray quotation marks on each element
        vibes_list  = [v.strip().strip('"') for v in raw_vibes.split(";") if v.strip()]
        genres_list = [g.strip().strip('"') for g in raw_genres.split(";") if g.strip()]

        # Re-join into semicolon-delimited strings for the SQL array conversion
        cleaned_vibes  = ";".join(vibes_list)
        cleaned_genres = ";".join(genres_list)

        # Execute the UPDATE by sequence
        cur.execute(
            """
            UPDATE bars
               SET neighborhood   = %s,
                   club_vibes     = string_to_array(%s, ';'),
                   music_genres   = string_to_array(%s, ';')
             WHERE id = %s;
            """,
            (raw_neighborhood, cleaned_vibes, cleaned_genres, bar_id)
        )
        print(f"Updated bar id={bar_id} → neighborhood='{raw_neighborhood}', vibes={vibes_list}, genres={genres_list}")

# ─────────────────────────────────────────────────────────────
# 5) Commit and close connection
conn.commit()
cur.close()
conn.close()

print("✅ All done — bars updated in sequence without matching by CSV id.")