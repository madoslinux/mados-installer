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

KERNEL_NAME=""
for candidate in linux-lts linux-mados linux linux-zen; do
    if [ -f "/boot/vmlinuz-${candidate}" ] && [ -f "/boot/initramfs-${candidate}.img" ]; then
        KERNEL_NAME="${candidate}"
        break
    fi
done

if [ -z "$KERNEL_NAME" ]; then
    echo "ERROR: No supported kernel/initramfs pair found in /boot"
    exit 1
fi

cat > /boot/limine.conf <<EOF
timeout: 5
default_entry: 1

/madOS (Installed)
    protocol: linux
    path: boot():/vmlinuz-${KERNEL_NAME}
    module_path: boot():/initramfs-${KERNEL_NAME}.img
    cmdline: root=UUID=${ROOT_UUID} rw zswap.enabled=0 splash quiet

/madOS (Installed, Safe Graphics)
    protocol: linux
    path: boot():/vmlinuz-${KERNEL_NAME}
    module_path: boot():/initramfs-${KERNEL_NAME}.img
    cmdline: root=UUID=${ROOT_UUID} rw nomodeset zswap.enabled=0 splash quiet

/UEFI Firmware Settings
    protocol: efi_boot_entry
    entry: UEFI Firmware Settings
EOF

# UEFI fallback search path used by Limine.
cp /boot/limine.conf /boot/EFI/BOOT/limine.conf

if [ ! -f /boot/limine.conf ]; then
    echo "ERROR: limine.conf was not generated"
    exit 1
fi

echo "  Root partition UUID: $ROOT_UUID"
echo "  Limine configured"
