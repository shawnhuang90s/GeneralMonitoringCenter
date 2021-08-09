# -*- coding:utf-8 -*-
from flask import request
from functools import wraps
from utils.login_tool import token_auth
from model.crris_model import AreaConfig, Permission


def get_area_info():
    """获取前端传来的区域ID"""
    params = request.get_json()
    area_id = params.get('id', 0)
    assert area_id, f'缺少必要的参数：区域ID'
    area_obj = AreaConfig.filter(AreaConfig.id == area_id).first()

    return area_obj


def viewable_permission(func):
    """查看权限验证装饰器"""
    @wraps(func)
    def inner(*args, **kwargs):
        # user_obj = token_auth()
        # if user_obj.isSuperuser:
        #     return func(request, *args, **kwargs)
        # area_obj = get_area_info()
        # permission_obj = Permission.filter(Permission.user == user_obj, Permission.area == area_obj,
        #                                    Permission.isViewable == 1).first()
        # assert permission_obj, f'您没有权限查看 "{area_obj.area}" 的配置信息, 请联系管理员'
        return func(*args, **kwargs)
    return inner


def operational_permission(func):
    """操作权限验证装饰器"""
    @wraps(func)
    def inner(*args, **kwargs):
        # user_obj = token_auth()
        # if user_obj.isSuperuser:
        #     return func(request, *args, **kwargs)
        # area_obj = get_area_info()
        # permission_obj = Permission.filter(Permission.user == user_obj, Permission.area == area_obj,
        #                                    Permission.isOperational == 1).first()
        # assert permission_obj, f'您没有权限操作 "{area_obj.area}" 的配置信息, 请联系管理员'
        return func(*args, **kwargs)
    return inner
