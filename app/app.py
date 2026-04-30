"""
AD 密码管理应用
Flask 后端
"""
import os
import re
import json
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

load_dotenv()

# 环境变量
AD_LDAP_URL = os.getenv("AD_LDAP_URL", "ldaps://localhost:636")
AD_BASE_DN = os.getenv("AD_BASE_DN", "DC=domain,DC=com")
AD_ADMIN_DN = os.getenv("AD_ADMIN_DN", "")
AD_ADMIN_PASSWORD = os.getenv("AD_ADMIN_PASSWORD", "")
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5002"))
DATABASE_PATH = os.getenv("DATABASE_PATH", "passwords.db")


def create_app():
    """创建 Flask 应用"""
    app = Flask(__name__, static_folder="../public", static_url_path="")
    
    # ==================== 数据库操作 ====================
    def get_db():
        """获取数据库连接"""
        import sqlite3
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db():
        """初始化数据库"""
        import sqlite3
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS passwords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL UNIQUE,
                user_account TEXT,
                user_name TEXT,
                email TEXT,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    
    def save_password(user_id: str, user_account: str, user_name: str, email: str, password: str) -> bool:
        """保存或更新密码"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO passwords (user_id, user_account, user_name, email, password, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                user_account = excluded.user_account,
                user_name = excluded.user_name,
                email = excluded.email,
                password = excluded.password,
                updated_at = excluded.updated_at
        """, (user_id, user_account, user_name, email, password, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return True
    
    def get_password_by_user_id(user_id: str) -> dict:
        """根据 user_id 获取密码"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM passwords WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None
    
    def check_user_exists(user_account: str) -> bool:
        """检查用户是否存在于 AD"""
        try:
            from ldap3 import ALL, Connection, Server
            from ldap3.core.exceptions import LDAPException
            
            use_ssl = AD_LDAP_URL.lower().startswith("ldaps://")
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
            if not use_ssl and hasattr(conn, "start_tls"):
                try:
                    conn.start_tls()
                except Exception:
                    pass
            
            # 搜索用户 DN
            search_filter = f"(sAMAccountName={user_account})"
            conn.search(
                search_base=AD_BASE_DN,
                search_filter=search_filter,
                search_scope="SUBTREE",
                attributes=["distinguishedName"]
            )
            
            exists = len(conn.response) > 0
            conn.unbind()
            return exists
            
        except LDAPException as e:
            print(f"AD 查询失败: {e}")
            return False
    
    def ad_reset_password(user_account: str, new_password: str) -> dict:
        """修改 AD 密码"""
        try:
            from ldap3 import ALL, Connection, MODIFY_REPLACE, Server
            from ldap3.core.exceptions import LDAPException
            
            # 检查是否使用 LDAPS
            use_ssl = AD_LDAP_URL.lower().startswith("ldaps://")
            
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
            if not use_ssl and hasattr(conn, "start_tls"):
                try:
                    conn.start_tls()
                    print("LDAP STARTTLS 已启用")
                except Exception as tls_err:
                    print(f"LDAP STARTTLS 失败（可能不支持）: {tls_err}")
            
            # 搜索用户 DN
            search_filter = f"(sAMAccountName={user_account})"
            conn.search(
                search_base=AD_BASE_DN,
                search_filter=search_filter,
                search_scope="SUBTREE",
                attributes=["distinguishedName"]
            )
            
            if not conn.response or len(conn.response) == 0:
                conn.unbind()
                return {"success": False, "error": "未找到 AD 用户"}
            
            user_dn = conn.response[0]["attributes"]["distinguishedName"]
            
            # 修改密码
            # unicodePwd 需要 UTF-16 LE 编码
            import base64
            new_password_unicode = '"' + new_password + '"'
            new_password_bytes = new_password_unicode.encode("utf-16-le")
            new_password_b64 = base64.b64encode(new_password_bytes).decode("ascii")
            
            conn.modify(
                user_dn,
                {
                    "unicodePwd": [(MODIFY_REPLACE, [new_password_b64])]
                }
            )
            
            result = conn.result
            conn.unbind()
            
            if result["result"] == 0:
                return {"success": True}
            else:
                error_msg = result.get("message", "")
                error_code = result.get("result", 0)
                
                # 错误信息映射
                error_messages = {
                    32: "AD 用户不存在",
                    49: "AD 凭据无效，请联系管理员",
                    50: "AD 权限不足，请联系管理员",
                    53: "密码不符合 AD 策略要求（需满足复杂度）",
                    64: "AD 用户名格式错误",
                    76: "密码不符合最小使用年限要求",
                }
                
                friendly_error = error_messages.get(error_code, f"AD 错误 ({error_code}): {error_msg}")
                return {"success": False, "error": friendly_error}
                
        except LDAPException as e:
            return {"success": False, "error": f"LDAP 错误: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"系统错误: {str(e)}"}
    
    # 初始化数据库
    init_db()
    
    # ==================== 路由 ====================
    
    @app.route("/")
    def index():
        """主页"""
        return send_from_directory("../public", "index.html")
    
    @app.route("/api/feishu/appid")
    def get_feishu_appid():
        """获取飞书 App ID"""
        return jsonify({"appid": FEISHU_APP_ID})
    
    @app.route("/api/feishu/user")
    def get_feishu_user():
        """通过 code 获取飞书用户信息"""
        code = request.args.get("code")
        if not code:
            return jsonify({"success": False, "error": "缺少 code 参数"}), 401
        
        try:
            # 获取 app_access_token
            import requests as req
            token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            token_resp = req.post(
                token_url,
                json={
                    "app_id": FEISHU_APP_ID,
                    "app_secret": FEISHU_APP_SECRET
                }
            )
            token_data = token_resp.json()
            print("token_data:", token_data)
            
            if token_data.get("code") != 0:
                return jsonify({
                    "success": False,
                    "error": f"获取 app_access_token 失败: {token_data.get('msg')}"
                }), 500
            
            app_token = token_data.get("tenant_access_token")
            
            # 获取 user_access_token
            user_token_url = "https://open.feishu.cn/open-apis/authen/v1/oidc/access_token"
            user_token_resp = req.post(
                user_token_url,
                headers={
                    "Authorization": f"Bearer {app_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "grant_type": "authorization_code",
                    "code": code
                }
            )
            user_token_data = user_token_resp.json()
            print("user_token_data:", user_token_data)
            
            if user_token_data.get("code") != 0:
                return jsonify({
                    "success": False,
                    "error": f"获取 user_access_token 失败: {user_token_data.get('msg')}"
                }), 500
            
            user_token = user_token_data.get("data", {}).get("access_token")
            
            # 获取用户信息
            user_info_url = "https://open.feishu.cn/open-apis/contact/v3/users/me"
            user_info_resp = req.get(
                user_info_url,
                headers={"Authorization": f"Bearer {user_token}"},
                params={"user_id_type": "open_id"}
            )
            user_info_data = user_info_resp.json()
            print("user_info_data:", user_info_data)
            
            if user_info_data.get("code") != 0:
                return jsonify({
                    "success": False,
                    "error": f"获取用户信息失败: {user_info_data.get('msg')}"
                }), 500
            
            user_data = user_info_data.get("data", {}).get("user", {})
            
            # 返回用户信息
            return jsonify({
                "success": True,
                "data": {
                    "user_id": user_data.get("open_id"),
                    "union_id": user_data.get("union_id"),
                    "name": user_data.get("name"),
                    "en_name": user_data.get("en_name"),
                    "email": user_data.get("email"),
                    "mobile": user_data.get("mobile"),
                    "avatar_url": user_data.get("avatar", {}).get("avatar_72"),
                    "_raw": user_data
                }
            })
            
        except Exception as e:
            return jsonify({"success": False, "error": f"系统错误: {str(e)}"}), 500
    
    @app.route("/api/ad/password/reset", methods=["POST"])
    def reset_password():
        """重置 AD 密码"""
        data = request.get_json()
        new_password = data.get("newPassword")
        user_id = data.get("user_id")
        user_name = data.get("user_name")
        email = data.get("email")
        
        if not new_password:
            return jsonify({"success": False, "error": "请提供新密码"}), 400
        
        # 从邮箱提取 AD 用户名
        user_account = ""
        if email and "@" in email:
            user_account = email.split("@")[0]
        
        if not user_account:
            return jsonify({"success": False, "error": "无法确定 AD 用户名（邮箱为空）"}), 400
        
        # 检查 AD 用户是否存在
        if not check_user_exists(user_account):
            return jsonify({"success": False, "error": "未找到 AD 用户"}), 404
        
        # 修改 AD 密码
        result = ad_reset_password(user_account, new_password)
        
        if result["success"]:
            # 保存到本地数据库
            save_password(user_id, user_account, user_name, email, new_password)
            return jsonify({"success": True, "message": "密码重置成功"})
        else:
            return jsonify({"success": False, "error": result.get("error", "密码修改失败")}), 500
    
    @app.route("/api/ad/password/query")
    def query_password():
        """查询已存储的密码"""
        user_id = request.args.get("user_id")
        
        if not user_id:
            return jsonify({"success": False, "error": "缺少 user_id 参数"}), 400
        
        record = get_password_by_user_id(user_id)
        
        if record:
            return jsonify({
                "success": True,
                "data": {
                    "user_id": record["user_id"],
                    "user_account": record["user_account"],
                    "user_name": record["user_name"],
                    "email": record["email"],
                    "password": record["password"],
                    "createdAt": record["created_at"],
                    "updatedAt": record["updated_at"]
                }
            })
        else:
            return jsonify({"success": False, "error": "未找到已存储的密码"})
    
    @app.route("/api/db/init")
    def check_db():
        """数据库连接检查"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            return jsonify({
                "success": True,
                "message": "数据库连接正常",
                "tables": tables
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"数据库错误: {str(e)}"
            }), 500
    
    return app


# 启动应用
if __name__ == "__main__":
    print(f"启动服务: http://0.0.0.0:{FLASK_PORT}")
    app = create_app()
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=True)
