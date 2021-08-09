# -*- coding:utf-8 -*-
import base64
from config import ServerConfig
from utils.file_tool import UploadFile


def get_picture_from_base64(base64_data):
    """返回base64解码后的字节流数据"""
    return bytes(base64.b64decode(base64_data))


def save_picture_data(src_pic_data, day_str, relative_path_str, pic_name=None):
    """将报警截图数据保存到相关目录"""
    pic_data = get_picture_from_base64(src_pic_data)
    relative_path = f'picture/{relative_path_str}/{day_str}/'
    absolute_path = f'{ServerConfig.root_path}{relative_path}'
    UploadFile.create_dirs(absolute_path)
    picture_path = f'{absolute_path}{pic_name}'
    with open(picture_path, 'wb') as f:
        f.write(pic_data)

    return f'{relative_path}{pic_name}'