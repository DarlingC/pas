#!/bin/bash
# AD 密码管理服务启动脚本

cd "$(dirname "$0")"

echo "检查环境..."
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 python3"
    exit 1
fi

echo "安装依赖..."
pip3 install -r requirements.txt -q

echo "启动服务..."
python3 run.py
