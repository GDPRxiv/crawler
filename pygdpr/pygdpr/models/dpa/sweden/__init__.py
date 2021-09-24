import os
import math
import requests
import json
import time
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

class Sweden(DPA):
    def __init__(self, path=os.curdir):
        country_code='se'
        super().__init__(country_code, path)

    def update_pagination(self, pagination=None, page_soup=None, driver=None):
        source = {
            "host": "https://www.datainspektionen.se",
            "start_path": "/nyheter"
        }
        host = source['host']
        start_path = source['start_path']
        if pagination is None:
            pagination = Pagination()
            pagination.add_item(host + start_path + "?query=&page=4")
        else:
            # pagination = Pagination()
            for i in range(5, 1000):
                page_href = "?query=&page={}".format(i)
                pagination.add_item(host + start_path + page_href)
            """pagination_list = page_soup.find('ul', class_='pagination-list')
            if pagination_list is not None:
                for li in pagination_list.find_all('li', class_='list-item'):
                    page_link = li.find('a')
                    if page_link is None:
                        continue
                    page_href = page_link.get('href')
                    print("pagination link:", host + start_path + page_href)
                    pagination.add_item(host + start_path + page_href)"""
        return pagination

    def get_source(self, page_url=None, driver=None):
        assert (page_url is not None)
        results_response = None
        try:
            results_response = requests.request('GET', page_url)
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
            result_list = results_soup.find('ul', {'id': 'imy-search__results-list-initial'})
            assert result_list
            # s1. Results
            for li in result_list.find_all('li', class_='imy-search__results-item'):
                time.sleep(5)
                item_created = li.find('time', class_='imy-search-hit__detail-text')
                assert item_created
                date_str = item_created.get('datetime')
                tmp = dateparser.parse(date_str, date_formats=['%d %B %Y'])
                date = datetime.date(tmp.year, tmp.month, tmp.day)
                if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                    continue
                item_header = li.find('h2', class_='imy-search-hit__heading')
                assert item_header
                # s2. Documents
                document_title = item_header.get_text()
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite == False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue
                item_link = li.find('a')
                assert item_link
                document_href = item_link.get('href')
                assert document_href
                document_url = document_href
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
                newspage = document_soup.find('div', class_='imy-newspage')
                assert newspage
                file_href = None
                file_links = [link for link in newspage.find_all('a') if link.get('href').endswith('.pdf')]
                for link in file_links:
                    if 'svenska' not in link.get_text().split(' '):
                        file_href = file_links[0].get('href')
                if file_href is None and len(file_links) > 0:
                    file_href = file_links[0].get('href')
                dpa_folder = self.path
                document_folder = dpa_folder + '/' + document_hash
                try:
                    os.makedirs(document_folder)
                except FileExistsError:
                    pass
                if file_href is None:
                    continue
                host = "https://www.datainspektionen.se"
                file_url = host + file_href
                file_response = None
                try:
                    file_response = requests.request('GET', file_url)
                    file_response.raise_for_status()
                except requests.exceptions.HTTPError as error:
                    pass
                if file_response is None:
                    continue
                file_content = file_response.content
                try:
                    with open(document_folder + '/' + self.language_code + '.pdf', 'wb') as f:
                        f.write(file_content)
                    with open(document_folder + '/' + self.language_code + '.txt', 'wb') as f:
                        document_text = textract.process(document_folder + '/' + self.language_code + '.pdf')
                        f.write(document_text)
                except:
                    with open(document_folder + '/' + self.language_code + '.txt', 'w') as f:
                        document_text = newspage.get_text().strip()
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