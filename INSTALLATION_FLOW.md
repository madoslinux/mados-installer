# madOS Installer - Installation Flow

## Step 1: Disk Selection

```mermaid
sequenceDiagram
    participant U as User
    participant App as madOS Installer
    participant Disk as pages/disk.py
    participant System as Linux (lsblk)

    U->>App: Starts installer
    App->>Disk: create_disk_page()
    Disk->>System: lsblk -d -n -o NAME,SIZE,TYPE,MODEL
    System-->>Disk: List of available disks
    Disk-->>App: Shows disk selection buttons
    App->>U: Displays available disks
    
    U->>App: Selects disk (e.g., /dev/sda)
    App->>App: install_data["disk"] = "/dev/sda"
    App->>App: Validates size (minimum 10GB)
    App->>U: Asks for confirmation
    U->>App: Confirms
    App->>App: notebook.next_page()
```

## Step 2: Partitioning

```mermaid
sequenceDiagram
    participant App as madOS Installer
    participant Steps as installer/steps.py
    participant System as Linux (parted, sgdisk)

    App->>Steps: step_partition_disk(disk, separate_home, size)
    
    Steps->>System: sgdisk --zap-all /dev/sda
    Steps->>System: wipefs -a -f /dev/sda
    Steps->>System: parted -s /dev/sda mklabel gpt
    
    Steps->>System: parted -s /dev/sda mkpart bios_boot 1MiB 2MiB
    Steps->>System: parted -s /dev/sda set 1 bios_grub on
    
    Steps->>System: parted -s /dev/sda mkpart EFI fat32 2MiB 1GiB
    Steps->>System: parted -s /dev/sda set 2 esp on
    
    Steps->>System: parted -s /dev/sda mkpart root ext4 1GiB 50GiB
    Steps->>System: parted -s /dev/sda mkpart home ext4 50GiB 100% (if separate_home)
    
    Steps->>System: partprobe /dev/sda
    Steps->>System: udevadm settle
    
    Steps-->>App: Returns (boot_part, root_part, home_part)
    Note over App: boot_part = /dev/sda2<br/>root_part = /dev/sda3<br/>home_part = /dev/sda4
```

## Step 3: Format Partitions

```mermaid
sequenceDiagram
    participant App as madOS Installer
    participant Steps as installer/steps.py
    participant System as Linux (mkfs)

    App->>Steps: step_format_partitions(boot_part, root_part, home_part)

    Steps->>System: mkfs.fat -F32 /dev/sda2
    Note over System: EFI System Partition (FAT32)

    Steps->>System: mkfs.ext4 -F /dev/sda3
    Note over System: Root partition (ext4)

    alt If separate_home
        Steps->>System: mkfs.ext4 -F /dev/sda4
    end

    Steps-->>App: Partitions formatted
```

## Step 4: Mount Filesystems

```mermaid
sequenceDiagram
    participant App as madOS Installer
    participant Steps as installer/steps.py
    participant System as Linux (mount)

    App->>Steps: step_mount_filesystems(boot_part, root_part, home_part)

    Steps->>System: mount /dev/sda3 /mnt
    Steps->>System: mkdir -p /mnt/boot
    Steps->>System: mount /dev/sda2 /mnt/boot

    alt If separate_home
        Steps->>System: mkdir -p /mnt/home
        Steps->>System: mount /dev/sda4 /mnt/home
    end

    Steps-->>App: Filesystems mounted
```

## Step 5: System Copy (rsync)

```mermaid
sequenceDiagram
    participant App as madOS Installer
    participant Steps as installer/steps.py
    participant Config as config.py
    participant System as Linux (rsync)

    App->>Steps: rsync_rootfs_with_progress()

    Note over Config: RSYNC_EXCLUDES = [<br/>"/dev/*", "/proc/*", "/sys/*"<br/>"/tmp/*", "/run/*", "/var/log/*"<br/>"/usr/share/doc/*", "/usr/share/man/*"<br/>"/usr/lib/python*/test/*"<br/>"/usr/include/*", "/usr/lib/*.a"<br/>... ]

    Steps->>System: rsync -aAXHWS --exclude (many) / /mnt/
    Note over System: Copies system<br/>excluding unnecessary files

    Steps->>System: rm -rf /mnt/usr/lib/python*/__pycache__

    Steps->>System: arch-chroot /mnt pacman -Rdd mkinitcpio-archiso
    Steps->>System: rm /mnt/etc/machine-id && touch /mnt/etc/machine-id

    Steps-->>App: System copied
```

## Step 6: Copy Additional Files

```mermaid
sequenceDiagram
    participant App as madOS Installer
    participant Steps as installer/steps.py
    participant System as Linux (cp)

    App->>Steps: step_copy_live_files()

    Note over Steps: Plymouth boot splash
    Steps->>System: mkdir -p /mnt/usr/share/plymouth/themes/mados
    Steps->>System: cp /usr/share/plymouth/themes/mados/logo.png /mnt/...
    Steps->>System: cp /usr/share/plymouth/themes/mados/dot.png /mnt/...

    Note over Steps: Desktop configs (skel)
    Steps->>System: cp -r /etc/skel/.config/* /mnt/etc/skel/.config/
    Steps->>System: cp /etc/skel/.bash_profile /mnt/etc/skel/

    Note over Steps: System scripts
    Steps->>System: cp /usr/local/bin/cage-greeter /mnt/usr/local/bin/
    Steps->>System: cp /usr/local/bin/sway-session /mnt/usr/local/bin/
    Steps->>System: chmod +x /mnt/usr/local/bin/*

    Note over Steps: Session files
    Steps->>System: cp /usr/share/wayland-sessions/*.desktop /mnt/...

    Steps-->>App: Files copied
```

## Step 7: Generate fstab

```mermaid
sequenceDiagram
    participant App as madOS Installer
    participant Steps as installer/steps.py
    participant System as Linux (genfstab)

    App->>Steps: step_generate_fstab()

    Note over Steps: /etc/fstab excluded from rsync

    Steps->>System: genfstab -U /mnt
    System-->>Steps: UUID=xxx / ext4 defaults 0 1<br/>UUID=yyy /boot vfat defaults 0 2<br/>UUID=zzz /home ext4 defaults 0 2
    
    Steps->>System: Writes to /mnt/etc/fstab

    Steps-->>App: fstab generated
```

## Step 8: Generate Configuration Script

```mermaid
sequenceDiagram
    participant App as madOS Installer
    participant Data as install_data
    participant Config as config_script.py

    App->>Data: Reads install_data
    Note over Data: disk = "/dev/sda"<br/>timezone = "Europe/Madrid"<br/>locale = "es_ES.UTF-8"<br/>username = "testuser"<br/>...

    App->>Config: build_config_script(data)

    rect rgb(240, 248, 255)
        Note over Config: Input validation
    end
    Config->>Config: Validates timezone in TIMEZONES
    Config->>Config: Validates locale in LOCALE_MAP
    Config->>Config: Validates disk regex "^/dev/[a-zA-Z0-9]+$"
    Config->>Config: Validates username regex "^[a-z_][a-z0-9_-]*$"

    rect rgb(255, 240, 240)
        Note over Config: Partition calculation
    end
    Config->>Config: _get_partition_prefix("/dev/sda")
    Note over Config: Returns: "sda" (no p prefix)

    Config->>Config: root_part = "sda3"
    Config->>Config: boot_part = "sda2"

    alt If NVMe disk
        Config->>Config: _get_partition_prefix("/dev/nvme0n1")
        Note over Config: Returns "nvme0n1p"
        Config->>Config: root_part = "nvme0n1p3"
    end

    Config-->>App: Returns bash script

    Note over App: Script contains:<br/>- ROOT_UUID=$(blkid -s UUID -o value /dev/sda3)<br/>- grub-install UEFI or BIOS<br/>- mkinitcpio -P<br/>- systemctl enable ...
```

## Step 9: Execute configure.sh in chroot (Part 1/2)

```mermaid
sequenceDiagram
    participant App as madOS Installer
    participant Steps as installer/steps.py
    participant System as Linux (arch-chroot)

    App->>System: Writes /mnt/root/configure.sh (bash script)
    App->>Steps: run_chroot_with_progress("/mnt/root/configure.sh")

    System->>System: arch-chroot /mnt /root/configure.sh

    rect rgb(240, 248, 255)
        Note over System: PROGRESS 1/8: Timezone and Locale
    end
    System->>System: ln -sf /usr/share/zoneinfo/Europe/Madrid /etc/localtime
    System->>System: hwclock --systohc
    System->>System: echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
    System->>System: echo "es_ES.UTF-8 UTF-8" >> /etc/locale.gen
    System->>System: locale-gen
    System->>System: echo "LANG=es_ES.UTF-8" > /etc/locale.conf

    rect rgb(240, 248, 255)
        Note over System: PROGRESS 2/8: User and Hostname
    end
    System->>System: echo "mados-test" > /etc/hostname
    System->>System: cat > /etc/hosts <<EOF<br/>127.0.0.1 localhost<br/>127.0.1.1 mados-test.localdomain mados-test<br/>EOF
    System->>System: userdel -r mados (cleanup live user)
    System->>System: systemctl disable livecd-*.service
    System->>System: useradd -m -G wheel,audio,video,storage -s /usr/bin/zsh testuser
    System->>System: echo 'testuser:password' | chpasswd
    System->>System: echo "%wheel ALL=(ALL:ALL) ALL" > /etc/sudoers.d/wheel
```

## Step 9: Execute configure.sh in chroot (Part 2/2 - GRUB)

```mermaid
sequenceDiagram
    participant System as Linux (chroot)

    rect rgb(255, 200, 200)
        Note over System: PROGRESS 3/8: Install GRUB
    end
    
    System->>System: Verifies /sys/firmware/efi exists

    alt UEFI Mode
        System->>System: mount -t efivarfs efivarfs /sys/firmware/efi/efivars
        System->>System: grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=madOS --recheck
        System->>System: grub-install --target=x86_64-efi --efi-directory=/boot --removable --recheck
        
        rect rgb(255, 200, 255)
            Note over System: Secure Boot (if enabled)
        end
        System->>System: Checks SecureBoot var
        System->>System: If enabled: sbctl create-keys, enroll-keys
        System->>System: sbctl sign /boot/EFI/BOOT/BOOTX64.EFI
        
    else BIOS Mode
        System->>System: BASE_DISK=$(echo "$disk" | sed 's/[0-9]*$//')
        System->>System: grub-install --target=i386-pc --recheck "$BASE_DISK"
    end

    rect rgb(200, 255, 200)
        Note over System: PROGRESS 4/8: Configure GRUB
    end
    System->>System: sed -i 's/GRUB_CMDLINE_LINUX="" /GRUB_CMDLINE_LINUX="zswap.enabled=0 splash quiet"/' /etc/default/grub
    System->>System: sed -i 's/GRUB_DISTRIBUTOR="Arch"/GRUB_DISTRIBUTOR="madOS"/' /etc/default/grub
    System->>System: echo 'GRUB_DISABLE_LINUX_UUID=false' >> /etc/default/grub
    
    rect rgb(200, 255, 200)
        Note over System: Create custom entry with UUID
    end
    System->>System: ROOT_UUID=$(blkid -s UUID -o value {root_part})
    Note over System: root_part = /dev/sda3 (dynamic)
    
    System->>System: mkdir -p /boot/grub/custom
    System->>System: cat > /boot/grub/custom/mados.cfg <<EOF<br/>menuentry 'madOS Linux' {<br/>search --no-floppy --fs-uuid --set=root $ROOT_UUID<br/>linux /vmlinuz-linux root=UUID=$ROOT_UUID rw ...<br/>initrd /initramfs-linux.img<br/>}<br/>EOF
    
    System->>System: grub-mkconfig -o /boot/grub/grub.cfg
```

## Step 9 (continued): Plymouth, Initramfs, Services

```mermaid
sequenceDiagram
    participant System as Linux (chroot)

    rect rgb(240, 255, 240)
        Note over System: PROGRESS 5/8: Plymouth
    end
    System->>System: mkdir -p /usr/share/plymouth/themes/mados
    System->>System: cat > /usr/share/plymouth/themes/mados/mados.plymouth
    System->>System: cat > /usr/share/plymouth/themes/mados/mados.script
    System->>System: plymouth-set-default-theme mados
    System->>System: cat > /etc/plymouth/plymouthd.conf

    rect rgb(255, 240, 255)
        Note over System: PROGRESS 6/8: Initramfs
    end
    System->>System: rm -f /etc/mkinitcpio.conf.d/archiso.conf
    System->>System: mkinitcpio -P

    rect rgb(255, 255, 240)
        Note over System: PROGRESS 7/8: Services
    end
    System->>System: passwd -l root
    System->>System: systemctl enable NetworkManager
    System->>System: systemctl enable systemd-resolved
    System->>System: systemctl enable earlyoom
    System->>System: systemctl enable greetd
    System->>System: systemctl enable iwd
    System->>System: systemctl enable bluetooth

    rect rgb(240, 240, 255)
        Note over System: PROGRESS 8/8: Final configuration
    end
    System->>System: cat > /etc/os-release (madOS branding)
    System->>System: cat > /etc/NetworkManager/conf.d/wifi-backend.conf
    System->>System: cat > /etc/sysctl.d/99-extreme-low-ram.conf
    System->>System: cat > /etc/systemd/zram-generator.conf
    System->>System: cat > /etc/greetd/config.toml
    System->>System: cat > /etc/greetd/regreet.toml
    System->>System: Copy configs to /home/testuser/.config/
```

## Step 10: Final Cleanup

```mermaid
sequenceDiagram
    participant App as madOS Installer
    participant Steps as installer/steps.py
    participant System as Linux

    App->>Steps: Final cleanup

    Steps->>System: rm /mnt/root/configure.sh
    Steps->>System: sync
    Steps->>System: umount -R /mnt

    App->>U: Installation complete!
```

## Partition Summary

```
/dev/sda (SATA/HDD)           /dev/nvme0n1 (NVMe)
├─ sda1 (1MB) BIOS Boot        ├─ nvme0n1p1 (1MB) BIOS Boot
├─ sda2 (1GB) EFI              ├─ nvme0n1p2 (1GB) EFI
├─ sda3 (50GB) Root (/)        ├─ nvme0n1p3 (50GB) Root (/)
└─ sda4 (rest) Home (/home)    └─ nvme0n1p4 (rest) Home (/home)
```

## Dynamic Partition Calculation

| Variable | SATA | NVMe |
|----------|------|------|
| `disk` | `/dev/sda` | `/dev/nvme0n1` |
| `part_prefix` | `sda` | `nvme0n1p` |
| `boot_part` | `sda2` | `nvme0n1p2` |
| `root_part` | `sda3` | `nvme0n1p3` |
| `home_part` | `sda4` | `nvme0n1p4` |

## Critical Process Points

1. **Partitioning**: Creates BIOS boot, EFI, root, home
2. **Formatting**: EFI = FAT32, root/home = ext4
3. **Mounting**: EFI at /boot, root at /mnt, home at /mnt/home
4. **fstab**: Generated with genfstab -U (UUIDs)
5. **GRUB**: 
   - UEFI: --efi-directory=/boot --removable
   - BIOS: --target=i386-pc --recheck $BASE_DISK
   - Custom entry with dynamic UUID
6. **initramfs**: mkinitcpio -P (rebuilt)
7. **Services**: NetworkManager, greetd, iwd, bluetooth