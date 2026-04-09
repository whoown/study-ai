#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import uuid
import subprocess
import shutil

# ========= 用户配置区域（必须修改） =========

SERVER_PORT = 443
SNI = "loewe.com"

UUID_DIRECT = ""
UUID_RELAY_VPS = ""
UUID_RELAY_PROXY = ""

RELAY_VPS_ADDRESS = "1.2.3.4"
RELAY_VPS_PORT = 443

PROXY_TYPE = "socks5"  # socks5 或 http
PROXY_ADDRESS = "127.0.0.1:1080"
PROXY_USERNAME = "user"
PROXY_PASSWORD = "pass"

# ==========================================

INSTALL_PATH = "/usr/local/bin/sing-box"
CONFIG_PATH = "/etc/sing-box/config.json"


def run(cmd):
    """执行 shell 命令"""
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def ensure_root():
    """确保 root 权限"""
    if os.geteuid() != 0:
        print("请使用 root 运行")
        exit(1)


def install_singbox():
    """幂等安装 sing-box"""
    if os.path.exists(INSTALL_PATH):
        print("sing-box 已安装，跳过")
        return

    print("安装 sing-box...")
    run("curl -fsSL https://sing-box.app/install.sh | bash")


def enable_bbr():
    """开启 BBR（幂等）"""
    print("尝试开启 BBR...")
    run("sysctl -w net.core.default_qdisc=fq")
    run("sysctl -w net.ipv4.tcp_congestion_control=bbr")


def gen_uuid(u):
    """生成 UUID"""
    return u if u else str(uuid.uuid4())


def gen_reality_key():
    """生成 reality 密钥"""
    result = run("sing-box generate reality-keypair")
    lines = result.stdout.splitlines()
    private_key = lines[0].split(":")[1].strip()
    public_key = lines[1].split(":")[1].strip()
    return private_key, public_key


def backup_config():
    """备份配置"""
    if os.path.exists(CONFIG_PATH):
        shutil.copy(CONFIG_PATH, CONFIG_PATH + ".bak")
        print("已备份旧配置")


def write_config(private_key, uuids):
    """生成 sing-box 配置"""

    uuid_direct, uuid_vps, uuid_proxy = uuids

    config = {
        "log": {"level": "warn"},
        "inbounds": [
            {
                "type": "vless",
                "tag": "vless-in",
                "listen": "::",
                "listen_port": SERVER_PORT,
                "users": [
                    {"uuid": uuid_direct},
                    {"uuid": uuid_vps},
                    {"uuid": uuid_proxy}
                ],
                "tls": {
                    "enabled": True,
                    "server_name": SNI,
                    "reality": {
                        "enabled": True,
                        "handshake": {"server": SNI, "server_port": 443},
                        "private_key": private_key
                    }
                },
                "transport": {
                    "type": "tcp"
                }
            }
        ],
        "outbounds": [
            {"type": "direct", "tag": "direct"},

            {
                "type": "vless",
                "tag": "relay-vps",
                "server": RELAY_VPS_ADDRESS,
                "server_port": RELAY_VPS_PORT
            },

            {
                "type": PROXY_TYPE,
                "tag": "relay-proxy",
                "server": PROXY_ADDRESS.split(":")[0],
                "server_port": int(PROXY_ADDRESS.split(":")[1]),
                "username": PROXY_USERNAME,
                "password": PROXY_PASSWORD
            }
        ],
        "route": {
            "rules": [
                {
                    "inbound": ["vless-in"],
                    "user": [uuid_direct],
                    "outbound": "direct"
                },
                {
                    "inbound": ["vless-in"],
                    "user": [uuid_vps],
                    "outbound": "relay-vps"
                },
                {
                    "inbound": ["vless-in"],
                    "user": [uuid_proxy],
                    "outbound": "relay-proxy"
                }
            ]
        }
    }

    os.makedirs("/etc/sing-box", exist_ok=True)

    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    print("配置写入完成")


def setup_service():
    """systemd 服务"""
    service = f"""
[Unit]
Description=sing-box
After=network.target

[Service]
ExecStart={INSTALL_PATH} run -c {CONFIG_PATH}
Restart=always

[Install]
WantedBy=multi-user.target
"""

    with open("/etc/systemd/system/sing-box.service", "w") as f:
        f.write(service)

    run("systemctl daemon-reexec")
    run("systemctl enable sing-box")
    run("systemctl restart sing-box")


def generate_urls(public_key, uuids):
    """生成 VLESS URL"""
    ip = run("curl -s ifconfig.me").stdout.strip()

    urls = []

    for u in uuids:
        url = f"vless://{u}@{ip}:{SERVER_PORT}?encryption=none&security=reality&sni={SNI}&fp=chrome&pbk={public_key}&type=tcp#route"
        urls.append(url)

    return urls


def main():
    ensure_root()
    install_singbox()
    enable_bbr()

    uuid1 = gen_uuid(UUID_DIRECT)
    uuid2 = gen_uuid(UUID_RELAY_VPS)
    uuid3 = gen_uuid(UUID_RELAY_PROXY)

    private_key, public_key = gen_reality_key()

    backup_config()
    write_config(private_key, (uuid1, uuid2, uuid3))
    setup_service()

    urls = generate_urls(public_key, (uuid1, uuid2, uuid3))

    print("\n=== VLESS Reality URLs ===")
    print("直连:\n", urls[0])
    print("VPS中转:\n", urls[1])
    print("住宅代理:\n", urls[2])


if __name__ == "__main__":
    main()