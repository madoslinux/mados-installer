"""
madOS Installer - Completion page
"""

import subprocess
import os

from gi.repository import Gtk

from config import DEMO_MODE, NORD_AURORA, NORD_POLAR_NIGHT


def create_completion_page(app):
    """Completion page with success message and reboot/exit buttons"""
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    page.get_style_context().add_class("page-container")

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    content.set_halign(Gtk.Align.FILL)
    content.set_valign(Gtk.Align.CENTER)
    content.set_hexpand(True)
    content.set_margin_start(30)
    content.set_margin_end(30)
    content.set_margin_top(10)
    content.set_margin_bottom(14)

    # Big success checkmark
    icon = Gtk.Label()
    icon.set_markup(
        f'<span size="40000" weight="bold" foreground="{NORD_AURORA["nord14"]}">&#x2713;</span>'
    )
    icon.set_halign(Gtk.Align.CENTER)
    icon.set_margin_bottom(8)
    content.pack_start(icon, False, False, 0)

    # Title
    title = Gtk.Label()
    title.set_markup(
        f'<span size="16000" weight="bold">{app.t("success_title")}</span>'
    )
    title.set_halign(Gtk.Align.CENTER)
    title.set_margin_bottom(10)
    content.pack_start(title, False, False, 0)

    # Info card
    info_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    info_card.get_style_context().add_class("completion-card")
    info_card.set_hexpand(True)

    if DEMO_MODE:
        info = Gtk.Label()
        info.set_markup(
            '<span size="9000">This was a <b>DEMONSTRATION</b> of the madOS installer.\n\n'
            "In real mode (DEMO_MODE = False):\n"
            "  • System would be installed to disk\n"
            "  • All configurations would be applied\n"
            "  • System would be ready to boot\n\n"
            "<b>Edit config.py and set DEMO_MODE = False\n"
            "for real installation.</b></span>"
        )
    else:
        info = Gtk.Label()
        info.set_markup(f'<span size="9000">{app.t("success_msg")}</span>')

    info.set_justify(Gtk.Justification.LEFT)
    info.set_line_wrap(True)
    info_card.pack_start(info, False, False, 0)
    content.pack_start(info_card, False, False, 0)

    # QR Code section
    if not DEMO_MODE:
        qr_box = _create_qr_section(app)
        if qr_box:
            content.pack_start(qr_box, False, False, 0)

    # Buttons
    btn_box = Gtk.Box(spacing=12)
    btn_box.set_halign(Gtk.Align.CENTER)
    btn_box.set_margin_top(14)

    if not DEMO_MODE:
        reboot_btn = Gtk.Button(label=app.t("reboot_now"))
        reboot_btn.get_style_context().add_class("success-button")
        reboot_btn.connect("clicked", lambda x: subprocess.run(["reboot"]))
        btn_box.pack_start(reboot_btn, False, False, 0)

    exit_btn = Gtk.Button(label=app.t("exit_live"))
    exit_btn.get_style_context().add_class("nav-back-button")
    exit_btn.connect("clicked", lambda x: Gtk.main_quit())
    btn_box.pack_start(exit_btn, False, False, 0)

    content.pack_start(btn_box, False, False, 0)
    page.pack_start(content, True, False, 0)
    app.notebook.append_page(page, Gtk.Label(label="Complete"))


def _create_qr_section(app):
    """Create QR code section for log sharing."""
    try:
        from scripts.log_summary import (
            create_log_summary,
            generate_decoder_url,
        )

        log_path = "/var/log/mados-install.log"
        if not os.path.exists(log_path):
            return None

        compressed, stats, error = create_log_summary(log_path)
        if error or not compressed:
            return None

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.get_style_context().add_class("qr-card")
        box.set_margin_top(16)
        box.set_halign(Gtk.Align.CENTER)

        qr_label = Gtk.Label()
        qr_label.set_markup(
            '<span size="9000" weight="bold">Share installation log via QR</span>'
        )
        qr_label.set_halign(Gtk.Align.CENTER)
        box.pack_start(qr_label, False, False, 0)

        decoder_url = generate_decoder_url(compressed)

        qr_image = Gtk.Image()
        try:
            import qrcode
            import tempfile
            from gi.repository import GdkPixbuf

            qr = qrcode.QRCode(
                version=2,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=1,
            )
            qr.add_data(decoder_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                img.save(f.name)
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(f.name, 200, 200, True)
                qr_image.set_from_pixbuf(pixbuf)
                os.unlink(f.name)
        except Exception as e:
            print(f"Warning: Could not generate local QR: {e}")
            qr_image.set_from_icon_name("dialog-error", 6)

        qr_image.set_halign(Gtk.Align.CENTER)
        box.pack_start(qr_image, False, False, 0)

        url_label = Gtk.Label()
        url_label.set_markup(
            f'<span size="7000" foreground="#81a1c1">{decoder_url[:60]}...</span>'
        )
        url_label.set_halign(Gtk.Align.CENTER)
        url_label.set_line_wrap(True)
        url_label.set_max_width_chars(50)
        box.pack_start(url_label, False, False, 0)

        stats_label = Gtk.Label()
        stats_label.set_markup(
            f'<span size="8000">Steps: {stats["steps"]} | '
            f"Errors: {stats['errors']} | "
            f"Warnings: {stats['warnings']} | "
            f"OK: {stats['ok']}</span>"
        )
        stats_label.set_halign(Gtk.Align.CENTER)
        box.pack_start(stats_label, False, False, 0)

        return box

    except Exception as e:
        print(f"Warning: Could not create QR section: {e}")
        return None
