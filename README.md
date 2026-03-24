# madOS Installer

A GTK3-based Linux distribution installer for madOS, an Arch Linux derivative with Sway/Hyprland desktop environment.

## Features

- Graphical wizard interface for easy installation
- Support for both UEFI and BIOS boot modes
- Automatic GRUB bootloader configuration
- Secure Boot support with sbctl
- Plymouth boot splash with Nord theme
- Sway and Hyprland desktop environments
- Automatic keyboard layout configuration based on locale
- Btrfs with subvolumes for OTA snapshot support
- Demo mode for testing without system changes

## Requirements

- Python 3 with GTK3 bindings
- Linux system with root privileges (or use demo mode)
- At least 10GB free disk space

## Installation

### Demo Mode (No system changes)

```bash
python3 -m app
```

Or:

```bash
DEMO_MODE=true python3 -m app
```

### Real Installation

```bash
sudo python3 -m app
```

## Project Structure

```
mados-installer/
├── app.py                    # Main window and orchestration
├── config.py                 # Configuration constants
├── utils.py                  # Shared utility functions
├── translations.py           # Translation helper
├── __main__.py               # Entry point
├── theme/                    # Visual theming
│   ├── __init__.py
│   ├── colors.py             # Nord color palette
│   ├── css.py                # GTK CSS styles
│   └── theme.py              # Theme application
├── pages/                    # Installer wizard pages
│   ├── base.py              # Shared UI helpers
│   ├── welcome.py
│   ├── disk.py
│   ├── partitioning.py
│   ├── user.py
│   ├── locale.py
│   ├── summary.py
│   ├── installation.py
│   └── completion.py
├── installer/                # Installation logic
│   ├── config_script.py     # Bash script generator
│   └── steps.py
├── translations/            # Language translations
│   ├── en.py, es.py, fr.py, de.py, etc.
└── tests/                    # Test suite
    └── test_config_script.py
```

## Testing

Run all tests:
```bash
python3 -m unittest discover -s tests -v
```

Run a single test:
```bash
python3 -m unittest tests.test_config_script.TestConfigScript.test_basic_replacements -v
```

## Supported Languages

- English
- Español (Spanish)
- Français (French)
- Deutsch (German)
- Português (Portuguese)
- Italiano (Italian)
- 한국어 (Korean)
- 中文 (Chinese)
- 日本語 (Japanese)

## Disk Partitioning

The installer creates the following partition scheme using **Btrfs with subvolumes** for OTA snapshot support:

| Partition | Size | Type | Mount Point | Filesystem |
|-----------|------|------|------------|------------|
| BIOS Boot | 1MB | bios_grub | - | - |
| EFI | 1GB | FAT32 | /boot | FAT32 |
| Root | Remaining | btrfs | / | Btrfs |

**Btrfs Subvolumes:**

| Subvolume | Mount Point | Purpose |
|-----------|-------------|---------|
| @ | / | Root system |
| @home | /home | User data |
| @snapshots | /.snapshots | OTA rollback |

This scheme enables atomic updates with automatic rollback capability.

## Supported Disk Types

- SATA/HDD (e.g., /dev/sda)
- NVMe (e.g., /dev/nvme0n1)
- eMMC (e.g., /dev/mmcblk0)

## License

MIT License