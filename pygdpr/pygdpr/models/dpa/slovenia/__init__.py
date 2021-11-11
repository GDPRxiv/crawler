import os
import math
import socket

import requests
import json
import datetime
import hashlib
import dateparser
import re
import csv
import sys
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
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pygdpr.policies.webdriver_exec_policy import WebdriverExecPolicy

class Slovenia(DPA):
    def __init__(self, path=os.curdir):
        country_code='SL'
        super().__init__(country_code, path)

    def update_pagination(self, pagination=None, page_soup=None, driver=None):
        source = {
            "host": "https://www.ip-rs.si",
            "start_path": "/mnenja-gdpr/"
        }
        host = source['host']
        start_path = source['start_path']
        if pagination is None:
            pagination = Pagination()
            pagination.add_item(host + start_path)
        elif page_soup is not None:
            nav = page_soup.find('div', class_='page pr')
            assert nav

            article = nav.find('article', class_='c9')
            assert article

            advsea_next = article.find('span', class_='advsea-next')
            assert advsea_next

            a_tag = advsea_next.find('a')
            assert a_tag

            href = a_tag.get('href')
            next_url = 'https://www.ip-rs.si/' + href
            #print("\nAdding page: " + next_url + " to pagination object")
            pagination.add_item(next_url)
        else:
            print("update_pagination() added zero links")

        return pagination

    def get_source(self, page_url=None, driver=None):
        assert page_url is not None
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
                print('\nPage:\t', page_url)
            page_source = self.get_source(page_url=page_url)
            results_soup = BeautifulSoup(page_source.text, 'html.parser')
            assert results_soup
            news_small = results_soup.find('ul', class_='news-small')
            assert news_small
            # s1. Results
            for li in news_small.find_all('li'):
                result_link = li.find('a')
                assert result_link
                time = result_link.find('time')
                assert time
                date_str = time.get_text().strip()
                tmp = datetime.datetime.strptime(date_str, '%d.%m.%Y')
                date = datetime.date(tmp.year, tmp.month, tmp.day)
                if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                    continue
                strong = result_link.find('strong')
                assert strong
                # s2. Documents
                document_title = result_link.get_text()
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite == False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue
                document_href = result_link.get('href')
                document_url = document_href
                if to_print:
                    print("\tDocument:\t", document_hash)
                host = "https://www.ip-rs.si"
                document_url = host + '/' + document_href
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
                article_c9 = document_soup.find('article', class_='c9')
                assert article_c9
                document_text = article_c9.get_text()
                assert len(document_text) > 0
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

    def get_docs_Opinions(self, existing_docs=[], overwrite=False, to_print=True):
        added_docs = []
        pagination = self.update_pagination()

        iteration = 1
        while pagination.has_next():
            page_url = pagination.get_next()
            if to_print:
                print('Page:\t', page_url)
            page_source = self.get_source(page_url=page_url)

            results_soup = BeautifulSoup(page_source.text, 'html.parser')
            assert results_soup

            nav = results_soup.find('div', class_='page pr')
            assert nav

            article = nav.find('article', class_='c9')
            assert article

            advsea = article.find('div', class_='advsea-results-list')
            assert advsea

            for tr in advsea.find_all('tr')[1:]:
                assert tr

                print('\n------------ Document ' + str(iteration) + ' ------------')
                iteration += 1

                td_date = tr.find('td', align='center')
                assert td_date

                document_date = td_date.get_text()
                assert document_date

                print('\tDocument Date: ' + document_date)

                if int(document_date[-4:]) < 2018:
                    print('\tSkipping outdated document')
                    continue
                if int(document_date[-4:]) < 2017:
                    sys.ext('Remaining documents are out of date')

                td = tr.find('td', align='left')
                assert td

                a = td.find('a')
                assert a

                href = a.get('href')
                assert href

                # THE HREF'S IN THE HTML ARE MISSING THE BEGINNING '/', SO IT MUST BE ADDED HERE
                document_url = 'https://www.ip-rs.si/' + href
                assert document_url

                print("\tDocument Link: " + document_url)

                document_response = None
                try:
                    document_response = requests.request('GET', document_url)
                    document_response.raise_for_status()

                except requests.exceptions.HTTPError as error:
                    if to_print:
                        print(error)
                    pass
                except requests.exceptions.ConnectionError as error:
                    if to_print:
                        print(error)
                    pass
                except urllib3.exceptions.MaxRetryError as error:
                    if to_print:
                        print(error)
                    pass
                except urllib3.exceptions.NewConnectionError as error:
                    if to_print:
                        print(error)
                    pass
                except socket.gaierror as error:
                    if to_print:
                        print(error)
                    pass

                if document_response is None:
                    continue

                document_soup = BeautifulSoup(document_response.text, 'html.parser')
                assert document_soup

                article = document_soup.find('article', class_='c9')
                assert article

                h1 = article.find('header').find('h1')
                assert h1

                document_title = h1.get_text()
                print('\tDocument Title: ' + document_title)

                # Get the document text
                article_text = article.get_text()

                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite is False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue

                dpa_folder = self.path
                document_folder = dpa_folder + '/' + 'Decisions' + '/' + document_hash
                try:
                    os.makedirs(document_folder)
                except FileExistsError:
                    pass
                with open(document_folder + '/' + self.language_code + '.txt', 'w') as f:
                    f.write(article_text)
                with open(document_folder + '/' + 'metadata.json', 'w') as f:
                    metadata = {
                        'title': {
                            self.language_code: document_title
                        },
                        'md5': document_hash,
                        'releaseDate': document_date,
                        'url': document_url
                    }
                    json.dump(metadata, f, indent=4, sort_keys=True)
                added_docs.append(document_hash)

            pagination = self.update_pagination(pagination=pagination, page_soup=results_soup)
        return added_docs
