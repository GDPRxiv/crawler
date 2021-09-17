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
from pygdpr.models.common.pagination import Pagination
from pygdpr.policies.gdpr_policy import GDPRPolicy
from striprtf.striprtf import rtf_to_text
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pygdpr.policies.webdriver_exec_policy import WebdriverExecPolicy
from urllib.parse import urlparse
from pygdpr.models.document import *
import time

class France(DPA):
    def __init__(self, path=os.curdir):
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
            pagination = Pagination()
            pagination.add_item(host + start_path)
        else:
            pager_load_more = page_soup.find('ul', class_='pager-load-more')
            if pager_load_more is not None:
                pager_next = pager_load_more.find('li', class_='pager-next')
                page_link = pager_next.find('a')
                page_href = page_link.get('href')
                pagination = Pagination()
                pagination.add_item(host + page_href)
        return pagination

    def get_source(self, page_url=None, driver=None):
        assert page_url is not None
        results_response = None
        try:
            results_response = requests.request('GET', page_url, timeout=1000)
            results_response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            pass
        return results_response

    def get_docs(self, existing_docs=[], overwrite=False, to_print=True):
        added_docs = []
        pagination = self.update_pagination()
        added_docs_set = set()
        url = "https://sandbox-oauth.piste.gouv.fr/api/oauth/token"
        client_id = os.environ["PISTE_CLIENT_ID"]
        client_secret = os.environ["PISTE_CLIENT_SECRET"]
        assert client_id and client_secret
        data = {
            "6c214ae3d2edc9c49a419f7870fe47f7": "1",
            "grant_type": "client_credentials",
            "client_id": os.environ["PISTE_CLIENT_ID"],
            "client_secret": os.environ["PISTE_CLIENT_SECRET"],
            "scope": "openid"
        }
        payload = '&'.join([k + "=" + v for k, v in data.items()])
        headers = {
            'Content-Type': "application/x-www-form-urlencoded",
            'cache-control': "no-cache"
        }
        response = requests.request("GET", url, data=payload, headers=headers, timeout=1000)
        body = response.json()
        assert "access_token" in body.keys()
        access_token = body["access_token"]
        while pagination.has_next():
            page_url = pagination.get_next()
            page_source = self.get_source(page_url=page_url)
            if page_source is None:
                continue
            # s1. Results
            results_soup = BeautifulSoup(page_source.text, 'html.parser')
            assert results_soup
            view_content = results_soup.find('div', class_='view-content')
            assert view_content
            for views_row in view_content.find_all('div', class_='views-row'):
                time.sleep(5)
                result_link = views_row.find('a')
                document_href = result_link.get('href')
                o = urlparse(document_href)
                cnil_text = o.query.split('=')[-1]
                added_docs_set.add(cnil_text)
                url = "https://sandbox-api.piste.gouv.fr/dila/legifrance-beta/lf-engine-app/consult/cnil"
                body_params = {
                    "textId": cnil_text
                }
                payload = json.dumps(body_params)
                bearer_token = "Bearer {access_token}".format(access_token=access_token)
                headers = {
                    'Content-Type': "application/json",
                    'Authorization': bearer_token,
                }

                response = requests.request("POST", url, data=payload, headers=headers, timeout=1000)
                if "text" not in response.json().keys():
                    continue
                text = response.json()['text']
                timestamp_ms = text["datePubli"]
                tmp = datetime.datetime.fromtimestamp(timestamp_ms/1000.0)
                date = datetime.date(tmp.year, tmp.month, tmp.day)
                if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                    continue
                # s2. Documents
                document_title = text["titre"]
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite == False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue
                if to_print:
                    print("\tDocument:\t", document_hash)
                document_text_html = text["texteHtml"]
                document_soup = BeautifulSoup(document_text_html, 'html.parser')
                assert document_soup
                document_text = document_soup.get_text()
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
                            self.language_code: document_title.encode('utf8').decode('utf8')
                        },
                        'md5': document_hash,
                        'releaseDate': date.strftime('%d/%m/%Y'),
                        'url': document_href
                    }
                    json.dump(metadata, f, indent=4, sort_keys=True)
                added_docs.append(document_hash)
            pagination = self.update_pagination(pagination=pagination, page_soup=results_soup)
        return added_docs
