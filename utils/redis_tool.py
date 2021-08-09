# -*- coding:utf-8 -*-
import json
import redis
import random
from loguru import logger
from config import ServerConfig
from utils.log_tool import redis_tool_log
from utils.interface_tool import get_crip_data

logger.add(redis_tool_log,
           format="{time:%Y-%m-%d %H:%M:%S} | {module}.py func_name[{function}] line[{line}] | {level} | {message}",
           level='INFO', retention='7 days')

REFRESH_CONF_CMD = """
local c = 1
local count = tonumber(KEYS[1])
local pos = 2
while (c <= count)
do
    local key = KEYS[pos]
    local num = tonumber(ARGV[pos])
    pos = pos + 1
    redis.call("del", key)
    for i=1,num
    do
        redis.call("hset", key, KEYS[pos], ARGV[pos])
        pos = pos + 1
    end
    c = c + 1
end
return 0
"""

RELEASE_LOCK_CMD = """
if redis.call("get",KEYS[1]) == ARGV[1]
then
    return redis.call("del",KEYS[1])
else
    return 0
end
"""


class RedisEvalHelper:
    """Redis lua 脚本加载"""

    def __init__(self, cmd, r):
        self.cmd = cmd
        self.sha = r.script_load(self.cmd)
        logger.info(f'初始化 sha 信息：{self.sha}')

    def call_cmd(self, r, num_keys, *args):
        if self.sha is None:
            logger.warning('警告：sha 值为空')
            self.sha = r.script_load(self.cmd)
            logger.info(f'重新获取的 sha 信息：{self.sha}')

        try:
            ret = r.evalsha(self.sha, num_keys, *args)
        except redis.exceptions.NoScriptError:
            logger.warning(f'sha 信息：{self.sha} 不存在，重新加载中...')
            self.sha = r.script_load(self.cmd)
            ret = r.evalsha(self.sha, num_keys, *args)
        logger.info(f'sha 信息：{self.sha}, 结果：{ret}')

        return ret


class RedisLockHelper:
    """Redis 锁配置"""

    def __init__(self, lock_key, r, lock_expire=10):
        self.r = r
        self.value = None
        self.is_lock = False
        self.lock_key = lock_key
        self.lock_expire = lock_expire

    def __enter__(self):
        """加锁"""
        self.acquire_lock()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """释放锁"""
        self.release_lock()

    def _get_lock(self):
        """获取锁"""
        self.value = str(random.randint(100000, 500080007000))
        ret = RedisConn.redis_db.set(self.lock_key, self.value, nx=True, ex=self.lock_expire)
        if not ret:
            logger.error(f'获取锁信息失败, key: {self.lock_key}, 结果：{ret}')
            return False
        logger.debug(f'获取锁信息成功, 键: {self.lock_key}, 值: {self.value}, 过期时间: {self.lock_expire}')
        self.is_lock = True
        return True

    def acquire_lock(self):
        assert self._get_lock(), "加锁失败..."
        return self

    def release_lock(self):
        if self.is_lock is True:
            logger.info(f'Redis 开始释放锁资源，锁的键为：{self.lock_key}')
            RedisConn.releaseLockEval.call_cmd(self.r, 1, self.lock_key, self.value)


class RedisConn:
    """redis 连接"""
    redis_db = None
    releaseLockEval = None
    refreshRedisConf = None

    @classmethod
    def init(cls, password, host, port, db, **kwargs):
        if password is not None:
            url = 'redis://:%s@%s:%s/%s' % (password, host, port, db)
        else:
            url = 'redis://@%s:%s/%s' % (host, port, db)
        logger.info(f"Redis 连接的 URL 信息：{url}")
        cls.redis_db = redis.from_url(url)
        cls.releaseLockEval = RedisLockHelper(RELEASE_LOCK_CMD, cls.redis_db)
        cls.refreshRedisConf = RedisEvalHelper(REFRESH_CONF_CMD, cls.redis_db)
        return cls.redis_db

    @classmethod
    def get_access_key(cls):
        """获取 accessKey """
        access_key = ''
        access_key_bytes = cls.redis_db.hget(ServerConfig.access_name, ServerConfig.access_key)
        if access_key_bytes:
            access_key = access_key_bytes.decode()
        # 如果 Redis 中查不到, 则尝试从 Redis 中获取 appId, appSecret, 再调用接口获取 access_key, 并保存到 Redis 中
        else:
            app_id_bytes = cls.redis_db.hget(ServerConfig.access_name, ServerConfig.app_id)
            app_secret_bytes = cls.redis_db.hget(ServerConfig.access_name, ServerConfig.app_secret)
            if app_id_bytes and app_secret_bytes:
                app_id = app_id_bytes.decode()
                app_secret = app_secret_bytes.decode()
                path = 'api/openapi/authenticate'
                data = {'appId': app_id, 'appSecret': app_secret}
                res = get_crip_data(path, method='POST', data_dict=data)
                # 申请成功则返回 accessKey, 保存下来
                if res.get('accessKey', ''):
                    RedisConn.redis_db.hmset(ServerConfig.access_name, {ServerConfig.access_key: res['accessKey']})
                    access_key = res['accessKey']

        return access_key

    @classmethod
    def get_app_id(cls):
        app_id = ''
        app_id_bytes = cls.redis_db.hget(ServerConfig.access_name, ServerConfig.app_id)
        if app_id_bytes:
            app_id = app_id_bytes.decode()

        return app_id

    @classmethod
    def get_app_secret(cls):
        app_secret = ''
        app_secret_bytes = cls.redis_db.hget(ServerConfig.access_name, ServerConfig.app_secret)
        if app_secret_bytes:
            app_secret = app_secret_bytes.decode()

        return app_secret

    @classmethod
    def get_algo_dict(cls):
        """获取报警ID与报警类型名的对应关系"""
        id_name_dict = dict()
        name_id_dict = dict()
        algo_config = cls.redis_db.get(ServerConfig.algo_key)
        if algo_config:
            algo_config = json.loads(algo_config)
            for config_dict in algo_config:
                id_name_dict[config_dict['task_key']] = config_dict['name']
                name_id_dict[config_dict['name']] = config_dict['task_key']

        return id_name_dict, name_id_dict

    @classmethod
    def get_system_name(cls):
        """获取系统名称"""
        key = ServerConfig.system_name
        system_name = cls.redis_db.get(key).decode('utf-8') if cls.redis_db.get(key) else ''

        return system_name

    @classmethod
    def set_system_name(cls, name):
        """更新系统名称"""
        key = ServerConfig.system_name
        cls.redis_db.set(key, name)

    @classmethod
    def set_face_flow_companies(cls, device_status_dict):
        """更新人脸Pad、人流监控设备状态、当前楼层入驻企业数"""
        if device_status_dict and isinstance(device_status_dict, dict):
            for floor_num, status_count in device_status_dict.items():
                if floor_num and status_count:
                    status_count_str = json.dumps(status_count)
                    cls.redis_db.hmset(ServerConfig.face_flow_companies_count, {floor_num: status_count_str})

    @classmethod
    def get_face_flow_companies(cls, floor_num):
        """
        获取人脸Pad、人流监控设备状态
        floor_name: 楼层名, 如果是查询整栋楼, 则固定为 allStatusCount"""
        face_flow_key = ServerConfig.face_flow_companies_count
        status_count_bytes = cls.redis_db.hget(face_flow_key, floor_num)
        if status_count_bytes:
            status_count_str = status_count_bytes.decode()
            status_count_dict = json.loads(status_count_str)
        else:
            status_count_dict = {'faceOnline': 0, 'faceOffline': 0, 'flowOffline': 0, 'flowOnline': 0, 'companies': 0}

        return status_count_dict
