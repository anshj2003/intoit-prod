import pandas as pd
import psycopg2

# Database configuration
db_config = {
    'dbname': 'intoit-prod',
    'user': 'postgres',
    'password': 'Anshtheboss1',
    'host': 'ec2-100-29-142-252.compute-1.amazonaws.com',
}

# Read the CSV file containing generated clean descriptions
csv_path = 'places_cleaned_generated_descriptions.csv'
data = pd.read_csv(csv_path)

# Connect to the PostgreSQL database
conn = psycopg2.connect(
    dbname=db_config['dbname'],
    user=db_config['user'],
    password=db_config['password'],
    host=db_config['host']
)
cursor = conn.cursor()

# Loop through each row in the CSV file
for index, row in data.iterrows():
    name = row['name']
    description = row['description']

    # Check if the description is missing or "Description not found"
    if description and description != "Description not found":
        # Update the bars table with the new description
        update_query = """
        UPDATE bars
        SET description = %s
        WHERE name = %s AND (description IS NULL OR description = 'Description not found')
        """
        cursor.execute(update_query, (description, name))
        print(f"Updated description for {name}")

# Commit the changes and close the connection
conn.commit()
cursor.close()
conn.close()

print("Database update complete.")
