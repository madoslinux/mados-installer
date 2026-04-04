#!/bin/bash
# madOS Initramfs Rebuild Script
set -euo pipefail

echo "[6/8] Rebuilding initramfs..."

PACMAN="/usr/bin/pacman"
MKINITCPIO="/usr/bin/mkinitcpio"
LSMOD="/usr/bin/lsmod"
AWK="/usr/bin/awk"
XARGS="/usr/bin/xargs"
BASENAME="/usr/bin/basename"
SYNC="/usr/bin/sync"
LS="/usr/bin/ls"
RM="/usr/bin/rm"
CP="/usr/bin/cp"
CAT="/usr/bin/cat"
DU="/usr/bin/du"
CUT="/usr/bin/cut"
TR="/usr/bin/tr"

echo "  Removing archiso-specific mkinitcpio configs..."
$PACMAN -Rdd --noconfirm mkinitcpio-archiso 2>/dev/null || true
$RM -f /etc/mkinitcpio.conf.d/archiso.conf
$RM -f /etc/mkinitcpio.d/linux.preset
$RM -f /etc/mkinitcpio.d/linux-zen.preset
$RM -f /etc/mkinitcpio.d/linux-lts.preset
$RM -f /etc/mkinitcpio.d/linux-mados.preset

KERNEL="linux-mados"
if [ ! -s /boot/vmlinuz-${KERNEL} ] || [ ! -r /boot/vmlinuz-${KERNEL} ]; then
    echo "  ERROR: Could not find kernel image. Reinstalling ${KERNEL} package..."
    $PACMAN -Sy --noconfirm ${KERNEL} || { echo "FATAL: Failed to install kernel"; exit 1; }
fi

echo "  Detecting installed kernel versions in target system..."
$LS /lib/modules/ 2>/dev/null || echo "  No kernel modules found"

TARGET_KVER=""
for kver in /lib/modules/*/; do
    kver_name=$($BASENAME "$kver")
    if [[ "$kver_name" == *"mados"* ]]; then
        TARGET_KVER="$kver_name"
        echo "  Found target kernel: $TARGET_KVER"
        break
    fi
done

if [ -z "$TARGET_KVER" ]; then
    echo "  ERROR: No madOS kernel modules found in /lib/modules"
    echo "  Available kernels:"
    $LS /lib/modules/ 2>/dev/null || echo "  (none)"
    exit 1
fi

echo "  Creating mkinitcpio preset file..."
$CAT > /etc/mkinitcpio.d/${KERNEL}.preset <<EOFPRESET
ALL_config="/etc/mkinitcpio.conf"
ALL_kver="/boot/vmlinuz-${KERNEL}"
PRESETS=('default')
default_image="/boot/initramfs-${KERNEL}.img"
fallback_image="/boot/initramfs-${KERNEL}-fallback.img"
EOFPRESET

echo "  Backing up and replacing mkinitcpio.conf..."
$CP /etc/mkinitcpio.conf /etc/mkinitcpio.conf.bak 2>/dev/null || true

echo "  Using mkinitcpio autodetect mode (MODULES=\"\")"
DETECTED_MODULES=$($LSMOD 2>/dev/null | $AWK 'NR>1 {print $1}' | $TR '\n' ' ' | $XARGS || true)
if [ -n "$DETECTED_MODULES" ]; then
    echo "  Live modules detected (informational): $DETECTED_MODULES"
fi

$CAT > /etc/mkinitcpio.conf <<EOFMKINIT
MODULES=""
BINARIES=""
HOOKS="base systemd udev microcode modconf kms plymouth block filesystems keyboard fsck"
EOFMKINIT

SED="/usr/bin/sed"
echo "  New /etc/mkinitcpio.conf content:"
$CAT /etc/mkinitcpio.conf | $SED 's/^/    /'

$SYNC
echo "  Running mkinitcpio for ${KERNEL}..."
mkinit_ok=0
if $MKINITCPIO -p ${KERNEL} 2>&1; then
    mkinit_ok=1
else
    echo "  WARNING: mkinitcpio -p ${KERNEL} returned non-zero"
fi

if [ ! -s /boot/initramfs-${KERNEL}.img ]; then
    echo "  Trying mkinitcpio with explicit kernel version..."
    if $MKINITCPIO -k "/boot/vmlinuz-${KERNEL}" -c /etc/mkinitcpio.conf -g /boot/initramfs-${KERNEL}.img 2>&1; then
        mkinit_ok=1
    else
        echo "  WARNING: explicit mkinitcpio command returned non-zero"
    fi
fi

if [ -s /boot/initramfs-${KERNEL}.img ]; then
    INITRAMFS_SIZE=$($DU -h /boot/initramfs-${KERNEL}.img | $CUT -f1)
    echo "  Initramfs created: /boot/initramfs-${KERNEL}.img (${INITRAMFS_SIZE})"
    if [ "$mkinit_ok" -eq 0 ]; then
        echo "  WARNING: mkinitcpio returned non-zero, but initramfs image was created"
    fi
else
    echo "  ERROR: initramfs not created!"
    exit 1
fi

if [ -f /boot/initramfs-${KERNEL}-fallback.img ]; then
    FALLBACK_SIZE=$($DU -h /boot/initramfs-${KERNEL}-fallback.img | $CUT -f1)
    echo "  Fallback initramfs: /boot/initramfs-${KERNEL}-fallback.img (${FALLBACK_SIZE})"
fi

echo "  Initramfs rebuilt successfully"
