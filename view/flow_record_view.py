# -*- coding:utf-8 -*-
from flask import request
from loguru import logger
from datetime import datetime
from config import ServerConfig
from utils.xlsx_tool import XlsxTool
from utils.log_tool import flow_record_view_log
from model.crris_model import CrowdFlowStatistics
from utils.save_picture_tool import save_picture_data

logger.add(flow_record_view_log,
           format="{time:%Y-%m-%d %H:%M:%S} | {module}.py func_name[{function}] line[{line}] | {level} | {message}",
           level='INFO', retention='7 days')


def query_crowd_record(params):
    """搜索人流统计数据"""
    page = params.get('page', 0)
    size = params.get('size', 0)
    keyword = params.get('keyword', '')
    pass_type = params.get('passType', '')
    start_date = params.get('startDate', '')
    end_date = params.get('endDate', '')
    id_list = params.get('idList', [])

    select = [CrowdFlowStatistics.id, CrowdFlowStatistics.deviceId, CrowdFlowStatistics.deviceName,
              CrowdFlowStatistics.floorName, CrowdFlowStatistics.passType, CrowdFlowStatistics.passNum,
              CrowdFlowStatistics.passTime, CrowdFlowStatistics.saveTime, CrowdFlowStatistics.pictureUrl]
    limit_list = list()
    flow_data = None
    if not id_list:
        if pass_type != '':
            pass_type = CrowdFlowStatistics.type_id_dict().get(pass_type, '')
            limit_list.append(CrowdFlowStatistics.passType == pass_type)
        if start_date and end_date:
            limit_list.append(CrowdFlowStatistics.passTime.between(start_date, end_date))

        if limit_list:
            flow_data = CrowdFlowStatistics.query(select=select, limit_list=limit_list)
        else:
            flow_data = CrowdFlowStatistics.query(select=select)

        if keyword != '':
            flow_data = flow_data.where((CrowdFlowStatistics.deviceId.contains(keyword)) | (CrowdFlowStatistics.deviceName.contains(keyword))).order_by(
                CrowdFlowStatistics.passTime.desc())
        else:
            flow_data = flow_data.order_by(CrowdFlowStatistics.passTime.desc())
        if page and size:
            flow_data = flow_data.paginate(page, size)
    else:
        flow_data = CrowdFlowStatistics.select().where(CrowdFlowStatistics.id << id_list).order_by(
                CrowdFlowStatistics.passTime.desc())

    res = list()
    if flow_data:
        for flow_obj in flow_data:
            obj_dict = {
                'id': flow_obj.id,
                'deviceId': flow_obj.deviceId if flow_obj.deviceId != '' else '',
                'deviceName': flow_obj.deviceName or '',
                'floor': flow_obj.floorName or '',
                'passType': flow_obj.id_type_dict().get(flow_obj.passType) if flow_obj.id_type_dict else '',
                'passNum': flow_obj.passNum if flow_obj.passNum != '' else '',
                'recordDate': flow_obj.passTime.strftime('%Y-%m-%d %H:%M:%S') if flow_obj.passTime else '',
                'dataDate': flow_obj.saveTime.strftime('%Y-%m-%d %H:%M:%S') if flow_obj.saveTime else '',
                # TODO:看贝叶斯返回的这个是可以访问的 URL，还是要我们这边存图片
                'pictureUrl': f'{ServerConfig.root_host}{flow_obj.pictureUrl}' if flow_obj.pictureUrl else '',
            }
            res.append(obj_dict)

    page_vo = CrowdFlowStatistics.get_table_page_vo(page, size, limits=limit_list)

    return res, page_vo


def query_crowd_flow_record():
    """搜索人流统计数据"""
    params = request.get_json()
    res, page_vo = query_crowd_record(params)

    return {'flowData': res, 'pageVo': page_vo}


def export_flow_record():
    """导出re"""
    params = request.get_json()
    query_data = query_crowd_record(params)[0]
    data_list = list()
    for obj_dict in query_data:
        obj_list = [obj_dict[k] for k in obj_dict]
        data_list.append(obj_list)
    xlsx = XlsxTool(['序号', '设备ID', '设备名称', '设备所在楼层', '出入类型', '出入人数', '记录时间', '数据获取时间', '抓图记录'])
    current_time = datetime.now().strftime('%Y-%m-%d')
    url = xlsx.write_xlsx(data_list, f'人流统计数据_{current_time}')

    return {'url': url}


def get_flow_data():
    """获取贝叶斯推送的人流统计数据"""
    try:
        logger.info('======== 开始处理贝叶斯推送的人流统计数据 ========')
        params = request.get_json()
        device_id = params.get('deviceId', '')  # 字符串形式的设备ID
        device_name = params.get('deviceName', '')  # 设备名称
        floor_name = params.get('floorName', '')  # 所在楼层
        floor_num = params.get('floorNum', '')  # 楼层名对应第几楼
        pass_type = params.get('passType', 0)  # 出入类型
        pass_num = params.get('passNum', 0)  # 出入人数
        alarm_pic_data = params.get('alarmPicData', '')  # 截图 base64 数据
        alarm_pic_name = params.get('alarmPicName', '')  # 截图名称
        pass_time = params.get('passTime', '')  # 截图记录时间, 格式: "2021-07-19 12:00:00"
        pass_strp_time = datetime.strptime(pass_time, '%Y-%m-%d %H:%M:%S')
        save_time = datetime.now()
        current_day_str = save_time.strftime('%Y-%m-%d')
        current_day = datetime.strptime(current_day_str, '%Y-%m-%d')
        picture_path = ''
        if alarm_pic_data:
            picture_path = save_picture_data(alarm_pic_data, current_day_str, 'flow_picture', alarm_pic_name)
        if picture_path:
            flow_obj = CrowdFlowStatistics()
            flow_obj.deviceId = device_id
            flow_obj.deviceName = device_name
            flow_obj.floorName = floor_name
            flow_obj.floorNum = floor_num
            flow_obj.passType = pass_type
            flow_obj.passNum = pass_num
            flow_obj.passTime = pass_strp_time
            flow_obj.createdDay = current_day
            flow_obj.saveTime = save_time
            flow_obj.pictureUrl = picture_path
            flow_obj.save()
    except Exception as e:
        logger.error(f'保存人流截图数据失败：{e}')

    return {'msg': '人流截图数据保存成功'}
