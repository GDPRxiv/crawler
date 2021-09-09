import os
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
from pygdpr.models.pagination import Pagination
from pygdpr.policies.gdpr_policy import GDPRPolicy
import textract

class Lithuania(DPA):
    def __init__(self, path):
        country_code='lt'
        super().__init__(country_code, path)

    def update_pagination(self, pagination=None, page_soup=None, driver=None):
        source = {
            "host": "https://vdai.lrv.lt",
            "start_path": "/lt/naujienos/exportPublicData?export_data_type=csv&download=1"
        }
        host = source["host"]
        start_path = source["start_path"]
        if pagination is None:
            pagination = Pagination()
            pagination.add_item(host + start_path)
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
            page_source = self.get_source(page_url=page_url)
            if page_source is None:
                continue
            results_content = page_source.content
            tmp_export_path = '/tmp/' + self.country.replace(' ', '-').lower() + '-export-data' + '.csv'
            with open(tmp_export_path, 'wb') as f:
                f.write(results_content)
            with open(tmp_export_path, encoding="utf-8-sig") as csvfile:
                csvreader = csv.DictReader(csvfile, delimiter=";")
                # s1. Results
                for row in csvreader:
                    date_from = row['date_from']
                    tmp = datetime.datetime.strptime(date_from, '%Y-%m-%d')
                    date = datetime.date(tmp.year, tmp.month, tmp.day)
                    if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                        continue
                    # s2. Document
                    title, link, description_html = row['title'], row['link'], row['description']
                    document_title = title
                    document_hash = hashlib.md5(document_title.encode()).hexdigest()
                    if document_hash in existing_docs and overwrite == False:
                        if to_print:
                            print('\tSkipping existing document:\t', document_hash)
                        continue
                    document_href = link
                    document_url = f"https{document_href}"
                    if to_print:
                        print("\tDocument:\t", document_hash)
                    document_soup = BeautifulSoup(description_html, 'html.parser')
                    assert document_soup
                    document_text = document_soup.get_text()
                    document_text = document_text.strip()
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
        return added_docs
