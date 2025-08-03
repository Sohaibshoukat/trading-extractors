from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
import time
import re
from tqdm import tqdm

# Setup driver
driver = webdriver.Chrome()

# Load CSV
df = pd.read_csv('dummy_data/psx_listings.csv')

# Add columns
df['StockPrice'] = ''
df['DividendYearsPaid'] = ''
df['DivPerYearPattern'] = ''
df['ConsistentPayer'] = ''
df['YearlyYieldDetails'] = ''
df['Remarks'] = ''

# Helper to extract % from Details column
def extract_dividend_percent(details):
    match = re.search(r'(\d+\.?\d*)%', details)
    return float(match.group(1)) if match else 0.0

# Go through each company
for index, row in tqdm(df.iterrows(), total=len(df), desc='Processing Companies'):
    symbol = row['Symbol']
    url = f'https://dps.psx.com.pk/company/{symbol}'

    try:
        print(f"\n🔍 Processing {symbol} → {url}")
        driver.get(url)
        time.sleep(3)

        # Extract Stock Price
        stock_price_elem = driver.find_element(By.CLASS_NAME, 'quote__close')
        print("📈 Raw stock price text:", stock_price_elem.text)
        cleaned_price = stock_price_elem.text.replace('Rs.', '').replace(',', '').strip()
        stock_price = float(cleaned_price)
        print("✅ Parsed stock price:", stock_price)

        # Try to locate the payout table
        payouts_section = driver.find_element(By.ID, 'payouts')
        print("✅ Payouts section found.")

        payouts_rows = payouts_section.find_elements(By.CSS_SELECTOR, 'tbody tr')
        print(f"📊 Found {len(payouts_rows)} payout rows.")

        dividends = {}

        for r in payouts_rows:
            cols = r.find_elements(By.TAG_NAME, 'td')
            print("   ➖ Row data:", [c.text.strip() for c in cols])
            if len(cols) >= 3:
                fin_result = cols[1].text.strip()
                details = cols[2].text.strip()

                year_match = re.search(r'(\d{4})', fin_result)
                if year_match:
                    year = year_match.group(1)
                else:
                    date_text = cols[0].text.strip()
                    year_match = re.search(r'(\d{4})', date_text)
                    year = year_match.group(1) if year_match else 'Unknown'

                dividend_percent = extract_dividend_percent(details)

                if year not in dividends:
                    dividends[year] = []
                dividends[year].append(dividend_percent)

        print("🧾 Dividends extracted:", dividends)

        # Summary + Calculations
        DividendYearsPaid = ', '.join(sorted(dividends.keys(), reverse=True))
        DivPerYearPattern = ', '.join([str(len(dividends[y])) for y in sorted(dividends.keys(), reverse=True)])
        sorted_years = sorted(dividends.keys(), reverse=True)
        # Exclude current year
        from datetime import datetime
        current_year = str(datetime.now().year)
        filtered_years = [y for y in sorted_years if y != current_year]

        pattern = [len(dividends[y]) for y in filtered_years]

        ConsistentPayer = 'Yes' if len(set(pattern)) == 1 and len(pattern) > 1 else 'No'


        YearlyYieldDetails = []
        for y in sorted(dividends.keys(), reverse=True):
            total_div = sum(dividends[y])
            yield_percent = (total_div / 100) / stock_price * 100
            YearlyYieldDetails.append(f'{y}: {yield_percent:.2f}%')
        YearlyYieldDetails_str = ' | '.join(YearlyYieldDetails)

        Remarks = ''
        if ConsistentPayer == 'Yes':
            Remarks = 'Consistent dividends with pattern: ' + str(pattern[0]) + ' per year'

        # Save results
        df.at[index, 'StockPrice'] = stock_price
        df.at[index, 'DividendYearsPaid'] = DividendYearsPaid
        df.at[index, 'DivPerYearPattern'] = DivPerYearPattern
        df.at[index, 'ConsistentPayer'] = ConsistentPayer
        df.at[index, 'YearlyYieldDetails'] = YearlyYieldDetails_str
        df.at[index, 'Remarks'] = Remarks

    except Exception as e:
        print(f"❌ Error processing {symbol}: {str(e)}")
        continue


# Save result
df.to_csv('psx_listings_with_dividends.csv', index=False, encoding='utf-8-sig')
print('Done. Saved to psx_listings_with_dividends.csv')

driver.quit()
