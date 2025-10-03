from flask import Flask, request, send_from_directory, jsonify, render_template, abort
import os, re, datetime

app = Flask(__name__)
PORT = 3000
UPLOAD_DIR = os.path.join(os.getcwd(), 'uploads')

# Ensure upload directory exists
if not os.path.exists(UPLOAD_DIR):
    print('Creating uploads directory')
    os.makedirs(UPLOAD_DIR)

# Regex for valid filenames: device (alphanumeric up to 10) + "_" + YYYYMMDD_HHMMSS + ".wav"
VALID_FILE_REGEX = re.compile(r'^[a-zA-Z0-9]{1,10}_[0-9]{8}_[0-9]{6}\.wav$')
# Regex for validating device names
DEVICE_REGEX = re.compile(r'^[a-zA-Z0-9-]{1,32}$')

def cleanup_files():
    """
    Deletes any files that do not follow the naming convention.
    Then, if there are more than 90 valid files, deletes the oldest ones.
    """
    valid_files = []
    for filename in os.listdir(UPLOAD_DIR):
        file_path = os.path.join(UPLOAD_DIR, filename)
        if VALID_FILE_REGEX.match(filename):
            valid_files.append(filename)
        else:
            try:
                os.remove(file_path)
                print(f"Deleted invalid file: {filename}")
            except Exception as e:
                print(f"Error deleting invalid file {filename}: {e}")
    
    # If more than 90 valid files exist, delete the oldest ones
    if len(valid_files) > 90:
        # Extract the timestamp part (YYYYMMDD_HHMMSS) from filename.
        def extract_timestamp(fn):
            # Split into device and timestamp parts
            try:
                device, ts_with_ext = fn.split('_', 1)
                ts, _ = ts_with_ext.split('.')
                return ts  # This format allows lexicographic sorting
            except Exception:
                return ""
        
        valid_files.sort(key=extract_timestamp)
        files_to_delete = valid_files[:-90]
        for filename in files_to_delete:
            try:
                os.remove(os.path.join(UPLOAD_DIR, filename))
                print(f"Deleted old file: {filename}")
            except Exception as e:
                print(f"Error deleting old file {filename}: {e}")

@app.route('/file', methods=['POST'])
def upload_file():
    """
    Expects:
      - Binary data in request.data.
      - Required header: Content-Type and Content-Disposition (with filename present, although we ignore the filename).
      - A required header X-Device-Name (must be alphanumeric, up to 10 characters).
      
    Saves the file as deviceName_TIMESTAMP.wav.
    """
    print('Received POST request to /file')
    print(request.headers)
    
    # Check required headers for file content
    if 'Content-Type' not in request.headers or 'Content-Disposition' not in request.headers:
        print('Missing Content-Type or Content-Disposition header')
        return 'Missing headers', 400

    # Check for device name header
    device_name = request.headers.get('X-Device-Name', '').strip()
    if not device_name or not DEVICE_REGEX.fullmatch(device_name):
        print('Invalid or missing device name')
        return 'Invalid or missing device name', 400

    # Validate Content-Disposition for a filename (even though we ignore it)
    content_disposition = request.headers.get('Content-Disposition')
    if 'filename="' not in content_disposition:
        print('Filename not found in Content-Disposition header')
        return 'Filename missing', 400

    # Generate machine-friendly timestamp for filename
    now = datetime.datetime.now()
    machine_ts = now.strftime("%Y%m%d_%H%M%S")
    new_filename = f"{device_name}_{machine_ts}.wav"
    file_path = os.path.join(UPLOAD_DIR, new_filename)
    print(f"Saving file as: {file_path}")
    
    try:
        with open(file_path, 'wb') as f:
            f.write(request.data)
        print(f"File saved successfully: {new_filename}")
        # Run cleanup after successful upload
        cleanup_files()
        return new_filename, 201
    except Exception as e:
        print('Error saving file:', e)
        return 'Failed to save file', 500

@app.route('/files', methods=['GET'])
def list_files():
    """
    Lists all valid files in the uploads directory.
    The response is a JSON object grouping files by device name.
    Each file entry includes the machine timestamp (from filename),
    a human-friendly timestamp, and the filename.
    """
    files_by_device = {}
    for filename in os.listdir(UPLOAD_DIR):
        if VALID_FILE_REGEX.match(filename):
            try:
                device, ts_with_ext = filename.split('_', 1)
                ts, _ = ts_with_ext.split('.')
                # Convert machine timestamp to human-readable format
                dt = datetime.datetime.strptime(ts, "%Y%m%d%H%M%S") if len(ts) == 14 else datetime.datetime.strptime(ts, "%Y%m%d_%H%M%S")
                human_ts = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception as e:
                print(f"Error parsing filename {filename}: {e}")
                continue
            files_by_device.setdefault(device, []).append({
                "machine_timestamp": ts,
                "human_timestamp": human_ts,
                "filename": filename
            })
    # Optionally sort each device's files by timestamp descending (latest first)
    for device, files in files_by_device.items():
        files.sort(key=lambda x: x["machine_timestamp"], reverse=True)
    return jsonify({"devices": files_by_device})

@app.route('/file/latest', methods=['GET'])
def download_latest_file():
    """
    Finds the latest file (by timestamp, across all devices) and returns it.
    """
    valid_files = []
    for filename in os.listdir(UPLOAD_DIR):
        if VALID_FILE_REGEX.match(filename):
            valid_files.append(filename)
    if not valid_files:
        return "No files available", 404

    def extract_timestamp(fn):
        try:
            _, ts_with_ext = fn.split('_', 1)
            ts, _ = ts_with_ext.split('.')
            return ts
        except Exception:
            return ""
    
    latest_file = max(valid_files, key=extract_timestamp)
    print(f"Latest file is: {latest_file}")
    return send_from_directory(UPLOAD_DIR, latest_file)

# A basic one-page UI using Tailwind CSS
UI_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Device Audio Files</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100">
  <div class="container mx-auto p-4">
    <h1 class="text-2xl font-bold mb-4">Device Audio Files</h1>
    <div class="flex">
      <!-- Left side: File List -->
      <div class="w-1/3 bg-white shadow p-4 mr-4 overflow-y-auto h-screen" id="fileList">
        <!-- File groups will be populated here -->
      </div>
      
    </div>
  </div>
  
</body>
</html>
"""

@app.route('/', methods=['GET'])
def ui():
    return render_template('index.html') 

@app.route('/file/<filename>', methods=['GET'])
def download_file(filename):
    """
    Download a specific file if it exists.
    Only serves files that match the naming convention.
    """
    if not VALID_FILE_REGEX.match(filename):
        print(f"Attempted to download invalid file: {filename}")
        abort(404)
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        abort(404)
    return send_from_directory(UPLOAD_DIR, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=True)
