# -*- coding:utf-8 -*-
import json
import redis
import pymysql
from config import ServerConfig
from datetime import datetime, timedelta
from utils.interface_tool import get_crip_data
from utils.time_tool import get_split_time_info, get_day_begin_end

exists_url_dict = dict()
exists_id_list = list()
event_record = dict()  # 事件日志


def get_redis_conn():
    """链接 Redis"""
    url = 'redis://@%s:%s/%s' % (ServerConfig.redis_host, ServerConfig.redis_port, ServerConfig.redis_db)
    redis_conn = redis.from_url(url)

    return redis_conn


def get_mysql_conn():
    """链接 MySQL"""
    mysql_conn = pymysql.connect(
        user=ServerConfig.db_user,
        password=ServerConfig.db_password,
        host=ServerConfig.db_host,
        port=ServerConfig.db_port,
        database=ServerConfig.db_name
    )

    return mysql_conn


def get_alarm_name(redis_conn):
    """根据报警类型ID获取报警类型名称"""
    id_name_dict = dict()
    algo_config = redis_conn.get(ServerConfig.algo_key)
    if algo_config:
        algo_config = json.loads(algo_config)
        for config_dict in algo_config:
            id_name_dict[config_dict['task_key']] = config_dict['name']

    return id_name_dict


def get_app_id(redis_conn):
    app_id = ''
    app_id_bytes = redis_conn.hget(ServerConfig.access_name, ServerConfig.app_id)
    if app_id_bytes:
        app_id = app_id_bytes.decode()

    return app_id


def get_app_secret(redis_conn):
    app_secret = ''
    app_secret_bytes = redis_conn.hget(ServerConfig.access_name, ServerConfig.app_secret)
    if app_secret_bytes:
        app_secret = app_secret_bytes.decode()

    return app_secret


def get_access_key(redis_conn):
    """获取 accessKey """
    access_key = ''
    access_key_bytes = redis_conn.hget(ServerConfig.access_name, ServerConfig.access_key)
    if access_key_bytes:
        access_key = access_key_bytes.decode()
    # 如果 Redis 中查不到, 则尝试从 Redis 中获取 appId, appSecret, 再调用接口获取 access_key, 并保存到 Redis 中
    else:
        app_id_bytes = redis_conn.hget(ServerConfig.access_name, ServerConfig.app_id)
        app_secret_bytes = redis_conn.hget(ServerConfig.access_name, ServerConfig.app_secret)
        if app_id_bytes and app_secret_bytes:
            app_id = app_id_bytes.decode()
            app_secret = app_secret_bytes.decode()
            path = 'api/openapi/authenticate'
            data = {'appId': app_id, 'appSecret': app_secret}
            res = get_crip_data(path, method='POST', data_dict=data)
            # 申请成功则返回 accessKey, 保存下来
            if res.get('accessKey', ''):
                redis_conn.hmset(ServerConfig.access_name, {ServerConfig.access_key: res['accessKey']})
                access_key = res['accessKey']

    return access_key


def get_latest_access_key(access_key, response, redis_conn):
    """获取最新的 accessKey"""
    # 判断 accessKey 是否还有效, 如果无效再调用接口获取最新的 accessKey
    if response.get('errorMsg', '') and 'access key' in response['errorMsg']:
        app_id = get_app_id(redis_conn)
        app_secret = get_app_secret(redis_conn)
        path = 'api/openapi/authenticate'
        data = {'appId': app_id, 'appSecret': app_secret}
        res = get_crip_data(path, method='POST', data_dict=data)
        # 申请成功则返回 accessKey, 保存下来
        if res.get('accessKey', ''):
            redis_conn.hmset(ServerConfig.access_name, {ServerConfig.access_key: res['accessKey']})
            access_key = res['accessKey']

    return access_key


def get_camera_url(camera_id, access_key, exists_url_dict, redis_conn):
    """获取点位可播放地址"""
    print(f'当前已保存的点位播放地址信息：{exists_url_dict}')
    if exists_url_dict.get(str(camera_id), ''):
        camera_url = exists_url_dict[str(camera_id)]
    else:
        # user_obj = token_auth()
        # open_id = user_obj.openId
        # 相关接口暂时不需要 openId
        open_id = ''
        path = f'api/openapi/camera/stream?cameraId={camera_id}&openId={open_id}'
        if access_key:
            ret = get_crip_data(path=path, accessKey=access_key)
            new_access_key = get_latest_access_key(access_key, ret, redis_conn)
            # 如果 accessKey 更新了, 则所有涉及 accessKey 调用推理平台的接口都要重新调用
            if new_access_key != access_key:
                ret = get_crip_data(path=path, accessKey=new_access_key)
            camera_url = ret['url'] if ret.get('url', '') else ''
            exists_url_dict[str(camera_id)] = camera_url
        else:
            print('accessKey 为空, 无法获取推理平台相关接口的数据')
            camera_url = ''
    # camera_url = 'http://192.168.0.101:9012/video?port=1935&app=video&stream=20210615111313ExGAvldxZ0'

    return camera_url


def get_floor_name(camera_id, cursor):
    """获取当前点位关联的楼层名"""
    floor_name_list = list()
    sql_str = """
    SELECT t.areaName, t.cameraList
    FROM crAreaConfig t;
    """
    cursor.execute(sql_str)
    areas = cursor.fetchall()
    if areas:
        for area_obj in areas:
            area_camera_list = json.loads(area_obj[1]) if area_obj[1] else []
            if area_camera_list and camera_id in area_camera_list:
                floor_name_list.append(f'{area_obj[0]}')
    floor_name_list = list(set(floor_name_list))

    return floor_name_list


def get_face_flow_companies(floor_name, redis_conn):
    """
    获取人脸Pad、人流监控设备状态
    floor_name: 楼层名, 如果是查询整栋楼, 则固定为 allStatusCount"""
    face_flow_key = ServerConfig.face_flow_companies_count
    status_count_bytes = redis_conn.hget(face_flow_key, floor_name)
    if status_count_bytes:
        status_count_str = status_count_bytes.decode()
        status_count_dict = json.loads(status_count_str)
    else:
        status_count_dict = {'faceOnline': 0, 'faceOffline': 0, 'flowOffline': 0, 'flowOnline': 0, 'companies': 0}

    return status_count_dict


def get_companies(floor_name, redis_conn):
    """获取当前楼层入驻的企业数量"""
    company_num = 0
    face_flow_companies = get_face_flow_companies(floor_name, redis_conn)
    if face_flow_companies.get('companies', 0):
        company_num = face_flow_companies['companies']

    return company_num


def get_camera_list(floor_name, cursor):
    """获取当前楼层名关联的点位ID"""
    camera_list = list()
    if floor_name == 'all':
        sql_str = """
            SELECT t.cameraList
            FROM crAreaConfig t;
            """
        cursor.execute(sql_str)
        areas = cursor.fetchall()
        if areas:
            for area_obj in areas:
                area_camera_list = json.loads(area_obj[0]) if area_obj[0] else []
                if area_camera_list:
                    camera_list.extend(area_camera_list)
    else:
        sql_str = f"""
        SELECT t.cameraList
        FROM crAreaConfig t
        WHERE t.areaName='{floor_name}';
        """
        cursor.execute(sql_str)
        area_obj = cursor.fetchone()
        if area_obj and area_obj.cameraList:
            camera_list = json.loads(area_obj.cameraList)

    camera_list = list(set(camera_list))

    return camera_list


def get_status_count(camera_list, redis_conn):
    # 调用接口获取摄像头在线离线状态
    res = {'online': 0, 'offline': 0}
    # user_obj = token_auth()
    # open_id = user_obj.openId
    open_id = ''
    path = f'api/openapi/camera/status?openId={open_id}'
    data_dict = {'cameraList': camera_list}
    access_key = get_access_key(redis_conn)
    response = get_crip_data(path=path, method='POST', data_dict=data_dict, accessKey=access_key)
    new_access_key = get_latest_access_key(access_key, response, redis_conn)
    # 如果 accessKey 更新了, 则所有涉及 accessKey 调用推理平台的接口都要重新调用
    if new_access_key != access_key:
        response = get_crip_data(path=path, method='POST', data_dict=data_dict, accessKey=new_access_key)
    cameras_list = response.get('cameraInfo', [])
    if cameras_list:
        for status_dict in cameras_list:
            if status_dict.get('status', 0):
                res['online'] += 1
            else:
                res['offline'] += 1

    return res


def get_alarm_num(camera_list, cursor, current_begin_str):
    """获取当前楼层今日报警截图总数"""
    alarm_num = 0
    camera_tuple = tuple(camera_list)
    sql_str = f"""
    SELECT COUNT(t.id)
    FROM crAlarmScreenshot t
    WHERE t.alarmTime>='{current_begin_str}' AND t.cameraId in {camera_tuple};
    """
    cursor.execute(sql_str)
    alarm_data = cursor.fetchone()
    if alarm_data:
        alarm_num = alarm_data[0]

    return alarm_num


def get_all_floor_person(cursor):
    """获取整栋楼当前所有人数"""
    all_floor_num = 0
    # 先查出所有的楼层名
    sql_str = """
            SELECT DISTINCT t.floorName
            FROM crFloorPersonStatistics t;
            """
    cursor.execute(sql_str)
    floors = cursor.fetchall()  # (('楼层1',), ..., ('楼层9',))
    # 查询每层楼最新的数据
    for i in floors:
        floor_name = i[0]
        sql_str = f"""
                SELECT t.personNum
                FROM crFloorPersonStatistics t
                WHERE t.floorName='{floor_name}'
                ORDER BY t.recordTime DESC
                LIMIT 1;
                """
        cursor.execute(sql_str)
        floor_data = cursor.fetchone()
        if floor_data:
            floor_num = floor_data[0]
            all_floor_num += floor_num

    return all_floor_num


def get_person_num_statistics(cursor):
    """获取楼层实时人数"""
    hour_minute_list, split_time_strp_list = get_split_time_info()
    x_axis_data = hour_minute_list
    series_data = [0, ]
    for i in range(len(split_time_strp_list)):
        num = 0
        if i < len(split_time_strp_list) - 1:
            sql_str = f"""
            SELECT t.personNum
            FROM crFloorPersonStatistics t
            WHERE t.recordTime>='{split_time_strp_list[i]}' and t.recordTime<'{split_time_strp_list[i + 1]}'
            """
            cursor.execute(sql_str)
            floor_data = cursor.fetchall()
            if floor_data:
                for i in floor_data:
                    num += i[0]
        series_data.append(num)

    return {'xAxisData': x_axis_data, 'seriesData': series_data}


def get_crowd_flow_statistics(cursor):
    """获取实时人员流量、人脸统计"""
    res = {'face': 0, 'in': 0, 'out': 0, 'charts': {}}
    current_time = datetime.now()
    last_minute_time = datetime.now() + timedelta(minutes=-1)
    # 查询最新一分钟内人脸统计数量
    sql_str = f"""
    SELECT COUNT(t.id) as face_num
    FROM crFacePassRecord t
    WHERE t.passTime BETWEEN '{last_minute_time}' AND '{current_time}';
    """
    cursor.execute(sql_str)
    face_data = cursor.fetchone()
    if face_data:
        res['face'] = face_data[0]
    # 查询最新一分钟内人员进入/离开数量
    sql_str = f"""
    SELECT t.passNum, t.passType
    FROM crCrowdFlowStatistics t
    WHERE t.passTime BETWEEN '{last_minute_time}' AND '{current_time}';
    """
    cursor.execute(sql_str)
    flow_data = cursor.fetchall()
    if flow_data:
        for flow_obj in flow_data:
            if flow_obj[1] == 1:
                res['in'] += flow_obj[0]
            else:
                res['out'] += flow_obj[0]
    # 人员流量统计
    hour_minute_list, split_time_strp_list = get_split_time_info()
    legend_data = ['人脸', '进入', '离开']
    x_axis_data = hour_minute_list
    series_data = [[0, ], [0, ], [0, ]]  # 三个列表, 分别代表人脸统计、人员进入、人员离开三个模块各个时间段的数量
    for i in range(len(split_time_strp_list)):
        # 人脸数量统计
        if i < len(split_time_strp_list) - 1:
            sql_str = f"""
            SELECT COUNT(t.id) as face_num
            FROM crFacePassRecord t
            WHERE t.passTime>='{split_time_strp_list[i]}' AND t.passTime<'{split_time_strp_list[i + 1]}';
            """
            cursor.execute(sql_str)
            face_data = cursor.fetchone()
            if face_data:
                series_data[0].append(face_data[0])
            # 人员进入数量统计
            flow_in_num = 0
            flow_out_num = 0
            sql_str = f"""
            SELECT t.passNum, t.passType
            FROM crCrowdFlowStatistics t
            WHERE t.passTime>='{split_time_strp_list[i]}' AND t.passTime<'{split_time_strp_list[i + 1]}';
            """
            cursor.execute(sql_str)
            flow_data = cursor.fetchall()
            if flow_data:
                for flow_obj in flow_data:
                    if flow_obj[1] == 1:
                        flow_in_num += flow_obj[0]
                    else:
                        flow_out_num += flow_obj[0]
            series_data[1].append(flow_in_num)
            series_data[2].append(flow_out_num)

    res['charts']['legendData'] = legend_data
    res['charts']['xAxisData'] = x_axis_data
    res['charts']['seriesData'] = series_data

    return res


def get_device_status(cursor, redis_conn):
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
    # 查询整栋楼人脸Pad、人流监控设备在线离线数量
    face_flow_companies = get_face_flow_companies('allStatusCount', redis_conn)
    ret['face']['online'] = face_flow_companies['faceOnline']
    ret['face']['total'] = face_flow_companies['faceOnline'] + face_flow_companies['faceOffline']
    ret['flow']['online'] = face_flow_companies['flowOnline']
    ret['flow']['total'] = face_flow_companies['flowOnline'] + face_flow_companies['flowOffline']
    # 查询整栋楼点位在线离线状态
    camera_list = get_camera_list('all', cursor)
    res = get_status_count(camera_list, redis_conn)
    ret['camera']['online'] = res['online']
    ret['camera']['total'] = res['offline'] + res['online']

    return ret


def get_algo_dict(redis_conn):
    """获取报警ID与报警类型名的对应关系"""
    id_name_dict = dict()
    name_id_dict = dict()
    algo_config = redis_conn.get(ServerConfig.algo_key)
    if algo_config:
        algo_config = json.loads(algo_config)
        for config_dict in algo_config:
            id_name_dict[config_dict['task_key']] = config_dict['name']
            name_id_dict[config_dict['name']] = config_dict['task_key']

    return id_name_dict, name_id_dict


def get_alarm_statistics(cursor, redis_conn):
    """获取7天AI报警统计"""
    res = {
        'legendData': [],
        'xAxisData': [],
        'seriesData': []
    }
    camera_list = get_camera_list('all', cursor)
    six_days_ago = get_day_begin_end(-6)[0]
    # 7天日期集合
    res['xAxisData'] = [
        get_day_begin_end(-6)[6], get_day_begin_end(-5)[6], get_day_begin_end(-4)[6], get_day_begin_end(-3)[6],
        get_day_begin_end(-2)[6], get_day_begin_end(-1)[6], get_day_begin_end(0)[6]
    ]
    # 7天内整栋楼的算法名称集合
    res['legendData'] = list()
    sql_str = ''
    if camera_list and len(camera_list) == 1:
        sql_str = f"""
        SELECT DISTINCT t.alarmType
        FROM crAlarmScreenshot t
        WHERE t.cameraId={camera_list[0]} AND t.alarmTime>='{six_days_ago}'
        GROUP BY t.createdDay;
        """
    if camera_list and len(camera_list) > 1:
        sql_str = f"""
        SELECT DISTINCT t.alarmType
        FROM crAlarmScreenshot t
        WHERE t.cameraId in {tuple(camera_list)} AND t.createdDay>='{six_days_ago}';
        """
    if sql_str:
        cursor.execute(sql_str)
        types = cursor.fetchall()
        if types:
            alarm_type_list = [i[0] for i in types]
            for alarm_type in alarm_type_list:
                alarm_days_count = [0, 0, 0, 0, 0, 0, 0]  # 长度与 x_coordinate 的一样
                alarm_type_name = get_algo_dict(redis_conn)[0].get(alarm_type, '')
                if alarm_type_name:
                    res['legendData'].append(alarm_type_name)
                    sql_str = f"""
                    SELECT t.createdDay, COUNT(t.id) as screenshot_num
                    FROM crAlarmScreenshot t
                    WHERE t.alarmType={alarm_type} AND t.alarmTime>='{six_days_ago}'
                    GROUP BY t.createdDay;
                    """
                    cursor.execute(sql_str)
                    type_count = cursor.fetchall()
                    if type_count:
                        for day_type in type_count:
                            if day_type[0]:
                                created_day_str = day_type[0].strftime('%Y-%m-%d')
                                for day_index in range(len(res['xAxisData'])):
                                    if created_day_str == res['xAxisData'][day_index]:
                                        alarm_days_count[day_index] = day_type[1]
                    res['seriesData'].append(alarm_days_count)

    return res


def push_event_record(cursor, redis_conn, socketio):
    """获取事件日志"""
    # 使用 UNION 将三个表的数据联合, 按截图时间排序, 查询最新的1条数据
    sql_str = """
    SELECT * FROM (
        SELECT id, alarmTime AS record_time FROM crAlarmScreenshot
        UNION (SELECT id, passTime AS record_time FROM crFacePassRecord)
        UNION (SELECT id, passTime AS record_time FROM crCrowdFlowStatistics)
    ) 
    AS alldata
    ORDER BY record_time DESC 
    LIMIT 1;
    """
    cursor.execute(sql_str)
    data_obj = cursor.fetchone()
    if data_obj:
        global event_record
        id = data_obj[0]
        record_time = data_obj[1]
        # 判断是否是报警截图表的数据
        sql_str = f"""
        SELECT t.id, t.cameraId, t.alarmType, t.alarmTime
        FROM crAlarmScreenshot t
        WHERE t.id={id} AND t.alarmTime='{record_time}'
        LIMIT 1;
        """
        cursor.execute(sql_str)
        alarm_obj = cursor.fetchone()
        if alarm_obj:
            floor_name_list = get_floor_name(alarm_obj[1], cursor)
            alarm_name = get_algo_dict(redis_conn)[0].get(alarm_obj[2], '')
            for floor_name in floor_name_list:
                res = {
                    'id': alarm_obj[0],
                    'date': alarm_obj[3].strftime('%Y-%m-%d %H:%M:%S') if alarm_obj[3] else '',
                    'area': floor_name,
                    'type': 'AI报警',
                    'isAlarm': True,
                    'detail': alarm_name
                }
                if res != event_record:
                    event_record = res
                    d = {'eventType': 'logs', 'data': event_record}
                    # print(f'>>>>>>> 开始推送整栋楼事件日志数据：{d} <<<<<<<<')
                    # socketio.emit('my_response', {'data': json.dumps(d)}, namespace='/test_conn')
                    socketio.emit('my_response', {'data': json.dumps(d)})
            return
        # 判断是否是人脸Pad表的数据
        sql_str = f"""
        SELECT t.id, t.passTime, t.floorName
        FROM crFacePassRecord t
        WHERE t.id={id} AND t.passTime='{record_time}'
        LIMIT 1;
        """
        cursor.execute(sql_str)
        face_obj = cursor.fetchone()
        if face_obj:
            res = {
                'id': face_obj[0],
                'date': face_obj[1].strftime('%Y-%m-%d %H:%M:%S') if face_obj[1] else '',
                'area': face_obj[2],
                'type': '人脸',
                'isAlarm': False,
                'detail': '刷脸进入'
            }
            if res != event_record:
                event_record = res
                d = {'eventType': 'logs', 'data': event_record}
                # print(f'>>>>>>> 开始推送整栋楼事件日志数据：{d} <<<<<<<<')
                # socketio.emit('my_response', {'data': json.dumps(d)}, namespace='/test_conn')
                socketio.emit('my_response', {'data': json.dumps(d)})
            return
        # 判断是否是人流统计表的数据
        sql_str = f"""
        SELECT t.id, t.floorName, t.passType, t.passTime, t.passNum
        FROM crCrowdFlowStatistics t
        WHERE t.id={id} AND t.passTime='{record_time}'
        LIMIT 1;
        """
        cursor.execute(sql_str)
        flow_obj = cursor.fetchone()
        if flow_obj:
            detail_info = ''
            id_type_dict = {0: '离开', 1: '进入'}
            pass_type_name = id_type_dict.get(flow_obj[2]) if flow_obj[2] else ''
            if pass_type_name and flow_obj[4]:
                detail_info = f'{pass_type_name} {flow_obj[4]} 人'
            res = {
                'id': flow_obj[0],
                'date': flow_obj[3].strftime('%Y-%m-%d %H:%M:%S') if flow_obj[3] else '',
                'area': flow_obj[1],
                'type': '流量计',
                'isAlarm': False,
                'detail': detail_info
            }
            if res != event_record:
                event_record = res
                d = {'eventType': 'logs', 'data': event_record}
                # print(f'>>>>>>> 开始推送整栋楼事件日志数据：{d} <<<<<<<<')
                # socketio.emit('my_response', {'data': json.dumps(d)}, namespace='/test_conn')
                socketio.emit('my_response', {'data': json.dumps(d)})
            return


def push_alarm_data(cursor, redis_conn, socketio):
    sql_str = """
            SELECT t.id, t.cameraId, t.alarmType, t.alarmTime, t.pictureUrl
            FROM crAlarmScreenshot t
            ORDER BY id DESC
            LIMIT 10;
            """
    cursor.execute(sql_str)
    alarms = cursor.fetchall()

    global exists_id_list
    if alarms:
        access_key = get_access_key(redis_conn)
        for alarm_obj in alarms:
            if alarm_obj[0] not in exists_id_list:
                # 报警时间
                alarm_time = alarm_obj[3]
                alarm_time_str = alarm_time.strftime('%Y-%m-%d %H:%M:%S')
                current_time = datetime.now()
                current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
                # if (current_time - alarm_time).seconds <= 30:
                # print(f'当前时间：{current_time_str}')
                # print(f'数据获取时间：{alarm_time_str}')
                # 点位ID
                camera_id = alarm_obj[1]
                # 点位名称
                camera_name = ''
                json_camera_name = redis_conn.get(camera_id)
                if json_camera_name:
                    camera_name = json_camera_name.decode()
                # 点位可播放地址
                camera_url = get_camera_url(camera_id, access_key, exists_url_dict, redis_conn)
                # 报警截图URL
                picture_url = ''
                picture = alarm_obj[-1] if alarm_obj[-1] else '',
                if picture:
                    picture_url = f'{ServerConfig.root_host}{picture[0]}'
                # 推送数据集合
                alarm_d = {
                    "id": alarm_obj[0],
                    "cameraId": camera_id,
                    "cameraName": camera_name,
                    "cameraUrl": camera_url,
                    "alarmType": alarm_obj[2] if alarm_obj[2] else '',
                    "alarmName": get_alarm_name(redis_conn).get(alarm_obj[2], '') if alarm_obj[2] else '',
                    "alarmTime": alarm_time_str,
                    "picture": picture_url
                }
                d = {'eventType': 'alarm', 'data': alarm_d}
                # print(f'>>>>>>> 开始推送整栋楼报警截图数据：{d} <<<<<<<<')
                # socketio.emit('my_response', {'data': json.dumps(d)}, namespace='/test_conn')
                socketio.emit('my_response', {'data': json.dumps(d)})
                exists_id_list.append(alarm_obj[0])

    print(f'已发送过的ID列表：{exists_id_list}')
    if len(exists_id_list) > 50:
        exists_id_list = exists_id_list[30:]
