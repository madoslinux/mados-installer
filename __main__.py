#!/usr/bin/env python3
"""madOS Installer - Entry point for: python3 -m mados_installer"""

import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from app import MadOSInstaller


def main():
    app = MadOSInstaller()
    app.connect("destroy", Gtk.main_quit)
    Gtk.main()


if __name__ == "__main__":
    main()
