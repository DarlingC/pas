#!/bin/bash

# AD 密码管理服务启动脚本

cd "$(dirname "$0")"

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 python3"
    exit 1
fi

# 安装依赖
echo "安装依赖..."
pip3 install -r requirements.txt -q

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "警告: .env 文件不存在，已创建示例文件"
    cp .env.example .env
    echo "请编辑 .env 文件配置 AD 和飞书参数"
fi

# 启动服务
echo "启动服务..."
python3 app.py
