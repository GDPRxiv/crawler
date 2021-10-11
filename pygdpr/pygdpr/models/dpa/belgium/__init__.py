import os
import sys
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
from zipfile import ZipFile


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
                    if page_link is None:
                        continue
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
                        # TODO: Use a fixed date (GDRP release date) rather than a moving window
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

                    # Conditional checks for document date
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

    # Gets all documents located at opinions link
    def get_docs_Opinions(self, existing_docs=[], overwrite=False, to_print=True):
        print("------------ GETTING OPINIONS ------------")
        added_docs = []
        pagination = self.update_pagination(host_link_input="https://www.autoriteprotectiondonnees.be",
                                            start_path_input="/citoyen/chercher?q=GDPR&search_category%5B%5D=taxonomy%3Apublications&search_type%5B%5D=advice&s=recent&l=50")

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
                document_folder = dpa_folder + '/' + 'Opinions' + '/' + document_hash
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

    # Gets all documents located at guides link
    def get_docs_Guides(self, existing_docs=[], overwrite=False, to_print=True):
        print("------------ GETTING GUIDES ------------")
        added_docs = []
        pagination = self.update_pagination(host_link_input="https://www.autoriteprotectiondonnees.be",
                                            start_path_input="/citoyen/chercher?q=&search_category%5B%5D=taxonomy%3Apublications&search_type%5B%5D=recommendation&s=recent&l=25")

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
                            print("---> SKIPPING DOCUMENT BECAUSE OF DATE <---")
                            print(year)
                            continue
                    else:
                        # TODO: Figure out if we still want to keep the date cutoff window relative to today's date
                        #  If not, then modify this to check if the year is less than 2018, which is the default
                        #  cutoff above.
                        date = datetime.date(tmp.year, tmp.month, tmp.day)
                        if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                            print("---> SKIPPING DOCUMENT BECAUSE OF DATE <---")
                            # Where to documents outside of time window are excluded
                            print(date)
                            continue
                dpa_folder = self.path
                document_folder = dpa_folder + '/' + 'Guides' + '/' + document_hash
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

    # Gets all documents located at annual report link
    # TODO: Put all the text files into one big text file
    def get_docs_AnnualReports(self, existing_docs=[], overwrite=False, to_print=True):
        print('------------ GETTING ANNUAL REPORTS ------------')
        added_docs = []

        page_url = "https://www.autoriteprotectiondonnees.be/citoyen/l-autorite/rapport-annuel"
        if to_print:
            print('Page:\t', page_url)
        page_source = self.get_source(page_url)
        if page_source is None:
            sys.exit("Couldn't obtain page_source from page_url")
        page_soup = BeautifulSoup(page_source.text, 'html.parser')
        assert page_soup
        page_content = page_soup.find('section', id='page-content')
        assert page_content
        page_body = page_content.find('div', class_='page-body')
        assert page_body

        iteration_number = 1
        for expanded in page_body.find_all('div', class_='collapse'):
            time.sleep(5)
            assert expanded
            result_link = expanded.find_all('a')
            assert result_link

            for link in result_link:
                document_href = link.get('href')
                assert document_href

                # If the document_href is not a pdf or zip file, its not relevant to our objective
                if not (document_href.endswith('.pdf') or document_href.endswith('.zip')):
                    continue

                # Get the year of the document by slicing document_href
                href_get_year = document_href[slice(-8, -4)]
                href_year_int = int(href_get_year)

                # If the document is older than 2018, skip it
                if href_year_int < 2018:
                    continue

                # Get document title by slicing it out of the href
                # TODO: Use more robust approach
                document_title = document_href[slice(-23, -4)]

                print('\n------------ Document ' + str(iteration_number) + '-------------')
                print('Document Title: ' + document_title)

                # If we don't want to overwrite documents and we already have this document_has in existing_docs,
                # skip the document
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite == False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue

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

                dpa_folder = self.path
                document_folder = dpa_folder + '/' + 'AnnualReports' + '/' + document_hash
                try:
                    os.makedirs(document_folder)
                except FileExistsError:
                    pass

                # If the link downloads a .zip file -> extract it, then iterate through the html files within it
                # and convert them the .txt files. Store these .txt files in document_folder
                # TODO: check if we want to keep the .zip file and extracted version after we have the .txt files
                # TODO: check how to handle metadata (what should we create metadata with?)
                if document_url.endswith('.zip'):
                    with open(document_folder + '/' + self.language_code + '.zip', 'wb') as f:
                        f.write(document_response.content)
                    # Extract zip file
                    file_name = document_folder + '/' + self.language_code + '.zip'
                    with ZipFile(file_name, 'r') as zip:
                        print('\n--- ZIP FILE CONTENT ---')
                        os.chdir(document_folder)
                        zip.printdir()
                        zip.extractall()

                        print('\n--- CONVERTING .HTML TO .TXT ---')

                        # Iterate through the extracted zip folder -> convert the html files to text files
                        html_iteration = 1
                        for file in os.listdir(document_folder):
                            filename = os.fsdecode(file)
                            if 'Rapport annuel' in filename:
                                for html_file in os.listdir(filename):
                                    os.chdir(filename)
                                    print(html_file)
                                    with open(html_file, 'r') as f:
                                        contents = f.read()
                                        html_soup = BeautifulSoup(contents, 'html.parser')
                                        assert html_soup
                                        html_body = html_soup.find('body')
                                        assert html_body

                                    # Store the text files in the document folder for the link
                                    os.chdir(document_folder)
                                    with open(document_folder + '/' + self.language_code + str(html_iteration) + '.txt','wb') as f:
                                        f.write(str.encode(html_body.get_text()))
                                        html_iteration += 1

                # document_url ends with '.pdf'
                else:
                    with open(document_folder + '/' + self.language_code + '.pdf', 'wb') as f:
                        f.write(document_response.content)

                    with open(document_folder + '/' + self.language_code + '.txt', 'wb') as f:
                        document_text = textract.process(document_folder + '/' + self.language_code + '.pdf')
                        f.write(document_text)

                with open(document_folder + '/' + 'metadata.json', 'w') as f:
                    metadata = {
                        'title': {
                            self.language_code: document_title
                        },
                        'md5': document_hash,
                        # TODO: Ask about document title and date (should it be more specific?)
                        'releaseDate': href_year_int,  #.strftime('%d/%m/%Y'),
                        'url': document_url
                    }
                    json.dump(metadata, f, indent=4, sort_keys=True)
                added_docs.append(document_hash)
                iteration_number += 1

        return added_docs
