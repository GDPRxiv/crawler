import os
import shutil
import math
import requests
import json
import datetime
import hashlib
import textract
from pygdpr.models.dpa import DPA
from bs4 import BeautifulSoup
import dateparser
from pygdpr.services.filename_from_path_service import filename_from_path_service
from pygdpr.specifications import pdf_file_extension_specification
from pygdpr.specifications.should_retain_document_specification import ShouldRetainDocumentSpecification
from pygdpr.models.pagination import Pagination
from pygdpr.policies.gdpr_policy import GDPRPolicy
from pygdpr.services.pdf_to_text_service import PDFToTextService

class UnitedKingdom(DPA):
    def __init__(self, path):
        country_code='GB'
        super().__init__(country_code, path)

    def update_pagination(self, pagination=None, page_soup=None, driver=None):
        source = {
            "host": "https://ico.org.uk",
            "start_path": "/action-weve-taken/enforcement/?rows=1000000"
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
            maincolumn = results_soup.find('div', class_='maincolumn')
            assert maincolumn
            resultlist = maincolumn.find('div', class_='resultlist')
            assert resultlist
            # s1. Results
            for itemlink in resultlist.find_all('div', class_='itemlink'):
                result_link = itemlink.find('a')
                assert result_link
                text_small = result_link.find('p', class_='text-small')
                assert text_small
                date_str = text_small.get_text().split(',')[0].strip()
                tmp = datetime.datetime.strptime(date_str, '%d %B %Y')
                date = datetime.date(tmp.year, tmp.month, tmp.day)
                if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                    continue
                # s2. Documents
                h2 = result_link.find('h2', class_='h3')
                assert h2
                document_title = h2.get_text().strip()
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite == False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue
                document_href = result_link.get('href')
                assert document_href
                host = "https://ico.org.uk"
                document_url = host + document_href
                if to_print:
                    print("\tDocument:\t", document_hash)
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
                dpa_folder = self.path
                document_folder = dpa_folder + '/' + document_hash
                try:
                    os.makedirs(document_folder)
                except FileExistsError:
                    pass
                file_url = None
                aside = document_soup.find('aside', class_='aside-further')
                if aside is not None:
                    ul = aside.find('ul')
                    assert ul
                    file_url = None
                    for li in ul.find_all('li'):
                        file_link = li.find('a')
                        assert file_link
                        file_href = file_link.get('href')
                        if file_href.endswith('.pdf'):
                            file_url = host + file_href
                            break
                if file_url is not None:
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
                    with open(document_folder + '/' + self.language_code + '.pdf', 'wb') as f:
                        f.write(file_content)
                    with open(document_folder + '/' + self.language_code + '.txt', 'w') as f:
                        document_text = PDFToTextService().text_from_pdf_path(document_folder + '/' + self.language_code + '.pdf')
                        f.write(document_text)
                else:
                    article_content = document_soup.find('div', class_='article-content')
                    assert article_content
                    document_text = article_content.get_text().strip()
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
        return added_docs
