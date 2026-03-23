#!/bin/bash
# madOS - Configure GRUB
set -euo pipefail

echo "[4/8] Configuring GRUB..."

ROOT_PART="${1:-}"

if [ -z "$ROOT_PART" ]; then
    echo "ERROR: ROOT_PART argument required"
    exit 1
fi

sed -i 's/GRUB_CMDLINE_LINUX=""/GRUB_CMDLINE_LINUX="zswap.enabled=0 splash quiet plymouth.use-simpledrm=0"/' /etc/default/grub
sed -i 's/GRUB_DISTRIBUTOR="Arch"/GRUB_DISTRIBUTOR="madOS"/' /etc/default/grub
sed -i 's/#GRUB_DISABLE_OS_PROBER=false/GRUB_DISABLE_OS_PROBER=false/' /etc/default/grub
echo 'GRUB_DISABLE_LINUX_UUID=false' >> /etc/default/grub
echo 'GRUB_TERMINAL="console"' >> /etc/default/grub

ROOT_UUID=$(blkid -s UUID -o value "$ROOT_PART" 2>/dev/null || echo "")
if [ -n "$ROOT_UUID" ]; then
    echo "  Root partition UUID: $ROOT_UUID"
    mkdir -p /boot/grub/custom
    cat > /boot/grub/custom/mados.cfg <<'EOFGRUB'
menuentry 'madOS Linux' {
    load_video
    set gfxpayload=keep
    insmod gzio
    insmod part_gpt
    insmod ext2
    search --no-floppy --fs-uuid --set=root $ROOT_UUID
    echo        'Loading Linux linux ...'
    linux       /vmlinuz-linux root=UUID=$ROOT_UUID rw zswap.enabled=0 splash quiet
    echo        'Loading initial ramdisk ...'
    initrd      /initramfs-linux.img
}
EOFGRUB
fi

grub-mkconfig -o /boot/grub/grub.cfg

if [ ! -f /boot/grub/grub.cfg ]; then
    echo "ERROR: grub.cfg was not generated!"
    exit 1
fi

echo "  GRUB configured"
