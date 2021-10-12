import os
import math
import requests
import json
import datetime
import hashlib

import textract

from pygdpr.models.dpa import DPA
from bs4 import BeautifulSoup
from pygdpr.services.filename_from_path_service import filename_from_path_service
from pygdpr.services.pdf_to_text_service import PDFToTextService
from pygdpr.specifications import pdf_file_extension_specification
from pygdpr.specifications.should_retain_document_specification import ShouldRetainDocumentSpecification
from pygdpr.models.common.pagination import Pagination
from pygdpr.policies.gdpr_policy import GDPRPolicy

# For getting the document date
import re

'''
# Logger to keep tracking of http get request
import logging
import http.client
http.client.HTTPConnection.debuglevel = 1

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
'''

class CzechRepublic(DPA):
    def __init__(self, path=os.curdir):
        country_code='CZ'
        super().__init__(country_code, path)

    # TODO: Update this method to take start_path as an input parameter, so that we don't have
    #  to write two update_pagination methods
    def update_pagination(self, pagination=None, page_soup=None, driver=None):
        source = {
            "host": "https://www.uoou.cz",
            # "start_path": "/vismo/zobraz_dok.asp?id_ktg=901"
            # "start_path": "/tiskove%2Dzpravy/ds-1017/p1=1017&tzv=1&pocet=25&stranka=1"
            "start_path": "/na%2Daktualni%2Dtema/ds-1018/archiv=0&p1=1099&tzv=1&pocet=25&stranka=1"
        }
        host = source['host']
        start_path = source['start_path']
        if pagination is None:
            pagination = Pagination()
            pagination.add_item(host + start_path)
        else:
            strlistovani = page_soup.find('div', class_='strlistovani')
            if strlistovani is not None:
                for a in strlistovani.find_all('a'):
                    page_href = a.get('href')
                    pagination.add_item(host + page_href)
        return pagination

    def get_source(self, page_url=None, driver=None):
        assert (page_url is not None)
        results_response = None
        try:
            # Set timeout param to low value
            # If IPv6 takes too long, the request will then switch to IPv4 quickly and use that protocol
            # This seems to be an issue for links with weaker infrastructure
            results_response = requests.request('GET', page_url, timeout=1)

            results_response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            pass
        return results_response

    def get_docs_PressReleases(self, existing_docs=[], overwrite=False, to_print=True):
        print('------------ GETTING PRESS RELEASES ------------')
        iteration = 1
        added_docs = []

        # We want to create the pagination object, then add the rest of the pages to visit to the
        # pagination object all at once, because calling update_pagination will insert all pages into the
        # pagination list each time.
        # We have to parse the first page before the while loop to do this
        pagination = self.update_pagination()
        initial_page_source = self.get_source(page_url='https://www.uoou.cz/tiskove%2Dzpravy/ds-1017/p1=1017&tzv=1&pocet=25&stranka=1')
        initial_results_soup = BeautifulSoup(initial_page_source.text, 'html.parser')
        pagination = self.update_pagination(pagination=pagination, page_soup=initial_results_soup)

        while pagination.has_next():
            page_url = pagination.get_next()
            print('\n------------ NEW PAGE ------------')
            if to_print:
                print('Page:\t', page_url)

            page_source = self.get_source(page_url=page_url)

            if page_source is None:
                print("Skipping page because page_source is None")
                continue
            results_soup = BeautifulSoup(page_source.text, 'html.parser')
            assert results_soup

            dok = results_soup.find('div', class_='obsah')
            assert dok
            ui = dok.find('ul', class_='ui')
            assert ui

            # Get the page number we are on -> if it greater than 3, skip
            # Only the first three pages contain documents made 2018 and after
            page_number = page_url[-1:]
            if int(page_number) > 3:
                print("\tSkipping page: " + page_number)
                continue

            for li in ui.find_all('li'):
                result_link = li.find('a')
                # s2. Documents
                document_title = result_link.get_text()
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite == False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue
                document_href = result_link.get('href')
                assert document_href
                if document_href.startswith('http') is not True:
                    host = "https://www.uoou.cz"
                    document_url = host + document_href
                else:
                    document_url = document_href

                # TODO: One of the document_urls leads to a pdf link -> skip it for now
                if document_url == 'https://www.uoou.cz/assets/File.ashx?id_org=200144&id_dokumenty=31695':
                    continue

                document_response = None
                try:
                    document_response = requests.request('GET', document_url, timeout=2)
                    document_response.raise_for_status()
                except requests.exceptions.HTTPError as error:
                    pass
                if document_response is None:
                    print("\tSkipping existing document: document_response is None")
                    continue

                # Created soup for the document link
                document_soup = BeautifulSoup(document_response.text, 'html.parser')
                assert document_soup

                div = li.find('div')
                if div is None:
                    print("\tSkipping existing document: div is None")
                    continue
                created_index = 0

                # Obtain document date -> implemented simpler method that just checks the years
                # TODO: Double check this and all...

                # Use this to get the date out
                div_text = div.get_text()

                m = re.search('(.+?) - ', div_text)
                if m:
                    found_date = m.group(1)
                else:
                    m = re.search('(.+?) – ', div_text)
                    if m:
                        found_date = m.group(1)

                found_date_year = found_date[-5:]

                if int(found_date_year):
                    found_date_year_int = int(found_date_year)
                    if found_date_year_int < 2018:
                        print("\tSkipping existing document: Document year is: " + found_date_year)
                        continue
                    # Document year is 2018 or greater
                    else:
                        document_year = found_date_year
                # Can't convert the year string to an int for whatever reason -> just keep the doc anyways
                else:
                    document_year = "Date not available"

                '''
                div_text = div.get_text()
                try:
                    date_str = div_text.split('-')[0].strip()
                    date_str = date_str.replace(u'\xa0', '')
                    date_str = date_str.replace(' ', '')
                    tmp = datetime.datetime.strptime(date_str, '%d.%m.%Y')
                    date = datetime.date(tmp.year, tmp.month, tmp.day)
                except:
                    date = None
                    pass

                if date is None:
                    print("\tSkipping existing document: date is None")
                    continue
                # TODO: Make sure date checking is correct (use the static date of GDPR release, not the moving window)
                if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                    print("\tSkipping existing document: ShouldRetainDocSpec is not satisfied by the date")
                    continue
                 '''

                # When we print document stuff, that means the document is not going to be thrown out
                print('\n\t------------ Document: ' + str(iteration) + ' ------------')
                print('\tDocument year: ' + found_date_year)
                iteration += 1
                if to_print:
                    print("\tDocument:\t", document_hash)
                obsah = document_soup.find('div', class_='obsah')
                assert obsah
                document_text = obsah.get_text()
                document_text = document_text.lstrip()
                dpa_folder = self.path
                document_folder = dpa_folder + '/' + 'PressReleases' + '/' + document_hash
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
                        'releaseDate': document_year,
                        'url': document_url
                    }
                    json.dump(metadata, f, indent=4, sort_keys=True)
                added_docs.append(document_hash)
                # Don't need to call update_pagination -> it already has all the pages
        return added_docs

    # Always gets text from a document page
    # If there is a pdf link on the document page, downloads the pdf (and its text) as well
    # Doesn't get dates -> html is to inconsistent -> just scrape first page of link instead (other pages
    # contains links that are too old)
    def get_docs_Opinions(self, existing_docs=[], overwrite=False, to_print=True):
        print('------------ GETTING PRESS RELEASES ------------')
        iteration = 1
        added_docs = []

        # We want to create the pagination object, then add the rest of the pages to visit to the
        # pagination object all at once, because calling update_pagination will insert all pages into the
        # pagination list each time.
        # We have to parse the first page before the while loop to do this
        pagination = self.update_pagination()
        initial_page_source = self.get_source(page_url='https://www.uoou.cz/na%2Daktualni%2Dtema/ds-1018/archiv=0&p1=1099&tzv=1&pocet=25&stranka=1')
        initial_results_soup = BeautifulSoup(initial_page_source.text, 'html.parser')
        pagination = self.update_pagination(pagination=pagination, page_soup=initial_results_soup)

        while pagination.has_next():
            page_url = pagination.get_next()
            print('\n------------ NEW PAGE ------------')
            if to_print:
                print('\tPage:\t', page_url)

            page_source = self.get_source(page_url=page_url)

            if page_source is None:
                print("Skipping page because page_source is None")
                continue
            results_soup = BeautifulSoup(page_source.text, 'html.parser')
            assert results_soup

            dok = results_soup.find('div', class_='obsah')
            assert dok
            ui = dok.find('ul', class_='ui')
            assert ui

            # Get the page number we are on -> if it greater than 3, skip
            # Only the first three pages contain documents made 2018 and after
            page_number = page_url[-1:]
            if int(page_number) > 1:
                print("\tSkipping page: " + page_number)
                continue

            for li in ui.find_all('li'):
                result_link = li.find('a')
                # s2. Documents
                document_title = result_link.get_text()
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite == False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue
                document_href = result_link.get('href')
                assert document_href
                if document_href.startswith('http') is not True:
                    host = "https://www.uoou.cz"
                    document_url = host + document_href
                else:
                    document_url = document_href

                # TODO: One of the document_urls leads to a pdf link -> skip it for now
                if document_url == 'https://www.uoou.cz/assets/File.ashx?id_org=200144&id_dokumenty=31695':
                    continue

                document_response = None
                try:
                    document_response = requests.request('GET', document_url, timeout=2)
                    document_response.raise_for_status()
                except requests.exceptions.HTTPError as error:
                    pass
                if document_response is None:
                    print("\tSkipping existing document: document_response is None")
                    continue

                # Created soup for the document link
                document_soup = BeautifulSoup(document_response.text, 'html.parser')
                assert document_soup

                # If significant pdf links exists, go to them and download
                obalcelek_tag = document_soup.find('div', id='obalcelek')
                assert obalcelek_tag
                a_tag = obalcelek_tag.find_all('a')
                if a_tag:
                    for element in a_tag:
                        assert element
                        # Check if we can get a href and if that href contains the string 'File.ashx', which indicates
                        # the link is intended to be downloaded
                        if element.get('href') is not None and ('File.ashx' in element.get('href')) :
                            link_href = element.get('href')
                            assert link_href
                            link_url = 'https://www.uoou.cz' + link_href
                            print("Link URL: " + link_url)

                            link_response = None
                            try:
                                link_response = requests.request('GET', link_url, timeout=2)
                                link_response.raise_for_status()
                            except requests.exceptions.HTTPError as error:
                                pass
                            if link_response is None:
                                continue

                            # If get a link reponse, then write the contents of the file as a pdf and text
                            dpa_folder = self.path
                            document_folder = dpa_folder + '/' + 'Opinions' + '/' + document_hash
                            try:
                                os.makedirs(document_folder)
                            except FileExistsError:
                                pass
                            with open(document_folder + '/' + self.language_code + '.pdf', 'wb') as f:
                                f.write(link_response.content)
                            try:
                                with open(document_folder + '/' + self.language_code + '.txt', 'wb') as f:
                                    link_text = textract.process(document_folder + '/' + self.language_code + '.pdf')
                                    f.write(link_text)
                            # If the link leads to a word document or a file format other than a pdf
                            # -> skip text conversion
                            except:
                                pass
                        else:
                            continue

                # Don't try to find the document date -> website html is too inconsistent
                # When we print document stuff, that means the document is not going to be thrown out
                print('\n\t------------ Document: ' + str(iteration) + ' ------------')
                print('\tDocument year: ' + "Not available")
                iteration += 1
                if to_print:
                    print("\tDocument:\t", document_hash)
                obsah = document_soup.find('div', class_='obsah')
                assert obsah
                document_text = obsah.get_text()
                document_text = document_text.lstrip()
                dpa_folder = self.path
                document_folder = dpa_folder + '/' + 'Opinions' + '/' + document_hash
                try:
                    os.makedirs(document_folder)
                except FileExistsError:
                    pass
                with open(document_folder + '/' + self.language_code + 'Summary' + '.txt', 'w') as f:
                    f.write(document_text)
                with open(document_folder + '/' + 'metadata.json', 'w') as f:
                    metadata = {
                        'title': {
                            self.language_code: document_title
                        },
                        'md5': document_hash,
                        'releaseDate': "Date not available",
                        'url': document_url
                    }
                    json.dump(metadata, f, indent=4, sort_keys=True)
                added_docs.append(document_hash)
                # Don't need to call update_pagination -> it already has all the pages
        return added_docs
