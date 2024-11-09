from DB import get_last_saved_date
from datetime import datetime, timedelta


def filter_2(issuer):
    # Initialize the date 10 years ago
    ten_years_ago = datetime.now() - timedelta(days=365 * 10)

    # Fetch the last saved date for the issuer
    last_date = get_last_saved_date(issuer)

    # If no date is found, default to 10 years ago
    if not last_date:
        last_date = ten_years_ago.strftime('%m/%d/%Y')

    # Return a tuple containing the issuer code and the last available date
    return issuer, last_date
