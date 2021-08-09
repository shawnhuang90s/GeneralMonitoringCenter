# -*- coding:utf-8 -*-
import functools
from flask import Blueprint


class CrBlueprint(Blueprint):
    def route(self, rule, **options):
        obj = super()
        def decorator(f):
            @functools.wraps(f)
            def wrapped(*args, **kwargs):
                resp = f(*args, **kwargs)
                res = {
                    'data': resp,
                    'requestInfo': {
                        'flag': True
                    }
                }
                return res
            obj.route(rule, **options)(wrapped)
            return wrapped
        return decorator
