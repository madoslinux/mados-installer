#!/usr/bin/env python3
"""madOS Installer - Entry point with debugging."""

import sys
import os
import traceback

LOG_FILE = "/var/log/mados-installer-debug.log"

def log(msg, level="INFO"):
    """Log to stderr and file."""
    line = f"[mados-installer] [{level}] {msg}"
    print(line, file=sys.stderr, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"[WARNING] Cannot write to {LOG_FILE}: {e}", file=sys.stderr)

log("=" * 60, "START")
log(f"Python: {sys.executable} ({sys.version_info.major}.{sys.version_info.minor})", "INFO")
log(f"PYTHONPATH: {os.environ.get('PYTHONPATH', '(not set)')}", "INFO")
log(f"PWD: {os.getcwd()}", "INFO")
log(f"DISPLAY: {os.environ.get('DISPLAY', '(not set)')}", "INFO")
log(f"WAYLAND_DISPLAY: {os.environ.get('WAYLAND_DISPLAY', '(not set)')}", "INFO")
log(f"XDG_SESSION_TYPE: {os.environ.get('XDG_SESSION_TYPE', '(not set)')}", "INFO")
log(f"DEMO_MODE: {os.environ.get('DEMO_MODE', '(not set)')}", "INFO")
log(f"USER: {os.environ.get('USER', '(not set)')} (UID: {os.getuid()})", "INFO")

try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log(f"Script directory: {script_dir}", "INFO")
    sys.path.insert(0, script_dir)
    
    log("Importing gi (PyGObject)...", "DEBUG")
    import gi
    log(f"gi imported from: {gi.__file__ if hasattr(gi, '__file__') else '(built-in)'}", "DEBUG")
    
    log("Requiring Gtk 3.0...", "DEBUG")
    gi.require_version("Gtk", "3.0")
    
    log("Importing Gtk...", "DEBUG")
    from gi.repository import Gtk
    
    log("Initializing GTK...", "INFO")
    gtk_ok = Gtk.init_check()
    log(f"Gtk.init_check() = {gtk_ok}", "DEBUG")
    
    if not gtk_ok:
        log("GTK INIT FAILED - No display available", "ERROR")
        log("Check: DISPLAY, WAYLAND_DISPLAY, or run with 'sudo'", "ERROR")
        sys.exit(1)
    
    log("GTK initialized successfully", "INFO")
    
    log("Importing MadOSInstaller...", "DEBUG")
    from mados_installer import MadOSInstaller
    log("MadOSInstaller imported", "DEBUG")
    
    log("Creating app instance...", "INFO")
    app = MadOSInstaller()
    log(f"App created: {type(app)}", "DEBUG")
    
    log("Connecting destroy signal...", "DEBUG")
    app.connect("destroy", Gtk.main_quit)
    
    log("Starting Gtk.main() - window should appear", "INFO")
    Gtk.main()
    log("Gtk.main() exited", "INFO")

except Exception as e:
    log(f"ERROR: {type(e).__name__}: {e}", "ERROR")
    log(f"Traceback:\n{traceback.format_exc()}", "ERROR")
    sys.exit(1)

finally:
    log("=" * 60, "EXIT")
