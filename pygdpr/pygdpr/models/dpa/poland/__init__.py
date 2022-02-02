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
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pygdpr.policies.webdriver_exec_policy import WebdriverExecPolicy

class Poland(DPA):
    def __init__(self, path=os.curdir):
        country_code='po'
        super().__init__(country_code, path)

    def update_pagination(self, pagination=None, page_soup=None, driver=None, start_path="decisions"):
        source = {
            "host": "https://uodo.gov.pl",
            "start_path_decisions": "/pl/p/decyzje",
            "start_path_tutorials": "/pl/383"
        }
        host = source['host']
        if start_path == "decisions":
            start_path = source['start_path_decisions']
        else:
            start_path = source['start_path_tutorials']
        if pagination is None:
            pagination = Pagination()
            pagination.add_item(host + start_path)
        return pagination

    def get_source(self,  page_url=None, driver=None):
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
        added_docs += self.get_docs_Tutorials(existing_docs=[], overwrite=False, to_print=True)
        return added_docs

    def get_docs_Decisions(self, existing_docs=[], overwrite=False, to_print=True):
        existed_docs = []
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
            decisions_container = results_soup.find('div', id='decisions-container')
            assert decisions_container
            # s1. Results
            for decision in decisions_container.find_all('div', class_='decision'):
                time.sleep(5)
                date_div = decision.find('div', class_='float-sm-right')
                assert date_div
                date_str = date_div.get_text()
                tmp = dateparser.parse(date_str, languages=[self.language_code])
                date = datetime.date(tmp.year, tmp.month, tmp.day)
                if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                    continue
                result_link = decision.find('a')
                assert result_link
                # s2. Documents
                document_title = result_link.get_text()
                print('document_title: ', document_title)
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite == False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue
                document_href = result_link.get('href')
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
                article_content = document_soup.find('div', id='article-content')
                assert article_content
                document_text = article_content.get_text()
                document_text = document_text.strip()
                dpa_folder = self.path
                document_folder = dpa_folder + '/' + 'Decisions' + '/' + document_hash
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
                    json.dump(metadata, f, indent=4, sort_keys=True, ensure_ascii=False)
                existed_docs.append(document_hash)
        return existed_docs

    def get_docs_Tutorials(self, existing_docs=[], overwrite=False, to_print=True):
        existed_docs = []
        pagination = self.update_pagination(start_path="tutorials")
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
            body_content = results_soup.find('div', class_='body-content')
            assert body_content
            # s1. Results
            for artLevel0 in body_content.find_all('div', class_='artLevel0'):
                time.sleep(5)
                result_link = artLevel0.find('a')
                assert result_link
                # s2. Documents
                document_title = result_link.get_text().strip()
                print('document_title: ', document_title)
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite == False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue
                document_href = result_link.get('href')
                assert document_href
                document_url = document_href
                print("\tdocument_url: ", document_url)
                if to_print:
                    print("\tDocument:\t", document_hash)
                exec_path = WebdriverExecPolicy().get_system_path()
                options = webdriver.ChromeOptions()
                options.add_argument('headless')
                driver_doc = webdriver.Chrome(options=options, executable_path=exec_path)
                driver_doc.get(document_url)
                article_content = driver_doc.find_element_by_id("article-content")
                document_text = article_content.text
                document_text = document_text.strip()
                date_div = driver_doc.find_elements_by_class_name('article-metric-button')
                date_str = ''
                for i in date_div:
                    date_str = i.text
                assert date_str
                tmp = dateparser.parse(date_str)
                date = datetime.date(tmp.year, tmp.month, tmp.day)
                if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                    continue
                print("\tdate: ", date)
                dpa_folder = self.path
                document_folder = dpa_folder + '/' + 'Tutorials' + '/' + document_hash
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
                    json.dump(metadata, f, indent=4, sort_keys=True, ensure_ascii=False)
                existed_docs.append(document_hash)
        return existed_docs
