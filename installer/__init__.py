"""
madOS Installer - Installation package
"""

from .steps import (
    step_partition_disk,
    step_format_partitions,
    step_mount_filesystems,
    step_copy_live_files,
    step_copy_scripts,
    step_copy_desktop_files,
    step_generate_fstab,
    post_rsync_cleanup,
    rsync_rootfs_with_progress,
    prepare_pacman,
    download_packages_with_progress,
    run_pacstrap_with_progress,
    run_single_pacstrap,
    run_chroot_with_progress,
)

from .config_script import (
    build_config_script,
    write_config_script,
)

__all__ = [
    "step_partition_disk",
    "step_format_partitions",
    "step_mount_filesystems",
    "step_copy_live_files",
    "step_copy_scripts",
    "step_copy_desktop_files",
    "step_generate_fstab",
    "post_rsync_cleanup",
    "rsync_rootfs_with_progress",
    "prepare_pacman",
    "download_packages_with_progress",
    "run_pacstrap_with_progress",
    "run_single_pacstrap",
    "run_chroot_with_progress",
    "build_config_script",
    "write_config_script",
]