#!/bin/bash
# madOS - Configure GRUB
set -euo pipefail

echo "[4/8] Configuring GRUB..."

ROOT_PART="${1:-}"

if [ -z "$ROOT_PART" ]; then
    echo "ERROR: ROOT_PART argument required"
    exit 1
fi

GRUB_MKCONFIG="/usr/bin/grub-mkconfig"
BLKID="/usr/bin/blkid"

require_cmd() {
    local cmd="$1"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "ERROR: Required command '$cmd' not found"
        exit 1
    fi
}

set_grub_key() {
    local key="$1"
    local value="$2"
    local file="/etc/default/grub"

    if grep -Eq "^#?${key}=" "$file"; then
        sed -i "s|^#\?${key}=.*|${key}=${value}|" "$file"
    else
        echo "${key}=${value}" >> "$file"
    fi
}

ensure_cmdline_token() {
    local token="$1"
    local file="/etc/default/grub"
    local current
    local raw

    raw=$(grep -E '^GRUB_CMDLINE_LINUX=' "$file" | tail -n1 || true)
    if [ -n "$raw" ]; then
        current=${raw#GRUB_CMDLINE_LINUX=}
        current=${current#\"}
        current=${current%\"}
    else
        current=""
    fi

    if [[ " $current " != *" $token "* ]]; then
        current="${current:+$current }$token"
    fi

    set_grub_key "GRUB_CMDLINE_LINUX" "\"$current\""
}

require_cmd "$GRUB_MKCONFIG"
require_cmd "$BLKID"

if [ ! -b "$ROOT_PART" ]; then
    echo "ERROR: ROOT_PART is not a valid block device: $ROOT_PART"
    exit 1
fi

ROOT_UUID=$($BLKID -s UUID -o value "$ROOT_PART" 2>/dev/null || true)
if [ -z "$ROOT_UUID" ]; then
    echo "ERROR: Could not detect UUID for root partition: $ROOT_PART"
    exit 1
fi

KERNEL="linux-mados"

if [ ! -f /boot/vmlinuz-${KERNEL} ]; then
    echo "ERROR: No madOS kernel found in /boot"
    exit 1
fi

mkdir -p /etc/default
[ -f /etc/default/grub ] || touch /etc/default/grub

mkdir -p /etc/mados
echo "$KERNEL" > /etc/mados/default-kernel
echo "  Selected default kernel: $KERNEL"

set_grub_key "GRUB_DISTRIBUTOR" '"madOS"'
set_grub_key "GRUB_DISABLE_OS_PROBER" "false"
set_grub_key "GRUB_DEFAULT" "0"
set_grub_key "GRUB_DISABLE_LINUX_UUID" "false"
set_grub_key "GRUB_TERMINAL" '"console"'

ensure_cmdline_token "zswap.enabled=0"
ensure_cmdline_token "splash"
ensure_cmdline_token "quiet"
ensure_cmdline_token "plymouth.use-simpledrm=0"
ensure_cmdline_token "rootflags=subvol=@"

# Remove legacy custom entry if present.
# GRUB's auto-generated linux entry is correct for this layout and avoids duplicate/broken menu entries.
rm -f /etc/grub.d/09_mados

$GRUB_MKCONFIG -o /boot/grub/grub.cfg

if [ ! -f /boot/grub/grub.cfg ]; then
    echo "ERROR: grub.cfg was not generated!"
    exit 1
fi

if ! grep -q "vmlinuz-linux-mados" /boot/grub/grub.cfg; then
    echo "ERROR: grub.cfg does not contain linux-mados entry"
    exit 1
fi

echo "  GRUB configured"
