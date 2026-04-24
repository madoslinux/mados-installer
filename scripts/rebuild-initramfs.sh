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

KERNEL=""
for candidate in linux-lts linux-mados linux linux-zen; do
    if [ -s "/boot/vmlinuz-${candidate}" ] && [ -r "/boot/vmlinuz-${candidate}" ]; then
        KERNEL="${candidate}"
        break
    fi
done

if [ -z "$KERNEL" ]; then
    KERNEL="linux-lts"
    echo "  WARNING: Could not find kernel image in /boot. Installing ${KERNEL} package..."
    $PACMAN -Sy --noconfirm ${KERNEL} || { echo "FATAL: Failed to install kernel"; exit 1; }
fi

if [ ! -s "/boot/vmlinuz-${KERNEL}" ] || [ ! -r "/boot/vmlinuz-${KERNEL}" ]; then
    echo "  ERROR: Could not find readable kernel image: /boot/vmlinuz-${KERNEL}"
    exit 1
fi

echo "  Detecting installed kernel versions in target system..."
$LS /lib/modules/ 2>/dev/null || echo "  No kernel modules found"

TARGET_KVER=""
for kver in /lib/modules/*/; do
    kver_name=$($BASENAME "$kver")
    case "$KERNEL" in
        linux-lts)
            [[ "$kver_name" == *"lts"* ]] || continue
            ;;
        linux-mados)
            [[ "$kver_name" == *"mados"* ]] || continue
            ;;
        linux-zen)
            [[ "$kver_name" == *"zen"* ]] || continue
            ;;
        linux)
            [[ "$kver_name" == *"arch"* || "$kver_name" == *"linux"* ]] || continue
            ;;
    esac
    TARGET_KVER="$kver_name"
    echo "  Found target kernel: $TARGET_KVER"
    break
done

if [ -z "$TARGET_KVER" ]; then
    echo "  WARNING: No matching kernel modules found for ${KERNEL}; using first available module tree"
    for kver in /lib/modules/*/; do
        TARGET_KVER=$($BASENAME "$kver")
        break
    done
fi

if [ -z "$TARGET_KVER" ]; then
    echo "  ERROR: No kernel modules found in /lib/modules"
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
