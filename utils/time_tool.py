# -*- coding:utf-8 -*-
from datetime import datetime, timedelta


def get_current_time_info():
    current_time = datetime.now()
    current_hour = current_time.hour
    current_minute = current_time.minute
    current_day_str = current_time.strftime('%Y-%m-%d')
    current_begin_str = f'{current_day_str} 00:00:00'
    current_day_begin = datetime.strptime(current_begin_str, '%Y-%m-%d %H:%M:%S')

    return current_time, current_hour, current_minute, current_day_str, current_begin_str, current_day_begin


def get_split_time_info():

    hour_minute_list = list()
    split_time_strp_list = list()
    current_hour, current_minute, current_day_str = get_current_time_info()[1:4]

    for i in range(24):
        for j in range(6):
            # if i == current_hour and (10*j) > current_minute:
            #     break
            hour_minute = f'{i:0>2d}:{10*j:0>2d}'
            hour_minute_list.append(hour_minute)
            hour_minute_seconds = f'{i:0>2d}:{10*j:0>2d}:00'
            split_time_strf = f'{current_day_str} {hour_minute_seconds}'
            split_time_strp = datetime.strptime(split_time_strf, '%Y-%m-%d %H:%M:%S')
            split_time_strp_list.append(split_time_strp)

    tomorrow_str = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d 00:00:00')
    tomorrow_begin = datetime.strptime(tomorrow_str, '%Y-%m-%d %H:%M:%S')
    split_time_strp_list.append(tomorrow_begin)
    hour_minute_list.append("24:00")

    return hour_minute_list, split_time_strp_list


def get_day_begin_end(delta_num):
    """
    获取某一天的开始时间和结束时间, 包括字符串形式和 datetime 形式
    delta_num：正数表示后几天, 负数表示前几天
    """
    current_time = datetime.now()
    that_day_strptime = current_time + timedelta(days=delta_num)
    that_day_strftime = that_day_strptime.strftime('%Y-%m-%d %H:%M:%S')
    that_day_str = that_day_strptime.strftime('%Y-%m-%d')
    begin_str = f'{that_day_str} 00:00:00'
    end_str = f'{that_day_str} 23:59:59'
    day_begin = datetime.strptime(begin_str, '%Y-%m-%d %H:%M:%S')
    day_end = datetime.strptime(end_str, '%Y-%m-%d %H:%M:%S')

    return begin_str, end_str, day_begin, day_end, that_day_strptime, that_day_strftime, that_day_str

