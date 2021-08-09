# -*- coding:utf-8 -*-
from flask import g
from loguru import logger
from utils.redis_tool import RedisConn
from utils.log_tool import cookie_tool_log
from utils.random_tool import get_random_string

logger.add(cookie_tool_log,
           format="{time:%Y-%m-%d %H:%M:%S} | {module}.py func_name[{function}] line[{line}] | {level} | {message}",
           level='INFO', retention='7 days')


class CookieSession:
    user_key = None
    token_key = None

    @classmethod
    def init(cls, user_key, token_key):
        cls.user_key = user_key
        cls.token_key = token_key

    @staticmethod
    def generate_token():
        """生成 Token"""
        return get_random_string()

    @classmethod
    def check_user_login(cls, user_name):
        if RedisConn.redis_db.hget(cls.user_key, user_name) is None:
            return False
        return True

    @classmethod
    def remove_old_token(cls, user_list):
        old_token = RedisConn.redis_db.hmget(cls.user_key, *user_list)
        old_token = list(map(lambda x: x.decode('utf8') if x is not None else '', old_token))
        logger.info(f'用户信息：{user_list}，Cookies 中移除的 Token 信息：{old_token}')
        if old_token is not None:
            RedisConn.redis_db.hdel(cls.user_key, *user_list)
            RedisConn.redis_db.hdel(cls.token_key, *old_token)

    @classmethod
    def get_user_by_token(cls, token):
        """通过token获取用户信息"""
        user_name = RedisConn.redis_db.hget(cls.token_key, token)
        if not user_name:
            return None
        return user_name.decode('utf-8')

    @classmethod
    def set_user_token(cls, user_name):
        try:
            token = cls.generate_token()
            logger.info(f'保存用户[ID:{user_name}]的 Token[{token}] 到 Redis 中')
            if RedisConn.redis_db.hget(cls.token_key, token) is None:
                g.set_cookies = token
                RedisConn.redis_db.hmset(cls.user_key, {user_name: token})
                RedisConn.redis_db.hmset(cls.token_key, {token: user_name})
                return token
            else:
                return ''
        except Exception as e:
            logger.error(f'保存用户[ID:{user_name}]的 Token 到 Redis 中失败：{e}')
            return ''
