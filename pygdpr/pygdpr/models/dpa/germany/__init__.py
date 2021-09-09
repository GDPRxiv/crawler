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
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
"""
from pygdpr.models.dpa.germany.dpa.baden_wurttemberg import BadenWurttemberg
from pygdpr.models.dpa.germany.bavaria import Bavaria
from pygdpr.models.dpa.germany.dpa.berlin import Berlin
from pygdpr.models.dpa.germany.dpa.brandenburg import Brandenburg
"""

class Germany(DPA):
    def __init__(self):
        country_code='de'
        super().__init__(country_code)

    def get_docs(self):
        print('docs - dpa germany')
        # BadenWurttemberg().get_docs()
        # Bavaria().get_docs()
        # Berlin().get_docs()
        # Brandenburg().get_docs()

        return True
