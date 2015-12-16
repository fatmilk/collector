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
from db import vkExchangeDB, Public

PAGELOAD_TIMEOUT = 10
USER_AGENT = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_4) AppleWebKit/537.36 ' +
    '(KHTML, like Gecko) Chrome/29.0.1547.57 Safari/537.36'
)


def get_exchange_page(driver):
    url = 'https://sociate.ru/spots/view/?ordering=users_asc&provider=vkontakte&blogger=all&min_age=0&min_geo=0'

    driver.get(url)
    # Scroll page to the end doesn't update page for PhantomJS driver (works for Firefox)
    #selenium.webdriver.common.action_chains.ActionChains(driver).send_keys(Keys.END).perform()
    
    reached_the_end = False
    current_len = 0
    updated_len = 1
    while updated_len != current_len:
        current_len = updated_len
        try:
            logging.getLogger("selenium").setLevel(logging.CRITICAL)
            WebDriverWait(driver, PAGELOAD_TIMEOUT).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "loading-more-w"))
            )
            loadmore_elem = driver.find_element_by_class_name("loading-more-w")
            time.sleep(10)
        except (selenium.common.exceptions.TimeoutException, \
            selenium.common.exceptions.NoSuchElementException):
            logging.debug('Reach the end of exchange list')
            reached_the_end = True
            break
        finally:
            logging.getLogger("selenium").setLevel(logging.WARNING)

        loadmore_elem.click()
        updated_len = len(driver.page_source)
        logging.debug('Updated page length: {}'.format(updated_len))

    
    assert(updated_len == current_len)
    return driver.page_source, reached_the_end


def parse_exchange_page(page):
    data = lxml.html.document_fromstring(page)
    public_names = data.xpath('//a[@class="exchange_ad_post_stats"]')
    
    def text2int(text):
        try:
            return int(text.replace(' ', ''))
        except:
            return 0
        
    last_size = 0
    were_new = False
    with db_session:
        for public_name in public_names:
            club_id = re.search('stats-(\d+)*', public_name.attrib['onclick']).group(1)
            public = Public.get(club_id=club_id)
            if public == None:
                cur_path = public_name.getparent().getnext()
                public_id = cur_path.attrib['href'].lstrip('/')
                name = cur_path.text if cur_path.text else 'Noname'
                cur_path = cur_path.getnext().getnext()
                category = cur_path.text
                cur_path = cur_path.getparent().getnext()
                size = text2int(cur_path.xpath('b')[0].text_content())
                cur_path = cur_path.getnext()
                coverage2 = cur_path.xpath('b')[0].text_content()
                coverage, coverage_day = map(text2int, coverage2.split('/'))
                cur_path = cur_path.getnext()
                price = text2int(cur_path.xpath('b')[0].text_content())

                try:
                    public = Public(club_id=club_id, public_id=public_id, name=name, \
                                    category=category, size=size, coverage=coverage, \
                                    coverage_day=coverage_day, price=price)
                except Exception as e:
                    logging.error('public_id: {}, name: {}, size: {}, price: {}'.\
                                  format(public_id, name, size, price))
                    raise e

                were_new = True
            
            last_size = public.size

    return last_size, were_new
    

def collect_exchange(driver):
    page, reached_the_end = get_exchange_page(driver)
    #were_new = parse_exchange_page(page)
    #logging.debug('Were new: {}'.format(were_new, from_size))


def main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.getLogger("selenium").setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(description="VK exchange collector")
    parser.add_argument("--dbfile", type=str, default='vkexch.sqlite', help="Path to sqlite DB file")
    args = parser.parse_args()

    #vkExchangeDB.bind('sqlite', args.dbfile, create_db=True)
    #vkExchangeDB.generate_mapping(create_tables=True)

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
