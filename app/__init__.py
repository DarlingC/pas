import os
from flask import Flask

def create_app():
    app = Flask(__name__, static_folder='../public', static_url_path='')
    
    # 加载配置
    from dotenv import load_dotenv
    load_dotenv()
    
    app.config['AD_LDAP_URL'] = os.getenv('AD_LDAP_URL', 'ldap://domain.com:389')
    app.config['AD_BASE_DN'] = os.getenv('AD_BASE_DN', 'DC=domain,DC=com')
    app.config['AD_ADMIN_DN'] = os.getenv('AD_ADMIN_DN', 'CN=Admin,CN=Users,DC=domain,DC=com')
    app.config['AD_ADMIN_PASSWORD'] = os.getenv('AD_ADMIN_PASSWORD', '')
    app.config['FEISHU_APP_ID'] = os.getenv('FEISHU_APP_ID', '')
    app.config['FEISHU_APP_SECRET'] = os.getenv('FEISHU_APP_SECRET', '')
    
    # 注册路由
    from app import routes
    app.register_blueprint(routes.bp)
    
    # 数据库初始化
    from app.models import init_db, close_db
    init_db()
    
    @app.teardown_appcontext
    def teardown_db(exception):
        close_db(exception)
    
    # 主页路由
    @app.route('/')
    def index():
        return app.send_static_file('index.html')
    
    return app
