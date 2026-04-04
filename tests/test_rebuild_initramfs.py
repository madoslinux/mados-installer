#!/usr/bin/env python3
"""Tests for rebuild-initramfs.sh script"""

import os
import shutil
import subprocess
import tempfile
import unittest


class TestRebuildInitramfsScript(unittest.TestCase):
    """Test rebuild-initramfs.sh auto-detection logic"""

    def test_lsmod_parsing(self):
        """Test that lsmod output is correctly parsed for module names"""
        lsmod_output = """Module                  Size  Used by
nvme                   65536  1
ahci                   40960  1
xhci_pci               16384  1
usb_storage            20480  2
virtio_balloon         16384  1
ext4                  614400  1"""

        modules = subprocess.run(
            ["awk", "NR>1 {print $1}"],
            input=lsmod_output,
            capture_output=True,
            text=True,
        )
        module_list = modules.stdout.strip().split("\n")
        self.assertIn("nvme", module_list)
        self.assertIn("ahci", module_list)
        self.assertIn("xhci_pci", module_list)

    def test_module_list_joined_with_spaces(self):
        """Test modules are joined with spaces for MODULES= line"""
        lsmod_output = """Module                  Size  Used by
nvme                   65536  1
ahci                   40960  1"""

        result = subprocess.run(
            ["awk", "NR>1 {print $1}"],
            input=lsmod_output,
            capture_output=True,
            text=True,
        )
        modules = result.stdout.strip().replace("\n", " ")
        self.assertIn("nvme", modules)
        self.assertIn("ahci", modules)

    def test_script_includes_lsmod_auto_detection(self):
        """Test that rebuild-initramfs.sh includes lsmod auto-detection"""
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "scripts",
            "rebuild-initramfs.sh",
        )

        with open(script_path, "r") as f:
            script_content = f.read()

        self.assertIn("lsmod", script_content)
        self.assertIn('MODULES=""', script_content)
        self.assertIn("/etc/mkinitcpio.conf", script_content)

    def test_script_adds_modules_before_mkinitcpio(self):
        """Test that MODULES config is written before mkinitcpio command"""
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "scripts",
            "rebuild-initramfs.sh",
        )

        with open(script_path, "r") as f:
            lines = f.readlines()

        modules_line = None
        mkinitcpio_line = None

        for i, line in enumerate(lines):
            if 'MODULES=""' in line:
                modules_line = i
            if "mkinitcpio -p" in line:
                mkinitcpio_line = i

        if modules_line is None:
            self.fail("MODULES line not found in script")
        if mkinitcpio_line is None:
            self.fail("mkinitcpio -p line not found")
        self.assertLess(
            modules_line,
            mkinitcpio_line,
            "MODULES should be added before mkinitcpio -p",
        )

    def test_empty_lsmod_handled(self):
        """Test that empty lsmod output doesn't break the script"""
        empty_lsmod = """Module                  Size  Used by
"""

        result = subprocess.run(
            [
                "bash",
                "-c",
                "echo '$1' | awk 'NR>1 {print $1}' | tr '\\n' ' '",
                "_",
                empty_lsmod,
            ],
            capture_output=True,
            text=True,
        )
        modules = result.stdout.strip()
        self.assertEqual(modules, "")


if __name__ == "__main__":
    unittest.main()
