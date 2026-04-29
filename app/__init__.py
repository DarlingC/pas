import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 从 app.py 导入 Flask 应用实例
from app.app import app

# 初始化数据库
from app.app import init_db
init_db()

# 导出应用实例
def create_app():
    """保持兼容性的工厂函数"""
    return app
