"""
madOS Installer - Installation summary page
"""

from gi.repository import Gtk

from config import NORD_AURORA, NORD_FROST, NORD_SNOW_STORM

from .base import create_nav_buttons, create_page_header


def create_summary_page(app):
    """Summary page showing all selected options before install"""
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    page.get_style_context().add_class("page-container")

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    content.set_margin_start(22)
    content.set_margin_end(22)
    content.set_margin_bottom(10)

    header = create_page_header(app, app.t("summary"), 6)
    content.pack_start(header, False, False, 0)

    risk_banner = Gtk.Label()
    risk_banner.set_markup(
        f'<span size="8200" weight="bold" foreground="{NORD_AURORA["nord11"]}">'
        "CRITICAL: selected disk will be fully erased"
        "</span>"
    )
    risk_banner.set_halign(Gtk.Align.CENTER)
    risk_banner.set_margin_top(4)
    app.summary_risk_banner = risk_banner
    content.pack_start(risk_banner, False, False, 0)

    app.summary_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    app.summary_container.set_margin_top(5)
    content.pack_start(app.summary_container, True, False, 0)

    from .installation import on_start_installation

    nav = create_nav_buttons(
        app,
        lambda x: app.notebook.prev_page(),
        lambda x: on_start_installation(app),
        next_label=app.t("start_install_btn"),
        next_class="start-button",
    )
    content.pack_start(nav, False, False, 0)

    page.pack_start(content, True, True, 0)
    app.notebook.append_page(page, Gtk.Label(label="Summary"))
    app.summary_page_index = app.notebook.page_num(page)


def update_summary(app):
    """Populate summary cards"""
    for child in app.summary_container.get_children():
        app.summary_container.remove(child)

    disk = app.install_data["disk"] or "N/A"
    root_size = max(0, app.install_data["disk_size_gb"] - 1)

    if "nvme" in disk or "mmcblk" in disk:
        part_prefix = f"{disk}p"
    else:
        part_prefix = disk

    app.summary_risk_banner.set_markup(
        f'<span size="8200" weight="bold" foreground="{NORD_AURORA["nord11"]}">'
        f"CRITICAL: {disk} will be fully erased"
        "</span>"
    )

    sys_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    sys_card.get_style_context().add_class("summary-card-system")

    sys_title = Gtk.Label()
    sys_title.set_markup(
        f'<span size="8800" weight="bold" foreground="{NORD_FROST["nord8"]}">{app.t("sys_config").rstrip(":")}</span>'
    )
    sys_title.set_halign(Gtk.Align.START)
    sys_card.pack_start(sys_title, False, False, 0)

    sys_info = Gtk.Label()
    sys_info.set_markup(
        f'<span size="8000">{disk} ({root_size}GB) | {app.install_data["timezone"]} | {app.install_data["locale"]}</span>'
    )
    sys_info.set_halign(Gtk.Align.START)
    sys_card.pack_start(sys_info, False, False, 0)
    app.summary_container.pack_start(sys_card, False, False, 0)

    acct_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    acct_card.get_style_context().add_class("summary-card-account")

    acct_title = Gtk.Label()
    acct_title.set_markup(
        f'<span size="8800" weight="bold" foreground="{NORD_AURORA["nord15"]}">Account</span>'
    )
    acct_title.set_halign(Gtk.Align.START)
    acct_card.pack_start(acct_title, False, False, 0)

    acct_info = Gtk.Label()
    acct_info.set_markup(
        f'<span size="8000">{app.install_data["username"]}@{app.install_data["hostname"]}</span>'
    )
    acct_info.set_halign(Gtk.Align.START)
    acct_card.pack_start(acct_info, False, False, 0)
    app.summary_container.pack_start(acct_card, False, False, 0)

    part_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    part_card.get_style_context().add_class("summary-card-partitions")

    part_title = Gtk.Label()
    part_title.set_markup(
        f'<span size="8800" weight="bold" foreground="{NORD_AURORA["nord13"]}">{app.t("partitions")}</span>'
    )
    part_title.set_halign(Gtk.Align.START)
    part_card.pack_start(part_title, False, False, 0)

    part_info = Gtk.Label()
    part_info.set_markup(
        f'<span size="8000">'
        f"{part_prefix}1=1MiB bios_grub | "
        f"{part_prefix}2=2MiB-1GiB EFI(FAT32, esp) | "
        f"{part_prefix}3=1GiB-100% Btrfs ({root_size}GB aprox)\n"
        "Subvolumes: @, @home, @snapshots, @var_cache"
        "</span>"
    )
    part_info.set_halign(Gtk.Align.START)
    part_info.set_line_wrap(True)
    part_card.pack_start(part_info, False, False, 0)
    app.summary_container.pack_start(part_card, False, False, 0)

    sw_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    sw_card.get_style_context().add_class("summary-card-software")

    sw_title = Gtk.Label()
    sw_title.set_markup(
        f'<span size="8800" weight="bold" foreground="{NORD_AURORA["nord14"]}">{app.t("software")}</span>'
    )
    sw_title.set_halign(Gtk.Align.START)
    sw_card.pack_start(sw_title, False, False, 0)

    sw_info = Gtk.Label()
    sw_info.set_markup(
        '<span size="7800">Sway + Hyprland | Browser + Code editor | AI tools</span>'
    )
    sw_info.set_halign(Gtk.Align.START)
    sw_info.set_line_wrap(True)
    sw_card.pack_start(sw_info, False, False, 0)
    app.summary_container.pack_start(sw_card, False, False, 0)

    app.summary_container.show_all()
