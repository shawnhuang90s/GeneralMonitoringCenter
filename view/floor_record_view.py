# -*- coding:utf-8 -*-
from flask import request
from loguru import logger
from datetime import datetime
from model.crris_model import FloorPersonStatistics


def get_floor_person_data():
    """获取贝叶斯推送的楼层人数记录数据"""
    try:
        logger.info('======== 开始处理贝叶斯推送的楼层人数记录数据 ========')
        params = request.get_json()
        # TODO:注意：配置页面的楼层名称必须与贝叶斯的楼层名称保持一致, 不然无法找到对应数据
        floor_name = params.get('floorName', '')  # 楼层名称
        floor_num = params.get('floorNum', '')  # 楼层名对应第几层
        person_num = params.get('personNum', 0)  # 楼层人数
        record_time = params.get('recordTime', '')  # 记录时间
        current_day_str = datetime.now().strftime('%Y-%m-%d')
        current_day = datetime.strptime(current_day_str, '%Y-%m-%d')
        if floor_name:
            floor_obj = FloorPersonStatistics()
            floor_obj.floorName = floor_name
            floor_obj.floorNum = floor_num
            floor_obj.personNum = person_num
            floor_obj.recordTime = record_time
            floor_obj.createdDay = current_day
            floor_obj.save()
    except Exception as e:
        logger.error(f'保存楼层人数数据失败：{e}')

    return {'msg': '楼层人数数据保存成功'}
