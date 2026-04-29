import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'passwords.db')

def init_db():
    """初始化数据库"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS passwords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            open_id TEXT NOT NULL UNIQUE,
            ad_username TEXT NOT NULL,
            user_name TEXT,
            password TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
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
        print(f'搜索 AD 用户: {search_filter}')
        conn.search(base_dn, search_filter, attributes=['distinguishedName', 'cn'])
        
        if not conn.entries:
            conn.unbind()
            return {'success': False, 'message': f'未找到 AD 用户: {ad_username}'}
        
        user_dn = conn.entries[0].distinguishedName.values[0]
        print(f'找到用户 DN: {user_dn}')
        
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
            return {'success': False, 'message': f'密码修改失败: {conn.result}'}
            
    except Exception as e:
        print(f'AD 错误: {e}')
        return {'success': False, 'message': f'错误: {str(e)}'}

def save_password(open_id: str, ad_username: str, user_name: str, password: str):
    """保存密码到数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO passwords (open_id, ad_username, user_name, password, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(open_id) DO UPDATE SET
            ad_username = excluded.ad_username,
            user_name = COALESCE(excluded.user_name, user_name),
            password = excluded.password,
            updated_at = excluded.updated_at
    ''', (open_id, ad_username, user_name, password, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_password_by_open_id(open_id: str) -> dict:
    """通过 open_id 获取密码"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM passwords WHERE open_id = ?', (open_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_password_by_username(ad_username: str) -> dict:
    """通过 AD 用户名获取密码"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM passwords WHERE ad_username = ?', (ad_username,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None
