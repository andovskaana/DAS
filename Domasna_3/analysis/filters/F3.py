import aiohttp
import asyncio
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import csv

from Domasna_3.analysis.DB import update_last_date, insert_stock_data

async def fetch_data_for_dates(session, issuer_code, start_date, end_date):
    """Fetch data for a specific issuer between start and end dates in 365-day increments."""
    url = f"https://www.mse.mk/page.aspx/stats/symbolhistory/{issuer_code}"
    params = {
        'FromDate': start_date,
        'ToDate': end_date
    }
    async with session.get(url, params=params) as response:
        if response.status == 200:
            page_content = await response.text()
            return parse_data(page_content)
        else:
            print(f"Failed to fetch data for {issuer_code}")
            return None


async def filter_3(issuer_code, start_date):
    """Fetch data for the issuer, ensuring that each request covers a 365-day range."""
    async with aiohttp.ClientSession() as session:
        current_start = datetime.strptime(start_date, '%m/%d/%Y')
        end = datetime.now().strftime('%m/%d/%Y')
        final_end = datetime.strptime(end, '%m/%d/%Y')
        all_data = []

        while current_start < final_end:
            current_end = min(current_start + timedelta(days=364), final_end)
            fetched_data = await fetch_data_for_dates(
                session, issuer_code,
                current_start.strftime('%m/%d/%Y'),
                current_end.strftime('%m/%d/%Y')
            )
            if fetched_data:
                all_data.extend(fetched_data)
            current_start = current_end + timedelta(days=1)  # Move to the next period

        return all_data


def parse_data(page_content):
    """Parses HTML content to extract table data."""
    soup = BeautifulSoup(page_content, 'html.parser')
    table = soup.find('table', id='resultsTable')  # Replace with the actual ID

    if not table:
        return []

    data = []
    for tr in table.find_all('tr')[1:]:  # Skip header row
        cols = [td.get_text().strip() for td in tr.find_all('td')]
        if len(cols) > 6 and cols[6] != '0':  # Check volume is not zero
            data.append(cols)
    return data

def reformat_number(value):
    """Reformats a numeric string to use dots for thousands and commas for decimals,
    adding decimal places only if originally present."""
    try:
        # Remove commas if present
        num = float(value.replace(',', ''))

        # Determine formatting based on the presence of decimals in the original input
        if '.' in value:
            # Format with 2 decimal places
            formatted_value = f"{num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            # Format without decimal places
            formatted_value = f"{num:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")

        return formatted_value
    except ValueError:
        return value


# def save_all_to_csv(results, issuers):
#     """Saves all issuer data in one CSV file."""
#     with open("all_issuers_data.csv", "w", newline="") as csvfile:
#         writer = csv.writer(csvfile)
#         writer.writerow(["IssuerCode", "Date", "Price", "Max", "Min", "Avg", "Volume", "Turnover", "All"])
#
#         for issuer, data in zip(issuers, results):
#             if data:
#                 for row in data:
#                     formatted_row = [issuer] + [reformat_number(cell) if i in {1, 2, 3, 4, 5, 6, 7, 8} else cell for
#                                                 i, cell
#                                                 in enumerate(row)]
#                     writer.writerow(formatted_row)  # Include issuer code in each row
#     print("Data saved to all_issuers_data.csv")

def save_to_database(results, issuers):
    """Saves all issuer data to the database."""
    for issuer, data in zip(issuers, results):
        if data:
            formatted_data = []
            for row in data:
                # Date and symbol remain as strings, others are converted to numbers
                formatted_row = [
                    row[0],  # Date
                    reformat_number(row[1]),  # LastTradePrice
                    reformat_number(row[2]),  # Max
                    reformat_number(row[3]),  # Min
                    reformat_number(row[4]),  # AvgPrice
                    reformat_number(row[5]),  # PercentageChange
                    str(reformat_number(row[6])),  # Volume
                    str(reformat_number(row[7])),  # TurnoverInBEST
                    str(reformat_number(row[8]))  # TotalTurnover
                ]
                formatted_data.append(formatted_row)
            # Insert formatted data into the database
            insert_stock_data(issuer, formatted_data)



