# -*- coding:utf-8 -*-
import json
import requests
from flask import request
from loguru import logger
from config import ServerConfig
from utils.log_tool import interface_tool_log

logger.add(interface_tool_log,
           format="{time:%Y-%m-%d %H:%M:%S} | {module}.py func_name[{function}] line[{line}] | {level} | {message}",
           level='INFO', retention='7 days')
HEADERS = {'Content-Type': 'application/json'}
SERVER_URL = ServerConfig.server_url


def get_token():
    """获取推理平台登录后的 Token 信息"""
    token = None
    try:
        login_url = f'{SERVER_URL}api/user/login'
        data = {'username': 'admin', 'password': 'admin'}
        res = requests.post(login_url, data=json.dumps(data), headers=HEADERS).json()
        if isinstance(res, dict):
            if res['data'].get('errorMsg', ''):
                logger.error(f"调用接口获取 Token 信息时返回结果有误: {res['data'].get('errorMsg', '')}")
                return token
            token = res['data']['cr']
    except Exception as e:
        logger.error(f'获取推理平台登录后的 Token 信息失败：{e}')

    return token


def call_interface_data(path, method='GET', data=None):
    """
    调用推理平台接口获取数据
    :param path: 请求的相对路径
    :param method: 请求方式
    :param data: POST 请求传参
    :return: 获取的结果
    """
    res = dict()
    try:
        token = get_token()
        cookies_obj = requests.cookies.RequestsCookieJar()
        cookies_obj.set('crToken', token)
        url = f'{SERVER_URL}{path}'

        if method == 'GET':
            res = requests.get(url, cookies=cookies_obj).json().get('data')
        elif method == 'POST':
            res = requests.post(url, cookies=cookies_obj, data=data, headers=HEADERS).json().get('data')
    except Exception as e:
        logger.error(f'调用推理平台接口获取数据失败：{e}')
        res['error_msg'] = f'调用推理平台接口获取数据失败：{e}'

    return res


def get_crip_data(path, method='GET', data_dict=None, accessKey=None):
    """调用 API 接口获取推理平台数据"""
    normal_headers = {'Content-Type': 'application/json'}
    get_key_headers = {'crKey': accessKey}
    post_key_headers = {'Content-Type': 'application/json', 'crKey': accessKey}
    url = f'{SERVER_URL}{path}'
    res = {}
    if method == 'GET':
        if accessKey:
            res = requests.get(url, headers=get_key_headers)
        else:
            res = requests.get(url)
    elif method == 'POST':
        if accessKey:
            res = requests.post(url, data=json.dumps(data_dict), headers=post_key_headers)
        else:  # 授权申请时没有 accessKey, 因此也不需要传
            res = requests.post(url, data=json.dumps(data_dict), headers=normal_headers)
    assert res.status_code == 200, '服务出错, 请联系管理员'
    logger.info(f'调用推理平台接口：{url} 的返回结果：{res.status_code} - {res.json()}')
    data_info = res.json().get('data', {})
    if data_info:
        if data_info.get('errorCode', 0) and data_info.get('errorMsg', ''):
            return {'errorMsg': data_info['errorMsg']}

    return data_info


def get_latest_access_key(access_key, response):
    """获取最新的 accessKey"""
    # 判断 accessKey 是否还有效, 如果无效再调用接口获取最新的 accessKey
    if response.get('errorMsg', '') and 'access key' in response['errorMsg']:
        from utils.redis_tool import RedisConn
        app_id = RedisConn.get_app_id()
        app_secret = RedisConn.get_app_secret()
        path = 'api/openapi/authenticate'
        data = {'appId': app_id, 'appSecret': app_secret}
        res = get_crip_data(path, method='POST', data_dict=data)
        # 申请成功则返回 accessKey, 保存下来
        if res.get('accessKey', ''):
            RedisConn.redis_db.hmset(ServerConfig.access_name, {ServerConfig.access_key: res['accessKey']})
            access_key = res['accessKey']

    return access_key


def get_bayes_data():
    """
    从贝叶斯获取人脸Pad、人流监控设备在线离线数量及当前楼层入驻企业数
    allStatusCount 表示整栋楼的数据
    DeviceStatusCount = {
        'allStatusCount': {'faceOnline': 0, 'faceOffline': 0, 'flowOffline': 0, 'flowOnline': 0, 'companies': 0},
        '楼层1': {'faceOnline': 0, 'faceOffline': 0, 'flowOffline': 0, 'flowOnline': 0, 'companies': 0},
        '楼层2': {'faceOnline': 0, 'faceOffline': 0, 'flowOffline': 0, 'flowOnline': 0, 'companies': 0},
        '楼层3': {'faceOnline': 0, 'faceOffline': 0, 'flowOffline': 0, 'flowOnline': 0, 'companies': 0},
        ......
    }
    """
    try:
        params = request.get_json()
        device_status_dict = params.get('DeviceStatusCount', {})
        if not device_status_dict:
            logger.error(f'从贝叶斯获取人脸Pad和人流监控设备在线离线数量失败：{params}')
        from utils.redis_tool import RedisConn
        RedisConn.set_face_flow_companies(device_status_dict)
    except Exception as e:
        logger.error(f'获取人脸Pad设备状态失败：{e}')

    return



