#!/usr/bin/env python3
import os
import csv
import psycopg2
from dotenv import load_dotenv

# 1) load creds
load_dotenv()
conn = psycopg2.connect(
    host=os.getenv("HOST"),
    dbname=os.getenv("DATABASE"),
    user=os.getenv("DB_USER"),
    password=os.getenv("PASSWORD"),
)
cur = conn.cursor()

# 2) open your tagged CSV
with open("tagged_vibes_and_stuff_full.csv", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        cur.execute(
            """
            UPDATE bars
               SET neighborhood   = %s,
                   club_vibes     = string_to_array(%s, ';'),
                   music_genres   = string_to_array(%s, ';')
             WHERE id = %s
            """,
            (
                row["neighborhood"],
                row["club_vibes"],
                row["music_genres"],
                row["id"],
            )
        )
# 3) commit & cleanup
conn.commit()
cur.close()
conn.close()

print("✅ Done updating all bars.")