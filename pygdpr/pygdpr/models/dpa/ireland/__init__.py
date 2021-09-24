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

class Ireland(DPA):
    def __init__(self, path=os.curdir):
        country_code='IE'
        super().__init__(country_code, path)

    def update_pagination(self, pagination=None, page_soup=None, driver=None):
        # ireland has two (official/primary) sources:
        # press releases and (latest) news.
        source = {
            "host": "https://www.dataprotection.ie",
            # "start_path": "/en/news-media/press-releases"
            "start_path": "/en/news-media/latest-news"
           
        }
        host = source['host']
        start_path = source['start_path']
        if pagination is None:
            pagination = Pagination()
            pagination.add_item(host + start_path)
        else:
            # pagination = Pagination()
            pager = page_soup.find('nav', class_='pager')
            if pager is None:
                return pagination
            pager_items = pager.find('ul', class_='pager__items')
            if pager_items is None:
                return pagination
            for pager_item in pager_items.find_all('li', 'pager__item'):
                page_link = pager_item.find('a')
                if page_link is None:
                    continue
                page_href = page_link.get('href')
                pagination.add_item(host + start_path + page_href)
                print('added link to pagination:', host + start_path + page_href)
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
            view_content = results_soup.find('div', class_='view-content')
            assert view_content
            item_list = view_content.find('div', class_='item-list')
            assert item_list
            ul = item_list.find('ul')
            assert ul
            # s1. Results
            for li in ul.find_all('li', recursive=False):
                time.sleep(5)
                article = li.find('article')
                assert article
                p_date = article.find('p', class_='date')
                assert p_date
                date_str = p_date.get_text().strip()
                regex = r"(\d\d)(st|nd|rd|th) (\w*) (\d\d\d\d)"

                matches = re.finditer(regex, date_str)
                matches = list(matches)
                if len(matches) == 0:
                    continue
                match = matches[0]
                groups = match.groups()
                date_suffix_group_num = 2
                date_str = date_str[:match.start(date_suffix_group_num)] + date_str[match.end(date_suffix_group_num):]
                tmp = datetime.datetime.strptime(date_str, '%d %B %Y')
                date = datetime.date(tmp.year, tmp.month, tmp.day)
                if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                    continue
                h2 = article.find('h2')
                assert h2
                result_link = h2.find('a')
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
                host = "https://www.dataprotection.ie"
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
                # Here is where we parse the document_url page (which is the new page containg the text or another link)
                # TODO: Write code to examine the pdf's, which are the publications
                document_soup = BeautifulSoup(document_response.text, 'html.parser')
                assert document_soup
                field_name_body = document_soup.find('div', class_='field--name-body')
                assert field_name_body
                document_text = field_name_body.get_text()
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
            pagination = self.update_pagination(pagination, page_soup=results_soup)
        return added_docs
