import os
import math
import requests
import json
import datetime
import hashlib
import dateparser
import re
import csv
from pygdpr.models.dpa import DPA
from bs4 import BeautifulSoup
from pygdpr.services.filename_from_path_service import filename_from_path_service
from pygdpr.services.pdf_to_text_service import PDFToTextService
from pygdpr.specifications import pdf_file_extension_specification
from pygdpr.specifications.should_retain_document_specification import ShouldRetainDocumentSpecification
from pygdpr.models.common.pagination import Pagination
from pygdpr.policies.gdpr_policy import GDPRPolicy
import textract

class Portugal(DPA):
    def __init__(self, path=os.curdir):
        country_code='pt'
        super().__init__(country_code, path)

    def update_pagination(self, pagination=None, page_soup=None, driver=None):
        source = {
            "host": "https://www.cnpd.pt",
            "start_path": "/decisoes/historico-de-decisoes"
        }
        host = source['host']
        start_path = source['start_path']
        if pagination is None:
            pagination = Pagination()
            for year in range(2021, 2017, -1):
                pagination.add_item(host + start_path + "/?year={year}&type=&ent=".format(year=year))
        else:
            c_pagination = page_soup.find('div', class_='c-pagination')
            if c_pagination is not None:
                for a in c_pagination('a'):
                    page_href = a.get('href')
                    pagination.add_item(host + page_href)
        return pagination

    def get_source(self, page_url=None, driver=None):
        assert (page_url is not None)
        results_response = None
        try:
            results_response = requests.request('GET', page_url, verify=False)
            results_response.raise_for_status()
        except requests.exceptions.HTTPError as error:
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
            assert results_soup
            layout = results_soup.find('div', class_='layout')
            assert layout
            for c_card in layout.find_all('div', class_='c-card'):
                result_link = c_card.find('a')
                if result_link is None:
                    continue
                # s2. Documents
                document_title = result_link.find('div', 'c-card-header-medium')
                assert document_title
                document_title = document_title.get_text()
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite == False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue
                document_href = result_link.get('href')
                host = "https://www.cnpd.pt"
                document_url = host + document_href
                if to_print:
                    print("\tDocument:\t", document_hash)
                document_response = None
                try:
                    document_response = requests.request('GET', document_url, verify=False)
                    document_response.raise_for_status()
                except requests.exceptions.HTTPError as error:
                    if to_print:
                        print(error)
                    pass
                if document_response is None:
                    continue
                document_content = document_response.content
                dpa_folder = self.path
                document_folder = dpa_folder + '/' + document_hash
                try:
                    os.makedirs(document_folder)
                except FileExistsError:
                    pass
                with open(document_folder + '/' + self.language_code + '.pdf', 'wb') as f:
                    f.write(document_content)
                with open(document_folder + '/' + self.language_code + '.txt', 'w') as f:
                    document_text = PDFToTextService().text_from_pdf_path(document_folder + '/' + self.language_code + '.pdf')
                    f.write(document_text)
                with open(document_folder + '/' + 'metadata.json', 'w') as f:
                    metadata = {
                        'title': {
                            self.language_code: document_title
                        },
                        'md5': document_hash,
                        'releaseDate': None,
                        'url': document_url
                    }
                    json.dump(metadata, f, indent=4, sort_keys=True)
                added_docs.append(document_hash)
        return added_docs