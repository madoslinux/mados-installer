#!/bin/bash
# madOS - Create User Account
set -euo pipefail

USERNAME="${1:-}"
HOSTNAME="${2:-}"
PASSWORD="${3:-}"

if [ -z "$USERNAME" ] || [ -z "$HOSTNAME" ]; then
    echo "ERROR: USERNAME and HOSTNAME arguments required"
    exit 1
fi

USERADD="/usr/sbin/useradd"
CHPASSWD="/usr/bin/chpasswd"
CAT="/usr/bin/cat"
ECHO="/usr/bin/echo"
CHMOD="/usr/bin/chmod"

echo "[2/8] Creating user account..."

$ECHO "$HOSTNAME" > /etc/hostname
$CAT > /etc/hosts <<EOF
127.0.0.1   localhost
::1         localhost
127.0.1.1   ${HOSTNAME}.localdomain ${HOSTNAME}
EOF

$USERADD -m -G wheel,audio,video,storage -s /usr/bin/zsh "$USERNAME"
if [ -n "$PASSWORD" ]; then
    $ECHO "$USERNAME:$PASSWORD" | $CHPASSWD
fi

$ECHO "%wheel ALL=(ALL:ALL) ALL" > /etc/sudoers.d/wheel
$CHMOD 440 /etc/sudoers.d/wheel

$ECHO "$USERNAME ALL=(ALL:ALL) NOPASSWD: /usr/local/bin/opencode,/usr/local/bin/ollama,/usr/bin/pacman,/usr/bin/systemctl,/usr/bin/usbguard" > /etc/sudoers.d/opencode-nopasswd
$CHMOD 440 /etc/sudoers.d/opencode-nopasswd

echo "  User account created: $USERNAME"
