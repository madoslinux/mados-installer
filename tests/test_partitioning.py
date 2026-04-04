#!/usr/bin/env python3
"""Tests for partitioning functions and installation data validation"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPartitionPrefix(unittest.TestCase):
    """Tests for _get_partition_prefix function"""

    def test_sata_disk(self):
        """Test SATA disk returns full path without p suffix"""
        from installer.config_script import _get_partition_prefix

        self.assertEqual(_get_partition_prefix("/dev/sda"), "/dev/sda")
        self.assertEqual(_get_partition_prefix("/dev/sdb"), "/dev/sdb")

    def test_nvme_disk(self):
        """Test NVMe disk returns full path with p suffix"""
        from installer.config_script import _get_partition_prefix

        self.assertEqual(_get_partition_prefix("/dev/nvme0n1"), "/dev/nvme0n1p")
        self.assertEqual(_get_partition_prefix("/dev/nvme1n1"), "/dev/nvme1n1p")

    def test_mmcblk_disk(self):
        """Test MMC/SD disk returns full path with p suffix"""
        from installer.config_script import _get_partition_prefix

        self.assertEqual(_get_partition_prefix("/dev/mmcblk0"), "/dev/mmcblk0p")
        self.assertEqual(_get_partition_prefix("/dev/mmcblk1"), "/dev/mmcblk1p")

    def test_none_disk(self):
        """Test None disk returns empty string"""
        from installer.config_script import _get_partition_prefix

        self.assertEqual(_get_partition_prefix(None), "")

    def test_empty_string_disk(self):
        """Test empty string disk returns empty string"""
        from installer.config_script import _get_partition_prefix

        self.assertEqual(_get_partition_prefix(""), "")


class TestCommandVerification(unittest.TestCase):
    """Tests for command verification"""

    def test_command_exists_function(self):
        """Test _command_exists detects available commands"""
        from installer.steps import _command_exists

        self.assertTrue(_command_exists("ls"))
        self.assertTrue(_command_exists("cat"))
        self.assertTrue(_command_exists("echo"))

    def test_command_not_exists(self):
        """Test _command_exists returns False for nonexistent commands"""
        from installer.steps import _command_exists

        self.assertFalse(_command_exists("nonexistent_command_12345"))


class TestInstallDataDefaults(unittest.TestCase):
    """Tests for install_data default values"""

    def test_install_data_defaults(self):
        """Test that config constants are properly defined"""
        from config import DEMO_MODE, LOCALE_MAP, MIN_DISK_SIZE_GB, TIMEZONES

        self.assertIsInstance(DEMO_MODE, bool)
        self.assertIsInstance(MIN_DISK_SIZE_GB, int)
        self.assertGreater(MIN_DISK_SIZE_GB, 0)
        self.assertIsInstance(TIMEZONES, list)
        self.assertGreater(len(TIMEZONES), 0)
        self.assertIsInstance(LOCALE_MAP, dict)
        self.assertGreater(len(LOCALE_MAP), 0)


class TestTimezoneValidation(unittest.TestCase):
    """Tests for timezone validation"""

    def test_valid_timezones(self):
        """Test that common timezones are in TIMEZONES list"""
        from config import TIMEZONES

        common_timezones = ["UTC", "Europe/Madrid", "Europe/London", "America/New_York"]
        for tz in common_timezones:
            self.assertIn(tz, TIMEZONES, f"{tz} should be in TIMEZONES")

    def test_invalid_timezone_rejected(self):
        """Test that invalid timezone raises ValueError"""
        from installer.config_script import build_config_script

        data = {
            "disk": "/dev/sda",
            "locale": "en_US.UTF-8",
            "hostname": "test",
            "username": "testuser",
            "password": "test123",
            "timezone": "Invalid/Zone",
            "ventoy_persist_size": 4096,
        }
        with self.assertRaises(ValueError):
            build_config_script(data)


class TestUsernameValidation(unittest.TestCase):
    """Tests for username validation"""

    def test_valid_usernames(self):
        """Test that valid usernames are accepted"""
        from installer.config_script import build_config_script

        valid_names = ["testuser", "admin", "user_name", "user-name", "a"]
        for name in valid_names:
            data = {
                "disk": "/dev/sda",
                "locale": "en_US.UTF-8",
                "hostname": "test",
                "username": name,
                "password": "test123",
                "timezone": "UTC",
                "ventoy_persist_size": 4096,
            }
            try:
                build_config_script(data)
            except ValueError:
                self.fail(f"Username '{name}' should be valid")

    def test_invalid_usernames(self):
        """Test that invalid usernames are rejected"""
        from installer.config_script import build_config_script

        invalid_names = ["123user", "User", "user name", "user@name", "-invalid"]
        for name in invalid_names:
            data = {
                "disk": "/dev/sda",
                "locale": "en_US.UTF-8",
                "hostname": "test",
                "username": name,
                "password": "test123",
                "timezone": "UTC",
                "ventoy_persist_size": 4096,
            }
            with self.assertRaises(
                ValueError, msg=f"Username '{name}' should be invalid"
            ):
                build_config_script(data)


if __name__ == "__main__":
    unittest.main()
