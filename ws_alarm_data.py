# -*- coding:utf-8 -*-
#!/usr/bin/env python
import json
from threading import Lock
from config import ServerConfig
from flask import Flask, render_template, request, copy_current_request_context
from flask_socketio import SocketIO, emit, join_room, leave_room, close_room, rooms, disconnect
from utils.websocket_tool import get_mysql_conn, get_redis_conn, get_all_floor_person, get_person_num_statistics, \
    get_crowd_flow_statistics, get_device_status, get_alarm_statistics, push_event_record, push_alarm_data

# 将此变量设置为 "threading"、"eventlet" 或 "gevent" 以测试不同的异步模式
# 或将其设置为 None 以便应用程序根据已安装的软件包选择最佳选项
async_mode = None
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode, cors_allowed_origins='*')
thread = None
thread_lock = Lock()
sid_list = list()
floor_num = 0  # 楼宇现有人员
people_flow = dict()  # 实时人员流量统计
crowd_flows = dict()  # 实时人员进出统计
device_status = dict()  # 设备状态
alarm_statistics = dict()  # 7天AI报警统计


def background_thread():
    """将服务器生成的事件发送到客户端"""
    global sid_list
    if sid_list:
        while True:
            socketio.sleep(1)
            # socketio.emit('my_response', {'data': 'The heartbeat continues...'}, namespace='/test_conn')
            # socketio.emit('my_response', {'data': 'The heartbeat continues...'})
            mysql_conn = get_mysql_conn()
            redis_conn = get_redis_conn()
            cursor = mysql_conn.cursor()
            # 报警截图
            push_alarm_data(cursor, redis_conn, socketio)
            # 楼宇现有人员
            global floor_num
            all_floor_num = get_all_floor_person(cursor)
            if all_floor_num != floor_num:
                floor_num = all_floor_num
                d = {'eventType': 'floorNum', 'data': {'num': floor_num}}
                # print(f'>>>>>>> 开始推送整栋楼实时人数：{d} <<<<<<<<')
                # socketio.emit('my_response', {'data': json.dumps(d)}, namespace='/test_conn')
                socketio.emit('my_response', {'data': json.dumps(d)})
            # 实时人员流量统计
            global people_flow
            person_num_statistics = get_person_num_statistics(cursor)
            if person_num_statistics != people_flow:
                people_flow = person_num_statistics
                d = {'eventType': 'peopleFlow', 'data': person_num_statistics}
                # print(f'>>>>>>> 开始推送整栋楼人流统计数据：{d} <<<<<<<<')
                # socketio.emit('my_response', {'data': json.dumps(d)}, namespace='/test_conn')
                socketio.emit('my_response', {'data': json.dumps(d)})
            # 实时人员进出统计
            global crowd_flows
            crowd_flow_statistics = get_crowd_flow_statistics(cursor)
            if crowd_flow_statistics != crowd_flows:
                crowd_flows = crowd_flow_statistics
                d = {'eventType': 'peopleInOut', 'data': crowd_flow_statistics}
                # print(f'>>>>>>> 开始推送整栋楼实时人员进出统计：{d} <<<<<<<<')
                # socketio.emit('my_response', {'data': json.dumps(d)}, namespace='/test_conn')
                socketio.emit('my_response', {'data': json.dumps(d)})
            # 设备状态
            global device_status
            devices_status = get_device_status(cursor, redis_conn)
            if devices_status != device_status:
                device_status = devices_status
                d = {'eventType': 'deviceStatus', 'data': devices_status}
                # print(f'>>>>>>> 开始推送整栋楼设备状态统计：{d} <<<<<<<<')
                # socketio.emit('my_response', {'data': json.dumps(d)}, namespace='/test_conn')
                socketio.emit('my_response', {'data': json.dumps(d)})
            # 7天AI报警统计
            global alarm_statistics
            alarms_statistics = get_alarm_statistics(cursor, redis_conn)
            if alarms_statistics != alarm_statistics:
                alarm_statistics = alarms_statistics
                d = {'eventType': 'alarmStatistics', 'data': alarms_statistics}
                # print(f'>>>>>>> 开始推送整栋楼7天AI报警统计：{d} <<<<<<<<')
                # socketio.emit('my_response', {'data': json.dumps(d)}, namespace='/test_conn')
                socketio.emit('my_response', {'data': json.dumps(d)})
            # 事件日志
            push_event_record(cursor, redis_conn, socketio)

            mysql_conn.close()
            redis_conn.close()


@app.route('/')
def index():
    return render_template('test01.html', async_mode=socketio.async_mode)


# @socketio.on('my_event', namespace='/test_conn')
@socketio.on('my_event')
def my_event(message):
    print('>>>>>>>> 单个事件处理 <<<<<<<<')
    print(f'接收到客户端传来的消息：{message}')
    # emit('my_response', {'data': message}, namespace='/test_conn')
    emit('my_response', {'data': json.dumps(message)})


@socketio.event
def my_broadcast_event(message):
    print('>>>>>>>> 广播事件处理 <<<<<<<<')
    emit('my_response', {'data': message['data']}, broadcast=True)


@socketio.event
def join(message):
    join_room(message['room'])
    emit('my_response', {'data': 'In rooms: ' + ', '.join(rooms())})


@socketio.event
def leave(message):
    leave_room(message['room'])
    emit('my_response', {'data': 'In rooms: ' + ', '.join(rooms())})


@socketio.on('close_room')
def on_close_room(message):
    emit('my_response', {'data': 'Room ' + message['room'] + ' is closing.'}, to=message['room'])
    close_room(message['room'])


@socketio.event
def my_room_event(message):
    emit('my_response', {'data': message['data']}, to=message['room'])


@socketio.event
def disconnect_request():
    """客户端主动点击‘关闭连接’按钮后, 会走这个函数"""
    @copy_current_request_context
    def can_disconnect():
        disconnect()
    # 使用回调函数确保消息已经收到, 断开连接是安全的
    emit('my_response', {'data': 'Disconnected!'}, callback=can_disconnect)
    print(f'>>>>>>>> 客户端：{request.sid} 已断开连接 <<<<<<<<')
    global sid_list
    if request.sid in sid_list:
        sid_list.remove(request.sid)
    if len(sid_list) > 0:
        print(f'>>>>>>>> 当前与服务端保持连接的客户端有：{sid_list}')


@socketio.event
def my_ping():
    emit('my_pong')


# @socketio.on('connect', namespace='/test_conn')
@socketio.on('connect')
def test_connect():
    print(f'>>>>>>>> 客户端：{request.sid} 已连接到服务端 <<<<<<<<')
    global sid_list
    sid_list.append(request.sid)
    print(f'>>>>>>>> 当前与服务端保存连接的客户端有：{sid_list}')
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)


# @socketio.on('disconnect', namespace='/test_conn')
@socketio.on('disconnect')
def test_disconnect():
    """客户端窗口关闭后, 会调用这个函数"""
    print(f'>>>>>>>> 客户端：{request.sid} 已断开连接 <<<<<<<<')
    global sid_list
    if request.sid in sid_list:
        sid_list.remove(request.sid)
    if len(sid_list) > 0:
        print(f'>>>>>>>> 当前与服务端保持连接的客户端有：{sid_list}')


if __name__ == '__main__':
    socketio.run(app, host=ServerConfig.ip, port=ServerConfig.socket_port, debug=True)
