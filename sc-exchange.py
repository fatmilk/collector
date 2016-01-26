#!/usr/bin/env python
# -*- coding: utf-8 -*-

import selenium
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


import sys
import time
import json
import logging
import lxml.html
import argparse
import re

from pony.orm import db_session
from db import exchangeDB, Public

PAGELOAD_TIMEOUT = 10
USER_AGENT = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_4) AppleWebKit/537.36 ' +
    '(KHTML, like Gecko) Chrome/29.0.1547.57 Safari/537.36'
)
MAX_LOAD_MORE_ITERS = 20

def get_filtered_exchange_page(driver, from_size):
    url = 'https://sociate.ru/spots/view/?ordering=users_asc&provider=vkontakte&min_users={}'.format(from_size)

    driver.get(url)
    # Scroll page to the end doesn't update page for PhantomJS driver (works for Firefox)
    #selenium.webdriver.common.action_chains.ActionChains(driver).send_keys(Keys.END).perform()
    
    current_len = 0
    updated_len = 1
    num_iters = 0
    while updated_len != current_len and num_iters < MAX_LOAD_MORE_ITERS:
        current_len = updated_len
        num_iters += 1
        try:
            logging.getLogger("selenium").setLevel(logging.CRITICAL)
            WebDriverWait(driver, PAGELOAD_TIMEOUT).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "loading-more-w"))
            )
            loadmore_elem = driver.find_element_by_class_name("loading-more-w")
            time.sleep(10)
        except (selenium.common.exceptions.TimeoutException, \
            selenium.common.exceptions.NoSuchElementException):
            logging.debug('Reached the end of exchange list')
            break
        finally:
            logging.getLogger("selenium").setLevel(logging.WARNING)

        loadmore_elem.click()
        updated_len = len(driver.page_source)
        logging.debug('Updated page length: {}'.format(updated_len))

    
    return driver.page_source


def parse_exchange_page(page):
    logging.debug('Parsing exchange page')

    data = lxml.html.document_fromstring(page)
    rows = data.xpath('//div[contains(@class, "row main-row-w")]')
    
    last_size = 0
    were_new = False
    with db_session:
        for row in rows:
            club = row.getchildren()[0].xpath('.//a')[0]
            club_id = re.search('club(\d+)*', club.attrib['href']).group(1)
            public = Public.get(club_id=club_id)
            if public == None:
                name = club.text_content().strip()
                if not name: name = 'Noname'
                price = int(re.sub("[^0-9]", "",
                                   row.xpath('.//span[contains(@class, "js_placement_price")]')[0].text_content()))
                size, coverage = map(lambda x: int(re.sub("[^0-9]", "", x.text_content())), row.xpath('.//span[@class="num"]'))

                try:
                    public = Public(club_id=club_id, name=name, \
                                    size=size, coverage=coverage, \
                                    price=price)
                except Exception as e:
                    logging.error('club_id: {}, name: {}, size: {}, price: {}'.\
                                  format(club_id, name, size, price))
                    raise e

                were_new = True
            
            last_size = public.size

    return last_size, were_new
    

def collect_exchange(driver):
    from_size = 0
    reached_the_end = False
    while not reached_the_end:
        page = get_filtered_exchange_page(driver, from_size)
        last_size, were_new = parse_exchange_page(page)
        reached_the_end = (last_size == from_size)
        from_size = last_size
        logging.debug('Were new: {}, last_size: {}'.format(were_new, last_size))


def main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.getLogger("selenium").setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(description="Sociate exchange collector")
    parser.add_argument("--dbfile", type=str, default='scexch.sqlite', help="Path to sqlite DB file")
    args = parser.parse_args()

    exchangeDB.bind('sqlite', args.dbfile, create_db=True)
    exchangeDB.generate_mapping(create_tables=True)

    #driver = selenium.webdriver.Firefox()
    #driver = selenium.webdriver.PhantomJS()
    dcap = dict(DesiredCapabilities.PHANTOMJS)
    dcap["phantomjs.page.settings.userAgent"] = USER_AGENT
    driver = selenium.webdriver.PhantomJS(desired_capabilities=dcap)

    logging.info('Collecting Sociate exchange info...')
    collect_exchange(driver)
    logging.info('Exchange collected')

    driver.close()


if __name__ == '__main__':
    main()
