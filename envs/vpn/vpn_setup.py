#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import uuid
import subprocess
import shutil

# ==================== 1. 人工配置区 ====================
# 基础配置
LISTEN_PORT = 443
SNI_DOMAIN = "www.loewe.com"  # 用于 REALITY 伪装的域名（默认按需求设为 loewe.com）
DEST_SERVER = "www.loewe.com"  # 握手回落的目标服务器

# 三种出口对应的 UUID (如果为空则脚本自动生成)
UUID_JP_DIRECT = ""  # 出口1：日本原生落地
UUID_US_RELAY = ""  # 出口2：中转美国 VPS
UUID_US_RESIDENTIAL = ""  # 出口3：中转美国家宽代理

# 出口2：美国 VPS 详细配置
# 注意：美国出口 VPS 必须采用 vless+reality 方案，否则本脚本的 US-VPS 中转无法正常工作。
US_VPS_IP = "142.111.135.252"
US_VPS_PORT = 443
US_VPS_UUID = "da7071bc-7c30-4528-9030-75160d6f656d"  # 占位值（合法 UUID）
US_VPS_SNI = "www.adidas.com"  # 美国 VPS reality 的 server_name（SNI）
US_VPS_REALITY_PUBLIC_KEY = "vrSV0CE3x2u9UHom4Xk9r-nVBdYKKfcv7hskX751eUw"  # 占位值（合法 base64）
US_VPS_REALITY_SHORT_ID = "0123456789abcdef"
US_VPS_FINGERPRINT = "chrome"  # 常见值：chrome / firefox / safari
US_VPS_FLOW = "xtls-rprx-vision"
US_VPS_PLACEHOLDER_UUID = "00000000-0000-0000-0000-000000000002"
US_VPS_PLACEHOLDER_PBK = "dGVzdF9yZWFsaXR5X3B1YmxpY19rZXlfcGxhY2Vob2xkZXI"

# 出口3：美国家宽代理配置 (支持 socks5 或 http)
US_HOME_PROXY_TYPE = "socks"  # 支持 "socks5" 或 "http"
US_HOME_PROXY_IP = "92.112.8.173"
US_HOME_PROXY_PORT = 44445
US_HOME_PROXY_USER = "14a75d3380fa4"
US_HOME_PROXY_PASS = "7369311a40"

# Reality 密钥 (如果为空则脚本自动生成)
PRIVATE_KEY = ""
PUBLIC_KEY = ""
SHORT_ID = "0123456789abcdef"
# ======================================================

CONFIG_PATH = "/etc/sing-box/config.json"
SERVICE_PATH = "/etc/systemd/system/sing-box.service"
SINGBOX_CANDIDATES = ["/usr/local/bin/sing-box", "/usr/bin/sing-box"]


def run_cmd(cmd, check=True):
    """执行 shell 命令并返回标准输出，失败时给出明确报错。"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        stderr = result.stderr.strip() or "无错误输出"
        raise RuntimeError(f"命令执行失败: {cmd}\n错误信息: {stderr}")
    return result.stdout.strip()


def get_public_host_for_url():
    """仅获取用于 URL 的公网 IPv4 地址。"""
    candidates = [
        "curl -4 -s ifconfig.me",
        "curl -4 -s ip.sb",
    ]
    for cmd in candidates:
        ip = run_cmd(cmd, check=False).strip()
        if ip:
            return ip
    raise RuntimeError("无法获取公网 IPv4，请检查网络或手动填写服务器 IPv4 地址。")


def find_singbox_bin():
    """探测 sing-box 二进制路径，兼容常见安装目录。"""
    for path in SINGBOX_CANDIDATES:
        if os.path.exists(path):
            return path
    found = shutil.which("sing-box")
    return found if found else ""


def ensure_valid_proxy_type():
    """校验代理类型，避免写入非法 outbound 类型。"""
    valid_types = {"socks5", "socks", "http"}
    if US_HOME_PROXY_TYPE not in valid_types:
        raise ValueError(f"US_HOME_PROXY_TYPE 仅支持 {valid_types}，当前值: {US_HOME_PROXY_TYPE}")


def get_singbox_proxy_type():
    """将用户输入的代理类型映射到 sing-box outbound 类型。"""
    return "socks" if US_HOME_PROXY_TYPE == "socks5" else US_HOME_PROXY_TYPE


def is_us_vps_enabled():
    """判断美国 VPS 出口是否已完成配置。"""
    return not (US_VPS_UUID == US_VPS_PLACEHOLDER_UUID or US_VPS_REALITY_PUBLIC_KEY == US_VPS_PLACEHOLDER_PBK)


def is_us_home_enabled():
    """判断美国家宽出口是否已完成配置。"""
    return not ("x.x" in US_HOME_PROXY_IP)


def build_us_vps_outbound():
    """构建美国 VPS 出站。"""
    return {
        "type": "vless",
        "tag": "out-us-vps",
        "server": US_VPS_IP,
        "server_port": US_VPS_PORT,
        "uuid": US_VPS_UUID,
        "flow": US_VPS_FLOW,
        "tls": {
            "enabled": True,
            "server_name": US_VPS_SNI,
            "utls": {"enabled": True, "fingerprint": US_VPS_FINGERPRINT},
            "reality": {
                "enabled": True,
                "public_key": US_VPS_REALITY_PUBLIC_KEY,
                "short_id": US_VPS_REALITY_SHORT_ID,
            },
        },
    }


def update_sysctl_key(lines, key, value):
    """更新 sysctl 配置项；存在则覆盖，不存在则追加。"""
    new_line = f"{key}={value}\n"
    replaced = False
    updated_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}="):
            if not replaced:
                updated_lines.append(new_line)
                replaced = True
            continue
        updated_lines.append(line)
    if not replaced:
        updated_lines.append(new_line)
    return updated_lines


def ensure_bbr_sysctl_config():
    """以幂等方式写入 BBR 所需 sysctl 配置，避免重复污染文件。"""
    sysctl_path = "/etc/sysctl.conf"
    existing_lines = []
    if os.path.exists(sysctl_path):
        with open(sysctl_path, "r", encoding="utf-8") as f:
            existing_lines = f.readlines()
    existing_lines = update_sysctl_key(existing_lines, "net.core.default_qdisc", "fq")
    existing_lines = update_sysctl_key(existing_lines, "net.ipv4.tcp_congestion_control", "bbr")
    with open(sysctl_path, "w", encoding="utf-8") as f:
        f.writelines(existing_lines)


def backup_config(config_path):
    """写入新配置前先备份旧配置。"""
    if os.path.exists(config_path):
        backup_path = f"{config_path}.bak"
        shutil.copy2(config_path, backup_path)
        print(f"[+] 已备份旧配置: {backup_path}")


def setup_bbr():
    """开启 BBR 加速 (幂等处理)"""
    print("[*] 检查并开启 BBR...")
    current_qdisc = run_cmd("sysctl -n net.core.default_qdisc")
    current_algo = run_cmd("sysctl -n net.ipv4.tcp_congestion_control")

    if current_qdisc != "fq" or current_algo != "bbr":
        ensure_bbr_sysctl_config()
        run_cmd("sysctl -p")
        print("[+] BBR 已启用")
    else:
        print("[!] BBR 已经是在运行状态")


def install_singbox():
    """安装 Sing-box (基于 Debian/Ubuntu)"""
    if find_singbox_bin():
        print("[!] Sing-box 已安装，跳过下载")
        return find_singbox_bin()

    print("[*] 正在安装 Sing-box...")
    # 使用 POSIX 兼容写法，避免 /bin/sh 不支持 <(...) 导致语法错误
    install_cmds = [
        "curl -fsSL https://sing-box.app/install.sh | bash",
        "curl -fsSL https://raw.githubusercontent.com/SagerNet/sing-box/main/install.sh | bash",
    ]
    install_ok = False
    for cmd in install_cmds:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            install_ok = True
            break
    if not install_ok:
        raise RuntimeError("安装 sing-box 失败，请检查网络连通性或手动执行安装脚本。")

    singbox_bin = find_singbox_bin()
    if not singbox_bin:
        raise RuntimeError("安装 sing-box 后仍未找到可执行文件，请手动检查安装日志。")
    return singbox_bin


def ensure_service_file(singbox_bin):
    """当服务文件缺失时自动创建，兼容不同安装方式。"""
    if os.path.exists(SERVICE_PATH):
        return

    service_content = f"""[Unit]
Description=sing-box Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={singbox_bin} run -c {CONFIG_PATH}
Restart=always
RestartSec=2
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
"""
    with open(SERVICE_PATH, "w", encoding="utf-8") as f:
        f.write(service_content)
    print("[+] 已创建 systemd 服务文件")


USER_NAME_JP_DIRECT = "jp-direct"
USER_NAME_US_VPS = "us-vps-relay"
USER_NAME_US_HOME = "us-home-relay"


def make_vless_route_rule(auth_name, outbound_tag):
    """按 VLESS 用户名分流。

    sing-box 的 route.auth_user 匹配的是入站 users.name，
    不是 users.uuid，也不是 Linux 系统用户。
    """
    return {
        "inbound": ["vless-in"],
        "auth_user": [auth_name],
        "action": "route",
        "outbound": outbound_tag,
    }


def generate_config(u1, u2, u3, priv_key):
    """生成 Sing-box 核心 JSON 配置"""
    # 为每条线路分配固定用户名，路由阶段通过 auth_user 命中对应出口。
    users = [{"name": USER_NAME_JP_DIRECT, "uuid": u1, "flow": "xtls-rprx-vision"}]
    outbounds = [{"type": "direct", "tag": "out-direct"}]
    route_rules = [make_vless_route_rule(USER_NAME_JP_DIRECT, "out-direct")]

    if is_us_vps_enabled():
        users.append({"name": USER_NAME_US_VPS, "uuid": u2, "flow": "xtls-rprx-vision"})
        outbounds.append(build_us_vps_outbound())
        route_rules.append(make_vless_route_rule(USER_NAME_US_VPS, "out-us-vps"))

    if is_us_home_enabled():
        users.append({"name": USER_NAME_US_HOME, "uuid": u3, "flow": "xtls-rprx-vision"})
        outbounds.append(
            {
                "type": get_singbox_proxy_type(),
                "tag": "out-us-home",
                "server": US_HOME_PROXY_IP,
                "server_port": US_HOME_PROXY_PORT,
                "username": US_HOME_PROXY_USER,
                "password": US_HOME_PROXY_PASS,
            }
        )
        route_rules.append(make_vless_route_rule(USER_NAME_US_HOME, "out-us-home"))

    config = {
        "log": {"level": "info"},
        "inbounds": [
            {
                "type": "vless",
                "tag": "vless-in",
                "listen": "::",
                "listen_port": LISTEN_PORT,
                "users": users,
                "tls": {
                    "enabled": True,
                    "server_name": SNI_DOMAIN,
                    "reality": {
                        "enabled": True,
                        "handshake": {"server": DEST_SERVER, "server_port": 443},
                        "private_key": priv_key,
                        "short_id": [SHORT_ID],
                    },
                },
            }
        ],
        "outbounds": outbounds,
        "route": {"rules": route_rules},
    }
    return config


def main():
    global UUID_JP_DIRECT, UUID_US_RELAY, UUID_US_RESIDENTIAL, PRIVATE_KEY, PUBLIC_KEY

    try:
        # 权限检查
        if os.getuid() != 0:
            print("[ERROR] 请使用 root 权限运行此脚本")
            return

        ensure_valid_proxy_type()

        # 1. 初始化参数
        UUID_JP_DIRECT = UUID_JP_DIRECT or str(uuid.uuid4())
        UUID_US_RELAY = UUID_US_RELAY or str(uuid.uuid4())
        UUID_US_RESIDENTIAL = UUID_US_RESIDENTIAL or str(uuid.uuid4())

        singbox_bin = find_singbox_bin() or install_singbox()

        if not PRIVATE_KEY or not PUBLIC_KEY:
            print("[*] 正在生成 Reality 密钥对...")
            key_out = run_cmd(f"{singbox_bin} generate reality-keypair")
            # 格式示例: Private key: xxx \n Public key: yyy
            lines = key_out.splitlines()
            if len(lines) < 2:
                raise RuntimeError("Reality 密钥输出格式异常，请检查 sing-box 版本。")
            PRIVATE_KEY = lines[0].split(": ", 1)[1]
            PUBLIC_KEY = lines[1].split(": ", 1)[1]

        # 2. 系统优化
        setup_bbr()

        # 3. 配置文件写入
        os.makedirs("/etc/sing-box", exist_ok=True)
        backup_config(CONFIG_PATH)
        config_data = generate_config(UUID_JP_DIRECT, UUID_US_RELAY, UUID_US_RESIDENTIAL, PRIVATE_KEY)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

        # 写入后先校验配置，确保可启动
        run_cmd(f"{singbox_bin} check -c {CONFIG_PATH}")
        print("[+] sing-box 配置校验通过")

        # 4. 重启服务
        ensure_service_file(singbox_bin)
        run_cmd("systemctl daemon-reexec")
        run_cmd("systemctl enable sing-box")
        run_cmd("systemctl restart sing-box")

        # 5. 输出 URL（三条线路除 UUID 外参数保持一致）
        server_ip = get_public_host_for_url()
        base_params = (
            f"encryption=none&flow=xtls-rprx-vision&security=reality"
            f"&sni={SNI_DOMAIN}&fp=chrome&pbk={PUBLIC_KEY}&sid={SHORT_ID}"
        )

        urls = [("日本原生落地", "JP_Direct", UUID_JP_DIRECT)]
        if is_us_vps_enabled():
            urls.append(("美国VPS中转", "US_VPS_Relay", UUID_US_RELAY))
        if is_us_home_enabled():
            urls.append(("美国家宽中转", "US_Residential", UUID_US_RESIDENTIAL))

        print("\n" + "=" * 30 + " 配置完成 " + "=" * 30)
        for idx, (name, tag, route_uuid) in enumerate(urls, start=1):
            print(f"{idx}. {name}:\n vless://{route_uuid}@{server_ip}:{LISTEN_PORT}?{base_params}#{tag}")
            if idx != len(urls):
                print("-" * 20)
        print("=" * 70)
        print("[提示] 请确保服务器防火墙已放行端口:", LISTEN_PORT)
    except Exception as exc:
        print(f"[ERROR] 脚本执行失败: {exc}")
        raise


if __name__ == "__main__":
    main()
