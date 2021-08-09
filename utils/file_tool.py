# -*- coding:utf-8 -*-
import os
import json
from loguru import logger
from utils.log_tool import file_tool_log

logger.add(file_tool_log,
           format="{time:%Y-%m-%d %H:%M:%S} | {module}.py func_name[{function}] line[{line}] | {level} | {message}",
           level='INFO', retention='7 days')
# 允许上传的文件类型
ALLOW_FILE_EXT = ['png', 'jpg', 'jpeg', 'ico', 'mp4', 'm4v', 'json', 'jpg', 'mov', 'png', 'avi']


class UploadFile:
    """文件上传配置类"""
    _root_path = None        # 项目根路径
    _root_host = None        # 项目所在服务器根路径
    _files_path = None       # 项目文件存放路径
    _files_host_path = None  # 项目所在服务器文件存放路径

    @classmethod
    def init(cls, root_path, root_host):
        """初始化文件路径和服务器域名"""
        cls._root_path = root_path
        cls._root_host = root_host
        cls._files_path = f'{cls._root_path}'
        cls.create_dirs(cls._files_path)
        cls._files_host_path = f'{cls._root_host}'
        logger.info(f"""
        项目根路径：{root_path} | 服务器路径：{root_host} 
        项目文件路径：{cls._files_path} | 服务器文件路径：{cls._files_host_path}""")

    @staticmethod
    def create_dirs(path):
        """新建目录"""
        os.makedirs(path, exist_ok=True)

    @staticmethod
    def get_file_name(current_path, value):
        """
        获取文件名, 比如 Bandari-童年记忆.mp3
        current_path: 当前文件所在目录
        注意：这里默认当前目录下只有一个文件
        """
        file_name = ''
        if os.listdir(current_path):
            for file_obj in os.listdir(current_path):
                if f'{value}&' in file_obj:
                    file_name = file_obj
        return file_name

    @staticmethod
    def dump_json_file(absolute_path, data):
        """将数据写入 JSON 文件"""
        with open(absolute_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

    @staticmethod
    def load_json_file(absolute_path):
        """将数据从 JSON 文件导出"""
        with open(absolute_path, encoding='utf-8') as f:
            content = json.load(f)

        return content

    @classmethod
    def save_file(cls, file_obj, file_type, value=None):
        """
        保存文件
        对于 logo 文件的上传与替换，传参 file_type 设为 logo
        对于每个区域对应的图像文件，传参 file_type 是对应的区域英文名即可
        """
        file_name, file_ext = file_obj.filename.split('.')
        assert file_ext.lower() in ALLOW_FILE_EXT, f'不支持上传的文件类型：{file_ext}'
        new_file_name = ''.join(file_name.split())  # 去除文件名空格
        # 获取相关文件路径
        file_type_path = f'{cls._files_path}{file_type}/'
        relative_path = f'{file_type}/{value}&{new_file_name}.{file_ext}'
        # 新建对应的文件夹
        cls.create_dirs(file_type_path)
        absolute_path = f'{file_type_path}{value}&{new_file_name}.{file_ext}'
        access_path = f'{cls._files_host_path}{relative_path}'
        logger.info(f'当前文件相对路径：{relative_path} | 当前文件绝对路径：{absolute_path} | 当前文件访问路径：{access_path}')
        # 同一个文件夹下只保留同一个类型的一份文件, 比如现在上传了一张 5F 的图片 2.jpg,
        # 首先判断 picture/ 目录下是否有 5F& 开头的文件名, 如果有就先删除这张图片, 再保存 2.jpg, 保存格式：5F&2.jpg
        exists_file_name = cls.get_file_name(file_type_path, value)
        if exists_file_name:
            exists_file_path = f'{file_type_path}{exists_file_name}'
            os.remove(exists_file_path)

        file_obj.save(absolute_path)

        return {
            'relative_path': relative_path,
            'absolute_path': absolute_path,
            # 'access_path': access_path,
            'access_path': "https://cdn3-banquan.ituchong.com/weili/l/919767976639332370.jpeg"
        }

    @classmethod
    def write_xlsx_file(cls, workbook, name):
        """写入 Excel 文件"""
        relative_path = f'xlsx/{name}.xlsx'
        save_folder = f'{cls._root_path}xlsx/'
        cls.create_dirs(save_folder)
        absolute_path = f'{cls._root_path}{relative_path}'
        workbook.save(absolute_path)
        access_path = f'{cls._root_host}{relative_path}'

        return access_path
