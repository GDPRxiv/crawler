import os
import time
import shutil
import math
import requests
import json
import datetime
import hashlib
import textract
from pygdpr.models.dpa import DPA
from bs4 import BeautifulSoup
import dateparser
from pygdpr.services.filename_from_path_service import filename_from_path_service
from pygdpr.services.pdf_to_text_service import PDFToTextService
from pygdpr.specifications import pdf_file_extension_specification
from pygdpr.specifications.should_retain_document_specification import ShouldRetainDocumentSpecification
from pygdpr.models.common.pagination import Pagination
from pygdpr.policies.gdpr_policy import GDPRPolicy
import dateparser

class Belgium(DPA):
    def __init__(self, path=os.curdir):
        country_code='BE'
        super().__init__(country_code, path)

    # Modified method to take the host and start path as inputs
    def update_pagination(self, pagination=None, page_soup=None, host_link_input=None, start_path_input=None):
        if pagination is None or page_soup is None:
            source = {
                "host": host_link_input,
                "start_path": start_path_input
            }
            host = source['host']
            start_path = source['start_path']
            pagination = Pagination()
            pagination.add_item(host + start_path)
        else:
            pager = page_soup.find('ul', class_='pagination')
            if pager is not None:
                for li in pager.find_all('li', class_='page-item'):
                    page_link = li.find('a')
                    if page_link is None: continue
                    host = "https://www.autoriteprotectiondonnees.be"
                    page_href = page_link.get('href')
                    page_url = host + page_href
                    pagination.add_item(page_url)
        return pagination

    def get_source(self, page_url=None, driver=None):
        assert (page_url is not None)
        results_response = None
        try:
            results_response = requests.request('GET', page_url, timeout=1000)
            results_response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            pass
        return results_response

    # Gets all documents located at first Decisions link
    def get_docs_Decisions_v1(self, existing_docs=[], overwrite=False, to_print=True):
        added_docs = []
        pagination = self.update_pagination(host_link_input="https://www.autoriteprotectiondonnees.be",
            start_path_input="/citoyen/chercher?q=&search_category%5B%5D=taxonomy%3Apublications&search_type%5B%5D=decision&search_subtype%5B%5D=taxonomy%3Adispute_chamber_substance_decisions&s=recent&l=25" )

        iteration_number = 1
        # s0. Pagination
        while pagination.has_next():
            page_url = pagination.get_next()
            if to_print:
                print('Page:\t', page_url)
            page_source = self.get_source(page_url)
            if page_source is None:
                continue
            page_soup = BeautifulSoup(page_source.text, 'html.parser')
            assert page_soup
            search_result = page_soup.find('div', id='search-result')
            assert search_result
            # s1. Results
            for media in search_result.find_all('div', class_='media'):
                time.sleep(5)
                media_title = media.find('h3', class_='media-title')
                print("------------ Document " + str(iteration_number) + " ------------")
                iteration_number += 1
                print('title:', media_title)
                assert media_title
                result_link = media_title.find('a')
                # s2. Documents
                document_title = result_link.get_text()
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite == False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue
                document_href = result_link.get('href')
                assert document_href
                #if document_href.endswith('.pdf') is False:
                #    continue
                host = "https://www.autoriteprotectiondonnees.be"
                document_url = host + document_href
                print('document_url:', document_url)
                if to_print:
                    print("\tDocument:\t", document_hash)
                document_response = None
                try:
                    document_response = requests.request('GET', document_url, timeout=1000)
                    document_response.raise_for_status()
                except requests.exceptions.HTTPError as error:
                    if to_print:
                        print(error)
                    pass
                if document_response is None:
                    continue
                if document_url.endswith('.pdf') is False:
                    document_soup = BeautifulSoup(document_response.text, 'html.parser')
                    assert document_soup
                    date_text = document_soup.find('div', class_='date').get_text()
                    date_str = date_text[-4:] # date_text[:-4] + ' ' + date_text[-4:]
                    print('date_str:', date_str)
                    tmp = dateparser.parse(date_str, languages=[self.language_code])
                    # print('date:', tmp.year, tmp.month, tmp.day)
                    date = datetime.date(tmp.year, tmp.month, tmp.day)
                    if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                        continue
                    page_body = document_soup.find('div', class_='page-body')
                    assert page_body
                    document_text = page_body.get_text()
                else:
                    date_str = document_title.split(' du ')[-1]
                    print("date_str:", date_str)
                    tmp = dateparser.parse(date_str, languages=[self.language_code])
                    if tmp is None:
                        media_date = media.find('span', class_="media-date")
                        assert media_date
                        year = int(media_date.get_text())
                        if year < 2018:
                            continue
                    else:
                        date = datetime.date(tmp.year, tmp.month, tmp.day)
                        if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                            continue
                dpa_folder = self.path
                document_folder = dpa_folder + '/' + 'Decisions' + '/' + document_hash
                try:
                    os.makedirs(document_folder)
                except FileExistsError:
                    pass
                with open(document_folder + '/' + self.language_code + '.pdf', 'wb') as f:
                    f.write(document_response.content)
                if document_url.endswith('.pdf'):
                    with open(document_folder + '/' + self.language_code + '.txt', 'wb') as f:
                        document_text = textract.process(document_folder + '/' + self.language_code + '.pdf')
                        f.write(document_text)
                else:
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
            pagination = self.update_pagination(pagination=pagination, page_soup=page_soup)
        return added_docs

    # Gets all documents located at second Decisions link
    def get_docs_Decisions_v2(self, existing_docs=[], overwrite=False, to_print=True):
        added_docs = []
        pagination = self.update_pagination(host_link_input="https://www.autoriteprotectiondonnees.be",
                                            start_path_input="/citoyen/chercher?q=&search_category%5B%5D=taxonomy%3Apublications&search_type%5B%5D=decision&search_subtype%5B%5D=taxonomy%3Ageneral_secretary_international_decisions&search_subtype%5B%5D=taxonomy%3Ageneral_secretary_general_decisions&s=recent&l=25")

        iteration_number = 1
        # s0. Pagination
        while pagination.has_next():
            page_url = pagination.get_next()
            if to_print:
                print('Page:\t', page_url)
            page_source = self.get_source(page_url)
            if page_source is None:
                continue
            page_soup = BeautifulSoup(page_source.text, 'html.parser')
            assert page_soup
            search_result = page_soup.find('div', id='search-result')
            assert search_result
            # s1. Results
            for media in search_result.find_all('div', class_='media'):
                time.sleep(5)
                media_title = media.find('h3', class_='media-title')
                print("------------ Document " + str(iteration_number) + " ------------")
                iteration_number += 1
                print('title:', media_title)
                assert media_title
                result_link = media_title.find('a')
                # s2. Documents
                document_title = result_link.get_text()
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite == False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue
                document_href = result_link.get('href')
                assert document_href
                # if document_href.endswith('.pdf') is False:
                #    continue
                host = "https://www.autoriteprotectiondonnees.be"
                document_url = host + document_href
                print('document_url:', document_url)
                if to_print:
                    print("\tDocument:\t", document_hash)
                document_response = None
                try:
                    document_response = requests.request('GET', document_url, timeout=1000)
                    document_response.raise_for_status()
                except requests.exceptions.HTTPError as error:
                    if to_print:
                        print(error)
                    pass
                if document_response is None:
                    continue
                if document_url.endswith('.pdf') is False:
                    document_soup = BeautifulSoup(document_response.text, 'html.parser')
                    assert document_soup
                    date_text = document_soup.find('div', class_='date').get_text()
                    date_str = date_text[-4:]  # date_text[:-4] + ' ' + date_text[-4:]
                    print('date_str:', date_str)
                    tmp = dateparser.parse(date_str, languages=[self.language_code])
                    # print('date:', tmp.year, tmp.month, tmp.day)
                    date = datetime.date(tmp.year, tmp.month, tmp.day)
                    if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                        continue
                    page_body = document_soup.find('div', class_='page-body')
                    assert page_body
                    document_text = page_body.get_text()
                else:
                    date_str = document_title.split(' du ')[-1]
                    print("date_str:", date_str)
                    tmp = dateparser.parse(date_str, languages=[self.language_code])
                    if tmp is None:
                        media_date = media.find('span', class_="media-date")
                        assert media_date
                        year = int(media_date.get_text())
                        if year < 2018:
                            continue
                    else:
                        date = datetime.date(tmp.year, tmp.month, tmp.day)
                        if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                            continue
                dpa_folder = self.path
                document_folder = dpa_folder + '/' + 'Decisions 2' + '/' + document_hash
                try:
                    os.makedirs(document_folder)
                except FileExistsError:
                    pass
                with open(document_folder + '/' + self.language_code + '.pdf', 'wb') as f:
                    f.write(document_response.content)
                if document_url.endswith('.pdf'):
                    with open(document_folder + '/' + self.language_code + '.txt', 'wb') as f:
                        document_text = textract.process(document_folder + '/' + self.language_code + '.pdf')
                        f.write(document_text)
                else:
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
            pagination = self.update_pagination(pagination=pagination, page_soup=page_soup)
        return added_docs
