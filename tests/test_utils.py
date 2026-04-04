#!/usr/bin/env python3
"""Tests for utility functions"""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import random_suffix


class TestRandomSuffix(unittest.TestCase):
    """Tests for random_suffix function"""

    def test_default_length(self):
        """Test default length is 4"""
        suffix = random_suffix()
        self.assertEqual(len(suffix), 4)

    def test_custom_length(self):
        """Test custom length works"""
        for length in [3, 6, 8, 12]:
            suffix = random_suffix(length)
            self.assertEqual(len(suffix), length)

    def test_alphanumeric_only(self):
        """Test suffix contains only lowercase letters and digits"""
        import string

        suffix = random_suffix(100)
        allowed = set(string.ascii_lowercase + string.digits)
        self.assertTrue(all(c in allowed for c in suffix))

    def test_different_each_time(self):
        """Test that multiple calls produce different suffixes"""
        suffixes = [random_suffix() for _ in range(100)]
        self.assertEqual(len(suffixes), len(set(suffixes)))


class TestEscapeShell(unittest.TestCase):
    """Tests for _escape_shell function"""

    def test_plain_string(self):
        """Test string without special chars passes through"""
        from installer.config_script import _escape_shell

        self.assertEqual(_escape_shell("hello"), "hello")

    def test_single_quotes(self):
        """Test single quotes are properly escaped"""
        from installer.config_script import _escape_shell

        self.assertEqual(_escape_shell("user's"), "user'\\''s")

    def test_empty_string(self):
        """Test empty string returns empty"""
        from installer.config_script import _escape_shell

        self.assertEqual(_escape_shell(""), "")


class TestWriteConfigScript(unittest.TestCase):
    """Tests for write_config_script function"""

    def test_write_config_script(self):
        """Test that script is written correctly"""
        from installer.config_script import write_config_script

        data = {
            "disk": "/dev/sda",
            "locale": "en_US.UTF-8",
            "hostname": "test-host",
            "username": "testuser",
            "password": "testpass",
            "timezone": "UTC",
            "ventoy_persist_size": 4096,
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            temp_path = f.name

        try:
            write_config_script(data, temp_path)
            self.assertTrue(os.path.exists(temp_path))
            with open(temp_path, "r") as f:
                content = f.read()
            self.assertTrue(content.startswith("#!/bin/bash"))
            self.assertIn("testuser", content)
            self.assertIn("test-host", content)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestDiskTypeDetection(unittest.TestCase):
    """Tests for disk type detection"""

    def test_sata_disk(self):
        """Test SATA disk type returns HDD"""
        from pages.disk import _get_disk_type

        dtype = _get_disk_type("sda", "")
        self.assertEqual(dtype, "HDD")

    def test_nvme_disk(self):
        """Test NVMe disk type returns NVMe"""
        from pages.disk import _get_disk_type

        dtype = _get_disk_type("nvme0n1", "")
        self.assertEqual(dtype, "NVMe")

    def test_mmc_disk(self):
        """Test MMC disk type returns HDD (current behavior)"""
        from pages.disk import _get_disk_type

        dtype = _get_disk_type("mmcblk0", "")
        self.assertEqual(dtype, "HDD")

    def test_ssd_in_model(self):
        """Test SSD detection from model string"""
        from pages.disk import _get_disk_type

        dtype = _get_disk_type("sda", "Samsung SSD")
        self.assertEqual(dtype, "SSD")

    def test_hdd_in_model(self):
        """Test HDD detection when no SSD indicators"""
        from pages.disk import _get_disk_type

        dtype = _get_disk_type("sda", "Seagate Barracuda")
        self.assertEqual(dtype, "HDD")


class TestCopyItem(unittest.TestCase):
    """Tests for _copy_item function"""

    def test_copy_item_nonexistent_source(self):
        """Test copying nonexistent file does not raise"""
        from installer.steps import _copy_item

        _copy_item("/nonexistent/file", "/tmp/dest")

    def test_copy_item_file(self):
        """Test copying a file works"""
        from installer.steps import _copy_item

        src_dir = tempfile.mkdtemp()
        dest_dir = tempfile.mkdtemp()
        src_file = os.path.join(src_dir, "test.txt")

        with open(src_file, "w") as f:
            f.write("test content")

        try:
            _copy_item(src_file, dest_dir)
            result_file = os.path.join(dest_dir, "test.txt")
            self.assertTrue(os.path.exists(result_file))
            with open(result_file, "r") as f:
                self.assertEqual(f.read(), "test content")
        finally:
            shutil.rmtree(src_dir, ignore_errors=True)
            shutil.rmtree(dest_dir, ignore_errors=True)


class TestDiskList(unittest.TestCase):
    """Tests for disk listing"""

    def test_get_disk_list_returns_list(self):
        """Test that _get_disk_list returns a list"""
        from pages.disk import _get_disk_list

        disks = _get_disk_list()
        self.assertIsInstance(disks, list)

    def test_get_disk_list_items_are_tuples(self):
        """Test that disk items are tuples with 3 elements"""
        from pages.disk import _get_disk_list

        disks = _get_disk_list()
        for disk in disks:
            self.assertIsInstance(disk, tuple)
            self.assertEqual(len(disk), 3)

    def test_get_disk_list_items_have_name_size_model(self):
        """Test that disk tuples have name, size, model"""
        from pages.disk import _get_disk_list

        disks = _get_disk_list()
        for disk in disks:
            name, size, model = disk
            self.assertIsInstance(name, str)
            self.assertIsInstance(size, str)
            self.assertIsInstance(model, str)


if __name__ == "__main__":
    unittest.main()
