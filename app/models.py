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
            user_name TEXT,
            password TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def ad_reset_password(user_id: str, new_password: str) -> dict:
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
        search_filter = f'(|(sAMAccountName={user_id})(userPrincipalName={user_id}*))'
        conn.search(base_dn, search_filter, attributes=['distinguishedName'])
        
        if not conn.entries:
            conn.unbind()
            return {'success': False, 'message': '未找到AD用户'}
        
        user_dn = conn.entries[0].distinguishedName.values[0]
        
        # 修改密码
        password_value = f'"{new_password}"'.encode('utf-16-le')
        conn.modify(user_dn, {
            'unicodePwd': [(MODIFY_REPLACE, [password_value])]
        })
        
        conn.unbind()
        
        if conn.result['result'] == 0:
            return {'success': True, 'message': '密码修改成功'}
        else:
            return {'success': False, 'message': f'密码修改失败'}
            
    except Exception as e:
        return {'success': False, 'message': f'错误: {str(e)}'}

def save_password(user_id: str, user_name: str, password: str):
    """保存密码到数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO passwords (user_id, user_name, password, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            password = excluded.password,
            user_name = COALESCE(excluded.user_name, user_name),
            updated_at = excluded.updated_at
    ''', (user_id, user_name, password, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_password(user_id: str) -> dict:
    """从数据库获取密码"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM passwords WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None
