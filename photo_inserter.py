import pandas as pd
import psycopg2

# Database connection details
db_config = {
    'dbname': 'intoit-prod',
    'user': 'postgres',
    'password': 'Anshtheboss1',
    'host': 'intoit-prod.cx2s40qaqixr.us-east-1.rds.amazonaws.com',
}

# Read the CSV file
csv_file_path = '/Users/anshjhaveri/downloads/places_with_images.csv'
data = pd.read_csv(csv_file_path)

# Establish a database connection
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

# Update the database records
for index, row in data.iterrows():
    name = row['name']
    photo = row['photo']
    # Construct the SQL query
    query = """
    UPDATE bars
    SET photo = %s
    WHERE name = %s;
    """
    cursor.execute(query, (photo, name))
    print(f"Updated {name} with photo {photo}")

# Commit the changes and close the connection
conn.commit()
cursor.close()
conn.close()