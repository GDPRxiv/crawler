import os
import math
import time
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
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pygdpr.policies.webdriver_exec_policy import WebdriverExecPolicy

class Denmark(DPA):
    def __init__(self, path=os.curdir):
        country_code='DK'
        super().__init__(country_code, path)

    def update_pagination(self, pagination=None, results_soup=None, driver=None):
        source = {
            'host': 'https://www.datatilsynet.dk',
            'start_path': '/afgoerelser/afgoerelser'
        }
        host = source['host']
        start_path = source['start_path']
        if pagination is None:
            page_url = host + start_path
            exec_path = WebdriverExecPolicy().get_system_path()
            options = webdriver.ChromeOptions()
            options.add_argument('headless')
            driver = webdriver.Chrome(options=options, executable_path=exec_path)
            driver.get(page_url)
            pagination = Pagination()
            pagination.add_item(driver)
        else:
            pagination = driver.find_element_by_class_name('pagination')
            if pagination is not None:
                items = pagination.find_elements_by_tag_name('li')
                last_item = items[-1]
                last_item.click()
                time.sleep(5)
                pagination = Pagination()
                pagination.add_item(driver)
        return pagination

    def get_source(self, page_url=None, driver=None):
        assert (driver is not None)
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located(
                (By.CLASS_NAME, 'archive-search-result')
            ))
            WebDriverWait(driver, 10).until(EC.presence_of_element_located(
                (By.CLASS_NAME, 'items')
            ))
        except:
            return None
        page_source = driver.page_source
        return page_source

    def get_docs(self, existing_docs=[], overwrite=False, to_print=True):
        added_docs = []
        # s0. Pagination
        pagination = self.update_pagination()
        while pagination.has_next():
            driver = pagination.get_next()
            if to_print:
                print('Page:\t', driver)
            page_source = self.get_source(driver=driver)
            if page_source is None:
                continue
            results_soup = BeautifulSoup(page_source, 'html.parser')
            assert results_soup
            archive_search_result = results_soup.find('div', class_='archive-search-result')
            assert archive_search_result
            ul = results_soup.find('ul', class_='items')
            assert ul
            # s1. Results
            for li in ul.find_all('li', class_='item'):
                content = li.find('div', class_='content')
                assert content
                span_date = content.find('span', class_='date')
                assert span_date
                date_str = span_date.get_text().strip().split(' ')[-1]
                tmp = datetime.datetime.strptime(date_str, '%d-%m-%Y')
                date = datetime.date(tmp.year, tmp.month, tmp.day)
                if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                    continue
                h2 = content.find('h2')
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
                host = 'https://www.datatilsynet.dk'
                document_url = host + document_href
                if to_print:
                    print("\tDocument:\t", document_hash)
                document_response = None
                exec_path = WebdriverExecPolicy().get_system_path()
                options = webdriver.ChromeOptions()
                options.add_argument('headless')
                driver_doc = webdriver.Chrome(options=options, executable_path=exec_path)
                driver_doc.get(document_url)
                print('document_url:', document_url)
                if driver_doc.page_source is None:
                    continue
                document_soup = BeautifulSoup(driver_doc.page_source, 'html.parser')
                assert document_soup
                WebDriverWait(driver_doc, 10).until(EC.presence_of_element_located(
                    (By.CLASS_NAME, 'news-page')
                ))
                print("made it thus far to news_page")
                news_page = document_soup.find('div', class_='news-page')
                assert news_page
                document_text = news_page.get_text()
                document_text = document_text.lstrip()
                dpa_folder = self.path
                document_folder = dpa_folder + '/' + document_hash
                try:
                    os.makedirs(document_folder)
                except FileExistsError:
                    pass
                print("writing to the directory:", document_folder)
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
            pagination = self.update_pagination(pagination=pagination, driver=driver)
        return added_docs
