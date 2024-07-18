import pandas as pd
import psycopg2
import ast

# Database connection details
db_config = {
    'dbname': 'intoit-prod',
    'user': 'postgres',
    'password': 'Anshtheboss1',
    'host': 'intoit-prod.cx2s40qaqixr.us-east-1.rds.amazonaws.com',
}

# Read the CSV file
csv_file_path = '/updated_csv_file_geoparse.csv'
data = pd.read_csv(csv_file_path)

# Define a function to extract latitude and longitude from the geometry column
def extract_lat_lng(geometry):
    try:
        geom_dict = ast.literal_eval(geometry)
        location = geom_dict.get('location', {})
        return location.get('lat', None), location.get('lng', None)
    except (ValueError, SyntaxError):
        return None, None

# Apply the function to the geometry column and update latitude and longitude columns
data['latitude'], data['longitude'] = zip(*data['geometry'].apply(extract_lat_lng))

# Establish a database connection
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

# Update the database records
for index, row in data.iterrows():
    name = row['name']
    latitude = row['latitude']
    longitude = row['longitude']
    # Construct the SQL query
    query = """
    UPDATE bars
    SET latitude = %s, longitude = %s
    WHERE name = %s;
    """
    cursor.execute(query, (latitude, longitude, name))
    print(f"Updated {name} with latitude {latitude} and longitude {longitude}")

# Commit the changes and close the connection
conn.commit()
cursor.close()
conn.close()