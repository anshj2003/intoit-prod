from flask import Flask, request, send_from_directory, abort
import os

app = Flask(__name__)
PORT = 8000
UPLOAD_DIR = os.path.join(os.getcwd(), 'uploads')
FIXED_FILENAME = 'sound.wav'

# Ensure upload directory exists
if not os.path.exists(UPLOAD_DIR):
    print('Creating uploads directory')
    os.makedirs(UPLOAD_DIR)

@app.route('/file', methods=['POST'])
def upload_file():
    print('Received POST request to /file')
    print(request.headers)

    # Check for required headers
    if 'Content-Type' not in request.headers or 'Content-Disposition' not in request.headers:
        print('Missing content-type or content-disposition header')
        return 'Missing headers', 400
    
    content_disposition = request.headers['Content-Disposition']
    print(f'Content-Disposition header: {content_disposition}')
    
    # Extract filename (not used since we save as a fixed filename)
    if 'filename="' not in content_disposition:
        print('Filename not found in content-disposition header')
        return 'Filename missing', 400
    
    file_path = os.path.join(UPLOAD_DIR, FIXED_FILENAME)
    print(f'Saving file as: {file_path}')
    
    try:
        # Write the file, replacing it if it already exists
        with open(file_path, 'wb') as f:
            f.write(request.data)
        print(f'File saved successfully: {file_path}')
        return FIXED_FILENAME, 201
    except Exception as e:
        print('Error saving file:', e)
        return 'Failed to save file', 500

@app.route('/file/<filename>', methods=['GET'])
def get_file(filename):
    print(f'Received GET request to /file/{filename}')
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    if not os.path.exists(file_path):
        print(f'File not found: {file_path}')
        return 'File not found', 404
    
    print(f'File found, sending: {file_path}')
    return send_from_directory(UPLOAD_DIR, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=True)
