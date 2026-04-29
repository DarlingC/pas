# AD密码管理工具

飞书内部应用，用于管理 AD 域账号密码。

## 功能

1. **密码重置**：用户输入新密码并确认，调用微软 AD 进行密码修改
2. **密码查询**：用户查询并复制已存储的密码

## 目录结构

```
├── app/
│   ├── __init__.py    # Flask 应用工厂
│   ├── routes.py      # 路由和 API
│   └── models.py      # 数据模型和 AD 操作
├── public/
│   └── index.html     # 前端页面
├── run.py             # 启动入口
├── requirements.txt   # Python 依赖
└── .env.example       # 环境变量示例
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 主页 |
| `/api/feishu/appid` | GET | 获取飞书 App ID |
| `/api/feishu/user` | GET | 通过 code 获取用户信息 |
| `/api/ad/password/reset` | POST | 重置 AD 密码 |
| `/api/ad/password/query` | GET | 查询已存储的密码 |
| `/api/db/init` | GET | 数据库连接检查 |

## 环境变量

| 变量名 | 说明 |
|--------|------|
| `AD_LDAP_URL` | AD LDAP 服务器地址 |
| `AD_BASE_DN` | AD 基础 DN |
| `AD_ADMIN_DN` | AD 管理员 DN |
| `AD_ADMIN_PASSWORD` | AD 管理员密码 |
| `FEISHU_APP_ID` | 飞书应用 App ID |
| `FEISHU_APP_SECRET` | 飞书应用 App Secret |
| `FLASK_PORT` | 服务端口（默认 5002） |
