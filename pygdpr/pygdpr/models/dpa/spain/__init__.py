import os
import time
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
import sys


class Spain(DPA):
    def __init__(self, path=os.curdir):
        country_code='es'
        super().__init__(country_code, path)

    # TODD: Fix bug in this method
    def update_pagination(self, pagination=None, page_soup=None, driver=None):
        source = {
            "host": "https://www.aepd.es",
            "start_path_new_page": "/es/informes-y-resoluciones/resoluciones",
            "start_path": "/es/informes-y-resoluciones/resoluciones?f%5B0%5D=ley_tipificacion_de_la_gravedad%3AReglamento%20General%20de%20Protecci%C3%B3n%20de%20Datos"
        }
        host = source['host']
        start_path = source['start_path']
        start_path_new_page = source['start_path_new_page']

        if pagination is None:
            pagination = Pagination()
            pagination.add_item(host + start_path)
        else:
            assert page_soup is not None
            pager = page_soup.find('nav', class_='pager')
            assert pager
            pager_items = pager.find('ul', class_='pager__items')
            assert pager_items

            # Only look at the visible next 9 items
            for li in pager_items.find_all('li', class_='pager__item')[1:9]:
                page_link = li.find('a')
                if page_link is None:
                    continue
                page_href = page_link.get('href')

                page_link = host + start_path_new_page + page_href

                # If the pagination object already has the page link, don't add it
                if not pagination.has_link(page_link):
                    print('\n')
                    print('Adding page: ' + page_link + ' to pagination object')
                    pagination.add_item(page_link)

        return pagination

    def get_source(self, page_url=None, driver=None):
        assert (page_url is not None)
        page_source = None
        try:
            page_source = requests.request('GET', page_url)
            page_source.raise_for_status()
        except requests.exceptions.HTTPError as error:
            pass
        return page_source

    def get_docs_Decisions(self, existing_docs=[], overwrite=False, to_print=True):
        print('------------ GETTING DECISION ------------')

        added_docs = []
        pagination = self.update_pagination()

        iteration = 1
        while pagination.has_next():
            page_url = pagination.get_next()
            if to_print:
                print('\nNEW PAGE: ' + page_url)

            page_source = self.get_source(page_url=page_url)
            page_soup = BeautifulSoup(page_source.text, 'html.parser')
            assert page_soup

            view_content = page_soup.find('div', class_='view-content')
            assert view_content

            for views_row in view_content.find_all('div', class_='views-row'):
                time.sleep(5)
                views_field_title = views_row.find('div', class_='views-field-title')
                assert views_field_title
                result_link = views_field_title.find('a')
                if result_link is None:
                    continue

                document_title = result_link.get_text()

                print('\n------------ Document ' + str(iteration) + ' ------------')
                iteration += 1

                print('\tDocument Title: ' + document_title)

                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite is False:
                    if to_print:
                        print('\tSkipping existing document:', document_hash)
                    continue
                document_href = result_link.get('href')
                assert document_href
                if document_href.endswith('.pdf') is False:
                    continue
                host = "https://www.aepd.es"
                document_url = host + document_href

                print('\tDocument URL: ' + document_url)
                views_field_field_advertise_on = views_row.find('div', class_='views-field-field-advertise-on')
                assert views_field_field_advertise_on
                time_ = views_field_field_advertise_on.find('time')
                assert time_
                date_str = time_.get('datetime')
                date_str = date_str.split('T')[0]
                tmp = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                date = datetime.date(tmp.year, tmp.month, tmp.day)

                print('\tDocument Date: ' + str(date))

                document_year = str(date)[0:4]
                if int(document_year) < 2018:
                    print('Skipping outdated document')
                    continue

                # By the time we reach document from 2016 and below, it is unlikely to encounter any relevant ones
                if int(document_year) < 2017:
                    sys.exit('Remaining documents outdated')


                '''
                if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                    continue
                if to_print:
                    print("\tDocument:", document_hash)
                '''

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

                document_content = document_response.content
                dpa_folder = self.path
                document_folder = dpa_folder + '/' + 'Decisions' + '/' + document_hash

                try:
                    os.makedirs(document_folder)
                except FileExistsError:
                    pass
                with open(document_folder + '/' + self.language_code + '.pdf', 'wb') as f:
                    f.write(document_content)
                with open(document_folder + '/' + self.language_code + '.txt', 'wb') as f:
                    try:
                        document_text = textract.process(document_folder + '/' + self.language_code + '.pdf')
                        f.write(document_text)
                    except:
                        print('Failed to convert PDF to text')
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
            pagination = self.update_pagination(pagination=pagination, page_soup=page_soup)
        return added_docs
