#!/usr/bin/env python3
"""Tests for config_script.py"""

import unittest
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from installer.config_script import build_config_script


class TestConfigScript(unittest.TestCase):
    def setUp(self):
        self.data = {
            "disk": "/dev/sda",
            "locale": "es_ES.UTF-8",
            "hostname": "mados-test",
            "username": "testuser",
            "password": "testpass123",
            "timezone": "Europe/Madrid",
            "ventoy_persist_size": 4096,
        }

    def test_basic_replacements(self):
        """Test basic variable replacements work"""
        script = build_config_script(self.data)
        
        self.assertIn("/usr/share/zoneinfo/Europe/Madrid", script)
        self.assertIn("es_ES.UTF-8 UTF-8", script)
        self.assertIn('LANG=es_ES.UTF-8', script)
        self.assertIn("mados-test.localdomain mados-test", script)
        self.assertIn("useradd -m -G wheel,audio,video,storage -s /usr/bin/zsh testuser", script)
        self.assertIn("echo 'testuser:testpass123' | chpasswd", script)
        self.assertIn("VENTOY_PERSIST_SIZE_MB=4096", script)

    def test_shell_variables_not_evaluated(self):
        """Test that shell variables like ${kdir} are preserved"""
        script = build_config_script(self.data)
        
        self.assertIn("${kdir}vmlinuz", script)
        self.assertIn("${session_name}", script)

    def test_grub_disk_variable(self):
        """Test $disk is properly used in BIOS mode grub-install"""
        script = build_config_script(self.data)
        
        # In BIOS mode, the disk should be extracted from the path
        self.assertIn('BASE_DISK=$(echo "$disk" | sed \'s/[0-9]*$//\')', script)
        self.assertIn("--recheck \"$BASE_DISK\"", script)
        self.assertNotIn("{disk}", script)

    def test_bash_blocks_properly_escaped(self):
        """Test bash blocks like { echo; } are double-braced"""
        script = build_config_script(self.data)
        
        self.assertIn("{ echo 'FATAL:", script)

    def test_find_command_braces(self):
        """Test find command {} is properly escaped"""
        script = build_config_script(self.data)
        
        self.assertIn("test -e {}", script)

    def test_no_python_placeholders(self):
        """Test no unescaped Python f-string placeholders remain"""
        script = build_config_script(self.data)
        
        # Check common patterns that would indicate broken placeholders
        self.assertNotIn("${{", script)  # Double dollar should not appear
        self.assertNotIn("{{{{", script)  # Quad braces would indicate over-escaping

    def test_script_is_valid_bash(self):
        """Test the generated script has valid bash syntax"""
        script = build_config_script(self.data)
        
        # Script should start with shebang
        self.assertTrue(script.startswith("#!/bin/bash"))
        
        # Check all required sections exist
        self.assertIn("[PROGRESS 1/8]", script)
        self.assertIn("[PROGRESS 2/8]", script)
        self.assertIn("[PROGRESS 3/8]", script)
        self.assertIn("[PROGRESS 4/8]", script)
        self.assertIn("[PROGRESS 5/8]", script)
        self.assertIn("[PROGRESS 6/8]", script)
        self.assertIn("[PROGRESS 7/8]", script)
        self.assertIn("[PROGRESS 8/8]", script)

    def test_locale_kb_map(self):
        """Test keyboard layout from locale is used"""
        script = build_config_script(self.data)
        
        # es_ES should use 'es' keyboard layout
        self.assertIn('KB_LAYOUT="es"', script)

    def test_locale_kb_map_en(self):
        """Test en_US locale maps to us keyboard"""
        data = self.data.copy()
        data["locale"] = "en_US.UTF-8"
        script = build_config_script(data)
        
        self.assertIn('KB_LAYOUT="us"', script)

    def test_sudoers_config(self):
        """Test sudoers configuration is correct"""
        script = build_config_script(self.data)
        
        self.assertIn("%wheel ALL=(ALL:ALL) ALL", script)
        self.assertIn("testuser ALL=(ALL:ALL) NOPASSWD:", script)
        self.assertIn("/usr/local/bin/opencode", script)
        self.assertIn("/usr/local/bin/ollama", script)

    def test_grub_config(self):
        """Test GRUB configuration is correct"""
        script = build_config_script(self.data)
        
        self.assertIn('GRUB_CMDLINE_LINUX="zswap.enabled=0 splash quiet"', script)
        self.assertIn('GRUB_DISTRIBUTOR="madOS"', script)
        self.assertIn("GRUB_DISABLE_OS_PROBER=false", script)

    def test_grub_uses_uuid(self):
        """Test GRUB uses UUID from dynamic root partition"""
        script = build_config_script(self.data)
        
        self.assertIn("GRUB_DISABLE_LINUX_UUID=false", script)
        # Should use dynamic partition based on disk (sda3 for /dev/sda)
        self.assertIn("blkid -s UUID -o value /dev/sda3", script)
        self.assertIn("root=UUID=$ROOT_UUID", script)

    def test_networkmanager_config(self):
        """Test NetworkManager iwd backend is configured"""
        script = build_config_script(self.data)
        
        self.assertIn("wifi.backend=iwd", script)

    def test_os_release(self):
        """Test os-release contains madOS branding"""
        script = build_config_script(self.data)
        
        self.assertIn('NAME="madOS"', script)
        self.assertIn('ID=mados', script)
        self.assertIn('ID_LIKE=arch', script)

    def test_sysctl_config(self):
        """Test kernel optimizations are configured"""
        script = build_config_script(self.data)
        
        self.assertIn("vm.swappiness = 5", script)
        self.assertIn("vm.min_free_kbytes = 16384", script)
        self.assertIn("net.ipv4.tcp_fin_timeout = 15", script)

    def test_zram_config(self):
        """Test ZRAM configuration"""
        script = build_config_script(self.data)
        
        self.assertIn("zram-size = ram / 2", script)
        self.assertIn("compression-algorithm = zstd", script)

    def test_greetd_config(self):
        """Test greetd is configured"""
        script = build_config_script(self.data)
        
        self.assertIn('command = "/usr/local/bin/cage-greeter"', script)
        self.assertIn("path = \"/usr/share/backgrounds/mad-os-wallpaper.png\"", script)
        self.assertIn('application_prefer_dark_theme = true', script)

    def test_services_enabled(self):
        """Test essential services are enabled"""
        script = build_config_script(self.data)
        
        self.assertIn("systemctl enable NetworkManager", script)
        self.assertIn("systemctl enable greetd", script)
        self.assertIn("systemctl enable bluetooth", script)
        self.assertIn("systemctl enable iwd", script)

    def test_mkinitcpio_cleanup(self):
        """Test archiso config is removed and initramfs is rebuilt"""
        script = build_config_script(self.data)
        
        self.assertIn("pacman -Rdd --noconfirm mkinitcpio-archiso", script)
        self.assertIn("rm -f /etc/mkinitcpio.conf.d/*.conf", script)
        self.assertIn("rm -f /etc/mkinitcpio.d/*", script)
        self.assertIn("mkinitcpio -p linux", script)

    def test_root_locked(self):
        """Test root account is locked"""
        script = build_config_script(self.data)
        
        self.assertIn("passwd -l root", script)

    def test_user_groups(self):
        """Test user is added to correct groups"""
        script = build_config_script(self.data)
        
        self.assertIn("useradd -m -G wheel,audio,video,storage", script)

    def test_pacman_hooks(self):
        """Test pacman hooks exist for sway/hyprland"""
        script = build_config_script(self.data)
        
        self.assertIn("sway-desktop-override.hook", script)
        self.assertIn("hyprland-desktop-override.hook", script)
        self.assertIn("sway-session", script)
        self.assertIn("hyprland-session", script)

    def test_live_iso_cleanup(self):
        """Test live ISO services are disabled"""
        script = build_config_script(self.data)
        
        self.assertIn("systemctl disable", script)
        self.assertIn("livecd-talk.service", script)
        self.assertIn("mados-installer-autostart.service", script)

    def test_mados_user_removed(self):
        """Test mados live user is removed"""
        script = build_config_script(self.data)
        
        self.assertIn("userdel -r mados", script)
        self.assertIn("rm -rf /home/mados", script)

    def test_invalid_disk_path(self):
        """Test invalid disk path raises error"""
        data = self.data.copy()
        data["disk"] = "/dev/sda invalid"
        
        with self.assertRaises(ValueError):
            build_config_script(data)

    def test_invalid_username(self):
        """Test invalid username raises error"""
        data = self.data.copy()
        data["username"] = "123invalid"
        
        with self.assertRaises(ValueError):
            build_config_script(data)

    def test_invalid_username_uppercase(self):
        """Test username with uppercase raises error"""
        data = self.data.copy()
        data["username"] = "InvalidUser"
        
        with self.assertRaises(ValueError):
            build_config_script(data)

    def test_invalid_timezone(self):
        """Test invalid timezone raises error"""
        data = self.data.copy()
        data["timezone"] = "Invalid/Zone"
        
        with self.assertRaises(ValueError):
            build_config_script(data)


if __name__ == "__main__":
    unittest.main()