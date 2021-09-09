from pygdpr.services.metadata_service import MetadataService
from pygdpr.services.list_eu_currencies_services import ListEUCurrenciesService
from price_parser import Price
import nltk

class PenaltiesMetaService(MetadataService):
    def join_numeric_words(self, words):
        ws = words
        joined_ws = []
        i = 0
        while i < len(ws)-1:
            if ws[i].isnumeric() is False:
                joined_ws.append(ws[i])
            else:
                j = i+1
                while j < len(ws) and ws[j].isnumeric():
                    j+=1
                joined_ws.append("".join(ws[i:j]))
                del ws[i+1:j]
            i+=1
        return joined_ws

    def for_text(self, text):
        penalties = {}
        for s in nltk.sent_tokenize(text):
            words = nltk.word_tokenize(s)
            words = [w.lower() for w in words]
            words = self.join_numeric_words(words)
            if 'penalty' not in words and 'fine' not in words: # stem the words. - what about plurals?
                continue
            if len(words) < 2:
                continue
            subwords = []
            currency_symbols = []
            for i in range(len(words)):
                w = words[i]
                list_eu_currencies = ListEUCurrenciesService()
                eu_currencies = list_eu_currencies.get()
                for c in eu_currencies:
                    for p in c['plural']:
                        if w == p and words[i-1].isnumeric():
                            currency_symbols.append(c['symbol'])
                            subwords.append(words[i-1] + ' ' + w)
                    if w == c['code'].lower() and words[i+1].isnumeric():
                        currency_symbols.append(c['symbol'])
                        subwords.append(w + ' ' + words[i+1])
                    if c['symbol'] is None:
                        continue
                    if w.startswith(c['symbol']) or w.endswith(c['symbol']):
                        currency_symbols.append(c['symbol'])
                        subwords.append(words[i])
                    elif w == c['symbol'] and w[i+1].isnumeric():
                        currency_symbols.append(c['symbol'])
                        subwords.append(words[i] + ' ' + words[i+1])
                    elif w == c['symbol'] and w[i-1].isnumeric():
                        currency_symbols.append(c['symbol'])
                        subwords.append(words[i-1] + ' ' + words[i])
            assert len(subwords) == len(currency_symbols)
            for i in range(len(subwords)):
                currency_symbol = currency_symbols[i]
                price = Price.fromstring(subwords[i], currency_hint=currency_symbol)
                if currency_symbol is None:
                    continue
                if price.amount_float is None:
                    continue
                currency = self.eu_currency_repo.for_symbol(currency_symbol)
                amount = price.amount_float
                if str(amount) not in penalties.keys():
                    penalties[str(amount)] = {
                        'amount': amount,
                        'currency_code': currency['code'],
                        'texts': {
                            'en': [s]
                        }
                    }
                else:
                    penalties[str(amount)]['texts']['en'].append(s)
        return list(penalties.values())
