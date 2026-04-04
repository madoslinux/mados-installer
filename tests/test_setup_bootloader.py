#!/usr/bin/env python3
"""Tests for setup-bootloader.sh secure boot logic."""

import os
import unittest


class TestSetupBootloaderScript(unittest.TestCase):
    """Validate setup-bootloader.sh contains hardened secure boot flow."""

    @classmethod
    def setUpClass(cls):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.script_path = os.path.join(root, "scripts", "setup-bootloader.sh")
        with open(cls.script_path, "r") as f:
            cls.script = f.read()

    def test_script_is_bash_and_strict(self):
        """Script should remain strict bash with errexit."""
        self.assertTrue(self.script.startswith("#!/bin/bash"))
        self.assertIn("set -euo pipefail", self.script)

    def test_uefi_mount_validation_exists(self):
        """UEFI flow should validate ESP mount before installing GRUB."""
        self.assertIn("ensure_efi_mount()", self.script)
        self.assertIn("mountpoint -q /boot", self.script)
        self.assertIn("findmnt -n -o FSTYPE /boot", self.script)
        self.assertIn("/boot must be mounted as vfat for EFI", self.script)

    def test_secure_boot_setup_mode_flow_uses_sbctl(self):
        """Setup Mode flow should use sbctl enrollment path."""
        self.assertIn("setup_secure_boot_setup_mode()", self.script)
        self.assertIn("sbctl create-keys", self.script)
        self.assertIn("sbctl enroll-keys --microsoft", self.script)
        self.assertIn("sign_secure_boot_artifacts", self.script)

    def test_secure_boot_user_mode_flow_uses_shim_and_mok(self):
        """User Mode flow should prepare shim fallback and MOK enrollment."""
        self.assertIn("setup_secure_boot_shim_mok()", self.script)
        self.assertIn("require_cmd mokutil", self.script)
        self.assertIn("/boot/EFI/BOOT/grubx64.efi", self.script)
        self.assertIn("/boot/EFI/BOOT/MMX64.EFI", self.script)
        self.assertIn("mokutil --import", self.script)
        self.assertIn("/root/mok-password.txt", self.script)

    def test_boot_artifact_validation_exists(self):
        """Final validation should ensure boot artifacts exist."""
        self.assertIn("validate_boot_artifacts()", self.script)
        self.assertIn("/boot/EFI/BOOT/BOOTX64.EFI", self.script)
        self.assertIn("/boot/EFI/madOS/grubx64.efi", self.script)
        self.assertIn("/boot/vmlinuz-linux-mados", self.script)


if __name__ == "__main__":
    unittest.main()
