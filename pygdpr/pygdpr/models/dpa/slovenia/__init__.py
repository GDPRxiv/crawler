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
from pygdpr.models.pagination import Pagination
from pygdpr.policies.gdpr_policy import GDPRPolicy
import textract
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pygdpr.policies.webdriver_exec_policy import WebdriverExecPolicy

class Slovenia(DPA):
    def __init__(self, path):
        country_code='SL'
        super().__init__(country_code, path)

    def update_pagination(self, pagination=None, page_soup=None, driver=None):
        source = {
            "host": "https://www.ip-rs.si",
            "start_path": "/novice/arhiv"
        }
        host = source['host']
        start_path = source['start_path']
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        exec_path = WebdriverExecPolicy().get_system_path()
        driver = webdriver.Chrome(options=options, executable_path=exec_path)
        if pagination is None:
            pagination = Pagination()
            page_url = host + start_path
            driver.get(page_url)
            pagination.add_item(driver)
        else:
            paginator = page_soup.find('ul', class_='f3-widget-paginator')
            if paginator is not None:
                for li in paginator.find_all('li'):
                    page_link = li.find('a')
                    if page_link is None:
                        continue
                    page_href = page_link.get('href')
                    driver.get(page_href)
                    pagination.add_item(driver)
        return pagination

    def get_source(self, page_url=None, driver=None):
        assert (driver is not None)
        try:
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.ID, "scheme5"))
            )
        except:
            pass
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
            results_soup = BeautifulSoup(page_source, 'html.parser')
            assert results_soup
            news_small = results_soup.find('ul', class_='news-small')
            assert news_small
            # s1. Results
            for li in news_small.find_all('li'):
                result_link = li.find('a')
                assert result_link
                time = result_link.find('time')
                assert time
                date_str = time.get('datetime')
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
                driver.get(document_url)
                try:
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "article"))
                    )
                except:
                    if to_print:
                        print('Something went wrong with webdriver, skipping.')
                    continue
                document_soup = BeautifulSoup(driver.page_source, 'html.parser')
                assert document_soup
                document_text = ""
                for body_text in document_soup.find_all('p', class_='bodytext'):
                    document_text += body_text.get_text()
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
        driver.quit()
        return added_docs
