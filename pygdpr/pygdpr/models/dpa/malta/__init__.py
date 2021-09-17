import os
import math
import requests
import json
import datetime
import hashlib
import dateparser
import re
import csv
import time
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

class Malta(DPA):
    def __init__(self, path=os.curdir):
        country_code='mt'
        super().__init__(country_code, path)

    def update_pagination(self, pagination=None, page_soup=None, driver=None):
        source = {
            "host": "https://idpc.org.mt",
            "start_path": "/news"
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
            news_pagination = driver.find_element_by_id('news-pagination')
            page_btn = news_pagination.find_element_by_class_name('page-btn')
            old_news_entries = driver.find_elements_by_class_name('news-entry')
            page_btn.click()
            time.sleep(20)
            news_entries = driver.find_elements_by_class_name('news-entry')
            if len(news_entries) > len(old_news_entries):
                pagination = Pagination()
                pagination.add_item(driver)
        return pagination

    def get_source(self, page_url=None, driver=None):
        assert (driver is not None)
        try:
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CLASS_NAME, "news-list-container"))
            )
        except:
            return None
        page_source = driver.page_source
        return page_source

    def get_docs(self, existing_docs=[], overwrite=False, to_print=True):
        added_docs = []
        pagination = self.update_pagination()
        # s0. Pagination
        while pagination.has_next():
            driver = pagination.get_next()
            if to_print:
                print('Page:\t', driver)
            page_source = self.get_source(driver=driver)
            if page_source is None:
                continue
            results_soup = BeautifulSoup(page_source, 'html.parser')
            assert results_soup
            news_list = results_soup.find('div', class_="news-list-container")
            assert news_list
            # s1. Results
            for news_entry in news_list.find_all('div', class_='news-entry'):
                news_entry_footer = news_entry.find('div', class_='news-entry-footer')
                if news_entry_footer is None:
                    continue
                h4_date = news_entry_footer.find('h4', class_='date')
                if h4_date is None:
                    continue
                date_str = h4_date.get_text()
                tmp = dateparser.parse(date_str, languages=[self.language_code])
                date = datetime.date(tmp.year, tmp.month, tmp.day)
                if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                    continue
                result_link = news_entry.find('a')
                assert result_link
                # s2. Documents
                h4 = result_link.find('h4')
                assert h4
                document_title = h4.get_text()
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
                article = document_soup.find('article')
                assert article
                document_text = article.get_text()
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
            pagination = self.update_pagination(pagination=pagination, driver=driver)
        return added_docs
