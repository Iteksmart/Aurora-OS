#!/bin/bash

# Aurora OS Initramfs Creation Script
# Creates initial RAM filesystem with essential Aurora OS components

set -e

# Configuration
INITRAMFS_DIR="build/initramfs"
INITRAMFS_FILE="build/aurora-initramfs.img"
KERNEL_VERSION="6.1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Aurora OS Initramfs Creation${NC}"
echo -e "${BLUE}===========================${NC}"

# Clean previous build
if [ -d "$INITRAMFS_DIR" ]; then
    echo -e "${YELLOW}Cleaning previous initramfs...${NC}"
    rm -rf "$INITRAMFS_DIR"
fi

# Create initramfs directory structure
echo -e "${GREEN}Creating directory structure...${NC}"
mkdir -p "$INITRAMFS_DIR"/{bin,dev,etc,lib,lib64,proc,root,run,sbin,sys,tmp,usr,var}
mkdir -p "$INITRAMFS_DIR"/usr/{bin,sbin,lib}
mkdir -p "$INITRAMFS_DIR"/etc/{udev,modprobe.d,init.d}
mkdir -p "$INITRAMFS_DIR"/lib/modules

# Copy essential binaries
echo -e "${GREEN}Installing essential binaries...${NC}"

# Core utilities
BINARIES="sh bash mount umount ls cat echo rm mkdir rmdir cp mv sleep kill ps sync"
BINARIES="$BINARIES mountpoint lsblk blkid switch_root pivot_root"

for binary in $BINARIES; do
    if [ -x "/bin/$binary" ]; then
        cp "/bin/$binary" "$INITRAMFS_DIR/bin/"
    elif [ -x "/usr/bin/$binary" ]; then
        cp "/usr/bin/$binary" "$INITRAMFS_DIR/bin/"
    fi
done

# Essential system binaries
SBINARIES="udevd udevadm modprobe kmod"
SBINARIES="$SBINARIES busybox"

for binary in $SBINARIES; do
    if [ -x "/sbin/$binary" ]; then
        cp "/sbin/$binary" "$INITRAMFS_DIR/sbin/"
    elif [ -x "/usr/sbin/$binary" ]; then
        cp "/usr/sbin/$binary" "$INITRAMFS_DIR/sbin/"
    fi
done

# Copy required libraries
echo -e "${GREEN}Installing required libraries...${NC}"

# Function to copy library and its dependencies
copy_lib() {
    local lib="$1"
    if [ -f "$lib" ] && [ ! -f "$INITRAMFS_DIR/$lib" ]; then
        local dir=$(dirname "$lib")
        mkdir -p "$INITRAMFS_DIR/$dir"
        cp "$lib" "$INITRAMFS_DIR/$lib"
        
        # Get library dependencies
        ldd "$lib" 2>/dev/null | grep -o '/lib[^ ]*' | while read dep; do
            copy_lib "$dep"
        done
    fi
}

# Copy libraries for all binaries
for binary in "$INITRAMFS_DIR"/bin/* "$INITRAMFS_DIR"/sbin/*; do
    if [ -f "$binary" ]; then
        ldd "$binary" 2>/dev/null | grep -o '/lib[^ ]*' | while read dep; do
            copy_lib "$dep"
        done
    fi
done

# Copy kernel modules
echo -e "${GREEN}Installing kernel modules...${NC}"

if [ -d "/lib/modules/$KERNEL_VERSION" ]; then
    mkdir -p "$INITRAMFS_DIR/lib/modules/$KERNEL_VERSION"
    
    # Essential modules
    MODULES="ext4 vfat iso9660 btrfs xfs"
    MODULES="$MODULES ahci sd_mod sr_mod usb_storage"
    MODULES="$MODULES ehci-pci ehci-hcd xhci-hcd uhci-hcd"
    MODULES="$MODULES i915 virtio_gpu virtio_pci virtio_blk"
    
    for module in $MODULES; do
        if [ -f "/lib/modules/$KERNEL_VERSION/kernel/drivers/${module}.ko" ]; then
            cp "/lib/modules/$KERNEL_VERSION/kernel/drivers/${module}.ko" \
               "$INITRAMFS_DIR/lib/modules/$KERNEL_VERSION/"
        else
            find "/lib/modules/$KERNEL_VERSION" -name "${module}.ko" -exec cp {} "$INITRAMFS_DIR/lib/modules/$KERNEL_VERSION/" \;
        fi
    done
    
    # Copy module dependencies
    if [ -f "/lib/modules/$KERNEL_VERSION/modules.dep" ]; then
        cp "/lib/modules/$KERNEL_VERSION/modules.dep" "$INITRAMFS_DIR/lib/modules/$KERNEL_VERSION/"
    fi
    
    if [ -f "/lib/modules/$KERNEL_VERSION/modules.alias" ]; then
        cp "/lib/modules/$KERNEL_VERSION/modules.alias" "$INITRAMFS_DIR/lib/modules/$KERNEL_VERSION/"
    fi
fi

# Create device nodes
echo -e "${GREEN}Creating device nodes...${NC}"
mknod -m 660 "$INITRAMFS_DIR/dev/console" c 5 1
mknod -m 660 "$INITRAMFS_DIR/dev/null" c 1 3
mknod -m 660 "$INITRAMFS_DIR/dev/zero" c 1 5
mknod -m 660 "$INITRAMFS_DIR/dev/tty" c 5 0
mknod -m 660 "$INITRAMFS_DIR/dev/random" c 1 8
mknod -m 660 "$INITRAMFS_DIR/dev/urandom" c 1 9

# Create essential configuration files
echo -e "${GREEN}Creating configuration files...${NC}"

# Init script
cat > "$INITRAMFS_DIR/init" << 'INIT_EOF'
#!/bin/sh

# Aurora OS Init Script
# Mount essential filesystems
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev

# Start udev
echo "Starting udev..."
udevd --daemon
udevadm trigger --type=subsystems --action=add
udevadm trigger --type=devices --action=add
udevadm settle

# Load kernel modules
echo "Loading kernel modules..."
modprobe ext4 2>/dev/null
modprobe vfat 2>/dev/null
modprobe iso9660 2>/dev/null

# Aurora OS banner
echo ""
echo "    ____             __       __          "
echo "   / __ \____ ______/ /______/ /_  __  __ "
echo "  / /_/ / __  / ___/ __/ ___/ __ \/ / / / "
echo " / ____/ /_/ (__  ) /_/ /  / /_/ / /_/ /  "
echo "/_/    \__,_/____/\__/_/  /_.___/\__, /   "
echo "    Aurora OS v1.0.0         /____/    "
echo ""

# Find boot device
echo "Scanning for Aurora OS root filesystem..."
for device in /dev/sda* /dev/nvme* /dev/vd* /dev/mmcblk*; do
    if [ -b "$device" ]; then
        # Try to mount and check for Aurora OS
        mkdir -p /mnt
        if mount -t ext4 -o ro "$device" /mnt 2>/dev/null; then
            if [ -f /mnt/etc/aurora-release ]; then
                echo "Found Aurora OS on $device"
                echo "Switching root..."
                switch_root /mnt /sbin/init
                break
            fi
            umount /mnt 2>/dev/null
        fi
        
        # Try ISO boot
        if mount -t iso9660 -o ro "$device" /mnt 2>/dev/null; then
            if [ -f /mnt/aurora-os.squashfs ]; then
                echo "Found Aurora OS ISO on $device"
                mkdir -p /squashfs
                mount -t squashfs -o ro /mnt/aurora-os.squashfs /squashfs
                echo "Switching root from ISO..."
                switch_root /squashfs /sbin/init
                break
            fi
            umount /mnt 2>/dev/null
            umount /squashfs 2>/dev/null
        fi
    fi
done

echo "ERROR: Aurora OS root filesystem not found!"
echo "Dropping to emergency shell..."
exec /bin/sh
INIT_EOF

chmod +x "$INITRAMFS_DIR/init"

# udev configuration
cat > "$INITRAMFS_DIR/etc/udev/udev.conf" << 'UDEV_EOF'
# udev.conf
udev_log="info"
UDEV_EOF

# Create Aurora OS release file
mkdir -p "$INITRAMFS_DIR/etc"
cat > "$INITRAMFS_DIR/etc/aurora-release" << 'RELEASE_EOF'
Aurora OS 1.0.0 - AI-Native Operating System
RELEASE_EOF

# Create modprobe configuration
cat > "$INITRAMFS_DIR/etc/modprobe.d/aurora.conf" << 'MODPROBE_EOF'
# Aurora OS module configuration
options ext4 errors=remount-ro
UDEV_EOF

# Create initramfs image
echo -e "${GREEN}Creating initramfs image...${NC}"
cd "$INITRAMFS_DIR"
find . | cpio -H newc -o | gzip -9 > "../$(basename $INITRAMFS_FILE)"
cd - > /dev/null

# Verify the image was created
if [ -f "$INITRAMFS_FILE" ]; then
    SIZE=$(du -h "$INITRAMFS_FILE" | cut -f1)
    echo -e "${GREEN}✓ Initramfs created successfully!${NC}"
    echo -e "${GREEN}  File: $INITRAMFS_FILE${NC}"
    echo -e "${GREEN}  Size: $SIZE${NC}"
    
    # Show contents
    echo -e "${BLUE}Initramfs contents:${NC}"
    gzip -dc "$INITRAMFS_FILE" | cpio -tv | head -20
    echo "   ... (truncated)"
else
    echo -e "${RED}✗ Failed to create initramfs!${NC}"
    exit 1
fi

echo -e "${GREEN}Aurora OS initramfs creation complete!${NC}"
