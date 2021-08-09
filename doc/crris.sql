-- �������ݿ�
CREATE DATABASE crris CHARSET='utf8';
USE crris;


-- ����������ñ�
CREATE TABLE IF NOT EXISTS `crAreaConfig` (
`id` INTEGER AUTO_INCREMENT NOT NULL PRIMARY KEY,
`areaName` VARCHAR(32) DEFAULT NULL COMMENT '������',
`areaNum` INTEGER DEFAULT 0 COMMENT '�ڼ���',
`cameraList` VARCHAR(128) DEFAULT NULL COMMENT '��λ��Ϣ',
`pictureUrl` VARCHAR(255) DEFAULT NULL COMMENT '����ͼ·��');


-- �û���Ϣ��
CREATE TABLE IF NOT EXISTS `crUser` (
`id` INTEGER AUTO_INCREMENT NOT NULL PRIMARY KEY,
`username` VARCHAR(32) NOT NULL UNIQUE COMMENT '�û���',
`password` VARCHAR(16) NOT NULL COMMENT '����',
`openId` VARCHAR(128) NOT NULL UNIQUE COMMENT 'Ψһʶ����',
`isSuperuser` SMALLINT DEFAULT 0 COMMENT '�Ƿ��ǳ��� 0:�� 1:��',
`loginTime` DATETIME NOT NULL DEFAULT NOW() COMMENT '���µ�¼ʱ��');


-- Ȩ�����ñ�
CREATE TABLE IF NOT EXISTS `crPermission` (
`id` INTEGER AUTO_INCREMENT NOT NULL PRIMARY KEY,
`userId` INTEGER NOT NULL COMMENT '�������û�ID',
`areaId` INTEGER DEFAULT NULL COMMENT '����������ID',
`isOperational` SMALLINT DEFAULT 0 COMMENT '�Ƿ��в���Ȩ�� 0:�� 1:��',
`isViewable` SMALLINT DEFAULT 0 COMMENT '�Ƿ��в鿴Ȩ�� 0:�� 1:��');


-- ������ͼ��¼��
CREATE TABLE IF NOT EXISTS `crAlarmScreenshot` (
`id` INTEGER AUTO_INCREMENT NOT NULL PRIMARY KEY,
`cameraId` INTEGER NOT NULL DEFAULT -100 COMMENT '��λID',
`alarmType` INTEGER NOT NULL DEFAULT -100 COMMENT '��������',
`alarmTime` DATETIME NOT NULL COMMENT '����ʱ��',
`createdDay` DATETIME NOT NULL COMMENT '���ݱ���ʱ��, ���ڷ����ѯ(��ʽʾ����2021-07-02 00:00:00)',
`saveTime` DATETIME NOT NULL DEFAULT NOW() COMMENT '����ʱ��',
`pictureUrl` VARCHAR(128) DEFAULT NULL COMMENT '������ͼ·��',
INDEX(cameraId),
INDEX(alarmType),
INDEX(alarmTime),
INDEX(createdDay),
INDEX(saveTime));


-- ����ͨ�м�¼��
CREATE TABLE IF NOT EXISTS `crFacePassRecord` (
`id` INTEGER AUTO_INCREMENT NOT NULL PRIMARY KEY,
`deviceId` VARCHAR(16) NOT NULL DEFAULT '' COMMENT '�豸ID',
`deviceName` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '�豸����',
`floorName` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '�豸����¥��',
`floorNum` INTEGER DEFAULT 0 COMMENT '�ڼ���',
`userId` VARCHAR(16) NOT NULL DEFAULT '' COMMENT '�û�ID',
`userName` VARCHAR(16) DEFAULT NULL COMMENT '�û���',
`userType` VARCHAR(16) DEFAULT '��ͨ�û�' COMMENT '�û�����',
`passTime` DATETIME NOT NULL COMMENT 'ͨ��ʱ��',
`createdDay` DATETIME NOT NULL COMMENT '���ݱ���ʱ��, ���ڷ����ѯ(��ʽʾ����2021-07-02 00:00:00)',
`saveTime` DATETIME NOT NULL DEFAULT NOW() COMMENT '����ʱ��',
`pictureUrl` VARCHAR(128) DEFAULT NULL COMMENT '������ͼ·��',
INDEX(deviceId),
INDEX(userId),
INDEX(userType),
INDEX(floorName),
INDEX(floorNum),
INDEX(passTime),
INDEX(createdDay));


-- ����ͳ�Ƽ�¼��
CREATE TABLE IF NOT EXISTS `crCrowdFlowStatistics` (
`id` INTEGER AUTO_INCREMENT NOT NULL PRIMARY KEY,
`deviceId` VARCHAR(16) NOT NULL DEFAULT '' COMMENT '�豸ID',
`deviceName` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '�豸����',
`floorName` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '�豸����¥��',
`floorNum` INTEGER DEFAULT 0 COMMENT '�ڼ���',
`passType` SMALLINT DEFAULT 0 COMMENT '�������� 0:�� 1:��',
`passNum` INTEGER DEFAULT 0 COMMENT '��������',
`passTime` DATETIME NOT NULL COMMENT '��¼ʱ��',
`createdDay` DATETIME NOT NULL COMMENT '���ݱ���ʱ��, ���ڷ����ѯ(��ʽʾ����2021-07-02 00:00:00)',
`saveTime` DATETIME NOT NULL DEFAULT NOW() COMMENT '����ʱ��',
`pictureUrl` VARCHAR(128) DEFAULT NULL COMMENT '������ͼ·��',
INDEX(deviceId),
INDEX(deviceName),
INDEX(passType),
INDEX(floorName),
INDEX(floorNum),
INDEX(passTime),
INDEX(createdDay));


-- ��ǰ¥������ͳ�Ʊ�
CREATE TABLE IF NOT EXISTS `crFloorPersonStatistics` (
`id` INTEGER AUTO_INCREMENT NOT NULL PRIMARY KEY,
`floorName` VARCHAR(32) COMMENT '�豸����¥��',
`floorNum` INTEGER DEFAULT 0 COMMENT '�ڼ���',
`personNum` INTEGER DEFAULT 0 COMMENT '��ǰ¥������',
`recordTime` DATETIME NOT NULL COMMENT '��¼ʱ��',
`createdDay` DATETIME NOT NULL COMMENT '���ݱ���ʱ��, ���ڷ����ѯ(��ʽʾ����2021-07-02 00:00:00)',
`saveTime` DATETIME NOT NULL DEFAULT NOW() COMMENT '����ʱ��',
INDEX(floorName),
INDEX(floorNum),
INDEX(recordTime),
INDEX(createdDay));


-- Ĭ���½�һ������, �˺��������������ƽ̨�ı���һ��
INSERT INTO `crUser` (username, password, isSuperuser) VALUES ('root', 'root123', 1);

-- Ĭ���½��������ܵ�Ȩ������
INSERT INTO `crPermission` (userId, isOperational, isViewable) VALUES (1, 1, 1);

-- 25 ��¥Ĭ���Զ�����¥����
INSERT INTO `crAreaConfig` (areaName, areaNum) VALUES ('1F', 1), ('2F', 2), ('3F', 3), ('4F', 4), ('5F', 5), ('6F', 6),
                                                      ('7F', 7), ('8F', 8), ('9F', 9), ('10F', 10), ('11F', 11),
                                                      ('12F', 12), ('13F', 13), ('14F', 14), ('15F', 15), ('16F', 16),
                                                      ('17F', 17), ('18F', 18), ('19F', 19), ('20F', 20), ('21F', 21),
                                                      ('22F', 22), ('23F', 23), ('24F', 24), ('25F', 25);