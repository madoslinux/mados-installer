"""
madOS Installer - Regional settings (locale/timezone) page
"""

from gi.repository import Gtk

from config import (
    KEYBOARDS,
    LOCALE_KB_MAP,
    LOCALE_MAP,
    LOCALE_OPTIONS_MAP,
    NORD_FROST,
    NORD_POLAR_NIGHT,
    NORD_SNOW_STORM,
    TIMEZONES,
)

from .base import create_nav_buttons, create_page_header


def create_locale_page(app):
    """Locale page with timezone selector (language already chosen on welcome)"""
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
    header = create_page_header(app, app.t("regional"), 5)
    content.pack_start(header, False, False, 0)

    # Language + locale card
    lang_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    lang_card.get_style_context().add_class("content-card")
    lang_card.set_margin_top(6)
    lang_card.set_hexpand(True)

    lang_icon_label = Gtk.Label()
    lang_icon_label.set_markup(
        f'<span size="9000" weight="bold" foreground="{NORD_FROST["nord8"]}">'
        f"{app.t('locale_label').rstrip(':')}</span>"
    )
    lang_icon_label.set_halign(Gtk.Align.START)
    lang_card.pack_start(lang_icon_label, False, False, 0)

    lang_value = Gtk.Label()
    lang_value.set_markup(f'<span size="11000" weight="bold">{app.current_lang}</span>')
    lang_value.set_halign(Gtk.Align.START)
    lang_value.set_margin_start(24)
    lang_card.pack_start(lang_value, False, False, 0)

    app.locale_combo = Gtk.ComboBoxText()
    locale_options = LOCALE_OPTIONS_MAP.get(
        app.current_lang,
        [LOCALE_MAP.get(app.current_lang, app.install_data["locale"])],
    )
    for locale_code in locale_options:
        app.locale_combo.append_text(locale_code)

    current_locale = app.install_data.get("locale")
    try:
        app.locale_combo.set_active(locale_options.index(current_locale))
    except ValueError:
        app.locale_combo.set_active(0)
        app.install_data["locale"] = locale_options[0]

    app.locale_combo.set_margin_start(24)
    app.locale_combo.set_margin_end(8)
    lang_card.pack_start(app.locale_combo, False, False, 0)

    content.pack_start(lang_card, False, False, 0)

    # Timezone card
    tz_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    tz_card.get_style_context().add_class("content-card")
    tz_card.set_margin_top(6)
    tz_card.set_hexpand(True)

    tz_label = Gtk.Label()
    tz_label.set_markup(
        f'<span size="9000" weight="bold" foreground="{NORD_FROST["nord8"]}">'
        f"{app.t('timezone').rstrip(':')}</span>"
    )
    tz_label.set_halign(Gtk.Align.START)
    tz_card.pack_start(tz_label, False, False, 0)

    app.timezone_combo = Gtk.ComboBoxText()
    for tz in TIMEZONES:
        app.timezone_combo.append_text(tz)
    app.timezone_combo.set_active(0)
    app.timezone_combo.set_margin_start(24)
    app.timezone_combo.set_margin_end(8)
    tz_card.pack_start(app.timezone_combo, False, False, 0)

    content.pack_start(tz_card, False, False, 0)

    # Keyboard layout card
    kb_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    kb_card.get_style_context().add_class("content-card")
    kb_card.set_margin_top(6)
    kb_card.set_hexpand(True)

    kb_label = Gtk.Label()
    kb_label.set_markup(
        f'<span size="9000" weight="bold" foreground="{NORD_FROST["nord8"]}">'
        f"{app.t('keyboard').rstrip(':')}</span>"
    )
    kb_label.set_halign(Gtk.Align.START)
    kb_card.pack_start(kb_label, False, False, 0)

    app.keyboard_combo = Gtk.ComboBoxText()
    for kb_code, kb_name in KEYBOARDS:
        app.keyboard_combo.append_text(f"{kb_name} ({kb_code})")
    app.keyboard_combo.set_active(0)
    app.keyboard_combo.set_margin_start(24)
    app.keyboard_combo.set_margin_end(8)
    kb_card.pack_start(app.keyboard_combo, False, False, 0)

    app.locale_combo.connect("changed", lambda combo: _on_locale_changed(app, combo))
    _set_keyboard_from_locale(app, app.locale_combo.get_active_text())

    content.pack_start(kb_card, False, False, 0)

    # Navigation
    nav = create_nav_buttons(
        app, lambda x: app.notebook.prev_page(), lambda x: _on_locale_next(app)
    )
    nav.set_hexpand(True)
    content.pack_start(nav, False, False, 0)

    page.pack_start(content, True, False, 0)
    app.notebook.append_page(page, Gtk.Label(label="Locale"))


def _on_locale_next(app):
    """Save locale data and advance to summary"""
    app.install_data["locale"] = app.locale_combo.get_active_text()
    app.install_data["timezone"] = app.timezone_combo.get_active_text()
    kb_code, _ = KEYBOARDS[app.keyboard_combo.get_active()]
    app.install_data["keyboard"] = kb_code
    # Trigger summary update before showing the page
    from pages.summary import update_summary

    update_summary(app)
    app.notebook.next_page()


def _on_locale_changed(app, combo):
    """Update keyboard suggestion when locale changes."""
    locale_code = combo.get_active_text()
    _set_keyboard_from_locale(app, locale_code)


def _set_keyboard_from_locale(app, locale_code):
    """Select matching keyboard layout for locale when available."""
    if not locale_code:
        return

    recommended_kb = LOCALE_KB_MAP.get(locale_code)
    if not recommended_kb:
        return

    for idx, (kb_code, _) in enumerate(KEYBOARDS):
        if kb_code == recommended_kb:
            app.keyboard_combo.set_active(idx)
            break
