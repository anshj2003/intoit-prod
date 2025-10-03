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

# Per-bar cooldown timestamps (replaces global single cooldown)
next_api_call_time_by_bar = {}

# Match: 17882_20251003_013018.wav  -> bar_id = 17882
FILENAME_RE = re.compile(r'^(\d+)_\d{8}_\d{6}\.wav$')

def acrcloud_process_wav_file(bar_id, file_path):
    try:
        # Read .wav file content
        with open(file_path, 'rb') as f:
            wav_data = f.read()
        sample_bytes = os.path.getsize(file_path)

        current_time = time.time()
        # Respect the 2-minute cool-down AFTER a high-score ID — per bar
        next_time = next_api_call_time_by_bar.get(bar_id, 0)
        if current_time < next_time:
            print(f"Skipping API call for file: {file_path} due to 2-minute wait period for bar {bar_id}.")
        else:
            # Prepare the request to ACRCloud
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

            files = [
                ('sample', (os.path.basename(file_path), open(file_path, 'rb'), 'audio/wav'))
            ]
            data = {
                'access_key': acr_config['access_key'],
                'sample_bytes': sample_bytes,
                'timestamp': timestamp,
                'signature': sign,
                'data_type': data_type,
                "signature_version": signature_version
            }

            # Send request to ACRCloud to recognize the song
            print(f"Making API call to ACRCloud for file: {file_path}")
            response = requests.post(requrl, files=files, data=data, timeout=acr_config['timeout'])
            response.encoding = "utf-8"
            print(f"API Response Code: {response.status_code}")
            print(f"API Response: {response.text}")
            result = response.json()

            # Check if the song was recognized and the score is greater than 30
            if result and 'metadata' in result and 'music' in result['metadata'] and result['metadata']['music']:
                music_info = result['metadata']['music'][0]
                score = music_info.get('score', 0)
                if score > 30:
                    song_name = music_info.get('title', 'Unknown')
                    # 'artists' may be list of dicts; pick first name if present
                    artists = music_info.get('artists') or []
                    artist_name = (artists[0].get('name') if artists and isinstance(artists[0], dict) else 'Unknown')

                    # Insert song into the database if not already present
                    acrcloud_insert_song_to_db(bar_id, song_name, artist_name)
                    print(f"Waiting for 2 minutes before making the next API call for bar {bar_id}.")
                    next_api_call_time_by_bar[bar_id] = current_time + 120  # per-bar cooldown
                else:
                    print(f"Score < 30 for file: {file_path}, not adding to database.")
            else:
                print(f"No song recognized for file: {file_path}")
    except Exception as e:
        print(f"Error processing WAV file: {e}")
    finally:
        # Delete the file after processing or skipping, matching your current behavior
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"File {file_path} has been deleted.")
        except Exception as e:
            print(f"Warning: could not delete {file_path}: {e}")

def acrcloud_insert_song_to_db(bar_id, song_name, artist_name):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the song already exists for the given bar
        check_query = 'SELECT 1 FROM songs WHERE bar_id = %s AND name = %s AND artist = %s LIMIT 1'
        cursor.execute(check_query, (bar_id, song_name, artist_name))
        result = cursor.fetchone()

        if result:
            print(f"Song '{song_name}' by '{artist_name}' already exists for bar id: {bar_id}, not adding to database.")
        else:
            insert_query = 'INSERT INTO songs (bar_id, name, artist) VALUES (%s, %s, %s)'
            cursor.execute(insert_query, (bar_id, song_name, artist_name))
            conn.commit()
            print(f"Inserted song: '{song_name}' by '{artist_name}' for bar id: {bar_id}")
    except Exception as e:
        print(f"Error inserting song into database: {e}")
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass

def monitor_files():
    base_directory = './static/uploads'  # monitor static/uploads
    # Ensure directory exists
    os.makedirs(base_directory, exist_ok=True)

    while True:
        print("Monitoring files...")  # heartbeat
        try:
            for file_name in os.listdir(base_directory):
                if not file_name.endswith('.wav'):
                    continue

                # Validate and parse filename to extract bar_id
                m = FILENAME_RE.match(file_name)
                if not m:
                    # Skip files that don't match expected naming pattern
                    print(f"Skipping non-matching filename: {file_name}")
                    continue

                bar_id = m.group(1)  # digits before first underscore
                file_path = os.path.join(base_directory, file_name)

                # (Optional) skip files that are still being written: ensure size stable for 1 cycle
                try:
                    size1 = os.path.getsize(file_path)
                    time.sleep(0.2)
                    size2 = os.path.getsize(file_path)
                    if size1 != size2:
                        print(f"File still growing, will retry next cycle: {file_path}")
                        continue
                except FileNotFoundError:
                    # If file disappeared mid-check, skip
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