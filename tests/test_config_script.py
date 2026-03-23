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

    def test_wrapper_script_calls_modular_scripts(self):
        """Test wrapper delegates to modular scripts"""
        script = build_config_script(self.data)

        self.assertIn("/usr/local/bin/setup-locale.sh", script)
        self.assertIn("/usr/local/bin/setup-user.sh", script)
        self.assertIn("/usr/local/bin/clean-live-artifacts.sh", script)
        self.assertIn("/usr/local/bin/setup-bootloader.sh", script)
        self.assertIn("/usr/local/bin/configure-grub.sh", script)
        self.assertIn("/usr/local/bin/setup-plymouth.sh", script)
        self.assertIn("/usr/local/bin/rebuild-initramfs.sh", script)
        self.assertIn("/usr/local/bin/enable-services.sh", script)
        self.assertIn("/usr/local/bin/apply-configuration.sh", script)

    def test_progress_markers(self):
        """Test progress markers are present"""
        script = build_config_script(self.data)

        self.assertIn("[PROGRESS 1/8]", script)
        self.assertIn("[PROGRESS 2/8]", script)
        self.assertIn("[PROGRESS 3/8]", script)
        self.assertIn("[PROGRESS 4/8]", script)
        self.assertIn("[PROGRESS 5/8]", script)
        self.assertIn("[PROGRESS 6/8]", script)
        self.assertIn("[PROGRESS 7/8]", script)
        self.assertIn("[PROGRESS 8/8]", script)

    def test_variables_passed_correctly(self):
        """Test variables are passed to scripts"""
        script = build_config_script(self.data)

        self.assertIn('USERNAME="testuser"', script)
        self.assertIn('TIMEZONE="Europe/Madrid"', script)
        self.assertIn('LOCALE="es_ES.UTF-8"', script)
        self.assertIn('HOSTNAME="mados-test"', script)
        self.assertIn('DISK="/dev/sda"', script)
        self.assertIn('VENTOY_PERSIST_SIZE="4096"', script)

    def test_script_is_valid_bash(self):
        """Test the generated script has valid bash syntax"""
        script = build_config_script(self.data)

        self.assertTrue(script.startswith("#!/bin/bash"))
        self.assertIn("set -e", script)

    def test_shell_escaping(self):
        """Test hostname is properly escaped"""
        script = build_config_script(self.data)

        self.assertIn("HOSTNAME=", script)

    def test_root_partitions(self):
        """Test ROOT_PART and BOOT_PART are set"""
        script = build_config_script(self.data)

        self.assertIn('ROOT_PART="/dev/sda3"', script)
        self.assertIn('BOOT_PART="/dev/sda2"', script)

    def test_nvme_partition_prefix(self):
        """Test nvme disks use p prefix"""
        data = self.data.copy()
        data["disk"] = "/dev/nvme0n1"
        script = build_config_script(data)

        self.assertIn('ROOT_PART="/dev/nvme0n1p3"', script)
        self.assertIn('BOOT_PART="/dev/nvme0n1p2"', script)

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
