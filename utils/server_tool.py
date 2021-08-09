# -*- coding:utf-8 -*-
import os
import sys
from loguru import logger
from utils import mysql_tool
from config import ServerConfig
from flask import request, g, Flask
from gevent.pywsgi import WSGIServer
from utils.redis_tool import RedisConn
from utils.file_tool import UploadFile
from utils.log_tool import server_tool_log
from utils.cookie_tool import CookieSession

logger.add(server_tool_log,
           format="{time:%Y-%m-%d %H:%M:%S} | {module}.py func_name[{function}] line[{line}] | {level} | {message}",
           level='INFO', retention='7 days')


def before_request():
    """处理每个请求之前记录请求路径、请求参数"""
    if request.path == '/crris/get_alarm_data':
        logger.info(f'当前请求路径：{request.path} | URL携带参数：{request.args}')
    else:
        logger.info(f'当前请求路径：{request.path} | URL携带参数：{request.args} | 请求体数据：{request.get_json()}')


def db_close():
    """断开数据库连接"""
    if not mysql_tool.DBConn.db.is_closed():
        mysql_tool.DBConn.db.close()


def teardown_request(exc):
    """处理每个请求之后都断开数据库连接, 哪怕过程中有异常"""
    db_close()


def after_request(response):
    """处理每个请求之后，如果过程中没问题，操作 Token 信息"""
    set_cookies = getattr(g, 'set_cookies', None)
    unset_cookies = getattr(g, 'unset_cookies', None)
    logger.info(f'设置的 Cookies 信息：{set_cookies} | 未设置的 Cookies 信息：{unset_cookies}')
    if set_cookies:
        # 返回结果中添加 Token 信息
        response.set_cookie(ServerConfig.token_key, set_cookies, httponly=True)
    elif unset_cookies:
        # 返回结果中删除 Token 信息
        response.delete_cookie(ServerConfig.token_key)

    return response


def after_request_cors(response):
    """跨域请求处理"""
    response = after_request(response)
    origin = request.headers.get('Origin', None)
    response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Method'] = 'GET, POST'
    response.headers['Access-Control-Allow-Headers'] = 'Origin, X-Requested-With, Content-Type, Accept'
    response.headers['Access-Control-Allow-Credentials'] = 'true'

    return response


def handle_error(error):
    """异常处理公共模块"""
    # logger.error(str(error))
    res = {
        'data': {
            'errorMsg': str(error),
            # 'error_msg': 'Server Error',
        },
        'requestInfo': {
            'flag': False
        }
    }

    return res


class Server:
    """服务类配置"""
    config = None
    init_register = None
    app = Flask(__name__, root_path=os.getcwd())

    @classmethod
    def init(cls):
        cls.init_register()
        cls.app.before_request(before_request)
        if cls.config.cors:
            cls.app.after_request(after_request_cors)
        else:
            cls.app.after_request(after_request)
        cls.app.teardown_request(teardown_request)
        cls.app.errorhandler(Exception)(handle_error)
        logger.info('======== 定时任务初始化配置 ========')
        from timed_task.task_scheduler import Config, scheduler
        cls.app.config.from_object(Config())
        scheduler.init_app(cls.app)
        scheduler.start()

    @classmethod
    def run(cls, ip, port):
        logger.info(f'本次服务监听的地址信息：{ip}:{port}')
        server = WSGIServer((ip, port), cls.app)
        logger.info('======== 项目启动成功 ========')
        server.serve_forever()


class Application:
    """应用类配置"""

    @classmethod
    def init(cls, config):
        """读取配置文件 config.py 中的信息并初始化相关配置"""
        try:
            logger.info('======== MySQL 初始化配置 ========')
            mysql_tool.DBConn.init(
                database=config.db_name,
                host=config.db_host,
                port=config.db_port,
                user=config.db_user,
                password=config.db_password,
                max_connections=config.db_max_connect_number,
                stale_timeout=config.db_stale_timeout,
                timeout=config.db_timeout,
            )
            logger.info('======== Redis 初始化配置 ========')
            if config.redis_password is not None:
                url = 'redis://:%s@%s:%s/%s' % (config.redis_password, config.redis_host,
                                                config.redis_port, config.redis_db)
            else:
                url = 'redis://@%s:%s/%s' % (config.redis_host, config.redis_port, config.redis_db)
            Server.app.config['REDIS_URL'] = url
            RedisConn.init(
                config.redis_password,
                config.redis_host,
                config.redis_port,
                config.redis_db
            )
            logger.info('======== Cookies 初始化配置 ========')
            CookieSession.init(
                config.user_key,
                config.token_key
            )
            logger.info('======== 文件上传初始化配置 ========')
            UploadFile.init(
                config.root_path,
                config.root_host
            )
        except Exception as e:
            logger.error(f'项目初始化失败：{e}')
            sys.exit(1)

    @classmethod
    def run(cls):
        config = Server.config
        cls.init(config)
        Server.init()
        Server.run(config.ip, config.port)
