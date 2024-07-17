import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

# Read the CSV file
csv_file_path = '/Users/anshjhaveri/Downloads/places.csv'
data = pd.read_csv(csv_file_path)

# Set up Chrome driver

driver = webdriver.Chrome()

# Function to perform a Google Images search, click on the first photo, and get the image address
def search_google_images(query):
    driver.get('https://images.google.com')
    search_box = driver.find_element('name', 'q')
    search_box.send_keys(query)
    search_box.send_keys(Keys.RETURN)
    time.sleep(3)  # Wait for the search results to load

    try:
        # Click on the first photo
        first_photo = driver.find_element('xpath', '/html/body/div[4]/div/div[15]/div/div[2]/div[2]/div/div/div/div/div[1]/div/div/div[1]')
        first_photo.click()
        time.sleep(2)  # Wait to ensure the click is registered

        # Get the image address
        image_element = driver.find_element('xpath', '/html/body/div[6]/div/div/div/div/div/div/c-wiz/div/div[2]/div[2]/div/div[2]/c-wiz/div/div[3]/div[1]/a/img[1]')
        image_address = image_element.get_attribute('src')
        print(f"Image address for query '{query}': {image_address}")
        
        return image_address

    except Exception as e:
        print(f"Error for query '{query}': {e}")
        return None

# Iterate over the names in the CSV file, perform searches, and store image addresses
image_addresses = []
checkpoint_file = '/Users/anshjhaveri/Downloads/places_with_images_checkpoint.csv'
checkpoint_interval = 5  # Save progress every 5 iterations

for index, row in data.iterrows():
    name = row['name']
    search_query = f"{name} bar nyc"
    image_address = search_google_images(search_query)
    image_addresses.append((name, image_address))
    time.sleep(2)  # Wait for 2 seconds before the next search
    
    # Checkpointing
    if (index + 1) % checkpoint_interval == 0:
        checkpoint_df = pd.DataFrame(image_addresses, columns=['name', 'photo'])
        checkpoint_df.to_csv(checkpoint_file, index=False)
        print(f"Checkpoint saved at iteration {index + 1}")

# Close the browser
driver.quit()

# Save the final results to a new CSV file
final_df = pd.DataFrame(image_addresses, columns=['name', 'photo'])
final_df.to_csv('/Users/anshjhaveri/Downloads/places_with_images.csv', index=False)
print("Final results saved.")