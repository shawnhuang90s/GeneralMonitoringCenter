# -*- coding:utf-8 -*-
from gevent import monkey
monkey.patch_all()  # 遇到阻塞自动切换协程
from flask import Response
from config import ServerConfig
from utils.server_tool import Server, Application

app = Server.app


def register_url():
    """注册路由"""
    from controller.crris_router import bp
    # TODO:后续这里要去掉 /api, 因为 nginx 中会配置好
    app.register_blueprint(bp, url_prefix='/api/crris')


@app.errorhandler(401)
def custom_401(error):
    return Response('Authentication failed...', 401, {'WWW-Authenticate':'Basic realm="Login Required"'})


def run():
    Server.init_register = register_url
    Server.config = ServerConfig
    Application.run()


if __name__ == '__main__':
    run()
