import os

from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'

    # 注册蓝图
    from app.auth.routes import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.main.routes import bp as main_bp
    app.register_blueprint(main_bp)

    from app.api.routes import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    # 👇 添加静态图片访问路径
    @app.route('/shopping_crawl/<path:filename>')
    def serve_tmall_images(filename):
        base_path = os.path.abspath(os.path.join(app.root_path, '..', 'shopping_crawl'))
        # app.logger.warning(f"[DEBUG] Serving image: {filename}")
        # app.logger.warning(f"[DEBUG] Correct absolute path: {base_path}")
        return send_from_directory(base_path, filename)

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))

    return app


from app.models import user, product, order, review