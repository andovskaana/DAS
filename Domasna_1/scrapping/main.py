from F1 import filter_1
from multiprocessing import Pool, cpu_count
import asyncio
from F2 import filter_2
from F3 import filter_3, save_to_database
from DB import update_last_date, init_createDB
from datetime import datetime
import time


def process_issuer(issuer):
    """Processes a single issuer's data."""
    issuer_code, last_saved_date = filter_2(issuer)
    start_date = last_saved_date if last_saved_date else "11/10/2014"
    data = asyncio.run(filter_3(issuer_code, start_date))
    return issuer_code, data


def scrape_all_issuers(issuers, end_date):
    """Scrapes data for all issuers using multi-core processing."""
    with Pool(cpu_count()) as pool:
        results = pool.map(process_issuer, issuers)  

    for issuer, data in results:
        save_to_database([data], [issuer])
        update_last_date(issuer, end_date)

    print("Scraping completed.")


if __name__ == "__main__":
    init_createDB()

    end_date = datetime.now().strftime('%m/%d/%Y')
    issuers = filter_1()

    start_time = time.time()

    scrape_all_issuers(issuers, end_date)

    end_time = time.time()
    execution_time = end_time - start_time

    print(f"Execution time: {execution_time:.2f} seconds")
