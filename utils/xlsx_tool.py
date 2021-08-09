# -*- coding:utf-8 -*-
import openpyxl
from config import ServerConfig
from utils.file_tool import UploadFile


class XlsxTool:

    def __init__(self, title, model=None):
        self.title = title
        self.model = model
        self.data_list = None

    def read_xlsx(self, file_path, start_line=2):
        """读取 Excel 内容"""
        try:
            file_path = f'{ServerConfig.root_path}{file_path}'
            workbook = openpyxl.load_workbook(file_path)
        except FileNotFoundError:
            print(f'文件不存在, 当前文件路径：{file_path}')
            return
        except Exception as e:
            print(f'打开文件报错：{e}')
            return
        ws = workbook['Sheet']
        index = 0
        data_list = {}
        for row_list in ws.rows:
            index += 1
            if index < start_line:
                continue
            data = {}
            for i in range(len(self.title)):
                row_value = str(row_list[i].value).strip().replace('\n', '').replace('\r', '') \
                    if row_list[i].value is not None else ''
                data[self.title[i]] = row_value

            data_list[index] = data
        self.data_list = data_list

    def insert_into_model(self):
        if self.model is not None:
            return self.model.xlsx_insert(self.data_list)

    def write_xlsx(self, data_list, name):
        """写入excel"""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(self.title)
        for data in data_list:
            ws.append(data)
        url = UploadFile.write_xlsx_file(wb, name) + f'?name={name}'
        return url


if __name__ == '__main__':
    path = r'C:\Users\DELL\Downloads\摄像头20210204142030.xlsx'
    xlsx = XlsxTool(['streamUrl', 'address', 'name'])
    xlsx.read_xlsx(path)
    print(xlsx.data_list)