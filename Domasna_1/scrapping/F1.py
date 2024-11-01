# Koristenje na BeautifulSoup deka za static scrapping e pokorisno i pobrzo (nema refreshing)

import requests
from bs4 import BeautifulSoup
import csv

# Proverka dali e obvrznik ili sodrzi brojka
def is_valid_issuer_code(s):
    for char in s:
        if char.isdigit():
            return False
    return True

def filter_1():
    response = requests.get("https://www.mse.mk/page.aspx/stats/symbolhistory/ADIN")

    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    dropdown = soup.find('select', {'id': 'Code'})
    symbols = []

    if dropdown:
        for option in dropdown.find_all('option'):
            symbol = option.get('value')
            # Proveri za brojki vo kodot, ako ne dodaj
            if symbol and is_valid_issuer_code(symbol):
                symbols.append(symbol)

    # Zacuvaj vo CSV
    with open('symbols.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["issuer_code"])
        for symbol in symbols:
            writer.writerow([symbol])

    # Za testiranje
    print("Issuer Codes:", symbols)
