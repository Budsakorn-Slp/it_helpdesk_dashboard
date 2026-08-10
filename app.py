# -*- coding: utf-8 -*-
"""IT Helpdesk Dashboard — จุดเริ่มของแอป

ใช้ไฟล์เดียวทั้ง dev และ prod ความต่างอยู่ใน .env เท่านั้น
(ดู .env.example)  รันด้วย:

    python app.py                              # dev
    gunicorn "app:create_app()" -b 0.0.0.0:5093  # prod
"""
import logging

from flask import Flask

import config
import db
import routes


def create_app():
    logging.basicConfig(
        level=logging.DEBUG if config.DEBUG else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    db.init_client()

    app = Flask(__name__)
    app.config["UPLOAD_FOLDER"] = config.UPLOAD_FOLDER
    routes.register(app)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
