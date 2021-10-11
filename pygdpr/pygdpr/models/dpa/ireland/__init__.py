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

from selenium import webdriver


class Ireland(DPA):
    # When running, make sure path is correct for you system
    def __init__(self, path=os.curdir):
        country_code='IE'
        super().__init__(country_code, path)

    def update_pagination(self, pagination=None, page_soup=None, driver=None):
        # ireland has two (official/primary) sources:
        # press releases and (latest) news.
        source = {
            "host": "https://www.dataprotection.ie",
            # "start_path": "/en/news-media/press-releases"
            "start_path": "/en/news-media/latest-news"

        }
        host = source['host']
        start_path = source['start_path']
        if pagination is None:
            pagination = Pagination()
            pagination.add_item(host + start_path)
        else:
            # pagination = Pagination()
            pager = page_soup.find('nav', class_='pager')
            if pager is None:
                return pagination
            pager_items = pager.find('ul', class_='pager__items')
            if pager_items is None:
                return pagination
            for pager_item in pager_items.find_all('li', 'pager__item'):
                page_link = pager_item.find('a')
                if page_link is None:
                    continue
                page_href = page_link.get('href')
                pagination.add_item(host + start_path + page_href)
                print('added link to pagination:', host + start_path + page_href)
        return pagination

    # Fixed bug resulting in broken 'next page' links
    # Use this for get_docs_Blogs
    def update_pagination_noStart(self, pagination=None, page_soup=None, driver=None):
        # ireland has two (official/primary) sources:
        # press releases and (latest) news.
        source = {
            "host": "https://www.dataprotection.ie",
            # "start_path": "/en/news-media/press-releases"
            # "start_path": "/en/news-media/latest-news"  (This is the link the original scraper code uses)
            "start_path": "/dpc-guidance/blogs"
        }
        host = source['host']
        start_path = source['start_path']
        if pagination is None:
            pagination = Pagination()
            pagination.add_item(host + start_path)
        else:
            # pagination = Pagination()
            pager = page_soup.find('nav', class_='pager')
            if pager is None:
                return pagination
            pager_items = pager.find('ul', class_='pager__items')
            if pager_items is None:
                return pagination
            for pager_item in pager_items.find_all('li', 'pager__item'):
                page_link = pager_item.find('a')
                if page_link is None:
                    continue
                page_href = page_link.get('href')

                # Fixed Bug: Should be just host + page_href instead of host + start_path + page_href
                pagination.add_item(host + page_href)
                print('added link to pagination:', host + page_href)
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
        # call all the get_docs_X() functions
        added_docs += self.get_docs_News(existing_docs=[], overwrite=False, to_print=True)
        added_docs += self.get_docs_Decisions(existing_docs=[], overwrite=False, to_print=True)
        added_docs += self.get_docs_Judgements(existing_docs=[], overwrite=False, to_print=True)
        return added_docs


    def get_docs_News(self, existing_docs=[], overwrite=False, to_print=True):

        existed_docs = []
        pagination = self.update_pagination()
        # s0. Pagination
        while pagination.has_next():
            page_url = pagination.get_next()
            if to_print:
                print('Page:\t', page_url)
            page_zero = 'https://www.dataprotection.ie/en/news-media/latest-news?page=0'
            if page_url == page_zero:
                print('page_url == page_zero')
                continue

            page_source = self.get_source(page_url=page_url)
            if page_source is None:
                continue
            results_soup = BeautifulSoup(page_source.text, 'html.parser')
            assert results_soup
            view_content = results_soup.find('div', class_='view-content')
            assert view_content
            item_list = view_content.find('div', class_='item-list')
            assert item_list
            ul = item_list.find('ul')
            assert ul
            # s1. Results
            for li in ul.find_all('li', recursive=False):
                time.sleep(5)
                article = li.find('article')
                assert article
                p_date = article.find('p', class_='date')
                assert p_date
                date_str = p_date.get_text().strip()
                regex = r"(\d\d)(st|nd|rd|th) (\w*) (\d\d\d\d)"
                matches = re.finditer(regex, date_str)
                matches = list(matches)
                if len(matches) == 0:
                    continue
                match = matches[0]
                groups = match.groups()
                date_suffix_group_num = 2
                date_str = date_str[:match.start(date_suffix_group_num)] + date_str[match.end(date_suffix_group_num):]
                tmp = datetime.datetime.strptime(date_str, '%d %B %Y')
                date = datetime.date(tmp.year, tmp.month, tmp.day)
                if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                    #print('ShouldRetainDocumentSpecification is false')
                    continue
                h2 = article.find('h2')
                assert h2
                result_link = h2.find('a')
                assert result_link
                # s2. Documents
                document_title = result_link.get_text()
                print('document_title: ', document_title)

                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                if document_hash in existing_docs and overwrite == False:
                    if to_print:
                        print('\tSkipping existing document:\t', document_hash)
                    continue
                document_href = result_link.get('href')
                assert document_href
                host = "https://www.dataprotection.ie"
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
                # Here is where we parse the document_url page (which is the new page containg the text or another link)
                # TODO: Write code to examine the pdf's, which are the publications
                document_soup = BeautifulSoup(document_response.text, 'html.parser')
                assert document_soup
                field_name_body = document_soup.find('div', class_='field--name-body')
                assert field_name_body

                document_text = field_name_body.get_text()
                dpa_folder = self.path
                #check whether have the same title
                if document_hash in existed_docs:

                    document_folder = dpa_folder + '/' + 'News' + '/' + document_hash + ' -02'
                else:

                    document_folder = dpa_folder + '/' + 'News' + '/' + document_hash
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
                existed_docs.append(document_hash)

                #existed_docs.append(document_hash)#added

            pagination = self.update_pagination(pagination, page_soup=results_soup)

        return existed_docs

    def get_docs_Decisions(self, existing_docs=[], overwrite=False, to_print=True):
        existed_docs = []
        source = {
            "host": "https://www.dataprotection.ie",
            "start_path": "/en/dpc-guidance/law/decisions-made-under-data-protection-act-2018"
        }
        host = source['host']
        start_path = source['start_path']
        page_url = host + start_path
        page_source = self.get_source(page_url=page_url)
        if page_source is None:
            print("This url is not exist.")

        results_soup = BeautifulSoup(page_source.text, 'html.parser')
        assert results_soup


        field_name_body = results_soup.find('div', class_='field--name-body')
        assert field_name_body

        for accordion in field_name_body.find_all('div', class_='accordion'):
            year = accordion.find('h5', class_='mb-0').get_text()
            #print('Year: \t', year)

            collapse_show = accordion.find('div', class_='collapse')

            for document in collapse_show.find_all('a'):
                assert collapse_show
                time.sleep(5)
                document_title = document.get_text()
                #print('document_title: ', document_title)
                document_hash = hashlib.md5(document_title.encode()).hexdigest()
                print('document_hash: ', document_hash)
                date = document_title.split()[-2] + ' ' + document_title.split()[-1]
                default_day = '01st'
                #print('date: ', date)

                full_date = default_day + ' ' + date
                date_str = full_date.strip()
                regex = r"(\d\d)(st|nd|rd|th) (\w*) (\d\d\d\d)"
                matches = re.finditer(regex, date_str)
                matches = list(matches)
                if len(matches) == 0:
                    continue
                match = matches[0]
                groups = match.groups()
                date_suffix_group_num = 2
                date_str = date_str[:match.start(date_suffix_group_num)] + date_str[match.end(date_suffix_group_num):]
                tmp = datetime.datetime.strptime(date_str, '%d %B %Y')
                date = datetime.date(tmp.year, tmp.month, tmp.day)
                document_href = document.get('href')
                assert document_href
                document_link = host + document_href
                try:
                    document_response = requests.request('GET', document_link)
                    document_response.raise_for_status()
                except requests.exceptions.ConnectionError as error:
                    #if to_print:
                        #print(error)
                    pass

                if document_response is None:
                    continue

                dpa_folder = self.path
                document_folder = dpa_folder + '/' + 'Decisions' + '/' + document_hash
                try:
                    os.makedirs(document_folder)
                except FileExistsError:
                    pass

                document_soup = BeautifulSoup(document_response.text, 'html.parser')
                field_name_body_2 = document_soup.find('div', class_='field--name-body')
                time.sleep(3)
                two_files = field_name_body_2.find_all('a')
                short_href = two_files[0].get('href')
                short_document_link = host + short_href
                short_document_title = two_files[0].get_text()
                print('\t\tshort document link: ', short_document_link)
                print('\t\tshort document title: ', short_document_title)
                try:
                     short_file_response = requests.request('GET', short_document_link)
                     short_file_response.raise_for_status()
                except requests.exceptions.ConnectionError as error:
                    #if to_print():
                    #    print(error)
                    pass
                if short_file_response is None:
                    continue
                short_file_content = short_file_response.content
                with open(document_folder + '/' + self.language_code + '_Summary' + '.pdf', 'wb') as f:
                    f.write(short_file_content)
                with open(document_folder + '/' + self.language_code + '_Summary' + '.txt', 'w') as f:
                    short_document_text = PDFToTextService().text_from_pdf_path(document_folder + '/' + self.language_code + '_Summary' + '.pdf')
                    f.write(short_document_text)

                full_href = two_files[1].get('href')
                full_document_link = host + full_href
                full_document_title = two_files[1].get_text()
                print('\t\tfull document link: ', full_document_link)
                print('\t\tfull document title: ',  full_document_title)
                try:
                     full_file_response = requests.request('GET', full_document_link)
                     full_file_response.raise_for_status()
                except requests.exceptions.ConnectionError as error:
                    #if to_print():
                    #    print(error)
                    pass
                if full_file_response is None:
                    continue
                full_file_content = full_file_response.content
                with open(document_folder + '/' + self.language_code + '_Full' + '.pdf', 'wb') as f:
                    f.write(full_file_content)
                with open(document_folder + '/' + self.language_code + '_Full' + '.txt', 'w') as f:
                    full_document_text = PDFToTextService().text_from_pdf_path(document_folder + '/' + self.language_code + '_Full' + '.pdf')
                    f.write(full_document_text)

                with open(document_folder + '/' + 'metadata.json', 'w') as f:
                    metadata = {
                        'title': {
                            self.language_code: document_title
                        },
                        'md5': document_hash,
                        'releaseDate': date.strftime('%m/%Y') + " --format: MM/YYYY",
                        'url': short_document_link,
                        'full_url': full_document_link
                    }
                    json.dump(metadata, f, indent=5, sort_keys=True)
                existed_docs.append(document_hash)
            print('\n')


        return existed_docs

    def get_docs_Judgements(self, existing_docs=[], overwrite=False, to_print=True):
        # please add your webdriver path in side the ()
        driver = webdriver.Chrome('/Users/chen/Downloads/chromedriver')

        existed_docs = []
        source = {
            "host": "https://www.dataprotection.ie",
            "start_path": "/en/dpc-guidance/law/judgments"
        }
        host = source['host']
        start_path = source['start_path']
        page_url = host + start_path

        assert (page_url is not None)
        results_response = None

        results_response = requests.request('GET', page_url)

        results_response

        results_soup = BeautifulSoup(results_response.text, 'html.parser')
        assert results_soup
        year_list = []
        for accordion in results_soup.find_all('div', class_='accordion'):
            for card in accordion.find_all('div', class_='card'):
                card_header = card.find('div', class_='card-header')

                year = card_header.find('h5', class_='mb-0').get_text()
                #print(year)

                if year < "2018" or year in year_list:
                    break
                year_list.append(year)
                card_body = card.find('div', class_='card-body')
                for articles in card_body.find_all('a'):
                    document_title = articles.get_text()
                    if document_title == '':
                        continue

                    # get the date of the document
                    date = document_title.split()[-3] + ' ' + document_title.split()[-2] + ' ' + document_title.split()[
                        -1]
                    # check whether contains specific day
                    if date[0] == '-':
                        date = '01 ' + date[2:]
                    # check whether contains year in title
                    if str(year) not in document_title:
                        # set a default date
                        date = '25 May 2018'
                    date_str = date.strip()

                    tmp = datetime.datetime.strptime(date_str, '%d %B %Y')
                    date = datetime.date(tmp.year, tmp.month, tmp.day)
                    if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                        #print('ShouldRetainDocumentSpecification is false')
                        continue

                    print('\tdocument_title: ', document_title)
                    document_href = articles.get('href')
                    document_hash = hashlib.md5(document_title.encode()).hexdigest()
                    dpa_folder = self.path
                    document_folder = dpa_folder + '/' + 'Judgements' + '/' + document_hash
                    try:
                        os.makedirs(document_folder)
                    except FileExistsError:
                        pass

                    if document_href.endswith('.html'):
                        #print("\t This is a html type")
                        document_url = document_href
                        print('\tdocument_link: ', document_url)

                        driver.get(document_url)
                        document_text = driver.find_element_by_xpath('//*[@id="search"]/div[2]/div/div[2]').text

                        with open(document_folder + '/' + self.language_code + '.txt', 'w') as f:
                            f.write(document_text)

                    elif document_href.endswith('/pdf'):
                        #print("\t This is a .pdf/pdf file")
                        document_url = document_href
                        document_response = None
                        try:
                            document_response = requests.request('GET', document_url)
                            document_response.raise_for_status()
                        except requests.exceptions.ConnectionError as error:
                            pass
                        if document_response is None:
                            continue
                        document_soup = BeautifulSoup(document_response.text, 'html.parser')
                        assert document_soup
                        full_view = document_soup.find('div', class_='download-text logo-pdf file-name')
                        full_view_href = full_view.find('a').get('href')
                        host_url = 'https://www.courts.ie/'
                        document_url = host_url + full_view_href
                        print('\tdocument_link: ', document_url)
                        full_view_response = None
                        try:
                            full_view_response = requests.request('GET', document_url)
                            full_view_response.raise_for_status()
                        except requests.exceptions.ConnectionError as error:
                            pass
                        if full_view_response is None:
                            continue
                        document_text = full_view_response.content
                        with open(document_folder + '/' + self.language_code + '.pdf', 'wb') as f:
                            f.write(document_text)
                        with open(document_folder + '/' + self.language_code + '.txt', 'w') as f:
                            document_text = PDFToTextService().text_from_pdf_path(
                                document_folder + '/' + self.language_code + '.pdf')
                            f.write(document_text)

                    elif document_href.endswith('.pdf'):
                        #print("\tThis is a PDF file")
                        document_url = host + document_href
                        print('\tdocument_link: ', document_url)
                        document_response = None
                        try:
                            document_response = requests.request('GET', document_url)
                            document_response.raise_for_status()
                        except requests.exceptions.ConnectionError as error:
                            pass
                        if document_response is None:
                            continue
                        document_text = document_response.content
                        with open(document_folder + '/' + self.language_code + '.pdf', 'wb') as f:
                            f.write(document_text)
                        with open(document_folder + '/' + self.language_code + '.txt', 'w') as f:
                            document_text = PDFToTextService().text_from_pdf_path(
                                document_folder + '/' + self.language_code + '.pdf')
                            f.write(document_text)

                    else:
                        #print("\tthis is a txt format file.")
                        if document_href.startswith('https'):
                            document_url = document_href
                        else:
                            document_url = host + document_href
                        print('\tdocument_link: ', document_url)
                        document_response = None
                        try:
                            document_response = requests.request('GET', document_url)
                            document_response.raise_for_status()
                        except requests.exceptions.ConnectionError as error:
                            pass
                        if document_response is None:
                            continue
                        document_soup = BeautifulSoup(document_response.text, 'html.parser')
                        assert document_soup
                        field_name_body = document_soup.find('div', class_='field--name-body')
                        # assert field_name_body
                        if field_name_body is not None:
                            document_text = field_name_body.get_text()
                        else:
                            tab_Content = document_soup.find('div', class_='tabContent')
                            document_text = tab_Content.get_text()
                        with open(document_folder + '/' + self.language_code + '.txt', 'w') as f:
                            f.write(document_text)
                    print("\tDocument hash:\t", document_hash)

                    with open(document_folder + '/' + 'metadata.json', 'w') as f:
                        metadata = {
                            'title': {
                                self.language_code: document_title
                            },
                            'md5': document_hash,
                            'releaseDate': date.strftime('%d/%m/%Y') + "    (default date: 25/05/2018)",
                            'url': document_url
                        }
                        json.dump(metadata, f, indent=4, sort_keys=True)
                    existed_docs.append(document_hash)
                    print('\n')
        return existed_docs

    def get_docs_Blogs(self, existing_docs=[], overwrite=False, to_print=True):
        added_docs = []
        pagination = self.update_pagination_noStart()
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
            view_content = results_soup.find('div', class_='view-content')
            assert view_content

            # For https://www.dataprotection.ie/en/dpc-guidance/blogs, the articles are found under the
            # view_content class, each located at view-row. Thus we iterate through views-row to find data
            # for each article.

            # Iterate through view_content to get articles
            for li in view_content.find_all('div', recursive=False):
                time.sleep(5)
                article = li.find('article')
                assert article
                p_date = article.find('p', class_='date')
                assert p_date
                date_str = p_date.get_text().strip()
                regex = r"(\d\d)(st|nd|rd|th) (\w*) (\d\d\d\d)"

                matches = re.finditer(regex, date_str)
                matches = list(matches)
                if len(matches) == 0:
                    continue
                match = matches[0]
                groups = match.groups()
                date_suffix_group_num = 2
                date_str = date_str[:match.start(date_suffix_group_num)] + date_str[match.end(date_suffix_group_num):]
                tmp = datetime.datetime.strptime(date_str, '%d %B %Y')
                date = datetime.date(tmp.year, tmp.month, tmp.day)
                if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                    continue
                h2 = article.find('h2')
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
                host = "https://www.dataprotection.ie"
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
                field_name_body = document_soup.find('div', class_='field--name-body')
                assert field_name_body
                document_text = field_name_body.get_text()

                # Make sure that self.path is not the path of the most recent user who pushed to git
                dpa_folder = self.path

                # Set document folder as ireland/blogs/document_hash
                document_folder = dpa_folder + '/' + 'Blogs' + '/' + document_hash
                try:
                    os.makedirs(document_folder)
                except FileExistsError:
                    pass
                # Store files in ireland/blogs
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

            # Add link to the next page to pagination object
            pagination = self.update_pagination_noStart(pagination, page_soup=results_soup)

        return added_docs

    # Doesn't include financial accounts
    # This scraper method doesn't use update_pagination and update_pagination_noStart
    def get_docs_Publications(self, existing_docs=[], overwrite=False, to_print=True):
        added_docs = []

        page_url = "https://www.dataprotection.ie/en/dpc-guidance/publications"
        if to_print:
            print('Page:\t', page_url)
        page_source = self.get_source(page_url=page_url)
        if page_source is None:
            sys.exit("Couldn't obtain page_source from page_url")
        results_soup = BeautifulSoup(page_source.text, 'html.parser')
        assert results_soup

        # view-content section contains articles within
        view_content = results_soup.find('div', class_='view-content')
        assert view_content

        # TODO: Refactor code
        # For each article on this page
        for article in view_content.find_all('article', recursive=True):
            time.sleep(5)
            article = article
            assert article
            p_date = article.find('p', class_='date')
            assert p_date
            date_str = p_date.get_text().strip()
            regex = r"(\d\d)(st|nd|rd|th) (\w*) (\d\d\d\d)"

            matches = re.finditer(regex, date_str)
            matches = list(matches)
            if len(matches) == 0:
                continue
            match = matches[0]
            groups = match.groups()
            date_suffix_group_num = 2
            date_str = date_str[:match.start(date_suffix_group_num)] + date_str[match.end(date_suffix_group_num):]
            tmp = datetime.datetime.strptime(date_str, '%d %B %Y')
            date = datetime.date(tmp.year, tmp.month, tmp.day)
            if ShouldRetainDocumentSpecification().is_satisfied_by(date) is False:
                continue
            h2 = article.find('h2')
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
            host = "https://www.dataprotection.ie"
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

            # Create next page parse object -> visit pdf link from here
            document_soup = BeautifulSoup(document_response.text, 'html.parser')
            assert document_soup

            content = document_soup.find('div', class_='content')
            assert content
            pdf_article = content.find('div', class_='clearfix text-formatted field field--name-body field--type-text-with-summary field--label-hidden field__item')
            assert pdf_article
            pdf_link = pdf_article.find('a')
            assert pdf_link
            pdf_href = pdf_link.get('href')
            assert pdf_href

            # If the pdf_href contains the full link, then that is the pdf_url
            if "https://www.dataprotection.ie" in pdf_href:
                pdf_url = pdf_href
            # Otherwise, the href just has the extension to add on to the host link
            else:
                pdf_url = host + pdf_href
            print(pdf_url)

            # Now try to open the pdf_url
            if to_print:
                print("\tPDF Document:\t", document_hash)
            pdf_response = None
            try:
                pdf_response = requests.request('GET', pdf_url)
                pdf_response.raise_for_status()
            except requests.exceptions.HTTPError as error:
                if to_print:
                    print(error)
                pass
            if pdf_response is None:
                continue

            # Make sure that self.path is not the path of the most recent user who pushed to git
            dpa_folder = self.path

            # For now, store the pdf in the folder for the page that links to the pdf
            document_folder = dpa_folder + '/' + 'Publications' + '/' + document_hash

            try:
                os.makedirs(document_folder)
            except FileExistsError:
                pass
            # Write pdf_response contents to the pdf files in the folder
            with open(document_folder + '/' + self.language_code + '.pdf', 'wb') as f:
                f.write(pdf_response.content)
            # Include a .txt file with pdf contents
            with open(document_folder + '/' + self.language_code + '.txt', 'w') as f:
                full_document_text = PDFToTextService().text_from_pdf_path(
                    document_folder + '/' + self.language_code + '.pdf')
                f.write(full_document_text)

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

    # A big error message with this line: ConnectionRefusedError: [Errno 61] Connection refused,
    # probably means that there is an issue with href that causes the document url to be broken.

    # Doesn't visit any links that lead to external edpb.europa.eu or ec.europa.eu sites
    def get_docs_Guidances_v1(self, existing_docs=[], overwrite=False, to_print=True):
        added_docs = []
        page_url = "https://www.dataprotection.ie/en/dpc-guidance"
        if to_print:
            print('Page:\t', page_url)
        page_source = self.get_source(page_url=page_url)
        if page_source is None:
            sys.exit("Couldn't obtain page_source from page_url")
        results_soup = BeautifulSoup(page_source.text, 'html.parser')
        assert results_soup
        view_content = results_soup.find('div', class_='card')
        assert view_content

        # Iterate through ul and li to get the articles (note, set recursive=True here to examine everything past scope)
        for ul in view_content.find_all('ul', recursive=True):
            # This will iterate through ALL li's -> even the ones within the scope of another li
            # (gets the very last links of the guidance page)
            for li in ul.find_all('li', recursive=True):
                time.sleep(5)

                # If there are multiple href links, get the second one only (first tends to be junk)
                if (len(li.find_all('a')) == 2):
                    article = li.find_all('a')[1]
                else:
                    article = li.find('a')

                assert article

                # The article object already contains the link
                result_link = article
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

                # If 'href' is a link that goes to the external edpb or ec.europa site, skip it
                # Otherwise conditionally check if 'href' is a full link that starts with https://www.dataprotection.ie
                # If so, document_url = href, since the href is the full link and not just the extension
                if "https://edpb.europa.eu" in document_href:
                    continue
                if "ec.europa.eu" in document_href:
                    continue
                elif "https://www.dataprotection.ie" in document_href:
                    document_url = document_href
                else:
                    host = "https://www.dataprotection.ie"
                    document_url = host + document_href

                # Skip current iteration if forbidden url (right now, just have to match the exact url)
                # TODO: Provide way to check if link if forbidden in a non-hardcoded way
                if document_url == "https://www.dataprotection.ie/en/dpc-guidance/transfers-personal-data-ireland-uk-event-no-deal-brexit":
                    continue

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

                # Create the next page parse object -> download pdf from link it it exists
                document_soup = BeautifulSoup(document_response.text, 'html.parser')
                assert document_soup

                # Look for pdf links
                # Set potential_link to empty be default
                potential_link = []
                try:
                    content = document_soup.find('div', class_='content')
                    assert content
                    potential_link_area = content.find('div', class_='clearfix text-formatted field field--name-body field--type-text-with-summary field--label-hidden field__item')
                    assert potential_link_area
                    potential_link = potential_link_area.find_all('a', recursive=True)
                    assert potential_link
                    for a in potential_link:
                        pdf_href_test = a.get('href')
                        assert pdf_href_test
                except AssertionError:
                    pass
                else:
                    potential_link = potential_link_area.find_all('a', recursive=True)

                # If potential_link is not empty, iterate through its tag objects and look for pdf links
                pdf_counter = 1
                for a in potential_link:
                    pdf_href = a.get('href')
                    # Determine if the found link leads to a pdf
                    if isinstance(pdf_href, str):
                        if ".pdf" in pdf_href:
                            # If the pdf_href contains the full link, then that is the pdf_url
                            if "https://www.dataprotection.ie" in pdf_href:
                                pdf_url = pdf_href
                            # Otherwise, the href just has the extension to add on to the host link
                            else:
                                pdf_url = "https://www.dataprotection.ie" + pdf_href

                            # Broken links
                            if pdf_url == 'https://www.dataprotection.iehttps://uat.dataprotection.ie/sites/default/files/uploads/2020-12/Brexit%20FAQ_Dec20.pdf':
                                continue
                            if pdf_url == "https://www.dataprotection.ie/sites/default/files/uploads/2020-04/Guide%20for%20Individuals%20Working%20Remotely_0_1.pdf":
                                continue

                            # Now try to open the pdf_url
                            #if to_print:
                                # TODO: Put pdf document hash here
                                #print("\tPDF Document:\t", "place specific pdf doc hash here")

                            pdf_response = None
                            try:
                                pdf_response = requests.request('GET', pdf_url)
                                pdf_response.raise_for_status()
                            except requests.exceptions.HTTPError as error:
                                if to_print:
                                    print(error)
                                pass
                            # Except the other potential errors -> don't let it crash program
                            except:
                                pass

                            if pdf_response is None:
                                continue

                            # We have the pdf_response object -> now download its contents
                            dpa_folder = self.path
                            # For now, store the pdf in the folder for the page that links to the pdf
                            document_folder = dpa_folder + '/' + "Guidances" + '/' + document_hash

                            try:
                                os.makedirs(document_folder)
                            except FileExistsError:
                                pass
                            # Write pdf_response contents to the pdf files in the folder
                            with open(document_folder + '/' + self.language_code + str(pdf_counter) + '.pdf', 'wb') as f:
                                f.write(pdf_response.content)
                            # Include a .txt file with pdf contents
                            with open(document_folder + '/' + self.language_code + str(pdf_counter) + '.txt', 'w') as f:
                                full_document_text = PDFToTextService().text_from_pdf_path(
                                    document_folder + '/' + self.language_code + str(pdf_counter) + '.pdf')
                                f.write(full_document_text)

                            pdf_counter = pdf_counter + 1

                            added_docs.append(document_hash)
                        else:
                            pass
                    else:
                        pass

                # Download text from the page as usual
                field_name_body = document_soup.find('div', class_='field--name-body')
                assert field_name_body
                document_text = field_name_body.get_text()
                dpa_folder = self.path
                document_folder = dpa_folder + '/' "Guidances" + '/' + document_hash
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
                        # Can't use the "date" variable
                        'releaseDate': "Not available with current webpage",
                        'url': document_url
                    }
                    json.dump(metadata, f, indent=4, sort_keys=True)
                added_docs.append(document_hash)

        return added_docs
