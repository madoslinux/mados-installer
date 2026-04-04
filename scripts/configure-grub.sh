#!/bin/bash
# madOS - Configure GRUB
set -euo pipefail

echo "[4/8] Configuring GRUB..."

ROOT_PART="${1:-}"

if [ -z "$ROOT_PART" ]; then
    echo "ERROR: ROOT_PART argument required"
    exit 1
fi

is_modern_cpu() {
    local flags
    flags=$(grep -m1 '^flags' /proc/cpuinfo 2>/dev/null || true)
    [[ "$flags" == *" avx2 "* ]] && [[ "$flags" == *" sse4_2 "* ]]
}

if is_modern_cpu; then
    KERNEL="linux-mados"
else
    KERNEL="linux-mados"
fi

if [ ! -f /boot/vmlinuz-${KERNEL} ]; then
    echo "ERROR: No madOS kernel found in /boot"
    exit 1
fi

mkdir -p /etc/mados
echo "$KERNEL" > /etc/mados/default-kernel
echo "  Selected default kernel: $KERNEL"

sed -i 's/GRUB_CMDLINE_LINUX=""/GRUB_CMDLINE_LINUX="zswap.enabled=0 splash quiet plymouth.use-simpledrm=0"/' /etc/default/grub
sed -i 's/GRUB_DISTRIBUTOR="Arch"/GRUB_DISTRIBUTOR="madOS"/' /etc/default/grub
sed -i 's/#GRUB_DISABLE_OS_PROBER=false/GRUB_DISABLE_OS_PROBER=false/' /etc/default/grub
sed -i 's/^#\?GRUB_DEFAULT=.*/GRUB_DEFAULT=0/' /etc/default/grub
    echo 'GRUB_DISABLE_LINUX_UUID=false' >> /etc/default/grub
echo 'GRUB_TERMINAL="console"' >> /etc/default/grub

# Remove legacy custom entry if present.
# GRUB's auto-generated linux entry is correct for this layout and avoids duplicate/broken menu entries.
rm -f /etc/grub.d/09_mados

grub-mkconfig -o /boot/grub/grub.cfg

if [ ! -f /boot/grub/grub.cfg ]; then
    echo "ERROR: grub.cfg was not generated!"
    exit 1
fi

echo "  GRUB configured"
