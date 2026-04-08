import os
import json
import uuid
import subprocess
import secrets

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()

def setup():
    print("🚀 开始全自动配置 Xray-Reality...")

    # 1. 开启 BBR
    print("🛠️ 正在优化内核与开启 BBR...")
    with open("/etc/sysctl.conf", "a") as f:
        f.write("\nnet.core.default_qdisc=fq\nnet.ipv4.tcp_congestion_control=bbr\n")
        f.write("net.ipv4.tcp_fastopen=3\nnet.ipv4.tcp_slow_start_after_idle=0\n")
    os.system("sysctl -p")

    # 2. 安装 Xray
    print("📥 安装 Xray 核心...")
    os.system('bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install')

    # 3. 生成必要参数
    u_id = str(uuid.uuid4())
    port = 443
    sni = "www.loewe.com"
    # 生成 Reality 密钥对
    keys = run("xray x25519")
    private_key = keys.splitlines()[0].split(": ")[1]
    public_key = keys.splitlines()[1].split(": ")[1]
    # 生成 ShortID (8位随机十六进制)
    short_id = secrets.token_hex(4)

    # 4. 配置防火墙
    print("🛡️ 配置防火墙 (UFW)...")
    os.system("apt install -y ufw")
    os.system(f"ufw allow {port}/tcp")
    os.system("ufw allow ssh")
    os.system("echo 'y' | ufw enable")

    # 5. 写入 Xray 配置文件
    config = {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "port": port,
            "protocol": "vless",
            "settings": {
                "clients": [{"id": u_id, "flow": "xtls-rprx-vision"}],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "show": False,
                    "dest": f"{sni}:443",
                    "xver": 0,
                    "serverNames": [sni],
                    "privateKey": private_key,
                    "shortIds": [short_id]
                }
            }
        }],
        "outbounds": [{"protocol": "freedom"}]
    }

    with open("/usr/local/etc/xray/config.json", "w") as f:
        json.dump(config, f, indent=4)

    # 6. 重启服务
    os.system("systemctl restart xray")
    os.system("systemctl enable xray")

    # 7. 获取公网 IP
    ip = run("curl -s ipv4.icanhazip.com")

    # 8. 生成 V2rayN 链接
    remark = f"Reality_{ip}"
    vless_link = f"vless://{u_id}@{ip}:{port}?security=reality&sni={sni}&fp=chrome&pbk={public_key}&sid={short_id}&flow=xtls-rprx-vision&type=tcp#{remark}"

    print("\n" + "="*50)
    print("✅ 配置完成！")
    print(f"\nYour V2rayN URL:\n\n{vless_link}\n")
    print("="*50)

if __name__ == "__main__":
    setup()