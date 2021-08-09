# -*- coding:utf-8 -*-
from utils.router_tool import CrBlueprint
from utils.login_tool import login_require
from utils.interface_tool import get_bayes_data
from view.floor_record_view import get_floor_person_data
from view.flow_record_view import query_crowd_flow_record, export_flow_record, get_flow_data
from view.system_config_view import save_access, apply_access, get_system_name, set_system_name, get_logo
from view.face_record_view import query_face_pass_record, export_face_record, get_face_data, get_user_types
from view.alarm_record_view import query_alarm_record, export_alarm_record, get_alarm_data, get_alarm_types
from view.home_view import get_push_url, get_floor_person_num, get_person_num_statistics, get_crowd_flow_statistics, \
    get_device_status, get_alarm_statistics, get_event_record, get_record_screenshot, get_companies_screenshots, \
    get_algo_config
from view.area_config_view import query_area_config, upload_file, add_area_name, update_area_name, update_area_config, \
    remove_area_config, get_camera_group, get_sub_camera, login, get_crip_host, open_camera, close_camera, sort_area, \
    user_info, area_user_config, get_user_open_id, area_camera_status_count, all_camera_status_count

bp = CrBlueprint('crris', __name__)

bp.route('/query_area_info', methods=['GET'])(login_require()(query_area_config))  # 查看监控区域配置信息
bp.route('/upload', methods=['POST'])(login_require()(upload_file))  # 上传文件
bp.route('/add_area_name', methods=['POST'])(login_require()(add_area_name))  # 新增监控区域名
bp.route('/update_area_name', methods=['POST'])(login_require()(update_area_name))  # 更新监控区域名
bp.route('/update_area_config', methods=['POST'])(login_require()(update_area_config))  # 新增/更新监控区域配置信息
bp.route('/remove_area_config', methods=['POST'])(login_require()(remove_area_config))  # 删除某个区域及关联的配置信息和文件等
bp.route('/save_access', methods=['POST'])(login_require()(save_access))  # 申请授权信息
bp.route('/apply_access', methods=['POST'])(login_require()(apply_access))  # 保存授权信息
bp.route('/get_camera_group', methods=['GET'])(login_require()(get_camera_group))  # 获取摄像头组树
bp.route('/get_sub_camera', methods=['GET'])(login_require()(get_sub_camera))  # 获取节点下的摄像头信息
bp.route('/open_camera', methods=['GET'])(login_require()(open_camera))  # 获取某个点位的可播放地址
bp.route('/close_camera', methods=['GET'])(login_require()(close_camera))  # 关闭某个点位的可播放地址
bp.route('/login', methods=['POST'])(login)  # 跳转登录
bp.route('/get_crip_host', methods=['GET'])(get_crip_host)  # 前端获取推理平台IP和PORT
bp.route('/get_open_id', methods=['GET'])(get_user_open_id)  # 前端获取推理平台 open_id
bp.route('/query_alarm_record', methods=['POST'])(login_require()(query_alarm_record))  # 查询报警截图数据
bp.route('/get_alarm_types', methods=['GET'])(login_require()(get_alarm_types))  # 查询所有的算法名称
bp.route('/query_face_record', methods=['POST'])(login_require()(query_face_pass_record))  # 查询人脸通行记录
bp.route('/get_user_types', methods=['GET'])(login_require()(get_user_types))  # 查询用户类型
bp.route('/query_flow_record', methods=['POST'])(login_require()(query_crowd_flow_record))  # 查询人流统计记录
bp.route('/export_alarm_record', methods=['POST'])(login_require()(export_alarm_record))  # 导出报警截图数据
bp.route('/export_face_record', methods=['POST'])(login_require()(export_face_record))  # 导出人脸通行记录
bp.route('/export_flow_record', methods=['POST'])(login_require()(export_flow_record))  # 导出人流统计记录
bp.route('/get_system_name', methods=['GET'])(login_require()(get_system_name))  # 获取系统名称
bp.route('/set_system_name', methods=['POST'])(login_require()(set_system_name))  # 设置系统名称
bp.route('/sort_area', methods=['POST'])(login_require()(sort_area))  # 监控区域拖拽排序
bp.route('/user_info', methods=['GET'])(login_require()(user_info))  # 获取用户下拉列表
bp.route('/area_config', methods=['POST'])(login_require()(area_user_config))  # 区域管理员权限配置
bp.route('/get_algo_config', methods=['POST'])(login_require()(get_algo_config))  # 展示当前区域下所有点位关联的报警类型
bp.route('/area_camera_status', methods=['POST'])(login_require()(area_camera_status_count))  # 统计某个楼层点位在线离线数量
bp.route('/all_camera_status', methods=['GET'])(login_require()(all_camera_status_count))  # 统计整栋楼点位在线离线数量
bp.route('/get_logo', methods=['GET'])(get_logo)  # 获取 logo 图片
bp.route('/get_push_url', methods=['GET'])(get_push_url)  # 获取推送地址
bp.route('/get_floor_person', methods=['POST'])(login_require()(get_floor_person_num))  # 获取整栋楼/当前楼层人数
bp.route('/get_person_statistics', methods=['POST'])(login_require()(get_person_num_statistics))  # 获取楼层实时人数
bp.route('/get_flow_statistics', methods=['POST'])(login_require()(get_crowd_flow_statistics))  # 获取楼层实时进出人数
bp.route('/get_device_status', methods=['POST'])(login_require()(get_device_status))  # 获取设备状态
bp.route('/get_alarm_statistics', methods=['POST'])(login_require()(get_alarm_statistics))  # 获取7天AI报警统计
bp.route('/get_event_record', methods=['POST'])(login_require()(get_event_record))  # 获取事件日志
bp.route('/get_record_screenshot', methods=['POST'])(login_require()(get_record_screenshot))  # 获取报警截图
bp.route('/get_companies_screenshots', methods=['POST'])(login_require()(get_companies_screenshots))  # 获取当前楼层入驻企业数量、今日报警总数

bp.route('/get_alarm_data', methods=['POST'])(get_alarm_data)  # 获取推理平台推送的报警截图数据
bp.route('/get_face_data', methods=['POST'])(get_face_data)  # 获取贝叶斯推送的人脸记录数据
bp.route('/get_flow_data', methods=['POST'])(get_flow_data)  # 获取贝叶斯推送的人流统计数据
bp.route('/get_floor_person_data', methods=['POST'])(get_floor_person_data)  # 获取贝叶斯推送的楼层人数记录
bp.route('/get_bayes_data', methods=['POST'])(get_bayes_data)  # 获取贝叶斯推送的人脸Pad、人流监控设备在线离线数量及当前楼层入驻企业数
