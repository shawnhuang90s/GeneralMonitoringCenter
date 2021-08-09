# -*- coding:utf-8 -*-
from peewee import fn
from flask import request
from loguru import logger
from datetime import datetime
from config import ServerConfig
from utils.xlsx_tool import XlsxTool
from model.crris_model import FacePassRecord
from utils.log_tool import face_pass_view_log
from utils.save_picture_tool import save_picture_data

logger.add(face_pass_view_log,
           format="{time:%Y-%m-%d %H:%M:%S} | {module}.py func_name[{function}] line[{line}] | {level} | {message}",
           level='INFO', retention='7 days')


def query_face_record(params):
    """搜索人脸通行记录"""
    page = params.get('page', 0)
    size = params.get('size', 0)
    keyword = params.get('keyword', '')
    user_type_name = params.get('userType', '')
    start_date = params.get('startDate', '')
    end_date = params.get('endDate', '')
    id_list = params.get('idList', [])

    select = [FacePassRecord.id, FacePassRecord.deviceId, FacePassRecord.deviceName, FacePassRecord.userId,
              FacePassRecord.userName, FacePassRecord.userType, FacePassRecord.passTime, FacePassRecord.saveTime,
              FacePassRecord.pictureUrl]
    limit_list = list()
    if not id_list:
        if user_type_name != '':
            # user_type = FacePassRecord.type_id_dict().get(user_type_name, '')
            limit_list.append(FacePassRecord.userType == user_type_name)
        if start_date and end_date:
            limit_list.append(FacePassRecord.passTime.between(start_date, end_date))

        if limit_list:
            pass_data = FacePassRecord.query(select=select, limit_list=limit_list)
        else:
            pass_data = FacePassRecord.query(select=select)

        if keyword != '':
            pass_data = pass_data.where(
                (FacePassRecord.deviceId.contains(keyword)) | (FacePassRecord.userId.contains(keyword))).order_by(
                FacePassRecord.passTime.desc())
        else:
            pass_data = pass_data.order_by(FacePassRecord.passTime.desc())

        if page and size:
            pass_data = pass_data.paginate(page, size)
    else:
        pass_data = FacePassRecord.select().where(FacePassRecord.id << id_list).order_by(
            FacePassRecord.passTime.desc())
    res = list()
    if pass_data:
        for pass_obj in pass_data:
            obj_dict = {
                'id': pass_obj.id,
                'deviceId': pass_obj.deviceId,
                'deviceName': pass_obj.deviceName,
                'userId': pass_obj.userId,
                'userName': pass_obj.userName,
                'userType': pass_obj.userType if pass_obj.userType else '',
                'passDate': pass_obj.passTime.strftime('%Y-%m-%d %H:%M:%S') if pass_obj.passTime else '',
                'dataDate': pass_obj.saveTime.strftime('%Y-%m-%d %H:%M:%S') if pass_obj.saveTime else '',
                'pictureUrl': f'{ServerConfig.root_host}{pass_obj.pictureUrl}' if pass_obj.pictureUrl else '',
            }
            res.append(obj_dict)

    page_vo = FacePassRecord.get_table_page_vo(page, size, limits=limit_list)

    return res, page_vo


def query_face_pass_record():
    """搜索人脸通行记录"""
    params = request.get_json()
    res, page_vo = query_face_record(params)

    return {'faceData': res, 'pageVo': page_vo}


def export_face_record():
    """导出人脸通行记录"""
    params = request.get_json()
    query_data = query_face_record(params)[0]
    data_list = list()
    for obj_dict in query_data:
        obj_list = [obj_dict[k] for k in obj_dict]
        data_list.append(obj_list)
    xlsx = XlsxTool(['序号', '设备ID', '设备名称', '用户ID', '用户姓名', '用户类型', '通行时间', '数据获取时间', '抓图记录'])
    current_time = datetime.now().strftime('%Y-%m-%d')
    url = xlsx.write_xlsx(data_list, f'人脸通行数据_{current_time}')

    return {'url': url}


def get_face_data():
    """获取贝叶斯推送的人脸记录数据"""
    try:
        logger.info('======== 开始处理贝叶斯推送的人脸记录数据 ========')
        params = request.get_json()
        device_id = params.get('deviceId', '')  # 字符串形式的设备ID
        device_name = params.get('deviceName', '')  # 设备名称
        floor_name = params.get('floorName', '')  # 设备所在楼层名
        floor_num = params.get('floorNum', 0)  # 楼层名对应在第几楼
        user_id = params.get('userId', '')  # 字符串形式的用户ID
        user_name = params.get('userName', 0)  # 用户名
        user_type = params.get('userType', '')  # 用户类型, 普通用户、黑名单、其他
        alarm_pic_data = params.get('alarmPicData', '')  # 截图 base64 数据
        alarm_pic_name = params.get('alarmPicName', '')  # 截图名称
        pass_time = params.get('passTime', '')  # 截图记录时间, 格式: "2021-07-19 12:00:00"
        pass_strp_time = datetime.strptime(pass_time, '%Y-%m-%d %H:%M:%S')
        save_time = datetime.now()
        current_day_str = save_time.strftime('%Y-%m-%d')
        current_day = datetime.strptime(current_day_str, '%Y-%m-%d')
        picture_path = ''
        if alarm_pic_data:
            picture_path = save_picture_data(alarm_pic_data, current_day_str, 'face_picture', alarm_pic_name)
        if picture_path:
            face_obj = FacePassRecord()
            face_obj.deviceId = device_id
            face_obj.deviceName = device_name
            face_obj.floorName = floor_name
            face_obj.floorNum = floor_num
            face_obj.userId = user_id
            face_obj.userName = user_name
            face_obj.userType = user_type
            face_obj.passTime = pass_strp_time
            face_obj.createdDay = current_day
            face_obj.saveTime = save_time
            face_obj.pictureUrl = picture_path
            face_obj.save()
    except Exception as e:
        logger.error(f'保存人脸截图数据失败：{e}')

    return {'msg': '人脸截图数据保存成功'}


def get_user_types():
    """获取所有的用户类型"""
    select = [fn.DISTINCT(FacePassRecord.userType)]
    all_user_types = FacePassRecord.query(select=select)
    user_type_list = [i.userType for i in all_user_types]

    return user_type_list
