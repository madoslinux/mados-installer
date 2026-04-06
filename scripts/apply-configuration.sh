#!/bin/bash
# madOS Final Configuration Script
set -e

USERNAME="${1:-}"
LOCALE="${2:-}"
VENTOY_PERSIST_SIZE="${3:-4096}"

if [ -z "$USERNAME" ]; then
    echo "ERROR: Username not provided"
    exit 1
fi

KB_LAYOUT="us"
case "$LOCALE" in
    en_US.UTF-8) KB_LAYOUT="us" ;;
    es_AR.UTF-8) KB_LAYOUT="latam" ;;
    es_ES.UTF-8) KB_LAYOUT="es" ;;
    pt_BR.UTF-8) KB_LAYOUT="br" ;;
    fr_FR.UTF-8) KB_LAYOUT="fr" ;;
    de_DE.UTF-8) KB_LAYOUT="de" ;;
    it_IT.UTF-8) KB_LAYOUT="it" ;;
esac

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

mkdir -p /etc/NetworkManager/conf.d
cat > /etc/NetworkManager/conf.d/wifi-backend.conf <<EOF
[device]
EOF

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

cat > /etc/systemd/zram-generator.conf <<EOF
[zram0]
zram-size = ram / 2
compression-algorithm = zstd
swap-priority = 100
fs-type = swap
EOF

# Configure LightDM with GTK greeter
cat > /etc/lightdm/lightdm.conf <<'EOLIGHTDM'
[Seat:*]
greeter-session = lightdm-gtk-greeter
user-session = hyprland
allow-user-switching = true
allow-guest = false
session-wrapper = /etc/lightdm/Xsession
EOLIGHTDM

cat > /etc/lightdm/lightdm-gtk-greeter.conf <<'EOLIGHTDMGTK'
[greeter]
icon-theme-name = Adwaita
background = /usr/share/backgrounds/mad-os-wallpaper.png
default-user-image = /usr/share/pixmaps/hicolor/128x128/apps/system-logo-icon.png
xft-antialias = true
xft-dpi = 96
xft-font = Sans 10
indicators = ~clock;~language;~session;~power
clock-format = %a %d %b  %H:%M
hide-users = false
show-manual-login = false
show-guest = false
EOLIGHTDMGTK

install -d -o "$USERNAME" -g "$USERNAME" /home/"$USERNAME"/.config/{sway,hypr,waybar,foot,wofi,gtk-3.0,gtk-4.0}
install -d -o "$USERNAME" -g "$USERNAME" /home/"$USERNAME"/{Documents,Downloads,Music,Videos,Desktop,Templates,Public}
install -d -o "$USERNAME" -g "$USERNAME" /home/"$USERNAME"/Pictures/{Wallpapers,Screenshots}
cp -r /etc/skel/.config/* /home/"$USERNAME"/.config/ 2>/dev/null || true
cp /etc/skel/.gtkrc-2.0 /home/"$USERNAME"/.gtkrc-2.0 2>/dev/null || true

mkdir -p /usr/share/music /usr/share/video
cp /usr/share/music/* /home/"$USERNAME"/Music/ 2>/dev/null || true
cp /usr/share/video/* /home/"$USERNAME"/Videos/ 2>/dev/null || true

cp /etc/profile.d/mados-media-links.sh /etc/profile.d/ 2>/dev/null || true

chown -R "$USERNAME":"$USERNAME" /home/"$USERNAME"

if [ -f /home/"$USERNAME"/.config/sway/config ]; then
    sed -i "s/xkb_layout \"es\"/xkb_layout \"$KB_LAYOUT\"/" /home/"$USERNAME"/.config/sway/config
elif [ -f /etc/skel/.config/sway/config ]; then
    sed -i "s/xkb_layout \"es\"/xkb_layout \"$KB_LAYOUT\"/" /etc/skel/.config/sway/config
fi

if [ -f /home/"$USERNAME"/.config/hypr/hyprland.conf ]; then
    sed -i "s/kb_layout = es/kb_layout = $KB_LAYOUT/" /home/"$USERNAME"/.config/hypr/hyprland.conf
elif [ -f /etc/skel/.config/hypr/hyprland.conf ]; then
    sed -i "s/kb_layout = es/kb_layout = $KB_LAYOUT/" /etc/skel/.config/hypr/hyprland.conf
fi

if [ ! -f /home/"$USERNAME"/.bash_profile ]; then
    cp /etc/skel/.bash_profile /home/"$USERNAME"/.bash_profile 2>/dev/null || true
fi
chown "$USERNAME":"$USERNAME" /home/"$USERNAME"/.bash_profile

if [ -f /etc/skel/.zshrc ]; then
    cp /etc/skel/.zshrc /home/"$USERNAME"/.zshrc 2>/dev/null || true
    chown "$USERNAME":"$USERNAME" /home/"$USERNAME"/.zshrc
fi

# ════════════════════════════════════════════════════════════════════════════
# Yay (AUR helper) - Install to user home from system binary
# ════════════════════════════════════════════════════════════════════════════
install_yay_to_user() {
    local yay_src="/usr/local/bin/yay"
    local yay_bin="/home/$USERNAME/.local/bin/yay"

    if command -v yay &>/dev/null; then
        echo "  ✓ yay available system-wide"
        return 0
    fi

    if [ ! -f "$yay_src" ]; then
        echo "  ⚠ yay binary not found in /usr/local/bin"
        return 1
    fi

    mkdir -p "/home/$USERNAME/.local/bin"
    if [ ! -f "$yay_bin" ]; then
        cp "$yay_src" "$yay_bin"
        chmod +x "$yay_bin"
        chown "$USERNAME:$USERNAME" "$yay_bin"
        echo "  ✓ yay installed to $yay_bin"
    else
        echo "  ✓ yay already in user home"
    fi
}

install_yay_to_user

mkdir -p /etc/mados
cat > /etc/mados/ventoy-persist.conf << EOFVENTOY
# madOS Persistence Configuration
# Read by persistence detection at boot

# Preferred persistence size in MB (used as reference for Ventoy .dat files)
VENTOY_PERSIST_SIZE_MB=$VENTOY_PERSIST_SIZE

# Minimum free space required on USB in MB
MIN_FREE_SPACE_MB=512
EOFVENTOY
chmod 644 /etc/mados/ventoy-persist.conf

rm -f /root/.automated_script.sh /root/.zlogin

mkdir -p /etc/systemd/system
cat > /etc/systemd/system/rkhunter-init.service <<'EOFRKHUNTERINIT'
[Unit]
Description=Rkhunter Initial Database Update
After=network-online.target
Requires=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/rkhunter --update --propupd
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOFRKHUNTERINIT

cat > /etc/systemd/system/rkhunter.service <<'EOFRKHUNTER'
[Unit]
Description=Rkhunter Daily Scan
After=network-online.target
Requires=rkhunter-init.service

[Service]
Type=oneshot
ExecStart=/usr/bin/rkhunter --check --sk
StandardOutput=journal
StandardError=journal
EOFRKHUNTER

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

echo "Verifying graphical environment components..."
GRAPHICAL_OK=1
for bin in lightdm lightdm-gtk-greeter sway; do
    if command -v "$bin" &>/dev/null; then
        echo "  ✓ $bin found: $(command -v "$bin")"
    else
        echo "  ✗ $bin NOT found — graphical login may fail"
        GRAPHICAL_OK=0
    fi
done

for script in /usr/local/bin/sway-session /usr/local/bin/hyprland-session /usr/local/bin/start-hyprland /usr/local/bin/select-compositor; do
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

if [ -f /etc/lightdm/lightdm.conf ]; then
    echo "  ✓ lightdm config exists"
else
    echo "  ✗ lightdm config NOT found — graphical login may fail"
    GRAPHICAL_OK=0
fi

for session_file in /usr/share/wayland-sessions/sway.desktop /usr/share/wayland-sessions/hyprland.desktop; do
    if [ -f "$session_file" ]; then
        if grep -q "/usr/local/bin/" "$session_file"; then
            echo "  ✓ $session_file has madOS session script"
        else
            echo "  ⚠ $session_file exists but Exec= may not point to madOS script — fixing..."
            session_name=$(basename "$session_file" .desktop)
            if [ -x "/usr/local/bin/${session_name}-session" ]; then
                sed -i "s|^Exec=.*|Exec=/usr/local/bin/${session_name}-session|" "$session_file"
                echo "    Fixed: Exec=/usr/local/bin/${session_name}-session"
            fi
        fi
    else
        echo "  ✗ $session_file NOT found — session may not appear in greeter"
    fi
done

if systemctl is-enabled lightdm.service &>/dev/null; then
    echo "  ✓ lightdm.service is enabled"
else
    echo "  ✗ lightdm.service is NOT enabled — enabling..."
    systemctl enable lightdm.service 2>/dev/null || true
fi

systemctl enable getty@tty2.service 2>/dev/null || true

if command -v ufw &>/dev/null; then
    echo "Configuring UFW firewall..."
    ufw --force enable 2>/dev/null || true
    ufw default deny incoming 2>/dev/null || true
    ufw default allow outgoing 2>/dev/null || true
    ufw reload 2>/dev/null || true
    echo "  ✓ UFW enabled"
fi

if [ "$GRAPHICAL_OK" -eq 0 ]; then
    echo "  ⚠ Some graphical components are missing. Enabling getty@tty1 as fallback..."
    systemctl enable getty@tty1.service 2>/dev/null || true
fi
