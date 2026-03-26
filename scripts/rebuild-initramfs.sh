#!/bin/bash
# madOS Initramfs Rebuild Script
set -euo pipefail

echo "[6/8] Rebuilding initramfs..."

echo "  Removing archiso-specific mkinitcpio configs..."
pacman -Rdd --noconfirm mkinitcpio-archiso 2>/dev/null || true
rm -f /etc/mkinitcpio.conf.d/archiso.conf
rm -f /etc/mkinitcpio.d/linux.preset

if [ ! -s /boot/vmlinuz-linux ] || [ ! -r /boot/vmlinuz-linux ]; then
    echo "  Kernel missing before mkinitcpio! Recovering..."
    for kdir in /usr/lib/modules/*/; do
        if [ -r "${kdir}vmlinuz" ]; then
            cp "${kdir}vmlinuz" /boot/vmlinuz-linux
            echo "  Recovered kernel from ${kdir}vmlinuz"
            break
        fi
    done
fi

if [ ! -s /boot/vmlinuz-linux ] || [ ! -r /boot/vmlinuz-linux ]; then
    echo "  ERROR: Could not find kernel image. Reinstalling linux package..."
    pacman -Sy --noconfirm linux || { echo "FATAL: Failed to install kernel"; exit 1; }
fi

echo "  Creating mkinitcpio preset file..."
cat > /etc/mkinitcpio.d/linux.preset <<'EOFPRESET'
ALL_config="/etc/mkinitcpio.conf"
ALL_kver="/boot/vmlinuz-linux"
PRESETS=('default')
default_image="/boot/initramfs-linux.img"
fallback_image="/boot/initramfs-linux-fallback.img"
EOFPRESET

echo "  Detecting loaded kernel modules for initramfs..."
MODULES=$(lsmod | awk 'NR>1 {print $1}' | tr '\n' ' ')
MODULE_COUNT=$(lsmod | awk 'NR>1 {print $1}' | wc -w)
if [ -n "$MODULES" ]; then
    echo "  Found ${MODULE_COUNT} modules to include in initramfs"
    echo "  MODULES=\"$MODULES\"" >> /etc/mkinitcpio.conf
    echo "  Added modules to /etc/mkinitcpio.conf"
else
    echo "  WARNING: No modules detected from lsmod"
fi

echo "  Current /etc/mkinitcpio.conf content:"
grep -v '^#' /etc/mkinitcpio.conf | grep -v '^$' | sed 's/^/    /'

sync
echo "  Running mkinitcpio -P..."
if ! mkinitcpio -P 2>&1; then
    echo "  ERROR: mkinitcpio -P failed"
    exit 1
fi

if [ ! -f /boot/initramfs-linux.img ]; then
    echo "  WARNING: initramfs not created, trying fallback preset..."
    mkinitcpio -p linux 2>&1 || { echo "FATAL: mkinitcpio -p linux failed"; exit 1; }
fi

if [ -f /boot/initramfs-linux.img ]; then
    INITRAMFS_SIZE=$(du -h /boot/initramfs-linux.img | cut -f1)
    echo "  Initramfs created: /boot/initramfs-linux.img (${INITRAMFS_SIZE})"
else
    echo "  ERROR: initramfs still not created!"
    exit 1
fi

if [ -f /boot/initramfs-linux-fallback.img ]; then
    FALLBACK_SIZE=$(du -h /boot/initramfs-linux-fallback.img | cut -f1)
    echo "  Fallback initramfs: /boot/initramfs-linux-fallback.img (${FALLBACK_SIZE})"
fi

echo "  Initramfs rebuilt successfully"
