# -*- coding:utf-8 -*-
import peewee
from loguru import logger
from functools import wraps
from utils.log_tool import mysql_tool_log
from playhouse.pool import PooledMySQLDatabase

logger.add(mysql_tool_log,
           format="{time:%Y-%m-%d %H:%M:%S} | {module}.py func_name[{function}] line[{line}] | {level} | {message}",
           level='INFO', retention='7 days')


class DBConn:
    """数据库连接"""
    db = None
    table_list = []

    @classmethod
    def init(cls, **kwargs):
        """数据库初始化"""
        cls.db = PooledMySQLDatabase(**kwargs)

    @classmethod
    def celery_init(cls, **kwargs):
        cls.db = peewee.MySQLDatabase(**kwargs)

    @classmethod
    def execute_sql(cls, sql):
        return cls.db.execute_sql(sql).fetchall()

    @classmethod
    def create_tables(cls):
        cls.db.create_tables(cls.table_list)


def close_db_connect(func):
    """协程调用装饰器，关闭数据库连接"""
    @wraps(func)
    def wrapped(*args, **kwargs):
        resp = func(*args, **kwargs)
        if not DBConn.db.is_closed():
            DBConn.db.close()
        return resp
    return wrapped