import os
import sqlite3
import time
import threading
import re
from datetime import datetime
import requests
import logging
from dotenv import load_dotenv
from flask import Flask, jsonify, request, g, session
from cryptography.fernet import Fernet
from ldap3 import ALL, Connection, MODIFY_REPLACE, Server
from ldap3.core.exceptions import LDAPException
from ldap3.utils.conv import escape_filter_chars  # 引入转义方法


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
# 加载环境变量
load_dotenv()

# 从环境变量获取配置
AD_LDAP_URL = os.getenv('AD_LDAP_URL', 'ldap://domain.com:389')
AD_BASE_DN = os.getenv('AD_BASE_DN', 'DC=domain,DC=com')
AD_ADMIN_DN = os.getenv('AD_ADMIN_DN', 'CN=Admin,CN=Users,DC=domain,DC=com')
AD_ADMIN_PASSWORD = os.getenv('AD_ADMIN_PASSWORD', '')
FEISHU_APP_ID = os.getenv('FEISHU_APP_ID', '')
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET', '')

# 获取加密密钥
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
if not ENCRYPTION_KEY:
    logger.error("环境变量中缺少 ENCRYPTION_KEY")
    raise ValueError("必须在环境变量中配置 ENCRYPTION_KEY")
cipher_suite = Fernet(ENCRYPTION_KEY.encode('utf-8'))

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'passwords.db')

# 创建 Flask 应用
app = Flask(__name__, static_folder='static', static_url_path='')
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', os.urandom(24))


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
    # 1. 创建密码表
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
    try:
        cursor.execute('ALTER TABLE passwords ADD COLUMN user_account TEXT')
    except sqlite3.OperationalError:
        pass

    # 2. 新增：创建系统缓存表（用于多进程共享 Token）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_cache (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            expire_at REAL NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


# ==================== 飞书相关接口 ====================

# 保留线程锁，防止单个进程内的多线程并发击穿飞书接口
_token_lock = threading.Lock()


def get_valid_tenant_access_token():
    """获取有效的 tenant_access_token（使用 SQLite 共享缓存，完美支持多进程部署）"""
    current_time = time.time()
    db = get_db()
    cursor = db.cursor()

    # 1. 第一层快速检查：从数据库读取缓存
    cursor.execute('SELECT value, expire_at FROM system_cache WHERE key = ?', ('tenant_access_token',))
    row = cursor.fetchone()

    # 如果缓存存在且剩余时间 > 30分钟(1800秒)，直接返回
    if row and (row['expire_at'] - current_time > 1800):
        return row['value']

    # 2. 缓存失效时，加锁防止多线程重复拉取
    with _token_lock:
        # 获取到锁后进行第二层检查（防止在等待锁的期间，别的线程/进程已经更新了数据库）
        cursor.execute('SELECT value, expire_at FROM system_cache WHERE key = ?', ('tenant_access_token',))
        row = cursor.fetchone()
        if row and (row['expire_at'] - current_time > 1800):
            return row['value']

        try:
            # 重新请求飞书接口
            token_url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
            token_response = requests.post(
                token_url,
                json={
                    'app_id': FEISHU_APP_ID,
                    'app_secret': FEISHU_APP_SECRET
                },
                timeout=5
            )
            token_data = token_response.json()

            if token_data.get('code') == 0:
                new_token = token_data.get('tenant_access_token')
                # expire_at = 当前时间戳 + 飞书返回的有效时间(通常是7200秒)
                expire_at = current_time + token_data.get('expire', 7200)

                # 写入数据库，所有进程将共享这个最新 Token
                cursor.execute('''
                    INSERT INTO system_cache (key, value, expire_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        expire_at = excluded.expire_at
                ''', ('tenant_access_token', new_token, expire_at))
                db.commit()

                return new_token
        except Exception as e:
            logger.error(f"获取飞书 Token 时发生错误: {e}")

    return None


def validate_password_complexity(password: str) -> bool:
    """后端同步校验密码复杂度：至少8位，包含大写、小写、数字、特殊字符中的3种"""
    if len(password) < 8:
        return False

    count = 0
    if re.search(r"[a-z]", password): count += 1  # 包含小写
    if re.search(r"[A-Z]", password): count += 1  # 包含大写
    if re.search(r"\d", password): count += 1  # 包含数字
    if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password): count += 1  # 包含特殊字符

    return count >= 3


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
            # 1. 获取（或从缓存读取） tenant_access_token
            tenant_access_token = get_valid_tenant_access_token()

            if not tenant_access_token:
                return jsonify({'error': '获取 tenant_access_token 失败，请检查网络或配置'}), 401

            # 2. 用 code 换取 user_access_token
            user_token_url = 'https://open.feishu.cn/open-apis/authen/v1/oidc/access_token'
            user_token_response = requests.post(
                user_token_url,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {tenant_access_token}'
                },
                json={
                    'grant_type': 'authorization_code',
                    'code': code
                },
                timeout=5
            )
            user_token_data = user_token_response.json()

            if user_token_data.get('code') != 0:
                return jsonify({
                    'error': user_token_data.get('msg', '换取user_access_token失败')
                }), 401

            user_access_token = user_token_data.get('data', {}).get('access_token')
            if not user_access_token:
                return jsonify({'error': '未获取到user_access_token'}), 401

            # 3. 获取用户信息
            user_info_url = 'https://open.feishu.cn/open-apis/authen/v1/user_info'
            user_info_response = requests.get(
                user_info_url,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {user_access_token}'
                },
                timeout=5
            )
            user_info_data = user_info_response.json()

            if user_info_data.get('code') == 0 and user_info_data.get('data'):
                user = user_info_data['data']

                # 将身份信息写入 Session 保护
                session['user_id'] = user.get('user_id')
                session['email'] = user.get('email')
                session['user_name'] = user.get('name')
                logger.info(f"用户已授权登录: {user.get('name')} ({user.get('user_id')})")
                return jsonify({'success': True, 'data': user})

            return jsonify({'error': '获取用户信息失败'}), 401

        except Exception as e:
            logger.error(f"获取用户信息错误: {e}")
            return jsonify({'error': '服务器内部通讯错误，请稍后再试'}), 500

    return jsonify({'error': '缺少授权码'}), 400


# ==================== AD 密码相关接口 ====================

@app.route('/api/ad/password/reset', methods=['POST'])
def reset_password():
    """重置 AD 密码"""
    if 'user_id' not in session:
        return jsonify({'error': '未授权，请重试'}), 401

    data = request.get_json()
    new_password = data.get('newPassword')
    confirm_password = data.get('confirmPassword')

    if not new_password or not confirm_password:
        return jsonify({'error': '请填写新密码和确认密码'}), 400

    if new_password != confirm_password:
        return jsonify({'error': '两次输入的密码不一致'}), 400

    if len(new_password) < 8:
        return jsonify({'error': '密码长度不能少于8位'}), 400

    if not validate_password_complexity(new_password):
        return jsonify({'error': '密码不符合复杂度要求（需含大小写字母、数字或特殊字符中的三种）'}), 400

    # 强制从 Session 中获取可信信息
    user_id = session['user_id']
    user_name = session['user_name']
    email = session.get('email', '')
    user_account = email.split('@')[0] if email else None

    if not user_account:
        return jsonify({'error': '无法获取用户账号信息'}), 400

    # 调用 AD 修改密码
    result = ad_reset_password(user_account, new_password)

    if not result['success']:
        return jsonify({'error': result['message']}), 500

    # 保存加密密码到数据库
    save_password(user_id, user_account, user_name, new_password)
    logger.info(f"账号 {user_account} 密码重置成功")
    return jsonify({'success': True, 'message': '密码重置成功'})


@app.route('/api/ad/password/query', methods=['GET'])
def query_password():
    """查询已存储的密码"""
    if 'user_id' not in session:
        return jsonify({'error': '未授权，请重试'}), 401

    # 强制从 Session 中获取可信信息
    user_id = session['user_id']
    email = session.get('email', '')
    user_account = email.split('@')[0] if email else ''

    if not user_id or not user_account:
        return jsonify({'error': '无法识别用户身份'}), 400

    record = get_password(user_id, user_account)

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


# ==================== AD 操作函数 ====================

def ad_reset_password(user_account: str, new_password: str) -> dict:
    """修改 AD 密码"""
    try:
        # 对外部输入进行严格转义，防止 LDAP 注入
        safe_user_account = escape_filter_chars(user_account)
        server = Server(AD_LDAP_URL, get_info=ALL)
        with Connection(server, user=AD_ADMIN_DN, password=AD_ADMIN_PASSWORD, auto_bind=True) as conn:
            # 搜索用户
            search_filter = f'(sAMAccountName={safe_user_account})'
            conn.search(AD_BASE_DN, search_filter, attributes=['distinguishedName'])

            if not conn.entries:
                return {'success': False, 'message': '未找到AD用户,请联系IT'}

            user_dn = conn.entries[0].distinguishedName.values[0]

            # 修改密码 (使用 unicodePwd)
            password_value = f'"{new_password}"'.encode('utf-16-le')
            # 在 AD 中，lockoutTime=0 表示解除锁定
            changes = {
                'unicodePwd': [(MODIFY_REPLACE, [password_value])],
                'lockoutTime': [(MODIFY_REPLACE, [0])]
            }
            conn.modify(user_dn, changes)

            if conn.result['result'] == 0:
                return {'success': True, 'message': '密码修改成功'}
            else:
                return {'success': False, 'message': f"修改失败: {conn.result.get('description', '未知错误')}"}

    except LDAPException as e:
        logger.error(f"LDAP操作异常: {str(e)}")
        return {'success': False, 'message': f'LDAP错误: 无法连接或修改'}
    except Exception as e:
        logger.error(f"AD修改未知异常: {str(e)}")
        return {'success': False, 'message': f'系统内部错误'}


# ==================== 数据库操作函数 ====================

def save_password(user_id: str, user_account: str, user_name: str, password: str):
    """加密并保存密码到数据库"""
    db = get_db()
    cursor = db.cursor()

    # 存入数据库前，对密码进行加密
    encrypted_password = cipher_suite.encrypt(password.encode('utf-8')).decode('utf-8')

    cursor.execute('''
        INSERT INTO passwords (user_id, user_account, user_name, password, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            user_account = COALESCE(excluded.user_account, user_account),
            password = excluded.password,
            user_name = COALESCE(excluded.user_name, user_name),
            updated_at = excluded.updated_at
    ''', (user_id, user_account, user_name, encrypted_password, datetime.now().isoformat()))
    db.commit()


def get_password(user_id: str, user_account: str) -> dict:
    """从数据库获取密码并解密"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM passwords WHERE user_id = ? AND user_account = ?', (user_id, user_account))
    row = cursor.fetchone()
    if row:
        record = dict(row)
        try:
            # 取出加密数据并解密
            decrypted_password = cipher_suite.decrypt(record['password'].encode('utf-8')).decode('utf-8')
            record['password'] = decrypted_password
        except Exception as e:
            logger.error(f"解密密码失败: {e}")
            record['password'] = "数据解密失败"
        return record
    return None


# ==================== 前端页面路由 ====================

@app.route('/')
def index():
    """主页"""
    response = app.send_static_file('index.html')
    response.headers['Cache-Control'] = 'no-store'
    return response


# ==================== 启动应用 ====================

if __name__ == '__main__':
    init_db()

    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5002))

    logger.info(f'启动服务: http://{host}:{port}')
    app.run(host=host, port=port, debug=False)
