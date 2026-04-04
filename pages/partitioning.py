"""
madOS Installer - Partitioning scheme page (Btrfs with subvolumes for OTA)
"""

from gi.repository import GLib, Gtk

from config import NORD_AURORA, NORD_POLAR_NIGHT, NORD_SNOW_STORM

from .base import create_nav_buttons, create_page_header


def _get_partition_prefix(disk):
    """Get partition prefix (nvme/mmcblk use 'p' separator)"""
    if disk is None:
        return ""
    return f"{disk}p" if "nvme" in disk or "mmcblk" in disk else disk


def refresh_partitioning_content(app):
    """Refresh partitioning page content with current install_data"""
    if not hasattr(app, "_partitioning_disk_info"):
        return

    total_gb = app.install_data.get("disk_size_gb") or 0
    efi_gb = 1
    root_gb = max(0, total_gb - efi_gb)
    disk_size_display = f"{total_gb} GB" if total_gb > 0 else "N/A"
    root_display = f"{root_gb}GB" if root_gb > 0 else "remaining"

    disk = app.install_data.get("disk")
    part_prefix = _get_partition_prefix(disk)

    app._partitioning_disk_info.set_markup(
        f'<span size="10000" foreground="{NORD_SNOW_STORM["nord4"]}">'
        f"{app.t('disk_info')} <b>{disk or 'N/A'}</b> "
        f"({disk_size_display})</span>"
    )

    app._partitioning_root_bar.set_markup(
        f'<span size="7000" foreground="{NORD_POLAR_NIGHT["nord0"]}">'
        f" Btrfs ({root_display}) </span>"
    )

    app._partitioning_labels.set_markup(
        f'<span size="8500" foreground="{NORD_AURORA["nord14"]}">'
        f"  {part_prefix}1  BIOS     1 MB      ({app.t('bootable')})\n"
        f"  {part_prefix}2  {app.t('efi_label')}      {efi_gb} GB    (FAT32)\n"
        f"  {part_prefix}3  {app.t('root_label')}     {root_display}    (Btrfs)</span>"
    )


def create_partitioning_page(app):
    """Btrfs partitioning with subvolumes for OTA support"""
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    page.get_style_context().add_class("page-container")

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    content.set_margin_start(22)
    content.set_margin_end(22)
    content.set_margin_bottom(10)

    header = create_page_header(app, app.t("partitioning"), 3)
    content.pack_start(header, False, False, 0)

    disk_info = Gtk.Label()
    disk_info.set_halign(Gtk.Align.CENTER)
    disk_info.set_margin_top(4)
    disk_info.set_margin_bottom(6)
    app._partitioning_disk_info = disk_info
    content.pack_start(disk_info, False, False, 0)

    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    card.get_style_context().add_class("partition-card")
    card.set_margin_bottom(6)

    title = Gtk.Label()
    title.set_markup(
        f'<span weight="bold" size="10000">{app.t("btrfs_scheme_title")}</span>'
    )
    title.set_halign(Gtk.Align.START)
    title.set_margin_start(28)
    card.pack_start(title, False, False, 0)

    desc = Gtk.Label()
    desc.set_markup(
        f'<span size="8200" foreground="{NORD_SNOW_STORM["nord4"]}">'
        f"{app.t('btrfs_scheme_desc')}</span>"
    )
    desc.set_halign(Gtk.Align.START)
    desc.set_margin_start(28)
    card.pack_start(desc, False, False, 0)

    bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    bar.set_margin_start(28)
    bar.set_margin_end(28)
    bar.set_margin_top(10)
    bar.set_size_request(400, 24)

    efi_ratio = 0.02
    efi_bar = Gtk.Label()
    efi_size_pct = int(efi_ratio * 400)
    efi_bar.set_size_request(efi_size_pct, 24)
    efi_bar.set_markup(
        f'<span size="7000" foreground="{NORD_POLAR_NIGHT["nord0"]}"> {app.t("efi_label")} 1GB </span>'
    )
    efi_bar.get_style_context().add_class("partition-bar-efi")
    bar.pack_start(efi_bar, False, False, 0)

    root_bar = Gtk.Label()
    app._partitioning_root_bar = root_bar
    root_bar.get_style_context().add_class("partition-bar-root-only")
    bar.pack_start(root_bar, True, True, 0)

    card.pack_start(bar, False, False, 0)

    partitions_labels = Gtk.Label()
    partitions_labels.set_halign(Gtk.Align.START)
    partitions_labels.set_margin_start(28)
    partitions_labels.set_margin_top(8)
    app._partitioning_labels = partitions_labels
    card.pack_start(partitions_labels, False, False, 0)

    content.pack_start(card, False, False, 0)

    nav = create_nav_buttons(
        app, lambda x: app.notebook.prev_page(), lambda x: app.notebook.next_page()
    )
    content.pack_start(nav, False, False, 0)

    page.pack_start(content, True, True, 0)
    app.notebook.append_page(page, Gtk.Label(label="Partitioning"))

    refresh_partitioning_content(app)
