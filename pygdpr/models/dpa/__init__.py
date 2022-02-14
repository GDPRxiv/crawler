import os
import json
import time
from pygdpr.specifications.supported_dpa_specification import SupportedDPASpecification
from pygdpr.specifications.eu_member_specification import EUMemberSpecification
from pygdpr.services.translate_price_service import TranslatePriceService
from pygdpr.services.translate_quota_service import TranslateQuotaService
from pygdpr.specifications.root_document_specification import RootDocumentSpecification
from pygdpr.policies.translate_file_policy import TranslateFilePolicy
from pygdpr.specifications.price_terminate_translate_specification import PriceTerminateTranslateSpecification
from pygdpr.specifications.not_reached_daily_translate_quota_specification import NotReachedDailyTranslateQuotaSpec
from pygdpr.specifications.not_reached_100_secs_translate_quota_specification import NotReached100SecsTranslateQuotaSpec
from pygdpr.specifications.translate_document_specification import TranslateDocumentSpecification
from pygdpr.specifications.not_exists_file_language_specification import NotExistsFileLanguageSpecification
#from google.cloud import translate_v2 as translate
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
from pygdpr.services.metadata.summary_metadata_service import *
from pygdpr.services.metadata.timeline_metadata_service import *
from pygdpr.services.metadata.citations_metadata_service import *
from pygdpr.services.metadata.citations_count_metadata_service import *
from pygdpr.services.metadata.keywords_metadata_service import *
from pygdpr.services.metadata.statistics_metadata_service import *
from pygdpr.services.metadata.est_read_time_metadata_service import *

nltk.download('punkt')
nltk.download('stopwords')
nltk.download('words')

# TODO: Bug here where supported_dpas was being instantiated as list, not dictionary
# TODO: Fix bug where these were not being read in from the dpa-info.json file in assets

supported_dpas = {
  "AT": {
    "country": "Austria",
    "language_code": "de",
    "name": "Österreichische Datenschutzbehörde",
    "addressFormatted": "Barichgasse 40-42, 1030 Wien",
    "phone": "1 52152 2550",
    "phone_code": "+43",
    "email": "dsb@dsb.gv.at",
    "website": "http://www.dsb.gv.at/",
    "member": {
      "name": "Dr Andrea JELINEK",
      "title": "Director"
    }
  },
  "DK": {
    "country": "Denmark",
    "language_code": "da",
    "name": "Datatilsynet",
    "addressFormatted": "Borgergade 28, 5",
    "phone": "33 1932 00",
    "phone_code": "+45",
    "email": "dt@datatilsynet.dk",
    "website": "http://www.datatilsynet.dk/",
    "member": {
      "name": "Ms Cristina Angela GULISANO",
      "title": "Director"
    }
  },
  "GB": {
    "country": "United Kingdom",
    "language_code": "en",
    "name": "The Information Commissioner’s Office",
    "addressFormatted": "Water Lane, Wycliffe House Wilmslow - Cheshire SK9 5AF",
    "phone": "1625 545 700",
    "phone_code": "+44",
    "email": "casework@ico.org.uk",
    "website": "https://ico.org.uk",
    "member": {
      "name": "Ms Elizabeth DENHAM",
      "title": "Information Commissioner"
    }
  },
  "BE": {
    "country": "Belgium",
    "language_code": "fr",
    "name": "Autorité de la protection des données - Gegevensbeschermingsautoriteit (APD-GBA)",
    "addressFormatted": "Rue de la Presse 35 – Drukpersstraat 35 1000 Bruxelles - Brussel",
    "phone": "2 274 48 00",
    "phone_code": "+32",
    "email": "contact@apd-gba.be",
    "website": "https://www.autoriteprotectiondonnees.be/",
    "member": {
      "name": "Mr David Stevens",
      "title": "President"
    }
  },
  "BG": {
    "country": "Bulgaria",
    "language_code": "bg",
    "encoding": "latin",
    "name": "Commission for Personal Data Protection",
    "addressFormatted": "2, Prof. Tsvetan Lazarov blvd. Sofia 1592",
    "phone": "2 915 3580",
    "phone_code": "+359",
    "email": "kzld@cpdp.bg",
    "website": "https://www.cpdp.bg/",
    "member": {
      "name": "Mr Ventsislav KARADJOV",
      "title": "Chairman of the Commission for Personal Data Protection"
    }
  },
  "HR": {
    "country": "Croatia",
    "language_code": "hr",
    "name": "Croatian Personal Data Protection Agency",
    "addressFormatted": "Martićeva 14 10000 Zagreb",
    "phone": "1 4609 000",
    "phone_code": "+385",
    "email": "azop@azop.hr",
    "website": "https://azop.hr",
    "member": {
      "name": "Mr Anto RAJKOVAČA",
      "title": "Director"
    }
  },
  "CY": {
    "country": "Cyprus",
    "language_code": "el",
    "name": "Commissioner for Personal Data Protection",
    "addressFormatted": "1 Iasonos Street,\n1082 Nicosia\nP.O. Box 23378, CY-1682 Nicosia",
    "phone": "22 818 456",
    "phone_code": "+357",
    "email": "commissioner@dataprotection.gov.cy",
    "website": "http://www.dataprotection.gov.cy",
    "member": {
      "name": "Ms Irene LOIZIDOU NIKOLAIDOU",
      "title": "Commissioner for Personal Data Protection"
    }
  },
  "CZ": {
    "country": "Czech Republic",
    "language_code": "cz",
    "name": "Office for Personal Data Protection",
    "addressFormatted": "Pplk. Sochora 27\n170 00 Prague 7",
    "phone": "234 665 111",
    "phone_code": "+420",
    "email": "posta@uoou.cz",
    "website": "https://www.uoou.cz",
    "member": {
      "name": "Ms Ivana JANŮ",
      "title": "President"
    }
  },
  "EE": {
    "country": "Estonia",
    "language_code": "et",
    "name": "Estonian Data Protection Inspectorate (Andmekaitse Inspektsioon)",
    "addressFormatted": "Tatari 39\n10134 Tallinn",
    "phone": "6828 712",
    "phone_code": "+372",
    "website": "https://www.aki.ee",
    "email": "info@aki.ee",
    "member": {
      "name": "Ms Pille Lehis",
      "title": "Director General"
    }
  },
  "FI": {
    "country": "Finland",
    "language_code": "fi",
    "name": "Office of the Data Protection Ombudsman",
    "addressFormatted": "P.O. Box 800\nFIN-00521 Helsinki",
    "phone": "29 56 66700",
    "phone_code": "+358",
    "website": "https://tietosuoja.fi/en",
    "email": "tietosuoja@om.fi",
    "member": {
      "name": "Mr Reijo AARNIO",
      "title": "Ombudsman"
    }
  },
  "FR": {
    "country": "France",
    "language_code": "fr",
    "name": "Commission Nationale de l'Informatique et des Libertés - CNIL",
    "addressFormatted": "3 Place de Fontenoy\nTSA 80715 – 75334 Paris, Cedex 07",
    "phone": "1 53 73 22 22",
    "phone_code": "+33",
    "website": "http://www.cnil.fr/",
    "email": "null",
    "member": {
      "name": "Ms Marie-Laure DENIS",
      "title": "President of CNIL"
    }
  },
  "GR": {
    "country": "Greece",
    "language_code": "en",
    "name": "Hellenic Data Protection Authority",
    "addressFormatted": "Kifisias Av. 1-3, PC 11523\nAmpelokipi Athens",
    "phone": "210 6475 600",
    "phone_code": "+30",
    "website": "http://www.dpa.gr/",
    "email": "contact@dpa.gr",
    "member": {
      "name": "Mr Konstantinos Menoudakos",
      "title": "President of the Hellenic Data Protection Authority"
    }
  },
  "HU": {
    "country": "Hungary",
    "language_code": "hu",
    "name": "Hungarian National Authority for Data Protection and Freedom of Information",
    "addressFormatted": "Szilágyi Erzsébet fasor 22/C\nH-1125 Budapest",
    "phone": "1 3911 400",
    "phone_code": "+36",
    "website": "http://www.naih.hu/",
    "email": "peterfalvi.attila@naih.hu",
    "member": {
      "name": "Dr Attila PÉTERFALVI",
      "title": "President of the National Authority for Data Protection and Freedom of Information"
    }
  },
  "IE": {
    "country": "Ireland",
    "language_code": "en",
    "name": "Data Protection Commission",
    "addressFormatted": "21 Fitzwilliam Square\nDublin 2\nD02 RD28\nIreland",
    "phone": "76 110 4800",
    "phone_code": "+353",
    "email": "info@dataprotection.ie",
    "website": "http://www.dataprotection.ie/",
    "member": {
      "name": "Ms Helen DIXON",
      "title": "Data Protection Commissioner"
    }
  },
  "IT": {
    "country": "Italy",
    "language_code": "it",
    "name": "Garante per la protezione dei dati personali",
    "addressFormatted": "Piazza di Monte Citorio, 121\n00186 Roma",
    "phone": "06 69677 1",
    "phone_code": "+39",
    "email": "garante@garanteprivacy.it",
    "website": "http://www.garanteprivacy.it/",
    "member": {
      "name": "Mr Antonello SORO",
      "title": "President of Garante per la protezione dei dati personali"
    }
  },
  "LV": {
    "country": "Latvia",
    "language_code": "lv",
    "name": "Data State Inspectorate",
    "addressFormatted": "Blaumana str. 11/13-15\n1011 Riga",
    "phone": "6722 3131",
    "phone_code": "+371",
    "email": "info@dvi.gov.lv",
    "website": "https://www.dvi.gov.lv",
    "member": {
      "name": "Ms DAIGA AVDEJANOVA",
      "title": "Director of Data State Inspectorate"
    }
  },
  "LT": {
    "country": "Lithuania",
    "language_code": "lv",
    "name": "State Data Protection Inspectorate",
    "addressFormatted": "A. Juozapaviciaus str. 6\nLT-09310 Vilnius",
    "phone": "5 279 14 45",
    "phone_code": "+370",
    "email": "ada@ada.lt",
    "website": "https://vdai.lrv.lt",
    "member": {
      "name": "Mr Raimondas Andrijauskas",
      "title": "Director of the State Data Protection Inspectorate"
    }
  },
  "LU": {
    "country": "Luxembourg",
    "language_code": "fr",
    "name": "Commission Nationale pour la Protection des Données",
    "addressFormatted": "1, avenue du Rock’n’Roll\nL-4361 Esch-sur-Alzette",
    "phone": "2610 60 1",
    "phone_code": "+352",
    "email": "info@cnpd.lu",
    "website": "https://cnpd.public.lu",
    "member": {
      "name": "Ms Tine A. LARSEN",
      "title": "President of the Commission Nationale pour la Protection des Données"
    }
  },
  "MT": {
    "country": "Malta",
    "language_code": "en",
    "name": "Office of the Information and Data Protection Commissioner",
    "addressFormatted": "Second Floor, Airways House\nHigh Street, Sliema SLM 1549",
    "phone": "2328 7100",
    "phone_code": "+356",
    "email": "idpc.info@idpc.org.mt",
    "website": "https://idpc.org.mt/en/Pages/Home.aspx",
    "member": {
      "name": "Mr Saviour CACHIA,",
      "title": "Information and Data Protection Commissioner"
    }
  },
  "NL": {
    "country": "Netherlands",
    "language_code": "nl",
    "name": "Autoriteit Persoonsgegevens",
    "addressFormatted": "Bezuidenhoutseweg 30\nP.O. Box 93374\n2509 AJ Den Haag/The Hague",
    "phone": "70 888 8500",
    "phone_code": "+31",
    "email": "null",
    "website": "https://autoriteitpersoonsgegevens.nl",
    "member": {
      "name": "Mr Aleid WOLFSEN",
      "title": "Chairman of the Autoriteit Persoonsgegevens"
    }
  },
  "PO": {
    "country": "Poland",
    "language_code": "pl",
    "name": "Urząd Ochrony Danych Osobowych (Personal Data Protection Office)",
    "addressFormatted": "ul. Stawki 2\n00-193 Warsaw",
    "phone": "22 531 03 00",
    "phone_code": "+48",
    "email": "kancelaria@uodo.gov.pl;zwme@uodo.gov.pl",
    "website": "https://uodo.gov.pl/",
    "member": {
      "name": "Mr Jan NOWAK",
      "title": "President of the Personal Data Protection Office"
    }
  },
  "PT": {
    "country": "Portugal",
    "language_code": "pt",
    "name": "Comissão Nacional de Protecção de Dados - CNPD",
    "addressFormatted": "Av. D. Carlos I, 134, 1º\n1200-651 Lisboa",
    "phone": "21 392 84 00",
    "phone_code": "+351",
    "email": "geral@cnpd.pt",
    "website": "https://www.cnpd.pt",
    "member": {
      "name": "Ms Filipa CALVÃO",
      "title": "President, Comissão Nacional de Protecção de Dados"
    }
  },
  "RO": {
    "country": "Romania",
    "language_code": "ro",
    "name": "The National Supervisory Authority for Personal Data Processing",
    "addressFormatted": "B-dul Magheru 28-30\nSector 1, BUCUREŞTI",
    "phone": "31 805 9211",
    "phone_code": "+40",
    "email": "anspdcp@dataprotection.ro",
    "website": "https://www.dataprotection.ro",
    "member": {
      "name": "Ms Ancuţa Gianina OPRE",
      "title": "President of the National Supervisory Authority for Personal Data Processing"
    }
  },
  "SK": {
    "country": "Slovakia",
    "language_code": "sk",
    "name": "Office for Personal Data Protection of the Slovak Republic",
    "addressFormatted": "Hraničná 12\n820 07 Bratislava 27",
    "phone": "2 32 31 32 14",
    "phone_code": "+421",
    "email": "statny.dozor@pdp.gov.sk",
    "website": "https://dataprotection.gov.sk",
    "member": {
      "name": "Ms Soňa PŐTHEOVÁ",
      "title": "President of the Office for Personal Data Protection of the Slovak Republic"
    }
  },
  "SL": {
    "country": "Slovenia",
    "language_code": "sl",
    "name": "Information Commissioner of the Republic of Slovenia",
    "addressFormatted": "Ms Mojca Prelesnik\nDunajska 22\n1000 Ljubljana",
    "phone": "1 230 9730",
    "phone_code": "+386",
    "email": "gp.ip@ip-rs.si",
    "website": "https://www.ip-rs.si",
    "member": {
      "name": "Ms Mojca PRELESNIK",
      "title": "Information Commissioner of the Republic of Slovenia"
    }
  },
  "ES": {
    "country": "Spain",
    "language_code": "es",
    "name": "Agencia Española de Protección de Datos (AEPD)",
    "addressFormatted": "C/Jorge Juan, 6\n28001 Madrid",
    "phone": "91 266 3517",
    "phone_code": "+34",
    "email": "internacional@aepd.es",
    "website": "https://www.aepd.es",
    "member": {
      "name": "Ms María del Mar España Martí",
      "title": "Director of the Spanish Data Protection Agency"
    }
  },
  "SE": {
    "country": "Sweden",
    "language_code": "se",
    "name": "Datainspektionen",
    "addressFormatted": "Drottninggatan 29\n5th Floor\nBox 8114\n104 20 Stockholm",
    "phone": "8 657 6100",
    "phone_code": "+46",
    "email": "datainspektionen@datainspektionen.se",
    "website": "https://www.datainspektionen.se",
    "member": {
      "name": "Ms Lena Lindgren Schelin",
      "title": "Director General of the Data Inspection Board"
    }
  },
  "DE": {
    "country": "Germany",
    "language_code": "de",
    "name": "Die Bundesbeauftragte für den Datenschutz und die Informationsfreiheit",
    "addressFormatted": "Husarenstraße 30\n53117 Bonn",
    "phone": "228 997799 0; 228 81995 0",
    "phone_code": "+49",
    "email": "poststelle@bfdi.bund.de",
    "website": "https://www.bfdi.bund.de",
    "member": {
      "name": "Mr Ulrich KELBER",
      "title": "Federal Commissioner for Data Protection and Freedom of Information"
    }
  },
  "EDPB": {
    "country": "EDPB",
    "language_code": "en",
    "name": "European Data Protection Board",
    "addressFormatted": "Rue Montoyer 30, B-1000 Brussels",
    "phone": "NA",
    "phone_code": "NA",
    "email": "NA",
    "website": "https://edpb.europa.eu/edpb_en",
    "member": {
      "name": "NA",
      "title": "NA"
    }
  }
}

'''
print("Path: ")
print(os.path.abspath("pygdpr/assets/dpa-info.json"))

if os.path.isfile(os.path.abspath("pygdpr/assets/dpa-info.json")):
    with open(os.path.abspath("pygdpr/assets/dpa-info.json"), 'r') as f:
        supported_dpas = json.load(f)
'''

class GoogleTranslatePriceError(Exception):
   """An exception class raised when the Google Translate price exceeds a predfined threshold (in usd)."""
   pass

class MaxRetriesError(Exception):
   """An exception class raised when maximum number of retries, trying to get docs, is exceeded."""
   pass

class DPA(object):
    """
    A class used to represent a DPA (Data Protection Authority).

    Attributes
    ----------
    country_code : str
        a two letter iso_code corresponding to a given country
    language_code : str
        a two letter iso_code referring to the written language 'preferred' by DPA
    name : str
        the official name of the DPA
    address : str
        formatted address string for the DPA
    phone : str
        formatted phone string for the DPA
    website : str
        official website of the DPA
    path : str
        the path where the documents, for this particular DPA, will be stored (default is os.cwd())
    translate_client : google.cloud.translate_v2.client.Client
        translate client for google-cloud-translate (see: https://googleapis.dev/python/translation/latest/client.html?highlight=client#module-google.cloud.translate_v2.client)

    Methods
    -------
    set_path(path)
        Sets the path to the given parameter. Stores documents at this path.
    set_translate_client(translate_client)
        Sets the translate_client to the given parameter. Client is used in :func:`~gdpr.dpa.DPA.translate_docs` to translate the DPA's documents at the specified path.
    get_docs(overwrite=False, to_print=True)
        Gets the documents for the DPA, stores them at the specified path and returns a list (md5 hashes) of documents added.
    translate_docs(target_languages, docs=[], overwrite=False, price_terminate_usd=0.0, quota_service=None, to_print=True)
        Translates the documents, located at the specified path, into the target languages and returns a list (md5 hashes) of documents translated.
    """
    def __init__(self, country_code, path):
        """
        Parameters
        ----------
        country_code : str
            The country_code for the country where the DPA has authority.
        """
        country_code = country_code.upper()

        # TODO: Determine if we need to do theses checks or not...
        #if EUMemberSpecification().is_satisfied_by(country_code) is False:
            #raise ValueError(f"Not found valid EU Member state for country code: {country_code}")
        #if SupportedDPASpecification().is_satisfied_by(country_code) is False:
            #raise ValueError(f"Not found supported DPA for country code: {country_code}")
        self.country_code = country_code

        dpa = supported_dpas[country_code]
        self.country = dpa['country']
        self.language_code = dpa['language_code']
        self.encoding = dpa['encoding'] if 'encoding' in dpa.keys() else None
        self.name = dpa['name']
        self.address = dpa['addressFormatted']
        self.phone = '({}) {}'.format(dpa['phone_code'], dpa['phone'])
        self.email = dpa['email']
        self.website = dpa['website']
        self.member = dpa['member']

        # DPA path is now whatever the user inputs
        self.path = path
        self.translate_client = None

    def set_path(self, path):
        self.path = path

    def set_translate_client(self, translate_client):
        self.translate_client = translate_client

    def update_pagination(self, pagination=None, page_soup=None, driver=None):
        """Updates and or creates a new pagination instance.

        Parameters
        ----------
        pagination : Pagination
            If pagination is None, a new pagination instance is created from scratch.
            Otherwise the pagination is updated with a new item.
        page_soup : Soup
            If page_soup is not None, this will be used to find and add the next item to the pagination.
        driver : Selenium
            If driver is not None, this will be used to find and add the next item to the pagination.

        Raises
        ------
        NotImplementedError
            If no subclass (ie. EU member state DPA) has implemented this method.

        Returns
        -------
        Pagination
            an updated pagination instance
        """
        raise NotImplementedError("'update_pagination' method not implemented.")

    def get_source(self, page_url=None, driver=None):
        """Returns a page source given either a page_url or a driver as input.

        Parameters
        ----------
        page_url : str
            If page_url is not None, this will be used to get the page source.
        driver : Selenium
            If driver is not None, this will be used to get the page source.

        Raises
        ------
        NotImplementedError
            If no subclass (ie. EU member state DPA) has implemented this method.

        Returns
        -------
        str
            a page source response from an html page.
        """
        raise NotImplementedError("'get_source' method not implemented.")

    def get_docs(self, existing_docs=[], overwrite=False, to_print=True):
        """Gets the documents for the DPA, stores them at the specified path and returns a list (md5 hashes) of documents added.

        Parameters
        ----------
        overwrite : bool
            If True, will overwrite the already existing documents at specified path.
            Otherwise will skip, if documents are already added.
        to_print : bool
            If True will print the progress of getting the documents.

        Raises
        ------
        NotImplementedError
            If no subclass (ie. EU member state DPA) has implemented this method.

        Returns
        -------
        [str]
            a list of documents (md5 hashes)
        """
        raise NotImplementedError("'get_docs' method not implemented.")

    def translate_docs(self, target_languages, docs=[], overwrite=False, price_terminate_usd=0.0, quota_service=None, to_print=True):
        """Translates the documents, located at the specified path, into the target languages and returns a list (md5 hashes) of documents translated.

        Parameters
        ----------
        target_languages : [str]
            A list of two letter iso_codes (language_codes) the documents will be translated into.
        docs : [str]
            A list of documents (md5 hashes) that needs to be translated. If list is empty it's assumed all documents at path should be translated.
        overwrite : bool
            If True, will overwrite the already existing documents at specified path.
            Otherwise will skip, if documents are already added.
        price_terminate_usd : float
            If price of translating the documents exceeds the price_terminate_usd parameter a GoogleTranslatePriceError will be raised.
            If price_terminate_usd is zero no GoogleTranslatePriceError will be raised.
        quota_service : TranslateQuotaService
            An instance of the TranslateQuotaService class which specifies the quota allowed for the google-cloud project with enabled google-cloud-translate api.
            If None is specified, default quota limits will be assumed. (See: https://cloud.google.com/translate/quotas)
        to_print : bool
            If True will print the progress of getting the documents.

        Returns
        -------
        [str]
            a list of translated documents (md5 hashes)
        """
        translated_docs = []
        target_languages = list(set(target_languages).difference(self.language_code))
        if self.translate_client is None:
            self.translate_client = translate.Client()
        price_service = TranslatePriceService()
        if quota_service is None:
            quota_service = TranslateQuotaService()
        agg_price = 0.0
        agg_quota = 0
        time_window_secs = 100
        for root,dirs,files in os.walk(self.path, topdown=True):
            if list(filter(lambda x: x.endswith('.txt'), files)) == 0:
                continue
            time.sleep(3)
            doc = root.split('/')[-1]
            if to_print and len(doc) > 0:
                print("Translating document:\t", doc)
                if doc in docs:
                    print("Progress:", docs.index(doc)/float(len(docs)))
            """if RootDocumentSpecification(root).is_satisfied_by(doc) is False:
                continue"""
            if TranslateDocumentSpecification(docs).is_satisfied_by(doc) is False:
                continue
            file_languages = list(filter(lambda x: len(x) == 2, [x.split('.')[0] for x in files]))
            for name in files:
                if TranslateFilePolicy().is_allowed(name) is False:
                    continue
                if PriceTerminateTranslateSpecification(price_terminate_usd).is_satisfied_by(agg_price):
                    raise GoogleTranslatePriceError(f"Estimated price of Google Translate exceeded value of {price_terminate_usd}.")
                with open(root + '/' + name, 'r', encoding='utf-8') as f:
                    document_text = f.read()
                    next_quota = agg_quota + len(document_text)
                    #if NotReachedDailyTranslateQuotaSpec(quota_service).is_satisfied_by(next_quota):
                    #    raise ValueError('Reached characters per day: %d. Please wait 24 hours until making another request.', agg_quota)
                    if NotReached100SecsTranslateQuotaSpec(quota_service).is_satisfied_by(next_quota):
                        if to_print:
                            print('Reached characters per 100 seconds per project per user: %d. sleeping %d secs before making next request.' % (agg_quota, time_window_secs))
                        time.sleep(time_window_secs+5)
                        agg_quota = 0
                    for target_language in target_languages:
                        if overwrite == True or\
                           NotExistsFileLanguageSpecification(file_languages).is_satisfied_by(target_language) == False:
                            continue
                        response = None
                        try:
                            # https://googleapis.dev/python/translation/latest/client.html
                            response = self.translate_client.translate(
                                document_text,
                                target_language=target_language,
                                format_='text' # text or html?
                            )
                        except:
                            if to_print:
                                print('Could not translate:\t', doc)
                            pass
                        if response is None:
                            continue
                        translated_text = response['translatedText']
                        with open(root + '/' + target_language + '.txt', 'w') as f:
                            f.write(translated_text)
                        agg_price += price_service.price_for_text(document_text)
                        agg_quota += len(document_text)
                        translated_docs.append(doc)
                        if to_print:
                            print('Translated:\t', doc)
                            print('\tFile:\t', name)
                            print('\tPrice:\t', agg_price)
        return translated_docs

    def extract_metadata(self, pipeline=[
        ('summary', SummaryMetadataService()),
        ('timeline', TimelineMetadataService()),
        ('citations', CitationsMetadataService()),
        ('citationsCount', CitationsCountMetadataService()),
        ('keywords', KeywordsMetadataService()),
        ('statistics', StatisticsMetadataService())
    ], docs=[], to_print=True):
        """Extracts the metadata from the documents.

        Parameters
        ----------
        pipeline : [tuple]
            A list of tuples where:
            First value in the tuple is a key of the metadata json file.
            Second value in the tuple is a value computed from the MetadataService method for_text
        docs : [str]
            A list of documents (md5 hashes) that requires metadata extraction. If list is empty it's assumed all documents at path should be translated.
        to_print : bool
            If True will print the progress of getting the documents.

        Returns
        -------
        [str]
            a list of documents (md5 hashes)
        """
        extracted_metadata = []
        for root, dirs, files in os.walk(self.path, topdown=True):
            print(root, dirs, files)
            split = root.split('/')
            if len(split) <= 4:
                continue
            country = split[-2]
            country = country.replace('-', ' ')
            country = ' '.join([word.capitalize() for word in country.split(' ')])
            if country != self.country:
                continue
            if 'en.txt' not in files:
                continue
            if 'metadata.json' not in files:
                continue
            if to_print:
                print('Country:\t', country)
            document_hash = split[-1]
            if document_hash not in docs:
                continue
            if to_print:
                print('Extracting metadata for:\t', document_hash)
            f = open(root + '/' + 'metadata.json', 'r')
            metadata = json.load(f)
            f.close()
            f = open(root + '/' + 'en.txt')
            document_text = f.read()
            f.close()
            for key, meta_service in pipeline:
                metadata[key] = meta_service.for_text(document_text)
            f = open(root + '/' + 'metadata.json', 'w')
            json.dump(metadata, f, indent=4, sort_keys=True)
            f.close()
            extracted_metadata.append(document_hash)
        return extracted_metadata
