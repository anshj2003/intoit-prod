import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import time

# Path to the WebDriver executable (ChromeDriver in this case)
driver_path = '/path/to/chromedriver'  # Replace with your actual path

# Load the CSV file
csv_path = '/Users/anshjhaveri/Downloads/places.csv'
df = pd.read_csv(csv_path)

# Initialize the Chrome driver
driver = webdriver.Chrome()

# Open Google Maps
driver.get('https://maps.google.com')
driver.implicitly_wait(10)

# Function to search for a bar in Google Maps
def search_bar(name):
    # Find the search box element
    search_box = driver.find_element(By.XPATH, '//*[@id="searchboxinput"]')

    # Clear the search box if there's any text
    search_box.clear()

    # Type the name followed by 'bar NYC' and hit enter
    search_box.send_keys(name + ' bar NYC')
    search_box.send_keys(Keys.RETURN)

    # Wait for a few seconds to allow the results to load
    time.sleep(5)

# Function to select each day from the dropdown menu and fetch data
def select_days_and_fetch_data():
    days = ['Sundays', 'Mondays', 'Tuesdays', 'Wednesdays', 'Thursdays', 'Fridays', 'Saturdays']

    for day in days:
        try:
            # Click the dropdown to expand it
            dropdown_button = driver.find_element(By.XPATH, '//*[@class="GqEqxf goog-inline-block goog-menu-button"]')
            dropdown_button.click()
            
            time.sleep(1)  # wait for the dropdown to expand
            
            # Select the day from the dropdown
            day_option = driver.find_element(By.XPATH, f'//div[@role="option" and text()="{day}"]')
            day_option.click()
            
            time.sleep(5)  # wait for the data to load
            
            # Here, add the code to extract the busy-ness data for the selected day
            # For example, you might want to parse the page content to get the required data
            
        except Exception as e:
            print(f"Error selecting day {day}: {e}")

# Iterate through each name in the CSV and perform the search and data fetching
for index, row in df.iterrows():
    bar_name = row['name']
    search_bar(bar_name)
    select_days_and_fetch_data()

# Close the browser after the searches are done
driver.quit()
