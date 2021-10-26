import os
import math
import requests
import json
import datetime
import hashlib
import dateparser
import re
from pygdpr.models.dpa import DPA
from bs4 import BeautifulSoup
from pygdpr.services.filename_from_path_service import filename_from_path_service
from pygdpr.services.pdf_to_text_service import PDFToTextService
from pygdpr.specifications import pdf_file_extension_specification
from pygdpr.specifications.should_retain_document_specification import ShouldRetainDocumentSpecification
from pygdpr.models.common.pagination import Pagination
from pygdpr.policies.gdpr_policy import GDPRPolicy
import textract
import time

# TODO: Run newely implemented links overnight to gather all documents
class Italy(DPA):
    def __init__(self, path=os.curdir):
        country_code='IT'
        super().__init__(country_code, path)

    def update_pagination(self, pagination=None, page_soup=None, driver=None, start_path=None):
        source = {
            "host": "https://www.garanteprivacy.it",
            "start_path": "/web/guest/home/stampa-comunicazione/interviste"
        }
        host = source['host']
        start_path = start_path

        if page_soup is not None:
            pagination = Pagination()

            # Page soup should be the page results_soup object
            pages = page_soup.find('ul', class_='pagination justify-content-center mt-3')
            assert pages

            li_page_list = pages.find_all('li', class_='page-item')
            assert li_page_list

            last_page_a = li_page_list[-2].find('a')
            assert last_page_a

            num_pages = int(last_page_a.get_text())

            # Add all the pages (including the first here)
            for num in range(1, num_pages + 1):
                page_link = host + start_path + str(num)
                print(page_link)
                pagination.add_item(page_link)
        else:
            print("Please give update_pagination() a page_source argument")
            pass

        return pagination

    def get_source(self, page_url=None, driver=None, to_print=True):
        assert (page_url is not None)
        results_response = None
        try:
            results_response = requests.request('GET', page_url, timeout=5)
            results_response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            if to_print:
                print(error)
            pass
        return results_response

    def get_docs(self, existing_docs=[], overwrite=False, to_print=True):
        added_docs = []
        pagination = self.update_pagination()
        # s0. Pagination
        while pagination.has_next():
            page_url = pagination.get_next()
            if to_print:
                print('Page:\t', page_url)
            page_source = self.get_source(page_url=page_url)
            if page_source is None:
                continue
            results_soup = BeautifulSoup(page_source.text, 'html.parser')
            assert results_soup
            testo = results_soup.find('div', class_='testo')
            assert testo
            ul_all = testo.find_all('ul', recursive=False)
            # s1. Results
            for ul in ul_all:
                for li in ul.find_all('li'):
                    time.sleep(5)
                    result_link = li.find('a')
                    assert result_link
                    # s2. Document
                    document_title = result_link.get_text()
                    document_hash = hashlib.md5(document_title.encode()).hexdigest()
                    if document_hash in existing_docs and overwrite == False:
                        if to_print:
                            print('\tSkipping existing document:\t', document_hash)
                        continue
                    document_href = result_link.get('href')
                    if document_href.startswith('http') and document_href.startswith(host) is False:
                        continue
                    document_url = document_href
                    if document_href.startswith('http') is False:
                        host = "https://www.garanteprivacy.it"
                        document_url = host + document_url
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
                    scheda = document_soup.find('div', class_='scheda')
                    if scheda is None:
                        continue
                    dl = scheda.find('dl')
                    assert dl
                    date_index = -1
                    dt_all = dl.find_all('dt', recursive=False)
                    for i in range(len(dt_all)):
                        dt = dt_all[i]
                        if dt.get_text().strip().startswith('Data'):
                            date_index = i
                            break
                    if date_index == -1:
                        continue
                    dd_all = dl.find_all('dd')
                    assert dd_all
                    dd = dd_all[date_index]
                    date_str = dd.get_text().strip()
                    tmp = datetime.datetime.strptime(date_str, '%d/%m/%y')
                    date = datetime.date(tmp.year, tmp.month, tmp.day)
                    if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                        continue
                    pdf_form = document_soup.find('form', {'name': 'pdfForm'})
                    if pdf_form is None:
                        continue
                    action = pdf_form.get('action')
                    assert action
                    if to_print:
                        print("\tDocument:\t", document_hash)
                    file_url = action
                    file_response = None
                    try:
                        file_response = requests.request('GET', file_url)
                        file_response.raise_for_status()
                    except requests.exceptions.HTTPError as error:
                        if to_print:
                            print(error)
                        pass
                    if file_response is None:
                        continue
                    file_content = file_response.content
                    dpa_folder = self.path
                    document_folder = dpa_folder + '/' + document_hash
                    try:
                        os.makedirs(document_folder)
                    except FileExistsError:
                        pass
                    with open(document_folder + '/' + self.language_code + '.pdf', 'wb') as f:
                        f.write(file_content)
                    with open(document_folder + '/' + self.language_code + '.txt', 'wb') as f:
                        document_text = textract.process(document_folder + '/' + self.language_code + '.pdf')
                        document_text = document_text.strip()
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

    # Utilizes the link starting at page 1, rather than the generic link
    def get_docs_Injunctions(self, existing_docs=[], overwrite=False, to_print=True):
        print('------------ GETTING INJUNCTIONS ------------')
        added_docs = []

        # Create pagination object and add all pages at once
        init_page_url = 'https://www.garanteprivacy.it/home/ricerca?p_p_id=g_gpdp5_search_GGpdp5SearchPortlet&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_g_gpdp5_search_GGpdp5SearchPortlet_mvcRenderCommandName=%2FrenderSearch&_g_gpdp5_search_GGpdp5SearchPortlet_text=&_g_gpdp5_search_GGpdp5SearchPortlet_dataInizio=&_g_gpdp5_search_GGpdp5SearchPortlet_dataFine=&_g_gpdp5_search_GGpdp5SearchPortlet_idsTipologia=10526&_g_gpdp5_search_GGpdp5SearchPortlet_idsArgomenti=&_g_gpdp5_search_GGpdp5SearchPortlet_quanteParole=&_g_gpdp5_search_GGpdp5SearchPortlet_quanteParoleStr=&_g_gpdp5_search_GGpdp5SearchPortlet_nonParoleStr=&_g_gpdp5_search_GGpdp5SearchPortlet_paginaWeb=false&_g_gpdp5_search_GGpdp5SearchPortlet_allegato=false&_g_gpdp5_search_GGpdp5SearchPortlet_ordinamentoPer=DESC&_g_gpdp5_search_GGpdp5SearchPortlet_ordinamentoTipo=data&_g_gpdp5_search_GGpdp5SearchPortlet_cur=1'
        init_page_source = self.get_source(page_url=init_page_url)
        init_results_soup = BeautifulSoup(init_page_source.text, 'html.parser')
        assert init_results_soup
        # The start_path doesn't contain the very last character, which is the unique page number
        pagination = self.update_pagination(start_path='/home/ricerca?p_p_id=g_gpdp5_search_GGpdp5SearchPortlet&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_g_gpdp5_search_GGpdp5SearchPortlet_mvcRenderCommandName=%2FrenderSearch&_g_gpdp5_search_GGpdp5SearchPortlet_text=&_g_gpdp5_search_GGpdp5SearchPortlet_dataInizio=&_g_gpdp5_search_GGpdp5SearchPortlet_dataFine=&_g_gpdp5_search_GGpdp5SearchPortlet_idsTipologia=10526&_g_gpdp5_search_GGpdp5SearchPortlet_idsArgomenti=&_g_gpdp5_search_GGpdp5SearchPortlet_quanteParole=&_g_gpdp5_search_GGpdp5SearchPortlet_quanteParoleStr=&_g_gpdp5_search_GGpdp5SearchPortlet_nonParoleStr=&_g_gpdp5_search_GGpdp5SearchPortlet_paginaWeb=false&_g_gpdp5_search_GGpdp5SearchPortlet_allegato=false&_g_gpdp5_search_GGpdp5SearchPortlet_ordinamentoPer=DESC&_g_gpdp5_search_GGpdp5SearchPortlet_ordinamentoTipo=data&_g_gpdp5_search_GGpdp5SearchPortlet_cur=', page_soup=init_results_soup)

        iteration = 1
        while pagination.has_next():
            page_url = pagination.get_next()
            if to_print:
                print('\n New Page:\t', page_url)
            page_source = self.get_source(page_url=page_url)
            if page_source is None:
                continue
            results_soup = BeautifulSoup(page_source.text, 'html.parser')
            assert results_soup

            section = results_soup.find('section', id='content')
            assert section

            blocco = section.find('div', class_='blocco-risultati')
            assert blocco

            for div in blocco.find_all('div', class_='card-risultato'):
                assert div
                time.sleep(5)

                # Obtain the document date
                date_div = div.find('div', class_='data-risultato')
                assert date_div
                p_tag = date_div.find('p')
                assert p_tag
                document_date = p_tag.get_text()

                # Check if the document is outdated
                document_year = document_date[-4:]
                if int(document_year) < 2018:
                    print("Skipping outdated document")
                    continue


                result_link = div.find('a', class_='titolo-risultato')
                assert result_link

                print('\n------------ Document ' + str(iteration) + ' ------------')
                iteration += 1
                print('\tDocument Date: ' + document_date)
                document_title = result_link.get_text()
                print('\tDocument Title: ' + document_title)
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite is False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue

                document_href = result_link.get('href')
                if document_href.startswith('http') and document_href.startswith(host) is False:
                    continue
                document_url = document_href
                if document_href.startswith('http') is False:
                    host = "https://www.garanteprivacy.it"
                    document_url = host + document_url
                document_response = None

                try:
                    document_response = requests.request('GET', document_url, timeout=5)
                    document_response.raise_for_status()
                except requests.exceptions.HTTPError as error:
                    if to_print:
                        print(error)
                    pass
                if document_response is None:
                    continue

                document_soup = BeautifulSoup(document_response.text, 'html.parser')
                assert document_soup

                body = document_soup.find('body')
                assert body

                body_text = body.find('div', class_='col-md-8 pl-4 px-md-5')
                assert body_text

                text_print_format = body_text.find('div', id='div-to-print')
                assert text_print_format

                second_text_print = text_print_format.find('div', class_='journal-content-article')
                assert second_text_print

                if to_print:
                    print("\tDocument:\t", document_hash)

                dpa_folder = self.path
                document_folder = dpa_folder + '/' + 'Injunctions' + '/' + document_hash

                try:
                    os.makedirs(document_folder)
                except FileExistsError:
                    pass
                with open(document_folder + '/' + self.language_code + '.txt', 'wb') as f:
                    f.write(second_text_print.get_text().encode())
                with open(document_folder + '/' + 'metadata.json', 'w') as f:
                    metadata = {
                        'title': {
                            self.language_code: document_title
                        },
                        'md5': document_hash,
                        'releaseDate': document_date,
                        'url': document_url
                    }
                    json.dump(metadata, f, indent=4, sort_keys=True)
                added_docs.append(document_hash)
        return added_docs

    # Utilizes the link starting at page 1, rather than the generic link
    def get_docs_Newsletters(self, existing_docs=[], overwrite=False, to_print=True):
        print('------------ GETTING NEWSLETTERS ------------')
        added_docs = []

        # Create pagination object and add all pages at once
        init_page_url = 'https://www.garanteprivacy.it/home/ricerca?p_p_id=g_gpdp5_search_GGpdp5SearchPortlet&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_g_gpdp5_search_GGpdp5SearchPortlet_mvcRenderCommandName=%2FrenderSearch&_g_gpdp5_search_GGpdp5SearchPortlet_text=&_g_gpdp5_search_GGpdp5SearchPortlet_dataInizio=&_g_gpdp5_search_GGpdp5SearchPortlet_dataFine=&_g_gpdp5_search_GGpdp5SearchPortlet_idsTipologia=10524&_g_gpdp5_search_GGpdp5SearchPortlet_idsArgomenti=&_g_gpdp5_search_GGpdp5SearchPortlet_quanteParole=&_g_gpdp5_search_GGpdp5SearchPortlet_quanteParoleStr=&_g_gpdp5_search_GGpdp5SearchPortlet_nonParoleStr=&_g_gpdp5_search_GGpdp5SearchPortlet_paginaWeb=false&_g_gpdp5_search_GGpdp5SearchPortlet_allegato=false&_g_gpdp5_search_GGpdp5SearchPortlet_ordinamentoPer=DESC&_g_gpdp5_search_GGpdp5SearchPortlet_ordinamentoTipo=data&_g_gpdp5_search_GGpdp5SearchPortlet_cur=1'
        init_page_source = self.get_source(page_url=init_page_url)
        init_results_soup = BeautifulSoup(init_page_source.text, 'html.parser')
        assert init_results_soup
        # The start_path doesn't contain the very last character, which is the unique page number
        pagination = self.update_pagination(start_path='/home/ricerca?p_p_id=g_gpdp5_search_GGpdp5SearchPortlet&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_g_gpdp5_search_GGpdp5SearchPortlet_mvcRenderCommandName=%2FrenderSearch&_g_gpdp5_search_GGpdp5SearchPortlet_text=&_g_gpdp5_search_GGpdp5SearchPortlet_dataInizio=&_g_gpdp5_search_GGpdp5SearchPortlet_dataFine=&_g_gpdp5_search_GGpdp5SearchPortlet_idsTipologia=10524&_g_gpdp5_search_GGpdp5SearchPortlet_idsArgomenti=&_g_gpdp5_search_GGpdp5SearchPortlet_quanteParole=&_g_gpdp5_search_GGpdp5SearchPortlet_quanteParoleStr=&_g_gpdp5_search_GGpdp5SearchPortlet_nonParoleStr=&_g_gpdp5_search_GGpdp5SearchPortlet_paginaWeb=false&_g_gpdp5_search_GGpdp5SearchPortlet_allegato=false&_g_gpdp5_search_GGpdp5SearchPortlet_ordinamentoPer=DESC&_g_gpdp5_search_GGpdp5SearchPortlet_ordinamentoTipo=data&_g_gpdp5_search_GGpdp5SearchPortlet_cur=', page_soup=init_results_soup)

        iteration = 1
        while pagination.has_next():
            page_url = pagination.get_next()
            if to_print:
                print('\n New Page:\t', page_url)
            page_source = self.get_source(page_url=page_url)
            if page_source is None:
                continue
            results_soup = BeautifulSoup(page_source.text, 'html.parser')
            assert results_soup

            section = results_soup.find('section', id='content')
            assert section

            blocco = section.find('div', class_='blocco-risultati')
            assert blocco

            for div in blocco.find_all('div', class_='card-risultato'):
                assert div
                time.sleep(5)

                # Obtain the document date
                date_div = div.find('div', class_='data-risultato')
                assert date_div
                p_tag = date_div.find('p')
                assert p_tag
                document_date = p_tag.get_text()

                # Check if the document is outdated
                document_year = document_date[-4:]
                if int(document_year) < 2018:
                    print("Skipping outdated document")
                    continue


                result_link = div.find('a', class_='titolo-risultato')
                assert result_link

                print('\n------------ Document ' + str(iteration) + ' ------------')
                iteration += 1
                print('\tDocument Date: ' + document_date)
                document_title = result_link.get_text()
                print('\tDocument Title: ' + document_title)
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite is False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue

                document_href = result_link.get('href')
                if document_href.startswith('http') and document_href.startswith(host) is False:
                    continue
                document_url = document_href
                if document_href.startswith('http') is False:
                    host = "https://www.garanteprivacy.it"
                    document_url = host + document_url
                document_response = None

                try:
                    document_response = requests.request('GET', document_url, timeout=5)
                    document_response.raise_for_status()
                except requests.exceptions.HTTPError as error:
                    if to_print:
                        print(error)
                    pass
                if document_response is None:
                    continue

                document_soup = BeautifulSoup(document_response.text, 'html.parser')
                assert document_soup

                body = document_soup.find('body')
                assert body

                body_text = body.find('div', class_='col-md-8 pl-4 px-md-5')
                assert body_text

                text_print_format = body_text.find('div', id='div-to-print')
                assert text_print_format

                # Try to go deep in order to get text without excess html baggage
                obtained_text = None
                try:
                    second_text_print = text_print_format.find('div', class_='journal-content-article')
                    assert second_text_print
                    obtained_text = second_text_print
                except:
                    obtained_text = text_print_format

                assert obtained_text

                if to_print:
                    print("\tDocument:\t", document_hash)

                dpa_folder = self.path
                document_folder = dpa_folder + '/' + 'Newsletters' + '/' + document_hash

                try:
                    os.makedirs(document_folder)
                except FileExistsError:
                    pass
                with open(document_folder + '/' + self.language_code + '.txt', 'wb') as f:
                    f.write(obtained_text.get_text().encode())
                with open(document_folder + '/' + 'metadata.json', 'w') as f:
                    metadata = {
                        'title': {
                            self.language_code: document_title
                        },
                        'md5': document_hash,
                        'releaseDate': document_date,
                        'url': document_url
                    }
                    json.dump(metadata, f, indent=4, sort_keys=True)
                added_docs.append(document_hash)
        return added_docs
