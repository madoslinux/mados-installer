# AGENTS.md - madOS Installer Development Guide

## Overview

madOS Installer is a GTK3-based Linux distribution installer written in Python. It provides a graphical wizard interface for installing madOS (an Arch Linux derivative) with Sway/Hyprland desktop environment.

## Project Structure

```
mados-installer/
├── app.py              # Main window and orchestration
├── config.py           # Configuration constants
├── utils.py            # Shared utility functions
├── theme.py            # GTK theme application
├── colors.py           # Nord color palette definitions
├── css.py              # CSS styles for GTK
├── translations.py     # Translation helper
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
├── installer/           # Installation logic
│   ├── config_script.py  # Bash script generator
│   └── steps.py
├── translations/       # Language translations
│   ├── en.py, es.py, fr.py, de.py, etc.
└── tests/              # Test suite
    └── test_config_script.py
```

## Build/Lint/Test Commands

### Running Tests

Run all tests:
```bash
python3 -m unittest discover -s tests -v
```

Run a single test:
```bash
python3 -m unittest tests.test_config_script.TestConfigScript.test_basic_replacements -v
```

Or using pytest (if installed):
```bash
pytest tests/test_config_script.py::TestConfigScript::test_basic_replacements -v
```

### Running the Application

Run in demo mode (no system changes):
```bash
python3 -m app
```

Run in demo mode (explicit):
```bash
DEMO_MODE=true python3 -m app
```

Or run the executable wrapper:
```bash
./mados-installer
```

## Code Style Guidelines

### General Principles

- Use **Python 3** with type hints where beneficial
- Follow [PEP 8](https://peps.python.org/pep-0008/) style guidelines
- Use 4 spaces for indentation (not tabs)
- Maximum line length: 120 characters
- Use meaningful, descriptive names

### Imports

Organize imports in the following order with blank lines between groups:

```python
# Standard library
import os
import sys
import re

# Third-party libraries
import gi
from gi.repository import Gtk, GLib, GdkPixbuf

# Local application imports
from config import DEMO_MODE, LOCALE_MAP
from translations import TRANSLATIONS
from utils import random_suffix, show_error
```

### Naming Conventions

- **Functions/variables**: `snake_case` (e.g., `random_suffix`, `install_data`)
- **Classes**: `PascalCase` (e.g., `MadOSInstaller`, `TestConfigScript`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DEMO_MODE`, `MIN_DISK_SIZE_GB`)
- **Private methods**: prefix with underscore (e.g., `_build_pages`, `_escape_shell`)

### Type Hints

Use type hints for function signatures, especially for public APIs:

```python
def build_config_script(data: dict) -> str:
    """Build the chroot configuration shell script."""
    ...

def create_page_header(app, title: str, step_num: int, total_steps: int = 7):
    """Create consistent page header with step indicator dots."""
    ...
```

### Docstrings

Use docstrings for all public functions and classes:

```python
def random_suffix(length=4):
    """Generate random hostname suffix"""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


class MadOSInstaller(Gtk.Window):
    """Main installer window — orchestrates pages and holds shared state."""
```

### Error Handling

- Use specific exception types (`ValueError` for validation, `OSError` for I/O)
- Provide clear error messages that explain what went wrong
- Validate inputs at function entry points

```python
def build_config_script(data):
    disk = data["disk"]

    timezone = data["timezone"]
    if timezone not in TIMEZONES:
        raise ValueError(f"Invalid timezone: {timezone}")

    username = data["username"]
    if not re.match(r"^[a-z_][a-z0-9_-]*$", username):
        raise ValueError(f"Invalid username: {username}")
```

### GTK-Specific Guidelines

- Use `Gtk.Orientation.VERTICAL` / `Gtk.Orientation.HORIZONTAL` instead of strings
- Use `Gtk.Align.CENTER`, `Gtk.Align.START`, etc. for alignment
- Apply dark theme using CSS classes and context add/remove
- Use `GLib.idle_add()` for thread-safe UI updates

```python
# Good
header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
header.get_style_context().add_class("page-header")
title_label.set_halign(Gtk.Align.CENTER)

# Thread-safe logging
GLib.idle_add(_log_idle, app, message)
```

### Shell Script Generation

When generating shell scripts (like `config_script.py`):

- Use single quotes for strings that shouldn't expand (`'${var}'`)
- Escape braces for Python f-strings: `{{ echo; }}` becomes `{ echo; }`
- Use the `_escape_shell()` helper for user-provided strings
- Include progress markers: `[PROGRESS 1/8]`, `[PROGRESS 2/8]`, etc.

```python
return f'''#!/bin/bash
set -e

echo "[PROGRESS 1/8] Setting timezone and locale..."
# Timezone
ln -sf /usr/share/zoneinfo/{timezone} /etc/localtime
...
'''
```

### Testing Guidelines

- Use Python's built-in `unittest` module
- Name test files as `test_*.py`
- Use descriptive test method names: `test_*_replacements`, `test_*_not_*`
- Test both success and failure cases (invalid inputs)

```python
class TestConfigScript(unittest.TestCase):
    def test_basic_replacements(self):
        """Test basic variable replacements work"""
        script = build_config_script(self.data)

        self.assertIn("/usr/share/zoneinfo/Europe/Madrid", script)
        self.assertIn("es_ES.UTF-8 UTF-8", script)

    def test_invalid_username(self):
        """Test invalid username raises error"""
        data = self.data.copy()
        data["username"] = "123invalid"

        with self.assertRaises(ValueError):
            build_config_script(data)
```

### Configuration Constants

Store all configuration in `config.py`:

- Package lists (`PACKAGES_PHASE1`, `PACKAGES_PHASE2`)
- Locale mappings (`LOCALE_MAP`, `LOCALE_KB_MAP`)
- Timezones list (`TIMEZONES`)
- RSYNC excludes (`RSYNC_EXCLUDES`)
- Demo mode flag (`DEMO_MODE`)

### Translation Support

- Store translations in `translations/` directory as language modules
- Use the translation helper in `app.py`: `self.t("key")`
- Access via `TRANSLATIONS[self.current_lang].get(key, key)`

### Common Patterns

**Creating a new wizard page:**
1. Create a function `create_X_page(app)` in `pages/X.py`
2. Use shared helpers from `pages/base.py`: `create_page_header()`, `create_nav_buttons()`
3. Import and add to the page flow in `app.py:_build_pages()`

**Adding new configuration:**
1. Add to `config.py` as a constant
2. Update `install_data` dictionary in `app.py` if it's user input
3. Use in relevant modules via import

## Important Notes

- The installer runs as root (required for disk operations)
- Demo mode (`DEMO_MODE=True`) allows testing without system changes
- The `config_script.py` generates a bash script that runs in chroot
- All UI updates must be thread-safe via `GLib.idle_add()`
