#!/bin/bash
# madOS - Clean Live ISO Artifacts
# Removes live-specific services, users, and files during installation
set -euo pipefail

USERNAME="${1:-}"

echo "Cleaning live ISO artifacts..."

rm -rf /etc/systemd/system/getty@tty1.service.d

for svc in \
    livecd-talk.service \
    livecd-alsa-unmuter.service \
    pacman-init.service \
    etc-pacman.d-gnupg.mount \
    choose-mirror.service \
    mados-persistence-detect.service \
    mados-persist-sync.service \
    mados-ventoy-setup.service \
    mados-timezone.service \
    mados-installer-autostart.service \
    plymouth-start.service \
    plymouth-quit.service \
    plymouth-quit-wait.service; do
    systemctl disable "$svc" 2>/dev/null || true
    rm -f "/etc/systemd/system/$svc"
done



if id mados &>/dev/null; then
    userdel -r mados 2>/dev/null || userdel mados 2>/dev/null || true
    rm -rf /home/mados
fi

rm -f /etc/sudoers.d/99-opencode-nopasswd
rm -f /etc/profile.d/mados-security-notify.sh
rm -f /etc/profile.d/mados-media-links.sh

mkdir -p /etc/sway/config.d
chmod 755 /etc/sway/config.d

echo "  Live artifacts cleaned"
