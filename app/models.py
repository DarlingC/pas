import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'passwords.db')

def get_db():
    """获取数据库连接"""
    from flask import g
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(exception=None):
    """关闭数据库连接"""
    from flask import g
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """初始化数据库"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS passwords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL UNIQUE,
            ad_username TEXT,
            user_name TEXT,
            email TEXT,
            password TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # 添加 email 字段（如果不存在）
    try:
        cursor.execute('ALTER TABLE passwords ADD COLUMN email TEXT')
    except:
        pass
    conn.commit()
    conn.close()

def ad_reset_password(ad_username: str, new_password: str) -> dict:
    """修改 AD 密码"""
    try:
        from ldap3 import Server, Connection, MODIFY_REPLACE
        
        from flask import current_app
        ad_url = current_app.config.get('AD_LDAP_URL')
        base_dn = current_app.config.get('AD_BASE_DN')
        admin_dn = current_app.config.get('AD_ADMIN_DN')
        admin_password = current_app.config.get('AD_ADMIN_PASSWORD')
        
        server = Server(ad_url, get_info=None)
        conn = Connection(server, user=admin_dn, password=admin_password, auto_bind=True)
        
        # 搜索用户
        search_filter = f'(sAMAccountName={ad_username})'
        conn.search(base_dn, search_filter, attributes=['distinguishedName'])
        
        if not conn.entries:
            conn.unbind()
            return {'success': False, 'message': f'未找到 AD 用户: {ad_username}'}
        
        user_dn = conn.entries[0].distinguishedName.values[0]
        
        # 修改密码
        password_value = f'"{new_password}"'.encode('utf-16-le')
        conn.modify(user_dn, {
            'unicodePwd': [(MODIFY_REPLACE, [password_value])]
        })
        
        result_code = conn.result['result']
        conn.unbind()
        
        if result_code == 0:
            return {'success': True, 'message': '密码修改成功'}
        else:
            return {'success': False, 'message': '密码修改失败'}
            
    except Exception as e:
        return {'success': False, 'message': f'错误: {str(e)}'}

def save_password(user_id: str, ad_username: str, user_name: str, email: str, password: str):
    """保存密码到数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO passwords (user_id, ad_username, user_name, email, password, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            ad_username = COALESCE(excluded.ad_username, ad_username),
            user_name = COALESCE(excluded.user_name, user_name),
            email = COALESCE(excluded.email, email),
            password = excluded.password,
            updated_at = excluded.updated_at
    ''', (user_id, ad_username, user_name, email, password, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_password_by_user_id(user_id: str) -> dict:
    """通过 user_id 获取密码"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM passwords WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None
