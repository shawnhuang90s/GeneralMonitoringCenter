# -*- coding:utf-8 -*-
import json
import random
from flask import Flask
from loguru import logger
from config import ServerConfig
from utils.redis_tool import RedisConn
from datetime import datetime, timedelta
from flask_apscheduler import APScheduler
from utils.log_tool import task_scheduler_log
from utils.interface_tool import get_crip_data, get_latest_access_key

logger.add(task_scheduler_log,
           format="{time:%Y-%m-%d %H:%M:%S} | {module}.py func_name[{function}] line[{line}] | {level} | {message}",
           level='INFO', retention='7 days')


class Config():
    SCHEDULER_API_ENABLED = True


scheduler = APScheduler()


@scheduler.task('cron', id='update_algo_config', day='*', hour='*', minute=30, second=0, next_run_time=datetime.now())
def update_algo_config():
    """每半小时调用推理平台接口更新算法配置信息"""
    logger.info('>>>>>>>> 更新算法配置定时任务开启 <<<<<<<<')
    # user_obj = token_auth()
    # open_id = user_obj.openId
    # path = f'api/openapi/algorithm?openId={open_id}'
    path = 'api/openapi/algorithm'
    access_key = RedisConn.get_access_key()
    ret = get_crip_data(path, accessKey=access_key)
    new_access_key = get_latest_access_key(access_key, ret)
    # 如果 accessKey 更新了, 则所有涉及 accessKey 调用推理平台的接口都要重新调用
    if new_access_key != access_key:
        logger.error(f'>>>>>>>> accessKey 已更新 <<<<<<<<')
        ret = get_crip_data(path, accessKey=new_access_key)
    algo_config = ret.get('algoConfig', [])
    if algo_config:
        RedisConn.redis_db.set(ServerConfig.algo_key, json.dumps(algo_config))
    logger.info('>>>>>>>> 更新算法配置定时任务结束 <<<<<<<<')


@scheduler.task('cron', id='update_screen_shot', day='*', hour='*', minute='*', second=30, next_run_time=datetime.now())
def update_screen_shot():
    """模拟数据, 定时批量插入报警截图数据"""
    logger.info('>>>>>>>> 开始模拟推送数据 <<<<<<<<')
    from model.crris_model import AlarmScreenshot, CrowdFlowStatistics, FacePassRecord, FloorPersonStatistics
    user_type = ['普通用户', '黑名单']
    camera_list = [14, 15, 16, 30, 32, 14, 15, 16, 30, 32]
    alarm_type_list = [0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 12, 13, 14, 16, 19, 20, 21, 23]
    floor_num_list = [1, 2, 3, 4, 5, 6, 7, 9, 10, 12, 13, 14, 16, 19, 20, 21, 23, 24, 25]
    current_day_str = datetime.now().strftime('%Y-%m-%d')
    current_day = datetime.strptime(current_day_str, '%Y-%m-%d')
    picture_url = 'picture/alarm_picture/test.jpg'
    for i in range(10):
        random.shuffle(alarm_type_list)
        random.shuffle(floor_num_list)
        import time
        time.sleep(1)
        new_alarm_obj = AlarmScreenshot()
        new_alarm_obj.cameraId = camera_list[i]
        # print(f'打乱顺序后的列表：{alarm_type_list}')
        new_alarm_obj.alarmType = alarm_type_list[i]
        # new_alarm_obj.alarmTime = datetime.now() + timedelta(hours=-i)
        new_alarm_obj.alarmTime = datetime.now()
        new_alarm_obj.createdDay = current_day
        new_alarm_obj.pictureUrl = picture_url
        new_alarm_obj.save()

        new_flow_obj = CrowdFlowStatistics()
        new_flow_obj.deviceId = f'{i + 1}'
        new_flow_obj.deviceName = f'测试设备{i}'
        new_flow_obj.floorName = f'{floor_num_list[0]}F'
        new_flow_obj.floorNum = floor_num_list[0]
        new_flow_obj.passType = random.randint(0, 1)
        new_flow_obj.passNum = random.randint(1, 100)
        # new_flow_obj.passTime = datetime.now() + timedelta(hours=-i)
        new_flow_obj.passTime = datetime.now()
        new_flow_obj.createdDay = current_day
        new_flow_obj.pictureUrl = picture_url
        new_flow_obj.save()

        new_face_obj = FacePassRecord()
        new_face_obj.deviceId = f'{i + 1}'
        new_face_obj.deviceName = f'测试设备{i}'
        new_face_obj.floorName = f'{floor_num_list[1]}F'
        new_face_obj.floorNum = floor_num_list[1]
        new_face_obj.userId = f'{i + 1}'
        new_face_obj.userName = f'测试用户{i}'
        new_face_obj.userType = user_type[i % 2]
        # new_face_obj.passTime = datetime.now() + timedelta(hours=-i)
        new_face_obj.passTime = datetime.now()
        new_face_obj.createdDay = current_day
        new_face_obj.pictureUrl = picture_url
        new_face_obj.save()

        new_floor_obj = FloorPersonStatistics()
        new_floor_obj.floorName = f'{floor_num_list[2]}F'
        new_floor_obj.floorNum = floor_num_list[2]
        new_floor_obj.personNum = random.randint(1, 100)
        # new_floor_obj.recordTime = datetime.now() + timedelta(hours=-i)
        new_floor_obj.recordTime = datetime.now()
        new_floor_obj.createdDay = current_day
        new_floor_obj.save()

    e_dict = {
        'faceOnline': 10*random.randint(0, 5), 'faceOffline': 10*random.randint(0, 5),
        'flowOnline': 10*random.randint(0, 5), 'flowOffline': 10*random.randint(0, 5),
        'companies': 2*random.randint(1, 5)
    }
    device_status_dict = {}
    for i in range(0, 26):
        if i == 0:
            device_status_dict['allStatusCount'] = e_dict
        else:
            device_status_dict[str(i)] = e_dict
    RedisConn.set_face_flow_companies(device_status_dict)

    logger.info('>>>>>>>> 模拟成功 <<<<<<<<')


if __name__ == '__main__':
    app = Flask(__name__)
    app.config.from_object(Config())
    scheduler.init_app(app)
    scheduler.start()
    app.run(port=8000)