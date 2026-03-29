#!/bin/bash
# madOS - Enable System Services
# This script enables essential system services during installation
set -euo pipefail

enable_service() {
    local svc="$1"
    if systemctl enable "$svc" 2>/dev/null; then
        echo "  Enabled: $svc"
    else
        echo "  WARN: Could not enable $svc (may be optional)"
    fi
}

echo "[7/8] Enabling essential services..."

passwd -l root 2>/dev/null || true

enable_service NetworkManager
enable_service systemd-resolved
enable_service earlyoom
enable_service systemd-timesyncd
enable_service lightdm
enable_service iwd
enable_service bluetooth
enable_service mados-gpu-wait.service
enable_service fail2ban

systemctl --global enable pipewire.socket pipewire-pulse.socket wireplumber.service 2>/dev/null || true

echo "  Essential services enabled"
