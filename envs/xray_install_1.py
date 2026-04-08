#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VLESS + WS + TLS 一键部署脚本（Nginx + Certbot）

功能：
1. 安装 Xray
2. 安装 Nginx + Certbot
3. 自动申请 TLS 证书
4. 配置 Nginx 反代 WebSocket
5. 启动服务
6. 输出 V2rayN 可用链接（TLS）

⚠️ 使用前必须：
- 已有域名并解析到服务器 IP
- 80/443 端口未被占用

运行：sudo python3 script.py
"""

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from urllib.parse import quote

# ========= 用户配置 =========
DOMAIN = "whoown.net"  # 必填（不能用 IP）
PORT = 8080  # Xray 内部端口
WS_PATH = "/graphql"
UUID = str(uuid.uuid4())
# ============================

CONFIG_PATH = Path("/usr/local/etc/xray/config.json")
NGINX_CONF = Path(f"/etc/nginx/sites-enabled/{DOMAIN}")


def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def run_ok(cmd):
    return run(cmd).returncode == 0


def install_base():
    print("安装基础组件...")
    run("apt update")
    run("apt install -y curl nginx certbot python3-certbot-nginx")


def install_xray():
    print("安装 Xray...")
    cmd = "curl -fsSL https://github.com/XTLS/Xray-install/raw/main/install-release.sh | bash"
    if not run_ok(cmd):
        print("Xray 安装失败")
        sys.exit(1)


def config_xray():
    print("配置 Xray...")

    if not WS_PATH.startswith("/"):
        raise ValueError("WS_PATH 必须以 / 开头")

    config = {
        "log": {"loglevel": "none"},
        "inbounds": [
            {
                "listen": "127.0.0.1",
                "port": PORT,
                "protocol": "vless",
                "settings": {
                    "clients": [{"id": UUID}],
                    "decryption": "none",
                },
                "streamSettings": {
                    "network": "ws",
                    "wsSettings": {"path": WS_PATH},
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls"],
                },
            }
        ],
        "outbounds": [{"protocol": "freedom"}],
    }

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=4) + "\n")

    if not run_ok("systemctl restart xray"):
        print("Xray 启动失败")
        sys.exit(1)

    run("systemctl enable xray")


def apply_cert():
    print("申请 TLS 证书...")
    cmd = f"certbot --nginx -d {DOMAIN} --non-interactive --agree-tos -m test@example.com"
    if not run_ok(cmd):
        print("证书申请失败，请检查域名解析")
        sys.exit(1)


def config_nginx():
    print("配置 Nginx WS 反代...")

    nginx_conf = f"""
server {{
    listen 443 ssl;
    server_name {DOMAIN};

    ssl_certificate /etc/letsencrypt/live/{DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{DOMAIN}/privkey.pem;

    location {WS_PATH} {{
        proxy_redirect off;
        proxy_pass http://127.0.0.1:{PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }}
}}
"""

    NGINX_CONF.write_text(nginx_conf)

    if not run_ok("nginx -t"):
        print("Nginx 配置错误")
        sys.exit(1)

    run("systemctl restart nginx")


def build_link():
    path = quote(WS_PATH, safe="/")
    return f"vless://{UUID}@{DOMAIN}:443?type=ws&path={path}&security=tls&encryption=none#TLS"


def main():
    if os.getuid() != 0:
        print("请使用 sudo 运行")
        sys.exit(1)

    install_base()
    install_xray()
    config_xray()
    # apply_cert()
    # config_nginx()

    link = build_link()

    print("\n===== 部署完成 =====")
    print(f"域名: {DOMAIN}")
    print(f"UUID: {UUID}")
    print(f"路径: {WS_PATH}")
    print("\nV2rayN 链接:")
    print(link)


if __name__ == "__main__":
    main()
