#!/usr/bin/env python3
"""madOS Installer - Entry point for: python3 -m mados_installer"""

import sys
import os

log_file = "/var/log/mados-installer-debug.log"

def log(msg, level="INFO"):
    line = f"[mados-installer] [{level}] {msg}"
    print(line, file=sys.stderr, flush=True)
    try:
        with open(log_file, "a") as f:
            f.write(line + "\n")
    except:
        pass

log("=" * 60, "START")
log(f"Python: {sys.executable}", "INFO")
log(f"PYTHONPATH: {os.environ.get('PYTHONPATH', '(not set)')}", "INFO")
log(f"PWD: {os.getcwd()}", "INFO")
log(f"DISPLAY: {os.environ.get('DISPLAY', '(not set)')}", "INFO")
log(f"WAYLAND_DISPLAY: {os.environ.get('WAYLAND_DISPLAY', '(not set)')}", "INFO")
log(f"DEMO_MODE: {os.environ.get('DEMO_MODE', '(not set)')}", "INFO")

try:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk
    
    log("GTK initialized", "INFO")
    
    from app import MadOSInstaller
    log("Creating app...", "INFO")
    app = MadOSInstaller()
    
    log("Starting Gtk.main()", "INFO")
    app.connect("destroy", Gtk.main_quit)
    Gtk.main()
    log("Exited", "INFO")

except Exception as e:
    log(f"ERROR: {e}", "ERROR")
    import traceback
    log(traceback.format_exc(), "ERROR")
    sys.exit(1)

finally:
    log("=" * 60, "EXIT")
