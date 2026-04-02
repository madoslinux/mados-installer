#!/bin/bash
# madOS - Configure Limine
set -euo pipefail

ROOT_PART="${1:-}"

if [ -z "$ROOT_PART" ]; then
    echo "ERROR: ROOT_PART argument required"
    exit 1
fi

echo "[4/8] Configuring Limine..."

ROOT_UUID=$(blkid -s UUID -o value "$ROOT_PART" 2>/dev/null || echo "")
if [ -z "$ROOT_UUID" ]; then
    echo "ERROR: Could not detect root UUID for $ROOT_PART"
    exit 1
fi

mkdir -p /boot/EFI/BOOT

cat > /boot/limine.conf <<EOF
TIMEOUT=5
DEFAULT_ENTRY=1

/1) madOS Linux
    PROTOCOL=linux
    KERNEL_PATH=boot():/vmlinuz-linux-mados-zen
    MODULE_PATH=boot():/initramfs-linux-mados-zen.img
    CMDLINE=root=UUID=${ROOT_UUID} rw zswap.enabled=0 splash quiet plymouth.use-simpledrm=0

/2) madOS Linux (Safe Graphics)
    PROTOCOL=linux
    KERNEL_PATH=boot():/vmlinuz-linux-mados-zen
    MODULE_PATH=boot():/initramfs-linux-mados-zen.img
    CMDLINE=root=UUID=${ROOT_UUID} rw nomodeset zswap.enabled=0 splash quiet
EOF

# UEFI fallback search path used by Limine.
cp /boot/limine.conf /boot/EFI/BOOT/limine.conf

if [ ! -f /boot/limine.conf ]; then
    echo "ERROR: limine.conf was not generated"
    exit 1
fi

echo "  Root partition UUID: $ROOT_UUID"
echo "  Limine configured"
