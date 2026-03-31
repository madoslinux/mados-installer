#!/usr/bin/env python3
"""madOS Installer - Entry point with comprehensive debugging."""

import sys
import os
import traceback
import logging

# Setup logging to both stderr and file
LOG_FILE = "/var/log/mados-installer-debug.log"

def setup_logging():
    """Setup comprehensive logging."""
    log_handlers = [logging.StreamHandler(sys.stderr)]
    try:
        fh = logging.FileHandler(LOG_FILE)
        log_handlers.append(fh)
    except Exception as e:
        pass
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        handlers=log_handlers
    )
    return logging.getLogger('mados-installer')

log = setup_logging()
log.info("=" * 60)
log.info("MADOS INSTALLER STARTING")
log.info("=" * 60)
log.info(f"Python executable: {sys.executable}")
log.info(f"Python version: {sys.version}")
log.info(f"Python path: {sys.path}")
log.info(f"Current working directory: {os.getcwd()}")
log.info(f"Script __file__: {__file__}")
log.info(f"Script absolute path: {os.path.abspath(__file__)}")
log.info(f"Environment DEMO_MODE: {os.environ.get('DEMO_MODE', 'not set')}")
log.info(f"Environment DISPLAY: {os.environ.get('DISPLAY', 'not set')}")
log.info(f"Environment WAYLAND_DISPLAY: {os.environ.get('WAYLAND_DISPLAY', 'not set')}")
log.info(f"Environment XDG_SESSION_TYPE: {os.environ.get('XDG_SESSION_TYPE', 'not set')}")
log.info(f"Environment XDG_RUNTIME_DIR: {os.environ.get('XDG_RUNTIME_DIR', 'not set')}")
log.info(f"User: {os.environ.get('USER', 'not set')} (UID: {os.getuid()})")
log.info(f"Home: {os.environ.get('HOME', 'not set')}")

try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log.info(f"Adding script_dir to sys.path: {script_dir}")
    sys.path.insert(0, script_dir)
    log.info(f"Updated sys.path: {sys.path[:5]}...")

    # Check if mados_installer module can be found
    log.info("Searching for mados_installer module...")
    for path in sys.path:
        test_path = os.path.join(path, 'mados_installer.py')
        if os.path.exists(test_path):
            log.info(f"  Found mados_installer.py at: {test_path}")
    
    log.info("Importing gi (PyGObject)...")
    import gi
    log.info(f"  gi imported successfully from: {gi.__file__ if hasattr(gi, '__file__') else 'built-in'}")
    
    log.info("Requiring Gtk version 3.0...")
    gi.require_version("Gtk", "3.0")
    log.info("  Gtk 3.0 requirement satisfied")
    
    log.info("Importing Gtk from gi.repository...")
    from gi.repository import Gtk
    log.info(f"  Gtk imported successfully")
    log.info(f"  Gtk version: {Gtk._version if hasattr(Gtk, '_version') else 'unknown'}")

    log.info("Initializing GTK...")
    gtk_initialized = Gtk.init_check()
    log.info(f"  Gtk.init_check() returned: {gtk_initialized}")
    
    if not gtk_initialized:
        log.error("GTK initialization failed - no display available")
        log.error("This usually means:")
        log.error("  1. No X11/Wayland display server is running")
        log.error("  2. DISPLAY environment variable is not set")
        log.error("  3. Running in a terminal without GUI access")
        sys.exit(1)
    
    log.info("GTK initialized successfully!")

    log.info("Importing MadOSInstaller from mados_installer module...")
    from mados_installer import MadOSInstaller
    log.info("  MadOSInstaller imported successfully")

    log.info("Creating MadOSInstaller instance...")
    app = MadOSInstaller()
    log.info(f"  App instance created: {app}")
    log.info(f"  App type: {type(app)}")
    
    log.info("Connecting destroy signal to Gtk.main_quit...")
    app.connect("destroy", Gtk.main_quit)
    log.info("  Signal connected")

    log.info("Starting Gtk.main() event loop...")
    log.info("  The installer window should appear now")
    Gtk.main()
    log.info("Gtk.main() exited - user closed window or quit")

except ImportError as e:
    log.error(f"IMPORT ERROR: {e}")
    log.error(f"ImportError details:")
    log.error(traceback.format_exc())
    log.error("Common causes:")
    log.error("  - Missing Python module (run: pacman -S python-gobject gtk3)")
    log.error("  - Wrong PYTHONPATH")
    log.error("  - Module file not found in expected location")
    sys.exit(1)

except Exception as e:
    log.error(f"FATAL ERROR: {e}")
    log.error(f"Error type: {type(e).__name__}")
    log.error("Full traceback:")
    log.error(traceback.format_exc())
    sys.exit(1)

finally:
    log.info("=" * 60)
    log.info("MADOS INSTALLER EXITING")
    log.info("=" * 60)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(f"\n[Final] Log file: {LOG_FILE}\n")
    except:
        pass

