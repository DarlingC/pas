import os
import sqlite3
from datetime import datetime

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, g

# 加载环境变量
load_dotenv()

# 从环境变量获取配置
AD_LDAP_URL = os.getenv('AD_LDAP_URL', 'ldap://domain.com:389')
AD_BASE_DN = os.getenv('AD_BASE_DN', 'DC=domain,DC=com')
AD_ADMIN_DN = os.getenv('AD_ADMIN_DN', 'CN=Admin,CN=Users,DC=domain,DC=com')
AD_ADMIN_PASSWORD = os.getenv('AD_ADMIN_PASSWORD', '')
FEISHU_APP_ID = os.getenv('FEISHU_APP_ID', '')
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET', '')

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'passwords.db')

# 创建 Flask 应用
app = Flask(__name__, static_folder='../public', static_url_path='')


# ==================== 数据库相关函数 ====================

def get_db():
    """获取数据库连接"""
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 创建表，包含 user_account 字段（放在 user_id 后面）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS passwords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL UNIQUE,
            user_account TEXT,
            user_name TEXT,
            password TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # 添加 user_account 字段（如果不存在）
    try:
        cursor.execute('ALTER TABLE passwords ADD COLUMN user_account TEXT')
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


# ==================== 飞书相关接口 ====================

@app.route('/api/feishu/appid', methods=['GET'])
def get_appid():
    """返回飞书应用ID"""
    if not FEISHU_APP_ID:
        return jsonify({'error': '未配置飞书应用ID'}), 500
    return jsonify({'appid': FEISHU_APP_ID})


@app.route('/api/feishu/user', methods=['GET'])
def get_user_info():
    """通过 code 获取用户信息（飞书 JSSDK 授权）"""
    code = request.args.get('code')

    if code:
        try:
            # 获取 app_access_token
            token_url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
            token_response = requests.post(
                token_url,
                json={
                    'app_id': FEISHU_APP_ID,
                    'app_secret': FEISHU_APP_SECRET
                },
                timeout=10
            )
            token_data = token_response.json()

            if token_data.get('code') != 0:
                return jsonify({'error': '获取access_token失败'}), 401

            app_access_token = token_data.get('tenant_access_token')

            # 用 code 换取 user_access_token
            user_token_url = 'https://open.feishu.cn/open-apis/authen/v1/oidc/access_token'
            user_token_response = requests.post(
                user_token_url,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {app_access_token}'
                },
                json={
                    'grant_type': 'authorization_code',
                    'code': code
                },
                timeout=10
            )
            user_token_data = user_token_response.json()

            if user_token_data.get('code') != 0:
                return jsonify({
                    'error': user_token_data.get('msg', '换取user_access_token失败')
                }), 401

            user_access_token = user_token_data.get('data', {}).get('access_token')
            if not user_access_token:
                return jsonify({'error': '未获取到user_access_token'}), 401

            # 获取用户信息
            user_info_url = 'https://open.feishu.cn/open-apis/authen/v1/user_info'
            user_info_response = requests.get(
                user_info_url,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {user_access_token}'
                },
                timeout=10
            )
            user_info_data = user_info_response.json()
            print(f'飞书用户信息原始数据: {user_info_data}')

            if user_info_data.get('code') == 0 and user_info_data.get('data'):
                user = user_info_data['data']
                return jsonify({
                    'success': True,
                    'data': {
                        'open_id': user.get('open_id') or '',
                        'user_id': user.get('user_id') or '',
                        'union_id': user.get('union_id'),
                        'name': user.get('name') or '',
                        'en_name': user.get('en_name'),
                        'email': user.get('email'),
                        'mobile': user.get('mobile'),
                        'avatar_url': user.get('avatar_url'),
                        # 保存原始数据用于调试
                        '_raw': user
                    }
                })

            return jsonify({'error': '获取用户信息失败'}), 401

        except Exception as e:
            print(f'获取用户信息错误: {e}')
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': '缺少授权码'}), 400


# ==================== AD 密码相关接口 ====================

@app.route('/api/ad/password/reset', methods=['POST'])
def reset_password():
    """重置 AD 密码"""
    data = request.get_json()
    print(data)
    new_password = data.get('newPassword')
    confirm_password = data.get('confirmPassword')
    user_id = data.get('user_id')
    user_name = data.get('user_name')
    email = data.get('email')
    # 从邮箱提取 AD 账号
    user_account = email.split('@')[0] if email else None

    if not new_password or not confirm_password:
        return jsonify({'error': '请填写新密码和确认密码'}), 400

    if new_password != confirm_password:
        return jsonify({'error': '两次输入的密码不一致'}), 400

    if len(new_password) < 8:
        return jsonify({'error': '密码长度不能少于8位'}), 400

    if not user_account:
        return jsonify({'error': '无法获取用户账号信息'}), 400

    # 调用 AD 修改密码
    result = ad_reset_password(user_account, new_password)

    if not result['success']:
        return jsonify({'error': result['message']}), 500

    # 保存密码到数据库
    save_password(user_id, user_account, user_name, new_password)

    return jsonify({'success': True, 'message': '密码重置成功'})


@app.route('/api/ad/password/query', methods=['GET'])
def query_password():
    """查询已存储的密码"""
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({'error': '无法识别用户身份'}), 400

    record = get_password(user_id)

    if not record:
        return jsonify({
            'success': False,
            'message': '未找到已存储的密码',
            'data': None
        })

    return jsonify({
        'success': True,
        'data': {
            'password': record['password'],
            'updatedAt': record['updated_at']
        }
    })


@app.route('/api/db/init', methods=['GET'])
def check_db():
    """检查数据库连接"""
    try:
        db = get_db()
        db.execute('SELECT 1')
        return jsonify({'success': True, 'message': '数据库连接正常'})
    except Exception as e:
        return jsonify({'error': f'数据库错误: {str(e)}'}), 500


# ==================== AD 操作函数 ====================

def ad_reset_password(user_account: str, new_password: str) -> dict:
    """修改 AD 密码"""
    try:
        from ldap3 import ALL, Connection, MODIFY_REPLACE, Server
        from ldap3.core.exceptions import LDAPException

        # 检查是否使用 LDAPS
        use_ssl = AD_LDAP_URL.lower().startswith('ldaps://')
        
        if use_ssl:
            server = Server(AD_LDAP_URL, get_info=ALL, use_ssl=True)
        else:
            server = Server(AD_LDAP_URL, get_info=ALL)
        
        conn = Connection(
            server,
            user=AD_ADMIN_DN,
            password=AD_ADMIN_PASSWORD,
            auto_bind=True,
            raise_exceptions=True
        )
        
        # 非 SSL 连接需要启用 TLS
        if not use_ssl and hasattr(conn, 'start_tls'):
            try:
                conn.start_tls()
                print('LDAP STARTTLS 已启用')
            except Exception as tls_err:
                print(f'LDAP STARTTLS 失败（可能不支持）: {tls_err}')

        # 搜索用户
        search_filter = (f'(|(sAMAccountName={user_account})')
        conn.search(AD_BASE_DN, search_filter, attributes=['distinguishedName'])

        if not conn.entries:
            conn.unbind()
            return {'success': False, 'message': '未找到AD用户'}

        user_dn = conn.entries[0].distinguishedName.values[0]

        # 修改密码 (使用 unicodePwd)
        password_value = f'"{new_password}"'.encode('utf-16-le')
        conn.modify(user_dn, {'unicodePwd': [(MODIFY_REPLACE, [password_value])]})

        conn.unbind()

        if conn.result['result'] == 0:
            return {'success': True, 'message': '密码修改成功'}
        else:
            return {'success': False, 'message': f'密码修改失败: {conn.result}'}

    except LDAPException as e:
        return {'success': False, 'message': f'LDAP错误: {str(e)}'}
    except Exception as e:
        return {'success': False, 'message': f'错误: {str(e)}'}


# ==================== 数据库操作函数 ====================

def save_password(user_id: str, user_account: str, user_name: str, password: str):
    """保存密码到数据库"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO passwords (user_id, user_account, user_name, password, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            user_account = COALESCE(excluded.user_account, user_account),
            password = excluded.password,
            user_name = COALESCE(excluded.user_name, user_name),
            updated_at = excluded.updated_at
    ''', (user_id, user_account, user_name, password, datetime.now().isoformat()))
    db.commit()


def get_password(user_id: str) -> dict:
    """从数据库获取密码"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM passwords WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if row:
        return dict(row)
    return None


# ==================== 前端页面路由 ====================

@app.route('/')
def index():
    """主页"""
    return app.send_static_file('index.html')


# ==================== 启动应用 ====================

if __name__ == '__main__':
    init_db()

    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5002))

    print(f'启动服务: http://{host}:{port}')
    app.run(host=host, port=port, debug=False)
