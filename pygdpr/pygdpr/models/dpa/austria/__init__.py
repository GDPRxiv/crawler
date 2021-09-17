import os
import shutil
import math
import requests
import json
import datetime
import hashlib
from pygdpr.models.dpa import DPA
from bs4 import BeautifulSoup
import textract
from pygdpr.services.filename_from_path_service import filename_from_path_service
from pygdpr.services.pdf_to_text_service import PDFToTextService
from pygdpr.specifications import pdf_file_extension_specification
from pygdpr.specifications.should_retain_document_specification import ShouldRetainDocumentSpecification
from pygdpr.models.common.pagination import Pagination
from pygdpr.specifications.root_document_specification import RootDocumentSpecification
from pygdpr.policies.gdpr_policy import GDPRPolicy

class Austria(DPA):
    def __init__(self, path=os.curdir):
        country_code='AT'
        super().__init__(country_code, path)

    def update_pagination(self, pagination=None, page_soup=None, driver=None):
        from_date = GDPRPolicy().implementation_date().strftime('%d.%m.%Y')
        to_date = datetime.datetime.now().strftime('%d.%m.%Y')
        source = {
            "host": "https://www.ris.bka.gv.at",
            "start_path": f"/Ergebnis.wxe?Abfrage=Dsk&Entscheidungsart=Undefined&Organ=Undefined&SucheNachRechtssatz=True&SucheNachText=True&GZ=&VonDatum={from_date}&BisDatum={to_date}&Norm=&ImRisSeitVonDatum=&ImRisSeitBisDatum=&ImRisSeit=Undefined&ResultPageSize=100&Suchworte=&Position=1&SkipToDocumentPage=true",
        }
        host = source['host']
        start_path = source['start_path']
        if pagination is None or page_soup is None:
            pagination = Pagination()
            pagination.add_item(host + start_path)
            return pagination
        pages = page_soup.find('ul', class_='pages')
        if pages is not None:
            for li in pages.find_all('li'):
                page_link = li.find('a')
                assert page_link
                page_href = page_link.get('href')
                pagination.add_item(host + page_href)
        return pagination

    def get_source(self, page_url=None, driver=None):
        assert (page_url is not None)
        results_response = None
        try:
            results_response = requests.request('GET', page_url)
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
            page_source = self.get_source(page_url)
            if page_source is None:
                continue
            page_soup = BeautifulSoup(page_source.text, 'html.parser')
            assert page_soup
            table = page_soup.find('table', class_='bocListTable')
            assert table
            tbody = table.find('tbody', class_='bocListTableBody')
            assert tbody
            # s1. Results
            for tr in tbody.find_all('tr', class_='bocListDataRow'):
                result_index, date_index, document_links_index = 2, 4, 8
                td_list = tr.find_all('td', class_='bocListDataCell')
                assert len(td_list) >= document_links_index + 1
                date_str = td_list[date_index].get_text()
                tmp = datetime.datetime.strptime(date_str, '%d.%m.%Y')
                date = datetime.date(tmp.year, tmp.month, tmp.day)
                if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                    continue
                result_link = td_list[result_index].find('a')
                assert result_link
                # s2. Documents
                document_title = result_link.get('title')
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite == False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue
                document_links = td_list[document_links_index]
                document_href = None
                for document_link in document_links.find_all('a'):
                    cand_href = document_link.get('href')
                    if cand_href.endswith('.pdf'):
                        document_href = cand_href
                        break
                assert document_href
                host = "https://www.ris.bka.gv.at"
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
                document_content = document_response.content
                dpa_folder = self.path
                document_folder = dpa_folder + '/' + document_hash
                try:
                    os.makedirs(document_folder)
                except FileExistsError:
                    pass
                with open(document_folder + '/' + self.language_code + '.pdf', 'wb') as f:
                    f.write(document_content)
                with open(document_folder + '/' + self.language_code + '.txt', 'wb') as f:
                    document_text = textract.process(document_folder + '/' + self.language_code + '.pdf')
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
