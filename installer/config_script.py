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
    if disk is None:
        return ""
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

# madOS Installer - System Configuration Wrapper
# This wrapper delegates to the modular scripts in /usr/local/bin/

USERNAME="{username}"
PASSWORD="{_escape_shell(data["password"])}"
TIMEZONE="{timezone}"
LOCALE="{locale}"
HOSTNAME="{_escape_shell(data["hostname"])}"
DISK="{disk}"
ROOT_PART="{root_part}"
BOOT_PART="{boot_part}"
VENTOY_PERSIST_SIZE="{data.get("ventoy_persist_size", 4096)}"

echo "[PROGRESS 1/8] Setting timezone and locale..."
/usr/local/bin/setup-locale.sh "$TIMEZONE" "$LOCALE"

echo "[PROGRESS 2/8] Creating user account..."
/usr/local/bin/setup-user.sh "$USERNAME" "$HOSTNAME" "$PASSWORD"

echo "  Cleaning live ISO artifacts..."
/usr/local/bin/clean-live-artifacts.sh

echo "[PROGRESS 3/8] Installing Limine bootloader..."
/usr/local/bin/setup-limine.sh "$DISK"

echo "[PROGRESS 4/8] Configuring Limine..."
/usr/local/bin/configure-limine.sh "$ROOT_PART"

echo "[PROGRESS 5/8] Setting up Plymouth boot splash..."
/usr/local/bin/setup-plymouth.sh

echo "[PROGRESS 6/8] Rebuilding initramfs..."
/usr/local/bin/rebuild-initramfs.sh

echo "[PROGRESS 7/8] Enabling essential services..."
/usr/local/bin/enable-services.sh

echo "[PROGRESS 8/8] Applying final configuration..."
/usr/local/bin/apply-configuration.sh "$USERNAME" "$LOCALE" "$VENTOY_PERSIST_SIZE"

echo "System configuration complete."
'''


def write_config_script(data, path="/mnt/root/configure.sh"):
    """Write the configuration script to a file."""
    import os

    script_content = build_config_script(data)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o700)
    with os.fdopen(fd, "w") as f:
        f.write(script_content)
