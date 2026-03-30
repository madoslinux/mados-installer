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
rm -f /etc/mkinitcpio.d/linux-mados-zen.preset

KERNEL="linux-mados-zen"

if [ ! -s /boot/vmlinuz-${KERNEL} ] || [ ! -r /boot/vmlinuz-${KERNEL} ]; then
    echo "  Kernel missing before mkinitcpio! Recovering..."
    for kdir in /usr/lib/modules/*/; do
        kver=$(basename "$kdir")
        if [[ "$kver" == *"mados-zen"* ]] && [ -r "${kdir}vmlinuz" ]; then
            cp "${kdir}vmlinuz" /boot/vmlinuz-${KERNEL}
            echo "  Recovered kernel from ${kdir}vmlinuz (mados-zen kernel)"
            break
        fi
    done
fi

if [ ! -s /boot/vmlinuz-${KERNEL} ] || [ ! -r /boot/vmlinuz-${KERNEL} ]; then
    echo "  ERROR: Could not find kernel image. Reinstalling linux-mados-zen package..."
    pacman -Sy --noconfirm ${KERNEL} || { echo "FATAL: Failed to install kernel"; exit 1; }
fi

echo "  Detecting installed kernel versions in target system..."
ls /lib/modules/ 2>/dev/null || echo "  No kernel modules found"

TARGET_KVER=""
for kver in /lib/modules/*/; do
    kver_name=$(basename "$kver")
    if [[ "$kver_name" == *"mados-zen"* ]]; then
        TARGET_KVER="$kver_name"
        echo "  Found target kernel: $TARGET_KVER"
        break
    fi
done

if [ -z "$TARGET_KVER" ]; then
    echo "  ERROR: No mados-zen kernel modules found in /lib/modules"
    echo "  Available kernels:"
    ls /lib/modules/ 2>/dev/null || echo "  (none)"
    exit 1
fi

echo "  Creating mkinitcpio preset file..."
cat > /etc/mkinitcpio.d/${KERNEL}.preset <<EOFPRESET
ALL_config="/etc/mkinitcpio.conf"
ALL_kver="/boot/vmlinuz-${KERNEL}"
PRESETS=('default')
default_image="/boot/initramfs-${KERNEL}.img"
fallback_image="/boot/initramfs-${KERNEL}-fallback.img"
EOFPRESET

echo "  Backing up and replacing mkinitcpio.conf..."
cp /etc/mkinitcpio.conf /etc/mkinitcpio.conf.bak 2>/dev/null || true

CORE_STORAGE="nvme ahci xhci_pci usb_storage virtio_scsi sd_mod sr_mod"
CORE_FS="btrfs ext4 xfs vfat fat"

cat > /etc/mkinitcpio.conf <<EOFMKINIT
MODULES="${CORE_STORAGE} ${CORE_FS}"
BINARIES=""
HOOKS="base systemd udev microcode modconf kms plymouth block filesystems keyboard fsck"
EOFMKINIT

echo "  New /etc/mkinitcpio.conf content:"
cat /etc/mkinitcpio.conf | sed 's/^/    /'

sync
echo "  Running mkinitcpio for ${KERNEL}..."
if ! mkinitcpio -p ${KERNEL} 2>&1; then
    echo "  ERROR: mkinitcpio -p ${KERNEL} failed"
    echo "  Trying mkinitcpio with explicit kernel version..."
    mkinitcpio -k "/boot/vmlinuz-${KERNEL}" -g /boot/initramfs-${KERNEL}.img 2>&1 || { echo "FATAL: mkinitcpio failed"; exit 1; }
fi

if [ -f /boot/initramfs-${KERNEL}.img ]; then
    INITRAMFS_SIZE=$(du -h /boot/initramfs-${KERNEL}.img | cut -f1)
    echo "  Initramfs created: /boot/initramfs-${KERNEL}.img (${INITRAMFS_SIZE})"
else
    echo "  ERROR: initramfs not created!"
    exit 1
fi

if [ -f /boot/initramfs-${KERNEL}-fallback.img ]; then
    FALLBACK_SIZE=$(du -h /boot/initramfs-${KERNEL}-fallback.img | cut -f1)
    echo "  Fallback initramfs: /boot/initramfs-${KERNEL}-fallback.img (${FALLBACK_SIZE})"
fi

echo "  Initramfs rebuilt successfully"
