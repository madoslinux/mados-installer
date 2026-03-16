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
- Disk partitioning with separate /home support
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
├── app.py              # Main window and orchestration
├── config.py           # Configuration constants
├── utils.py            # Shared utility functions
├── theme.py            # GTK theme application
├── colors.py           # Nord color palette definitions
├── css.py              # CSS styles for GTK
├── pages/              # Installer wizard pages
│   ├── base.py         # Shared UI helpers
│   ├── welcome.py
│   ├── disk.py
│   ├── partitioning.py
│   ├── user.py
│   ├── locale.py
│   ├── summary.py
│   ├── installation.py
│   └── completion.py
├── installer/          # Installation logic
│   ├── config_script.py  # Bash script generator
│   └── steps.py
├── translations/      # Language translations
└── tests/             # Test suite
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

The installer creates the following partition scheme:

| Partition | Size | Type | Mount Point |
|-----------|------|------|--------------|
| BIOS Boot | 1MB | bios_grub | - |
| EFI | 1GB | FAT32 | /boot |
| Root | 50GB | ext4 | / |
| Home | Remaining | ext4 | /home (optional) |

## Supported Disk Types

- SATA/HDD (e.g., /dev/sda)
- NVMe (e.g., /dev/nvme0n1)
- eMMC (e.g., /dev/mmcblk0)

## License

MIT License