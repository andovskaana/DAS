import aiohttp
import asyncio
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import csv


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


async def fetch_data(issuer_code, start_date, end_date):
    """Fetch data for the issuer, ensuring that each request covers a 365-day range."""
    async with aiohttp.ClientSession() as session:
        current_start = datetime.strptime(start_date, '%m/%d/%Y')
        final_end = datetime.strptime(end_date, '%m/%d/%Y')
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
    """Reformats a numeric string to use dots for thousands and commas for decimals."""
    # Remove commas for thousands, replace dot with comma for decimals, then add dots for thousands
    try:
        # Remove commas if present, and convert to float for accurate decimal handling
        num = float(value.replace(',', ''))
        # Format with dots as thousands separator and comma as decimal separator
        return f"{num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except ValueError:
        return value


def save_all_to_csv(results, issuers):
    """Saves all issuer data in one CSV file."""
    with open("all_issuers_data.csv", "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["IssuerCode", "Date", "Price", "Max", "Min", "Avg", "Volume", "Turnover", "All"])

        for issuer, data in zip(issuers, results):
            if data:
                for row in data:
                    formatted_row = [issuer] + [reformat_number(cell) if i in {1, 2, 3, 4, 5, 7, 8} else cell for
                                                i, cell
                                                in enumerate(row)]
                    writer.writerow(formatted_row)  # Include issuer code in each row
    print("Data saved to all_issuers_data.csv")
