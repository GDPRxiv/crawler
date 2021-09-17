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

class Latvia(DPA):
    def __init__(self, path=os.curdir):
        country_code='LV'
        super().__init__(country_code, path)

    def update_pagination(self, pagination=None, page_soup=None, driver=None):
        source = {
            "host": "https://www.dvi.gov.lv",
            "start_path": "/lv/jaunumi"
        }
        host = source['host']
        start_path = source['start_path']
        if pagination is None:
            pagination = Pagination()
            pagination.add_item(host + start_path)
        else:
            ul_pagination = page_soup.find('ul', class_='pagination')
            if ul_pagination is not None:
                for page_item in ul_pagination.find_all('li', class_='page-item'):
                    page_link = page_item.find('a')
                    if page_link is None:
                        continue
                    page_href = page_link.get('href')
                    pagination.add_item(host + start_path + page_href)
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
            articles_wrapper = results_soup.find('div', class_='articles-wrapper')
            assert articles_wrapper
            # s1. Results
            for views_row in articles_wrapper.find_all('div', class_='views-row'):
                article_details = views_row.find('div', class_='article-details')
                assert article_details
                date_div = article_details.find('div', class_='date')
                assert date_div
                date_str = date_div.get_text().strip()
                print('date_str:', date_str)
                tmp = datetime.datetime.strptime(date_str, '%d.%m.%Y.')
                date = datetime.date(tmp.year, tmp.month, tmp.day)
                if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                    continue
                article_info = views_row.find('div', class_='article-info')
                assert article_info
                title = article_info.find('div', class_='title')
                assert title
                a = title.find('a')
                # s2. Documents
                document_title = a.get_text()
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite == False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue
                host = 'https://www.dvi.gov.lv'
                result_link = a.get('href')
                document_href = result_link
                assert document_href
                document_url = host + document_href
                if to_print:
                    print("\tDocument:\t", document_hash)
                document_response = None
                try:
                    document_response = requests.request('GET', document_url)
                    document_response.raise_for_status()
                except requests.exceptions.HTTPError as error:
                    pass
                if document_response is None:
                    continue
                document_soup = BeautifulSoup(document_response.text, 'html.parser')
                content_area = document_soup.find('div', id='content-area')
                document_text = content_area.get_text()
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
