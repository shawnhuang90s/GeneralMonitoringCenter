# -*- coding:utf-8 -*-
import os
from loguru import logger
from flask import request
from config import ServerConfig
from utils.file_tool import UploadFile
from utils.redis_tool import RedisConn
from utils.login_tool import token_auth
from utils.interface_tool import get_crip_data
from utils.log_tool import system_config_view_log

logger.add(system_config_view_log,
           format="{time:%Y-%m-%d %H:%M:%S} | {module}.py func_name[{function}] line[{line}] | {level} | {message}",
           level='INFO', retention='7 days')


def get_system_name():
    """获取系统名称"""
    name = RedisConn.get_system_name()
    res = {'name': name}

    return res


def set_system_name():
    """设置系统名称"""
    # user_obj = token_auth()
    # assert user_obj.isSuperuser == 1, '您没有权限执行此操作, 请联系管理员'
    params = request.get_json()
    name = params.get('name', '')
    assert name, '所传系统名称为空'
    name = "".join(name.split(" "))  # 去除所有的空格
    RedisConn.set_system_name(name)

    res = {'msg': '系统名称设置成功'}

    return res


def get_logo():
    """获取系统 logo"""
    res = {'url': '', 'name': ''}
    relative_logo_path = f'picture/'
    exists_logo_path = f'{ServerConfig.root_path}{relative_logo_path}'
    if os.path.exists(exists_logo_path):
        logo_file_name = UploadFile.get_file_name(exists_logo_path, 'logo')  # logo&cat2.jpg
        res['name'] = logo_file_name.split('&')[1]
        res['url'] = f'{ServerConfig.root_host}{relative_logo_path}{logo_file_name}'
    # res['url'] = 'https://cdn3-banquan.ituchong.com/weili/l/920203348883800193.jpeg'
    # res['name'] = '920203348883800193.jpeg'

    return res


def get_access_info():
    """获取授权申请相关参数"""
    params = request.get_json()
    app_id = params.get('appId', '')
    app_secret = params.get('appSecret', '')
    assert app_id and app_secret, '请确保两个参数：appId、appSecret 都不为空'

    return app_id, app_secret


def save_access():
    """保存 AccessKey 信息"""
    # user_obj = token_auth()
    # assert user_obj.isSuperuser == 1, '您没有权限执行此操作, 请联系管理员'
    app_id, app_secret = get_access_info()
    RedisConn.redis_db.hmset(ServerConfig.access_name, {ServerConfig.app_id: app_id})
    RedisConn.redis_db.hmset(ServerConfig.access_name, {ServerConfig.app_secret: app_secret})

    return {'msg': '设置成功'}


def apply_access():
    """向推理平台申请一个 appId 和 appSecret, 即应用授权申请时不需要传 accessKey"""
    # user_obj = token_auth()
    # assert user_obj.isSuperuser == 1, '您没有权限执行此操作, 请联系管理员'
    app_id, app_secret = get_access_info()
    path = 'api/openapi/authenticate'
    data = {'appId': app_id, 'appSecret': app_secret}
    res = get_crip_data(path, method='POST', data_dict=data)
    # 申请成功则返回 accessKey, 保存下来
    if res.get('accessKey', ''):
        RedisConn.redis_db.hmset(ServerConfig.access_name, {ServerConfig.access_key: res['accessKey']})
    else:
        return {
            'errorMsg': '应用授权失败：未返回 accessKey'
        }

    return {'msg': '授权成功'}
