import pandas as pd
import psycopg2
import re
import numpy as np

# Database connection details
db_config = {
    'dbname': 'nightlife_st',
    'user': 'postgres',
    'password': 'Anshtheboss1',
    'host': 'ec2-3-229-18-161.compute-1.amazonaws.com',
}

# Read the CSV file
csv_file_path = '/Users/anshjhaveri/Downloads/popular_times_database.csv'
data = pd.read_csv(csv_file_path)

# Function to remove non-numerical characters from phone number
def clean_phone_number(phone_number):
    if isinstance(phone_number, str):  # Ensure it's a string before cleaning
        cleaned = re.sub(r'\D', '', phone_number)
        return cleaned if cleaned else None
    return None

# Establish a database connection
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

# Update the database records
for index, row in data.iterrows():
    name = row['name']
    phone_number = row.get('international_phone_number', None)
    
    if pd.isna(phone_number) or phone_number == '':  # Check for NaN or empty string
        clean_number = None
    else:
        clean_number = clean_phone_number(phone_number)
    
    # Construct the SQL query
    query = """
    UPDATE bars
    SET phone_number = %s
    WHERE name = %s;
    """
    cursor.execute(query, (clean_number, name))
    print(f"Updated bar {name} with phone number {clean_number}")

# Commit the changes and close the connection
conn.commit()
cursor.close()
conn.close()

print("Phone numbers updated successfully.")
