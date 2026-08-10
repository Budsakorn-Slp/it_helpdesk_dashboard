# -*- coding: utf-8 -*-
"""รวม blueprint ทั้งหมดของแอป"""
from routes.board_api import bp as board_api_bp
from routes.cost_center import bp as cost_center_bp
from routes.docs import bp as docs_bp
from routes.employee_api import bp as employee_api_bp
from routes.pages import bp as pages_bp
from routes.request_api import bp as request_api_bp

#: หน้า HTML ต้องลงท้าย เพราะ pages มี rule แบบ /<board_key> ที่กินได้ทุก path
ALL_BLUEPRINTS = (
    board_api_bp,
    request_api_bp,
    employee_api_bp,
    cost_center_bp,
    docs_bp,
    pages_bp,
)


def register(app):
    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)
