#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from pony.orm import db_session, select
from db import vkExchangeDB, Public

def main():
    parser = argparse.ArgumentParser(description="VK exchange collector")
    parser.add_argument("--dbfile", type=str, default='vkexch.sqlite', help="Path to sqlite DB file")
    parser.add_argument("--csvfile", type=str, default='vkexch.csv', help="Path to csv file")
    args = parser.parse_args()


    vkExchangeDB.bind('sqlite', args.dbfile, create_db=True)
    vkExchangeDB.generate_mapping(create_tables=True)

    import codecs
    with db_session, codecs.open(args.csvfile, 'w', encoding='cp1251', errors='replace') as csv_file:
        for public in select(public for public in Public):
            csv_file.write('\t'.join([public.club_id, public.public_id, \
                                      str(public.size), str(public.price), str(public.coverage), \
                                      str(public.coverage_day), public.name, public.category]))
            csv_file.write('\n')

if __name__ == '__main__':
    main()
