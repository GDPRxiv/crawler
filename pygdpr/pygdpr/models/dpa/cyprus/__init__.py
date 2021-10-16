import os
import shutil
import math
import requests
import json
import hashlib
import datetime
from pygdpr.models.dpa import DPA
from bs4 import BeautifulSoup
from pygdpr.services.filename_from_path_service import filename_from_path_service
from pygdpr.services.pdf_to_text_service import PDFToTextService
from pygdpr.specifications import pdf_file_extension_specification
from pygdpr.models.common.pagination import Pagination
from pygdpr.specifications.should_retain_document_specification import ShouldRetainDocumentSpecification
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pygdpr.policies.webdriver_exec_policy import WebdriverExecPolicy

class Cyprus(DPA):
    def __init__(self, path=os.curdir):
        country_code='CY'
        super().__init__(country_code, path)

    def update_pagination(self, pagination=None, page_soup=None, start_path="Decisions"):
        if pagination is None:
            source = {
                "host": "http://www.dataprotection.gov.cy",
                "start_path_Decisions": "/DATAPROTECTION/DATAPROTECTION.NSF/dp06/dp06?opendocument",
                "start_path_AnnualReport": "/dataprotection/dataprotection.nsf/reports_gr/reports_gr?opendocument"
            }
            host = source['host']
            if start_path != "Decisions":
                start_path = source['start_path_AnnualReport']
            else:
                start_path = source['start_path_Decisions']
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
        # call all the get_docs_X() functions
        added_docs += self.get_docs_Decisions(existing_docs=[], overwrite=False, to_print=True)
        added_docs += self.get_docs_AnnualReport(existing_docs=[], overwrite=False, to_print=True)
        return added_docs

    def get_docs_Decisions(self, existing_docs=[], overwrite=False, to_print=True):
        existed_docs = []
        # s0. Pagination
        pagination = self.update_pagination()
        while pagination.has_next():
            page_url = pagination.get_next()
            if to_print:
                print('Page:\t', page_url)
            page_source = self.get_source(page_url=page_url)
            if page_source is None:
                continue
            results_soup = BeautifulSoup(page_source.text, 'html.parser')
            assert results_soup
            content_block = results_soup.find('div', class_='content-block')
            assert content_block
            # s1. Results
            for li in content_block.find_all('li', class_='photos'):
                span_date = li.find('span', class_='date')
                assert span_date
                date_str = span_date.get_text()
                date_str = date_str.strip()
                tmp = datetime.datetime.strptime(date_str, '%d/%m/%Y')
                date = datetime.date(tmp.year, tmp.month, tmp.day)
                if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                    continue
                result_link = li.find('a')
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
                host = "http://www.dataprotection.gov.cy"
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
                document_soup = BeautifulSoup(document_response.content, 'html.parser')
                assert document_soup
                document_content_block = document_soup.find('div', class_='content-block')
                assert document_content_block
                document_text = document_content_block.get_text()
                document_text = document_text.lstrip()
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





    def get_docs_AnnualReport(self, existing_docs=[], overwrite=False, to_print=True):
        existed_docs = []
        # s0. Pagination
        pagination = self.update_pagination(start_path="AnnualReport")
        while pagination.has_next():
            page_url = pagination.get_next()
            if to_print:
                print('Page:\t', page_url)
            page_source = self.get_source(page_url=page_url)
            if page_source is None:
                continue
            results_soup = BeautifulSoup(page_source.text, 'html.parser')
            assert results_soup
            content_block = results_soup.find('div', class_='content-block')
            assert content_block
            # s1. Results
            for li in content_block.find_all('tr', {'valign': 'top'}):
                result_link = li.find('a')
                assert result_link
                # s2. Documents
                document_title = result_link.get_text()
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite == False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue
                document_href = result_link.get('href')
                print('document_href: ', document_href)
                assert document_href
                host = "http://www.dataprotection.gov.cy"
                document_url = host + document_href
                print('document_url: ', document_url)
                date = document_title.split()[-1]
                print('\tdate: ', date)
                if date < '2018':
                    continue
                if to_print:
                    print("\tDocument:\t", document_hash)
                dpa_folder = self.path
                document_folder = dpa_folder + '/' + 'Annual Reports' + '/' + document_hash
                exec_path = WebdriverExecPolicy().get_system_path()
                options = webdriver.ChromeOptions()
                options.add_argument('headless')
                driver_doc = webdriver.Chrome(options=options, executable_path=exec_path)
                driver_doc.get(document_url)
                article_url = driver_doc.find_element_by_xpath('/html/body/form/section[3]/div/div/div/a').get_attribute("href")
                article_response = None
                try:
                    article_response = requests.request('GET', article_url)
                    article_response.raise_for_status()
                except requests.exceptions.HTTPError as error:
                    if to_print:
                        print(error)
                    pass
                if article_response is None:
                    continue
                document_content = article_response.content
                try:
                    os.makedirs(document_folder)
                except FileExistsError:
                    pass
                with open(document_folder + '/' + self.language_code + '.pdf', 'wb') as f:
                    f.write(document_content)
                with open(document_folder + '/' + self.language_code + '.txt', 'w') as f:
                    document_text = PDFToTextService().text_from_pdf_path(
                        document_folder + '/' + self.language_code + '.pdf')
                    f.write(document_text)
                with open(document_folder + '/' + 'metadata.json', 'w') as f:
                    metadata = {
                        'title': {
                            self.language_code: document_title
                        },
                        'md5': document_hash,
                        'releaseDate': date,
                        'url': document_url
                    }
                    json.dump(metadata, f, indent=4, sort_keys=True, ensure_ascii=False)
                existed_docs.append(document_hash)
        return existed_docs