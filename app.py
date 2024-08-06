from flask import Flask, request, redirect, session, jsonify, url_for
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import os
from datetime import date, time, datetime
import time
from urllib.parse import urlencode
import json
import openai
import math
from dotenv import load_dotenv
import threading
import schedule
import pandas as pd

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)



CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')

OPENAI_KEY = os.getenv('OPENAI_KEY')

HOST = os.getenv('HOST')
DATABASE = os.getenv('DATABASE')
DB_USER = os.getenv('DB_USER')
PASSWORD = os.getenv('PASSWORD')



def get_db_connection():
    conn = psycopg2.connect(
        host=HOST,
        database=DATABASE,
        user=DB_USER,
        password=PASSWORD
    )
    return conn

# BAR REDIRECT

@app.route('/barredirect/<int:bar_id>')
def bar_redirect(bar_id):
    custom_url_scheme = f"intoit.ansh://bar/{bar_id}"
    return redirect(custom_url_scheme)


# AI SEARCH 

@app.route('/api/ai_search', methods=['POST'])
def ai_search():
    data = request.json
    query = data.get('query', '')
    email = data.get('email', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch user's location from the database
    cursor.execute('SELECT location FROM users WHERE email = %s', (email,))
    result = cursor.fetchone()
    if not result:
        cursor.close()
        conn.close()
        return jsonify({'error': 'User not found'}), 404

    location = result[0]
    print(f"User's location: {location}")

    # Combine query and location
    combined_query = f"{query} near {location}"

    print(combined_query)

    # Call OpenAI API
    openai.api_key = OPENAI_KEY

    response = openai.chat.completions.create(
        model="ft:gpt-3.5-turbo-1106:personal:first-intoit:9rfZxmSO",
        messages=[
            {"role": "system", "content": "You are a nightlife guru who recommends bars and clubs based on users' desires."},
            {"role": "user", "content": f"Based on the following query, suggest 3 bars near me. Format must be 'bar1', 'bar2', 'bar3' no additional punctuation. Here is the query: {combined_query}"}
        ],
        max_tokens=150
    )

    suggestions = response.choices[0].message.content
    suggested_bars = [suggestion.strip() for suggestion in suggestions.split(',') if suggestion.strip()]

    print("Pre database check:", suggested_bars)

    # Use ILIKE for case-insensitive matching and pattern matching for partial matches
    placeholder = ', '.join(['%s'] * len(suggested_bars))
    cursor.execute(f'SELECT * FROM bars WHERE name ILIKE ANY(ARRAY[{placeholder}]) LIMIT 1', tuple([f'%{bar}%' for bar in suggested_bars]))
    bars = cursor.fetchall()

    if not bars:
        cursor.close()
        conn.close()
        return jsonify({'error': 'This happens sometimes, try a different query'}), 400

    bar = bars[0]
    bar_dict = {
        "id": bar[0],
        "name": bar[1],
        "address": bar[2],
        "phone_number": bar[3],
        "description": bar[6],
        "vibe": float(bar[7]) if bar[7] is not None else None,
        "type": bar[8],
        "lineWaitTime": bar[9],
        "price_signs": bar[15],
        "price_num": bar[16],
        "photo": bar[18],
        "avgMaleAge": bar[10],
        "avgFemaleAge": bar[11],
        "percentSingleMen": bar[12],
        "percentSingleWomen": bar[13],
        "latitude": bar[23], 
        "longitude": bar[24],
        "djsInstagram": bar[25],
        "ticketLink": bar[26],
        "enableRequests": bar[27],
        "website_link": bar[28],
        "reservation_link": bar[29],
        "howCrowded": bar[30]
    }

    # Update the AI recommendations database
    import time
    current_time = int(time.time())
    cursor.execute('''
        INSERT INTO ai_recommendations (query, bars, last_updated)
        VALUES (%s, %s, %s)
        ON CONFLICT (query) DO UPDATE
        SET bars = EXCLUDED.bars,
            last_updated = EXCLUDED.last_updated
    ''', (query, json.dumps([bar_dict]), current_time))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify([bar_dict])





    

# SUBMIT NEARBY FORM

@app.route('/api/update_bar', methods=['POST'])
def update_bar():
    data = request.json
    bar_id = data.get('bar_id')
    vibe = data.get('vibe')
    line_length = data.get('line_length')
    how_crowded = data.get('how_crowded')

    if not bar_id or line_length is None:
        return jsonify({'error': 'bar_id and line_length are required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    updates = []
    params = []

    if vibe is not None:
        updates.append('vibe = %s')
        params.append(vibe)

    if how_crowded is not None:
        updates.append('how_crowded = %s')
        params.append(how_crowded)

    updates.append('line_wait_time = %s')
    params.append(line_length)

    update_query = f"UPDATE bars SET {', '.join(updates)} WHERE id = %s"
    params.append(bar_id)

    cursor.execute(update_query, params)
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({'status': 'Bar information updated successfully!'}), 200



# USERNAME VALIDATION AND SETTING

@app.route('/check_username', methods=['POST'])
def check_username():
    data = request.json
    username = data.get('username')

    if not username:
        return jsonify({'status': 'Username is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
    existing_user = cursor.fetchone()

    cursor.close()
    conn.close()

    if existing_user:
        return jsonify({'status': 'Username is already taken'}), 400
    else:
        return jsonify({'status': 'Username is available'}), 200










# BAR OWNER SPOTIFY STUFF



@app.route('/api/spotify_token', methods=['POST'])
def save_spotify_token():
    data = request.json
    token = data.get('token')
    bar_id = data.get('bar_id')

    if not token or not bar_id:
        return 'Missing token or bar_id', 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE bars SET spotify_token = %s WHERE id = %s', (token, bar_id))
    conn.commit()
    cursor.close()
    conn.close()

    return 'Token saved successfully', 200


@app.route('/api/spotify_callback')
def spotify_callback():
    code = request.args.get('code')
    if code is None:
        return 'Authorization code not provided', 400

    token_url = 'https://accounts.spotify.com/api/token'
    body_params = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(token_url, data=body_params, headers=headers)
    
    if response.status_code != 200:
        return 'Failed to fetch token', 400

    token_data = response.json()
    access_token = token_data['access_token']

    bar_id = request.args.get('bar_id')
    if not bar_id:
        return 'Bar ID not provided', 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE bars SET spotify_token = %s WHERE id = %s', (access_token, bar_id))
    conn.commit()
    cursor.close()
    conn.close()

    return 'Spotify token saved successfully', 200


@app.route('/api/bars/<int:bar_id>/playlists')
def fetch_playlists(bar_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT spotify_token FROM bars WHERE id = %s', (bar_id,))
    bar = cursor.fetchone()
    cursor.close()
    conn.close()

    if not bar or not bar['spotify_token']:
        return jsonify({'error': 'Spotify token not found'}), 400

    spotify_token = bar['spotify_token']
    headers = {
        'Authorization': f'Bearer {spotify_token}'
    }
    response = requests.get('https://api.spotify.com/v1/me/playlists', headers=headers)

    if response.status_code != 200:
        return jsonify({'error': 'Failed to fetch playlists'}), 400

    playlists = response.json().get('items', [])
    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear existing songs for the bar
    cursor.execute('DELETE FROM songs WHERE bar_id = %s', (bar_id,))
    
    # Clear existing playlists for the bar
    cursor.execute('DELETE FROM playlists WHERE bar_id = %s', (bar_id,))

    for playlist in playlists:
        cursor.execute('''
            INSERT INTO playlists (bar_id, name, spotify_id) VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
        ''', (bar_id, playlist['name'], playlist['id']))

    conn.commit()
    cursor.close()
    conn.close()
    print(playlists)
    return jsonify(response.json().get('items', []))








@app.route('/api/bars/<int:bar_id>/playlists/<string:playlist_id>/songs')
def fetch_songs(bar_id, playlist_id):
    print(f"Fetching songs for playlist_id: {playlist_id} and bar_id: {bar_id}")

    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the playlist exists using spotify_id
    cursor.execute('SELECT id FROM playlists WHERE spotify_id = %s', (playlist_id,))
    playlist = cursor.fetchone()
    print(f"Database result for playlist: {playlist}")

    if not playlist:
        print(f"Playlist with ID {playlist_id} not found.")
        cursor.close()
        conn.close()
        return jsonify({'error': 'Playlist not found'}), 404

    # Get the internal playlist id
    internal_playlist_id = playlist[0]

    # Fetch the Spotify token for the bar
    cursor.execute('SELECT spotify_token FROM bars WHERE id = %s', (bar_id,))
    bar = cursor.fetchone()
    print(f"Database result for bar: {bar}")

    # Check if the token is found
    if not bar or not bar[0]:
        print("Spotify token not found for the bar.")
        cursor.close()
        conn.close()
        return jsonify({'error': 'Spotify token not found'}), 400

    spotify_token = bar[0]
    print(f"Using Spotify token: {spotify_token}")

    # Use the token to fetch songs from the Spotify API
    headers = {
        'Authorization': f'Bearer {spotify_token}'
    }
    response = requests.get(f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks', headers=headers)

    # Check the response status
    if response.status_code != 200:
        print(f"Failed to fetch songs, status code: {response.status_code}")
        cursor.close()
        conn.close()
        return jsonify({'error': 'Failed to fetch songs'}), 400

    tracks = response.json().get('items', [])
    print(f"Tracks fetched: {tracks}")

    # Prepare the songs list
    songs = []
    for item in tracks:
        track = item['track']
        song = {
            'id': track['id'],
            'name': track['name'],
            'artist': ', '.join(artist['name'] for artist in track['artists']),
            'albumArt': track['album']['images'][0]['url'] if track['album']['images'] else None,
            'spotify_url': track['external_urls']['spotify']
        }
        print(f"Song fetched: {song}")
        songs.append(song)

    # Clear existing songs for the bar's current playlist
    cursor.execute('DELETE FROM songs WHERE bar_id = %s', (bar_id,))
    
    # Insert or update the songs in the database using the internal playlist id and bar_id
    for song in songs:
        cursor.execute('''
            INSERT INTO songs (playlist_id, name, artist, album_art, spotify_url, bar_id) 
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET 
            name = EXCLUDED.name, 
            artist = EXCLUDED.artist, 
            album_art = EXCLUDED.album_art,
            spotify_url = EXCLUDED.spotify_url,
            bar_id = EXCLUDED.bar_id
        ''', (internal_playlist_id, song['name'], song['artist'], song['albumArt'], song['spotify_url'], bar_id))
        print(f"Inserted/Updated song: {song}")

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify(songs)











@app.route('/api/bars/<int:bar_id>/songs')
def get_songs_for_bar(bar_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.id, s.name, s.artist, s.album_art, s.spotify_url
        FROM songs s
        WHERE s.bar_id = %s
    ''', (bar_id,))
    songs = cursor.fetchall()
    cursor.close()
    conn.close()

    song_list = [
        {
            'id': str(song[0]),  # Convert id to string
            'name': song[1],
            'artist': song[2],
            'albumArt': song[3],
            'spotifyUrl': song[4]  # Include the spotifyUrl in the response
        }
        for song in songs
    ]
    
    return jsonify(song_list)



















# USER ONBOARDING STUFF


@app.route('/create_user', methods=['POST'])
def create_user():
    data = request.json
    identifier = data['email']
    name = data.get('name')  # Get the name from the request

    if not name:
        return jsonify({"error": "Name is required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the user already exists
    cursor.execute('SELECT * FROM users WHERE email = %s', (identifier,))
    user = cursor.fetchone()

    if user:
        return jsonify({'status': 'User already exists'}), 200

    cursor.execute(
        'INSERT INTO users (email, name) VALUES (%s, %s)',
        (identifier, name)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"status": "User created successfully!"}), 201





@app.route('/check_user_birthday', methods=['POST'])
def check_user_birthday():
    data = request.json
    email = data['email']
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT birthday, gender, relationship_status FROM users WHERE email = %s', (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if user and user['birthday'] and user['gender'] and user['relationship_status']:
        return jsonify({'has_info': True}), 200
    else:
        return jsonify({'has_info': False}), 200



@app.route('/update_user', methods=['POST'])
def update_user():
    data = request.json
    email = data.get('email')
    birthday = data.get('birthday')
    gender = data.get('gender')
    relationship_status = data.get('relationship_status')
    location = data.get('location')
    username = data.get('username')

    if not email:
        return jsonify({'status': 'Email is required'}), 400
    
    print(f"Received data for update: email={email}, birthday={birthday}, gender={gender}, relationship_status={relationship_status}, location={location}, username={username}")
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # Build the update query dynamically based on which fields are provided
    updates = []
    params = []

    if birthday:
        updates.append('birthday = %s')
        params.append(birthday)
    if gender:
        updates.append('gender = %s')
        params.append(gender)
    if relationship_status:
        updates.append('relationship_status = %s')
        params.append(relationship_status)
    if location:
        updates.append('location = %s')
        params.append(location)
    if username:
        updates.append('username = %s')
        params.append(username)

    if not updates:
        return jsonify({'status': 'No fields to update'}), 400

    update_query = f"UPDATE users SET {', '.join(updates)} WHERE email = %s"
    params.append(email)

    print(f"Executing query: {update_query} with params: {params}")
    cursor.execute(update_query, params)
    conn.commit()
    print("Commit successful")
    cursor.close()
    conn.close()
    return jsonify({'status': 'User information updated successfully!'}), 200




# DELETE USER

@app.route('/delete_user', methods=['POST'])
def delete_user():
    data = request.json
    email = data['email']

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Start a transaction
        conn.autocommit = False

        # Delete from votes
        cursor.execute('DELETE FROM votes WHERE user_email = %s', (email,))

        # Delete from song_requests
        cursor.execute('DELETE FROM song_requests WHERE user_email = %s', (email,))

        # Delete from user_feedback
        cursor.execute('DELETE FROM user_feedback WHERE user_email = %s', (email,))

        # Get user_id from users table
        cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        if not user:
            raise Exception("User not found")
        user_id = user[0]

        # Delete from been_there
        cursor.execute('DELETE FROM been_there WHERE user_id = %s', (user_id,))

        # Delete from liked
        cursor.execute('DELETE FROM liked WHERE user_id = %s', (user_id,))

        # Delete from want_to_go
        cursor.execute('DELETE FROM want_to_go WHERE user_id = %s', (user_id,))

        # Finally, delete from users
        cursor.execute('DELETE FROM users WHERE email = %s', (email,))

        # Commit the transaction
        conn.commit()
        return jsonify({"status": "User deleted successfully!"}), 200

    except Exception as e:
        # Rollback the transaction on error
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()




@app.route('/api/bars', methods=['GET'])
def get_bars():
    page = int(request.args.get('page', 1))
    per_page = 30
    #per_page = int(request.args.get('per_page', 30))
    search = request.args.get('search', '')
    selected_price = request.args.get('selected_price', '')
    selected_distance = float(request.args.get('selected_distance', 0))
    latitude = float(request.args.get('latitude', 0))
    longitude = float(request.args.get('longitude', 0))
    selected_genres = request.args.getlist('selected_genres[]')

    offset = (page - 1) * per_page

    # Haversine formula to calculate distance
    haversine = """
    3959 * acos(
        cos(radians(%s)) * cos(radians(b.latitude)) *
        cos(radians(b.longitude) - radians(%s)) +
        sin(radians(%s)) * sin(radians(b.latitude))
    )
    """

    query = f"""
    SELECT b.*, {haversine} AS distance
    FROM bars b
    LEFT JOIN playlists p ON b.id = p.bar_id
    LEFT JOIN songs s ON p.id = s.playlist_id
    WHERE (b.name ILIKE %s OR b.description ILIKE %s OR b.address ILIKE %s
           OR s.name ILIKE %s OR s.artist ILIKE %s)
    AND (%s = '' OR b.price_signs = %s)
    AND (%s = 0 OR {haversine} < %s)
    """

    params = [
        latitude, longitude, latitude,
        f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%",
        selected_price, selected_price,
        selected_distance, latitude, longitude, latitude, selected_distance
    ]

    if selected_genres:
        genre_conditions = " OR ".join("b.venue_types ILIKE %s" for _ in selected_genres)
        query += f" AND ({genre_conditions})"
        params.extend(f"%{genre}%" for genre in selected_genres)

    query += f" ORDER BY distance LIMIT %s OFFSET %s"
    params.extend([per_page, offset])

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(query, params)
    bars = cursor.fetchall()

    # Fetch songs for each bar
    for bar in bars:
        bar_id = bar['id']
        cursor.execute("""
            SELECT s.id::text, s.name, s.artist, s.album_art, s.spotify_url
            FROM songs s
            JOIN playlists p ON s.playlist_id = p.id
            WHERE p.bar_id = %s
        """, (bar_id,))
        songs = cursor.fetchall()
        bar['songs'] = songs

    cursor.close()
    conn.close()

    return jsonify(bars)






@app.route('/api/nearby_bars', methods=['GET'])
def get_nearby_bars():
    latitude = float(request.args.get('latitude'))
    longitude = float(request.args.get('longitude'))
    distance_limit = 15  # meters

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371e3  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    query = """
    SELECT id, name, address, latitude, longitude
    FROM bars
    """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(query)
    bars = cursor.fetchall()

    nearby_bars = []
    for bar in bars:
        if bar['latitude'] is None or bar['longitude'] is None:
            continue
        distance = haversine(latitude, longitude, bar['latitude'], bar['longitude'])
        if distance < distance_limit:
            bar['distance'] = distance
            nearby_bars.append(bar)

    # Sort by distance
    nearby_bars.sort(key=lambda x: x['distance'])

    cursor.close()
    conn.close()

    print(nearby_bars)

    return jsonify(nearby_bars)






@app.route('/api/bars/<int:id>', methods=['GET'])
def get_bar(id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT * FROM bars WHERE id = %s', (id,))
    bar = cursor.fetchone()
    
    if bar:
        cursor.execute('SELECT * FROM events WHERE bar_id = %s', (id,))
        events = cursor.fetchall()
        bar['events'] = events

    cursor.close()
    conn.close()

    if bar:
        return jsonify(bar)
    return jsonify({"error": "Bar not found"}), 404



@app.route('/api/events', methods=['GET'])
def get_events():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT * FROM events')
    events = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(events)

@app.route('/api/events/<int:id>', methods=['GET'])
def get_event(id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT * FROM events WHERE id = %s', (id,))
    event = cursor.fetchone()
    cursor.close()
    conn.close()
    if event:
        return jsonify(event)
    return jsonify({"error": "Event not found"}), 404

@app.route('/api/bars/<int:id>/events', methods=['GET'])
def get_bar_events(id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT * FROM events WHERE bar_id = %s', (id,))
    events = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(events)



@app.route('/api/song_requests', methods=['POST'])
def create_song_request():
    data = request.json
    user_email = data['user_email']
    bar_id = data['bar_id']
    event_id = data.get('event_id', None)  # Optional event_id
    song_name = data['song_name']
    artist_name = data['artist_name']
    album_cover_url = data.get('album_cover_url', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the song has already been requested by this user at this bar/event
    cursor.execute(
        'SELECT * FROM song_requests WHERE user_email = %s AND bar_id = %s AND (event_id = %s OR event_id IS NULL) AND song_name = %s AND artist_name = %s',
        (user_email, bar_id, event_id, song_name, artist_name)
    )
    existing_request = cursor.fetchone()

    if existing_request:
        cursor.close()
        conn.close()
        return jsonify({"status": "Song has already been requested"}), 400

    cursor.execute(
        'INSERT INTO song_requests (user_email, bar_id, event_id, song_name, artist_name, album_cover_url) VALUES (%s, %s, %s, %s, %s, %s)',
        (user_email, bar_id, event_id, song_name, artist_name, album_cover_url)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"status": "Song request created successfully!"}), 201




@app.route('/api/song_requests/<int:bar_id>', methods=['GET'])
def get_song_requests(bar_id):
    event_id = request.args.get('event_id', None)
    today = date.today()

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if event_id:
        # Get song requests for the specific event
        cursor.execute('SELECT * FROM song_requests WHERE bar_id = %s AND (event_id = %s OR (event_id IS NULL AND request_time::date = %s)) ORDER BY request_time DESC', (bar_id, event_id, today))
    else:
        # Get song requests for the bar (not tied to an event)
        cursor.execute('SELECT * FROM song_requests WHERE bar_id = %s AND event_id IS NULL ORDER BY request_time DESC', (bar_id,))

    song_requests = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(song_requests)

@app.route('/api/song_requests/<int:request_id>/upvote', methods=['POST'])
def upvote_song_request(request_id):
    data = request.json
    user_email = data['user_email']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the user has already voted on this request
    cursor.execute('SELECT * FROM votes WHERE user_email = %s AND request_id = %s', (user_email, request_id))
    existing_vote = cursor.fetchone()

    if existing_vote:
        cursor.close()
        conn.close()
        return jsonify({"status": "User has already voted on this request"}), 400

    # Check if the user is the one who requested the song
    cursor.execute('SELECT user_email FROM song_requests WHERE id = %s', (request_id,))
    request = cursor.fetchone()

    if request and request['user_email'] == user_email:
        cursor.close()
        conn.close()
        return jsonify({"status": "User cannot vote on their own request"}), 400

    cursor.execute('UPDATE song_requests SET upvotes = upvotes + 1 WHERE id = %s', (request_id,))
    cursor.execute('INSERT INTO votes (user_email, request_id, vote_type) VALUES (%s, %s, %s)', (user_email, request_id, 'upvote'))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"status": "Upvoted successfully!"})

@app.route('/api/song_requests/<int:request_id>/downvote', methods=['POST'])
def downvote_song_request(request_id):
    data = request.json
    user_email = data['user_email']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the user has already voted on this request
    cursor.execute('SELECT * FROM votes WHERE user_email = %s AND request_id = %s', (user_email, request_id))
    existing_vote = cursor.fetchone()

    if existing_vote:
        cursor.close()
        conn.close()
        return jsonify({"status": "User has already voted on this request"}), 400

    # Check if the user is the one who requested the song
    cursor.execute('SELECT user_email FROM song_requests WHERE id = %s', (request_id,))
    request = cursor.fetchone()

    if request and request['user_email'] == user_email:
        cursor.close()
        conn.close()
        return jsonify({"status": "User cannot vote on their own request"}), 400

    cursor.execute('UPDATE song_requests SET downvotes = downvotes + 1 WHERE id = %s', (request_id,))
    cursor.execute('INSERT INTO votes (user_email, request_id, vote_type) VALUES (%s, %s, %s)', (user_email, request_id, 'downvote'))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"status": "Downvoted successfully!"})






# BEEN THERE, LIKED, WANT TO GO



@app.route('/add_to_list', methods=['POST'])
def add_to_list():
    data = request.json
    email = data.get('email')
    bar_id = data.get('bar_id')
    list_type = data.get('list_type')
    rating = data.get('rating')
    comments = data.get('comments')

    if not email or not bar_id or not list_type:
        return jsonify({'status': 'Email, Bar ID, and List Type are required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Get user ID from email
    cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
    user = cursor.fetchone()

    if not user:
        return jsonify({'status': 'User not found'}), 404

    user_id = user['id']

    # Check if the bar already exists in the list
    if list_type == 'been_there':
        cursor.execute(
            'SELECT * FROM been_there WHERE user_id = %s AND bar_id = %s',
            (user_id, bar_id)
        )
    elif list_type == 'liked':
        cursor.execute(
            'SELECT * FROM liked WHERE user_id = %s AND bar_id = %s',
            (user_id, bar_id)
        )
    elif list_type == 'want_to_go':
        cursor.execute(
            'SELECT * FROM want_to_go WHERE user_id = %s AND bar_id = %s',
            (user_id, bar_id)
        )
    else:
        return jsonify({'status': 'Invalid list type'}), 400

    existing_entry = cursor.fetchone()

    if existing_entry:
        return jsonify({'status': f'This bar is already in your {list_type} list'}), 400

    # Insert into the appropriate list table
    if list_type == 'been_there':
        cursor.execute(
            'INSERT INTO been_there (user_id, bar_id, rating, comments) VALUES (%s, %s, %s, %s)',
            (user_id, bar_id, rating, comments)
        )
    elif list_type == 'liked':
        cursor.execute(
            'INSERT INTO liked (user_id, bar_id) VALUES (%s, %s)',
            (user_id, bar_id)
        )
    elif list_type == 'want_to_go':
        cursor.execute(
            'INSERT INTO want_to_go (user_id, bar_id) VALUES (%s, %s)',
            (user_id, bar_id)
        )

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'status': f'Added to {list_type} list successfully!'}), 200




@app.route('/get_been_there', methods=['GET'])
def get_been_there():
    email = request.args.get('email')
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute('''
        SELECT b.id, b.name, b.address, b.photo, bt.rating, bt.comments
        FROM been_there bt
        JOIN bars b ON bt.bar_id = b.id
        JOIN users u ON bt.user_id = u.id
        WHERE u.email = %s
    ''', (email,))
    
    bars = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify(bars)



@app.route('/get_liked', methods=['GET'])
def get_liked():
    email = request.args.get('email')
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute('''
        SELECT b.id, b.name, b.address, b.photo
        FROM liked l
        JOIN bars b ON l.bar_id = b.id
        JOIN users u ON l.user_id = u.id
        WHERE u.email = %s
    ''', (email,))
    
    bars = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify(bars)


@app.route('/get_want_to_go', methods=['GET'])
def get_want_to_go():
    email = request.args.get('email')
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute('''
        SELECT b.id, b.name, b.address, b.photo
        FROM want_to_go wtg
        JOIN bars b ON wtg.bar_id = b.id
        JOIN users u ON wtg.user_id = u.id
        WHERE u.email = %s
    ''', (email,))
    
    bars = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify(bars)



@app.route('/remove_from_list', methods=['POST'])
def remove_from_list():
    data = request.json
    email = data.get('email')
    bar_id = data.get('bar_id')
    list_type = data.get('list_type')

    if not email or not bar_id or not list_type:
        return jsonify({'status': 'Missing required fields'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get user_id from email
    cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
    user_id = cursor.fetchone()

    if not user_id:
        return jsonify({'status': 'User not found'}), 404


    if list_type == 'been_there':
        cursor.execute('DELETE FROM been_there WHERE user_id = %s AND bar_id = %s', (user_id, bar_id))
    elif list_type == 'liked':
        cursor.execute('DELETE FROM liked WHERE user_id = %s AND bar_id = %s', (user_id, bar_id))
    elif list_type == 'want_to_go':
        cursor.execute('DELETE FROM want_to_go WHERE user_id = %s AND bar_id = %s', (user_id, bar_id))
    else:
        return jsonify({'status': 'Invalid list type'}), 400

    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'status': 'Bar removed from list successfully!'}), 200



# BAR OWNER SIDE

@app.route('/api/owned_bars', methods=['GET'])
def get_owned_bars():
    email = request.args.get('email')
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT * FROM bars WHERE owner_email = %s', (email,))
    bars = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(bars)


@app.route('/validate_passcode', methods=['POST'])
def validate_passcode():
    data = request.json
    bar_id = data['bar_id']
    passcode = data['passcode']
    user_email = data['user_email']  # Get the user email from the request data
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT * FROM bars WHERE id = %s AND passcode = %s', (bar_id, passcode))
    bar = cursor.fetchone()
    
    if bar:
        cursor.execute('UPDATE bars SET owner_email = %s WHERE id = %s', (user_email, bar_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'status': 'Passcode is valid', 'bar': bar}), 200
    else:
        cursor.close()
        conn.close()
        return jsonify({'status': 'Passcode is invalid'}), 400





# UPDATE BAR DETAILS


@app.route('/api/update_bar_detail/<int:bar_id>', methods=['PUT'])
def update_bar_detail(bar_id):
    data = request.json
    field_map = {
        "description": "description",
        "phone_number": "phone_number",
        "djs_instagram": "djs_instagram",
        "ticket_link": "ticket_link",
        "price_num": "price_num"
    }
    
    updates = []
    params = []
    
    for key, field in field_map.items():
        if key in data:
            if data[key] == "" or data[key] is None:
                updates.append(f"{field} = NULL")
            else:
                if key == "price_num":
                    try:
                        # Validate that price_num is a valid double precision number
                        price_num = float(data[key])
                        updates.append(f"{field} = %s")
                        params.append(price_num)
                    except ValueError:
                        return jsonify({"error": f"Invalid value for {key}"}), 400
                else:
                    updates.append(f"{field} = %s")
                    params.append(data[key])
    
    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400
    
    query = f"UPDATE bars SET {', '.join(updates)} WHERE id = %s"
    params.append(bar_id)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, tuple(params))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({"status": "Bar details updated successfully"})



@app.route('/api/update_enable_requests/<int:bar_id>', methods=['PUT'])
def update_enable_requests(bar_id):
    data = request.json
    enable_requests = data.get('enable_requests')

    if enable_requests is None:
        return jsonify({'error': 'enable_requests field is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE bars SET enable_requests = %s WHERE id = %s', (enable_requests, bar_id))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'status': 'enable_requests updated successfully'})








# FEED VIEW FEEDBACK

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    email = data.get('email')
    feedback = data.get('feedback')
    comment = data.get('comment')

    if not email or feedback not in ['yes', 'neutral', 'no']:
        return jsonify({'error': 'Invalid input'}), 400

    yes = 1 if feedback == 'yes' else 0
    neutral = 1 if feedback == 'neutral' else 0
    no = 1 if feedback == 'no' else 0

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO user_feedback (user_email, yes, neutral, no, comment)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_email) 
        DO UPDATE SET 
            yes = EXCLUDED.yes,
            neutral = EXCLUDED.neutral,
            no = EXCLUDED.no,
            comment = EXCLUDED.comment,
            created_at = CURRENT_TIMESTAMP
    ''', (email, yes, neutral, no, comment))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'status': 'Feedback submitted successfully'}), 200

@app.route('/api/feedback/<email>', methods=['GET'])
def get_feedback(email):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT * FROM user_feedback WHERE user_email = %s', (email,))
    feedback = cursor.fetchone()
    cursor.close()
    conn.close()

    if feedback:
        return jsonify(feedback)
    return jsonify({'error': 'Feedback not found'}), 404



# SOCIAL PART

# ADD FRIENDS

@app.route('/api/users', methods=['GET'])
def get_users():
    search = request.args.get('search', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 30
    offset = (page - 1) * per_page

    # If the search query is empty, return an empty list
    if not search:
        return jsonify([])

    query = """
    SELECT id, email, name, username FROM users
    WHERE name ILIKE %s OR username ILIKE %s
    ORDER BY name ASC
    LIMIT %s OFFSET %s
    """
    
    params = [f"%{search}%", f"%{search}%", per_page, offset]
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(query, params)
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify(users)




if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
