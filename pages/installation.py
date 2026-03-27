"""
madOS Installer - Installation progress page and install logic
"""

import os
import subprocess
import time
import threading
import urllib.parse

from gi.repository import Gtk, GLib

from config import DEMO_MODE, NORD_FROST
from utils import log_message, set_progress, show_error, save_log_to_file

from pages.base import create_page_header
from installer import (
    step_partition_disk,
    step_format_partitions,
    step_create_btrfs_subvolumes,
    step_mount_filesystems,
    step_copy_live_files,
    step_copy_installer_scripts,
    step_generate_fstab,
    step_configure_snapper,
    step_configure_mados_updater,
    step_create_base_snapshot,
    rsync_rootfs_with_progress,
    run_chroot_with_progress,
    build_config_script,
    _check_required_commands,
    step_install_nvidia_if_needed,
)


def create_installation_page(app):
    """Installation progress page with spinner, progress bar and log"""
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    page.get_style_context().add_class("page-container")
    page.set_valign(Gtk.Align.CENTER)

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    content.set_margin_start(30)
    content.set_margin_end(30)
    content.set_margin_top(10)
    content.set_margin_bottom(14)

    app.install_spinner = Gtk.Spinner()
    app.install_spinner.get_style_context().add_class("install-spinner")
    app.install_spinner.set_halign(Gtk.Align.CENTER)
    app.install_spinner.set_margin_top(8)
    content.pack_start(app.install_spinner, False, False, 0)

    title = Gtk.Label()
    title.set_markup(f'<span size="15000" weight="bold">{app.t("installing")}</span>')
    title.set_halign(Gtk.Align.CENTER)
    content.pack_start(title, False, False, 0)

    app.status_label = Gtk.Label()
    app.status_label.set_markup(
        f'<span size="10000" foreground="{NORD_FROST["nord8"]}">{app.t("preparing")}</span>'
    )
    app.status_label.set_halign(Gtk.Align.CENTER)
    content.pack_start(app.status_label, False, False, 0)

    app.progress_bar = Gtk.ProgressBar()
    app.progress_bar.set_show_text(True)
    app.progress_bar.set_margin_top(4)
    app.progress_bar.set_margin_start(16)
    app.progress_bar.set_margin_end(16)
    content.pack_start(app.progress_bar, False, False, 0)

    app.log_toggle = Gtk.EventBox()
    app.log_toggle.set_halign(Gtk.Align.CENTER)
    app.log_toggle.set_margin_top(8)
    toggle_label = Gtk.Label()
    toggle_label.set_markup(
        f'<span size="9000" foreground="{NORD_FROST["nord8"]}">{app.t("show_log")}</span>'
    )
    toggle_label.get_style_context().add_class("log-toggle")
    app.log_toggle.add(toggle_label)
    app.log_toggle.connect("button-press-event", lambda w, e: _toggle_log(app))
    content.pack_start(app.log_toggle, False, False, 0)

    log_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    log_card.get_style_context().add_class("content-card")
    log_card.set_margin_top(4)
    log_card.set_no_show_all(True)
    app.log_card = log_card

    scrolled = Gtk.ScrolledWindow()
    scrolled.set_min_content_height(120)
    scrolled.set_max_content_height(180)
    app.log_scrolled = scrolled

    app.log_buffer = Gtk.TextBuffer()
    log_view = Gtk.TextView(buffer=app.log_buffer)
    log_view.set_editable(False)
    log_view.set_monospace(True)
    log_view.set_left_margin(12)
    log_view.set_right_margin(12)
    log_view.set_top_margin(8)
    log_view.set_bottom_margin(8)
    scrolled.add(log_view)

    log_card.pack_start(scrolled, True, True, 0)
    content.pack_start(log_card, True, True, 0)

    page.pack_start(content, True, True, 0)
    app.notebook.append_page(page, Gtk.Label(label="Installing"))


def _toggle_log(app):
    """Toggle visibility of the log console"""
    if app.log_card.get_visible():
        app.log_card.hide()
        label = app.log_toggle.get_child()
        label.set_markup(
            f'<span size="9000" foreground="{NORD_FROST["nord8"]}">{app.t("show_log")}</span>'
        )
    else:
        app.log_card.show()
        app.log_card.foreach(lambda w: w.show_all())
        label = app.log_toggle.get_child()
        label.set_markup(
            f'<span size="9000" foreground="{NORD_FROST["nord8"]}">{app.t("hide_log")}</span>'
        )


def on_start_installation(app):
    """Start the installation process"""
    app.notebook.next_page()
    app.install_spinner.start()

    thread = threading.Thread(target=_run_installation, args=(app,))
    thread.daemon = True
    thread.start()


def _run_installation(app):
    """Perform installation (runs in background thread)."""
    try:
        if not DEMO_MODE:
            _check_required_commands(app)

        data = app.install_data
        disk = data["disk"]
        disk_size_gb = data["disk_size_gb"]

        boot_part, root_part = step_partition_disk(app, disk, disk_size_gb)
        app.install_data["root_part"] = root_part

        step_format_partitions(app, boot_part, root_part)

        step_create_btrfs_subvolumes(app, root_part)

        step_mount_filesystems(app, boot_part, root_part)

        if DEMO_MODE:
            log_message(app, "[DEMO] Simulating system copy from live ISO...")
            set_progress(app, 0.21, "Copying system files...")
            time.sleep(0.5)
            log_message(app, "[DEMO] rsync / → /mnt/ ...")
            for pct in (25, 50, 75, 100):
                set_progress(app, 0.21 + 0.22 * pct / 100, f"Copying ({pct}%)...")
                time.sleep(0.3)
            log_message(app, "[DEMO] Cleaning archiso artifacts...")
            time.sleep(0.3)
            log_message(app, "[DEMO] System files copied")
            set_progress(app, 0.48, "System files copied")
            time.sleep(0.3)
        else:
            rsync_rootfs_with_progress(app)

        if not DEMO_MODE:
            from installer.steps import _ensure_kernel_in_target

            _ensure_kernel_in_target(app)

        step_install_nvidia_if_needed(app)

        step_generate_fstab(app)

        step_configure_snapper(app)

        step_configure_mados_updater(app)

        set_progress(app, 0.50, "Preparing system configuration...")
        log_message(app, "Preparing system configuration...")

        if DEMO_MODE:
            log_message(
                app, "[DEMO] Would call configure-system.sh with proper arguments"
            )
            log_message(app, "[DEMO]   - Timezone setup")
            log_message(app, "[DEMO]   - Locale generation")
            log_message(app, "[DEMO]   - Hostname configuration")
            log_message(app, "[DEMO]   - User creation")
            log_message(app, "[DEMO]   - GRUB bootloader")
            log_message(app, "[DEMO]   - Graphical environment verification")
            time.sleep(1)
        else:
            import os

            script_content = build_config_script(data)
            fd = os.open(
                "/mnt/root/configure.sh", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o700
            )
            with os.fdopen(fd, "w") as f:
                f.write(script_content)

            step_copy_live_files(app)

        set_progress(app, 0.55, "Applying configurations...")
        log_message(app, "Running chroot configuration...")
        if DEMO_MODE:
            demo_steps = [
                (0.58, "Installing GRUB bootloader"),
                (0.64, "Enabling essential services..."),
                (0.70, "Rebuilding initramfs..."),
                (0.76, "Verifying graphical environment..."),
            ]
            log_message(app, "[DEMO] Simulating arch-chroot configuration...")
            for progress, desc in demo_steps:
                set_progress(app, progress, desc)
                log_message(app, f"[DEMO]   - {desc}")
                time.sleep(0.5)
        else:
            run_chroot_with_progress(app, "/mnt/root/configure.sh")

        step_create_base_snapshot(app)

        set_progress(app, 0.90, "Cleaning up...")
        log_message(app, "Cleaning up...")
        if DEMO_MODE:
            log_message(app, "[DEMO] Would remove configuration script")
            time.sleep(0.3)
            log_message(app, "[DEMO] Would unmount filesystems")
            time.sleep(0.5)
        else:
            subprocess.run(["rm", "/mnt/root/configure.sh"], check=True)
            log_message(app, "Syncing and unmounting filesystems...")
            subprocess.run(["sync"], check=False)
            subprocess.run(["umount", "-R", "/mnt"], check=False)

        set_progress(app, 1.0, "Installation complete!")
        if DEMO_MODE:
            log_message(app, "\n[OK] Demo installation completed successfully!")
            log_message(app, "\n[DEMO] No actual changes were made to your system.")
            log_message(app, "[DEMO] Set DEMO_MODE = False for real installation.")
        else:
            log_message(app, "\n[OK] Installation completed successfully!")
            log_message(app, "madOS is fully configured and ready to use.")

        GLib.idle_add(_finish_installation, app)

    except Exception as e:
        log_message(app, f"\n[ERROR] {str(e)}")
        if not DEMO_MODE:
            log_message(app, "Cleaning up after error...")
            subprocess.run(["umount", "-R", "/mnt"], capture_output=True)
        GLib.idle_add(app.install_spinner.stop)
        GLib.idle_add(_handle_installation_error, app, str(e))


def _handle_installation_error(app, error_msg):
    """Save log to file, show error dialog, then quit the installer."""
    log_path = save_log_to_file(app)
    if log_path:
        message = (
            f"{error_msg}\n\n"
            f"The installation log has been saved to:\n{log_path}\n\n"
            "The installer will now close."
        )
    else:
        message = f"{error_msg}\n\nThe installer will now close."
    show_error(app, "Installation Failed", message)
    Gtk.main_quit()
    return False


def _finish_installation(app):
    """Stop spinner, save log and move to completion page"""
    log_message(app, "QR: _finish_installation called")
    log_message(app, f"QR: DEMO_MODE={DEMO_MODE}")
    log_path = save_log_to_file(app)
    if log_path:
        log_message(app, f"\nLog saved to: {log_path}")
    app.install_spinner.stop()

    log_message(app, f"QR: about to call _add_qr_to_completion, DEMO_MODE={DEMO_MODE}")
    if not DEMO_MODE:
        _add_qr_to_completion(app, log_path)
    else:
        log_message(app, "QR: skipped due to DEMO_MODE")

    app.notebook.next_page()
    return False


def _add_qr_to_completion(app, log_path):
    """Add QR code section to completion page after installation."""
    log_message(app, f"QR: _add_qr_to_completion started, log_path={log_path}")
    log_message(app, f"QR: qr_container exists={hasattr(app, 'qr_container')}")

    try:
        import importlib.util

        scripts_dir = os.path.dirname(os.path.dirname(__file__))
        log_summary_path = os.path.join(scripts_dir, "scripts", "log-summary.py")
        spec = importlib.util.spec_from_file_location("log_summary", log_summary_path)
        log_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(log_mod)

        log_message(app, f"QR: generating from {log_path}")
        compressed, stats, error = log_mod.create_log_summary(log_path)
        if error or not compressed:
            log_message(app, f"QR: compression error={error}, compressed={compressed}")
            return

        decoder_url = log_mod.generate_decoder_url(compressed)
        qr_box = _build_qr_box(app, decoder_url, stats)

        if hasattr(app, "qr_container") and app.qr_container:
            app.qr_container.pack_start(qr_box, False, False, 0)
            app.qr_container.show_all()
            log_message(app, "QR: added to completion page")
        else:
            log_message(app, "QR: qr_container not found on app")
    except Exception as e:
        log_message(app, f"QR exception: {e}")


def _build_qr_box(app, decoder_url, stats):
    """Build the QR code GTK box."""
    import tempfile
    import urllib.request

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

    qr_image = Gtk.Image()
    try:
        import qrcode

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
    except ImportError:
        try:
            qr_api_url = (
                f"https://api.qrserver.com/v1/create-qr-code/"
                f"?size=200x200&data={urllib.parse.quote(decoder_url)}"
            )
            log_message(app, f"QR API: trying {qr_api_url[:60]}...")
            with urllib.request.urlopen(qr_api_url, timeout=10) as response:
                img_data = response.read()
            log_message(app, f"QR API: got {len(img_data)} bytes")
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                f.write(img_data)
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(f.name, 200, 200, True)
                qr_image.set_from_pixbuf(pixbuf)
                os.unlink(f.name)
            log_message(app, "QR: generated via API")
        except Exception as e:
            log_message(app, f"QR API failed: {e}")
            qr_image.set_from_icon_name("dialog-information", 6)
            qr_image.set_pixel_size(100)
    except Exception as e:
        log_message(app, f"QR local failed: {e}")
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
