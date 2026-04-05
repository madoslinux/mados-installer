#!/usr/bin/env python3
"""Tests for fstab subvolume option normalization."""

import unittest


def _normalize_fstab(fstab_content: str) -> str:
    """Apply installer fstab normalization logic for Btrfs subvolumes."""
    lines = fstab_content.split("\n")
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue

        parts = line.split()
        if len(parts) < 4:
            new_lines.append(line)
            continue

        mount_point = parts[1]
        fs_type = parts[2]
        opts = parts[3].split(",") if parts[3] else []
        has_subvol = any(opt.startswith("subvol=") for opt in opts)

        if fs_type == "btrfs" and not has_subvol:
            if mount_point == "/":
                opts.append("subvol=@")
            elif mount_point == "/home":
                opts.append("subvol=@home")

        parts[3] = ",".join([opt for opt in opts if opt])
        new_lines.append(" ".join(parts))

    return "\n".join(new_lines) + "\n"


class TestFstabGeneration(unittest.TestCase):
    """Validate Btrfs subvolume options are always present."""

    def test_adds_subvol_options_for_uuid_entries(self):
        """Should add subvol options even when genfstab outputs UUID= lines."""
        input_fstab = (
            "UUID=1111 / btrfs rw,relatime 0 0\n"
            "UUID=1111 /home btrfs rw,relatime 0 0\n"
            "UUID=2222 /boot vfat rw,relatime 0 2\n"
        )
        output = _normalize_fstab(input_fstab)
        self.assertIn("UUID=1111 / btrfs rw,relatime,subvol=@ 0 0", output)
        self.assertIn("UUID=1111 /home btrfs rw,relatime,subvol=@home 0 0", output)
        self.assertIn("UUID=2222 /boot vfat rw,relatime 0 2", output)

    def test_keeps_existing_subvol_options(self):
        """Should not duplicate subvol options when already present."""
        input_fstab = (
            "UUID=1111 / btrfs rw,relatime,subvol=@ 0 0\n"
            "UUID=1111 /home btrfs rw,relatime,subvol=@home 0 0\n"
        )
        output = _normalize_fstab(input_fstab)
        self.assertEqual(output.count("subvol=@"), 2)
        self.assertEqual(output.count("subvol=@home"), 1)


if __name__ == "__main__":
    unittest.main()
