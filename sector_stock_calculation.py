from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
import time
import re
from tqdm import tqdm
from datetime import datetime
import statistics
from sample import get_csv_filenames

# Setup driver
driver = webdriver.Chrome()

# array_of_sectors = [
#     'FERTILIZER', 
#     'COMMERCIAL_BANKS', 
#     'OIL_&_GAS_MARKETING_COMPANIES', 
#     'OIL_&_GAS_EXPLORATION_COMPANIES', 
#     'CEMENT', 
#     'PHARMACEUTICALS'
# ]

array_of_sectors = get_csv_filenames('sector_files')

# Helper to extract % from Details column
def extract_dividend_percent(details):
    match = re.search(r'(\d+\.?\d*)%', details)
    return float(match.group(1)) if match else 0.0

# Function to calculate expected dividend for 2025
def calculate_expected_dividend_2025(dividends, stock_price):
    """
    Calculate expected dividend for 2025 based on past dividend history
    Returns: (expected_dividend_pkr, expected_dividend_percent, calculation_method)
    """
    if not dividends:
        return 0.0, 0.0, "No dividend history"
    
    # Get all dividend years excluding current year
    current_year = str(datetime.now().year)
    dividend_years = [y for y in dividends.keys() if y != current_year]
    
    if len(dividend_years) < 2:
        return 0.0, 0.0, "Insufficient history (need at least 2 years)"
    
    # Calculate total dividends per year
    yearly_totals = []
    for year in dividend_years:
        total_div = sum(dividends[year])
        yearly_totals.append(total_div)
    
    # Calculate expected dividend using different methods
    methods = {}
    
    # Method 1: Simple average of last 3 years
    recent_years = yearly_totals[-3:] if len(yearly_totals) >= 3 else yearly_totals
    avg_recent = statistics.mean(recent_years)
    methods['recent_avg'] = avg_recent
    
    # Method 2: Weighted average (more recent years have higher weight)
    if len(yearly_totals) >= 3:
        weights = [0.5, 0.3, 0.2]  # 50% weight to most recent, 30% to second, 20% to third
        weighted_avg = sum(w * v for w, v in zip(weights, yearly_totals[-3:]))
        methods['weighted_avg'] = weighted_avg
    
    # Method 3: Median (more robust to outliers)
    median_div = statistics.median(yearly_totals)
    methods['median'] = median_div
    
    # Method 4: Growth trend (if there's a clear trend)
    if len(yearly_totals) >= 3:
        # Calculate growth rate
        growth_rates = []
        for i in range(1, len(yearly_totals)):
            if yearly_totals[i-1] > 0:
                growth_rate = (yearly_totals[i] - yearly_totals[i-1]) / yearly_totals[i-1]
                growth_rates.append(growth_rate)
        
        if growth_rates:
            avg_growth_rate = statistics.mean(growth_rates)
            # Apply growth to most recent year
            trend_prediction = yearly_totals[-1] * (1 + avg_growth_rate)
            methods['trend'] = max(0, trend_prediction)  # Ensure non-negative
    
    # Choose the best method based on data quality
    if len(yearly_totals) >= 3 and 'trend' in methods and methods['trend'] > 0:
        # Use trend if we have enough data and positive trend
        expected_dividend = methods['trend']
        method_used = "Growth trend"
    elif 'weighted_avg' in methods:
        # Use weighted average for recent years
        expected_dividend = methods['weighted_avg']
        method_used = "Weighted average (recent 3 years)"
    else:
        # Fall back to simple average
        expected_dividend = methods['recent_avg']
        method_used = f"Average of last {len(recent_years)} years"
    
    # Convert to PKR and percentage
    expected_dividend_pkr = expected_dividend / 10  # Convert % to PKR
    expected_dividend_percent = (expected_dividend_pkr / stock_price) * 100 if stock_price > 0 else 0
    
    return expected_dividend_pkr, expected_dividend_percent, method_used

# Enhanced consistency checking function
def check_dividend_consistency(dividends, current_year):
    """
    Enhanced consistency check that looks for uninterrupted dividend payments
    Returns: (is_consistent, consistency_score, remarks)
    """
    if not dividends:
        return False, 0, "No dividends found"
    
    # Sort years in descending order
    sorted_years = sorted(dividends.keys(), reverse=True)
    
    # Filter out current year for analysis
    filtered_years = [y for y in sorted_years if y != current_year]
    
    if len(filtered_years) < 2:
        return False, 0, "Insufficient dividend history"
    
    # Check if company has paid dividends recently (within last 3 years)
    current_year_int = int(current_year)
    recent_years = [y for y in filtered_years if current_year_int - int(y) <= 3]
    
    # Check if company has stopped paying dividends
    if not recent_years:
        last_dividend_year = max(filtered_years)
        return False, 0, f"Stopped paying dividends since {last_dividend_year}"
    
    # Check for gaps in dividend payments
    years_int = [int(y) for y in filtered_years]
    years_int.sort(reverse=True)
    
    # Find gaps in dividend years
    gaps = []
    for i in range(len(years_int) - 1):
        gap = years_int[i] - years_int[i + 1]
        if gap > 1:  # Gap of more than 1 year
            gaps.append(gap)
    
    # Calculate consistency metrics
    total_years = len(filtered_years)
    years_with_dividends = len(filtered_years)
    consistency_score = (years_with_dividends / total_years) * 100 if total_years > 0 else 0
    
    # Check dividend frequency pattern
    dividend_counts = [len(dividends[y]) for y in filtered_years]
    pattern_consistent = len(set(dividend_counts)) == 1 if dividend_counts else False
    
    # Determine if company is a consistent payer
    is_consistent = False
    remarks = ""
    
    # Comprehensive consistency check
    if len(gaps) == 0:
        # No gaps - perfect consistency
        is_consistent = True
        remarks = f"Perfect consistency: {years_with_dividends} consecutive years"
    elif len(gaps) == 1 and max(gaps) <= 2:
        # Minor gap (1-2 years) - still considered consistent
        is_consistent = True
        remarks = f"Minor gap detected but overall consistent: {years_with_dividends} years with dividends"
    elif consistency_score >= 80 and len(recent_years) >= 2:
        # High consistency score and recent payments
        is_consistent = True
        remarks = f"High consistency ({consistency_score:.1f}%): {years_with_dividends} years with dividends"
    else:
        # Inconsistent due to gaps or low consistency
        gap_info = f", {len(gaps)} gaps detected" if gaps else ""
        remarks = f"Low consistency ({consistency_score:.1f}%): {years_with_dividends} years with dividends{gap_info}"
    
    if pattern_consistent and is_consistent:
        remarks += f", Pattern: {dividend_counts[0]} dividends per year"
    
    return is_consistent, consistency_score, remarks

for sector in array_of_sectors:
    df = pd.read_csv(f'sector_files/{sector}.csv')
    dividend_df = pd.DataFrame(columns=['Symbol', 'StockPrice', 'DividendYearsPaid', 'DivPerYearPattern', 'ConsistentPayer', 'YearlyYieldDetails', 'DividendAmountsPKR', 'ConsistencyScore', 'Remarks', 'ExpectedDividend2025_PKR', 'ExpectedDividend2025_Percent', 'CalculationMethod'])
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

            # Enhanced Summary + Calculations
            current_year = str(datetime.now().year)
            DividendYearsPaid = ', '.join(sorted(dividends.keys(), reverse=True))
            DivPerYearPattern = ', '.join([str(len(dividends[y])) for y in sorted(dividends.keys(), reverse=True)])
            
            # Enhanced consistency check
            is_consistent, consistency_score, consistency_remarks = check_dividend_consistency(dividends, current_year)
            ConsistentPayer = 'Yes' if is_consistent else 'No'

            # Calculate expected dividend for 2025
            expected_dividend_pkr, expected_dividend_percent, calculation_method = calculate_expected_dividend_2025(dividends, stock_price)

            # Calculate yearly yield details and dividend amounts in PKR
            YearlyYieldDetails = []
            DividendAmountsPKR = []
            
            for y in sorted(dividends.keys(), reverse=True):
                total_div = sum(dividends[y])
                dividend_amount_pkr = total_div / 10  # Convert to PKR
                yield_percent = (dividend_amount_pkr / stock_price) * 100
                
                YearlyYieldDetails.append(f'{y}: {yield_percent:.2f}%')
                DividendAmountsPKR.append(f'{y}: Rs.{dividend_amount_pkr:.2f}')
            
            YearlyYieldDetails_str = ' | '.join(YearlyYieldDetails)
            DividendAmountsPKR_str = ' | '.join(DividendAmountsPKR)

            # Enhanced remarks
            Remarks = consistency_remarks
            
            # Only add companies that are consistent AND have recent dividends (2024 or 2025)
            if ConsistentPayer == 'Yes':
                # Check if company has paid dividends in 2024 or 2025
                recent_dividend_years = [y for y in dividends.keys() if y in ['2024', '2025']]
                if recent_dividend_years:
                    dividend_df.loc[index] = [
                        symbol, 
                        stock_price, 
                        DividendYearsPaid, 
                        DivPerYearPattern, 
                        ConsistentPayer, 
                        YearlyYieldDetails_str, 
                        DividendAmountsPKR_str,
                        f"{consistency_score:.1f}%",
                        Remarks,
                        f"Rs.{expected_dividend_pkr:.2f}",
                        f"{expected_dividend_percent:.2f}%",
                        calculation_method
                    ]
                else:
                    print(f"⚠️ Skipping {symbol}: Consistent but no recent dividends (2024/2025)")
            else:
                print(f"⚠️ Skipping {symbol}: Not consistent payer")
            

        except Exception as e:
            print(f"❌ Error processing {symbol}: {str(e)}")
            continue

    # Save result
    dividend_df.to_csv(f'sector_calculations/{sector}_with_dividends.csv', index=False, encoding='utf-8-sig')
    print(f'Done. Saved to {sector}_with_dividends.csv')


driver.quit()
