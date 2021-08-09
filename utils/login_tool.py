# -*- coding:utf-8 -*-
from loguru import logger
from functools import wraps
from model.crris_model import User
from flask import g, request, abort
from utils.log_tool import login_tool_log
from utils.cookie_tool import CookieSession

logger.add(login_tool_log,
           format="{time:%Y-%m-%d %H:%M:%S} | {module}.py func_name[{function}] line[{line}] | {level} | {message}",
           level='INFO', retention='7 days')


def token_auth():
    """Token 验证"""
    # TODO
    token = request.cookies.get(CookieSession.token_key, '')
    # token = '5rcJiI0RsYxVVem4xwjICwzq'
    # assert token, 'Token 不能为空'
    if not token:
        abort(401)
    logger.info(f'当前用户的 Token 信息：{token}')
    user_name = CookieSession.get_user_by_token(token)
    assert user_name, '暂无用户信息, 请联系管理员'
    user_obj = User.filter(User.username == user_name).first()
    return user_obj


def login_require():
    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            # user_obj = token_auth()
            # g.user = user_obj
            resp = func(*args, **kwargs)
            return resp
        return wrapped
    return decorator


def set_token_user(username):
    """获取 Token, 并将 Token 与 username 的对应关系存到 Redis 中"""
    token = False
    # 对于 Token 和要保存的 Redis 信息, 多尝试几次
    for i in range(5):
        token = CookieSession.set_user_token(username)
        if token:
            break
    assert token, '将 Token 和当前用户的对应关系保存到 Redis 失败'

    return token
