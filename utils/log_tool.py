# -*- coding:utf-8 -*-
import os
import loguru
from pathlib import Path
from datetime import datetime

# 基础路径配置
logger = loguru.logger
base_path = Path(__file__).resolve().parent.parent
current_time = datetime.now().strftime('%Y-%m-%d')
# 以日期为界限, 每天的日志放在一个文件夹内
base_log_path = f'{base_path}/log/{current_time}'
if not os.path.exists(base_log_path):
    os.makedirs(base_log_path, exist_ok=False)

cookie_tool_log = f'{base_log_path}/cookie_tool.log'
redis_tool_log = f'{base_log_path}/redis_tool.log'
file_tool_log = f'{base_log_path}/file_tool.log'
mysql_tool_log = f'{base_log_path}/mysql_tool.log'
server_tool_log = f'{base_log_path}/server_tool.log'
task_scheduler_log = f'{base_log_path}/task_scheduler.log'
login_tool_log = f'{base_log_path}/login_tool.log'
interface_tool_log = f'{base_log_path}/interface_tool.log'
area_config_view_log = f'{base_log_path}/area_config_view.log'
home_view_log = f'{base_log_path}/home_view.log'
alarm_record_view_log = f'{base_log_path}/alarm_record_view.log'
system_config_view_log = f'{base_log_path}/system_config_view.log'
face_pass_view_log = f'{base_log_path}/face_pass_view.log'
flow_record_view_log = f'{base_log_path}/flow_record_view.log'
