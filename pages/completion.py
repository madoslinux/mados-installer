"""
madOS Installer - Completion page
"""

import os
import subprocess

from gi.repository import Gtk

from config import DEMO_MODE, NORD_AURORA
from utils import LOG_FILE


def create_completion_page(app):
    """Completion success page with reboot/exit buttons."""
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    page.get_style_context().add_class("page-container")

    # Centered success content (no QR on success page)
    main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    main_box.set_halign(Gtk.Align.CENTER)
    main_box.set_valign(Gtk.Align.CENTER)
    main_box.set_hexpand(False)
    main_box.set_margin_start(22)
    main_box.set_margin_end(22)
    main_box.set_margin_top(6)
    main_box.set_margin_bottom(10)

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    content.set_halign(Gtk.Align.CENTER)
    content.set_valign(Gtk.Align.CENTER)
    content.set_hexpand(False)

    icon = Gtk.Label()
    icon.set_markup(
        f'<span size="30000" weight="bold" foreground="{NORD_AURORA["nord14"]}">&#x2713;</span>'
    )
    icon.set_halign(Gtk.Align.CENTER)
    icon.set_margin_bottom(4)
    content.pack_start(icon, False, False, 0)

    title = Gtk.Label()
    title.set_markup(
        f'<span size="13200" weight="bold">{app.t("success_title")}</span>'
    )
    title.set_halign(Gtk.Align.CENTER)
    title.set_margin_bottom(6)
    content.pack_start(title, False, False, 0)

    info_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    info_card.get_style_context().add_class("completion-card")
    info_card.set_halign(Gtk.Align.CENTER)
    info_card.set_hexpand(False)

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

    info.set_halign(Gtk.Align.CENTER)
    info.set_justify(Gtk.Justification.CENTER)
    info.set_line_wrap(True)
    info_card.pack_start(info, False, False, 0)
    content.pack_start(info_card, False, False, 0)

    if not DEMO_MODE:
        reboot_hint = Gtk.Label()
        reboot_hint.set_markup(
            '<span size="7600">Tip: remove installation media before reboot</span>'
        )
        reboot_hint.set_halign(Gtk.Align.CENTER)
        reboot_hint.set_margin_top(4)
        content.pack_start(reboot_hint, False, False, 0)

        secure_boot_note = Gtk.Label()
        secure_boot_note.set_markup(
            f'<span size="8400">{app.t("secure_boot_note")}</span>'
        )
        secure_boot_note.set_halign(Gtk.Align.CENTER)
        secure_boot_note.set_justify(Gtk.Justification.CENTER)
        secure_boot_note.set_line_wrap(True)
        secure_boot_note.set_margin_top(8)
        content.pack_start(secure_boot_note, False, False, 0)

    # Buttons
    btn_box = Gtk.Box(spacing=12)
    btn_box.set_halign(Gtk.Align.CENTER)
    btn_box.set_margin_top(8)

    restart_toggle = Gtk.CheckButton(label="Reboot after completion")
    restart_toggle.set_active(not DEMO_MODE)
    restart_toggle.set_halign(Gtk.Align.CENTER)
    restart_toggle.set_margin_top(6)
    content.pack_start(restart_toggle, False, False, 0)
    app.reboot_after_completion = restart_toggle

    if not DEMO_MODE:
        reboot_btn = Gtk.Button(label=app.t("reboot_now"))
        reboot_btn.get_style_context().add_class("success-button")
        reboot_btn.connect("clicked", lambda x: _on_reboot_clicked(app))
        btn_box.pack_start(reboot_btn, False, False, 0)

    exit_btn = Gtk.Button(label=app.t("exit_live"))
    exit_btn.get_style_context().add_class("nav-back-button")
    exit_btn.connect("clicked", lambda x: Gtk.main_quit())
    btn_box.pack_start(exit_btn, False, False, 0)

    open_log_btn = Gtk.Button(label="Open Install Log")
    open_log_btn.get_style_context().add_class("nav-back-button")
    open_log_btn.connect("clicked", lambda x: _on_open_log_clicked(app))
    btn_box.pack_start(open_log_btn, False, False, 0)

    content.pack_start(btn_box, False, False, 0)

    main_box.pack_start(content, False, False, 0)

    page.pack_start(main_box, True, True, 0)
    app.notebook.append_page(page, Gtk.Label(label="Complete"))
    app.success_page_index = app.notebook.page_num(page)
    app.qr_container = None


def _on_reboot_clicked(app):
    """Reboot only when checkbox is active."""
    if (
        hasattr(app, "reboot_after_completion")
        and app.reboot_after_completion.get_active()
    ):
        subprocess.run(["reboot"])


def _on_open_log_clicked(app):
    """Open saved installer log in terminal pager."""
    log_path = getattr(app, "last_log_path", LOG_FILE)
    if not log_path or not os.path.exists(log_path):
        return
    terminals = ["konsole", "gnome-terminal", "xfce4-terminal", "xterm", "uxterm"]
    for term in terminals:
        try:
            subprocess.Popen([term, "-e", f"less '{log_path}'"])
            return
        except FileNotFoundError:
            continue


def create_error_page(app):
    """Completion error page with QR support only."""
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    page.get_style_context().add_class("page-container")

    main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    main_box.set_halign(Gtk.Align.CENTER)
    main_box.set_valign(Gtk.Align.CENTER)
    main_box.set_hexpand(True)
    main_box.set_margin_start(22)
    main_box.set_margin_end(22)
    main_box.set_margin_top(6)
    main_box.set_margin_bottom(10)

    left_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    left_content.set_halign(Gtk.Align.START)
    left_content.set_valign(Gtk.Align.CENTER)
    left_content.set_hexpand(True)

    icon = Gtk.Label()
    icon.set_markup(
        '<span size="28000" weight="bold" foreground="#dc7878">&#x2717;</span>'
    )
    icon.set_halign(Gtk.Align.CENTER)
    icon.set_margin_bottom(4)
    left_content.pack_start(icon, False, False, 0)

    title = Gtk.Label()
    title.set_markup('<span size="13200" weight="bold">Installation Failed</span>')
    title.set_halign(Gtk.Align.CENTER)
    title.set_margin_bottom(6)
    left_content.pack_start(title, False, False, 0)

    info_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    info_card.get_style_context().add_class("completion-card")
    info_card.set_hexpand(True)

    error_info = Gtk.Label()
    error_info.set_markup(
        '<span size="9000" foreground="#dc7878">Installation failed. Scan the QR code to share logs.</span>'
    )
    error_info.set_justify(Gtk.Justification.LEFT)
    error_info.set_line_wrap(True)
    info_card.pack_start(error_info, False, False, 0)
    left_content.pack_start(info_card, False, False, 0)

    btn_box = Gtk.Box(spacing=12)
    btn_box.set_halign(Gtk.Align.CENTER)
    btn_box.set_margin_top(8)

    exit_btn = Gtk.Button(label="Exit")
    exit_btn.get_style_context().add_class("nav-back-button")
    exit_btn.connect("clicked", lambda x: Gtk.main_quit())
    btn_box.pack_start(exit_btn, False, False, 0)
    left_content.pack_start(btn_box, False, False, 0)

    right_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    right_content.set_halign(Gtk.Align.CENTER)
    right_content.set_valign(Gtk.Align.CENTER)
    right_content.set_name("qr-container-error")
    right_content.set_size_request(220, -1)

    main_box.pack_start(left_content, True, True, 0)
    main_box.pack_start(right_content, False, False, 0)
    page.pack_start(main_box, True, True, 0)
    app.notebook.append_page(page, Gtk.Label(label="Error"))
    app.error_page_index = app.notebook.page_num(page)
    app.qr_error_container = right_content
    app.error_info_label = error_info


def _create_qr_section(app):
    """Create QR code section for log sharing."""
    try:
        from scripts.log_summary import create_log_summary, generate_decoder_url

        log_path = LOG_FILE
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
            import tempfile

            import qrcode
            from gi.repository import GdkPixbuf

            qr = qrcode.QRCode(
                version=2,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=2,
            )
            qr.add_data(decoder_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                img.save(f.name)
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(f.name, 300, 300, True)
                qr_image.set_from_pixbuf(pixbuf)
                os.unlink(f.name)
        except Exception as e:
            print(f"Warning: Could not generate local QR: {e}")
            try:
                import urllib.request

                qr_api_url = (
                    f"https://api.qrserver.com/v1/create-qr-code/"
                    f"?size=300x300&data={urllib.parse.quote(decoder_url)}"
                )
                with urllib.request.urlopen(qr_api_url, timeout=15) as response:
                    img_data = response.read()
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                    f.write(img_data)
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        f.name, 300, 300, True
                    )
                    qr_image.set_from_pixbuf(pixbuf)
                    os.unlink(f.name)
                print("QR: generated via API fallback")
            except Exception as e2:
                print(f"Warning: QR API fallback also failed: {e2}")
                qr_image.set_from_icon_name("dialog-information", 6)
                qr_image.set_pixel_size(100)

        qr_image.set_halign(Gtk.Align.CENTER)
        box.pack_start(qr_image, False, False, 0)

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
