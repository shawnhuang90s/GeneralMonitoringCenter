# -*- coding:utf-8 -*-
import os
import json
import pymysql
from peewee import fn
from loguru import logger
from flask import request
from config import ServerConfig
from utils.host_tool import get_ip
from utils.redis_tool import RedisConn
from utils.log_tool import home_view_log
from datetime import datetime, timedelta
from view.area_config_view import get_status_count
from utils.time_tool import get_split_time_info, get_day_begin_end
from model.crris_model import FloorPersonStatistics, CrowdFlowStatistics, FacePassRecord, AreaConfig, AlarmScreenshot

logger.add(home_view_log,
           format="{time:%Y-%m-%d %H:%M:%S} | {module}.py func_name[{function}] line[{line}] | {level} | {message}",
           level='INFO', retention='7 days')


def get_push_url():
    """AI报警页面、人脸通行页面、人流统计页面的接收地址、Websocket 推送地址"""
    host_ip = get_ip()
    url = f'http://{host_ip}:{ServerConfig.port}/api/crris/'
    alarm_url = f'{url}get_alarm_data'
    face_url = f'{url}get_face_data'
    flow_url = f'{url}get_flow_data'
    # ws_url = f'http://{host_ip}:{ServerConfig.port}/test_conn'  # /test_conn 是命名空间设置的内容
    ws_url = f'http://{host_ip}:{ServerConfig.port}'  # 暂时不使用命名空间的方式

    return {
        'alarmUrl': alarm_url,
        'faceUrl': face_url,
        'flowUrl': flow_url,
        'wsUrl': ws_url
    }


def get_floor_num():
    """获取前端传来的楼层名"""
    params = request.get_json()
    floor_num = params.get('floor', '')
    assert floor_num, '缺少必要参数：floor'

    return floor_num


def get_floor_person_num():
    """首页刷新时获取当前楼层人数"""
    floor_num = get_floor_num()
    res = {'num': 0}
    # 查询所有楼层的人数并汇总
    if floor_num == 'all':
        select = [fn.DISTINCT(FloorPersonStatistics.floorNum)]
        floors = FloorPersonStatistics.query(select=select)
        # floor_list = [i.floorNum for i in floors]
        for i in floors:
            floor_number = i.floorNum
            floor_obj = FloorPersonStatistics.filter(FloorPersonStatistics.floorNum == floor_number).order_by(
                FloorPersonStatistics.recordTime.desc()).first()
            if floor_obj and floor_obj.personNum:
                res['num'] += floor_obj.personNum
    # 查询单个楼层的人数
    else:
        floor_obj = FloorPersonStatistics.filter(FloorPersonStatistics.floorNum == floor_num).order_by(
            FloorPersonStatistics.recordTime.desc()).first()
        if floor_obj:
            res['num'] += floor_obj.personNum

    return res


def get_person_num_statistics():
    """获取楼层实时人数"""
    floor_num = get_floor_num()
    hour_minute_list, split_time_strp_list = get_split_time_info()
    x_axis_data = hour_minute_list
    series_data = [0, ]
    for i in range(len(split_time_strp_list)):
        num = 0
        select = [FloorPersonStatistics.personNum]
        if floor_num == 'all':
            limit_list = []
        else:
            limit_list = [FloorPersonStatistics.floorNum == floor_num]
        if i < len(split_time_strp_list) - 1:
            limit_list.append(FloorPersonStatistics.recordTime >= split_time_strp_list[i])
            limit_list.append(FloorPersonStatistics.recordTime < split_time_strp_list[i + 1])
            num_data = FloorPersonStatistics.query(select=select, limit_list=limit_list)
            if num_data:
                for i in num_data:
                    num += i.personNum
        series_data.append(num)

    return {'xAxisData': x_axis_data, 'seriesData': series_data}


def get_crowd_flow_statistics():
    """获取实时人员流量、人脸统计"""
    floor_num = get_floor_num()
    res = {'face': 0, 'in': 0, 'out': 0, 'charts': {}}
    current_time = datetime.now()
    last_minute_time = datetime.now() + timedelta(minutes=-1)
    print(current_time, last_minute_time)
    # 查询最新一分钟内人脸统计数量
    face_select = [fn.COUNT(FacePassRecord.id).alias('face_num')]
    limit_list = [FacePassRecord.passTime.between(last_minute_time, current_time)]
    face_data = FacePassRecord.query(select=face_select, limit_list=limit_list).first()
    res['face'] = face_data.face_num
    # 查询最新一分钟内人员进入/离开数量
    flow_select = [CrowdFlowStatistics.passNum]
    limit_list = [CrowdFlowStatistics.passTime.between(last_minute_time, current_time)]
    flow_data = CrowdFlowStatistics.query(select=flow_select, limit_list=limit_list)
    for flow_obj in flow_data:
        if flow_obj.passType == 1:  # 人员进入
            res['in'] += flow_obj.passNum
        else:  # 人员离开
            res['out'] += flow_obj.passNum

    hour_minute_list, split_time_strp_list = get_split_time_info()
    legend_data = ['人脸', '进入', '离开']
    x_axis_data = hour_minute_list
    series_data = [[0, ], [0, ], [0, ]]  # 三个列表, 分别代表人脸统计、人员进入、人员离开三个模块各个时间段的数量
    for i in range(len(split_time_strp_list)):
        # 人脸数量统计
        if floor_num == 'all':
            limit_list = []
        else:
            limit_list = [FacePassRecord.floorNum == floor_num]
        if i < len(split_time_strp_list) - 1:
            limit_list.append(FacePassRecord.passTime >= split_time_strp_list[i])
            limit_list.append(FacePassRecord.passTime < split_time_strp_list[i + 1])
            num_data = FacePassRecord.query(select=face_select, limit_list=limit_list).first()
            series_data[0].append(num_data.face_num)
        # 人员进入数量统计
        flow_in_num = 0
        flow_out_num = 0
        flow_select = [CrowdFlowStatistics.passNum, CrowdFlowStatistics.passType]
        if floor_num == 'all':
            limit_list = []
        else:
            limit_list = [CrowdFlowStatistics.floorNum == floor_num]
        if i < len(split_time_strp_list) - 1:
            limit_list.append(CrowdFlowStatistics.passTime >= split_time_strp_list[i])
            limit_list.append(CrowdFlowStatistics.passTime < split_time_strp_list[i + 1])
            num_data = CrowdFlowStatistics.query(select=flow_select, limit_list=limit_list)
            for flow_obj in num_data:
                if flow_obj.passType == 1:  # 人员进入
                    flow_in_num += flow_obj.passNum
                else:  # 人员离开
                    flow_out_num -= flow_obj.passNum
        series_data[1].append(flow_in_num)
        series_data[2].append(flow_out_num)

    res['charts']['legendData'] = legend_data
    res['charts']['xAxisData'] = x_axis_data
    res['charts']['seriesData'] = series_data

    return res


def get_camera_list(floor_num):
    """获取某楼层或整栋楼的点位ID"""
    camera_list = list()
    if floor_num == 'all':
        # 查询整栋楼摄像头ID
        areas = AreaConfig.select()
        for area_obj in areas:
            area_camera_list = json.loads(area_obj.cameraList) if area_obj.cameraList else []
            if area_camera_list:
                camera_list.extend(area_camera_list)
    else:
        # 查询某层楼摄像头ID
        area_obj = AreaConfig.filter(AreaConfig.areaNum == floor_num).first()
        if area_obj and area_obj.cameraList:
            area_camera_list = json.loads(area_obj.cameraList)
            camera_list.extend(area_camera_list)

    camera_list = list(set(camera_list))

    return camera_list


def get_device_status():
    """获取摄像头、人脸Pad、人流监控设备状态"""
    ret = {
        'camera': {
            'online': 0,
            'total': 0
        },
        'face': {
            'online': 0,
            'total': 0
        },
        'flow': {
            'online': 0,
            'total': 0
        },
    }
    floor_num = get_floor_num()
    camera_list = get_camera_list(floor_num)
    if floor_num == 'all':
        # 查询整栋楼人脸Pad、人流监控设备在线离线数量
        # {'faceOnline': 0, 'faceOffline': 0, 'flowOffline': 0, 'flowOnline': 0, 'companies': 0}
        face_flow_count = RedisConn.get_face_flow_companies(floor_num='allStatusCount')
    else:
        # 查询整栋楼人脸Pad、人流监控设备在线离线数量
        face_flow_count = RedisConn.get_face_flow_companies(floor_num=floor_num)

    res = get_status_count(camera_list)  # {'online': 5, 'offline': 0}
    ret['camera']['online'] = res['online']
    ret['camera']['total'] = res['offline'] + res['online']
    ret['face']['online'] = face_flow_count['faceOnline']
    ret['face']['total'] = face_flow_count['faceOnline'] + face_flow_count['faceOffline']
    ret['flow']['online'] = face_flow_count['flowOnline']
    ret['flow']['total'] = face_flow_count['flowOnline'] + face_flow_count['flowOffline']

    return ret


def get_alarm_statistics():
    """获取7天AI报警统计"""
    res = {
        'legendData': [],
        'xAxisData': [],
        'seriesData': []
    }
    floor_num = get_floor_num()
    area_camera_list = get_camera_list(floor_num)
    six_days_ago = get_day_begin_end(-6)[0]
    # 7天日期集合
    res['xAxisData'] = [
        get_day_begin_end(-6)[6], get_day_begin_end(-5)[6], get_day_begin_end(-4)[6], get_day_begin_end(-3)[6],
        get_day_begin_end(-2)[6], get_day_begin_end(-1)[6], get_day_begin_end(0)[6]
    ]
    # 7天内当前楼层有过的算法名称集合
    select = [fn.DISTINCT(AlarmScreenshot.alarmType)]
    limit_list = [AlarmScreenshot.alarmTime >= six_days_ago, AlarmScreenshot.cameraId << area_camera_list]
    seven_alarm_cameras = AlarmScreenshot.query(select=select, limit_list=limit_list)
    # 统计7天内所有的报警截图类型
    alarm_type_list = [i.alarmType for i in seven_alarm_cameras]
    for alarm_type in alarm_type_list:
        alarm_days_count = [0, 0, 0, 0, 0, 0, 0]  # 长度与 x_coordinate 的一样
        alarm_type_name = RedisConn.get_algo_dict()[0].get(alarm_type, '')
        if alarm_type_name:
            res['legendData'].append(alarm_type_name)
            type_count = AlarmScreenshot.select(AlarmScreenshot.createdDay,
                                                fn.COUNT(AlarmScreenshot.id).alias('screenshot_num')).where(
                AlarmScreenshot.alarmType == alarm_type, AlarmScreenshot.createdDay >= six_days_ago,
                AlarmScreenshot.cameraId << area_camera_list).group_by(AlarmScreenshot.createdDay)
            for day_type in type_count:
                if day_type.createdDay:
                    created_day_str = day_type.createdDay.strftime('%Y-%m-%d')
                    for day_index in range(len(res['xAxisData'])):
                        if created_day_str == res['xAxisData'][day_index]:
                            alarm_days_count[day_index] = day_type.screenshot_num
            res['seriesData'].append(alarm_days_count)

    return res


def get_floor_name_by_camera_id(camera_id):
    """根据点位ID找到关联的楼层名称"""
    floor_name_list = list()
    areas = AreaConfig.select()
    for area_obj in areas:
        area_camera_list = json.loads(area_obj.cameraList) if area_obj.cameraList else []
        if area_camera_list and camera_id in area_camera_list:
            floor_name_list.append((area_obj.areaName, area_obj.areaNum))

    return floor_name_list


def get_floor_num_by_camera_id(camera_id):
    """根据点位ID找到关联的楼层名称"""
    floor_num_list = list()
    areas = AreaConfig.select()
    for area_obj in areas:
        area_camera_list = json.loads(area_obj.cameraList) if area_obj.cameraList else []
        if area_camera_list and camera_id in area_camera_list:
            floor_num_list.append(area_obj.areaNum)

    return floor_num_list


def get_event_record():
    """获取事件日志"""
    params = request.get_json()
    floor_num = params.get('floor', '')
    assert floor_num, '缺少必要参数：floor'
    name = params.get('name', '')
    assert name, '缺少必要参数：name'

    res = list()
    area_camera_list = get_camera_list(floor_num)
    if name == '全部':
        # 连接 MySQL
        mysql_conn = pymysql.connect(
            user=ServerConfig.db_user,
            password=ServerConfig.db_password,
            host=ServerConfig.db_host,
            port=ServerConfig.db_port,
            database=ServerConfig.db_name
        )
        cursor = mysql_conn.cursor()
        # 使用 UNION 将三个表的数据联合, 按截图时间排序, 查询最新的 50 条数据
        # 如果查询整栋楼的数据
        if floor_num == 'all':
            sql_str = """
            SELECT * FROM (
                SELECT id, alarmTime AS record_time FROM crAlarmScreenshot
                UNION (SELECT id, passTime AS record_time FROM crFacePassRecord)
                UNION (SELECT id, passTime AS record_time FROM crCrowdFlowStatistics)
            ) 
            AS alldata
            ORDER BY record_time DESC 
            LIMIT 50;
            """
        # 如果查询某层楼的数据
        else:
            area_camera_tuple = tuple(area_camera_list)
            if area_camera_tuple:
                if len(area_camera_tuple) == 1:
                    sql_str = f"""
                    SELECT * FROM (
                        SELECT id, alarmTime AS record_time FROM crAlarmScreenshot WHERE cameraId={area_camera_tuple[0]}
                        UNION (SELECT id, passTime AS record_time FROM crFacePassRecord WHERE floorNum={floor_num}) 
                        UNION (SELECT id, passTime AS record_time FROM crCrowdFlowStatistics WHERE floorNum={floor_num})
                    )
                    AS alldata
                    ORDER BY record_time 
                    DESC LIMIT 50;
                    """
                else:
                    sql_str = f"""
                    SELECT * FROM (
                        SELECT id, alarmTime AS record_time FROM crAlarmScreenshot WHERE cameraId in {area_camera_tuple}
                        UNION (SELECT id, passTime AS record_time FROM crFacePassRecord WHERE floorNum={floor_num}) 
                        UNION (SELECT id, passTime AS record_time FROM crCrowdFlowStatistics WHERE floorNum={floor_num})
                    )
                    AS alldata
                    ORDER BY record_time 
                    DESC LIMIT 50;
                    """
            # 如果某个楼层没有配置点位信息, 那么该楼层肯定没有报警截图, 就不用查该楼层的信息, 否则报错
            else:
                sql_str = f"""
                SELECT * FROM (
                    SELECT id, passTime AS record_time FROM crFacePassRecord WHERE floorNum={floor_num}
                    UNION (SELECT id, passTime AS record_time FROM crCrowdFlowStatistics WHERE floorNum={floor_num})
                )
                AS alldata
                ORDER BY record_time 
                DESC LIMIT 50;
                """
        cursor.execute(sql_str)
        all_data = cursor.fetchall()
        if all_data:
            for data_obj in all_data:
                id = data_obj[0]
                record_time = data_obj[1]
                # 判断是哪个表的数据
                alarm_obj = AlarmScreenshot.filter(AlarmScreenshot.id == id,
                                                   AlarmScreenshot.alarmTime == record_time).first()
                if alarm_obj:
                    floor = ''
                    if floor_num == 'all':
                        # 如果首页查询整栋楼事件日志, 且查询的是全部事件, 则报警截图对应的点位可能多个楼层都有使用
                        area_info = get_floor_name_by_camera_id(alarm_obj.cameraId)
                    else:
                        area_obj = AreaConfig.filter(AreaConfig.areaNum == floor_num).first()
                        area_info = area_obj.areaName
                        floor = area_obj.areaNum
                    alarm_name = RedisConn.get_algo_dict()[0].get(alarm_obj.alarmType, '')
                    if isinstance(area_info, list):
                        for area in area_info:
                            obj_dict = {
                                'id': alarm_obj.id,
                                'date': alarm_obj.alarmTime.strftime('%H:%M:%S') if alarm_obj.alarmTime else '',
                                'area': area[0],
                                'floor': area[1],
                                'type': 'AI报警',
                                'isAlarm': True,
                                'detail': alarm_name
                            }
                            res.append(obj_dict)
                        continue
                    else:
                        obj_dict = {
                            'id': alarm_obj.id,
                            'date': alarm_obj.alarmTime.strftime('%H:%M:%S') if alarm_obj.alarmTime else '',
                            'area': area_info,
                            'floor': floor,
                            'isAlarm': True,
                            'type': 'AI报警',
                            'detail': alarm_name
                        }
                        res.append(obj_dict)
                        continue

                face_obj = FacePassRecord.filter(FacePassRecord.id == id,
                                                 FacePassRecord.passTime == record_time).first()
                if face_obj:
                    obj_dict = {
                        'id': face_obj.id,
                        'date': face_obj.passTime.strftime('%H:%M:%S') if face_obj.passTime else '',
                        'area': face_obj.floorName,
                        'floor': face_obj.floorNum,
                        'type': '人脸',
                        'isAlarm': False,
                        'detail': '刷脸进入'
                    }
                    res.append(obj_dict)
                    continue

                flow_obj = CrowdFlowStatistics.filter(CrowdFlowStatistics.id == id,
                                                      CrowdFlowStatistics.passTime == record_time).first()
                if flow_obj:
                    detail_info = ''
                    pass_type_name = flow_obj.id_type_dict().get(flow_obj.passType) if flow_obj.passType else ''
                    if pass_type_name and flow_obj.passNum:
                        detail_info = f'{pass_type_name} {flow_obj.passNum} 人'
                    obj_dict = {
                        'id': flow_obj.id,
                        'date': flow_obj.passTime.strftime('%H:%M:%S') if flow_obj.passTime else '',
                        'area': flow_obj.floorName,
                        'floor': flow_obj.floorNum,
                        'type': '流量计',
                        'isAlarm': False,
                        'detail': detail_info
                    }
                    res.append(obj_dict)
                    continue
    elif name == 'AI报警':
        # select() 添加只需要查询的字段
        alarm_data = AlarmScreenshot.select(AlarmScreenshot.id, AlarmScreenshot.alarmTime, AlarmScreenshot.cameraId,
                                            AlarmScreenshot.alarmType).where(
            AlarmScreenshot.cameraId << area_camera_list).order_by(AlarmScreenshot.alarmTime.desc()).limit(50)
        for alarm_obj in alarm_data:
            floor = ''
            if floor_num == 'all':
                # 如果首页查询整栋楼事件日志, 且查询的是全部事件, 则报警截图对应的点位可能多个楼层都有使用
                area_info = get_floor_name_by_camera_id(alarm_obj.cameraId)
            else:
                area_obj = AreaConfig.filter(AreaConfig.areaNum == floor_num).first()
                area_info = area_obj.areaName
                floor = area_obj.areaNum
            # 报警类型名称
            alarm_name = RedisConn.get_algo_dict()[0].get(alarm_obj.alarmType, '')
            if isinstance(area_info, list):
                for area in area_info:
                    obj_dict = {
                        'id': alarm_obj.id,
                        'date': alarm_obj.alarmTime.strftime('%H:%M:%S') if alarm_obj.alarmTime else '',
                        'area': area[0],
                        'floor': area[1],
                        'type': name,
                        'isAlarm': True,
                        'detail': alarm_name
                    }
                    res.append(obj_dict)
            else:
                alarm_dict = {
                    'id': alarm_obj.id,
                    'date': alarm_obj.alarmTime.strftime('%H:%M:%S') if alarm_obj.alarmTime else '',
                    'area': area_info,
                    'floor': floor,
                    'isAlarm': True,
                    'type': name,
                    'detail': alarm_name
                }
                res.append(alarm_dict)
    elif name == '流量计':
        if floor_num == 'all':
            flow_data = CrowdFlowStatistics.select(CrowdFlowStatistics.id, CrowdFlowStatistics.passTime,
                                                   CrowdFlowStatistics.floorName, CrowdFlowStatistics.passType,
                                                   CrowdFlowStatistics.passNum).order_by(
                CrowdFlowStatistics.passTime.desc()).limit(50)
        else:
            flow_data = CrowdFlowStatistics.select(CrowdFlowStatistics.id, CrowdFlowStatistics.passTime,
                                                   CrowdFlowStatistics.floorName, CrowdFlowStatistics.floorNum,
                                                   CrowdFlowStatistics.passType, CrowdFlowStatistics.passNum).where(
                CrowdFlowStatistics.floorNum == floor_num).order_by(CrowdFlowStatistics.passTime.desc()).limit(50)
        for flow_obj in flow_data:
            # 出入详情
            detail_info = ''
            pass_type_name = flow_obj.id_type_dict().get(flow_obj.passType) if flow_obj.id_type_dict else ''
            if pass_type_name and flow_obj.passNum:
                detail_info = f'{pass_type_name} {flow_obj.passNum} 人'
            flow_dict = {
                'id': flow_obj.id,
                'date': flow_obj.passTime.strftime('%H:%M:%S') if flow_obj.passTime else '',
                'area': flow_obj.floorName,
                'floor': flow_obj.floorNum,
                'isAlarm': False,
                'type': name,
                'detail': detail_info
            }
            res.append(flow_dict)
    elif name == '人脸':
        if floor_num == 'all':
            face_data = FacePassRecord.select(FacePassRecord.id, FacePassRecord.floorName,
                                              FacePassRecord.passTime).order_by(FacePassRecord.passTime.desc()).limit(
                50)
        else:
            face_data = FacePassRecord.select(FacePassRecord.id, FacePassRecord.floorName, FacePassRecord.floorNum,
                                              FacePassRecord.passTime).where(
                FacePassRecord.floorNum == floor_num).order_by(
                FacePassRecord.passTime.desc()).limit(50)
        for face_obj in face_data:
            flow_dict = {
                'id': face_obj.id,
                'date': face_obj.passTime.strftime('%H:%M:%S') if face_obj.passTime else '',
                'area': face_obj.floorName,
                'floor': face_obj.floorNum,
                'isAlarm': False,
                'type': name,
                'detail': '刷脸进入'
            }
            res.append(flow_dict)

    return res


def get_record_screenshot():
    """
    用户刚打开首页, 前端传当前楼层名过来, 后端返回该区域下所有点位中的报警截图
    具体多少张根据 page 和 size 来决定
    """
    res = list()
    params = request.get_json()
    page = params.get('page', 1)
    size = params.get('size', 20)
    alarm_type = params.get('alarmType', '')
    floor_num = get_floor_num()
    area_camera_list = get_camera_list(floor_num)
    if area_camera_list:
        # 报警抓图
        select = [AlarmScreenshot.id, AlarmScreenshot.cameraId, AlarmScreenshot.alarmType, AlarmScreenshot.alarmTime,
                  AlarmScreenshot.createdDay, AlarmScreenshot.saveTime, AlarmScreenshot.pictureUrl]
        if alarm_type or alarm_type == 0:
            query_limit = [AlarmScreenshot.cameraId << area_camera_list, AlarmScreenshot.alarmType == alarm_type]
        else:
            query_limit = [AlarmScreenshot.cameraId << area_camera_list]
        screen_shots = AlarmScreenshot.query(select=select, limit_list=query_limit).order_by(
            AlarmScreenshot.alarmTime.desc()).paginate(page, size)
        for screen_obj in screen_shots:
            picture_url = ''
            picture_path = ''
            picture = screen_obj.pictureUrl if screen_obj.pictureUrl else '',
            if picture:
                picture_url = f'{ServerConfig.root_host}{picture[0]}'
                picture_path = f'{ServerConfig.root_path}{picture[0]}'
            # 有真正的报警截图文件才传给前端, 反之不传
            if os.path.exists(picture_path):
                camera_id = screen_obj.cameraId
                camera_name = ''
                json_camera_name = RedisConn.redis_db.get(camera_id)
                if json_camera_name:
                    camera_name = json_camera_name.decode()
                res.append({
                    'id': screen_obj.id,
                    'cameraId': camera_id,
                    'alarmType': screen_obj.alarmType,
                    'alarmName': RedisConn.get_algo_dict()[0].get(screen_obj.alarmType, ''),
                    'cameraName': camera_name,
                    'alarmTime': screen_obj.alarmTime.strftime('%Y-%m-%d %H:%M:%S') if screen_obj.alarmTime else '',
                    'pictureUrl': picture_url
                })
    return res


def get_companies_screenshots():
    """获取当前楼层入驻企业数量、报警截图数量"""
    res = {'companies': 0, 'screens': 0, 'person': 0}
    try:
        floor_num = get_floor_num()
        camera_list = get_camera_list(floor_num)
        current_day_begin = get_day_begin_end(0)[2]
        alarm_data = AlarmScreenshot.select(fn.COUNT(AlarmScreenshot.id).alias('screenshot_num')).where(
            AlarmScreenshot.alarmTime >= current_day_begin, AlarmScreenshot.cameraId << camera_list).first()
        res['screens'] = alarm_data.screenshot_num
        face_flow_companies = RedisConn.get_face_flow_companies(floor_num)
        if face_flow_companies.get('companies', 0):
            res['companies'] = face_flow_companies['companies']
        person_num = get_floor_person_num()
        res['person'] = person_num['num']
    except Exception as e:
        logger.error(f'获取入驻企业数量、报警截图数失败：{e}')

    return res


def get_algo_config():
    """展示当前区域下所有点位关联的报警类型，包括ID和名称（从报警截图记录表中获取）"""
    floor_num = get_floor_num()
    res = dict()
    area_camera_list = get_camera_list(floor_num)
    if area_camera_list:
        select = [fn.DISTINCT(AlarmScreenshot.alarmType)]
        limit_list = [AlarmScreenshot.cameraId << area_camera_list]
        screen_shots = AlarmScreenshot.query(select=select, limit_list=limit_list)
        if screen_shots:
            alarm_type_list = [i.alarmType for i in screen_shots]
            # 整理出算法类型的ID与名称的对应关系
            id_name_dict = RedisConn.get_algo_dict()[0]
            for alarm_type in alarm_type_list:
                if id_name_dict.get(alarm_type, ''):
                    res[alarm_type] = id_name_dict.get(alarm_type, '')
    return res
