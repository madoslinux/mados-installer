"""
madOS Installer - User account creation page
"""

import re

from gi.repository import Gtk

from config import NORD_FROST
from utils import show_error

from .base import create_nav_buttons, create_page_header


def create_user_page(app):
    """User account page with username, password, hostname fields"""
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    page.get_style_context().add_class("page-container")

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    content.set_margin_start(22)
    content.set_margin_end(22)
    content.set_margin_bottom(10)
    content.set_halign(Gtk.Align.FILL)
    content.set_valign(Gtk.Align.CENTER)
    content.set_hexpand(True)

    # Page header
    header = create_page_header(app, app.t("create_user"), 4)
    content.pack_start(header, False, False, 0)

    # Form card
    form = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    form.get_style_context().add_class("form-card")
    form.set_margin_top(6)
    form.set_hexpand(True)

    # Username
    user_label = Gtk.Label()
    user_label.set_markup(
        f'<span size="9000" weight="bold" foreground="{NORD_FROST["nord8"]}">'
        f"{app.t('username').rstrip(':')}</span>"
    )
    user_label.set_halign(Gtk.Align.START)
    form.pack_start(user_label, False, False, 0)

    app.username_entry = Gtk.Entry()
    app.username_entry.set_placeholder_text("lowercase, no spaces")
    app.username_entry.connect("changed", lambda e: _refresh_user_hints(app))
    form.pack_start(app.username_entry, False, False, 0)

    # Password
    pwd_label = Gtk.Label()
    pwd_label.set_markup(
        f'<span size="9000" weight="bold" foreground="{NORD_FROST["nord8"]}">'
        f"{app.t('pwd_label').rstrip(':')}</span>"
    )
    pwd_label.set_halign(Gtk.Align.START)
    pwd_label.set_margin_top(2)
    form.pack_start(pwd_label, False, False, 0)

    app.password_entry = Gtk.Entry()
    app.password_entry.set_visibility(False)
    app.password_entry.set_placeholder_text("enter password")
    app.password_entry.connect("changed", lambda e: _refresh_user_hints(app))
    form.pack_start(app.password_entry, False, False, 0)

    # Confirm password
    pwd2_label = Gtk.Label()
    pwd2_label.set_markup(
        f'<span size="9000" weight="bold" foreground="{NORD_FROST["nord8"]}">'
        f"{app.t('pwd_confirm_label').rstrip(':')}</span>"
    )
    pwd2_label.set_halign(Gtk.Align.START)
    pwd2_label.set_margin_top(2)
    form.pack_start(pwd2_label, False, False, 0)

    app.password2_entry = Gtk.Entry()
    app.password2_entry.set_visibility(False)
    app.password2_entry.set_placeholder_text("confirm password")
    app.password2_entry.connect("changed", lambda e: _refresh_user_hints(app))
    form.pack_start(app.password2_entry, False, False, 0)

    # Hostname
    host_label = Gtk.Label()
    host_label.set_markup(
        f'<span size="9000" weight="bold" foreground="{NORD_FROST["nord8"]}">'
        f"{app.t('hostname').rstrip(':')}</span>"
    )
    host_label.set_halign(Gtk.Align.START)
    host_label.set_margin_top(2)
    form.pack_start(host_label, False, False, 0)

    app.hostname_entry = Gtk.Entry()
    app.hostname_entry.set_text(app.install_data["hostname"])
    app.hostname_entry.connect("changed", lambda e: _refresh_user_hints(app))
    form.pack_start(app.hostname_entry, False, False, 0)

    app.user_hints_label = Gtk.Label()
    app.user_hints_label.set_halign(Gtk.Align.START)
    app.user_hints_label.set_margin_top(4)
    form.pack_start(app.user_hints_label, False, False, 0)
    _refresh_user_hints(app)

    content.pack_start(form, False, False, 0)

    # Navigation
    nav = create_nav_buttons(
        app, lambda x: app.notebook.prev_page(), lambda x: _on_user_next(app)
    )
    nav.set_hexpand(True)
    content.pack_start(nav, False, False, 0)

    page.pack_start(content, True, False, 0)
    app.notebook.append_page(page, Gtk.Label(label="User"))

    app.username_entry.grab_focus()


def _refresh_user_hints(app):
    """Show live validation hints for account fields."""
    username = app.username_entry.get_text().strip()
    password = app.password_entry.get_text()
    password2 = app.password2_entry.get_text()
    hostname = app.hostname_entry.get_text().strip()

    username_ok = bool(re.match(r"^[a-z_][a-z0-9_-]*$", username))
    password_len_ok = len(password) >= 8
    password_match_ok = bool(password) and password == password2
    hostname_ok = (
        bool(re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$", hostname))
        and len(hostname) <= 63
    )

    checks = [
        ("username", username_ok),
        ("password", password_len_ok),
        ("confirm", password_match_ok),
        ("hostname", hostname_ok),
    ]
    hint_text = "  ".join([f"{'OK' if ok else '...'} {label}" for label, ok in checks])
    app.user_hints_label.set_markup(
        f'<span size="7800" foreground="{NORD_FROST["nord8"]}">{hint_text}</span>'
    )


def _on_user_next(app):
    """Validate and save user data"""
    username = app.username_entry.get_text()
    password = app.password_entry.get_text()
    password2 = app.password2_entry.get_text()
    hostname = app.hostname_entry.get_text()

    if not re.match(r"^[a-z_][a-z0-9_-]*$", username):
        show_error(
            app,
            "Invalid Username",
            "Username must start with a letter and contain only lowercase letters, numbers, - and _",
        )
        return

    if not password:
        show_error(app, "Empty Password", "Password cannot be empty.")
        return

    if password != password2:
        show_error(app, "Password Mismatch", "Passwords do not match!")
        return

    if not hostname:
        show_error(app, "Empty Hostname", "Hostname cannot be empty.")
        return

    if (
        not re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$", hostname)
        or len(hostname) > 63
    ):
        show_error(
            app,
            "Invalid Hostname",
            "Hostname must contain only letters, numbers and hyphens, "
            "start/end with a letter or number, and be at most 63 characters.",
        )
        return

    if len(password) < 8:
        show_error(app, "Weak Password", "Password must be at least 8 characters.")
        return

    app.install_data["username"] = username
    app.install_data["password"] = password
    app.install_data["hostname"] = hostname
    app.notebook.next_page()
