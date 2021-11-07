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

class Finland(DPA):
    def __init__(self, path=os.curdir):
        country_code='FI'
        super().__init__(country_code, path)

    # Removed update_pagination() and get_source() methods because they were not necessary
    # and contained major logic errors.

    # TODO: Ask about naming of documents: use 'fi' or 'en' ?
    def get_docs(self, existing_docs=[], overwrite=False, to_print=True):
        print('------------ GETTING FINLAND DOCUMENTS ------------')
        added_docs = []

        page_url = 'https://tietosuoja.fi/en/current-issues'
        if to_print:
            print('\nPAGE:\t', page_url)

        page_source = None
        try:
            page_source = requests.request('GET', page_url)
            page_source.raise_for_status()
        except requests.exceptions.HTTPError as error:
            if to_print:
                print(error)
            pass

        # Page parse object
        results_soup = BeautifulSoup(page_source.text, 'html.parser')
        assert results_soup

        # Each year has a ul tag with the links underneath (Although the page appears as if each
        # year is a separate page, the actual html layout is like on big page)
        ul_list = results_soup.find_all('ul', class_='results')
        assert ul_list

        for ul in ul_list:
            ul_year = ul.get('id')
            assert ul_year
            print("\nExamining documents for year: " + ul_year)

            iterator = 1
            for li in ul.find_all('li', class_='list__item'):
                span_date = li.find('span', class_='date')
                assert span_date
                date_str = span_date.get_text()
                tmp = datetime.datetime.strptime(date_str, '%d.%m.%Y')
                date = datetime.date(tmp.year, tmp.month, tmp.day)

                if date.year < 2018:
                    print("Skipping outdated document")
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

                print('\n------------ Document: ' + str(iterator) + ' ------------')
                print('\tDocument Title: ' + document_title)
                iterator += 1

                document_href = result_link.get('href')
                assert document_href
                host = "https://tietosuoja.fi"
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

                # Document parse object
                document_soup = BeautifulSoup(document_response.text, 'html.parser')
                assert document_soup

                # Obtain document text
                news_page = document_soup.find('div', class_='news-page')
                assert news_page
                document_text = news_page.get_text()
                document_text = document_text.lstrip()

                # Look at all links contained in the document
                document_p = news_page.find_all('p')
                assert document_p

                # Use this when naming the files for pdf links we download. Only increment if use it in a name.
                link_iterator = 1
                # This second iterator is for if we have finlex links on the page too
                # -> don't want to confuse with pdf stuff
                link_iterator_finlex_links = 1
                for p in document_p:
                    if p.find('a') is not None:
                        a_tag = p.find('a')
                        href = a_tag.get('href')
                        assert href

                        if href.startswith('http'):
                            url = href
                        else:
                            url = "https://tietosuoja.fi" + href

                        if '.pdf' in url:
                            pdf_response = None
                            try:
                                pdf_response = requests.request('GET', url)
                                pdf_response.raise_for_status()
                            except requests.exceptions.HTTPError as error:
                                if to_print:
                                    print(error)
                                pass
                            if pdf_response is None:
                                continue

                            print("\tDownloading PDF: " + url)
                            # Write pdf and its text to files
                            dpa_folder = self.path
                            document_folder = dpa_folder + '/' + str(ul_year) + ' Finland Documents' + '/' + document_hash

                            try:
                                os.makedirs(document_folder)
                            except FileExistsError:
                                pass
                            with open(document_folder + '/' + self.language_code + str(link_iterator) + '.pdf', 'wb') as f:
                                f.write(pdf_response.content)
                            with open(document_folder + '/' + self.language_code + str(link_iterator) + '.txt', 'wb') as f:
                                link_text = textract.process(document_folder + '/' + self.language_code + str(link_iterator) + '.pdf')
                                f.write(link_text)
                            link_iterator += 1

                        elif url.startswith('https://finlex'):
                            text_response = None
                            try:
                                text_response = requests.request('GET', url)
                                text_response.raise_for_status()
                            except requests.exceptions.HTTPError as error:
                                if to_print:
                                    print(error)
                                pass
                            if text_response is None:
                                continue

                            print("\tDownloading Finlex text: " + url)
                            text_soup = BeautifulSoup(document_response.text, 'html.parser')
                            assert text_soup

                            body = text_soup.find('div', id='main-content')
                            assert body
                            body_text = body.get_text()
                            body_text = body_text.lstrip()
                            assert body_text

                            dpa_folder = self.path
                            document_folder = dpa_folder + '/' + str(ul_year) + ' Finland Documents' + '/' + document_hash

                            try:
                                os.makedirs(document_folder)
                            except FileExistsError:
                                pass
                            with open(document_folder + '/' + self.language_code + 'Finlex' + str(link_iterator_finlex_links) + '.txt', 'wb') as f:
                                f.write(body_text.encode())
                            link_iterator_finlex_links += 1

                        # Link is not useful
                        else:
                            continue

                    # The <p tag doesn't provide a link
                    else:
                        continue

                dpa_folder = self.path
                document_folder = dpa_folder + '/' + str(ul_year) + ' Finland Documents' + '/' + document_hash
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
                        'releaseDate': date.strftime('%d/%m/%Y'),
                        'url': document_url
                    }
                    json.dump(metadata, f, indent=4, sort_keys=True)
                added_docs.append(document_hash)
        return added_docs
