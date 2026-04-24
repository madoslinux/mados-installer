#!/usr/bin/env python3
"""Tests for configure-grub.sh hardening logic."""

import os
import unittest


class TestConfigureGrubScript(unittest.TestCase):
    """Validate configure-grub.sh has robust GRUB configuration flow."""

    @classmethod
    def setUpClass(cls):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.script_path = os.path.join(root, "scripts", "configure-grub.sh")
        with open(cls.script_path, "r") as f:
            cls.script = f.read()

    def test_script_is_strict_bash(self):
        """Script should keep strict bash mode."""
        self.assertTrue(self.script.startswith("#!/bin/bash"))
        self.assertIn("set -euo pipefail", self.script)

    def test_validates_root_partition_uuid(self):
        """Script should validate root partition and UUID."""
        self.assertIn('if [ ! -b "$ROOT_PART" ]; then', self.script)
        self.assertIn("ROOT_UUID=$($BLKID -s UUID -o value", self.script)
        self.assertIn("Could not detect UUID for root partition", self.script)

    def test_uses_idempotent_grub_key_updates(self):
        """Script should avoid duplicate appends in /etc/default/grub."""
        self.assertIn("set_grub_key()", self.script)
        self.assertIn("ensure_cmdline_token()", self.script)
        self.assertIn("sanitize_grub_cmdline_key()", self.script)
        self.assertIn("sanitize_generated_grub_cfg()", self.script)
        self.assertIn("assert_no_legacy_grub_tokens()", self.script)
        self.assertIn("remove_cmdline_token()", self.script)
        self.assertIn(
            "remove_cmdline_token 'rootflags=subvol=[^[:space:]]+'", self.script
        )
        self.assertIn("Drop malformed bare subvol= tokens", self.script)
        self.assertIn('set_grub_key "GRUB_DISTRIBUTOR"', self.script)
        self.assertIn('set_grub_key "GRUB_DISABLE_OS_PROBER"', self.script)
        self.assertIn(
            'set_grub_key "GRUB_CMDLINE_LINUX_DEFAULT" \'"quiet splash loglevel=3',
            self.script,
        )
        self.assertIn('set_grub_key "GRUB_GFXMODE" "auto"', self.script)
        self.assertIn('set_grub_key "GRUB_GFXPAYLOAD_LINUX" "keep"', self.script)
        self.assertIn('set_grub_key "GRUB_TERMINAL_OUTPUT" "gfxterm"', self.script)
        self.assertIn("rd.systemd.show_status=false", self.script)
        self.assertIn("systemd.show_status=false", self.script)
        self.assertIn("vt.global_cursor_default=0", self.script)
        self.assertIn('sanitize_grub_cmdline_key "GRUB_CMDLINE_LINUX"', self.script)
        self.assertIn(
            'sanitize_grub_cmdline_key "GRUB_CMDLINE_LINUX_DEFAULT"', self.script
        )
        self.assertNotIn('ensure_cmdline_token "rootflag=', self.script)
        self.assertNotIn('ensure_cmdline_token "rootflags=subvol=@"', self.script)
        self.assertNotIn('ensure_cmdline_token "splash"', self.script)
        self.assertNotIn('ensure_cmdline_token "quiet"', self.script)
        self.assertNotIn('ensure_cmdline_token "plymouth.use-simpledrm=0"', self.script)
        self.assertNotIn("ensure_btrfs_rootflags()", self.script)
        self.assertIn("assert_no_legacy_grub_tokens", self.script)

    def test_validates_generated_grub_cfg_contains_kernel(self):
        """Script should fail when grub.cfg misses selected kernel entry."""
        self.assertIn("$GRUB_MKCONFIG -o /boot/grub/grub.cfg", self.script)
        self.assertIn("sanitize_generated_grub_cfg", self.script)
        self.assertIn("for candidate in linux-lts linux-mados linux linux-zen", self.script)
        self.assertIn("grub.cfg does not contain vmlinuz-${KERNEL} entry", self.script)


if __name__ == "__main__":
    unittest.main()
