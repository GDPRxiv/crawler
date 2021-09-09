import os
import math
import requests
import json
import datetime
import hashlib
from pygdpr.models.dpa import DPA
from bs4 import BeautifulSoup
from pygdpr.services.filename_from_path_service import filename_from_path_service
from pygdpr.services.pdf_to_text_service import PDFToTextService
from pygdpr.specifications import pdf_file_extension_specification
from pygdpr.specifications.should_retain_document_specification import ShouldRetainDocumentSpecification
from pygdpr.models.pagination import Pagination
from pygdpr.policies.gdpr_policy import GDPRPolicy

class CzechRepublic(DPA):
    def __init__(self, path):
        country_code='CZ'
        super().__init__(country_code, path)

    def update_pagination(self, pagination=None, page_soup=None, driver=None):
        source = {
            "host": "https://www.uoou.cz",
            "start_path": "/vismo/zobraz_dok.asp?id_org=200144&id_ktg=1022&n=z-rozhodovaci-cinnosti-uradu&p1=1277"
        }
        host = source['host']
        start_path = source['start_path']
        if pagination is None:
            pagination = Pagination()
            pagination.add_item(host + start_path)
        else:
            strlistovani = page_soup.find('div', class_='strlistovani')
            if strlistovani is not None:
                for a in strlistovani.find_all('a'):
                    page_href = a.get('href')
                    pagination.add_item(host + page_href)
        return pagination

    def get_source(self, page_url=None, driver=None):
        assert (page_url is not None)
        results_response = None
        try:
            results_response = requests.request('GET', page_url)
            results_response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            if to_print:
                print(error)
            pass
        return results_response

    def get_docs(self, existing_docs=[], overwrite=False, to_print=True):
        added_docs = []
        pagination = self.update_pagination()
        # s0. Pagination
        while pagination.has_next():
            page_url = pagination.get_next()
            if to_print:
                print('Page:\t', page_url)
            page_source = self.get_source(page_url=page_url)
            if page_source is None:
                continue
            results_soup = BeautifulSoup(page_source.text, 'html.parser')
            ui = results_soup.find('ul', class_='ui')
            assert ui
            # s1. Results
            for li in ui.find_all('li'):
                result_link = li.find('a')
                # s2. Documents
                document_title = result_link.get_text()
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite == False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue
                document_href = result_link.get('href')
                assert document_href
                host = "https://www.uoou.cz"
                document_url = host + document_href
                print('document_url:', document_url)
                document_response = None
                try:
                    document_response = requests.request('GET', document_url)
                    document_response.raise_for_status()
                except requests.exceptions.HTTPError as error:
                    if to_print:
                        print(error)
                    pass
                if document_response is None:
                    continue
                document_soup = BeautifulSoup(document_response.text, 'html.parser')
                assert document_soup
                popis = document_soup.find('div', class_='popis')
                if popis is None:
                    continue
                created_index = 0
                popis_text = popis.get_text()
                try:
                    date_str = popis_text.split(':')[-1].split('/')[created_index].strip()
                    tmp = datetime.datetime.strptime(date_str, '%-d.%-m.%Y')
                    date = datetime.date(tmp.year, tmp.month, tmp.day)
                except:
                    date = None
                    pass
                if date is None:
                    continue
                if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                    continue
                if to_print:
                    print("\tDocument:\t", document_hash)
                obsah = document_soup.find('div', class_='obsah')
                assert obsah
                document_text = obsah.get_text()
                document_text = document_text.lstrip()
                dpa_folder = self.path
                document_folder = dpa_folder + '/' + document_hash
                try:
                    os.makedirs(document_folder)
                except FileExistsError:
                    pass
                with open(document_folder + '/' + self.language_code + '.txt', 'w') as f:
                    f.write(document_text)
                with open(document_folder + '/' + 'metadata.json', 'w') as f:
                    metadata = {
                        'title': {
                            self.language_code: document_title
                        },
                        'md5': document_hash,
                        'releaseDate': date.strftime('%d/%m/%Y'),
                        'url': document_url
                    }
                    json.dump(metadata, f, indent=4, sort_keys=True)
                added_docs.append(document_hash)
            # s0. Pagination
            pagination = self.update_pagination(pagination=pagination, page_soup=results_soup)
        return added_docs
