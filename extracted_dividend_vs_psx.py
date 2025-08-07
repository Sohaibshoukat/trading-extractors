from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import pandas as pd
import time
from tqdm import tqdm
from sample import get_csv_filenames

# Setup WebDriver
driver = webdriver.Chrome()
wait = WebDriverWait(driver, 10)

# Go to the indices page
driver.get("https://dps.psx.com.pk/indices")

# Click on the PSXDIV20 link
psxdiv20 = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "PSXDIV20")))
psxdiv20.click()

# Wait for the table to load
time.sleep(5)  # wait extra time to be sure all JS loads

# Data storage
data = []

# Loop through all pages
while True:
    # Wait for table rows to appear
    table = wait.until(EC.presence_of_element_located((By.ID, "indexConstituentsTable")))
    rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")

    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")
        data.append([col.text.strip() for col in cols])

    # Try to go to next page if available
    try:
        next_btn = driver.find_element(By.ID, "indexConstituentsTable_next")
        if "disabled" in next_btn.get_attribute("class"):
            break  # End of pages
        else:
            next_btn.click()
            time.sleep(2)
    except:
        break

# Close driver
driver.quit()

# Save data
columns = ["SYMBOL", "NAME", "LDCP", "CURRENT", "CHANGE", "CHANGE(%)", "IDX_WTG(%)", "IDX_POINT", "VOLUME", "FREEFLOAT(M)", "MARKET_CAP(M)"]
df = pd.DataFrame(data, columns=columns)
df.to_csv("psx_divident_data/PSXDIV20_index_constituents.csv", index=False, encoding='utf-8-sig')

print("Data saved to PSXDIV20_index_constituents.csv")

# read the csv file
psx_df = pd.read_csv("psx_divident_data/PSXDIV20_index_constituents.csv")

# array_of_sectors = [
#     'FERTILIZER', 
#     'COMMERCIAL_BANKS', 
#     'OIL_&_GAS_MARKETING_COMPANIES', 
#     'OIL_&_GAS_EXPLORATION_COMPANIES', 
#     'CEMENT', 
#     'PHARMACEUTICALS'
# ]

array_of_sectors = get_csv_filenames('sector_files')

# Initialize list to store matching records
matching_records = []

# Find existing same record in PSX20 AND EXTRACTED_SECTOR_DIVIDEND
for sector in array_of_sectors:
    print(f"Processing sector: {sector}")
    try:
        sector_df = pd.read_csv(f'sector_calculations/{sector}_with_dividends.csv')
        
        # Create a set of symbols from PSX dataframe for faster lookup
        psx_symbols = set(psx_df['SYMBOL'].str.strip())
        
        # Find matching records
        for index, sector_row in tqdm(sector_df.iterrows(), total=len(sector_df), desc=f'Processing {sector}'):
            sector_symbol = sector_row['Symbol'].strip()
            
            if sector_symbol in psx_symbols:
                # Get the corresponding PSX record
                psx_row = psx_df[psx_df['SYMBOL'].str.strip() == sector_symbol].iloc[0]
                
                # Create a combined record
                combined_record = {
                    'Sector': sector,
                    'Symbol': sector_symbol,
                    'Name': psx_row.get('NAME', ''),
                    'StockPrice': sector_row.get('StockPrice', ''),
                    'DividendYearsPaid': sector_row.get('DividendYearsPaid', ''),
                    'DivPerYearPattern': sector_row.get('DivPerYearPattern', ''),
                    'ConsistentPayer': sector_row.get('ConsistentPayer', ''),
                    'YearlyYieldDetails': sector_row.get('YearlyYieldDetails', ''),
                    'DividendAmountsPKR': sector_row.get('DividendAmountsPKR', ''),
                    'ConsistencyScore': sector_row.get('ConsistencyScore', ''),
                    'Remarks': sector_row.get('Remarks', ''),
                    'ExpectedDividend2025_PKR': sector_row.get('ExpectedDividend2025_PKR', ''),
                    'ExpectedDividend2025_Percent': sector_row.get('ExpectedDividend2025_Percent', ''),
                    'CalculationMethod': sector_row.get('CalculationMethod', ''),
                    'PSX_NAME': psx_row.get('NAME', ''),
                    'PSX_LDCP': psx_row.get('LDCP', ''),
                    'PSX_CURRENT': psx_row.get('CURRENT', ''),
                    'PSX_CHANGE': psx_row.get('CHANGE', ''),
                    'PSX_CHANGE_PERCENT': psx_row.get('CHANGE(%)', ''),
                    'PSX_IDX_WTG_PERCENT': psx_row.get('IDX_WTG(%)', ''),
                    'PSX_IDX_POINT': psx_row.get('IDX_POINT', ''),
                    'PSX_VOLUME': psx_row.get('VOLUME', ''),
                    'PSX_FREEFLOAT_M': psx_row.get('FREEFLOAT(M)', ''),
                    'PSX_MARKET_CAP_M': psx_row.get('MARKET_CAP(M)', '')
                }
                
                matching_records.append(combined_record)
                
    except FileNotFoundError:
        print(f"Warning: File not found for sector {sector}")
        continue
    except Exception as e:
        print(f"Error processing sector {sector}: {str(e)}")
        continue

# Create DataFrame from matching records
if matching_records:
    matching_df = pd.DataFrame(matching_records)
    
    # Save to CSV
    output_filename = "psx_divident_data/psx_dividend_matching_records.csv"
    matching_df.to_csv(output_filename, index=False, encoding='utf-8-sig')
    
    print(f"\nMatching records saved to: {output_filename}")
    print(f"Total matching records found: {len(matching_records)}")
    
    # Display summary by sector
    print("\nSummary by sector:")
    sector_counts = matching_df['Sector'].value_counts()
    for sector, count in sector_counts.items():
        print(f"{sector}: {count} records")
        
else:
    print("No matching records found between PSX and sector dividend files.")
