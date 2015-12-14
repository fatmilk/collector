#!/usr/bin/env python
# -*- coding: utf-8 -*-

import selenium
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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


def vk_auth(driver, username, password):

    email_elem = driver.find_element_by_id("quick_email")
    pass_elem = driver.find_element_by_id("quick_pass")
    email_elem.send_keys(username)
    pass_elem.send_keys(password, Keys.RETURN)

    logging.debug(driver.execute_script("return navigator.userAgent"))

    WebDriverWait(driver, PAGELOAD_TIMEOUT).until(
        EC.presence_of_element_located((By.ID, "authcheck_code"))
    )

    confirm_elem = driver.find_element_by_id('authcheck_code')

    print("Enter confirmation code: ")
    confirm_code = sys.stdin.readline()
    confirm_elem.send_keys(confirm_code, Keys.RETURN)
    WebDriverWait(driver, PAGELOAD_TIMEOUT).until(
        EC.presence_of_element_located((By.ID, 'main_feed'))
    )


def get_filtered_exchange_page(driver, from_size):
    url = 'https://vk.com/exchange?act=community_search&sort=size&r=1&size={}'.format(from_size)

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
                EC.visibility_of_element_located((By.XPATH, "//tr[@id='exchange_more_results']/td/a"))
            )
            showmore_btn = driver.find_element_by_xpath("//tr[@id='exchange_more_results']/td/a")
        except (selenium.common.exceptions.TimeoutException, \
            selenium.common.exceptions.NoSuchElementException):
            logging.debug('Reach the end of exchange list')
            reached_the_end = True
            break
        finally:
            logging.getLogger("selenium").setLevel(logging.WARNING)

        showmore_btn.click()
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
                name = cur_path.text if public_name.text else 'Noname'
                cur_path = cur_path.getnext().getnext()
                category = cur_path.text
                cur_path = cur_path.getparent().getnext()
                size = text2int(cur_path.xpath('b')[0].text_content())
                cur_path = cur_path.getnext()
                coverage2 = cur_path.xpath('b')[0].text_content()
                coverage, coverage_day = map(text2int, coverage2.split('/'))
                cur_path = cur_path.getnext()
                price = text2int(cur_path.xpath('b')[0].itertext())

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
    from_size = 0
    reached_the_end = False
    while not reached_the_end:
        page, reached_the_end = get_filtered_exchange_page(driver, from_size)
        from_size, were_new = parse_exchange_page(page)
        logging.debug('Were new: {}, from_size: {}'.format(were_new, from_size))


def main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.getLogger("selenium").setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(description="VK exchange collector")
    parser.add_argument("--dbfile", type=str, default='vkexch.sqlite', help="Path to sqlite DB file")
    parser.add_argument("--cksfile", type=str, default='vkcookies.json', help="Path to cookies file")
    parser.add_argument("--authfile", type=str, default='.vkauth', help="Path to cookies file")
    args = parser.parse_args()

    vkExchangeDB.bind('sqlite', args.dbfile, create_db=True)
    vkExchangeDB.generate_mapping(create_tables=True)

    #driver = selenium.webdriver.Firefox()
    driver = selenium.webdriver.PhantomJS()

    # We have to navigate to VK page before setting cookies
    # (PhantomJS' feature, see https://github.com/detro/ghostdriver/issues/178)
    driver.get("https://vk.com")

    try:
        cookies = json.load(open(args.cksfile, "r"))
        for cookie in cookies:
            driver.add_cookie(cookie)
    except:
        logging.info('Autorization...')
        vk_auth_info = json.load(open(args.authfile))
        vk_auth(driver, vk_auth_info['username'], vk_auth_info['password'])
        logging.info('Autorization passed')
        json.dump(driver.get_cookies(), open(args.cksfile, 'w'))

    logging.info('Collecting VK exchange info...')
    collect_exchange(driver)
    logging.info('Exchange collected')

    driver.close()


if __name__ == '__main__':
    main()
