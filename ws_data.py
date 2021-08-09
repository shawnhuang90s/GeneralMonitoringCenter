import json
import datetime
from config import ServerConfig
from gevent.pywsgi import WSGIServer
from utils.login_tool import token_auth
from bottle import request, Bottle, abort
from geventwebsocket import WebSocketError
from geventwebsocket.handler import WebSocketHandler
from utils.websocket_tool import get_redis_conn, get_mysql_conn, get_camera_url, get_access_key, get_alarm_name

app = Bottle()
exists_url_dict = dict()


@app.get('/alarm')
def handle_websocket():
    exists_id_list = list()
    ws = request.environ.get('wsgi.websocket')
    print(f'当前链接对象：{ws}')
    # users.add(ws)
    if not ws:
        abort(400, 'Expected WebSocket request.')
    while True:
        print('***********************************')
        try:
            # TODO:前端心跳机制每秒跳动一次
            message = ws.receive()
        except WebSocketError:
            break
        # print("现有连接用户：%s" % (len(users)))
        print(message)
        # for user in users:
        try:
            if message:
                ws.send(message)

            redis_conn = get_redis_conn()
            mysql_conn = get_mysql_conn()
            cursor = mysql_conn.cursor()
            sql_str = """
            SELECT t.id, t.cameraId, t.alarmType, t.alarmTime, t.pictureUrl
            FROM crAlarmScreenshot t
            ORDER BY id DESC 
            LIMIT 10;
            """
            cursor.execute(sql_str)
            alarms = cursor.fetchall()

            if alarms:
                access_key = get_access_key(redis_conn)
                for alarm_obj in alarms:
                    if alarm_obj[0] not in exists_id_list:
                        # 报警时间
                        alarm_time = alarm_obj[3]
                        alarm_time_str = alarm_time.strftime('%Y-%m-%d %H:%M:%S')
                        current_time = datetime.datetime.now()
                        current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
                        # current_begin_str = current_time.strftime('%Y-%m-%d 00:00:00')
                        print(f'当前时间：{current_time_str}')
                        print(f'保存截图时间：{alarm_time_str}')
                        if (current_time - alarm_time).seconds <= 30:
                            # 点位ID
                            camera_id = alarm_obj[1]
                            # 点位名称
                            camera_name = ''
                            json_camera_name = redis_conn.get(camera_id)
                            if json_camera_name:
                                camera_name = json_camera_name.decode()
                            # 点位可播放地址
                            camera_url = get_camera_url(camera_id, access_key, exists_url_dict)
                            # 报警截图URL
                            picture_url = ''
                            picture = alarm_obj[-1] if alarm_obj[-1] else '',
                            if picture:
                                picture_url = f'{ServerConfig.root_host}{picture[0]}'
                            # 关联楼层名
                            # floor_name = get_floor_name(camera_id, cursor)
                            # 当前楼层的企业入驻数量
                            # company_num = get_companies(floor_name, redis_conn)
                            # 今日报警截图总数
                            # camera_list = get_camera_list(floor_name, cursor)
                            # alarm_num = get_alarm_num(camera_list, cursor, current_begin_str)
                            # 推送数据集合
                            d = {
                                "id": alarm_obj[0],
                                "cameraId": camera_id,
                                "cameraName": camera_name,
                                "cameraUrl": camera_url,
                                "alarmType": alarm_obj[2] if alarm_obj[2] else '',
                                "alarmName": get_alarm_name(redis_conn).get(alarm_obj[2], '') if alarm_obj[2] else '',
                                "alarmTime": alarm_time_str,
                                "picture": picture_url,
                                # "floor": floor_name,
                                # "companyNum": company_num,
                                # "alarmNum": alarm_num
                            }
                            print(f'>>>>>>> 开始推送 ID={alarm_obj[0]} 的数据 <<<<<<<<')
                            print(f'发送的数据为：{json.dumps(d)}')
                            ws.send(json.dumps(d))
                            exists_id_list.append(alarm_obj[0])
                            print(f'当前已推送的ID列表：{exists_id_list}')
                            if len(exists_id_list) > 50:
                                exists_id_list = exists_id_list[30:]
            redis_conn.close()
            mysql_conn.close()
        except WebSocketError:
            print(f'连接对象：{ws} 已断开')
            break


server = WSGIServer((ServerConfig.ip, ServerConfig.socket_port), app, handler_class=WebSocketHandler)
print('======== 服务已启动 ========')
server.serve_forever()