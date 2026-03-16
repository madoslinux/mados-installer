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
)
from utils import log_message, set_progress

MNT_USR_LOCAL_BIN = "/mnt/usr/local/bin/"
SKEL_DIR = "/mnt/etc/skel/"


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
    """Ensure /mnt/boot/vmlinuz-linux exists before entering the chroot."""
    target_kernel = "/mnt/boot/vmlinuz-linux"

    if (
        os.path.isfile(target_kernel)
        and os.access(target_kernel, os.R_OK)
        and os.path.getsize(target_kernel) > 0
    ):
        return

    log_message(app, "  Kernel not found in target /boot, copying from live system...")

    for vmlinuz in sorted(globmod.glob("/usr/lib/modules/*/vmlinuz"), reverse=True):
        if os.path.isfile(vmlinuz) and os.access(vmlinuz, os.R_OK):
            subprocess.run(["cp", vmlinuz, target_kernel], check=True)
            log_message(app, f"  Copied kernel from {vmlinuz}")
            return

    if os.path.isfile("/boot/vmlinuz-linux") and os.access("/boot/vmlinuz-linux", os.R_OK):
        subprocess.run(["cp", "/boot/vmlinuz-linux", target_kernel], check=True)
        log_message(app, "  Copied kernel from /boot/vmlinuz-linux")
        return

    for vmlinuz in sorted(globmod.glob("/mnt/usr/lib/modules/*/vmlinuz"), reverse=True):
        if os.path.isfile(vmlinuz) and os.access(vmlinuz, os.R_OK):
            subprocess.run(["cp", vmlinuz, target_kernel], check=True)
            log_message(app, f"  Copied kernel from {vmlinuz}")
            return

    log_message(
        app,
        "  WARNING: Could not find kernel in live system, chroot will attempt recovery",
    )


def step_partition_disk(app, disk, separate_home, disk_size_gb):
    """Step 1: Partition the disk. Returns (boot_part, root_part, home_part)."""
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
            subprocess.run(["umount", "-l", part], stderr=subprocess.DEVNULL, check=False)
        time.sleep(1)
        subprocess.run(["sgdisk", "--zap-all", disk], check=False)
        subprocess.run(["wipefs", "-a", "-f", disk], check=True)
        subprocess.run(["parted", "-s", disk, "mklabel", "gpt"], check=True)
        subprocess.run(["parted", "-s", disk, "mkpart", "bios_boot", "1MiB", "2MiB"], check=True)
        subprocess.run(["parted", "-s", disk, "set", "1", "bios_grub", "on"], check=True)
        subprocess.run(["parted", "-s", disk, "mkpart", "EFI", "fat32", "2MiB", "1GiB"], check=True)
        subprocess.run(["parted", "-s", disk, "set", "2", "esp", "on"], check=True)

    _create_root_partition(app, disk, separate_home, disk_size_gb)

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
        f"{part_prefix}4" if separate_home else None,
    )


def _create_root_partition(app, disk, separate_home, disk_size_gb):
    """Create root (and optionally home) partition."""
    if separate_home:
        root_end = "51GiB" if disk_size_gb < 128 else "61GiB"
        if DEMO_MODE:
            log_message(app, f"[DEMO] Simulating parted mkpart root 1GiB-{root_end}...")
            time.sleep(0.5)
            log_message(app, "[DEMO] Simulating parted mkpart home...")
            time.sleep(0.5)
        else:
            subprocess.run(
                ["parted", "-s", disk, "mkpart", "root", "ext4", "1GiB", root_end],
                check=True,
            )
            subprocess.run(
                ["parted", "-s", disk, "mkpart", "home", "ext4", root_end, "100%"],
                check=True,
            )
    else:
        if DEMO_MODE:
            log_message(app, "[DEMO] Simulating parted mkpart root 1GiB-100%...")
            time.sleep(0.5)
        else:
            subprocess.run(
                ["parted", "-s", disk, "mkpart", "root", "ext4", "1GiB", "100%"],
                check=True,
            )


def step_format_partitions(app, boot_part, root_part, home_part, separate_home):
    """Step 2: Format partitions."""
    set_progress(app, 0.15, "Formatting partitions...")
    log_message(app, "Formatting partitions...")

    if DEMO_MODE:
        _format_partitions_demo(app, boot_part, root_part, home_part, separate_home)
    else:
        _format_partitions_real(boot_part, root_part, home_part, separate_home)


def _format_partitions_demo(app, boot_part, root_part, home_part, separate_home):
    """Demo mode partition formatting."""
    log_message(app, f"[DEMO] Simulating mkfs.fat {boot_part}...")
    time.sleep(0.5)
    log_message(app, f"[DEMO] Simulating mkfs.ext4 {root_part}...")
    time.sleep(0.5)
    if separate_home and home_part:
        log_message(app, f"[DEMO] Simulating mkfs.ext4 {home_part}...")
        time.sleep(0.5)


def _format_partitions_real(boot_part, root_part, home_part, separate_home):
    """Real partition formatting."""
    partitions = [("EFI", boot_part), ("root", root_part)]
    if separate_home and home_part:
        partitions.append(("home", home_part))
    for part_name, part_dev in partitions:
        if not os.path.exists(part_dev):
            raise RuntimeError(f"Partition device {part_dev} ({part_name}) does not exist!")
    subprocess.run(["mkfs.fat", "-F32", boot_part], check=True)
    subprocess.run(["mkfs.ext4", "-F", root_part], check=True)
    if separate_home and home_part:
        subprocess.run(["mkfs.ext4", "-F", home_part], check=True)


def step_mount_filesystems(app, boot_part, root_part, home_part, separate_home):
    """Step 3: Mount filesystems."""
    set_progress(app, 0.20, "Mounting filesystems...")
    log_message(app, "Mounting filesystems...")

    if DEMO_MODE:
        log_message(app, f"[DEMO] Simulating mount {root_part} /mnt...")
        time.sleep(0.5)
        log_message(app, "[DEMO] Simulating mkdir /mnt/boot...")
        time.sleep(0.3)
        log_message(app, f"[DEMO] Simulating mount {boot_part} /mnt/boot...")
        time.sleep(0.5)
        if separate_home and home_part:
            log_message(app, "[DEMO] Simulating mkdir /mnt/home...")
            time.sleep(0.3)
            log_message(app, f"[DEMO] Simulating mount {home_part} /mnt/home...")
            time.sleep(0.5)
    else:
        subprocess.run(["mount", root_part, "/mnt"], check=True)
        subprocess.run(["mkdir", "-p", "/mnt/boot"], check=True)
        subprocess.run(["mount", boot_part, "/mnt/boot"], check=True)
        if separate_home and home_part:
            subprocess.run(["mkdir", "-p", "/mnt/home"], check=True)
            subprocess.run(["mount", home_part, "/mnt/home"], check=True)


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


def step_copy_desktop_files(app):
    """Copy session and desktop files."""
    set_progress(app, 0.54, "Copying session files...")
    log_message(app, "Copying session files...")
    subprocess.run(["mkdir", "-p", "/mnt/usr/share/wayland-sessions"], check=False)
    _copy_item("/usr/share/wayland-sessions/sway.desktop", "/mnt/usr/share/wayland-sessions/")
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
    """Step 5: Generate fstab."""
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
        with open("/mnt/etc/fstab", "w") as f:
            f.write(result.stdout)


def post_rsync_cleanup(app):
    """Remove bulky files from the target after rsync to reclaim disk space."""
    for pattern in POST_COPY_CLEANUP:
        full = os.path.join("/mnt", pattern)
        for path in globmod.glob(full):
            subprocess.run(["rm", "-rf", path], check=False)
    subprocess.run(
        ["find", "/mnt/usr", "-type", "d", "-name", "__pycache__", "-exec", "rm", "-rf", "{}", "+"],
        check=False,
        capture_output=True,
    )
    log_message(app, "  Removed __pycache__ directories")


def rsync_rootfs_with_progress(app):
    """Copy the live root filesystem to /mnt using rsync."""
    set_progress(app, 0.21, "Copying live system to disk...")
    log_message(app, "Copying live system to target disk (rsync)...")
    log_message(app, "  (Packages already installed in the ISO – no download needed)")

    cmd = ["rsync", "-aAXHWS", "--info=progress2", "--no-inc-recursive", "--numeric-ids"]
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
        ["arch-chroot", "/mnt", "pacman", "-Rdd", "--noconfirm"] + list(ARCHISO_PACKAGES),
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
                log_message(app, f"  Still initializing keyring... ({elapsed}s elapsed)")

    if status in ("failed", "inactive", "unknown"):
        log_message(app, f"  Keyring service status: {status}, initializing manually...")
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
        log_message(app, "  Warning: database sync returned non-zero, pacstrap will retry")
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
        progress = progress_start + (progress_end - progress_start) * (downloaded / total)
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
                app, 0.36, f"Retrying installation (attempt {attempt + 1}/{max_retries})..."
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

    numbered_pkg_pattern = re.compile(r"\((\d+)/(\d+)\)\s+installing\s+(\S+)", re.IGNORECASE)
    pkg_pattern = re.compile(r"installing\s+(\S+)", re.IGNORECASE)
    downloading_pattern = re.compile(r"downloading\s+(\S+)", re.IGNORECASE)
    resolving_pattern = re.compile(r"resolving dependencies|looking for conflicting", re.IGNORECASE)
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
        raise ValueError(f"Configuration script at {config_script_path} is empty — write may have failed")

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
            progress = progress_start + (progress_end - progress_start) * (step / max(total, 1))
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