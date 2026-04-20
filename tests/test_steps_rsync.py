#!/usr/bin/env python3
"""Regression tests for rsync behavior in installer steps."""

import os
import unittest


class TestStepsRsync(unittest.TestCase):
    """Validate rsync fallback logic for metadata-incompatible targets."""

    @classmethod
    def setUpClass(cls):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.steps_path = os.path.join(root, "installer", "steps.py")
        with open(cls.steps_path) as f:
            cls.steps = f.read()

    def test_has_rsync_metadata_fallback(self):
        """Installer should retry rsync without ACL/xattr on code 23."""
        self.assertIn("if proc.returncode == 23:", self.steps)
        self.assertIn("retrying without ACL/xattr", self.steps)
        self.assertIn('"-aHWS"', self.steps)
        self.assertNotIn('"-aAXHWS"', self.steps.split("retry_cmd =", 1)[1])

    def test_has_btrfs_mount_retry_helper(self):
        """Installer should retry Btrfs mounts before creating subvolumes."""
        self.assertIn("def _mount_btrfs_with_retry(", self.steps)
        self.assertIn('"mount", "-t", "btrfs", root_part, mount_point', self.steps)
        self.assertIn("for attempt in range(1, retries + 1):", self.steps)

    def test_subvolume_step_uses_mount_retry_helper(self):
        """Subvolume creation should call the mount retry helper."""
        section = self.steps.split("def step_create_btrfs_subvolumes", 1)[1]
        self.assertIn("_mount_btrfs_with_retry(app, root_part, mount_point)", section)
        self.assertIn(
            "except (subprocess.CalledProcessError, RuntimeError) as e:", section
        )


if __name__ == "__main__":
    unittest.main()
