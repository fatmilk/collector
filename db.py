#!/usr/bin/env python

from pony.orm import *

vkExchangeDB = Database()
class Public(vkExchangeDB.Entity):
    club_id = Required(str, unique=True)
    public_id = Required(str, unique=True)
    name = Required(str)
    category = Optional(str)
    size = Required(int)
    coverage = Optional(int)
    coverage_day = Optional(int)
    price = Required(int)
