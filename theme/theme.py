"""
madOS Installer - Nord theme application
"""

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk

from theme.css import CSS


def apply_theme():
    """Apply Nord dark theme to the entire application"""
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(CSS.encode())
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
