"""
madOS Installer - Configuration script builder
"""

import re

from config import (
    LOCALE_KB_MAP,
    LOCALE_MAP,
    TIMEZONES,
)


def _escape_shell(s):
    """Escape a string for safe use inside single quotes in shell"""
    return s.replace("'", "'\\''")


def _get_partition_prefix(disk):
    """Get partition prefix (nvme/mmcblk use 'p' separator)"""
    return f"{disk}p" if "nvme" in disk or "mmcblk" in disk else disk


def build_config_script(data):
    """Build the chroot configuration shell script."""
    disk = data["disk"]

    timezone = data["timezone"]
    if timezone not in TIMEZONES:
        raise ValueError(f"Invalid timezone: {timezone}")

    locale = data["locale"]
    valid_locales = list(LOCALE_MAP.values())
    if locale not in valid_locales:
        raise ValueError(f"Invalid locale: {locale}")

    if not re.match(r"^/dev/[a-zA-Z0-9]+$", disk):
        raise ValueError(f"Invalid disk path: {disk}")

    username = data["username"]
    if not re.match(r"^[a-z_][a-z0-9_-]*$", username):
        raise ValueError(f"Invalid username: {username}")

    part_prefix = _get_partition_prefix(disk)
    root_part = f"{part_prefix}3"
    boot_part = f"{part_prefix}2"

    return f'''#!/bin/bash
set -e

# ── Configuration variables ─────────────────────────────────────────────────
disk="{disk}"

# ── Initialize pacman keyring ────────────────────────────────────────────────
echo '  Initializing pacman keyring...'
[ -d /etc/pacman.d/gnupg ] && rm -rf /etc/pacman.d/gnupg
pacman-key --init
pacman-key --populate archlinux
echo '  Pacman keyring initialized'

echo "[PROGRESS 1/8] Setting timezone and locale..."
# Timezone
ln -sf /usr/share/zoneinfo/{timezone} /etc/localtime
hwclock --systohc 2>/dev/null || true

# Locale
echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
echo "{locale} UTF-8" >> /etc/locale.gen
locale-gen
echo "LANG={locale}" > /etc/locale.conf

echo '[PROGRESS 2/8] Creating user account...'
# Hostname
echo '{_escape_shell(data["hostname"])}' > /etc/hostname
cat > /etc/hosts <<EOF
127.0.0.1   localhost
::1         localhost
127.0.1.1   {_escape_shell(data["hostname"])}.localdomain {_escape_shell(data["hostname"])}
EOF

# ── Clean up live ISO artifacts ─────────────────────────────────────────
rm -rf /etc/systemd/system/getty@tty1.service.d

for svc in \
    livecd-talk.service \
    livecd-alsa-unmuter.service \
    pacman-init.service \
    etc-pacman.d-gnupg.mount \
    choose-mirror.service \
    mados-persistence-detect.service \
    mados-persist-sync.service \
    mados-ventoy-setup.service \
    mados-ventoy-setup.service \
    mados-timezone.service \
    mados-installer-autostart.service; do
    systemctl disable "$svc" 2>/dev/null || true
    rm -f "/etc/systemd/system/$svc"
done

find /etc/systemd/system -type l ! -exec test -e {{}} \\; -delete 2>/dev/null || true

if id mados &>/dev/null; then
    userdel -r mados 2>/dev/null || userdel mados 2>/dev/null || true
    rm -rf /home/mados
fi

rm -f /etc/sudoers.d/99-opencode-nopasswd

# User
useradd -m -G wheel,audio,video,storage -s /usr/bin/zsh {username}
echo '{username}:{_escape_shell(data["password"])}' | chpasswd

# Sudo
echo "%wheel ALL=(ALL:ALL) ALL" > /etc/sudoers.d/wheel
chmod 440 /etc/sudoers.d/wheel

echo "{username} ALL=(ALL:ALL) NOPASSWD: /usr/local/bin/opencode,/usr/local/bin/ollama,/usr/bin/pacman,/usr/bin/systemctl" > /etc/sudoers.d/opencode-nopasswd
chmod 440 /etc/sudoers.d/opencode-nopasswd

# Ensure kernel image exists at /boot/vmlinuz-linux
if [ ! -s /boot/vmlinuz-linux ] || [ ! -r /boot/vmlinuz-linux ]; then
    echo '  Kernel not found or unreadable at /boot/vmlinuz-linux, recovering...'
    KERN_FOUND=0
    for kdir in /usr/lib/modules/*/; do
        if [ -r "${{kdir}}vmlinuz" ]; then
            cp "${{kdir}}vmlinuz" /boot/vmlinuz-linux
            echo "  Recovered kernel from ${{kdir}}vmlinuz"
            KERN_FOUND=1
            break
        fi
    done
    if [ "$KERN_FOUND" = "0" ]; then
        echo '  Modules vmlinuz not found. Reinstalling linux package...'
        pacman -Sy --noconfirm linux || {{ echo 'FATAL: Failed to install kernel'; exit 1; }}
    fi
fi
if [ ! -s /boot/vmlinuz-linux ] || [ ! -r /boot/vmlinuz-linux ]; then
    echo 'FATAL: /boot/vmlinuz-linux is missing or unreadable after recovery!'
    exit 1
fi

echo '[PROGRESS 3/8] Installing GRUB bootloader...'
# GRUB - Auto-detect UEFI or BIOS
if [ -d /sys/firmware/efi ]; then
    echo "==> Detected UEFI boot mode"
    if ! mountpoint -q /sys/firmware/efi/efivars 2>/dev/null; then
        mount -t efivarfs efivarfs /sys/firmware/efi/efivars 2>/dev/null || true
    fi

    echo 'GRUB_DISABLE_SHIM_LOCK=true' >> /etc/default/grub

    if ! grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=madOS --recheck 2>&1; then
        echo "WARN: grub-install bootloader-id failed (NVRAM may be read-only)"
    fi
    if ! grub-install --target=x86_64-efi --efi-directory=/boot --removable --recheck 2>&1; then
        echo "ERROR: GRUB UEFI --removable install failed!"
        exit 1
    fi
    if [ ! -f /boot/EFI/BOOT/BOOTX64.EFI ]; then
        echo "ERROR: /boot/EFI/BOOT/BOOTX64.EFI was not created!"
        exit 1
    fi

    SECURE_BOOT=0
    if [ -f /sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c ]; then
        SB_VAL=$(od -An -t u1 -j4 -N1 /sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c 2>/dev/null | tr -d ' ')
        [ "$SB_VAL" = "1" ] && SECURE_BOOT=1
    fi

    if [ "$SECURE_BOOT" = "1" ]; then
        echo "==> Secure Boot is ENABLED – setting up sbctl signing"

        sbctl create-keys 2>/dev/null || echo "WARN: sbctl keys may already exist"

        SETUP_MODE=0
        if [ -f /sys/firmware/efi/efivars/SetupMode-8be4df61-93ca-11d2-aa0d-00e098032b8c ]; then
            SM_VAL=$(od -An -t u1 -j4 -N1 /sys/firmware/efi/efivars/SetupMode-8be4df61-93ca-11d2-aa0d-00e098032b8c 2>/dev/null | tr -d ' ')
            [ "$SM_VAL" = "1" ] && SETUP_MODE=1
        fi

        if [ "$SETUP_MODE" = "1" ]; then
            echo "==> Firmware is in Setup Mode – enrolling Secure Boot keys"
            sbctl enroll-keys --microsoft 2>&1 || echo "WARN: Could not enroll keys automatically"
        else
            echo "==> Firmware is NOT in Setup Mode"
            echo "    After first reboot, enter UEFI firmware settings and either:"
            echo "    1) Disable Secure Boot, or"
            echo "    2) Put firmware in Setup Mode, reboot to madOS, then run: sudo sbctl enroll-keys --microsoft"
        fi

        for f in /boot/EFI/BOOT/BOOTX64.EFI /boot/EFI/madOS/grubx64.efi /boot/vmlinuz-linux; do
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
Target = grub

[Action]
Description = Signing EFI binaries for Secure Boot...
When = PostTransaction
Exec = /usr/bin/sbctl sign-all
Depends = sbctl
EOFHOOK
    else
        echo "==> Secure Boot is disabled – skipping sbctl signing"
    fi
else
    echo "==> Detected BIOS boot mode"
    BASE_DISK=$(echo "$disk" | sed 's/[0-9]*$//')
    echo "  Using disk: $BASE_DISK"
    if ! grub-install --target=i386-pc --recheck "$BASE_DISK" 2>&1; then
        echo "ERROR: GRUB BIOS install failed!"
        exit 1
    fi
fi

echo '[PROGRESS 4/8] Configuring GRUB...'
sed -i 's/GRUB_CMDLINE_LINUX=""/GRUB_CMDLINE_LINUX="zswap.enabled=0 splash quiet"/' /etc/default/grub
sed -i 's/GRUB_DISTRIBUTOR="Arch"/GRUB_DISTRIBUTOR="madOS"/' /etc/default/grub
sed -i 's/#GRUB_DISABLE_OS_PROBER=false/GRUB_DISABLE_OS_PROBER=false/' /etc/default/grub
echo 'GRUB_DISABLE_LINUX_UUID=false' >> /etc/default/grub

# Detect root partition UUID for boot
ROOT_UUID=$(blkid -s UUID -o value {root_part} 2>/dev/null || echo "")
if [ -n "$ROOT_UUID" ]; then
    echo "  Root partition UUID: $ROOT_UUID"
    # Create custom menu entry with UUID
    mkdir -p /boot/grub/custom
    cat > /boot/grub/custom/mados.cfg <<'EOFGRUB'
menuentry 'madOS Linux' {{
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
}}
EOFGRUB
fi

grub-mkconfig -o /boot/grub/grub.cfg
if [ ! -f /boot/grub/grub.cfg ]; then
    echo "ERROR: grub.cfg was not generated!"
    exit 1
fi

echo '[PROGRESS 5/8] Setting up Plymouth boot splash...'
# Plymouth theme
mkdir -p /usr/share/plymouth/themes/mados
cat > /usr/share/plymouth/themes/mados/mados.plymouth <<EOFPLY
[Plymouth Theme]
Name=madOS
Description=madOS boot splash with Nord theme
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/mados
ScriptFile=/usr/share/plymouth/themes/mados/mados.script
EOFPLY

cat > /usr/share/plymouth/themes/mados/mados.script <<'EOFSCRIPT'
Window.SetBackgroundTopColor(0.18, 0.20, 0.25);
Window.SetBackgroundBottomColor(0.13, 0.15, 0.19);
logo.image = Image("logo.png");
logo.sprite = Sprite(logo.image);
logo.sprite.SetX(Window.GetWidth() / 2 - logo.image.GetWidth() / 2);
logo.sprite.SetY(Window.GetHeight() / 2 - logo.image.GetHeight() / 2 - 50);
logo.sprite.SetZ(10);
logo.sprite.SetOpacity(1);
NUM_DOTS = 8;
SPINNER_RADIUS = 25;
spinner_x = Window.GetWidth() / 2;
spinner_y = Window.GetHeight() / 2 + logo.image.GetHeight() / 2;
dot_image = Image("dot.png");
for (i = 0; i < NUM_DOTS; i++) {{
    dot[i].sprite = Sprite(dot_image);
    dot[i].sprite.SetZ(10);
    angle = i * 2 * 3.14159 / NUM_DOTS;
    dot[i].sprite.SetX(spinner_x + SPINNER_RADIUS * Math.Sin(angle) - dot_image.GetWidth() / 2);
    dot[i].sprite.SetY(spinner_y - SPINNER_RADIUS * Math.Cos(angle) - dot_image.GetHeight() / 2);
    dot[i].sprite.SetOpacity(0.2);
}}
frame = 0;
fun refresh_callback() {{
    frame++;
    active_dot = Math.Int(frame / 4) % NUM_DOTS;
    for (i = 0; i < NUM_DOTS; i++) {{
        dist = active_dot - i;
        if (dist < 0) dist = dist + NUM_DOTS;
        if (dist == 0) opacity = 1.0;
        else if (dist == 1) opacity = 0.7;
        else if (dist == 2) opacity = 0.45;
        else if (dist == 3) opacity = 0.25;
        else opacity = 0.12;
        dot[i].sprite.SetOpacity(opacity);
    }}
    pulse = Math.Abs(Math.Sin(frame * 0.02)) * 0.08 + 0.92;
    logo.sprite.SetOpacity(pulse);
}}
Plymouth.SetRefreshFunction(refresh_callback);
fun display_normal_callback(text) {{}}
fun display_message_callback(text) {{}}
Plymouth.SetDisplayNormalFunction(display_normal_callback);
Plymouth.SetMessageFunction(display_message_callback);
fun quit_callback() {{
    for (i = 0; i < NUM_DOTS; i++) {{ dot[i].sprite.SetOpacity(0); }}
    logo.sprite.SetOpacity(1);
}}
Plymouth.SetQuitFunction(quit_callback);
EOFSCRIPT

plymouth-set-default-theme mados 2>/dev/null || true
mkdir -p /etc/plymouth
cat > /etc/plymouth/plymouthd.conf <<EOFPLYCONF
[Daemon]
Theme=mados
ShowDelay=0
DeviceTimeout=5
EOFPLYCONF

echo '[PROGRESS 6/8] Rebuilding initramfs...'
pacman -Rdd --noconfirm mkinitcpio-archiso 2>/dev/null || true
rm -f /etc/mkinitcpio.conf.d/archiso.conf
rm -f /etc/mkinitcpio.d/linux.preset

# Add storage and network modules for broad hardware support:
# - virtio: QEMU/KVM virtual machines
# - ahci: Modern SATA controllers
# - ata: Legacy ATA/SATA
# - scsi_mod, sd_mod, sg: SCSI support
# - nvme: NVMe SSDs
# - loop: Loop devices
# - dm_mod: Device Mapper/LVM
# - ext4, xfs, btrfs: Filesystems
# - usb_storage: USB drives
# - pata: Legacy IDE
# - sata_nv, sata_via, sata_ali: Various SATA controllers
MODULES_LIST="virtio virtio_blk virtio_scsi virtio_net virtio_pci virtio_balloon ahci ata scsi_mod sd_mod sg nvme loop dm_mod ext4 xfs btrfs usb_storage pata sata_nv sata_via sata_ali"
sed -i "s/^MODULES=()/MODULES=($MODULES_LIST)/" /etc/mkinitcpio.conf

cat <<'EOFPRESET' > /etc/mkinitcpio.d/linux.preset
ALL_config="/etc/mkinitcpio.conf"
ALL_kver="/boot/vmlinuz-linux"
PRESETS=('default')
default_image="/boot/initramfs-linux.img"
fallback_image="/boot/initramfs-linux-fallback.img"
EOFPRESET
sync
mkinitcpio -P
if [ ! -f /boot/initramfs-linux.img ]; then
    echo "ERROR: initramfs not created! Trying fallback..."
    mkinitcpio -p linux
fi
if [ ! -f /boot/initramfs-linux.img ]; then
    echo "ERROR: initramfs still not created!"
    exit 1
fi
echo "  initramfs created successfully with virtio drivers"

echo '[PROGRESS 7/8] Enabling essential services...'
passwd -l root

systemctl enable NetworkManager
systemctl enable systemd-resolved
systemctl enable earlyoom
systemctl enable systemd-timesyncd
systemctl enable greetd
systemctl enable iwd
systemctl enable bluetooth
systemctl enable plymouth-quit-wait.service 2>/dev/null || true

systemctl --global enable pipewire.socket pipewire-pulse.socket wireplumber.service 2>/dev/null || true

echo '[PROGRESS 8/8] Applying system configuration...'
set +e

# madOS branding
cat > /etc/os-release <<EOF
NAME="madOS"
PRETTY_NAME="madOS (Arch Linux)"
ID=mados
ID_LIKE=arch
BUILD_ID=rolling
ANSI_COLOR="38;2;23;147;209"
HOME_URL="https://github.com/madkoding/mad-os"
DOCUMENTATION_URL="https://wiki.archlinux.org/"
SUPPORT_URL="https://bbs.archlinux.org/"
BUG_REPORT_URL="https://gitlab.archlinux.org/groups/archlinux/-/issues"
PRIVACY_POLICY_URL="https://terms.archlinux.org/docs/privacy-policy/"
LOGO=archlinux-logo
EOF

# NetworkManager iwd backend
mkdir -p /etc/NetworkManager/conf.d
cat > /etc/NetworkManager/conf.d/wifi-backend.conf <<EOF
[device]
wifi.backend=iwd
EOF

# Kernel optimizations
cat > /etc/sysctl.d/99-extreme-low-ram.conf <<EOF
vm.vfs_cache_pressure = 200
vm.swappiness = 5
vm.dirty_ratio = 5
vm.dirty_background_ratio = 3
vm.min_free_kbytes = 16384
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_tw_reuse = 1
net.core.rmem_max = 262144
net.core.wmem_max = 262144
EOF

# ZRAM
cat > /etc/systemd/zram-generator.conf <<EOF
[zram0]
zram-size = ram / 2
compression-algorithm = zstd
swap-priority = 100
fs-type = swap
EOF

# greetd + ReGreet
mkdir -p /etc/greetd
cat > /etc/greetd/config.toml <<'EOFGREETD'
[terminal]
vt = 1

[default_session]
command = "/usr/local/bin/cage-greeter"
user = "greeter"
EOFGREETD

cat > /etc/greetd/regreet.toml <<'EOFREGREET'
[background]
path = "/usr/share/backgrounds/mad-os-wallpaper.png"
fit = "Cover"

[env]
LIBSEAT_BACKEND = "logind"

[GTK]
application_prefer_dark_theme = true

[commands]
reboot = [ "systemctl", "reboot" ]
poweroff = [ "systemctl", "poweroff" ]
EOFREGREET

chown -R greeter:greeter /etc/greetd
chmod 755 /etc/greetd
chmod 644 /etc/greetd/config.toml /etc/greetd/regreet.toml

usermod -aG video,input greeter 2>/dev/null || echo "Note: greeter user group modification skipped"

mkdir -p /var/cache/regreet
chown greeter:greeter /var/cache/regreet
chmod 750 /var/cache/regreet
mkdir -p /var/lib/greetd
chown greeter:greeter /var/lib/greetd

mkdir -p /etc/systemd/system/greetd.service.d
cat > /etc/systemd/system/greetd.service.d/override.conf <<'EOFOVERRIDE'
[Unit]
After=systemd-logind.service plymouth-quit-wait.service
Wants=systemd-logind.service
Conflicts=getty@tty1.service
After=getty@tty1.service
EOFOVERRIDE

# Copy configs to user home
install -d -o {username} -g {username} /home/{username}/.config/{{sway,hypr,waybar,foot,wofi,gtk-3.0,gtk-4.0}}
install -d -o {username} -g {username} /home/{username}/{{Documents,Downloads,Music,Videos,Desktop,Templates,Public}}
install -d -o {username} -g {username} /home/{username}/Pictures/{{Wallpapers,Screenshots}}
cp -r /etc/skel/.config/* /home/{username}/.config/ 2>/dev/null || true
cp -r /etc/skel/Pictures/* /home/{username}/Pictures/ 2>/dev/null || true
cp /etc/skel/.gtkrc-2.0 /home/{username}/.gtkrc-2.0 2>/dev/null || true

# Copy system media content
mkdir -p /usr/share/music /usr/share/video
cp /usr/share/music/* /home/{username}/Music/ 2>/dev/null || true
cp /usr/share/video/* /home/{username}/Videos/ 2>/dev/null || true

cp /etc/profile.d/mados-media-links.sh /etc/profile.d/ 2>/dev/null || true

chown -R {username}:{username} /home/{username}

# Set keyboard layout
KB_LAYOUT="{LOCALE_KB_MAP.get(locale, "us")}"
if [ -f /home/{username}/.config/sway/config ]; then
    sed -i "s/xkb_layout \"es\"/xkb_layout \"$KB_LAYOUT\"/" /home/{username}/.config/sway/config
elif [ -f /etc/skel/.config/sway/config ]; then
    sed -i "s/xkb_layout \"es\"/xkb_layout \"$KB_LAYOUT\"/" /etc/skel/.config/sway/config
fi
if [ -f /home/{username}/.config/hypr/hyprland.conf ]; then
    sed -i "s/kb_layout = es/kb_layout = $KB_LAYOUT/" /home/{username}/.config/hypr/hyprland.conf
elif [ -f /etc/skel/.config/hypr/hyprland.conf ]; then
    sed -i "s/kb_layout = es/kb_layout = $KB_LAYOUT/" /etc/skel/.config/hypr/hyprland.conf
fi

if [ ! -f /home/{username}/.bash_profile ]; then
    cp /etc/skel/.bash_profile /home/{username}/.bash_profile 2>/dev/null || true
fi
chown {username}:{username} /home/{username}/.bash_profile

if [ -f /etc/skel/.zshrc ]; then
    cp /etc/skel/.zshrc /home/{username}/.zshrc 2>/dev/null || true
    chown {username}:{username} /home/{username}/.zshrc
fi

# Ventoy/persistence configuration
mkdir -p /etc/mados
cat > /etc/mados/ventoy-persist.conf << EOFVENTOY
# madOS Persistence Configuration

VENTOY_PERSIST_SIZE_MB={data.get("ventoy_persist_size", 4096)}

MIN_FREE_SPACE_MB=512
EOFVENTOY
chmod 644 /etc/mados/ventoy-persist.conf

# Clean up archiso artifacts
rm -f /root/.automated_script.sh /root/.zlogin

# Pacman hooks for session file protection
mkdir -p /etc/pacman.d/hooks
cat > /etc/pacman.d/hooks/sway-desktop-override.hook <<'EOFHOOK'
[Trigger]
Operation = Install
Operation = Upgrade
Type = Package
Target = sway

[Action]
Description = Customizing Sway session for madOS...
When = PostTransaction
Depends = sed
Exec = /usr/bin/sed -i -e 's|^Exec=.*|Exec=/usr/local/bin/sway-session|' -e 's|^Comment=.*|Comment=madOS Sway session with hardware detection|' /usr/share/wayland-sessions/sway.desktop
EOFHOOK

cat > /etc/pacman.d/hooks/hyprland-desktop-override.hook <<'EOFHOOK2'
[Trigger]
Operation = Install
Operation = Upgrade
Type = Package
Target = hyprland

[Action]
Description = Customizing Hyprland session for madOS...
When = PostTransaction
Depends = sed
Exec = /usr/bin/sed -i -e 's|^Exec=.*|Exec=/usr/local/bin/hyprland-session|' -e 's|^Comment=.*|Comment=madOS Hyprland session|' /usr/share/wayland-sessions/hyprland.desktop
EOFHOOK2

# Graphical environment verification
echo "Verifying graphical environment components..."
GRAPHICAL_OK=1
for bin in cage regreet sway; do
    if command -v "$bin" &>/dev/null; then
        echo "  ✓ $bin found: $(command -v "$bin")"
    else
        echo "  ✗ $bin NOT found — graphical login may fail"
        GRAPHICAL_OK=0
    fi
done

for script in /usr/local/bin/cage-greeter /usr/local/bin/sway-session /usr/local/bin/hyprland-session /usr/local/bin/start-hyprland /usr/local/bin/select-compositor; do
    if [ -x "$script" ]; then
        echo "  ✓ $script is executable"
    elif [ -f "$script" ]; then
        echo "  ✗ $script exists but is not executable — fixing..."
        chmod +x "$script"
    else
        echo "  ✗ $script NOT found — graphical login may fail"
        GRAPHICAL_OK=0
    fi
done

if [ -f /etc/greetd/config.toml ]; then
    echo "  ✓ greetd config exists"
else
    echo "  ✗ greetd config NOT found — graphical login may fail"
    GRAPHICAL_OK=0
fi

if [ -f /etc/greetd/regreet.toml ]; then
    echo "  ✓ regreet config exists"
else
    echo "  ✗ regreet.toml NOT found — greeter UI may fail"
    GRAPHICAL_OK=0
fi

for session_file in /usr/share/wayland-sessions/sway.desktop /usr/share/wayland-sessions/hyprland.desktop; do
    if [ -f "$session_file" ]; then
        if grep -q "/usr/local/bin/" "$session_file"; then
            echo "  ✓ $session_file has madOS session script"
        else
            echo "  ⚠ $session_file exists but Exec= may not point to madOS script — fixing..."
            session_name=$(basename "$session_file" .desktop)
            if [ -x "/usr/local/bin/${{session_name}}-session" ]; then
                sed -i "s|^Exec=.*|Exec=/usr/local/bin/${{session_name}}-session|" "$session_file"
                echo "    Fixed: Exec=/usr/local/bin/${{session_name}}-session"
            fi
        fi
    else
        echo "  ✗ $session_file NOT found — session may not appear in greeter"
    fi
done

if systemctl is-enabled greetd.service &>/dev/null; then
    echo "  ✓ greetd.service is enabled"
else
    echo "  ✗ greetd.service is NOT enabled — enabling..."
    systemctl enable greetd.service 2>/dev/null || true
fi

systemctl enable getty@tty2.service 2>/dev/null || true

if [ "$GRAPHICAL_OK" -eq 0 ]; then
    echo "  ⚠ Some graphical components are missing. Enabling getty@tty1 as fallback..."
    systemctl enable getty@tty1.service 2>/dev/null || true
fi

echo "Graphical environment verification complete."
'''


def write_config_script(data, path="/mnt/root/configure.sh"):
    """Write the configuration script to a file."""
    import os

    script_content = build_config_script(data)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o700)
    with os.fdopen(fd, "w") as f:
        f.write(script_content)
