import asyncio
from datetime import datetime
import time
from F3 import fetch_data, save_to_database
from F1 import filter_1
from F2 import filter_2
from DB import update_last_date

async def fetch_all_issuers(issuers, end_date):
    """Fetch data for all issuers asynchronously using the last saved date from the database."""
    tasks = []

    for issuer in issuers:
        # Apply filter_2 to get the issuer code and last saved date
        issuer_code, last_saved_date = filter_2(issuer)

        # Set the start date to the last saved date or a default start date if no data is saved
        start_date = last_saved_date if last_saved_date else "11/10/2014"

        # Create an asynchronous task for each issuer using fetch_data
        task = asyncio.create_task(fetch_data(issuer_code, start_date, end_date))
        tasks.append(task)

    # Gather all results asynchronously
    results = await asyncio.gather(*tasks)

    # Save all data to CSV
    # save_all_to_csv(results, issuers)
    save_to_database(results, issuers)

    # Update last saved date in the database for each issuer after saving
    for issuer_code in issuers:
        update_last_date(issuer_code, end_date)

if __name__ == "__main__":
    # Parameters
    end_date = datetime.now().strftime('%m/%d/%Y')
    issuers = filter_1()  # Get issuer codes using filter_1

    # Track start time
    start_time = time.time()

    # Run the async function
    asyncio.run(fetch_all_issuers(issuers, end_date))

    # Track end time and calculate duration
    end_time = time.time()
    execution_time = end_time - start_time

    print(f"Execution time: {execution_time:.2f} seconds")
