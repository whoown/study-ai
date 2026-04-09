sudo apt update
sudo apt install -y qemu-guest-agent curl ca-certificates

# 1) swap
sudo fallocate -l 1G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=1024
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-swappiness.conf
sudo sysctl -p /etc/sysctl.d/99-swappiness.conf

# 2) disable non-essential daemons
sudo systemctl disable --now fwupd.service ModemManager.service multipathd.service udisks2.service upower.service 2>/dev/null || true

# 3) keep essentials
sudo systemctl enable --now ssh systemd-networkd systemd-resolved qemu-guest-agent

free -h
systemctl list-units --type=service --state=running
