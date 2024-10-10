import time
import os
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

# Timestamp to manage 2-minute wait after high score
next_api_call_time = 0

def acrcloud_process_wav_file(bar_id, file_path):
    global next_api_call_time
    try:
        # Read .wav file content
        with open(file_path, 'rb') as f:
            wav_data = f.read()
        sample_bytes = os.path.getsize(file_path)
        
        current_time = time.time()
        # Check if we are in a waiting period before making another API call
        if current_time < next_api_call_time:
            print(f"Skipping API call for file: {file_path} due to 2-minute wait period.")
        else:
            # Prepare the request to ACRCloud
            http_method = "POST"
            http_uri = "/v1/identify"
            data_type = "audio"
            signature_version = "1"
            timestamp = str(int(time.time()))

            string_to_sign = f"{http_method}\n{http_uri}\n{acr_config['access_key']}\n{data_type}\n{signature_version}\n{timestamp}"
            sign = base64.b64encode(hmac.new(acr_config['access_secret'].encode('ascii'), string_to_sign.encode('ascii'), digestmod=hashlib.sha1).digest()).decode('ascii')

            files = [
                ('sample', (file_path, open(file_path, 'rb'), 'audio/wav'))
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
            response = requests.post(requrl, files=files, data=data)
            response.encoding = "utf-8"
            print(f"API Response Code: {response.status_code}")
            print(f"API Response: {response.text}")
            result = response.json()
            
            # Check if the song was recognized and the score is greater than 30
            if result and 'metadata' in result and 'music' in result['metadata']:
                music_info = result['metadata']['music'][0]
                score = music_info.get('score', 0)
                if score > 30:
                    song_name = music_info.get('title', 'Unknown')
                    artist_name = music_info.get('artists', [{}])[0].get('name', 'Unknown')
                    
                    # Insert song into the database if not already present
                    acrcloud_insert_song_to_db(bar_id, song_name, artist_name)
                    print("Waiting for 2 minutes before making the next API call.")
                    next_api_call_time = current_time + 120  # Set the next allowed API call time
                else:
                    print(f"Score is less than 30 for file: {file_path}, not adding to database.")
            else:
                print(f"No song recognized for file: {file_path}")
    except Exception as e:
        print(f"Error processing WAV file: {e}")
    finally:
        # Delete the file after processing, regardless of the outcome
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"File {file_path} has been deleted.")

def acrcloud_insert_song_to_db(bar_id, song_name, artist_name):
    try:
        # Connect to the PostgreSQL database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if the song already exists for the given bar
        check_query = 'SELECT * FROM songs WHERE bar_id = %s AND name = %s AND artist = %s'
        cursor.execute(check_query, (bar_id, song_name, artist_name))
        result = cursor.fetchone()
        
        if result:
            print(f"Song '{song_name}' by '{artist_name}' already exists for bar id: {bar_id}, not adding to database.")
        else:
            # Insert the song information into the songs table
            insert_query = 'INSERT INTO songs (bar_id, name, artist) VALUES (%s, %s, %s)'
            cursor.execute(insert_query, (bar_id, song_name, artist_name))
            
            # Commit the transaction and close the connection
            conn.commit()
            print(f"Inserted song: '{song_name}' by '{artist_name}' for bar id: {bar_id}")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error inserting song into database: {e}")

def monitor_files():
    while True:
        print("Monitoring files...")  # Debug statement to indicate the function is running
        base_directory = './files'
        for bar_id in os.listdir(base_directory):
            bar_directory = os.path.join(base_directory, bar_id)
            if os.path.isdir(bar_directory):
                for file_name in os.listdir(bar_directory):
                    if file_name.endswith('.wav'):
                        file_path = os.path.join(bar_directory, file_name)
                        try:
                            acrcloud_process_wav_file(bar_id, file_path)
                        except Exception as e:
                            print(f"Error processing file {file_path}: {e}")
        time.sleep(10)

if __name__ == '__main__':
    # Start monitoring files
    monitor_files()