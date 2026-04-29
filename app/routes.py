import os
import sqlite3
from flask import Blueprint, request, jsonify, current_app, g

bp = Blueprint('api', __name__, url_prefix='/api')

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'passwords.db')

def get_db():
    """获取数据库连接"""
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

# ==================== 飞书相关接口 ====================

@bp.route('/feishu/appid', methods=['GET'])
def get_appid():
    """返回飞书应用ID"""
    app_id = current_app.config.get('FEISHU_APP_ID')
    if not app_id:
        return jsonify({'error': '未配置飞书应用ID'}), 500
    return jsonify({'appid': app_id})

@bp.route('/feishu/user', methods=['GET'])
def get_user_info():
    """通过 code 获取用户信息（飞书 JSSDK 授权）"""
    import requests
    code = request.args.get('code')
    
    if not code:
        return jsonify({'error': '缺少授权码'}), 400
    
    try:
        app_id = current_app.config.get('FEISHU_APP_ID')
        app_secret = current_app.config.get('FEISHU_APP_SECRET')
        
        # 获取 app_access_token
        token_response = requests.post(
            'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
            json={'app_id': app_id, 'app_secret': app_secret},
            timeout=10
        )
        token_data = token_response.json()
        
        if token_data.get('code') != 0:
            return jsonify({'error': '获取access_token失败'}), 401
        
        app_access_token = token_data.get('tenant_access_token')
        
        # 用 code 换取 user_access_token
        user_token_response = requests.post(
            'https://open.feishu.cn/open-apis/authen/v1/oidc/access_token',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {app_access_token}'
            },
            json={'grant_type': 'authorization_code', 'code': code},
            timeout=10
        )
        user_token_data = user_token_response.json()
        
        if user_token_data.get('code') != 0:
            return jsonify({'error': user_token_data.get('msg', '换取user_access_token失败')}), 401
        
        user_access_token = user_token_data.get('data', {}).get('access_token')
        if not user_access_token:
            return jsonify({'error': '未获取到user_access_token'}), 401
        
        # 获取用户信息
        user_info_response = requests.get(
            'https://open.feishu.cn/open-apis/authen/v1/user_info',
            headers={'Authorization': f'Bearer {user_access_token}'},
            timeout=10
        )
        user_info_data = user_info_response.json()
        
        if user_info_data.get('code') == 0 and user_info_data.get('data'):
            user = user_info_data['data']
            return jsonify({
                'success': True,
                'data': {
                    'user_id': user.get('open_id') or user.get('user_id') or '',
                    'union_id': user.get('union_id'),
                    'name': user.get('name') or '',
                    'en_name': user.get('en_name'),
                    'email': user.get('email'),
                    'mobile': user.get('mobile'),
                    '_raw': user
                }
            })
        
        return jsonify({'error': '获取用户信息失败'}), 401
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== AD 密码相关接口 ====================

@bp.route('/ad/password/reset', methods=['POST'])
def reset_password():
    """重置 AD 密码"""
    data = request.get_json()
    new_password = data.get('newPassword')
    confirm_password = data.get('confirmPassword')
    user_id = data.get('user_id')
    user_name = data.get('user_name')
    email = data.get('email')
    
    if not new_password or not confirm_password:
        return jsonify({'error': '请填写新密码和确认密码'}), 400
    
    if new_password != confirm_password:
        return jsonify({'error': '两次输入的密码不一致'}), 400
    
    if len(new_password) < 8:
        return jsonify({'error': '密码长度不能少于8位'}), 400
    
    if not user_id:
        return jsonify({'error': '无法识别用户身份'}), 400
    
    # 从邮箱提取 AD 用户名
    if email:
        ad_username = email.split('@')[0]
    else:
        return jsonify({'error': '无法获取用户邮箱信息'}), 400
    
    # 调用 AD 修改密码
    from app.models import ad_reset_password, save_password as db_save_password
    result = ad_reset_password(ad_username, new_password)
    
    if not result['success']:
        return jsonify({'error': result['message']}), 500
    
    # 保存密码到数据库
    db_save_password(user_id, ad_username, user_name, email, new_password)
    
    return jsonify({'success': True, 'message': '密码重置成功'})

@bp.route('/ad/password/query', methods=['GET'])
def query_password():
    """查询已存储的密码"""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': '无法识别用户身份'}), 400
    
    from app.models import get_password_by_user_id
    record = get_password_by_user_id(user_id)
    
    if not record:
        return jsonify({'success': False, 'message': '未找到已存储的密码', 'data': None})
    
    return jsonify({
        'success': True,
        'data': {
            'password': record['password'],
            'updatedAt': record['updated_at']
        }
    })

@bp.route('/db/init', methods=['GET'])
def check_db():
    """检查数据库连接"""
    try:
        db = get_db()
        db.execute('SELECT 1')
        return jsonify({'success': True, 'message': '数据库连接正常'})
    except Exception as e:
        return jsonify({'error': f'数据库错误: {str(e)}'}), 500
