#!/usr/bin/env python3
"""
AD 密码管理服务启动入口
"""
import os
from app import create_app

if __name__ == '__main__':
    app = create_app()
    
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5002))
    
    print(f'启动服务: http://{host}:{port}')
    app.run(host=host, port=port, debug=False)
