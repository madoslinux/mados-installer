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
        with open(cls.steps_path, "r") as f:
            cls.steps = f.read()

    def test_has_rsync_metadata_fallback(self):
        """Installer should retry rsync without ACL/xattr on code 23."""
        self.assertIn("if proc.returncode == 23:", self.steps)
        self.assertIn("retrying without ACL/xattr", self.steps)
        self.assertIn('"-aHWS"', self.steps)
        self.assertNotIn('"-aAXHWS"', self.steps.split("retry_cmd =", 1)[1])


if __name__ == "__main__":
    unittest.main()
