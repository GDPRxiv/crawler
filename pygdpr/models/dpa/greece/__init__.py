import os
import math
import socket
import sys

import requests
import json
import datetime
import hashlib
import dateparser
import requests.exceptions
import urllib3.exceptions

from pygdpr.models.dpa import DPA
from bs4 import BeautifulSoup
from pygdpr.services.filename_from_path_service import filename_from_path_service
from pygdpr.services.pdf_to_text_service import PDFToTextService
from pygdpr.specifications import pdf_file_extension_specification
from pygdpr.specifications.should_retain_document_specification import ShouldRetainDocumentSpecification
from pygdpr.models.common.pagination import Pagination
from pygdpr.policies.gdpr_policy import GDPRPolicy
import textract

class Greece(DPA):
    def __init__(self, path=os.curdir):
        country_code='GR'
        super().__init__(country_code, path)

    def update_pagination(self, pagination=None, page_soup=None, driver=None, start_path=None):
        source = {
            "host": "https://www.dpa.gr"
            # "start_path": "/portal/page?_pageid=33,43547&_dad=portal&_schema=PORTAL"
            #"start_path": "/el/enimerwtiko/prakseisArxis?field_year_from=2018&field_year_to=&field_category=239&field_thematic=All&field_protocol_number=&field_keywords=&page=0"
        }
        host = source['host']
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
            pass
        return results_response

    def get_docs(self, existing_docs=[], overwrite=False, to_print=True):
        added_docs = []
        # call all the get_docs_X() functions
        added_docs += self.get_docs_Decisions(existing_docs=[], overwrite=False, to_print=True)
        added_docs += self.get_docs_Recommendations(existing_docs=[], overwrite=False, to_print=True)
        added_docs += self.get_docs_Opinions(existing_docs=[], overwrite=False, to_print=True)
        added_docs += self.get_docs_AnnualReports(existing_docs=[], overwrite=False, to_print=True)
        added_docs += self.get_docs_Guidelines(existing_docs=[], overwrite=False, to_print=True)

        return added_docs

    # TODO: Run this overnight
    def get_docs_Decisions(self, existing_docs=[], overwrite=False, to_print=True):
        print('------------ GETTING DECISIONS ------------')
        added_docs = []
        pagination = self.update_pagination(start_path='/el/enimerwtiko/prakseisArxis?field_year_from=2018&field_year_to=&field_category=239&field_thematic=All&field_protocol_number=&field_keywords=&page=0')

        # This list stores the pages we have visited
        visited_pages = []
        while pagination.has_next():
            page_url = pagination.get_next()
            if to_print:
                print('Page:\t', page_url)
            page_source = self.get_source(page_url=page_url)
            if page_source is None:
                continue
            results_soup = BeautifulSoup(page_source.text, 'html.parser')
            assert results_soup

            tbody = results_soup.find('tbody')
            assert tbody

            iterator = 1
            for tr in tbody.find_all('tr'):
                assert tr

                print("\n------------ Document " + str(iterator) + " ------------")
                iterator += 1

                date_tag = tr.find('time', datetime='00Z')
                assert date_tag
                date_str = date_tag.get_text()
                print('\tDocument Date: ' + date_str)
                document_year = date_str[-4:]

                if int(document_year) < 2018:
                    print("\tSkipping outdated document")
                    continue

                a_tag = tr.find('a')
                document_title = a_tag.get_text()
                assert document_title
                print('\tDocument Title: ' + document_title)

                # Create the document has using the document title
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite is False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue

                document_href = a_tag.get('href')
                assert document_href
                if document_href.startswith('http'):
                    document_url = document_href
                else:
                    document_url = 'https://www.dpa.gr' + document_href

                if to_print:
                    print("\tDocument:\t", document_hash)

                # Get document response object
                document_response = None
                try:
                    document_response = requests.request('GET', document_url, timeout=3)
                    document_response.raise_for_status()
                except requests.exceptions.HTTPError as error:
                    if to_print:
                        print(error)
                    pass
                if document_response is None:
                    continue

                document_soup = BeautifulSoup(document_response.text, 'html.parser')
                assert document_soup

                span_tag = document_soup.find('span', class_='file-link')
                assert span_tag

                span_a_tag = span_tag.find('a')
                assert span_a_tag
                pdf_href = span_a_tag.get('href')
                assert pdf_href

                if pdf_href.startswith('http'):
                    pdf_url = pdf_href
                else:
                    pdf_url = 'https://www.dpa.gr' + pdf_href

                pdf_response = None
                try:
                    pdf_response = requests.request('GET', pdf_url, timeout=3)
                    pdf_response.raise_for_status()
                except requests.exceptions.HTTPError as error:
                    if to_print:
                        print(error)
                    pass
                if pdf_response is None:
                    continue

                dpa_folder = self.path
                # document_folder = dpa_folder + '/' + 'Decisions' + '/' + document_hash
                document_folder = dpa_folder + '/greece' + '/' + 'Decisions' + '/' + document_hash
                try:
                    os.makedirs(document_folder)
                except FileExistsError:
                    pass

                # TODO: Ask about self.language_code -> its 'en' right now...
                with open(document_folder + '/' + self.language_code + '.pdf', 'wb') as f:
                    f.write(pdf_response.content)

                with open(document_folder + '/' + self.language_code + '.txt', 'wb') as f:
                    link_text = textract.process(document_folder + '/' + self.language_code + '.pdf')
                    f.write(link_text)

                with open(document_folder + '/' + 'metadata.json', 'w') as f:
                    metadata = {
                        'title': {
                            self.language_code: document_title
                        },
                        'md5': document_hash,
                        'releaseDate': date_str,
                        'url': document_url
                    }
                    json.dump(metadata, f, indent=4, sort_keys=True)
                added_docs.append(document_hash)

            # Add the next page to the pagination object
            ul = results_soup.find('ul', class_='pagination js-pager__items')
            assert ul
            # The last two li tags contain links for 'next' and 'end' buttons
            li_list = ul.find_all('li')
            assert li_list
            # The second to last element should contain the 'next page' link
            a = li_list[-2].find('a')
            assert a
            a_href = a.get('href')
            assert a_href
            page_link = 'https://www.dpa.gr/el/enimerwtiko/prakseisArxis' + a_href
            # If the index where next page usually is leads to a page that scraper has already visited -> don't add
            # to pagination object
            if page_link in visited_pages:
                print("There seems to be no more pages to look at")
                continue
            else:
                print("\nNext Page: " + page_link)
                visited_pages.append(page_link)
                pagination.add_item(page_link)
        return added_docs

    def get_docs_Recommendations(self, existing_docs=[], overwrite=False, to_print=True):
        print('------------ GETTING RECOMMENDATIONS ------------')
        added_docs = []
        pagination = self.update_pagination(start_path='/el/enimerwtiko/prakseisArxis?field_year_from=&field_year_to=&field_category=246&field_thematic=All&field_protocol_number=&field_keywords=')

        # This list stores the pages we have visited
        visited_pages = []
        while pagination.has_next():
            page_url = pagination.get_next()
            if to_print:
                print('Page:\t', page_url)
            page_source = self.get_source(page_url=page_url)
            if page_source is None:
                continue
            results_soup = BeautifulSoup(page_source.text, 'html.parser')
            assert results_soup

            tbody = results_soup.find('tbody')
            assert tbody

            iterator = 1
            for tr in tbody.find_all('tr'):
                assert tr

                print("\n------------ Document " + str(iterator) + " ------------")
                iterator += 1

                date_tag = tr.find('time', datetime='00Z')
                assert date_tag
                date_str = date_tag.get_text()
                print('\tDocument Date: ' + date_str)
                document_year = date_str[-4:]

                if int(document_year) < 2018:
                    print("\tSkipping outdated document")
                    continue

                a_tag = tr.find('a')
                document_title = a_tag.get_text()
                assert document_title
                print('\tDocument Title: ' + document_title)

                # Create the document has using the document title
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite is False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue

                document_href = a_tag.get('href')
                assert document_href
                if document_href.startswith('http'):
                    document_url = document_href
                else:
                    document_url = 'https://www.dpa.gr' + document_href

                if to_print:
                    print("\tDocument:\t", document_hash)

                # Get document response object
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

                span_tag = document_soup.find('span', class_='file-link')
                assert span_tag

                span_a_tag = span_tag.find('a')
                assert span_a_tag
                pdf_href = span_a_tag.get('href')
                assert pdf_href

                if pdf_href.startswith('http'):
                    pdf_url = pdf_href
                else:
                    pdf_url = 'https://www.dpa.gr' + pdf_href

                pdf_response = None
                try:
                    pdf_response = requests.request('GET', pdf_url)
                    pdf_response.raise_for_status()
                except requests.exceptions.HTTPError as error:
                    if to_print:
                        print(error)
                    pass
                if pdf_response is None:
                    continue

                dpa_folder = self.path
                # document_folder = dpa_folder + '/' + 'Recommendations' + '/' + document_hash
                document_folder = dpa_folder + '/greece' + '/' + 'Recommendations' + '/' + document_hash
                try:
                    os.makedirs(document_folder)
                except FileExistsError:
                    pass

                # TODO: Ask about self.language_code -> its 'en' right now...
                with open(document_folder + '/' + self.language_code + '.pdf', 'wb') as f:
                    f.write(pdf_response.content)

                with open(document_folder + '/' + self.language_code + '.txt', 'wb') as f:
                    link_text = textract.process(document_folder + '/' + self.language_code + '.pdf')
                    f.write(link_text)

                with open(document_folder + '/' + 'metadata.json', 'w') as f:
                    metadata = {
                        'title': {
                            self.language_code: document_title
                        },
                        'md5': document_hash,
                        'releaseDate': date_str,
                        'url': document_url
                    }
                    json.dump(metadata, f, indent=4, sort_keys=True)
                added_docs.append(document_hash)

        return added_docs

    # TODO: Address slow download speeds for documents
    def get_docs_Opinions(self, existing_docs=[], overwrite=False, to_print=True):
        print('------------ GETTING OPINIONS ------------')
        added_docs = []
        pagination = self.update_pagination(start_path='/el/enimerwtiko/prakseisArxis?field_year_from=&field_year_to=&field_category=238&field_thematic=All&field_protocol_number=&field_keywords=')

        # This list stores the pages we have visited
        visited_pages = []
        while pagination.has_next():
            page_url = pagination.get_next()
            if to_print:
                print('Page:\t', page_url)
            page_source = self.get_source(page_url=page_url)
            if page_source is None:
                continue
            results_soup = BeautifulSoup(page_source.text, 'html.parser')
            assert results_soup

            tbody = results_soup.find('tbody')
            assert tbody

            iterator = 1
            for tr in tbody.find_all('tr'):
                assert tr

                print("\n------------ Document " + str(iterator) + " ------------")
                iterator += 1

                date_tag = tr.find('time', datetime='00Z')
                assert date_tag
                date_str = date_tag.get_text()
                print('\tDocument Date: ' + date_str)
                document_year = date_str[-4:]

                if int(document_year) < 2018:
                    print("\tSkipping outdated document")
                    continue

                a_tag = tr.find('a')
                document_title = a_tag.get_text()
                assert document_title
                print('\tDocument Title: ' + document_title)

                # Create the document has using the document title
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite is False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue

                document_href = a_tag.get('href')
                assert document_href
                if document_href.startswith('http'):
                    document_url = document_href
                else:
                    document_url = 'https://www.dpa.gr' + document_href

                if to_print:
                    print("\tDocument:\t", document_hash)

                # Get document response object
                document_response = None
                try:
                    document_response = requests.request('GET', document_url, timeout=(2, 2))
                    document_response.raise_for_status()
                # Added more errors to catch
                except requests.exceptions.ReadTimeout as error:
                    if to_print:
                        print(error)
                    pass
                except requests.exceptions.ConnectionError as error:
                    if to_print:
                        print(error)
                    pass
                except urllib3.exceptions.ReadTimeoutError as error:
                    if to_print:
                        print(error)
                    pass
                except socket.timeout as error:
                    if to_print:
                        print(error)
                    pass
                if document_response is None:
                    continue

                document_soup = BeautifulSoup(document_response.text, 'html.parser')
                assert document_soup

                span_tag = document_soup.find('span', class_='file-link')
                assert span_tag

                span_a_tag = span_tag.find('a')
                assert span_a_tag
                pdf_href = span_a_tag.get('href')
                assert pdf_href

                if pdf_href.startswith('http'):
                    pdf_url = pdf_href
                else:
                    pdf_url = 'https://www.dpa.gr' + pdf_href

                pdf_response = None
                try:
                    pdf_response = requests.request('GET', pdf_url, timeout=(2, 2))
                    pdf_response.raise_for_status()
                except requests.exceptions.HTTPError as error:
                    if to_print:
                        print(error)
                    pass
                except requests.exceptions.ConnectionError as error:
                    if to_print:
                        print(error)
                    pass
                except urllib3.exceptions.ReadTimeoutError as error:
                    if to_print:
                        print(error)
                    pass
                except socket.timeout as error:
                    if to_print:
                        print(error)
                    pass

                if pdf_response is None:
                    continue

                dpa_folder = self.path
                # document_folder = dpa_folder + '/' + 'Opinions' + '/' + document_hash
                document_folder = dpa_folder + '/greece' + '/' + 'Opinions' + '/' + document_hash
                try:
                    os.makedirs(document_folder)
                except FileExistsError:
                    pass

                # TODO: Ask about self.language_code -> its 'en' right now...
                with open(document_folder + '/' + self.language_code + '.pdf', 'wb') as f:
                    f.write(pdf_response.content)
                # If a pdf fails to convert to text (because pdf is broken), print error
                try:
                    with open(document_folder + '/' + self.language_code + '.txt', 'wb') as f:
                        link_text = textract.process(document_folder + '/' + self.language_code + '.pdf')
                        f.write(link_text)
                except:
                    print("Failed to convert pdf to text document.")
                    pass

                with open(document_folder + '/' + 'metadata.json', 'w') as f:
                    metadata = {
                        'title': {
                            self.language_code: document_title
                        },
                        'md5': document_hash,
                        'releaseDate': date_str,
                        'url': document_url
                    }
                    json.dump(metadata, f, indent=4, sort_keys=True)
                added_docs.append(document_hash)

            # Add the next page to the pagination object
            ul = results_soup.find('ul', class_='pagination js-pager__items')
            assert ul
            # The last two li tags contain links for 'next' and 'end' buttons
            li_list = ul.find_all('li')
            assert li_list
            # The second to last element should contain the 'next page' link
            a = li_list[-2].find('a')
            assert a
            a_href = a.get('href')
            assert a_href
            page_link = 'https://www.dpa.gr/el/enimerwtiko/prakseisArxis' + a_href
            # If the index where next page usually is leads to a page that scraper has already visited -> don't add
            # to pagination object
            if page_link in visited_pages:
                print("There seems to be no more pages to look at")
                continue
            else:
                print("\nNext Page: " + page_link)
                visited_pages.append(page_link)
                pagination.add_item(page_link)
        return added_docs

    def get_docs_Guidelines(self, existing_docs=[], overwrite=False, to_print=True):
        print('------------ GETTING GUIDELINES ------------')
        added_docs = []
        pagination = self.update_pagination(start_path='/el/enimerwtiko/prakseisArxis?field_year_from=&field_year_to=&field_category=245&field_thematic=All&field_protocol_number=&field_keywords=')

        # This list stores the pages we have visited
        visited_pages = []
        while pagination.has_next():
            page_url = pagination.get_next()
            if to_print:
                print('Page:\t', page_url)
            page_source = self.get_source(page_url=page_url)
            if page_source is None:
                continue
            results_soup = BeautifulSoup(page_source.text, 'html.parser')
            assert results_soup

            tbody = results_soup.find('tbody')
            assert tbody

            iterator = 1
            for tr in tbody.find_all('tr'):
                assert tr

                print("\n------------ Document " + str(iterator) + " ------------")
                iterator += 1

                date_tag = tr.find('time', datetime='00Z')
                assert date_tag
                date_str = date_tag.get_text()
                print('\tDocument Date: ' + date_str)
                document_year = date_str[-4:]

                if int(document_year) < 2018:
                    print("\tSkipping outdated document")
                    continue

                a_tag = tr.find('a')
                document_title = a_tag.get_text()
                assert document_title
                print('\tDocument Title: ' + document_title)

                # Create the document has using the document title
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite is False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue

                document_href = a_tag.get('href')
                assert document_href
                if document_href.startswith('http'):
                    document_url = document_href
                else:
                    document_url = 'https://www.dpa.gr' + document_href

                if to_print:
                    print("\tDocument:\t", document_hash)

                # Get document response object
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

                span_tag = document_soup.find('span', class_='file-link')
                assert span_tag

                span_a_tag = span_tag.find('a')
                assert span_a_tag
                pdf_href = span_a_tag.get('href')
                assert pdf_href

                if pdf_href.startswith('http'):
                    pdf_url = pdf_href
                else:
                    pdf_url = 'https://www.dpa.gr' + pdf_href

                pdf_response = None
                try:
                    pdf_response = requests.request('GET', pdf_url)
                    pdf_response.raise_for_status()
                except requests.exceptions.HTTPError as error:
                    if to_print:
                        print(error)
                    pass
                if pdf_response is None:
                    continue

                dpa_folder = self.path
                #document_folder = dpa_folder + '/' + 'Guidelines' + '/' + document_hash
                document_folder = dpa_folder + '/greece' + '/' + 'Guidelines' + '/' + document_hash
                try:
                    os.makedirs(document_folder)
                except FileExistsError:
                    pass

                # TODO: Ask about self.language_code -> its 'en' right now...
                with open(document_folder + '/' + self.language_code + '.pdf', 'wb') as f:
                    f.write(pdf_response.content)

                with open(document_folder + '/' + self.language_code + '.txt', 'wb') as f:
                    link_text = textract.process(document_folder + '/' + self.language_code + '.pdf')
                    f.write(link_text)

                with open(document_folder + '/' + 'metadata.json', 'w') as f:
                    metadata = {
                        'title': {
                            self.language_code: document_title
                        },
                        'md5': document_hash,
                        'releaseDate': date_str,
                        'url': document_url
                    }
                    json.dump(metadata, f, indent=4, sort_keys=True)
                added_docs.append(document_hash)

        return added_docs

    # Only visits first page because further pages contain only outdated documents
    def get_docs_AnnualReports(self, existing_docs=[], overwrite=False, to_print=True):
        print('------------ GETTING ANNUAL REPORTS ------------')
        added_docs = []
        pagination = self.update_pagination(start_path='/enimerwtiko/etisies-ektheseis')

        # This list stores the pages we have visited
        visited_pages = []
        while pagination.has_next():
            page_url = pagination.get_next()
            if to_print:
                print('Page:\t', page_url)
            page_source = self.get_source(page_url=page_url)
            if page_source is None:
                continue
            results_soup = BeautifulSoup(page_source.text, 'html.parser')
            assert results_soup

            region = results_soup.find('div', class_='region region-content')
            assert region

            view_content = region.find('div', class_='view-content')
            assert view_content

            clearfix = view_content.find('div', class_='views-col')
            assert clearfix

            iterator = 1
            # Only look at outer 'div' tags
            for div in clearfix.find_all('div', class_='events-teaser'):
                assert div

                print("\n------------ Document " + str(iterator) + " ------------")
                iterator += 1

                a_tag = div.find('a')
                assert a_tag

                document_year = a_tag.get_text()[-4:]

                print('\tDocument Date: ' + document_year)

                if int(document_year) < 2018:
                    print("\tSkipping outdated document")
                    continue

                document_title = a_tag.get_text()
                assert document_title
                print('\tDocument Title: ' + document_title)

                # Create the document has using the document title
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite is False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue

                document_href = a_tag.get('href')
                assert document_href
                if document_href.startswith('http'):
                    document_url = document_href
                else:
                    document_url = 'https://www.dpa.gr' + document_href

                if to_print:
                    print("\tDocument:\t", document_hash)

                # Get document response object
                document_response = None
                try:
                    document_response = requests.request('GET', document_url, timeout=5)
                    document_response.raise_for_status()
                except requests.exceptions.HTTPError as error:
                    if to_print:
                        print(error)
                    pass
                if document_response is None:
                    continue

                document_soup = BeautifulSoup(document_response.text, 'html.parser')
                assert document_soup

                article = document_soup.find('article', role='article')
                assert article

                content = article.find('div', class_='content')
                assert content

                pdf_a = content.find('a')
                assert pdf_a

                pdf_href = pdf_a.get('href')
                assert pdf_href

                if pdf_href.startswith('http'):
                    pdf_url = pdf_href
                else:
                    pdf_url = 'https://www.dpa.gr' + pdf_href

                print("\tPDF URL: " + pdf_url)

                pdf_response = None
                try:
                    pdf_response = requests.request('GET', pdf_url, timeout=5)
                    pdf_response.raise_for_status()
                except requests.exceptions.HTTPError as error:
                    if to_print:
                        print(error)
                    pass
                if pdf_response is None:
                    continue

                dpa_folder = self.path
                #document_folder = dpa_folder + '/' + 'Annual Reports' + '/' + document_hash
                document_folder = dpa_folder + '/greece' + '/' + 'Annual Reports' + '/' + document_hash
                try:
                    os.makedirs(document_folder)
                except FileExistsError:
                    pass

                # TODO: Ask about self.language_code -> its 'en' right now...
                with open(document_folder + '/' + self.language_code + '.pdf', 'wb') as f:
                    f.write(pdf_response.content)

                try:
                    with open(document_folder + '/' + self.language_code + '.txt', 'wb') as f:
                        link_text = textract.process(document_folder + '/' + self.language_code + '.pdf')
                        f.write(link_text)
                except:
                    print("Failed to convert pdf to text document")
                    pass

                with open(document_folder + '/' + 'metadata.json', 'w') as f:
                    metadata = {
                        'title': {
                            self.language_code: document_title
                        },
                        'md5': document_hash,
                        'releaseDate': document_year,
                        'url': document_url
                    }
                    json.dump(metadata, f, indent=4, sort_keys=True)
                added_docs.append(document_hash)

        return added_docs

