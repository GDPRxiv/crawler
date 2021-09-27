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




class Luxembourg(DPA):
    def __init__(self, path=os.curdir):
        country_code='lu'
        super().__init__(country_code, path)

    def update_pagination(self, pagination=None, page_soup=None, driver=None):
        source = {
            "host": "https://cnpd.public.lu",
            "start_path": "/fr/decisions-avis.html"
        }
        host = source['host']
        start_path = source['start_path']
        if pagination is None:
            pagination = Pagination()
            pagination.add_item(host + start_path)
        else:
            ol_pagination = page_soup.find('ol', class_='pagination')
            assert ol_pagination
            for li in ol_pagination.find_all('li', class_='pagination-page'):
                page_link = li.find('a')
                if page_link is None:
                    continue
                page_href = page_link.get('href')
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
            assert results_soup
            search_results = results_soup.find('ol', class_='search-results')
            assert search_results
            # s1. Results
            for li in search_results.find_all('li', recursive=False):
                time = li.find('time', class_='article-published')
                assert time
                date_str = time.get('datetime')
                tmp = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                date = datetime.date(tmp.year, tmp.month, tmp.day)
                if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                    continue
                article_title = li.find('h2', class_='article-title')
                assert article_title
                result_link = article_title.find('a')
                assert result_link
                # s2. Documents
                document_title = result_link.get_text()
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite == False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue
                document_href = result_link.get('href')
                assert document_href
                host = "https://cnpd.public.lu"
                document_url = host + document_href
                if to_print:
                    print("\tDocument:\t", document_hash)
                document_response = None
                try:
                    document_response = requests.request('GET', document_url)
                except requests.exceptions.HTTPError as error:
                    if to_print:
                        print(error)
                    pass
                if document_response is None:
                    continue
                document_soup = BeautifulSoup(document_response.text, 'html.parser')
                assert document_soup
                aside = document_soup.find('aside', class_='page-more')
                assert aside
                file_links = aside.find_all('a')
                file_url = None
                for file_link in file_links:
                    file_href = file_link.get('href')
                    if file_href.endswith('.pdf'):
                        if file_href.startswith('http') is False:
                            file_url = host + file_href
                        else:
                            file_url = file_href
                        break
                file_response = None
                try:
                    print('file_url:', file_url)
                    file_response = requests.request('GET', file_url)
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
                    try:
                        document_text = textract.process(document_folder + '/' + self.language_code + '.pdf')
                        f.write(document_text)
                    except:
                        pass
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
