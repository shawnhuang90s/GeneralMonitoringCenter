# -*- coding:utf-8 -*-
import os
import json
import datetime
from loguru import logger
from flask import request
from config import ServerConfig
from utils.redis_tool import RedisConn
from utils.file_tool import UploadFile
from utils.log_tool import area_config_view_log
from utils.login_tool import set_token_user, token_auth
from utils.permission_tool import operational_permission
from utils.interface_tool import get_crip_data, get_latest_access_key
from model.crris_model import AreaConfig, User, Permission, FloorPersonStatistics

logger.add(area_config_view_log,
           format="{time:%Y-%m-%d %H:%M:%S} | {module}.py func_name[{function}] line[{line}] | {level} | {message}",
           level='INFO', retention='7 days')
# TODO:如果设置了这个全局变量会报502错误, 则在需要它的时候再获取, 而不是这样写在一个方法内
ACCESS_KEY = RedisConn.get_access_key()


def upload_file():
    """
    文件上传
    type: 图片（picture）、音频（audio）、视频（video）等
    如果是上传区域图片, type: picture  value: 区域名
    如果是上传 logo, type: picture  value: logo
    目录结构示例：
    ├─files
    │  └─picture
    │      ├─5F&cat2.jpg
    │      ├─logo&cat2.jpg
    其中, & 作为分隔符方便获取左边的 value 和右边的文件名
    """
    file_obj = request.files.get('file') or None
    type = request.form.get('type') or None  # video：离线视频  picture：图片
    value = request.form.get('value') or None
    res = UploadFile.save_file(file_obj, type, value)

    return res


def query_area_config():
    """查看监控区域配置信息"""
    # 超管可以查看所有监控区域配置信息，其他用户只能查看超管给其分配的区域配置信息
    # user_obj = token_auth()
    # if user_obj.isSuperuser == 1:
    #     areas = AreaConfig.query().order_by(AreaConfig.areaNum.desc())
    # else:
    #     permissions = Permission.filter(Permission.user == user_obj, Permission.isViewable == 1)
    #     assert permissions, '您没有权限查看监控区域信息, 请联系管理员'
    #     area_id_list = [i.area.id for i in permissions]
    #     areas = AreaConfig.filter(AreaConfig.id << area_id_list).order_by(AreaConfig.areaNum.desc())
    areas = AreaConfig.query().order_by(AreaConfig.areaNum.desc())
    if not areas:
        return []

    # 获取整栋楼所有点位的状态
    camera_list = list()
    for area in areas:
        area_camera_list = json.loads(area.cameraList) if area.cameraList else []
        if area_camera_list:
            camera_list.extend(area_camera_list)
    camera_list = list(set(camera_list))
    id_status_dict = dict()
    # user_obj = token_auth()
    # open_id = user_obj.openId
    open_id = ''
    path = f'api/openapi/camera/status?openId={open_id}'
    data_dict = {'cameraList': camera_list}
    response = get_crip_data(path=path, method='POST', data_dict=data_dict, accessKey=ACCESS_KEY)
    new_access_key = get_latest_access_key(ACCESS_KEY, response)
    # 如果 accessKey 更新了, 则所有涉及 accessKey 调用推理平台的接口都要重新调用
    if new_access_key != ACCESS_KEY:
        logger.info(f'已过期的 AccesssKey 值：{ACCESS_KEY}')
        logger.info(f'获取的新 AccesssKey 值：{new_access_key}')
        response = get_crip_data(path=path, method='POST', data_dict=data_dict, accessKey=new_access_key)
    cameras_list = response.get('cameraInfo', [])
    if cameras_list:
        for id_status in cameras_list:
            id_status_dict[id_status['id']] = id_status['status']

    res = list()
    l = list(range(25, 0, -1))
    flag = 0
    for i in areas:
        area_name = i.areaName
        # 每个点位的配置信息
        camera_detail = dict()
        area_camera_list = json.loads(i.cameraList) if i.cameraList else []
        if area_camera_list:
            # 获取每个摄像头的点位配置信息
            for camera_id in area_camera_list:
                current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                camera_name = ''
                json_camera_name = RedisConn.redis_db.get(camera_id)
                if json_camera_name:
                    camera_name = json_camera_name.decode()
                camera_detail[camera_id] = {'cameraId': camera_id, 'points': [], 'cameraName': camera_name,
                                            'cameraStatus': id_status_dict.get(camera_id, 0), 'createdAt': current_time}
                relative_json_path = f'json/{area_name}&camera_{camera_id}.json'
                json_path = f'{ServerConfig.root_path}{relative_json_path}'
                if os.path.exists(json_path):
                    camera_detail[camera_id]['points'] = UploadFile.load_json_file(json_path)
        people_num = 0
        floor_obj = FloorPersonStatistics.filter(FloorPersonStatistics.floorName == area_name).order_by(
            FloorPersonStatistics.recordTime.desc()).first()
        if floor_obj:
            people_num = floor_obj.personNum
        # 如果某个楼层在配置页面删掉了, 则这里返回给前端时也要返回楼层信息, 包括楼层名(固定格式:"产研大楼n层"), ID(默认为0), 第几层
        if l[flag] > i.areaNum:
            area_obj = dict(
                id=0,
                name=f'产研大楼{l[flag]}层',
                cameraDict={},
                pictureUrl='',
                floor=l[flag],
                peopleNum=0
            )
            l.remove(l[flag])
            res.append(area_obj)
        area_obj = dict(
            id=i.id,
            name=i.areaName,
            cameraDict=camera_detail,
            pictureUrl=i.pictureUrl,
            floor=i.areaNum,
            peopleNum=people_num
        )
        flag += 1
        res.append(area_obj)

    return res


def add_area_name():
    """新增一个区域名"""
    # user_obj = token_auth()
    # assert user_obj.isSuperuser == 1, '您没有权限执行此操作, 请联系管理员'
    params = request.get_json()
    area_name = params.get('name', '')
    area_num = params.get('floor', 0)
    assert area_num, '缺少必要参数：floor'
    assert area_name, f'区域名为空'
    exists_obj = AreaConfig.filter(AreaConfig.areaNum == area_num).first()
    assert not exists_obj, '当前楼层已存在'
    new_area_obj = AreaConfig()
    new_area_obj.areaName = area_name
    new_area_obj.areaNum = area_num
    new_area_obj.save()

    return {
        'id': new_area_obj.id
    }


@operational_permission
def update_area_name():
    """更新监控区域名"""
    params = request.get_json()
    area_id = params.get('id', -100)
    area_name = params.get('name', '')
    area_num = params.get('floor', 0)
    area_obj = AreaConfig.filter(AreaConfig.id == area_id).first()
    assert area_obj, f'区域配置表中 ID={area_id} 的数据不存在'
    area_obj.areaName = area_name
    area_obj.areaNum = area_num
    area_obj.save()

    return {'msg': '编辑成功'}


@operational_permission
def update_area_config():
    """新增/更新监控区域配置信息"""
    params = request.get_json()
    area_id = params.get('id', '')
    assert area_id, f'缺少必要的参数：区域ID'
    area_obj = AreaConfig.filter(AreaConfig.id == area_id).first()
    assert area_obj, f'数据不存在'
    picture_url = params.get('pictureUrl', '')
    camera_dict = params.get('cameraDict', {})

    camera_list = list()
    if camera_dict:
        area_name = area_obj.areaName
        relative_json_path = f'json/'
        new_json_path = f'{ServerConfig.root_path}{relative_json_path}'
        UploadFile.create_dirs(new_json_path)

        for camera_id_str, point_dict in camera_dict.items():
            camera_id = point_dict.get('cameraId', 0)
            camera_name = point_dict.get('cameraName', '')
            # 把对应的点位ID和点位名称保存到 Redis 中
            RedisConn.redis_db.set(camera_id, camera_name)
            camera_list.append(camera_id)
            # 保存点位信息
            point_list = point_dict.get('points', [])
            new_json_path = f'{ServerConfig.root_path}{relative_json_path}{area_name}&camera_{camera_id}.json'
            UploadFile.dump_json_file(new_json_path, point_list)

    area_obj.pictureUrl = picture_url
    area_obj.cameraList = json.dumps(camera_list)
    area_obj.save()

    return {'msg': '更新区域配置信息成功'}


@operational_permission
def remove_area_config():
    """删除某个楼层及关联的配置信息和文件等"""
    params = request.get_json()
    area_id = params.get('id', 0)
    assert area_id, f'缺少必要的参数：区域ID'
    area_obj = AreaConfig.filter(AreaConfig.id == area_id).first()
    floor = area_obj.areaNum
    assert area_obj, f'区域配置表中 ID={area_id} 的数据不存在'
    area_obj.delete_instance()
    areas = AreaConfig.select()
    if areas:
        for i in areas:
            if i.areaNum > floor:
                i.areaNum -= 1
                i.save()
    # 删除该楼层对应的 JSON 文件和图片等
    area_name = area_obj.areaName
    relative_json_path = f'json/'
    area_camera_list = json.loads(area_obj.cameraList) if area_obj.cameraList else []
    if area_camera_list:
        for camera_id in area_camera_list:
            exists_json_path = f'{ServerConfig.root_path}{relative_json_path}{area_name}&camera_{camera_id}.json'
            if os.path.exists(exists_json_path):
                os.remove(exists_json_path)
    exists_picture_path = f'{ServerConfig.root_path}{area_obj.pictureUrl}'
    if os.path.exists(exists_picture_path):
        os.remove(exists_picture_path)

    return {'msg': '删除成功'}


@operational_permission
def sort_area():
    """区域配置页面区域拖拽排序"""
    # user_obj = token_auth()
    # assert user_obj.isSuperuser == 1, '您没有权限执行此操作, 请联系管理员'
    params = request.get_json()
    id_floor_list = params.get('idFloorList', [])
    assert id_floor_list, '缺少必要参数：idFloor'
    for d in id_floor_list:
        id = d['id']
        area_num = d['floor']
        area_obj = AreaConfig.filter(AreaConfig.id == id).first()
        if not area_obj: continue
        area_obj.areaNum = area_num
        area_obj.save()

    return {'msg': '拖拽排序成功'}


def user_info():
    """用户下拉列表"""
    # user_obj = token_auth()
    # assert user_obj.isSuperuser == 1, '您没有权限执行此操作, 请联系管理员'
    res = list()
    users = User.query()
    if not users:
        return res
    for user_obj in users:
        res.append({'username': user_obj.username, 'id': user_obj.id})

    return res


def area_user_config():
    """区域管理员权限配置"""
    # user_obj = token_auth()
    # assert user_obj.isSuperuser == 1, '您没有权限执行此操作, 请联系管理员'
    params = request.get_json()
    area_id = params.get('areaId', 0)
    assert area_id, '请选择对应的区域ID'
    area_obj = AreaConfig.filter(AreaConfig.id == area_id).first()
    assert area_obj, '区域信息不存在'
    # 目前暂时决定选中的用户查看、操作权限都有
    is_operational = params.get('isOperational', 1)
    is_viewable = params.get('isViewable', 1)
    user_list = params.get('userList', [])
    area_users = User.filter(User.id << user_list)
    for area_user in area_users:
        permission_obj = Permission.filter(Permission.user == area_user, Permission.area == area_obj).first()
        if permission_obj:
            permission_obj.isOperational = is_operational
            permission_obj.isViewable = is_viewable
            permission_obj.save()
        else:
            new_obj = Permission()
            new_obj.user = area_user
            new_obj.area = area_obj
            new_obj.isOperational = is_operational
            new_obj.isViewable = is_viewable
            new_obj.save()

    return {'msg': '权限分配成功'}


def get_camera_group():
    """获取摄像头组树"""
    # user_obj = token_auth()
    # open_id = user_obj.openId
    open_id = ''
    path = f'api/openapi/camera/group?openId={open_id}'
    res = get_crip_data(path, accessKey=ACCESS_KEY)
    new_access_key = get_latest_access_key(ACCESS_KEY, res)
    # 如果 accessKey 更新了, 则所有涉及 accessKey 调用推理平台的接口都要重新调用
    if new_access_key != ACCESS_KEY:
        res = get_crip_data(path=path, accessKey=new_access_key)
    # path = 'api/device/camera/monitor'
    # res = call_interface_data(path)

    return res


def get_sub_camera():
    """单个摄像头详情"""
    page = request.args.get('page', 1)
    size = request.args.get('size', 20)
    partner_id = request.args.get('parentId', -1)
    # user_obj = token_auth()
    # open_id = user_obj.openId
    open_id = ''
    path = f'api/openapi/camera/group/sub?parentId={partner_id}&page={page}&size={size}&openId={open_id}'
    res = get_crip_data(path, accessKey=ACCESS_KEY)
    new_access_key = get_latest_access_key(ACCESS_KEY, res)
    # 如果 accessKey 更新了, 则所有涉及 accessKey 调用推理平台的接口都要重新调用
    if new_access_key != ACCESS_KEY:
        res = get_crip_data(path=path, accessKey=new_access_key)
    # path = f'api/device/camera/group/sub?parentId={partner_id}&page={page}&size={size}'
    # res = call_interface_data(path)

    return res


def login():
    """登录接口"""
    error_msg = '用户名或密码错误, 请重新输入'
    params = request.get_json()
    username = params.get('username', '')
    username = "".join(username.split(" "))
    password = params.get('password', '')
    password = "".join(password.split(" "))
    user_obj = User.filter(User.username == username).first()
    assert user_obj, error_msg
    assert user_obj.password == password, error_msg

    if username != 'root':
        open_id = user_obj.openId
        assert open_id, '登录出错, 请点击第三方登录'
    # 为每个用户自动生成一个 Token
    token = set_token_user(username)

    return {
        "name": username,
        "picture": "",
        ServerConfig.token_key: token,
    }


def get_crip_host():
    """前端获取推理平台的 IP 和端口"""
    url = ServerConfig.server_url
    assert ACCESS_KEY, '请先让超级管理员登录并进行 AccessKey 设置'
    access_url = f'{url}#/third/login?accessKey={ACCESS_KEY}'

    return access_url


def get_user_open_id():
    """根据前端传来的 code 获取 openId 并保存"""
    # user_obj = token_auth()
    code = request.args.get('code', '')
    assert code, '参数 code 值为空'
    # 根据 code 从推理平台获取当前用户的 openId
    path = 'api/openapi/third/code'
    data_dict = {'code': code}
    assert ACCESS_KEY, '请先让超级管理员登录并进行 AccessKey 设置'
    response = get_crip_data(path=path, method='POST', data_dict=data_dict,
                             accessKey=ACCESS_KEY)  # {'openId': open_id, 'userInfo': {}}
    new_access_key = get_latest_access_key(ACCESS_KEY, response)
    # 如果 accessKey 更新了, 则所有涉及 accessKey 调用推理平台的接口都要重新调用
    if new_access_key != ACCESS_KEY:
        response = get_crip_data(path=path, method='POST', data_dict=data_dict, accessKey=new_access_key)
    assert response.get('openId', ''), response.get('errorMsg', '')
    # 获取 openId 意味着要新建一个用户
    assert response.get('userInfo', {}), '为获取到用户信息'
    assert response['userInfo'].get('name', ''), '未获取到用户名'
    open_id = response['openId']
    user_obj = User.filter(User.username == response['userInfo']['name']).first()
    if user_obj:
        user_obj.openId = open_id
        user_obj.save()
    else:
        new_user = User()
        new_user.openId = open_id
        new_user.username = response['userInfo']['name']
        new_user.password = '123456'
        new_user.save()

    token = set_token_user(response['userInfo']['name'])

    return {
        'name': response['userInfo']['name'],
        'picture': '',
        ServerConfig.token_key: token
    }


def open_camera():
    """获取某个点位的可播放地址"""
    camera_id = request.args.get('cameraId', -100)
    assert camera_id != -100, '缺少必要的参数：点位ID'
    # user_obj = token_auth()
    # open_id = user_obj.openId
    open_id = ''
    path = f'api/openapi/camera/stream?cameraId={camera_id}&openId={open_id}'
    ret = get_crip_data(path=path, accessKey=ACCESS_KEY)
    new_access_key = get_latest_access_key(ACCESS_KEY, ret)
    # 如果 accessKey 更新了, 则所有涉及 accessKey 调用推理平台的接口都要重新调用
    if new_access_key != ACCESS_KEY:
        ret = get_crip_data(path=path, accessKey=new_access_key)
    # ret = {'url': 'http://192.168.0.101:9012/video?port=1935&app=video&stream=20210615111313ExGAvldxZ0'}
    assert not ret.get('errorMsg', ''), ret.get('errorMsg', '')

    return ret


def close_camera():
    """关闭某个摄像头播放流地址"""
    camera_id = request.args.get('cameraId', -100)
    assert camera_id != -100, '缺少必要的参数：点位ID'
    # user_obj = token_auth()
    # open_id = user_obj.openId
    open_id = ''
    path = f'api/openapi/camera/stream/close?cameraId={camera_id}&openId={open_id}'
    ret = get_crip_data(path=path, accessKey=ACCESS_KEY)
    new_access_key = get_latest_access_key(ACCESS_KEY, ret)
    # 如果 accessKey 更新了, 则所有涉及 accessKey 调用推理平台的接口都要重新调用
    if new_access_key != ACCESS_KEY:
        ret = get_crip_data(path=path, accessKey=new_access_key)
    # 调用的关闭摄像头接口成功时返回的数据为空, 因此这里这样判断
    if not ret:
        return {'msg': '已关闭该摄像头的播放流地址'}

    return ret


def get_area_cameras():
    """获取当前区域下的所有点位ID"""
    params = request.get_json()
    area_id = params.get('areaId', -100)
    assert area_id, '缺少必要的参数：区域ID'
    area_obj = AreaConfig.filter(AreaConfig.id == area_id).first()
    assert area_obj, '系统没有当前区域的信息'
    area_camera_list = json.loads(area_obj.cameraList) if area_obj.cameraList else []

    return area_camera_list


def get_status_count(camera_list):
    # 调用接口获取摄像头在线离线状态
    res = {'online': 0, 'offline': 0}
    # user_obj = token_auth()
    # open_id = user_obj.openId
    open_id = ''
    path = f'api/openapi/camera/status?openId={open_id}'
    data_dict = {'cameraList': camera_list}
    response = get_crip_data(path=path, method='POST', data_dict=data_dict, accessKey=ACCESS_KEY)
    new_access_key = get_latest_access_key(ACCESS_KEY, response)
    # 如果 accessKey 更新了, 则所有涉及 accessKey 调用推理平台的接口都要重新调用
    if new_access_key != ACCESS_KEY:
        response = get_crip_data(path=path, method='POST', data_dict=data_dict, accessKey=new_access_key)
    cameras_list = response.get('cameraInfo', [])
    if cameras_list:
        for status_dict in cameras_list:
            if status_dict.get('status', 0):
                res['online'] += 1
            else:
                res['offline'] += 1

    return res


def area_camera_status_count():
    """统计某个楼层点位在线离线数量"""
    area_camera_list = get_area_cameras()
    res = get_status_count(area_camera_list)

    return res


def all_camera_status_count():
    """获取整栋楼的所有点位在线离线状态数量"""
    camera_list = list()
    areas = AreaConfig.select()
    if areas:
        for area in areas:
            area_camera_list = json.loads(area.cameraList) if area.cameraList else []
            if area_camera_list:
                camera_list.extend(area_camera_list)
    camera_list = list(set(camera_list))
    res = get_status_count(camera_list)

    return res
