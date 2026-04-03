#!/bin/bash
# madOS - Setup Limine bootloader (BIOS + UEFI)
set -euo pipefail

DISK="${1:-}"

if [ -z "$DISK" ]; then
    echo "ERROR: DISK argument required"
    exit 1
fi

echo "[3/8] Installing Limine bootloader..."

if ! command -v limine >/dev/null 2>&1; then
    echo "ERROR: limine binary not found. Ensure the 'limine' package is installed."
    exit 1
fi

if [ ! -f /usr/share/limine/BOOTX64.EFI ]; then
    echo "ERROR: /usr/share/limine/BOOTX64.EFI not found"
    exit 1
fi

if [ ! -f /usr/share/limine/limine-bios.sys ]; then
    echo "ERROR: /usr/share/limine/limine-bios.sys not found"
    exit 1
fi

mkdir -p /boot/EFI/BOOT

# Required by Limine BIOS stage 2 discovery.
cp /usr/share/limine/limine-bios.sys /boot/limine-bios.sys

if [ -d /sys/firmware/efi ]; then
    echo "==> Detected UEFI boot mode"
    cp /usr/share/limine/BOOTX64.EFI /boot/EFI/BOOT/BOOTX64.EFI
    cp /usr/share/limine/BOOTIA32.EFI /boot/EFI/BOOT/BOOTIA32.EFI 2>/dev/null || true

    if [ ! -f /boot/EFI/BOOT/BOOTX64.EFI ]; then
        echo "ERROR: /boot/EFI/BOOT/BOOTX64.EFI was not created"
        exit 1
    fi

    # Prefer disk boot first by creating/updating an EFI boot entry.
    if command -v efibootmgr >/dev/null 2>&1; then
        if ! efibootmgr --create --disk "$DISK" --part 2 --label "madOS Limine" --loader '\\EFI\\BOOT\\BOOTX64.EFI' >/dev/null 2>&1; then
            echo "WARN: Could not create EFI boot entry (NVRAM may be read-only)"
        fi

        BOOT_CURRENT=$(efibootmgr | awk '/BootOrder:/ {print $2}')
        BOOT_NUM=$(efibootmgr | awk '/madOS Limine/ {gsub("Boot", "", $1); gsub("\*", "", $1); print $1; exit}')
        if [ -n "$BOOT_NUM" ]; then
            if [ -n "$BOOT_CURRENT" ]; then
                REST=$(echo "$BOOT_CURRENT" | tr ',' '\n' | grep -v "^$BOOT_NUM$" | paste -sd, -)
                if [ -n "$REST" ]; then
                    NEW_ORDER="$BOOT_NUM,$REST"
                else
                    NEW_ORDER="$BOOT_NUM"
                fi
                efibootmgr -o "$NEW_ORDER" >/dev/null 2>&1 || echo "WARN: Could not set BootOrder"
            else
                efibootmgr -o "$BOOT_NUM" >/dev/null 2>&1 || echo "WARN: Could not set BootOrder"
            fi
        fi
    else
        echo "WARN: efibootmgr not available; skipping UEFI BootOrder update"
    fi
fi

echo "==> Installing Limine BIOS stages to $DISK"
if ! limine bios-install "$DISK" 2>&1; then
    echo "ERROR: Limine BIOS install failed"
    exit 1
fi

if command -v sbctl >/dev/null 2>&1; then
    SECURE_BOOT=0
    if [ -f /sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c ]; then
        SB_VAL=$(od -An -t u1 -j4 -N1 /sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c 2>/dev/null | tr -d ' ')
        [ "$SB_VAL" = "1" ] && SECURE_BOOT=1
    fi

    if [ "$SECURE_BOOT" = "1" ]; then
        echo "==> Secure Boot is ENABLED - setting up sbctl signing"
        sbctl create-keys 2>/dev/null || echo "WARN: sbctl keys may already exist"

        for f in /boot/EFI/BOOT/BOOTX64.EFI /boot/vmlinuz-linux-mados-zen; do
            if [ -f "$f" ]; then
                echo "    Signing $f"
                sbctl sign -s "$f" 2>&1 || echo "WARN: Could not sign $f"
            fi
        done

        mkdir -p /etc/pacman.d/hooks
        cat > /etc/pacman.d/hooks/99-sbctl-sign.hook <<'EOFHOOK'
[Trigger]
Operation = Install
Operation = Upgrade
Type = Package
Target = linux
Target = linux-lts
Target = linux-zen
Target = linux-mados-zen
Target = limine

[Action]
Description = Signing EFI binaries for Secure Boot...
When = PostTransaction
Exec = /usr/bin/sbctl sign-all
Depends = sbctl
EOFHOOK
    fi
fi

echo "  Limine bootloader installed"
