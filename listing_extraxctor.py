from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import os

# Initialize driver
driver = webdriver.Chrome()  # or give path: Chrome(executable_path="your_path_to_chromedriver")

# Open URL
url = 'https://dps.psx.com.pk/listings'
driver.get(url)

# Wait for table to load
wait = WebDriverWait(driver, 20)
wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table.dataTable')))

# Extract data from all pages
all_data = []

while True:
    print("Processing page...")

    # Wait a bit to ensure page is ready
    time.sleep(2)

    # Get all rows of table body
    rows = driver.find_elements(By.CSS_SELECTOR, 'table.dataTable tbody tr')

    for row in rows:
        cols = row.find_elements(By.TAG_NAME, 'td')
        if len(cols) >= 7:
            symbol = cols[0].text.strip()
            name = cols[1].text.strip()
            sector = cols[2].text.strip()
            shares = cols[4].text.strip()
            listed_in = cols[6].text.strip()

            all_data.append({
                'Symbol': symbol,
                'Name': name,
                'Sector': sector,
                'Shares': shares,
                'Listed In': listed_in
            })

    # Check if "Next" button is enabled
    next_button = driver.find_element(By.LINK_TEXT, 'Next')
    if 'disabled' in next_button.get_attribute('class'):
        break
    else:
        next_button.click()

# Save to CSV
df = pd.DataFrame(all_data)
df.to_csv('data/psx_listings.csv', index=False, encoding='utf-8-sig')


file_path = "data/psx_listings.csv"  # Replace with the actual file path if different
df = pd.read_csv(file_path)

# Create a folder to store the sector files
output_folder = "sector_files"
os.makedirs(output_folder, exist_ok=True)

# Group by sector and save each group as a separate CSV file
for sector, group in df.groupby('Sector'):
    # Create a valid filename by replacing invalid characters
    filename = sector.replace("/", "-").replace("\\", "-").replace(" ", "_") + ".csv"
    group.to_csv(os.path.join(output_folder, filename), index=False)

print(f"Files have been created in the '{output_folder}' folder.")

print("Done. Data saved to psx_listings.csv")

# Close driver
driver.quit()
