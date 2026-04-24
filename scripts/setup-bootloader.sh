#!/bin/bash
# madOS - Setup GRUB Bootloader
set -euo pipefail

DISK="${1:-}"

if [ -z "$DISK" ]; then
    echo "ERROR: DISK argument required"
    exit 1
fi

echo "[3/8] Installing GRUB bootloader..."

GRUB_INSTALL="/usr/bin/grub-install"
FINDMNT="/usr/bin/findmnt"

require_cmd() {
    local cmd="$1"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "ERROR: Required command '$cmd' not found"
        exit 1
    fi
}

append_grub_setting_once() {
    local setting="$1"
    local grub_defaults="/etc/default/grub"
    mkdir -p /etc/default
    [ -f "$grub_defaults" ] || touch "$grub_defaults"
    if ! grep -Fxq "$setting" "$grub_defaults"; then
        echo "$setting" >> "$grub_defaults"
    fi
}

ensure_efi_mount() {
    if ! mountpoint -q /boot; then
        echo "ERROR: /boot is not mounted (EFI partition missing)"
        exit 1
    fi

    local fs_type
    fs_type=$($FINDMNT -n -o FSTYPE /boot 2>/dev/null || true)
    if [ "$fs_type" != "vfat" ]; then
        echo "ERROR: /boot must be mounted as vfat for EFI (found: ${fs_type:-unknown})"
        exit 1
    fi

    mkdir -p /boot/EFI/BOOT
    mkdir -p /boot/EFI/madOS
}

is_secure_boot_enabled() {
    local sb_var
    sb_var="/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c"
    if [ -f "$sb_var" ]; then
        local sb_val
        sb_val=$(od -An -t u1 -j4 -N1 "$sb_var" 2>/dev/null | tr -d ' ')
        [ "$sb_val" = "1" ] && return 0
    fi
    return 1
}

is_setup_mode_enabled() {
    local sm_var
    sm_var="/sys/firmware/efi/efivars/SetupMode-8be4df61-93ca-11d2-aa0d-00e098032b8c"
    if [ -f "$sm_var" ]; then
        local sm_val
        sm_val=$(od -An -t u1 -j4 -N1 "$sm_var" 2>/dev/null | tr -d ' ')
        [ "$sm_val" = "1" ] && return 0
    fi
    return 1
}

install_grub_uefi() {
    append_grub_setting_once 'GRUB_DISABLE_SHIM_LOCK=true'

    if ! $GRUB_INSTALL --target=x86_64-efi --efi-directory=/boot --bootloader-id=madOS --recheck 2>&1; then
        echo "WARN: grub-install with --bootloader-id failed (NVRAM may be read-only)"
    fi

    if ! $GRUB_INSTALL --target=x86_64-efi --efi-directory=/boot --removable --recheck 2>&1; then
        echo "ERROR: GRUB UEFI --removable install failed"
        exit 1
    fi

    if [ ! -f /boot/EFI/madOS/grubx64.efi ]; then
        echo "ERROR: /boot/EFI/madOS/grubx64.efi was not created"
        exit 1
    fi

    if [ ! -f /boot/EFI/BOOT/BOOTX64.EFI ]; then
        cp /boot/EFI/madOS/grubx64.efi /boot/EFI/BOOT/BOOTX64.EFI
    fi

    if [ ! -f /boot/EFI/BOOT/BOOTX64.EFI ]; then
        echo "ERROR: /boot/EFI/BOOT/BOOTX64.EFI was not created"
        exit 1
    fi
}

setup_sbctl_hook() {
    mkdir -p /etc/pacman.d/hooks
    cat > /etc/pacman.d/hooks/99-sbctl-sign.hook <<'EOFHOOK'
[Trigger]
Operation = Install
Operation = Upgrade
Type = Package
Target = linux
Target = linux-lts
Target = linux-zen
Target = linux-mados
Target = grub

[Action]
Description = Signing EFI binaries for Secure Boot...
When = PostTransaction
Exec = /usr/bin/sbctl sign-all
Depends = sbctl
EOFHOOK
}

sign_secure_boot_artifacts() {
    local artifacts=()
    local path

    for path in \
        /boot/EFI/BOOT/BOOTX64.EFI \
        /boot/EFI/BOOT/grubx64.efi \
        /boot/EFI/madOS/grubx64.efi; do
        if [ -f "$path" ]; then
            artifacts+=("$path")
        fi
    done

    for path in \
        /boot/vmlinuz-linux-lts \
        /boot/vmlinuz-linux-mados \
        /boot/vmlinuz-linux \
        /boot/vmlinuz-linux-zen; do
        if [ -f "$path" ]; then
            artifacts+=("$path")
        fi
    done

    if [ "${#artifacts[@]}" -eq 0 ]; then
        echo "ERROR: No EFI artifacts found to sign"
        exit 1
    fi

    for path in "${artifacts[@]}"; do
        echo "    Signing $path"
        sbctl sign -s "$path"
    done
}

find_first_existing() {
    local candidate
    for candidate in "$@"; do
        if [ -f "$candidate" ]; then
            printf '%s' "$candidate"
            return 0
        fi
    done
    return 1
}

setup_secure_boot_setup_mode() {
    require_cmd sbctl

    echo "==> Secure Boot ON + Setup Mode ON: using sbctl key enrollment"
    sbctl create-keys 2>/dev/null || true
    sbctl enroll-keys --microsoft
    sign_secure_boot_artifacts
    setup_sbctl_hook
}

setup_secure_boot_shim_mok() {
    require_cmd sbctl
    require_cmd mokutil
    require_cmd openssl

    echo "==> Secure Boot ON + Setup Mode OFF: using shim + MOK enrollment"

    sbctl create-keys 2>/dev/null || true
    sign_secure_boot_artifacts

    cp /boot/EFI/madOS/grubx64.efi /boot/EFI/BOOT/grubx64.efi

    local shim_src
    shim_src=$(find_first_existing \
        /usr/share/shim-signed/shimx64.efi \
        /usr/share/shim/shimx64.efi \
        /usr/lib/shim/shimx64.efi) || {
        echo "ERROR: Could not find shimx64.efi (package 'shim' missing?)"
        exit 1
    }

    cp "$shim_src" /boot/EFI/BOOT/BOOTX64.EFI
    cp "$shim_src" /boot/EFI/madOS/shimx64.efi

    local mm_src
    mm_src=$(find_first_existing \
        /usr/share/shim-signed/mmx64.efi \
        /usr/share/shim/mmx64.efi \
        /usr/lib/shim/mmx64.efi) || true

    if [ -n "${mm_src:-}" ]; then
        cp "$mm_src" /boot/EFI/BOOT/MMX64.EFI
        cp "$mm_src" /boot/EFI/madOS/mmx64.efi
    fi

    local db_pem db_der
    db_pem="/var/lib/sbctl/keys/db/db.pem"
    db_der="/boot/EFI/madOS/mados-db.cer"
    if [ ! -f "$db_pem" ]; then
        echo "ERROR: sbctl db key not found at $db_pem"
        exit 1
    fi

    openssl x509 -outform DER -in "$db_pem" -out "$db_der"

    local mok_password_file
    mok_password_file="/root/mok-password.txt"
    head -c 128 /dev/urandom | tr -dc 'A-Za-z0-9' | head -c 20 > "$mok_password_file"
    chmod 600 "$mok_password_file"

    if mokutil --help 2>&1 | grep -q -- "--password-file"; then
        mokutil --import "$db_der" --password-file "$mok_password_file"
    elif mokutil --help 2>&1 | grep -q -- "--password"; then
        mokutil --import "$db_der" --password "$(cat "$mok_password_file")"
    else
        echo "ERROR: mokutil does not support non-interactive password options"
        exit 1
    fi

    setup_sbctl_hook

    echo "==> MOK enrollment prepared"
    echo "    On next boot, MokManager will prompt for enrollment."
    echo "    Password is stored at: /root/mok-password.txt"
}

validate_boot_artifacts() {
    local required_paths=(
        "/boot/EFI/BOOT/BOOTX64.EFI"
        "/boot/EFI/madOS/grubx64.efi"
    )

    local path
    for path in "${required_paths[@]}"; do
        if [ ! -s "$path" ]; then
            echo "ERROR: Required boot artifact missing: $path"
            exit 1
        fi
    done

    local kernel_found=0
    local kernel_path
    for kernel_path in \
        /boot/vmlinuz-linux-lts \
        /boot/vmlinuz-linux-mados \
        /boot/vmlinuz-linux \
        /boot/vmlinuz-linux-zen; do
        if [ -s "$kernel_path" ]; then
            kernel_found=1
            break
        fi
    done

    if [ "$kernel_found" -ne 1 ]; then
        echo "ERROR: Required kernel artifact missing: expected one of /boot/vmlinuz-linux-lts|linux-mados|linux|linux-zen"
        exit 1
    fi
}

require_cmd "$GRUB_INSTALL"
require_cmd "$FINDMNT"

if [ -d /sys/firmware/efi ]; then
    echo "==> Detected UEFI boot mode"

    if ! mountpoint -q /sys/firmware/efi/efivars 2>/dev/null; then
        mount -t efivarfs efivarfs /sys/firmware/efi/efivars 2>/dev/null || true
    fi

    ensure_efi_mount
    install_grub_uefi

    if is_secure_boot_enabled; then
        if is_setup_mode_enabled; then
            setup_secure_boot_setup_mode
        else
            setup_secure_boot_shim_mok
        fi
    else
        echo "==> Secure Boot is disabled"
    fi

    validate_boot_artifacts
else
    echo "==> Detected BIOS boot mode"
    if ! $GRUB_INSTALL --target=i386-pc --recheck "$DISK" 2>&1; then
        echo "ERROR: GRUB BIOS install failed"
        exit 1
    fi
fi

echo "  GRUB bootloader installed"
