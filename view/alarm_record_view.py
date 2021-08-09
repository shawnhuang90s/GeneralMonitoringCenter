# -*- coding:utf-8 -*-
import json
import base64
from peewee import fn
from flask import request
from loguru import logger
from datetime import datetime
from config import ServerConfig
from utils.xlsx_tool import XlsxTool
from utils.file_tool import UploadFile
from utils.redis_tool import RedisConn
from utils.log_tool import alarm_record_view_log
from utils.save_picture_tool import save_picture_data
from model.crris_model import AlarmScreenshot, AreaConfig

logger.add(alarm_record_view_log,
           format="{time:%Y-%m-%d %H:%M:%S} | {module}.py func_name[{function}] line[{line}] | {level} | {message}",
           level='INFO', retention='7 days')


def query_alarm_data(params):
    """
    搜索报警截图数据
    搜索时传参:
        {
            "page": 1,
            "size": 10,
            "cameraId": "",
            "alarmType": "",
            "startDate": "",
            "endDate": ""
        }
    导出时传参:
        {
            "cameraId": "",
            "alarmName": "",
            "keyword": "",
            "userTypeName": "",
            "startDate": "2021-06-01",
            "endDate": "2021-08-01",
            "idList": [1, 2, 3, 4, 5]  # 以 id_list 是否为空来判断用户是批量导出, 还是将搜索出的结果都导出来
        }
    """
    page = params.get('page', 0)
    size = params.get('size', 0)
    camera_id = params.get('cameraId', '')
    alarm_name = params.get('alarmType', '')
    start_date = params.get('startDate', '')
    end_date = params.get('endDate', '')
    id_list = params.get('idList', [])

    select = [AlarmScreenshot.id, AlarmScreenshot.cameraId, AlarmScreenshot.alarmType, AlarmScreenshot.alarmTime,
              AlarmScreenshot.saveTime, AlarmScreenshot.pictureUrl]
    limit_list = list()
    id_name_dict, name_id_dict = RedisConn.get_algo_dict()
    # id_list 为空, 则是搜索数据, 但单纯搜索数据有分页处理, 导出搜索数据时没有分页处理
    if not id_list:
        if camera_id != '':
            limit_list.append(AlarmScreenshot.cameraId == camera_id)
        if alarm_name:
            alarm_type = name_id_dict.get(alarm_name, 0)
            limit_list.append(AlarmScreenshot.alarmType == alarm_type)
        if start_date and end_date:
            limit_list.append(AlarmScreenshot.alarmTime.between(start_date, end_date))

        if limit_list:
            alarm_data = AlarmScreenshot.query(select=select, limit_list=limit_list).order_by(
                AlarmScreenshot.alarmTime.desc())
        else:
            alarm_data = AlarmScreenshot.query(select=select).order_by(AlarmScreenshot.alarmTime.desc())

        if page and size:
            alarm_data = alarm_data.paginate(page, size)
    # 只要 id_list 不为空, 说明就是批量选择, 搜索出这些数据导出即可
    else:
        alarm_data = AlarmScreenshot.select().where(AlarmScreenshot.id << id_list).order_by(
            AlarmScreenshot.alarmTime.desc())

    res = list()
    area_data = AreaConfig.select()
    if alarm_data:
        for alarm_obj in alarm_data:
            # 每个点位关联的所有区域名
            area_names = ''
            camera_id = alarm_obj.cameraId
            if camera_id:
                for area in area_data:
                    camera_list = json.loads(area.cameraList) if area.cameraList else []
                    if camera_id in camera_list:
                        area_names += f'{area.areaName}, '
            if area_names:
                area_names = area_names[:-2]
            # 每个报警类型ID关联的报警类型名称
            alarm_name = ''
            if alarm_obj.alarmType:
                alarm_name = id_name_dict.get(alarm_obj.alarmType, '')
            obj_dict = {
                'id': alarm_obj.id,
                'cameraId': alarm_obj.cameraId,
                'name': area_names,
                'alarmType': alarm_name,
                'alarmDate': alarm_obj.alarmTime.strftime('%Y-%m-%d %H:%M:%S') if alarm_obj.alarmTime else '',
                'dataDate': alarm_obj.saveTime.strftime('%Y-%m-%d %H:%M:%S') if alarm_obj.saveTime else '',
                # TODO:看贝叶斯返回的这个是可以访问的 URL，还是要我们这边存图片
                'pictureUrl': f'{ServerConfig.root_host}{alarm_obj.pictureUrl}' if alarm_obj.pictureUrl else '',
            }
            res.append(obj_dict)

    page_vo = AlarmScreenshot.get_table_page_vo(page, size, limits=limit_list)

    return res, page_vo


def query_alarm_record():
    """查询报警截图数据"""
    params = request.get_json()
    res, page_vo = query_alarm_data(params)

    return {'alarmData': res, 'pageVo': page_vo}


def export_alarm_record():
    """导出报警截图数据"""
    params = request.get_json()
    query_data = query_alarm_data(params)[0]
    data_list = list()
    for obj_dict in query_data:
        obj_list = [obj_dict[k] for k in obj_dict]
        data_list.append(obj_list)
    xlsx = XlsxTool(['序号', '点位ID', '关联区域', '异常类型', '报警时间', '数据获取时间', '报警截图'])
    current_time = datetime.now().strftime('%Y-%m-%d')
    url = xlsx.write_xlsx(data_list, f'报警截图数据_{current_time}')

    return {'url': url}


def get_alarm_data():
    """推理平台调用这个接口使用 callback 方式将截图数据传过来"""
    try:
        logger.info('======== 开始处理推理平台推送的数据 ========')
        params = request.get_json()
        # params = json.loads(params)
        task_id = params.get('taskId', -100)
        camera_id = params.get('cameraId', -100)
        current_day_str = datetime.now().strftime('%Y-%m-%d')
        current_day = datetime.strptime(current_day_str, '%Y-%m-%d')
        save_strp_time = datetime.now()
        timestamp = params.get('timestamp', 0)
        if timestamp:
            localtime = datetime.fromtimestamp(timestamp)
            save_str_time = localtime.strftime("%Y-%m-%d %H:%M:%S")
            save_strp_time = datetime.strptime(save_str_time, '%Y-%m-%d %H:%M:%S')
        # 报警截图保存
        alarm_name = params.get('alarmPicName', '')
        alarm_data = params.get('alarmPicData', '')
        picture_path = ''
        if alarm_name and alarm_data:
            picture_path = save_picture_data(alarm_data, current_day_str, 'alarm_picture', alarm_name)
        alarm_type = task_id
        if picture_path:
            alarm_obj = AlarmScreenshot()
            alarm_obj.cameraId = camera_id
            alarm_obj.alarmTime = save_strp_time
            alarm_obj.createdDay = current_day
            alarm_obj.alarmType = alarm_type
            alarm_obj.pictureUrl = picture_path
            alarm_obj.save()
    except Exception as e:
        logger.error(f'保存报警截图数据失败：{e}')

    return {'msg': '报警截图保存成功'}


def get_alarm_types():
    """获取所有的报警类型名称"""
    select = [fn.DISTINCT(AlarmScreenshot.alarmType)]
    all_alarm_types = AlarmScreenshot.query(select=select)
    # 统计7天内所有的报警截图类型
    alarm_type_list = [i.alarmType for i in all_alarm_types]
    alarm_types = [RedisConn.get_algo_dict()[0].get(i, '') for i in alarm_type_list]

    return alarm_types
