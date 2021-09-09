import os
import math
import requests
import json
import datetime
import hashlib
from pygdpr.models.dpa import DPA
from bs4 import BeautifulSoup
from pygdpr.services.filename_from_path_service import filename_from_path_service
from pygdpr.services.pdf_to_text_service import PDFToTextService
from pygdpr.specifications import pdf_file_extension_specification
from pygdpr.models.pagination import Pagination
from pygdpr.specifications.should_retain_document_specification import ShouldRetainDocumentSpecification
from pygdpr.policies.gdpr_policy import GDPRPolicy
from pygdpr.policies.webdriver_exec_policy import WebdriverExecPolicy

class Denmark(DPA):
    def __init__(self, path):
        country_code='DK'
        super().__init__(country_code, path)

    def update_pagination(self, pagination=None, page_soup=None, driver=None):
        source = {
            'host': 'https://www.datatilsynet.dk',
            'start_path': '/tilsyn-og-afgoerelser/afgoerelser/proxy.gba'
        }
        host = source['host']
        start_path = source['start_path']
        page_url = host + start_path
        payload = {
            "url": page_url,
            "body": {
                "control": "GoBasic.Presentation.Controls.ListHelper, GoBasic.Presentation",
                "method": "GetPage",
                "path": "/tilsyn-og-afgoerelser/afgoerelser",
                "query": "",
                "args": {
                    "arg0": {
                        "options": {
                            "generator": "GoBasic.Presentation.Controls.ListHelper, GoBasic.Presentation",
                            "dateRange": True
                        },
                        "context": "eyJzaXRlU2VhcmNoIjogZmFsc2UsICJwZGZTZWFyY2giOiBmYWxzZSwgImNvbnRleHRQYXRoIjogIi9Db250ZW50L0RhdGF0aWxzeW5ldC9Gb3JzaWRlL1RpbHN5biBvZyBhZmfDuHJlbHNlci9BZmfDuHJlbHNlciIsICJmaWx0ZXIiOiB7InQiOiBbIldlYlBhZ2UiLCAiTmV3c1BhZ2UiLCAiUHVibGljYXRpb25QYWdlIiwgIkh0bWxQdWJsaWNhdGlvblBhZ2UiXSwgInJmIjogWyI2NTQzIl0sICJyIjogdHJ1ZSwgImNvIjogIk9yIiwgImN0byI6ICJBbmQifSwgIm9wdGlvbnMiOiB7InNob3dUZWFzZXIiOiB0cnVlLCAic2hvd0NhdGVnb3JpemF0aW9ucyI6IHRydWUsICJzaG93RGF0ZSI6IHRydWUsICJkb05vdFNob3dJbml0aWFsUmVzdWx0cyI6IGZhbHNlLCAiZGlzcGxheVJlY29yZFR5cGVGaWx0ZXIiOiBmYWxzZSwgImluY2x1ZGVQaW5uZWRTZWFyY2hRdWVyaWVzIjogZmFsc2UsICJzaG93UnNzTGluayI6IGZhbHNlLCAibWF4SXRlbXNTaG93biI6IDEwLCAiZ3JvdXBCeSI6ICJOb0dyb3VwaW5nIiwgInNob3dQYWdlciI6IHRydWUsICJzaG93TG9hZE1vcmUiOiBmYWxzZSwgInJzc1RpdGxlIjogIiIsICJyc3NEZXNjcmlwdGlvbiI6ICIiLCAic2hvd1RodW1ibmFpbHMiOiB0cnVlLCAic2hvd0Fic29sdXRlVXJsIjogZmFsc2UsICJ0cmFuc2xhdGlvbkZvbGRlciI6ICJBcmNoaXZlIiwgInNvdXJjZVBhdGgiOiAiIiwgInNob3dGb3JtYXR0ZWRVcmwiOiBmYWxzZSwgImZlYXR1cmVkSXRlbUlkcyI6ICIiLCAiY29sdW1ucyI6IDEsICJwaW5uZWRDb2x1bW5zIjogMSwgInJlc1R4dE5vbmUiOiAiRGluIHPDuGduaW5nIGVmdGVyICcjI3F1ZXJ5IyMnIGdhdiBpbmdlbiByZXN1bHRhdGVyIiwgInJlc1R4dFNpbmd1bGFyIjogIkRpbiBzw7hnbmluZyBlZnRlciAnIyNxdWVyeSMjJyBnYXYgIyN0b3RhbHJlc3VsdHMjIyByZXN1bHRhdCIsICJyZXNUeHRQbHVyYWwiOiAiRGluIHPDuGduaW5nIGVmdGVyICcjI3F1ZXJ5IyMnIGdhdiAgIyN0b3RhbHJlc3VsdHMjIyByZXN1bHRhdGVyIiwgInNvcnRpbmciOiAiIiwgImhlYWRsaW5lRW1wdHkiOiBmYWxzZSwgIm9wZW5MaW5rc0luUG9wdXBXaW5kb3ciOiBmYWxzZSwgImNoYW5nZUZyb21IMlRvSDEiOiB0cnVlLCAiZG9Ob3RTaG93T2xkRG9jdW1lbnRzIjogZmFsc2V9fQ==",
                        "hash": "0c5d99c727a97e64abbe4a2f0b06833fcf390d903a747221a70e2ed753b2c643"
                    },
                    "arg1": 2,
                    "arg2": {
                        "categorizations": []
                    },
                    "arg3": ""
                }
            }
        }
        if pagination is None:
            pagination = Pagination()
            pagination.add_item(payload)
        else:
            payload['body']['args']['arg1'] = page_soup['body']['args']['arg1'] + 1
            pagination.add_item(payload)
        return pagination

    def get_source(self, page_url=None, driver=None):
        url = page_url['url']
        payload = json.dumps(page_url['body'])
        headers = {
            'Content-Type': "application/json",
        }
        response = requests.request("POST", url, data=payload, headers=headers)
        return response.json()['value']['page']

    def get_docs(self, existing_docs=[], overwrite=False, to_print=True):
        added_docs = []
        # s0. Pagination
        pagination = self.update_pagination()
        while pagination.has_next():
            page_url = pagination.get_next()
            if to_print:
                print('Page:\t', page_url['url'])
            page_source = self.get_source(page_url=page_url)
            if page_source is None:
                continue
            page_soup = BeautifulSoup(page_source, 'html.parser')
            assert page_soup
            no_results = page_soup.find('p', class_='no-results')
            if no_results is not None:
                break
            ul = page_soup.find('ul', class_='items')
            assert ul
            # s1. Results
            for li in ul.find_all('li', class_='item'):
                content = li.find('div', class_='content')
                assert content
                span_date = content.find('span', class_='date')
                assert span_date
                date_str = span_date.get_text().strip().split(' ')[-1]
                tmp = datetime.datetime.strptime(date_str, '%d-%m-%Y')
                date = datetime.date(tmp.year, tmp.month, tmp.day)
                if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                    continue
                h2 = content.find('h2')
                assert h2
                result_link = h2.find('a')
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
                host = 'https://www.datatilsynet.dk'
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
                document_soup = BeautifulSoup(document_response.text, 'html.parser')
                assert document_soup
                news_page = document_soup.find('div', class_='news-page')
                assert news_page
                document_text = news_page.get_text()
                document_text = document_text.lstrip()
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
            pagination = self.update_pagination(pagination=pagination, page_soup=page_url)
        return added_docs
