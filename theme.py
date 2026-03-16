"""
madOS Installer - Nord theme application
"""

from gi.repository import Gtk, Gdk

from css import CSS


def apply_theme():
    """Apply Nord dark theme to the entire application"""
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(CSS.encode())
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )