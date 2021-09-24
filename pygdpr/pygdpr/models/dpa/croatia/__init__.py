import os
import shutil
import math
import requests
import json
import hashlib
import datetime
from pygdpr.models.dpa import DPA
import dateparser
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

class Croatia(DPA):
    def __init__(self, path=os.curdir):
        country_code='HR'
        super().__init__(country_code, path)

    def update_pagination(self, pagination=None, page_soup=None, driver=None):
        source = {
            "host": "https://azop.hr",
            "start_path": "/novosti"
        }
        host = source['host']
        start_path = source['start_path']
        if pagination is None:
            page_url = host + start_path
            pagination = Pagination()
            pagination.add_item(page_url)
        else:
            print("pagination was called.")
            pagination = Pagination()
            wp_pagenavi = page_soup.find('div', class_='wp-pagenavi')
            print('wp_pagenavi:')
            print(wp_pagenavi)
            if wp_pagenavi is not None:
                for a in wp_pagenavi.find_all('a', class_='page'):
                    page_link = a.get('href')
                    print("page_link was added:", page_link)
                    pagination.add_item(page_link)
        return pagination

    def get_source(self, page_url=None, driver=None):
        assert (page_url is not None)
        exec_path = WebdriverExecPolicy().get_system_path()
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        driver = webdriver.Chrome(options=options, executable_path=exec_path)
        driver.get(page_url)
        page_source = driver.page_source
        return page_source

    def get_docs(self, existing_docs=[], overwrite=False, to_print=True):
        added_docs = []
        pagination = self.update_pagination()
        #  s0. Pagination
        while pagination.has_next():
            page_url = pagination.get_next()
            if to_print:
                print('Page:\t', page_url)
            page_source = self.get_source(page_url=page_url)
            if page_source is None:
                continue
            results_soup = BeautifulSoup(page_source, 'html.parser')
            assert results_soup
            # s1. Results
            for post in results_soup.find_all('article', class_='post'):
                post_meta = post.find('p', class_='post-meta')
                assert post_meta
                published = post_meta.find('span', class_='published')
                date_str = published.get_text()
                tmp = dateparser.parse(date_str, languages=[self.language_code])
                date = datetime.date(tmp.year, tmp.month, tmp.day)
                if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                    continue
                entry_title = post.find('h2', class_='entry-title')
                result_link = entry_title.find('a')
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
                if to_print:
                    print("\tDocument:\t", document_hash)
                exec_path = WebdriverExecPolicy().get_system_path()
                options = webdriver.ChromeOptions()
                options.add_argument('headless')
                driver_doc = webdriver.Chrome(options=options, executable_path=exec_path)
                driver_doc.get(document_url)
                document_soup = BeautifulSoup(driver_doc.page_source, 'html.parser')
                assert document_soup
                et_pb_post_content = document_soup.find('div', class_='et_pb_post_content')
                assert et_pb_post_content
                document_text = et_pb_post_content.get_text()
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
            pagination = self.update_pagination(pagination=pagination, page_soup=results_soup)
        return added_docs