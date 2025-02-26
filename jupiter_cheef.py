import time
import random
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

# Database credentials
HOST = os.getenv('HOST')
DATABASE = os.getenv('DATABASE')
DB_USER = os.getenv('DB_USER')
PASSWORD = os.getenv('PASSWORD')

# Bar ID for inserting songs
BAR_ID = 19961

# List of 50 Japanese jazz songs (examples, replace with actual song titles)
JAPANESE_JAZZ_SONGS = [
    ("Misty", "Tsuyoshi Yamamoto Trio"),
    ("A Shade of Blue", "Isao Suzuki Quartet"),
    ("Blow Up", "Isao Suzuki Trio"),
    ("Midnight Sugar", "Tsuyoshi Yamamoto Trio"),
    ("Gentle Blues", "Takeshi Inomata & Sound Limited"),
    ("Sahara", "Fumio Karashima"),
    ("Scandinavian Suite", "Eiji Nakayama"),
    ("Black Nile", "Terumasa Hino"),
    ("Round Midnight", "Masabumi Kikuchi"),
    ("Someday My Prince Will Come", "Tsuyoshi Yamamoto Trio"),
    ("Aqua Marine", "Hideo Shiraki Quintet"),
    ("Lullaby of Birdland", "Toshiko Akiyoshi"),
    ("Here's That Rainy Day", "George Otsuka Quintet"),
    ("Dawn", "Masaru Imada Trio"),
    ("Speak Low", "Hidehiko Matsumoto"),
    ("On Green Dolphin Street", "Takehiro Honda"),
    ("Autumn Leaves", "Shigeharu Mukai"),
    ("Blue Bossa", "Terumasa Hino"),
    ("Stella by Starlight", "Sadao Watanabe"),
    ("Cantaloupe Island", "Fumio Itabashi"),
    ("Moanin'", "Hideo Shiraki"),
    ("Summertime", "Masaru Imada"),
    ("Four", "Takehiro Honda"),
    ("Spain", "Toshiko Akiyoshi"),
    ("I Remember Clifford", "Shigeharu Mukai"),
    ("Softly, as in a Morning Sunrise", "Masabumi Kikuchi"),
    ("Night in Tunisia", "George Otsuka"),
    ("My Funny Valentine", "Sadao Watanabe"),
    ("Wave", "Fumio Karashima"),
    ("Alone Together", "Masaru Imada Trio"),
    ("My One and Only Love", "Hidehiko Matsumoto"),
    ("Satin Doll", "Takehiro Honda"),
    ("I Got Rhythm", "Isao Suzuki Trio"),
    ("Fly Me to the Moon", "Tsuyoshi Yamamoto Trio"),
    ("Bags' Groove", "Masaru Imada"),
    ("All Blues", "Fumio Itabashi"),
    ("Django", "Terumasa Hino"),
    ("Cheek to Cheek", "Shigeharu Mukai"),
    ("It Could Happen to You", "George Otsuka"),
    ("I Love You", "Masabumi Kikuchi"),
    ("The Girl from Ipanema", "Sadao Watanabe"),
    ("Blue in Green", "Takehiro Honda"),
    ("Caravan", "Toshiko Akiyoshi"),
    ("St. Thomas", "Masaru Imada"),
    ("So What", "Hideo Shiraki"),
    ("Misty Night", "Masabumi Kikuchi"),
    ("Solar", "Isao Suzuki Trio"),
    ("Take Five", "Tsuyoshi Yamamoto Trio"),
    ("Giant Steps", "Terumasa Hino")
]

def get_db_connection():
    return psycopg2.connect(
        host=HOST,
        database=DATABASE,
        user=DB_USER,
        password=PASSWORD
    )

def insert_random_song():
    song_name, artist_name = random.choice(JAPANESE_JAZZ_SONGS)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if the song already exists for the given bar
        check_query = 'SELECT * FROM songs WHERE bar_id = %s AND name = %s AND artist = %s'
        cursor.execute(check_query, (BAR_ID, song_name, artist_name))
        result = cursor.fetchone()
        
        if result:
            print(f"Song '{song_name}' by '{artist_name}' already exists for bar id: {BAR_ID}, not adding to database.")
        else:
            # Insert the song information into the songs table
            insert_query = 'INSERT INTO songs (bar_id, name, artist) VALUES (%s, %s, %s)'
            cursor.execute(insert_query, (BAR_ID, song_name, artist_name))
            conn.commit()
            print(f"Inserted song: '{song_name}' by '{artist_name}' for bar id: {BAR_ID}")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error inserting song into database: {e}")

def run_song_inserter():
    while True:
        insert_random_song()
        print("Waiting 2 minutes before inserting the next song...")
        time.sleep(120)  # Wait for 2 minutes

if __name__ == '__main__':
    run_song_inserter()