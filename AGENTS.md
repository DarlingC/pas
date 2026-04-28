# AD密码管理工具 - AGENTS.md

## 项目概述

飞书内部应用，用于管理 AD 域账号密码：
1. **密码重置**：用户输入新密码并确认，调用微软 AD 进行密码修改
2. **密码查询**：用户查询并复制已存储的密码

## 技术栈

- **Framework**: Next.js 16 (App Router)
- **Core**: React 19
- **Language**: TypeScript 5
- **UI 组件**: shadcn/ui (基于 Radix UI)
- **Styling**: Tailwind CSS 4
- **数据库**: SQLite (better-sqlite3)
- **飞书集成**: @larksuiteoapi/node-sdk
- **AD 集成**: ldapjs

## 环境变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `AD_LDAP_URL` | AD LDAP 服务器地址 | `ldap://domain.com:389` |
| `AD_BASE_DN` | AD 基础 DN | `DC=domain,DC=com` |
| `AD_ADMIN_DN` | AD 管理员 DN | `CN=Admin,CN=Users,DC=domain,DC=com` |
| `AD_ADMIN_PASSWORD` | AD 管理员密码 | - |
| `FEISHU_APP_ID` | 飞书应用 App ID | cli_xxx |
| `FEISHU_APP_SECRET` | 飞书应用 App Secret | - |

## 目录结构

```
src/
├── app/
│   ├── api/
│   │   ├── feishu/user/route.ts    # 飞书用户信息获取
│   │   ├── ad/password/reset/route.ts  # AD 密码重置
│   │   ├── ad/password/query/route.ts   # 密码查询
│   │   └── db/
│   │       └── init/route.ts      # 数据库初始化
│   ├── page.tsx                   # 主页
│   └── layout.tsx                 # 布局
├── lib/
│   ├── db.ts                      # SQLite 数据库操作
│   ├── feishu.ts                  # 飞书客户端
│   └── ad.ts                      # AD LDAP 操作
└── components/
    └── password-form.tsx          # 密码表单组件
```

## API 接口

### 1. 获取飞书用户信息
- **路径**: `/api/feishu/user`
- **方法**: GET
- **描述**: 获取当前飞书用户信息

### 2. 重置 AD 密码
- **路径**: `/api/ad/password/reset`
- **方法**: POST
- **参数**: `{ userId: string, newPassword: string }`
- **描述**: 重置用户 AD 密码并存储到 SQLite

### 3. 查询密码
- **路径**: `/api/ad/password/query`
- **方法**: GET
- **参数**: `?userId=xxx`
- **描述**: 查询用户已存储的密码

## 数据库 Schema

```sql
CREATE TABLE IF NOT EXISTS passwords (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL UNIQUE,
  password TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```
