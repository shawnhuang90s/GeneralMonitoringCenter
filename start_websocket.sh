#!/bin/bash
# 注意：前一个服务一定要在后台运行, 即后面加个&; 最后一个服务要以前台运行
# 全部以前台运行的话, 只有第一个服务会启动
# 全部以后台运行的话, 当最后一个服务执行完成后, 容器就退出了
python run.py &
# 启动 Websocket 服务
python3 ws_alarm_data.py