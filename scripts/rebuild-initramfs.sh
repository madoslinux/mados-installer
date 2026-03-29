#!/bin/bash
# madOS Initramfs Rebuild Script
set -euo pipefail

echo "[6/8] Rebuilding initramfs..."

echo "  Removing archiso-specific mkinitcpio configs..."
pacman -Rdd --noconfirm mkinitcpio-archiso 2>/dev/null || true
rm -f /etc/mkinitcpio.conf.d/archiso.conf
rm -f /etc/mkinitcpio.d/linux.preset
rm -f /etc/mkinitcpio.d/linux-zen.preset
rm -f /etc/mkinitcpio.d/linux-lts.preset

KERNEL="linux-zen"
if [ ! -s /boot/vmlinuz-${KERNEL} ] || [ ! -r /boot/vmlinuz-${KERNEL} ]; then
    echo "  Kernel missing before mkinitcpio! Recovering..."
    for kdir in /usr/lib/modules/*/; do
        if [ -r "${kdir}vmlinuz" ]; then
            cp "${kdir}vmlinuz" /boot/vmlinuz-${KERNEL}
            echo "  Recovered kernel from ${kdir}vmlinuz"
            break
        fi
    done
fi

if [ ! -s /boot/vmlinuz-${KERNEL} ] || [ ! -r /boot/vmlinuz-${KERNEL} ]; then
    echo "  ERROR: Could not find kernel image. Reinstalling linux-zen package..."
    pacman -Sy --noconfirm ${KERNEL} || { echo "FATAL: Failed to install kernel"; exit 1; }
fi

echo "  Creating mkinitcpio preset file..."
cat > /etc/mkinitcpio.d/${KERNEL}.preset <<'EOFPRESET'
ALL_config="/etc/mkinitcpio.conf"
ALL_kver="/boot/vmlinuz-${KERNEL}"
PRESETS=('default')
default_image="/boot/initramfs-${KERNEL}.img"
fallback_image="/boot/initramfs-${KERNEL}-fallback.img"
EOFPRESET

echo "  Detecting loaded kernel modules for initramfs..."
MODULES=$(lsmod | awk 'NR>1 {print $1}' | tr '\n' ' ')

CORE_STORAGE="nvme ahci xhci_pci usb_storage virtio_scsi sd_mod sr_mod"
CORE_FS="btrfs ext4 xfs vfat fat"

if [ -n "$MODULES" ]; then
    echo "  Modules from live system: ${MODULES}"
    echo "  Adding core modules: ${CORE_STORAGE} ${CORE_FS}"
    echo "MODULES=\"${MODULES} ${CORE_STORAGE} ${CORE_FS}\"" >> /etc/mkinitcpio.conf
else
    echo "  No modules from lsmod, adding core only: ${CORE_STORAGE} ${CORE_FS}"
    echo "MODULES=\"${CORE_STORAGE} ${CORE_FS}\"" >> /etc/mkinitcpio.conf
fi

echo "  Current /etc/mkinitcpio.conf content:"
grep -v '^#' /etc/mkinitcpio.conf | grep -v '^$' | sed 's/^/    /'

sync
echo "  Running mkinitcpio -P..."
if ! mkinitcpio -P 2>&1; then
    echo "  ERROR: mkinitcpio -P failed"
    exit 1
fi

if [ ! -f /boot/initramfs-${KERNEL}.img ]; then
    echo "  WARNING: initramfs not created, trying fallback preset..."
    mkinitcpio -p ${KERNEL} 2>&1 || { echo "FATAL: mkinitcpio -p ${KERNEL} failed"; exit 1; }
fi

if [ -f /boot/initramfs-${KERNEL}.img ]; then
    INITRAMFS_SIZE=$(du -h /boot/initramfs-${KERNEL}.img | cut -f1)
    echo "  Initramfs created: /boot/initramfs-${KERNEL}.img (${INITRAMFS_SIZE})"
else
    echo "  ERROR: initramfs still not created!"
    exit 1
fi

if [ -f /boot/initramfs-${KERNEL}-fallback.img ]; then
    FALLBACK_SIZE=$(du -h /boot/initramfs-${KERNEL}-fallback.img | cut -f1)
    echo "  Fallback initramfs: /boot/initramfs-${KERNEL}-fallback.img (${FALLBACK_SIZE})"
fi

echo "  Initramfs rebuilt successfully"
