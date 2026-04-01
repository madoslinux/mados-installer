"""
madOS Installer - Installation steps
"""

import glob as globmod
import os
import re
import subprocess
import time

from config import (
    DEMO_MODE,
    RSYNC_EXCLUDES,
    POST_COPY_CLEANUP,
    ARCHISO_PACKAGES,
    PACKAGES_NVIDIA,
)
from utils import log_message, set_progress

MNT_USR_LOCAL_BIN = "/mnt/usr/local/bin/"
SKEL_DIR = "/mnt/etc/skel/"


def _detect_nvidia_gpu():
    """Detect if NVIDIA GPU is present using lspci."""
    try:
        result = subprocess.run(["lspci"], capture_output=True, text=True, check=False)
        return "nvidia" in result.stdout.lower()
    except Exception:
        return False


def _command_exists(cmd):
    """Check if a command exists in PATH."""
    result = subprocess.run(["which", cmd], capture_output=True, text=True)
    return result.returncode == 0


def _check_required_commands(app):
    """Verify all required commands exist before starting installation."""
    required = ["mkfs.fat", "mkfs.btrfs", "btrfs", "parted", "genfstab"]
    missing = []
    for cmd in required:
        if not _command_exists(cmd):
            missing.append(cmd)
    if missing:
        error_msg = f"Missing required commands: {', '.join(missing)}"
        log_message(app, f"ERROR: {error_msg}")
        raise RuntimeError(error_msg)
    log_message(app, "All required commands verified")


def _get_partition_prefix(disk):
    """Get partition prefix (nvme/mmcblk use 'p' separator)"""
    return f"{disk}p" if "nvme" in disk or "mmcblk" in disk else disk


def _copy_item(src, dst):
    """Copy file or directory if it exists."""
    if not os.path.exists(src):
        print(f"  WARNING: {src} not found, skipping copy")
        return
    result = subprocess.run(["cp", "-a", src, dst], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  WARNING: failed to copy {src} → {dst}: {result.stderr.strip()}")


def _ensure_kernel_in_target(app):
    """Ensure /mnt/boot/vmlinuz-linux-mados-zen exists before entering the chroot."""
    target_kernel = "/mnt/boot/vmlinuz-linux-mados-zen"

    # Debug: list what exists in live system /boot
    import glob
    log_message(app, "  DEBUG: Checking live system /boot:")
    for f in sorted(glob.glob("/boot/vmlinuz*")):
        log_message(app, f"    {f}")
    log_message(app, "  DEBUG: Checking live system /lib/modules/:")
    for d in sorted(glob.glob("/lib/modules/*")):
        log_message(app, f"    {d}")
    log_message(app, "  DEBUG: Checking /usr/lib/modules/*/vmlinuz:")
    for f in sorted(glob.glob("/usr/lib/modules/*/vmlinuz")):
        log_message(app, f"    {f}")

    if (
        os.path.isfile(target_kernel)
        and os.access(target_kernel, os.R_OK)
        and os.path.getsize(target_kernel) > 0
    ):
        log_message(app, "  Kernel already exists in target /boot")
        return

    log_message(app, "  Kernel not found in target /boot, copying from live system...")

    # First, try madOS kernel in /boot
    if os.path.isfile("/boot/vmlinuz-linux-mados-zen") and os.access(
        "/boot/vmlinuz-linux-mados-zen", os.R_OK
    ):
        subprocess.run(
            ["cp", "/boot/vmlinuz-linux-mados-zen", target_kernel], check=True
        )
        log_message(app, "  Copied kernel from /boot/vmlinuz-linux-mados-zen")
        return

    # Try modules directory - ONLY copy madOS kernels (filter by "mados-zen")
    for vmlinuz in sorted(globmod.glob("/usr/lib/modules/*/vmlinuz"), reverse=True):
        if "mados-zen" in vmlinuz and os.path.isfile(vmlinuz) and os.access(vmlinuz, os.R_OK):
            subprocess.run(["cp", vmlinuz, target_kernel], check=True)
            log_message(app, f"  Copied kernel from {vmlinuz}")
            return

    # Fallback: try to find kernel image in /lib/modules/*/vmlinuz (Arch standard location)
    for vmlinuz in sorted(globmod.glob("/lib/modules/*/vmlinuz"), reverse=True):
        if "mados-zen" in vmlinuz and os.path.isfile(vmlinuz) and os.access(vmlinuz, os.R_OK):
            subprocess.run(["cp", vmlinuz, target_kernel], check=True)
            log_message(app, f"  Copied kernel from {vmlinuz}")
            return

    # Try /boot/vmlinuz-linux as last resort (only if it contains "mados-zen")
    # Skip if it doesn't exist or is a non-mados kernel
    if os.path.isfile("/boot/vmlinuz-linux") and os.access(
        "/boot/vmlinuz-linux", os.R_OK
    ):
        # Only copy if it's the madOS kernel (not standard Arch linux)
        with open("/boot/vmlinuz-linux", "rb") as f:
            header = f.read(512)
            # Check for madOS kernel signature or skip
            if b"mados" in header.lower() or b"linux-mados" in header.lower():
                subprocess.run(["cp", "/boot/vmlinuz-linux", target_kernel], check=True)
                log_message(app, "  Copied kernel from /boot/vmlinuz-linux (madOS)")
                return
            else:
                log_message(app, "  Skipping /boot/vmlinuz-linux (not a madOS kernel)")
                # Don't fall through to other options - raise error instead
                raise RuntimeError("madOS kernel not found in live system")

    # Try /mnt modules directory - ONLY copy madOS kernels
    for vmlinuz in sorted(globmod.glob("/mnt/usr/lib/modules/*/vmlinuz"), reverse=True):
        if "mados-zen" in vmlinuz and os.path.isfile(vmlinuz) and os.access(vmlinuz, os.R_OK):
            subprocess.run(["cp", vmlinuz, target_kernel], check=True)
            log_message(app, f"  Copied kernel from {vmlinuz}")
            return

    log_message(
        app,
        "  ERROR: Could not find madOS kernel (mados-zen) in live system",
    )
    raise RuntimeError("madOS kernel not found")


def step_partition_disk(app, disk, disk_size_gb):
    """Step 1: Partition the disk. Returns (boot_part, root_part)."""
    set_progress(app, 0.05, "Partitioning disk...")
    log_message(app, f"Partitioning {disk}...")

    if DEMO_MODE:
        for msg in [
            "unmount/swapoff",
            "wipefs",
            "parted mklabel gpt",
            "parted mkpart bios_boot",
            "parted set bios_grub",
            "parted mkpart EFI",
            "parted set esp",
        ]:
            log_message(app, f"[DEMO] Simulating {msg}...")
            time.sleep(0.3)
    else:
        log_message(app, f"Unmounting existing partitions on {disk}...")
        for part in globmod.glob(f"{disk}[0-9]*") + globmod.glob(f"{disk}p[0-9]*"):
            subprocess.run(["swapoff", part], stderr=subprocess.DEVNULL, check=False)
            subprocess.run(
                ["umount", "-l", part], stderr=subprocess.DEVNULL, check=False
            )
        time.sleep(1)
        subprocess.run(["sgdisk", "--zap-all", disk], check=False)
        subprocess.run(["wipefs", "-a", "-f", disk], check=True)
        subprocess.run(["parted", "-s", disk, "mklabel", "gpt"], check=True)
        subprocess.run(
            ["parted", "-s", disk, "mkpart", "bios_boot", "1MiB", "2MiB"], check=True
        )
        subprocess.run(
            ["parted", "-s", disk, "set", "1", "bios_grub", "on"], check=True
        )
        subprocess.run(
            ["parted", "-s", disk, "mkpart", "EFI", "fat32", "2MiB", "1GiB"], check=True
        )
        subprocess.run(["parted", "-s", disk, "set", "2", "esp", "on"], check=True)

    _create_root_partition(app, disk)

    if not DEMO_MODE:
        log_message(app, "Waiting for partition devices...")
        subprocess.run(["partprobe", disk], check=False)
        subprocess.run(["udevadm", "settle", "--timeout=10"], check=False)
        time.sleep(2)
    else:
        time.sleep(0.5)

    part_prefix = _get_partition_prefix(disk)
    return (
        f"{part_prefix}2",
        f"{part_prefix}3",
    )


def _create_root_partition(app, disk):
    """Create root partition using entire disk (Btrfs for OTA snapshots)."""
    if DEMO_MODE:
        log_message(app, "[DEMO] Simulating parted mkpart root btrfs 1GiB-100%...")
        time.sleep(0.5)
    else:
        result = subprocess.run(
            ["parted", "-s", disk, "mkpart", "root", "btrfs", "1GiB", "100%"],
            capture_output=True,
            text=True,
            check=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create root partition: {result.stderr}")
        log_message(app, "Created root partition")

        part_prefix = _get_partition_prefix(disk)
        root_part = f"{part_prefix}3"

        for _ in range(10):
            if os.path.exists(root_part):
                break
            subprocess.run(["udevadm", "settle", "--timeout=1"], check=False)
            time.sleep(0.5)
        else:
            raise RuntimeError(f"Partition {root_part} not found after creation")

        log_message(app, f"Verified partition {root_part} exists")


def step_format_partitions(app, boot_part, root_part):
    """Step 2: Format partitions."""
    set_progress(app, 0.15, "Formatting partitions...")
    log_message(app, "Formatting partitions...")

    if DEMO_MODE:
        _format_partitions_demo(app, boot_part, root_part)
    else:
        _format_partitions_real(boot_part, root_part)


def _format_partitions_demo(app, boot_part, root_part):
    """Demo mode partition formatting."""
    log_message(app, f"[DEMO] Simulating mkfs.fat {boot_part}...")
    time.sleep(0.5)
    log_message(app, f"[DEMO] Simulating mkfs.btrfs -f {root_part}...")
    time.sleep(0.5)


def _format_partitions_real(boot_part, root_part):
    """Real partition formatting with Btrfs for OTA snapshots."""
    for part_name, part_dev in [("EFI", boot_part), ("root", root_part)]:
        if not os.path.exists(part_dev):
            raise RuntimeError(
                f"Partition device {part_dev} ({part_name}) does not exist!"
            )
    subprocess.run(["mkfs.fat", "-F32", boot_part], check=True)
    subprocess.run(["mkfs.btrfs", "-f", root_part], check=True)


def step_create_btrfs_subvolumes(app, root_part):
    """Create Btrfs subvolumes for OTA support."""
    set_progress(app, 0.18, "Creating Btrfs subvolumes...")
    log_message(app, "Creating Btrfs subvolumes...")

    if DEMO_MODE:
        log_message(app, "[DEMO] Simulating btrfs subvolume create @ ...")
        time.sleep(0.3)
        log_message(app, "[DEMO] Simulating btrfs subvolume create @home ...")
        time.sleep(0.3)
        log_message(app, "[DEMO] Simulating btrfs subvolume create @snapshots ...")
        time.sleep(0.3)
        return

    mount_point = "/mnt/btrfs_temp"
    os.makedirs(mount_point, exist_ok=True)

    try:
        subprocess.run(["mount", root_part, mount_point], check=True)
        time.sleep(1)

        subprocess.run(
            ["btrfs", "subvolume", "create", f"{mount_point}/@"],
            check=True,
        )
        log_message(app, "Created subvolume @")

        subprocess.run(
            ["btrfs", "subvolume", "create", f"{mount_point}/@home"],
            check=True,
        )
        log_message(app, "Created subvolume @home")

        subprocess.run(
            ["btrfs", "subvolume", "create", f"{mount_point}/@snapshots"],
            check=True,
        )
        log_message(app, "Created subvolume @snapshots")

        subprocess.run(["umount", mount_point], check=True)
    except subprocess.CalledProcessError as e:
        log_message(app, f"Error creating subvolumes: {e}")
        raise
    finally:
        if os.path.exists(mount_point):
            os.rmdir(mount_point)


def step_configure_snapper(app):
    """Configure snapper for automatic snapshots."""
    set_progress(app, 0.72, "Configuring snapper...")
    log_message(app, "Configuring snapper for OTA updates...")

    if DEMO_MODE:
        log_message(app, "[DEMO] Simulating snapper configuration...")
        time.sleep(0.5)
        return

    snapper_config = """SUBVOLUME="/"
ALLOW_USERS=""
ALLOW_GROUPS=""
SYNC_ACL="no"
BACKGROUND_COMPARISON="no"
TIMELINE_CREATE="no"
TIMELINE_LIMIT_HOURLY="0"
TIMELINE_LIMIT_DAILY="0"
TIMELINE_LIMIT_WEEKLY="0"
TIMELINE_LIMIT_MONTHLY="0"
TIMELINE_LIMIT_YEARLY="0"
NUMBER_LIMIT="1"
NUMBER_LIMIT_IMPORTANT="1"
"""

    try:
        subprocess.run(["mkdir", "-p", "/mnt/etc/snapper/configs"], check=True)
        with open("/mnt/etc/snapper/configs/root", "w") as f:
            f.write(snapper_config)
        log_message(app, "Configured snapper for root subvolume")

        subprocess.run(
            ["chmod", "644", "/mnt/etc/snapper/configs/root"],
            check=False,
        )
    except Exception as e:
        log_message(app, f"Warning: snapper configuration failed: {e}")


def step_configure_mados_updater(app):
    """Install and configure mados-updater in target system."""
    set_progress(app, 0.73, "Configuring mados-updater...")
    log_message(app, "Installing mados-updater...")

    if DEMO_MODE:
        log_message(app, "[DEMO] Simulating mados-updater installation...")
        time.sleep(0.5)
        return

    try:
        subprocess.run(["mkdir", "-p", "/mnt/etc"], check=True)
        with open("/mnt/etc/mados-updater.conf", "w") as f:
            f.write("[updater]\n")
            f.write("repo_url = https://github.com/madkoding/mados-updates\n")
            f.write("channel = stable\n")
            f.write("check_interval = 3600\n")
            f.write("auto_download = false\n")
            f.write("auto_install = false\n")
            f.write("\n[notifications]\n")
            f.write("enabled = true\n")
            f.write("use_dialog = true\n")

        with open("/mnt/etc/mados-version", "w") as f:
            f.write("1.0.0\n")

        subprocess.run(
            ["chmod", "644", "/mnt/etc/mados-updater.conf"],
            check=False,
        )

        log_message(app, "Configured mados-updater")
    except Exception as e:
        log_message(app, f"Warning: mados-updater configuration failed: {e}")


def step_create_base_snapshot(app):
    """Create initial base snapshot for rollback capability."""
    set_progress(app, 0.88, "Creating base snapshot...")
    log_message(app, "Creating base snapshot for rollback...")

    if DEMO_MODE:
        log_message(app, "[DEMO] Simulating btrfs snapshot creation...")
        time.sleep(0.5)
        return

    try:
        os.makedirs("/mnt/.snapshots", exist_ok=True)
        result = subprocess.run(
            [
                "mount",
                "-o",
                "subvol=@snapshots",
                app.install_data["root_part"],
                "/mnt/.snapshots",
            ],
            capture_output=True,
        )
        if result.returncode != 0:
            log_message(
                app, f"Warning: Could not mount @snapshots: {result.stderr.decode()}"
            )
            log_message(app, "Creating snapshot at top-level instead...")
            subprocess.run(
                [
                    "btrfs",
                    "subvolume",
                    "snapshot",
                    "/mnt",
                    "/mnt/snapshots/base-install",
                ],
                check=True,
            )
        else:
            subprocess.run(
                [
                    "btrfs",
                    "subvolume",
                    "snapshot",
                    "/mnt",
                    "/mnt/.snapshots/base-install",
                ],
                check=True,
            )
            subprocess.run(["umount", "/mnt/.snapshots"], check=False)

        log_message(app, "Created base snapshot for rollback capability")
    except subprocess.CalledProcessError as e:
        log_message(app, f"Warning: Failed to create base snapshot: {e}")


def step_mount_filesystems(app, boot_part, root_part):
    """Step 3: Mount filesystems with Btrfs subvolume support."""
    set_progress(app, 0.20, "Mounting filesystems...")
    log_message(app, "Mounting filesystems...")

    if DEMO_MODE:
        log_message(app, "[DEMO] Simulating mount -o subvol=@ btrfs /mnt...")
        time.sleep(0.5)
        log_message(app, "[DEMO] Simulating mkdir /mnt/boot...")
        time.sleep(0.3)
        log_message(app, f"[DEMO] Simulating mount {boot_part} /mnt/boot...")
        time.sleep(0.5)
        log_message(app, "[DEMO] Simulating mount -o subvol=@home btrfs /mnt/home...")
        time.sleep(0.3)
    else:
        subprocess.run(["mount", "-o", "subvol=@", root_part, "/mnt"], check=True)
        subprocess.run(["mkdir", "-p", "/mnt/boot"], check=True)
        subprocess.run(["mount", boot_part, "/mnt/boot"], check=True)
        subprocess.run(["mkdir", "-p", "/mnt/home"], check=True)
        subprocess.run(
            ["mount", "-o", "subvol=@home", root_part, "/mnt/home"],
            check=True,
        )


def step_copy_live_files(app):
    """Step 6: Copy files from live ISO to installed system."""
    set_progress(app, 0.51, "Copying boot splash assets...")
    log_message(app, "Copying Plymouth boot splash assets...")
    subprocess.run(["mkdir", "-p", "/mnt/usr/share/plymouth/themes/mados"], check=True)
    _copy_item(
        "/usr/share/plymouth/themes/mados/logo.png",
        "/mnt/usr/share/plymouth/themes/mados/",
    )
    _copy_item(
        "/usr/share/plymouth/themes/mados/dot.png",
        "/mnt/usr/share/plymouth/themes/mados/",
    )

    set_progress(app, 0.52, "Copying desktop configuration files...")
    log_message(app, "Copying desktop configuration files...")
    for item in [
        ".config",
        "Pictures",
        ".bash_profile",
        ".zshrc",
        ".bashrc",
        ".gtkrc-2.0",
    ]:
        _copy_item(f"/etc/skel/{item}", f"{SKEL_DIR}{item}")

    subprocess.run(["mkdir", "-p", "/mnt/etc/gtk-3.0"], check=False)
    _copy_item("/etc/gtk-3.0/settings.ini", "/mnt/etc/gtk-3.0/")

    _copy_item("/usr/share/themes/Nordic", "/mnt/usr/share/themes/")
    _copy_item("/etc/skel/.oh-my-zsh", SKEL_DIR)

    for binary in ["opencode", "ollama"]:
        _copy_item(f"/usr/local/bin/{binary}", MNT_USR_LOCAL_BIN)

    step_copy_scripts(app)
    step_copy_installer_scripts(app)
    step_copy_desktop_files(app)


def step_copy_scripts(app):
    """Copy system scripts and launchers."""
    set_progress(app, 0.53, "Copying system scripts...")
    log_message(app, "Copying system scripts...")
    subprocess.run(["mkdir", "-p", "/mnt/usr/local/bin"], check=False)

    scripts = [
        "detect-legacy-hardware",
        "cage-greeter",
        "sway-session",
        "hyprland-session",
        "start-hyprland",
        "select-compositor",
        "mados-audio-quality.sh",
    ]
    for script in scripts:
        _copy_item(f"/usr/local/bin/{script}", MNT_USR_LOCAL_BIN)

    for launcher in [
        "mados-photo-viewer",
        "mados-pdf-viewer",
        "mados-equalizer",
        "mados-debug",
    ]:
        _copy_item(f"/usr/local/bin/{launcher}", MNT_USR_LOCAL_BIN)

    subprocess.run(["mkdir", "-p", "/mnt/usr/local/lib"], check=False)
    for lib in ["mados_photo_viewer", "mados_pdf_viewer", "mados_equalizer"]:
        _copy_item(f"/usr/local/lib/{lib}", "/mnt/usr/local/lib/")

    for script in scripts + [
        "mados-photo-viewer",
        "mados-pdf-viewer",
        "mados-equalizer",
        "mados-debug",
    ]:
        subprocess.run(["chmod", "+x", f"{MNT_USR_LOCAL_BIN}{script}"], check=False)


def step_copy_installer_scripts(app):
    """Copy installer scripts to target for chroot execution."""
    set_progress(app, 0.52, "Copying configuration scripts...")
    log_message(app, "Copying configuration scripts...")
    subprocess.run(["mkdir", "-p", "/mnt/usr/local/bin"], check=False)

    installer_scripts_dir = os.path.dirname(os.path.abspath(__file__))
    scripts_source = os.path.join(installer_scripts_dir, "..", "scripts")

    if not os.path.isdir(scripts_source):
        log_message(app, f"  WARNING: scripts directory not found at {scripts_source}")
        return

    for script_file in os.listdir(scripts_source):
        if script_file.endswith(".sh"):
            src = os.path.join(scripts_source, script_file)
            dst = os.path.join(MNT_USR_LOCAL_BIN, script_file)
            _copy_item(src, MNT_USR_LOCAL_BIN)
            subprocess.run(["chmod", "+x", dst], check=False)
            log_message(app, f"  Copied {script_file}")


def step_copy_desktop_files(app):
    """Copy session and desktop files."""
    set_progress(app, 0.54, "Copying session files...")
    log_message(app, "Copying session files...")
    subprocess.run(["mkdir", "-p", "/mnt/usr/share/wayland-sessions"], check=False)
    _copy_item(
        "/usr/share/wayland-sessions/sway.desktop", "/mnt/usr/share/wayland-sessions/"
    )
    _copy_item(
        "/usr/share/wayland-sessions/hyprland.desktop",
        "/mnt/usr/share/wayland-sessions/",
    )

    subprocess.run(["mkdir", "-p", "/mnt/usr/share/backgrounds"], check=False)
    for wp_file in globmod.glob("/usr/share/backgrounds/*"):
        _copy_item(wp_file, "/mnt/usr/share/backgrounds/")

    subprocess.run(["mkdir", "-p", "/mnt/usr/share/applications"], check=False)
    for desktop in [
        "mados-photo-viewer.desktop",
        "mados-pdf-viewer.desktop",
        "mados-equalizer.desktop",
    ]:
        _copy_item(f"/usr/share/applications/{desktop}", "/mnt/usr/share/applications/")

    _copy_item("/usr/share/fonts/dseg", "/mnt/usr/share/fonts/")


def step_generate_fstab(app):
    """Step 5: Generate fstab with Btrfs subvolume support."""
    set_progress(app, 0.49, "Generating filesystem table...")
    log_message(app, "Generating fstab...")
    if DEMO_MODE:
        log_message(app, "[DEMO] Simulating genfstab -U /mnt...")
        time.sleep(0.5)
        log_message(app, "[DEMO] Would write fstab to /mnt/etc/fstab")
        time.sleep(0.5)
    else:
        result = subprocess.run(
            ["genfstab", "-U", "/mnt"], capture_output=True, text=True, check=True
        )
        fstab_content = result.stdout
        lines = fstab_content.split("\n")
        new_lines = []
        for line in lines:
            if "/dev/" in line and "/boot" not in line and "subvol=" not in line:
                parts = line.split()
                if len(parts) >= 4:
                    mount_point = parts[1]
                    if mount_point == "/":
                        parts[3] = parts[3] + ",subvol=@"
                    elif mount_point == "/home":
                        parts[3] = parts[3] + ",subvol=@home"
                new_lines.append(" ".join(parts))
            else:
                new_lines.append(line)
        with open("/mnt/etc/fstab", "w") as f:
            f.write("\n".join(new_lines) + "\n")


def post_rsync_cleanup(app):
    """Remove bulky files from the target after rsync to reclaim disk space."""
    for pattern in POST_COPY_CLEANUP:
        full = os.path.join("/mnt", pattern)
        for path in globmod.glob(full):
            subprocess.run(["rm", "-rf", path], check=False)
    subprocess.run(
        [
            "find",
            "/mnt/usr",
            "-type",
            "d",
            "-name",
            "__pycache__",
            "-exec",
            "rm",
            "-rf",
            "{}",
            "+",
        ],
        check=False,
        capture_output=True,
    )
    log_message(app, "  Removed __pycache__ directories")


def rsync_rootfs_with_progress(app):
    """Copy the live root filesystem to /mnt using rsync."""
    set_progress(app, 0.21, "Copying live system to disk...")
    log_message(app, "Copying live system to target disk (rsync)...")
    log_message(app, "  (Packages already installed in the ISO – no download needed)")

    cmd = [
        "rsync",
        "-aAXHWS",
        "--info=progress2",
        "--no-inc-recursive",
        "--numeric-ids",
    ]
    for exc in RSYNC_EXCLUDES:
        cmd.extend(["--exclude", exc])
    cmd.extend(["/", "/mnt/"])

    progress_start = 0.21
    progress_end = 0.43
    pct_re = re.compile(r"(\d{1,3})%")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.rstrip()
        if not line:
            continue
        match = pct_re.search(line)
        if match:
            pct = int(match.group(1))
            progress = progress_start + (progress_end - progress_start) * (pct / 100)
            set_progress(app, progress, f"Copying system files ({pct}%)...")
        elif line.startswith("rsync:") or line.startswith("sent "):
            log_message(app, f"  {line}")

    proc.wait()
    if proc.returncode not in (0, 24):
        raise subprocess.CalledProcessError(proc.returncode, "rsync")
    if proc.returncode == 24:
        log_message(
            app,
            "  WARNING: rsync reported vanished source files (normal on live system)",
        )

    log_message(app, "  System files copied successfully")

    set_progress(app, 0.43, "Reducing disk footprint...")
    log_message(app, "Removing unnecessary files to save disk space...")
    post_rsync_cleanup(app)

    set_progress(app, 0.45, "Cleaning archiso artifacts...")
    log_message(app, "Removing archiso-specific packages...")
    subprocess.run(
        ["arch-chroot", "/mnt", "pacman", "-Rdd", "--noconfirm"]
        + list(ARCHISO_PACKAGES),
        capture_output=True,
    )
    machine_id = "/mnt/etc/machine-id"
    try:
        os.remove(machine_id)
    except FileNotFoundError:
        pass
    with open(machine_id, "w"):
        pass
    log_message(app, "  Archiso cleanup complete")

    set_progress(app, 0.48, "System ready")
    log_message(app, "Base system ready")


def step_install_nvidia_if_needed(app):
    """Conditionally install NVIDIA drivers if NVIDIA GPU is detected."""
    has_nvidia = _detect_nvidia_gpu()
    app.install_data["has_nvidia"] = has_nvidia

    if not has_nvidia:
        log_message(app, "No NVIDIA GPU detected, skipping NVIDIA packages")
        return

    if DEMO_MODE:
        log_message(app, "[DEMO] Would install NVIDIA packages...")
        return

    set_progress(app, 0.49, "Installing NVIDIA drivers...")
    log_message(app, "NVIDIA GPU detected, installing proprietary drivers...")

    try:
        proc = subprocess.Popen(
            ["arch-chroot", "/mnt", "pacman", "-Sy", "--noconfirm", "--needed"]
            + PACKAGES_NVIDIA,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            line = line.rstrip()
            if line:
                log_message(app, f"  {line}")
        proc.wait()
        if proc.returncode == 0:
            log_message(app, "  NVIDIA drivers installed successfully")
        else:
            log_message(
                app,
                f"  Warning: NVIDIA driver installation returned code {proc.returncode}",
            )
    except Exception as e:
        log_message(app, f"  Warning: Could not install NVIDIA drivers: {e}")


def prepare_pacman(app):
    """Ensure pacman keyring is ready and databases are synced before pacstrap."""
    set_progress(app, 0.21, "Checking package manager keyring...")
    log_message(app, "Checking pacman keyring status...")

    try:
        result = subprocess.run(
            ["systemctl", "is-active", "pacman-init.service"],
            capture_output=True,
            text=True,
        )
        status = result.stdout.strip()
    except Exception:
        status = "unknown"

    if status == "activating":
        log_message(app, "  Pacman keyring is still being initialized, waiting...")
        log_message(app, "  (This can take several minutes on slow hardware)")
        poll_count = 0
        while True:
            time.sleep(5)
            poll_count += 1
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", "pacman-init.service"],
                    capture_output=True,
                    text=True,
                )
                status = result.stdout.strip()
            except Exception:
                status = "unknown"
                break
            if status != "activating":
                break
            if poll_count % 6 == 0:
                elapsed = poll_count * 5
                log_message(
                    app, f"  Still initializing keyring... ({elapsed}s elapsed)"
                )

    if status in ("failed", "inactive", "unknown"):
        log_message(
            app, f"  Keyring service status: {status}, initializing manually..."
        )
        gnupg_dir = "/etc/pacman.d/gnupg"
        os.makedirs(gnupg_dir, mode=0o700, exist_ok=True)
        subprocess.run(["pacman-key", "--init"], check=True)
        subprocess.run(["pacman-key", "--populate"], check=True)

    log_message(app, "  Pacman keyring is ready")

    set_progress(app, 0.23, "Synchronizing package databases...")
    log_message(app, "Synchronizing package databases...")
    proc = subprocess.Popen(
        ["pacman", "-Sy", "--noconfirm"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.rstrip()
        if line:
            log_message(app, f"  {line}")
    proc.wait()
    if proc.returncode != 0:
        log_message(
            app, "  Warning: database sync returned non-zero, pacstrap will retry"
        )
    else:
        log_message(app, "  Package databases synchronized")


def download_packages_with_progress(app, packages):
    """Pre-download packages in small groups so the progress bar stays alive."""
    total = len(packages)
    progress_start = 0.25
    progress_end = 0.36
    group_size = 10

    downloaded = 0
    for i in range(0, total, group_size):
        group = packages[i : i + group_size]
        end = min(i + group_size, total)
        progress = progress_start + (progress_end - progress_start) * (i / total)
        set_progress(app, progress, f"Downloading packages ({downloaded}/{total})...")

        group_preview = ", ".join(group[:3]) + ("..." if len(group) > 3 else "")
        log_message(app, f"  Downloading group: {group_preview}")

        proc = subprocess.Popen(
            ["pacman", "-Sw", "--noconfirm"] + group,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        while True:
            line = proc.stdout.readline()
            if not line:
                break
            line = line.rstrip()
            if not line:
                continue
            if re.match(r"^\s*\d+%\s*\[|^\s*[-#]+\s*$", line):
                continue
            log_message(app, f"    {line}")

        proc.wait()
        if proc.returncode != 0:
            log_message(
                app,
                f"  Warning: download failed for group {i // group_size + 1} "
                f"(exit code {proc.returncode}), pacstrap will retry",
            )

        downloaded = end
        progress = progress_start + (progress_end - progress_start) * (
            downloaded / total
        )
        set_progress(app, progress, f"Downloading packages ({downloaded}/{total})...")

    set_progress(app, progress_end, "All packages downloaded")
    log_message(app, f"  All {total} packages downloaded to cache")


def run_pacstrap_with_progress(app, packages, max_retries=3):
    """Run pacstrap while parsing output to update progress bar and log."""
    last_error = None

    for attempt in range(1, max_retries + 1):
        returncode, installed_count = run_single_pacstrap(app, packages)

        if returncode == 0:
            set_progress(app, 0.48, "Base system installed")
            log_message(app, f"Base system installed ({installed_count} packages)")
            return

        last_error = subprocess.CalledProcessError(returncode, "pacstrap")
        if attempt < max_retries:
            log_message(
                app,
                f"  pacstrap failed (exit code {returncode}), "
                f"retrying ({attempt}/{max_retries})...",
            )
            set_progress(
                app,
                0.36,
                f"Retrying installation (attempt {attempt + 1}/{max_retries})...",
            )
            refresh = subprocess.run(
                ["pacman", "-Sy", "--noconfirm"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if refresh.returncode != 0:
                log_message(
                    app,
                    "  Warning: database refresh failed, retrying pacstrap anyway...",
                )

    raise last_error


def run_single_pacstrap(app, packages):
    """Execute one pacstrap invocation and return (returncode, installed_count)."""
    total_packages = len(packages)
    installed_count = 0

    progress_start = 0.36
    progress_end = 0.48

    proc = subprocess.Popen(
        ["pacstrap", "/mnt"] + packages,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    numbered_pkg_pattern = re.compile(
        r"\((\d+)/(\d+)\)\s+installing\s+(\S+)", re.IGNORECASE
    )
    pkg_pattern = re.compile(r"installing\s+(\S+)", re.IGNORECASE)
    downloading_pattern = re.compile(r"downloading\s+(\S+)", re.IGNORECASE)
    resolving_pattern = re.compile(
        r"resolving dependencies|looking for conflicting", re.IGNORECASE
    )
    total_pattern = re.compile(r"Packages\s+\((\d+)\)", re.IGNORECASE)
    section_pattern = re.compile(r"^::")
    hook_pattern = re.compile(r"^\((\d+)/(\d+)\)\s+(?!installing)", re.IGNORECASE)
    keyring_pattern = re.compile(
        r"checking keyring|checking keys|checking integrity|"
        r"checking package integrity|checking available disk|"
        r"synchronizing package|loading package|"
        r"checking for file conflicts|upgrading|retrieving",
        re.IGNORECASE,
    )
    progress_bar_pattern = re.compile(r"^\s*\d+%\s*\[|^\s*[-#]+\s*$|^$")

    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.rstrip()
        if not line:
            continue

        total_match = total_pattern.search(line)
        if total_match:
            total_packages = int(total_match.group(1))
            log_message(app, f"Total packages to install: {total_packages}")
            continue

        numbered_match = numbered_pkg_pattern.search(line)
        if numbered_match:
            installed_count = int(numbered_match.group(1))
            total_from_line = int(numbered_match.group(2))
            current_pkg = numbered_match.group(3).rstrip(".")
            if total_from_line > 0:
                total_packages = total_from_line
            progress = progress_start + (progress_end - progress_start) * (
                installed_count / max(total_packages, 1)
            )
            progress = min(progress, progress_end)
            set_progress(
                app,
                progress,
                f"Installing packages ({installed_count}/{total_packages})...",
            )
            log_message(app, f"  Installing {current_pkg}...")
            continue

        pkg_match = pkg_pattern.search(line)
        if pkg_match:
            current_pkg = pkg_match.group(1).rstrip(".")
            installed_count += 1
            progress = progress_start + (progress_end - progress_start) * (
                installed_count / max(total_packages, 1)
            )
            progress = min(progress, progress_end)
            set_progress(
                app,
                progress,
                f"Installing packages ({installed_count}/{total_packages})...",
            )
            log_message(app, f"  Installing {current_pkg}...")
            continue

        dl_match = downloading_pattern.search(line)
        if dl_match:
            log_message(app, f"  Downloading {dl_match.group(1)}...")
            continue

        if resolving_pattern.search(line):
            log_message(app, f"  {line.strip()}")
            continue

        if section_pattern.search(line):
            log_message(app, line.strip())
            continue

        if hook_pattern.search(line):
            log_message(app, f"  {line.strip()}")
            continue

        if keyring_pattern.search(line):
            set_progress(app, progress_start, f"{line.strip()}...")
            log_message(app, f"  {line.strip()}")
            continue

        if progress_bar_pattern.search(line):
            continue

        log_message(app, f"  {line.strip()}")

    proc.wait()
    return proc.returncode, installed_count


def run_chroot_with_progress(app, config_script_path):
    """Run arch-chroot configure.sh while streaming output and updating progress"""
    progress_start = 0.55
    progress_end = 0.90

    if not os.path.isfile(config_script_path):
        raise FileNotFoundError(
            f"Configuration script not found at {config_script_path} — disk may be full or write failed"
        )
    if os.path.getsize(config_script_path) == 0:
        raise ValueError(
            f"Configuration script at {config_script_path} is empty — write may have failed"
        )

    proc = subprocess.Popen(
        ["arch-chroot", "/mnt", "/root/configure.sh"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    progress_pattern = re.compile(r"\[PROGRESS\s+(\d+)/(\d+)\]\s+(.+)")

    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.rstrip()
        if not line:
            continue

        progress_match = progress_pattern.search(line)
        if progress_match:
            step = int(progress_match.group(1))
            total = int(progress_match.group(2))
            description = progress_match.group(3)
            progress = progress_start + (progress_end - progress_start) * (
                step / max(total, 1)
            )
            progress = min(progress, progress_end)
            set_progress(app, progress, description)
            log_message(app, f"  {description}")
            continue

        log_message(app, f"  {line}")

    proc.wait()
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, "arch-chroot")

    set_progress(app, progress_end, "System configured")
    log_message(app, "System configuration complete")
