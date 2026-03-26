#!/usr/bin/env python3
"""Tests for log-summary.py"""

import unittest
import subprocess
import os

SCRIPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scripts",
    "log-summary.py",
)


class TestLogSummaryScript(unittest.TestCase):
    """Test log-summary.py script functionality"""

    def test_script_runs_without_error(self):
        """Test that the script runs without errors"""
        result = subprocess.run(
            ["python3", SCRIPT_PATH, "/nonexistent/path"],
            capture_output=True,
            text=True,
        )
        self.assertIn("Error:", result.stderr)

    def test_script_accepts_help(self):
        """Test that script shows usage with no args or help"""
        result = subprocess.run(
            ["python3", SCRIPT_PATH], capture_output=True, text=True
        )
        self.assertIn("Usage:", result.stdout)

    def test_script_produces_base64_output(self):
        """Test that script produces base64-like output"""
        test_log = "/tmp/test-mados-install.log"
        with open(test_log, "w") as f:
            f.write("""
[PROGRESS 1/8] Starting installation
[ERROR] Something failed
  WARNING: Low disk space
[OK] Installation completed
""")
        try:
            result = subprocess.run(
                ["python3", SCRIPT_PATH, test_log], capture_output=True, text=True
            )
            lines = result.stdout.strip().split("\n")
            compressed_line = [
                l
                for l in lines
                if not l.startswith("Compressed")
                and not l.startswith("Decoder")
                and not l.startswith("QR API")
            ][0]
            self.assertGreater(len(compressed_line), 50)
            self.assertTrue(
                compressed_line.replace("+", "")
                .replace("/", "")
                .replace("=", "")
                .isalnum()
                or compressed_line.endswith("[TRUNCATED]")
            )
        finally:
            os.unlink(test_log)

    def test_script_includes_urls(self):
        """Test that script outputs decoder and QR URLs"""
        test_log = "/tmp/test-mados-install.log"
        with open(test_log, "w") as f:
            f.write("[PROGRESS 1/8] Test\n[OK] Done\n")
        try:
            result = subprocess.run(
                ["python3", SCRIPT_PATH, test_log], capture_output=True, text=True
            )
            self.assertIn("Decoder URL:", result.stdout)
            self.assertIn("QR API URL:", result.stdout)
            self.assertIn("madoslinux.github.io", result.stdout)
        finally:
            os.unlink(test_log)

    def test_script_counts_stats(self):
        """Test that script reports statistics"""
        test_log = "/tmp/test-mados-install.log"
        with open(test_log, "w") as f:
            f.write("""
[PROGRESS 1/8] Step 1
[PROGRESS 2/8] Step 2
[ERROR] Failed
  WARNING: Warning 1
  WARNING: Warning 2
[OK] Success 1
[OK] Success 2
""")
        try:
            result = subprocess.run(
                ["python3", SCRIPT_PATH, test_log], capture_output=True, text=True
            )
            self.assertIn("2 steps", result.stdout)
            self.assertIn("1 errors", result.stdout)
            self.assertIn("2 warnings", result.stdout)
            self.assertIn("2 ok", result.stdout)
        finally:
            os.unlink(test_log)


if __name__ == "__main__":
    unittest.main()
