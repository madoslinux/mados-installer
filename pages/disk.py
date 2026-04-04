"""
madOS Installer - Disk selection page
"""

import subprocess

from gi.repository import Gtk

from config import (
    DEMO_MODE,
    MIN_DISK_SIZE_GB,
    NORD_AURORA,
    NORD_FROST,
    NORD_POLAR_NIGHT,
    NORD_SNOW_STORM,
)
from utils import show_error, style_dialog

from .base import create_nav_buttons, create_page_header


def create_disk_page(app):
    """Disk selection page with clickable button cards"""
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    page.get_style_context().add_class("page-container")

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    content.set_margin_start(22)
    content.set_margin_end(22)
    content.set_margin_bottom(10)

    # Page header
    header = create_page_header(app, app.t("select_disk"), 2)
    content.pack_start(header, False, False, 0)

    # Warning banner
    warn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    warn_box.get_style_context().add_class("warning-banner")
    warn_box.set_margin_top(5)
    warn_box.set_margin_bottom(6)

    warn_text = Gtk.Label()
    warn_text.set_markup(
        f'<span weight="bold" foreground="{NORD_AURORA["nord11"]}">  {app.t("warning")}</span>'
    )
    warn_text.set_halign(Gtk.Align.CENTER)
    warn_box.pack_start(warn_text, True, True, 0)
    content.pack_start(warn_box, False, False, 0)

    # Disk buttons container
    app.disk_buttons_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    app.disk_buttons_box.set_margin_top(2)
    app.disk_buttons = []
    app.selected_disk_info = None

    app.no_disks_label = Gtk.Label()
    app.no_disks_label.set_markup(
        f'<span size="11000" foreground="{NORD_POLAR_NIGHT["nord3"]}">'
        f"{app.t('no_disks_available')}</span>"
    )
    app.no_disks_label.set_halign(Gtk.Align.CENTER)
    app.no_disks_label.set_margin_top(12)
    app.no_disks_label.set_no_show_all(True)
    app.disk_buttons_box.pack_start(app.no_disks_label, False, False, 0)

    _populate_disks(app)

    content.pack_start(app.disk_buttons_box, False, False, 0)

    # Navigation
    nav = create_nav_buttons(
        app, lambda x: app.notebook.prev_page(), lambda x: _on_disk_next(app)
    )
    content.pack_start(nav, False, False, 0)

    page.pack_start(content, True, True, 0)
    app.notebook.append_page(page, Gtk.Label(label="Disk"))


def _get_disk_type(name, model=""):
    """Determine disk type from name and model."""
    name_lower = name.lower()
    model_lower = model.lower()
    if "nvme" in name_lower:
        return "NVMe"
    if "ssd" in model_lower or "flash" in model_lower:
        return "SSD"
    return "HDD"


def _get_disk_list():
    """Get list of available disks (excluding live USB and zram)."""
    if DEMO_MODE:
        return [
            ("sda", "256G", "Samsung SSD 860 EVO"),
            ("nvme0n1", "512G", "WD Black SN750"),
            ("sdb", "1T", "Seagate BarraCuda HDD"),
        ]

    disk_list = []
    result = subprocess.run(
        ["lsblk", "-d", "-n", "-o", "NAME,SIZE,TYPE,MODEL"],
        capture_output=True,
        text=True,
    )

    root_disk = None
    root_result = subprocess.run(
        ["lsblk", "-n", "-o", "PKNAME", "/"],
        capture_output=True,
        text=True,
    )
    if root_result.returncode == 0 and root_result.stdout.strip():
        root_disk = root_result.stdout.strip()

    for line in result.stdout.splitlines():
        if "disk" not in line:
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        name = parts[0]
        size = parts[1]
        model = " ".join(parts[3:]) if len(parts) > 3 else "Unknown disk"

        if name.startswith("zram") or name.startswith("fd"):
            continue

        if name == root_disk:
            continue

        disk_list.append((name, size, model))

    return disk_list


def _create_disk_badge(disk_type):
    """Create disk type badge widget."""
    badge = Gtk.Label()
    badge.get_style_context().add_class(f"disk-type-{disk_type.lower()}")
    badge.set_size_request(50, -1)

    colors = {
        "NVMe": NORD_FROST["nord8"],
        "SSD": NORD_AURORA["nord14"],
        "HDD": NORD_SNOW_STORM["nord4"],
    }
    badge.set_markup(
        f'<span size="9000" weight="bold" foreground="{colors.get(disk_type, colors["HDD"])}">{disk_type}</span>'
    )
    return badge


def _create_disk_button(name, size, model, on_click):
    """Create a disk selection button widget."""
    btn = Gtk.Button()
    btn.get_style_context().add_class("disk-card")
    btn.connect("clicked", on_click, name, size)

    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    hbox.set_margin_start(12)
    hbox.set_margin_end(12)
    hbox.set_margin_top(6)
    hbox.set_margin_bottom(6)

    disk_type = _get_disk_type(name, model)
    hbox.pack_start(_create_disk_badge(disk_type), False, False, 0)

    info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)

    dev_label = Gtk.Label()
    dev_label.set_markup(
        f'<span weight="bold" size="10000" foreground="{NORD_SNOW_STORM["nord6"]}">'
        f"/dev/{name}</span>"
    )
    dev_label.set_halign(Gtk.Align.START)
    info_box.pack_start(dev_label, False, False, 0)

    model_label = Gtk.Label()
    model_label.set_markup(
        f'<span size="8800" foreground="{NORD_SNOW_STORM["nord4"]}">{model}</span>'
    )
    model_label.set_halign(Gtk.Align.START)
    info_box.pack_start(model_label, False, False, 0)
    hbox.pack_start(info_box, True, True, 0)

    size_label = Gtk.Label()
    size_label.set_markup(
        f'<span weight="bold" size="12000" foreground="{NORD_FROST["nord8"]}">{size}</span>'
    )
    hbox.pack_start(size_label, False, False, 0)

    btn.add(hbox)
    return btn


def _populate_disks(app):
    """Populate disk list with clickable button cards."""
    for child in app.disk_buttons_box.get_children():
        if child != app.no_disks_label:
            app.disk_buttons_box.remove(child)
    app.disk_buttons = []
    app.selected_disk_info = None

    def on_disk_click(button, name, size):
        for btn in app.disk_buttons:
            ctx = btn.get_style_context()
            ctx.remove_class("disk-card-selected")
            ctx.add_class("disk-card")
        ctx = button.get_style_context()
        ctx.remove_class("disk-card")
        ctx.add_class("disk-card-selected")
        app.selected_disk_info = {"name": name, "size": size}

    try:
        disks = _get_disk_list()
        if not disks:
            app.no_disks_label.show()
        else:
            app.no_disks_label.hide()
            for name, size, model in disks:
                btn = _create_disk_button(name, size, model, on_disk_click)
                app.disk_buttons.append(btn)
                app.disk_buttons_box.pack_start(btn, False, False, 0)
    except Exception as e:
        print(f"Error listing disks: {e}")
        app.no_disks_label.show()


def _on_disk_next(app):
    """Handle disk selection next"""
    if app.selected_disk_info is None:
        show_error(app, "No Disk Selected", "Please select a disk to continue.")
        return

    name = app.selected_disk_info["name"]
    size_str = app.selected_disk_info["size"]
    app.install_data["disk"] = f"/dev/{name}"

    # Parse disk size
    try:
        size_str = size_str.strip()
        if size_str.endswith("G") or size_str.endswith("GB"):
            app.install_data["disk_size_gb"] = int(float(size_str.rstrip("GB")))
        elif size_str.endswith("T") or size_str.endswith("TB"):
            app.install_data["disk_size_gb"] = int(float(size_str.rstrip("TB")) * 1024)
        elif size_str.endswith("M") or size_str.endswith("MB"):
            app.install_data["disk_size_gb"] = max(
                1, int(float(size_str.rstrip("MB")) / 1024)
            )
        else:
            bytes_val = int(size_str)
            app.install_data["disk_size_gb"] = max(1, bytes_val // (1024**3))
    except (ValueError, IndexError):
        app.install_data["disk_size_gb"] = 120

    if app.install_data["disk_size_gb"] < MIN_DISK_SIZE_GB:
        show_error(
            app,
            "Disk Too Small",
            f"madOS requires at least {MIN_DISK_SIZE_GB} GB. "
            f"The selected disk is only {app.install_data['disk_size_gb']} GB.",
        )
        return

    if DEMO_MODE:
        dialog = Gtk.MessageDialog(
            transient_for=app,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="DEMO MODE",
        )
        dialog.format_secondary_text(
            f"Selected disk: {app.install_data['disk']}\n\n"
            "In real mode, all data would be erased.\n"
            "Demo mode: No actual changes will be made."
        )
        dialog.set_modal(True)
        dialog.set_keep_above(True)
        style_dialog(dialog)
        dialog.run()
        dialog.destroy()
        app.notebook.next_page()
    else:
        dialog = Gtk.MessageDialog(
            transient_for=app,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text="CONFIRM DISK ERASURE",
        )
        dialog.format_secondary_text(
            f"ALL DATA on {app.install_data['disk']} will be PERMANENTLY ERASED!\n\n"
            "Are you absolutely sure you want to continue?"
        )
        dialog.set_modal(True)
        dialog.set_keep_above(True)
        style_dialog(dialog)
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            app.notebook.next_page()
