import os
import math
import requests
import json
import datetime
import hashlib
import dateparser
import re
from pygdpr.models.dpa import DPA
from bs4 import BeautifulSoup
from pygdpr.services.filename_from_path_service import filename_from_path_service
from pygdpr.services.pdf_to_text_service import PDFToTextService
from pygdpr.specifications import pdf_file_extension_specification
from pygdpr.specifications.should_retain_document_specification import ShouldRetainDocumentSpecification
from pygdpr.models.common.pagination import Pagination
from pygdpr.policies.gdpr_policy import GDPRPolicy
import textract
import time

class Italy(DPA):
    def __init__(self, path=os.curdir):
        country_code='IT'
        super().__init__(country_code, path)

    def update_pagination(self, pagination=None, page_soup=None, driver=None):
        source = {
            "host": "https://www.garanteprivacy.it",
            "start_path": "/web/guest/home/stampa-comunicazione/interviste"
        }
        host = source['host']
        start_path = source['start_path']
        if pagination is None:
            pagination = Pagination()
            pagination.add_item(host + start_path)
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
            assert results_soup
            testo = results_soup.find('div', class_='testo')
            assert testo
            ul_all = testo.find_all('ul', recursive=False)
            # s1. Results
            for ul in ul_all:
                for li in ul.find_all('li'):
                    time.sleep(5)
                    result_link = li.find('a')
                    assert result_link
                    # s2. Document
                    document_title = result_link.get_text()
                    document_hash = hashlib.md5(document_title.encode()).hexdigest()
                    if document_hash in existing_docs and overwrite == False:
                        if to_print:
                            print('\tSkipping existing document:\t', document_hash)
                        continue
                    document_href = result_link.get('href')
                    if document_href.startswith('http') and document_href.startswith(host) is False:
                        continue
                    document_url = document_href
                    if document_href.startswith('http') is False:
                        host = "https://www.garanteprivacy.it"
                        document_url = host + document_url
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
                    scheda = document_soup.find('div', class_='scheda')
                    if scheda is None:
                        continue
                    dl = scheda.find('dl')
                    assert dl
                    date_index = -1
                    dt_all = dl.find_all('dt', recursive=False)
                    for i in range(len(dt_all)):
                        dt = dt_all[i]
                        if dt.get_text().strip().startswith('Data'):
                            date_index = i
                            break
                    if date_index == -1:
                        continue
                    dd_all = dl.find_all('dd')
                    assert dd_all
                    dd = dd_all[date_index]
                    date_str = dd.get_text().strip()
                    tmp = datetime.datetime.strptime(date_str, '%d/%m/%y')
                    date = datetime.date(tmp.year, tmp.month, tmp.day)
                    if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                        continue
                    pdf_form = document_soup.find('form', {'name': 'pdfForm'})
                    if pdf_form is None:
                        continue
                    action = pdf_form.get('action')
                    assert action
                    if to_print:
                        print("\tDocument:\t", document_hash)
                    file_url = action
                    file_response = None
                    try:
                        file_response = requests.request('GET', file_url)
                        file_response.raise_for_status()
                    except requests.exceptions.HTTPError as error:
                        if to_print:
                            print(error)
                        pass
                    if file_response is None:
                        continue
                    file_content = file_response.content
                    dpa_folder = self.path
                    document_folder = dpa_folder + '/' + document_hash
                    try:
                        os.makedirs(document_folder)
                    except FileExistsError:
                        pass
                    with open(document_folder + '/' + self.language_code + '.pdf', 'wb') as f:
                        f.write(file_content)
                    with open(document_folder + '/' + self.language_code + '.txt', 'wb') as f:
                        document_text = textract.process(document_folder + '/' + self.language_code + '.pdf')
                        document_text = document_text.strip()
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
        return added_docs
