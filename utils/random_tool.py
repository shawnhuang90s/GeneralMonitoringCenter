# -*- coding:utf-8 -*-
import string
import random
import datetime


def get_random_string(length=24, random_string=string.ascii_uppercase + string.digits + string.ascii_lowercase):
    return ''.join([random.choice(random_string) for _ in range(length)])


def time_random_string(length=9, random_string=string.ascii_uppercase + string.ascii_lowercase, index='0'):
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + \
           ''.join([random.choice(random_string) for _ in range(length)]) + index
