-- 创建数据库
CREATE DATABASE crris CHARSET='utf8';
USE crris;


-- 监控区域配置表
CREATE TABLE IF NOT EXISTS `crAreaConfig` (
`id` INTEGER AUTO_INCREMENT NOT NULL PRIMARY KEY,
`areaName` VARCHAR(32) DEFAULT NULL COMMENT '区域名',
`areaNum` INTEGER DEFAULT 0 COMMENT '第几层',
`cameraList` VARCHAR(128) DEFAULT NULL COMMENT '点位信息',
`pictureUrl` VARCHAR(255) DEFAULT NULL COMMENT '区域图路径');


-- 用户信息表
CREATE TABLE IF NOT EXISTS `crUser` (
`id` INTEGER AUTO_INCREMENT NOT NULL PRIMARY KEY,
`username` VARCHAR(32) NOT NULL UNIQUE COMMENT '用户名',
`password` VARCHAR(16) NOT NULL COMMENT '密码',
`openId` VARCHAR(128) NOT NULL UNIQUE COMMENT '唯一识别码',
`isSuperuser` SMALLINT DEFAULT 0 COMMENT '是否是超管 0:否 1:是',
`loginTime` DATETIME NOT NULL DEFAULT NOW() COMMENT '最新登录时间');


-- 权限配置表
CREATE TABLE IF NOT EXISTS `crPermission` (
`id` INTEGER AUTO_INCREMENT NOT NULL PRIMARY KEY,
`userId` INTEGER NOT NULL COMMENT '关联的用户ID',
`areaId` INTEGER DEFAULT NULL COMMENT '关联的区域ID',
`isOperational` SMALLINT DEFAULT 0 COMMENT '是否有操作权限 0:否 1:是',
`isViewable` SMALLINT DEFAULT 0 COMMENT '是否有查看权限 0:否 1:是');


-- 报警截图记录表
CREATE TABLE IF NOT EXISTS `crAlarmScreenshot` (
`id` INTEGER AUTO_INCREMENT NOT NULL PRIMARY KEY,
`cameraId` INTEGER NOT NULL DEFAULT -100 COMMENT '点位ID',
`alarmType` INTEGER NOT NULL DEFAULT -100 COMMENT '报警类型',
`alarmTime` DATETIME NOT NULL COMMENT '报警时间',
`createdDay` DATETIME NOT NULL COMMENT '数据保存时间, 用于分组查询(格式示例：2021-07-02 00:00:00)',
`saveTime` DATETIME NOT NULL DEFAULT NOW() COMMENT '保存时间',
`pictureUrl` VARCHAR(128) DEFAULT NULL COMMENT '报警截图路径',
INDEX(cameraId),
INDEX(alarmType),
INDEX(alarmTime),
INDEX(createdDay),
INDEX(saveTime));


-- 人脸通行记录表
CREATE TABLE IF NOT EXISTS `crFacePassRecord` (
`id` INTEGER AUTO_INCREMENT NOT NULL PRIMARY KEY,
`deviceId` VARCHAR(16) NOT NULL DEFAULT '' COMMENT '设备ID',
`deviceName` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '设备名称',
`floorName` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '设备所在楼层',
`floorNum` INTEGER DEFAULT 0 COMMENT '第几层',
`userId` VARCHAR(16) NOT NULL DEFAULT '' COMMENT '用户ID',
`userName` VARCHAR(16) DEFAULT NULL COMMENT '用户名',
`userType` VARCHAR(16) DEFAULT '普通用户' COMMENT '用户类型',
`passTime` DATETIME NOT NULL COMMENT '通行时间',
`createdDay` DATETIME NOT NULL COMMENT '数据保存时间, 用于分组查询(格式示例：2021-07-02 00:00:00)',
`saveTime` DATETIME NOT NULL DEFAULT NOW() COMMENT '保存时间',
`pictureUrl` VARCHAR(128) DEFAULT NULL COMMENT '报警截图路径',
INDEX(deviceId),
INDEX(userId),
INDEX(userType),
INDEX(floorName),
INDEX(floorNum),
INDEX(passTime),
INDEX(createdDay));


-- 人流统计记录表
CREATE TABLE IF NOT EXISTS `crCrowdFlowStatistics` (
`id` INTEGER AUTO_INCREMENT NOT NULL PRIMARY KEY,
`deviceId` VARCHAR(16) NOT NULL DEFAULT '' COMMENT '设备ID',
`deviceName` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '设备名称',
`floorName` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '设备所在楼层',
`floorNum` INTEGER DEFAULT 0 COMMENT '第几层',
`passType` SMALLINT DEFAULT 0 COMMENT '出入类型 0:出 1:入',
`passNum` INTEGER DEFAULT 0 COMMENT '出入人数',
`passTime` DATETIME NOT NULL COMMENT '记录时间',
`createdDay` DATETIME NOT NULL COMMENT '数据保存时间, 用于分组查询(格式示例：2021-07-02 00:00:00)',
`saveTime` DATETIME NOT NULL DEFAULT NOW() COMMENT '保存时间',
`pictureUrl` VARCHAR(128) DEFAULT NULL COMMENT '报警截图路径',
INDEX(deviceId),
INDEX(deviceName),
INDEX(passType),
INDEX(floorName),
INDEX(floorNum),
INDEX(passTime),
INDEX(createdDay));


-- 当前楼层人数统计表
CREATE TABLE IF NOT EXISTS `crFloorPersonStatistics` (
`id` INTEGER AUTO_INCREMENT NOT NULL PRIMARY KEY,
`floorName` VARCHAR(32) COMMENT '设备所在楼层',
`floorNum` INTEGER DEFAULT 0 COMMENT '第几层',
`personNum` INTEGER DEFAULT 0 COMMENT '当前楼层人数',
`recordTime` DATETIME NOT NULL COMMENT '记录时间',
`createdDay` DATETIME NOT NULL COMMENT '数据保存时间, 用于分组查询(格式示例：2021-07-02 00:00:00)',
`saveTime` DATETIME NOT NULL DEFAULT NOW() COMMENT '保存时间',
INDEX(floorName),
INDEX(floorNum),
INDEX(recordTime),
INDEX(createdDay));


-- 默认新建一个超管, 账号密码避免与推理平台的保持一致
INSERT INTO `crUser` (username, password, isSuperuser) VALUES ('root', 'root123', 1);

-- 默认新建关联超管的权限配置
INSERT INTO `crPermission` (userId, isOperational, isViewable) VALUES (1, 1, 1);

-- 25 层楼默认自动生成楼层名
INSERT INTO `crAreaConfig` (areaName, areaNum) VALUES ('1F', 1), ('2F', 2), ('3F', 3), ('4F', 4), ('5F', 5), ('6F', 6),
                                                      ('7F', 7), ('8F', 8), ('9F', 9), ('10F', 10), ('11F', 11),
                                                      ('12F', 12), ('13F', 13), ('14F', 14), ('15F', 15), ('16F', 16),
                                                      ('17F', 17), ('18F', 18), ('19F', 19), ('20F', 20), ('21F', 21),
                                                      ('22F', 22), ('23F', 23), ('24F', 24), ('25F', 25);