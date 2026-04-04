"""
madOS Installer - Installation package
"""

from installer.config_script import build_config_script, write_config_script
from installer.steps import (_check_required_commands,
                             download_packages_with_progress,
                             post_rsync_cleanup, prepare_pacman,
                             rsync_rootfs_with_progress,
                             run_chroot_with_progress,
                             run_pacstrap_with_progress, run_single_pacstrap,
                             step_configure_mados_updater,
                             step_configure_snapper, step_copy_desktop_files,
                             step_copy_installer_scripts, step_copy_live_files,
                             step_copy_scripts, step_create_base_snapshot,
                             step_create_btrfs_subvolumes,
                             step_format_partitions, step_generate_fstab,
                             step_install_nvidia_if_needed,
                             step_mount_filesystems, step_partition_disk)

__all__ = [
    "step_partition_disk",
    "step_format_partitions",
    "step_create_btrfs_subvolumes",
    "step_mount_filesystems",
    "step_copy_live_files",
    "step_copy_scripts",
    "step_copy_installer_scripts",
    "step_copy_desktop_files",
    "step_generate_fstab",
    "step_configure_snapper",
    "step_configure_mados_updater",
    "step_create_base_snapshot",
    "post_rsync_cleanup",
    "rsync_rootfs_with_progress",
    "prepare_pacman",
    "download_packages_with_progress",
    "run_pacstrap_with_progress",
    "run_single_pacstrap",
    "run_chroot_with_progress",
    "build_config_script",
    "write_config_script",
    "_check_required_commands",
    "step_install_nvidia_if_needed",
]
