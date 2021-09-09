import os
import json

class ListEUCurrenciesService():
    def get(self):
        eu_currencies = []
        path = os.path.abspath('pygdpr/assets/eu-currencies.json')
        f = open(path, 'r')
        eu_currencies_items = json.load(f)
        f.close()
        for country_code, currency in self.eu_currencies.items():
            currency_code = currency['code'].upper()
            if currency_code not in currencies.keys():
                currencies[currency_code] = currency
        return list(currencies.values())
