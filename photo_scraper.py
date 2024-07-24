import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import time
import os

# Specify the path to the ChromeDriver
driver_path = '/path/to/chromedriver'

# Create a new instance of the Chrome driver
driver = webdriver.Chrome()

# Read the CSV file
csv_path = '/Users/anshjhaveri/Downloads/places.csv'
data = pd.read_csv(csv_path)

# Prepare the output CSV file
output_csv_path = '/Users/anshjhaveri/Downloads/places_with_links.csv'

# Check if the output CSV file already exists
if os.path.exists(output_csv_path):
    existing_data = pd.read_csv(output_csv_path)
    processed_names = set(existing_data['name'])
    output_data = existing_data.to_dict('records')
else:
    processed_names = set()
    output_data = []

# Loop through each name in the CSV and perform a Google search
for index, row in data.iterrows():
    name = row['name']

    # Skip names that have already been processed
    if name in processed_names:
        continue

    search_query = f"{name} bar nyc"
    
    # Open Google
    driver.get('https://www.google.com')
    
    # Find the search box
    search_box = driver.find_element('name', 'q')
    
    # Enter the search query and submit
    search_box.send_keys(search_query)
    search_box.send_keys(Keys.RETURN)
    
    # Wait for a few seconds to load results
    time.sleep(3)
    
    # Parse the search results page
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # Find the website link element
    website_link = soup.find('a', class_='n1obkb')
    website_url = website_link.get('href') if website_link else 'Not found'

    # Find the reservation link element
    reservation_div = soup.find('div', {'data-attrid': 'kc:/local:table_reservations'})
    reservation_link = reservation_div.find('a', class_='xFAlBc') if reservation_div else None
    reservation_url = reservation_link.get('href') if reservation_link else 'Not found'

    output_data.append({
        'name': name,
        'website_link': website_url,
        'reservation_link': reservation_url
    })

    # Add the name to the set of processed names
    processed_names.add(name)

    # Save the data to the output CSV file after every 10 iterations
    if len(output_data) % 10 == 0:
        pd.DataFrame(output_data).to_csv(output_csv_path, index=False)

# Save any remaining data to the output CSV file
pd.DataFrame(output_data).to_csv(output_csv_path, index=False)

# Close the browser
driver.quit()
