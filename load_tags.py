#!/usr/bin/env python3
import os
import csv
import psycopg2
from dotenv import load_dotenv

# 1) Load your environment variables
load_dotenv()  # assumes .env in cwd

HOST     = os.getenv("HOST")
DB_NAME  = os.getenv("DATABASE")
USER     = os.getenv("DB_USER")
PASSWORD = os.getenv("PASSWORD")
CSV_PATH = "tagged_vibes_and_stuff_full.csv"

# 2) Connect to Postgres
conn = psycopg2.connect(
    host=HOST,
    dbname=DB_NAME,
    user=USER,
    password=PASSWORD,
)
cur = conn.cursor()

# 3) Fetch all bar primary keys in the table order
cur.execute("SELECT id FROM bars ORDER BY id;")
bar_ids = [row[0] for row in cur.fetchall()]

# 4) Open your tagged CSV (which has rows in the same order)
with open(CSV_PATH, newline="") as f:
    reader = csv.DictReader(f)
    for bar_id, row in zip(bar_ids, reader):
        neighborhood   = row["neighborhood"]
        club_vibes_str = row["club_vibes"]
        genres_str     = row["music_genres"]

        cur.execute(
            """
            UPDATE bars
               SET neighborhood   = %s,
                   club_vibes     = string_to_array(%s, ';'),
                   music_genres   = string_to_array(%s, ';')
             WHERE id = %s;
            """,
            (neighborhood, club_vibes_str, genres_str, bar_id)
        )

# 5) Commit and clean up
conn.commit()
cur.close()
conn.close()

print("✅ All bars updated in sequence without matching by CSV id.")