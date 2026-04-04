#!/bin/bash
# madOS - Setup Timezone and Locale
set -euo pipefail

TIMEZONE="${1:-}"
LOCALE="${2:-}"

if [ -z "$TIMEZONE" ] || [ -z "$LOCALE" ]; then
    echo "ERROR: TIMEZONE and LOCALE arguments required"
    exit 1
fi

echo "[1/8] Setting timezone and locale..."

ln -sf "/usr/share/zoneinfo/$TIMEZONE" /etc/localtime
hwclock --systohc 2>/dev/null || true

if ! grep -q '^en_US.UTF-8 UTF-8$' /etc/locale.gen; then
    echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
fi
if ! grep -q "^$LOCALE UTF-8$" /etc/locale.gen; then
    echo "$LOCALE UTF-8" >> /etc/locale.gen
fi
locale-gen
echo "LANG=$LOCALE" > /etc/locale.conf

echo "  Timezone and locale configured"
