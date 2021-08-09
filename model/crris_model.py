# -*- coding:utf-8 -*-
import peewee
import datetime
from utils.mysql_tool import DBConn
from utils.model_tool import BaseModel


class AreaConfig(BaseModel):
    """监控区域配置表"""
    areaName = peewee.CharField(max_length=32, null=True, verbose_name='区域名')
    areaNum = peewee.IntegerField(default=0, verbose_name='第几层')
    cameraList = peewee.CharField(max_length=128, null=True, verbose_name='点位信息')
    pictureUrl = peewee.CharField(max_length=255, null=True, verbose_name='区域图路径')

    class Meta:
        database = DBConn.db
        table_name = 'crAreaConfig'


class User(BaseModel):
    """用户信息表"""
    username = peewee.CharField(max_length=32, unique=True, verbose_name='用户名')
    password = peewee.CharField(max_length=16, verbose_name='密码')
    openId = peewee.CharField(max_length=128, unique=True, verbose_name='唯一识别码')
    isSuperuser = peewee.SmallIntegerField(default=0, verbose_name='是否是超管 0:否 1:是')
    loginTime = peewee.DateTimeField(verbose_name='最新登录时间')

    class Meta:
        database = DBConn.db
        table_name = 'crUser'


class Permission(BaseModel):
    """权限配置表"""
    user = peewee.ForeignKeyField(User, column_name='userId', backref='user_permission', verbose_name='关联的用户ID')
    area = peewee.ForeignKeyField(AreaConfig, column_name='areaId', null=True, backref='area_permission', verbose_name='关联的区域ID')
    isOperational = peewee.SmallIntegerField(default=0, verbose_name='是否有操作权限 0:否 1:是')
    isViewable = peewee.SmallIntegerField(default=0, verbose_name='是否有查看权限 0:否 1:是')

    class Meta:
        database = DBConn.db
        table_name = 'crPermission'


class AlarmScreenshot(BaseModel):
    """每个算法对应的报警截图记录表"""
    cameraId = peewee.IntegerField(index=True, default=-100, verbose_name='点位ID')
    alarmType = peewee.IntegerField(index=True, default=-100, verbose_name='报警类型ID')
    alarmTime = peewee.DateTimeField(index=True, verbose_name='报警时间')
    createdDay = peewee.DateTimeField(index=True, verbose_name='数据保存时间, 格式示例：2021-07-02 00:00:00')
    saveTime = peewee.DateTimeField(default=datetime.datetime.now(), verbose_name='保存时间')
    pictureUrl = peewee.CharField(max_length=128, null=True, verbose_name='报警截图路径')

    class Meta:
        database = DBConn.db
        table_name = 'crAlarmScreenshot'


class FacePassRecord(BaseModel):
    """人脸通行记录表"""
    deviceId = peewee.CharField(max_length=16, index=True, default='', verbose_name='设备ID')
    deviceName = peewee.CharField(max_length=64, default='', verbose_name='设备名称')
    floorName = peewee.CharField(max_length=32, index=True, default='', verbose_name='设备所在楼层')
    floorNum = peewee.IntegerField(default=0, verbose_name='第几层')
    userId = peewee.CharField(max_length=16, index=True, default='', verbose_name='用户ID')
    userName = peewee.CharField(max_length=16, null=True, verbose_name='用户名')
    userType = peewee.CharField(max_length=16, index=True, default='普通用户', verbose_name='用户类型')
    passTime = peewee.DateTimeField(index=True, verbose_name='通行时间')
    createdDay = peewee.DateTimeField(index=True, verbose_name='数据保存时间, 格式示例：2021-07-02 00:00:00')
    saveTime = peewee.DateTimeField(default=datetime.datetime.now(), verbose_name='保存时间')
    pictureUrl = peewee.CharField(max_length=128, null=True, verbose_name='报警截图路径')

    class Meta:
        database = DBConn.db
        table_name = 'crFacePassRecord'

    # @staticmethod
    # def type_id_dict():
    #     return {'普通用户': 0, '黑名单': 1}
    #
    # @staticmethod
    # def id_type_dict():
    #     return {0: '普通用户', 1: '黑名单'}


class CrowdFlowStatistics(BaseModel):
    """人流统计记录表"""
    deviceId = peewee.CharField(max_length=16, index=True, default='', verbose_name='设备ID')
    deviceName = peewee.CharField(max_length=64, default='', index=True, verbose_name='设备名称')
    floorName = peewee.CharField(max_length=32, index=True, default='', verbose_name='设备所在楼层')
    floorNum = peewee.IntegerField(default=0, verbose_name='第几层')
    passType = peewee.SmallIntegerField(index=True, default=0, verbose_name='出入类型 0:出 1:入')
    passNum = peewee.IntegerField(default=0, verbose_name='出入人数')
    passTime = peewee.DateTimeField(index=True, verbose_name='记录时间')
    createdDay = peewee.DateTimeField(index=True, verbose_name='数据保存时间, 格式示例：2021-07-02 00:00:00')
    saveTime = peewee.DateTimeField(default=datetime.datetime.now(), verbose_name='保存时间')
    pictureUrl = peewee.CharField(max_length=128, null=True, verbose_name='截图路径')

    class Meta:
        database = DBConn.db
        table_name = 'crCrowdFlowStatistics'

    @staticmethod
    def type_id_dict():
        return {'离开': 0, '进入': 1}

    @staticmethod
    def id_type_dict():
        return {0: '离开', 1: '进入'}


class FloorPersonStatistics(BaseModel):
    """当前楼层人数统计, 只记录二层及以上的人数"""
    floorName = peewee.CharField(max_length=32, index=True, verbose_name='设备所在楼层')
    floorNum = peewee.IntegerField(default=0, verbose_name='第几层')
    personNum = peewee.IntegerField(default=0, verbose_name='当前楼层人数')
    recordTime = peewee.DateTimeField(index=True, verbose_name='记录时间')
    createdDay = peewee.DateTimeField(index=True, verbose_name='数据保存时间, 格式示例：2021-07-02 00:00:00')
    saveTime = peewee.DateTimeField(default=datetime.datetime.now(), verbose_name='保存时间')

    class Meta:
        database = DBConn.db
        table_name = 'crFloorPersonStatistics'
