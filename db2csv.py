#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import codecs

from pony.orm import db_session, select
from db import exchangeDB, Public

def main():
    parser = argparse.ArgumentParser(description="Exchange DB converter")
    parser.add_argument("--dbfile", type=str, default='vkexch.sqlite', help="Path to sqlite DB file")
    parser.add_argument("--csvfile", type=str, default='vkexch.csv', help="Path to csv file")
    args = parser.parse_args()

    exchangeDB.bind('sqlite', args.dbfile, create_db=True)
    exchangeDB.generate_mapping(create_tables=True)

    def str2(s):
        return s if s else 'None'

    with db_session, codecs.open(args.csvfile, 'w', encoding='utf-8', errors='replace') as csv_file:
        for public in select(public for public in Public):
            csv_file.write('\t'.join([str(public.club_id), str(public.public_id), \
                                      str(public.size), str(public.price), str(public.coverage), \
                                      str(public.coverage_day), str2(public.name), str2(public.category)]))
            csv_file.write('\n')

if __name__ == '__main__':
    main()
