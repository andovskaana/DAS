from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import time
import csv


# Иницијализација на драјверот
chromedriver_path = r"C:\Users\Administrator\Downloads\chromedriver-win64\chromedriver-win64\chromedriver.exe"

# Create a Service object
service = Service(chromedriver_path)

# Start the WebDriver with the Service
driver = webdriver.Chrome(service=service)

def fetch_data_for_dates(issuer_code, start_date, end_date):
    url = f"https://www.mse.mk/page.aspx/stats/symbolhistory/{issuer_code}"
    driver.get(url)

    # Set the start and end dates
    start_date_input = driver.find_element(By.ID, 'FromDate')
    start_date_input.clear()
    start_date_input.send_keys(start_date)

    end_date_input = driver.find_element(By.ID, 'ToDate')
    end_date_input.clear()
    end_date_input.send_keys(end_date)

    # Click the button to load data
    buttons = driver.find_elements(By.CLASS_NAME, 'btn-primary-sm')
    buttons[0].click()

    time.sleep(3)  # Wait for data to load

    table = driver.find_element(By.ID, 'resultsTable')
    time.sleep(1)  # Small pause to ensure interaction is registered

    data = []
    last_date = None

    rows = table.find_elements(By.TAG_NAME, 'tr')
    for row in rows[1:]:  # Skip the header
        dataa = row.accessible_name
        # Split the data based on space
        values = dataa.split(" ")  # Adjust the delimiter if necessary
        data.append(values)
        if data:
            last_date = data[0][0]  # Update last_date with the current row's date

    return data, last_date


def fetch_data_for_all_issuers():
    with open('symbols.csv', newline='') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Прескокни го заглавјето
        issuer_codes = [row[0] for row in reader]

    start_year = 2014
    end_year = 2024

    for issuer_code in issuer_codes:
        all_data = []  # Список за чување податоци за сите години
        last_saved_date = None  # Last saved date for the issuer

        for year in range(start_year, end_year + 1):
            # Set the start and end dates for the current year
            start_date = f'01/01/{year}'
            end_date = f'12/31/{year}'

            data, last_saved_date = fetch_data_for_dates(issuer_code, start_date, end_date)
            all_data.extend(data)  # Додајте ги новите податоци во all_data

        # Зачувај ги податоците за секој издавач во еден фајл
        with open(f'{issuer_code}_data_all_years.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Date', 'Last Trade Price', 'Max Price', 'Min Price', 'Avg Price', 'Change', 'Volume',
                             'Turnover in BEST in Denars', 'Total Turnover in Denars'])
            writer.writerows(all_data)

        # Вратете го последниот зачуван датум по завршувањето на обработката за сите години
        print(f"Податоците за {issuer_code} за сите години се зачувани. Последниот зачуван датум: {last_saved_date}")

# Повик на функцијата за собирање податоци
fetch_data_for_all_issuers()

# Затвори го драјверот
driver.quit()
