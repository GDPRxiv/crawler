import os
import math
import requests
import json
import datetime
import hashlib
import dateparser
from pygdpr.models.dpa import DPA, MaxRetriesError
from bs4 import BeautifulSoup
from pygdpr.services.filename_from_path_service import filename_from_path_service
from pygdpr.services.pdf_to_text_service import PDFToTextService
from pygdpr.specifications import pdf_file_extension_specification
from pygdpr.specifications.should_retain_document_specification import ShouldRetainDocumentSpecification
from pygdpr.models.pagination import Pagination
from pygdpr.policies.gdpr_policy import GDPRPolicy
from .policies import rtf_decoding_policy
from striprtf.striprtf import rtf_to_text
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pygdpr.policies.webdriver_exec_policy import WebdriverExecPolicy

class France(DPA):
    def __init__(self, path):
        country_code='FR'
        super().__init__(country_code, path)

    def update_pagination(self, pagination=None, page_soup=None, driver=None):
        source = {
            "host": "https://www.cnil.fr",
            "start_path": "/fr/deliberations"
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
            try:
                 pager = driver.find_element_by_class_name('pager-next')
                 next_button = pager.find_elements_by_tag_name('a')[-1]
                 next_button.click()
                 pagination.add_item(driver)
            except:
                 pass
        return pagination

    def get_source(self, page_url=None, driver=None):
        assert (driver is not None)
        try:
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.CLASS_NAME, "view-content"))
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
            view_content = results_soup.find('div', class_='view-content')
            assert view_content
            # s1. Results
            for views_row in view_content.find_all('div', class_='views-row'):
                result_link = views_row.find('a')
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
                document_url = document_href
                print(document_url)
                exec_path = WebdriverExecPolicy().get_system_path()
                options = webdriver.ChromeOptions()
                options.add_argument('headless')
                doc_driver = webdriver.Chrome(options=options, executable_path=exec_path)
                doc_driver.get(document_url)
                #WebDriverWait(doc_driver, 60).until_not(
                #    EC.presence_of_element_located((By.ID, "main-iframe"))
                #)
                WebDriverWait(doc_driver, 10).until(
                    EC.url_contains("legifrance")
                )
                document_response = doc_driver.page_source
                # cnil_id = document_href.split('?')[-1].split('=')[-1]
                # document_response = requests.get(f"https://www.legifrance.gouv.fr/cnil/id/{cnil_id}/")
                print(document_response)
                document_soup = BeautifulSoup(document_response, 'html.parser')
                assert document_soup
                cnil = document_soup.find('div', class_='cnil')
                assert cnil
                li = document_soup.find('li')
                assert (li is not None)
                li_text = li.get_text()
                print("li_text:", li_text)
                date_str = cnil.get_text().strip().split('\n')[-1].split(':')[-1].strip()
                tmp = dateparser.parse(date_str, languages=[self.language_code])
                date = datetime.date(tmp.year, tmp.month, tmp.day)
                if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                    continue
                if to_print:
                    print("\tDocument:\t", document_hash)
                page_content = document_soup.find('div', class_='page-content')
                document_text = page_content.get_text()
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
                        'releaseYear': int(date.strftime('%Y')),
                        'releaseMonth': int(date.strftime('%m')),
                        'source_url': document_url
                    }
                    json.dump(metadata, f, indent=4, sort_keys=True)
                added_docs.append(document_hash)
            # s0. Pagination
            pagination = self.update_pagination(pagination=pagination, driver=driver)
        return added_docs
