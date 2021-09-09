from pygdpr.services.metadata_service import MetadataService
from ..specifications.absolute_date_specification import AbsoluteDateSpecification
import dateparser
from dateparser.search import search_dates
import datetime
import nltk

class TimelineMetaService(MetadataService):
    def __init__(self):
        self.date_formats = ['%d-%m-%Y', '%d %B %Y']
        dateparser.date._DateLocaleParser._try_freshness_parser = lambda self: False

    def for_text(self, text):
        timeline = {}
        sents = nltk.sent_tokenize(text)
        for s in sents:
            words = nltk.word_tokenize(s)
            words = [w.lower() for w in words]
            words = [w for w in words if w.isdigit() or w.isalpha()]
            try:
                matches = search_dates(s, languages=['en'], settings={
                    'STRICT_PARSING': True,
                    'PREFER_DATES_FROM': 'past'
                })
                if matches is None:
                    continue
                if len(matches) == 0:
                    continue
                for m in matches:
                    if AbsoluteDateSpecification().is_satisfied_by(m) is False:
                        continue
                    date = m[1]
                    date_str = datetime.datetime.strftime(date, '%d/%m/%Y')
                    if date_str not in timeline.keys():
                        timeline[date_str] = {
                            'date': date_str,
                            'texts': {
                                'en': [s]
                            }
                        }
                    else:
                        timeline[date_str]['texts']['en'].append(s)
            except:
                pass
        return list(timeline.values())
