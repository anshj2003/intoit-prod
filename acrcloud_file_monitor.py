import time
import os
import re
import base64
import hashlib
import hmac
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv('HOST')
DATABASE = os.getenv('DATABASE')
DB_USER = os.getenv('DB_USER')
PASSWORD = os.getenv('PASSWORD')

ACR_ACCESS = os.getenv('ACR_ACCESS')
ACR_SECRET = os.getenv('ACR_SECRET')

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

def get_db_connection():
    conn = psycopg2.connect(
        host=HOST,
        database=DATABASE,
        user=DB_USER,
        password=PASSWORD
    )
    return conn

# ACRCloud configuration
acr_config = {
    'host': 'identify-us-west-2.acrcloud.com',
    'access_key': ACR_ACCESS,
    'access_secret': ACR_SECRET,
    'timeout': 10  # seconds
}

requrl = f"https://{acr_config['host']}/v1/identify"

# Per-bar cooldown timestamps
next_api_call_time_by_bar = {}

# Regex for filenames
FILENAME_RE = re.compile(r'^(\d+)_\d{8}_\d{6}\.wav$')


def get_spotify_token():
    """Fetch a fresh Spotify API token using Client Credentials flow."""
    try:
        resp = requests.post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "client_credentials"},
            auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET),
        )
        resp.raise_for_status()
        return resp.json().get("access_token")
    except Exception as e:
        print(f"Error getting Spotify token: {e}")
        return None


def get_album_art_spotify(song_name, artist_name):
    """Search Spotify for album art using song + artist."""
    token = get_spotify_token()
    if not token:
        return None
    try:
        query = f"track:{song_name} artist:{artist_name}"
        resp = requests.get(
            "https://api.spotify.com/v1/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"q": query, "type": "track", "limit": 1},
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("tracks", {}).get("items", [])
        if items:
            album_images = items[0]["album"]["images"]
            if album_images:
                # Return the first (largest) image
                return album_images[0]["url"]
    except Exception as e:
        print(f"Error fetching album art: {e}")
    return None


def acrcloud_process_wav_file(bar_id, file_path):
    try:
        with open(file_path, 'rb') as f:
            wav_data = f.read()
        sample_bytes = os.path.getsize(file_path)

        current_time = time.time()
        next_time = next_api_call_time_by_bar.get(bar_id, 0)
        if current_time < next_time:
            print(f"Skipping API call for file: {file_path} due to cooldown for bar {bar_id}.")
        else:
            # Sign request
            http_method = "POST"
            http_uri = "/v1/identify"
            data_type = "audio"
            signature_version = "1"
            timestamp = str(int(time.time()))
            string_to_sign = f"{http_method}\n{http_uri}\n{acr_config['access_key']}\n{data_type}\n{signature_version}\n{timestamp}"
            sign = base64.b64encode(
                hmac.new(
                    acr_config['access_secret'].encode('ascii'),
                    string_to_sign.encode('ascii'),
                    digestmod=hashlib.sha1
                ).digest()
            ).decode('ascii')

            files = [('sample', (os.path.basename(file_path), open(file_path, 'rb'), 'audio/wav'))]
            data = {
                'access_key': acr_config['access_key'],
                'sample_bytes': sample_bytes,
                'timestamp': timestamp,
                'signature': sign,
                'data_type': data_type,
                "signature_version": signature_version
            }

            print(f"Making API call to ACRCloud for file: {file_path}")
            response = requests.post(requrl, files=files, data=data, timeout=acr_config['timeout'])
            print(f"API Response Code: {response.status_code}")
            result = response.json()

            if result and 'metadata' in result and 'music' in result['metadata'] and result['metadata']['music']:
                music_info = result['metadata']['music'][0]
                score = music_info.get('score', 0)
                if score > 30:
                    song_name = music_info.get('title', 'Unknown')
                    artists = music_info.get('artists') or []
                    artist_name = (artists[0].get('name') if artists and isinstance(artists[0], dict) else 'Unknown')

                    album_art_url = get_album_art_spotify(song_name, artist_name)

                    acrcloud_insert_song_to_db(bar_id, song_name, artist_name, album_art_url)
                    print(f"Cooldown 2 min for bar {bar_id}.")
                    next_api_call_time_by_bar[bar_id] = current_time + 120
                else:
                    print(f"Score < 30 for file: {file_path}")
            else:
                print(f"No song recognized for file: {file_path}")
    except Exception as e:
        print(f"Error processing WAV file: {e}")
    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Deleted {file_path}")
        except Exception as e:
            print(f"Warning: could not delete {file_path}: {e}")


def acrcloud_insert_song_to_db(bar_id, song_name, artist_name, album_art_url):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        check_query = 'SELECT 1 FROM songs WHERE bar_id = %s AND name = %s AND artist = %s LIMIT 1'
        cursor.execute(check_query, (bar_id, song_name, artist_name))
        result = cursor.fetchone()

        if result:
            print(f"Song '{song_name}' by '{artist_name}' already exists for bar {bar_id}.")
        else:
            insert_query = 'INSERT INTO songs (bar_id, name, artist, album_art) VALUES (%s, %s, %s, %s)'
            cursor.execute(insert_query, (bar_id, song_name, artist_name, album_art_url))
            conn.commit()
            print(f"Inserted '{song_name}' by '{artist_name}' for bar {bar_id} (album art: {album_art_url})")
    except Exception as e:
        print(f"Error inserting song into DB: {e}")
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass


def monitor_files():
    base_directory = './static/uploads'
    os.makedirs(base_directory, exist_ok=True)

    while True:
        print("Monitoring files...")
        try:
            for file_name in os.listdir(base_directory):
                if not file_name.endswith('.wav'):
                    continue

                m = FILENAME_RE.match(file_name)
                if not m:
                    print(f"Skipping bad filename: {file_name}")
                    continue

                bar_id = m.group(1)
                file_path = os.path.join(base_directory, file_name)

                try:
                    size1 = os.path.getsize(file_path)
                    time.sleep(0.2)
                    size2 = os.path.getsize(file_path)
                    if size1 != size2:
                        print(f"File still growing: {file_path}")
                        continue
                except FileNotFoundError:
                    continue

                try:
                    acrcloud_process_wav_file(bar_id, file_path)
                except Exception as e:
                    print(f"Error processing file {file_path}: {e}")
        except Exception as loop_err:
            print(f"Monitor loop error: {loop_err}")

        time.sleep(10)


if __name__ == '__main__':
    monitor_files()