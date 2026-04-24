#!/usr/bin/env python3
"""Regression tests for kernel fallback support in installer scripts."""

import os
import unittest


class TestKernelFallbacks(unittest.TestCase):
    """Ensure installer supports linux-lts-first kernel detection."""

    @classmethod
    def setUpClass(cls):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "installer", "steps.py"), "r") as f:
            cls.steps = f.read()
        with open(os.path.join(root, "scripts", "configure-grub.sh"), "r") as f:
            cls.configure_grub = f.read()
        with open(os.path.join(root, "scripts", "rebuild-initramfs.sh"), "r") as f:
            cls.rebuild_initramfs = f.read()
        with open(os.path.join(root, "scripts", "setup-bootloader.sh"), "r") as f:
            cls.setup_bootloader = f.read()
        with open(os.path.join(root, "scripts", "configure-limine.sh"), "r") as f:
            cls.configure_limine = f.read()

    def test_steps_supports_generic_kernel_detection(self):
        self.assertIn('"linux-lts"', self.steps)
        self.assertIn('"linux-mados"', self.steps)
        self.assertIn('"linux"', self.steps)
        self.assertIn('"linux-zen"', self.steps)
        self.assertIn("supported kernel not found", self.steps)
        self.assertNotIn("madOS kernel not found", self.steps)

    def test_configure_grub_supports_kernel_candidates(self):
        self.assertIn("for candidate in linux-lts linux-mados linux linux-zen", self.configure_grub)
        self.assertIn("No supported kernel found in /boot", self.configure_grub)
        self.assertIn("vmlinuz-${KERNEL}", self.configure_grub)
        self.assertNotIn("No madOS kernel found in /boot", self.configure_grub)

    def test_rebuild_initramfs_supports_kernel_candidates(self):
        self.assertIn("for candidate in linux-lts linux-mados linux linux-zen", self.rebuild_initramfs)
        self.assertIn("KERNEL=\"linux-lts\"", self.rebuild_initramfs)
        self.assertIn("No matching kernel modules found", self.rebuild_initramfs)

    def test_setup_bootloader_accepts_any_supported_kernel(self):
        self.assertIn("/boot/vmlinuz-linux-lts", self.setup_bootloader)
        self.assertIn("/boot/vmlinuz-linux-mados", self.setup_bootloader)
        self.assertIn("/boot/vmlinuz-linux", self.setup_bootloader)
        self.assertIn("/boot/vmlinuz-linux-zen", self.setup_bootloader)
        self.assertIn("Required kernel artifact missing", self.setup_bootloader)

    def test_configure_limine_uses_dynamic_kernel_selection(self):
        self.assertIn("KERNEL_NAME=\"\"", self.configure_limine)
        self.assertIn("for candidate in linux-lts linux-mados linux linux-zen", self.configure_limine)
        self.assertIn("/vmlinuz-${KERNEL_NAME}", self.configure_limine)
        self.assertIn("/initramfs-${KERNEL_NAME}.img", self.configure_limine)


if __name__ == "__main__":
    unittest.main()
