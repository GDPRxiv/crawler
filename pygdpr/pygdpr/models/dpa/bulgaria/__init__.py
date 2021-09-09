import os
import math
import requests
import json
import datetime
from pygdpr.models.dpa import DPA
from bs4 import BeautifulSoup
from bs4.dammit import EncodingDetector
from pygdpr.services.filename_from_path_service import filename_from_path_service
from pygdpr.services.pdf_to_text_service import PDFToTextService
from pygdpr.specifications import pdf_file_extension_specification
from pygdpr.models.pagination import Pagination
from pygdpr.policies.gdpr_policy import GDPRPolicy
from pygdpr.specifications.should_retain_document_specification import ShouldRetainDocumentSpecification
from urllib.parse import urlparse
import hashlib
import textract

class Bulgaria(DPA):
    def __init__(self, path):
        country_code='BG'
        super().__init__(country_code, path)

    def update_pagination(self, pagination=None, page_soup=None, driver=None):
        source = {
            'host': 'https://www.cpdp.bg',
            'start_path': '/index.php?p=rubric_element&aid=1180'
        }
        host = source['host']
        start_path = source['start_path']
        if pagination is None:
            pagination = Pagination()
            pagination.add_item(host + start_path)
        else:
            pages = page_soup.find('div', class_='pages')
            if pages is not None:
                for page_link in pages.find_all('a'):
                    page_href = page_link.get('href')
                    print('page_href:', page_href)
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
            page_soup = self.get_source(page_url=page_url)
            if page_soup is None:
                continue
            results_soup = BeautifulSoup(page_soup.text, 'html.parser')
            assert results_soup
            center_part = results_soup.find('div', class_='center-part')
            assert center_part
            # s1. results
            for div in center_part.find_all('div', class_='news-home'):
                news_content = div.find('div', class_='news-content')
                assert news_content
                h6 = news_content.find('h6')
                assert h6
                result_link = h6.find('a')
                assert result_link
                document_title = result_link.get_text()
                date_str = document_title.split('/')[-1].split(' ')[0]
                if len(date_str.split('.')) != 3:
                    continue
                tmp = datetime.datetime.strptime(date_str, '%d.%m.%Y')
                date = datetime.date(tmp.year, tmp.month, tmp.day)
                if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                    continue
                # s2. Documents
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite == False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue
                document_href = result_link.get('href')
                assert document_href
                host = "https://www.cpdp.bg"
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
                document_center_part = document_soup.find('div', class_='center-part')
                assert document_center_part
                file_href = None
                for a in document_center_part.find_all('a'):
                    cand_href = a.get('href')
                    if cand_href is None:
                        continue
                    if cand_href.startswith('download'):
                        file_href = cand_href
                        break
                assert file_href
                file_url = host + '/' + file_href
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
                if len(file_response.text) == 0:
                    continue
                file_content = file_response.content
                if file_content is None:
                    continue
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
