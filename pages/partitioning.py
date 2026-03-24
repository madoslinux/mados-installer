"""
madOS Installer - Partitioning scheme page (Btrfs with subvolumes for OTA)
"""

from gi.repository import Gtk, GLib

from config import NORD_POLAR_NIGHT, NORD_SNOW_STORM, NORD_AURORA
from pages.base import create_page_header, create_nav_buttons


def _get_partition_prefix(disk):
    """Get partition prefix (nvme/mmcblk use 'p' separator)"""
    return f"{disk}p" if "nvme" in disk or "mmcblk" in disk else disk


def create_partitioning_page(app):
    """Btrfs partitioning with subvolumes for OTA support"""
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    page.get_style_context().add_class("page-container")

    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    content.set_margin_start(30)
    content.set_margin_end(30)
    content.set_margin_bottom(14)

    header = create_page_header(app, app.t("partitioning"), 3)
    content.pack_start(header, False, False, 0)

    disk_info = Gtk.Label()
    disk_info.set_markup(
        f'<span size="10000" foreground="{NORD_SNOW_STORM["nord4"]}">'
        f"{app.t('disk_info')} <b>{app.install_data['disk'] or 'N/A'}</b> "
        f"({app.install_data['disk_size_gb']} GB)</span>"
    )
    disk_info.set_halign(Gtk.Align.CENTER)
    disk_info.set_margin_top(6)
    disk_info.set_margin_bottom(8)
    content.pack_start(disk_info, False, False, 0)

    total_gb = app.install_data["disk_size_gb"]
    efi_gb = 1
    root_gb = total_gb - efi_gb

    disk = app.install_data["disk"]
    part_prefix = _get_partition_prefix(disk)

    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    card.get_style_context().add_class("partition-card")
    card.set_margin_bottom(8)

    title = Gtk.Label()
    title.set_markup(
        f'<span weight="bold" size="11000">{app.t("btrfs_scheme_title")}</span>'
    )
    title.set_halign(Gtk.Align.START)
    title.set_margin_start(28)
    card.pack_start(title, False, False, 0)

    desc = Gtk.Label()
    desc.set_markup(
        f'<span size="9000" foreground="{NORD_SNOW_STORM["nord4"]}">'
        f"{app.t('btrfs_scheme_desc')}</span>"
    )
    desc.set_halign(Gtk.Align.START)
    desc.set_margin_start(28)
    card.pack_start(desc, False, False, 0)

    bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    bar.set_margin_start(28)
    bar.set_margin_end(28)
    bar.set_margin_top(16)
    bar.set_size_request(400, 32)

    efi_ratio = 0.02
    efi_bar = Gtk.Label()
    efi_size_pct = int(efi_ratio * 400)
    efi_bar.set_size_request(efi_size_pct, 32)
    efi_bar.set_markup(
        f'<span size="7000" foreground="{NORD_POLAR_NIGHT["nord0"]}"> {app.t("efi_label")} {efi_gb}GB </span>'
    )
    efi_bar.get_style_context().add_class("partition-bar-efi")
    bar.pack_start(efi_bar, False, False, 0)

    root_bar = Gtk.Label()
    root_bar.set_markup(
        f'<span size="7000" foreground="{NORD_POLAR_NIGHT["nord0"]}">'
        f" Btrfs ({root_gb}GB) </span>"
    )
    root_bar.get_style_context().add_class("partition-bar-root-only")
    bar.pack_start(root_bar, True, True, 0)

    card.pack_start(bar, False, False, 0)

    partitions_labels = Gtk.Label()
    partitions_labels.set_markup(
        f'<span size="8500" foreground="{NORD_AURORA["nord14"]}">'
        f"  {part_prefix}1  BIOS     1 MB      ({app.t('bootable')})\n"
        f"  {part_prefix}2  {app.t('efi_label')}      {efi_gb} GB    (FAT32)\n"
        f"  {part_prefix}3  {app.t('root_label')}     {root_gb} GB    (Btrfs)</span>"
    )
    partitions_labels.set_halign(Gtk.Align.START)
    partitions_labels.set_margin_start(28)
    partitions_labels.set_margin_top(12)
    card.pack_start(partitions_labels, False, False, 0)

    subvol_title = Gtk.Label()
    subvol_title.set_markup(
        f'<span weight="bold" size="9000" foreground="{NORD_SNOW_STORM["nord4"]}">'
        f"  {app.t('btrfs_subvolumes_title')}</span>"
    )
    subvol_title.set_halign(Gtk.Align.START)
    subvol_title.set_margin_start(28)
    subvol_title.set_margin_top(12)
    card.pack_start(subvol_title, False, False, 0)

    subvol_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    subvol_bar.set_margin_start(28)
    subvol_bar.set_margin_end(28)
    subvol_bar.set_margin_top(8)

    subvol_at = Gtk.Label()
    subvol_at.set_size_request(240, 24)
    subvol_at.set_markup(
        f'<span size="7000" foreground="{NORD_POLAR_NIGHT["nord0"]}"> @ </span>'
    )
    subvol_at.get_style_context().add_class("partition-bar-root")
    subvol_bar.pack_start(subvol_at, False, False, 0)

    subvol_home = Gtk.Label()
    subvol_home.set_markup(
        f'<span size="7000" foreground="{NORD_POLAR_NIGHT["nord0"]}"> @home </span>'
    )
    subvol_home.get_style_context().add_class("partition-bar-home")
    subvol_bar.pack_start(subvol_home, False, False, 0)

    subvol_snap = Gtk.Label()
    subvol_snap.set_markup(
        f'<span size="7000" foreground="{NORD_POLAR_NIGHT["nord0"]}"> @snapshots </span>'
    )
    subvol_snap.get_style_context().add_class("partition-bar-snapshots")
    subvol_bar.pack_start(subvol_snap, True, True, 0)

    card.pack_start(subvol_bar, False, False, 0)

    subvol_labels = Gtk.Label()
    subvol_labels.set_markup(
        f'<span size="8000" foreground="{NORD_SNOW_STORM["nord4"]}">'
        f"  @           → /                (root system)\n"
        f"  @home       → /home            (user data)\n"
        f"  @snapshots  → /.snapshots      (OTA rollback)</span>"
    )
    subvol_labels.set_halign(Gtk.Align.START)
    subvol_labels.set_margin_start(28)
    subvol_labels.set_margin_top(6)
    card.pack_start(subvol_labels, False, False, 0)

    content.pack_start(card, False, False, 0)

    nav = create_nav_buttons(
        app, lambda x: app.notebook.prev_page(), lambda x: app.notebook.next_page()
    )
    content.pack_start(nav, False, False, 0)

    scroll.add(content)
    page.pack_start(scroll, True, True, 0)
    app.notebook.append_page(page, Gtk.Label(label="Partitioning"))
