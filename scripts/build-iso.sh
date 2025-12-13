#!/bin/bash

# Aurora-OS ISO Builder
# Creates bootable ISO image for Aurora-OS

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AURORA_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$AURORA_ROOT/build"
ISO_DIR="$BUILD_DIR/iso"
ROOTFS_DIR="$BUILD_DIR/rootfs"
KERNEL_VERSION="6.6.1"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
log() {
    echo -e "${GREEN}[BUILD]${NC} $*"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

error() {
    echo -e "${RED}[ERROR]${NC} $*"
    exit 1
}

# Check dependencies
check_deps() {
    log "Checking build dependencies"
    
    local deps=("xorriso" "grub-mkrescue" "mksquashfs" "wget" "tar" "gzip" "cpio")
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            error "Missing dependency: $dep. Please install it first."
        fi
    done
    
    log "All dependencies found"
}

# Clean previous build
clean_build() {
    log "Cleaning previous build"
    
    rm -rf "$BUILD_DIR"
    mkdir -p "$BUILD_DIR" "$ISO_DIR" "$ROOTFS_DIR"
    
    log "Build directory cleaned"
}

# Build Aurora kernel
build_kernel() {
    log "Building Aurora-OS kernel"
    
    cd "$AURORA_ROOT/kernel"
    
    # Download kernel source if not present
    if [[ ! -d "linux-$KERNEL_VERSION" ]]; then
        log "Downloading Linux kernel $KERNEL_VERSION"
        ./configure-aurora-kernel.sh
    fi
    
    # Build kernel
    cd "linux-$KERNEL_VERSION"
    
    log "Compiling kernel (this may take a while...)"
    make -j$(nproc) ARCH=x86_64 || error "Kernel build failed"
    
    # Install modules to rootfs
    make modules_install INSTALL_MOD_PATH="$ROOTFS_DIR" ARCH=x86_64 || error "Module installation failed"
    
    # Copy kernel to ISO
    cp arch/x86/boot/bzImage "$ISO_DIR/boot/vmlinuz" || error "Failed to copy kernel"
    
    log "Kernel build completed"
}

# Build Aurora kernel modules
build_modules() {
    log "Building Aurora kernel modules"
    
    local modules=("aie" "sense" "flow" "desktop" "runtime")
    
    for module in "${modules[@]}"; do
        log "Building Aurora $module module"
        
        cd "$AURORA_ROOT/core/$module"
        
        if [[ -f "Makefile" ]]; then
            make -j$(nproc) || warn "Failed to build $module module"
            
            # Install to rootfs
            if [[ -f *.ko ]]; then
                mkdir -p "$ROOTFS_DIR/lib/modules/$KERNEL_VERSION/extra/aurora"
                cp *.ko "$ROOTFS_DIR/lib/modules/$KERNEL_VERSION/extra/aurora/" 2>/dev/null || true
            fi
        else
            warn "No Makefile found for module: $module"
        fi
    done
    
    log "Kernel modules build completed"
}

# Create basic root filesystem
create_rootfs() {
    log "Creating Aurora-OS root filesystem"
    
    # Basic directory structure
    mkdir -p "$ROOTFS_DIR"/{bin,sbin,etc,dev,proc,sys,tmp,var,usr,opt}
    mkdir -p "$ROOTFS_DIR"/{usr/{bin,sbin,lib,share},var/{lib,log,run}}
    mkdir -p "$ROOTFS_DIR"/{etc/{init.d,rc.d,udev,sysconfig},lib/modules}
    
    # Essential device nodes
    mknod -m 666 "$ROOTFS_DIR/dev/null" c 1 3
    mknod -m 666 "$ROOTFS_DIR/dev/zero" c 1 5
    mknod -m 666 "$ROOTFS_DIR/dev/tty" c 5 0
    mknod -m 666 "$ROOTFS_DIR/dev/console" c 5 1
    mknod -m 600 "$ROOTFS_DIR/dev/initctl" p
    
    # Basic configuration files
    cat > "$ROOTFS_DIR/etc/passwd" << 'EOF'
root:x:0:0:root:/root:/bin/bash
nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin
EOF
    
    cat > "$ROOTFS_DIR/etc/group" << 'EOF'
root:x:0:
nobody:x:65534:
EOF
    
    cat > "$ROOTFS_DIR/etc/fstab" << 'EOF'
proc /proc proc defaults 0 0
sysfs /sys sysfs defaults 0 0
devtmpfs /dev devtmpfs defaults 0 0
tmpfs /run tmpfs defaults 0 0
EOF
    
    # Aurora-OS specific config
    cat > "$ROOTFS_DIR/etc/aurora-release" << 'EOF'
Aurora-OS 1.0.0 "Enterprise Edition"
Next-Generation Operating System with AI
EOF
    
    log "Basic root filesystem created"
}

# Install Aurora system files
install_aurora_system() {
    log "Installing Aurora-OS system files"
    
    # Copy Aurora init
    cp "$AURORA_ROOT/system/aurora-init" "$ROOTFS_DIR/init"
    chmod +x "$ROOTFS_DIR/init"
    
    # Copy Aurora system libraries
    mkdir -p "$ROOTFS_DIR/usr/lib/aurora"
    cp -r "$AURORA_ROOT/system"/* "$ROOTFS_DIR/usr/lib/aurora/" 2>/dev/null || true
    
    # Create essential links
    cd "$ROOTFS_DIR"
    ln -sf init /sbin/init
    ln -sf /usr/lib/aurora/aurora-init /usr/sbin/aurora-init
    
    log "Aurora system files installed"
}

# Install essential tools
install_tools() {
    log "Installing essential tools"
    
    # Basic shell and utilities (from host system)
    local essential_tools=(
        "/bin/bash"
        "/bin/sh"
        "/bin/cat"
        "/bin/ls"
        "/bin/mkdir"
        "/bin/mknod"
        "/bin/mount"
        "/bin/umount"
        "/bin/ps"
        "/bin/pwd"
        "/bin/sleep"
        "/bin/sync"
        "/sbin/modprobe"
        "/sbin/lsmod"
        "/usr/bin/vi"
    )
    
    for tool in "${essential_tools[@]}"; do
        if [[ -f "$tool" ]]; then
            # Copy tool and its dependencies
            cp "$tool" "$ROOTFS_DIR$tool" 2>/dev/null || true
            
            # Copy library dependencies
            ldd "$tool" 2>/dev/null | grep "=>" | awk '{print $3}' | while read lib; do
                if [[ -f "$lib" ]]; then
                    mkdir -p "$ROOTFS_DIR$(dirname "$lib")"
                    cp "$lib" "$ROOTFS_DIR$lib" 2>/dev/null || true
                fi
            done
        fi
    done
    
    log "Essential tools installed"
}

# Create initramfs
create_initramfs() {
    log "Creating Aurora initramfs"
    
    cd "$ROOTFS_DIR"
    
    # Create initramfs
    find . | cpio -o -H newc | gzip > "$ISO_DIR/boot/initrd.gz" || error "Failed to create initramfs"
    
    log "Initramfs created: $ISO_DIR/boot/initrd.gz"
}

# Setup GRUB configuration
setup_grub() {
    log "Setting up GRUB bootloader"
    
    mkdir -p "$ISO_DIR/boot/grub"
    
    # Copy GRUB configuration
    cp "$AURORA_ROOT/bootloader/grub.cfg" "$ISO_DIR/boot/grub/" || warn "GRUB config not found"
    
    # Create GRUB theme directory
    mkdir -p "$ISO_DIR/boot/grub/themes/aurora"
    
    # Copy GRUB theme if available
    if [[ -f "$AURORA_ROOT/bootloader/aurora-os.png" ]]; then
        cp "$AURORA_ROOT/bootloader/aurora-os.png" "$ISO_DIR/boot/grub/themes/aurora/" 2>/dev/null || true
    fi
    
    log "GRUB configuration completed"
}

# Create ISO image
create_iso() {
    log "Creating Aurora-OS ISO image"
    
    cd "$BUILD_DIR"
    
    # Create ISO with GRUB
    if command -v grub-mkrescue >/dev/null 2>&1; then
        grub-mkrescue -o aurora-os.iso iso || error "Failed to create ISO with grub-mkrescue"
    else
        # Fallback to xorriso
        xorriso -as mkisofs \
            -iso-level 3 \
            -full-iso9660-filenames \
            -volid "Aurora-OS" \
            -appid "Aurora-OS Enterprise Edition" \
            -publisher "Aurora-OS Enterprises" \
            -preparer "Aurora-OS Build System" \
            -eltorito-boot boot/grub/i386-pc/eltorito.img \
            -no-emul-boot \
            -boot-load-size 4 \
            -boot-info-table \
            -output aurora-os.iso \
            iso || error "Failed to create ISO with xorriso"
    fi
    
    log "ISO image created: $BUILD_DIR/aurora-os.iso"
    
    # Show ISO information
    if [[ -f "$BUILD_DIR/aurora-os.iso" ]]; then
        local size=$(du -h "$BUILD_DIR/aurora-os.iso" | cut -f1)
        log "ISO size: $size"
        
        # Generate checksum
        sha256sum "$BUILD_DIR/aurora-os.iso" > "$BUILD_DIR/aurora-os.iso.sha256"
        log "SHA256 checksum: $BUILD_DIR/aurora-os.iso.sha256"
    fi
}

# Run tests on built ISO
test_iso() {
    log "Running ISO validation tests"
    
    if [[ ! -f "$BUILD_DIR/aurora-os.iso" ]]; then
        error "ISO file not found"
    fi
    
    # Check ISO integrity
    if command -v isoinfo >/dev/null 2>&1; then
        log "Validating ISO structure"
        isoinfo -d -i "$BUILD_DIR/aurora-os.iso" >/dev/null || warn "ISO validation failed"
    fi
    
    # Check kernel presence
    if ! isoinfo -i "$BUILD_DIR/aurora-os.iso" -x "/boot/vmlinuz" >/dev/null 2>&1; then
        error "Kernel not found in ISO"
    fi
    
    # Check initramfs presence
    if ! isoinfo -i "$BUILD_DIR/aurora-os.iso" -x "/boot/initrd.gz" >/dev/null 2>&1; then
        error "Initramfs not found in ISO"
    fi
    
    log "ISO validation completed successfully"
}

# Main build function
main() {
    log "Starting Aurora-OS ISO build process"
    log "Build directory: $BUILD_DIR"
    log "Source directory: $AURORA_ROOT"
    
    # Check if running as root (needed for some operations)
    if [[ $EUID -eq 0 ]]; then
        warn "Running as root - this may affect the generated ISO"
    fi
    
    # Execute build steps
    check_deps
    clean_build
    build_kernel
    build_modules
    create_rootfs
    install_aurora_system
    install_tools
    create_initramfs
    setup_grub
    create_iso
    test_iso
    
    log "🎉 Aurora-OS ISO build completed successfully!"
    log "ISO location: $BUILD_DIR/aurora-os.iso"
    
    # Show usage instructions
    echo ""
    echo "=== Usage Instructions ==="
    echo "1. Test in QEMU:"
    echo "   qemu-system-x86_64 -m 2G -cdrom $BUILD_DIR/aurora-os.iso -boot d"
    echo ""
    echo "2. Create bootable USB:"
    echo "   sudo dd if=$BUILD_DIR/aurora-os.iso of=/dev/sdX bs=4M status=progress"
    echo ""
    echo "3. Deploy to enterprise:"
    echo "   See $AURORA_ROOT/docs/deployment.md for enterprise deployment guides"
    echo ""
    
    return 0
}

# Handle command line arguments
case "${1:-}" in
    "clean")
        clean_build
        ;;
    "kernel")
        build_kernel
        ;;
    "modules")
        build_modules
        ;;
    "test")
        test_iso
        ;;
    "help"|"-h"|"--help")
        echo "Aurora-OS ISO Builder"
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  (none)  - Build complete ISO"
        echo "  clean   - Clean build directory"
        echo "  kernel  - Build kernel only"
        echo "  modules - Build kernel modules only"
        echo "  test    - Test existing ISO"
        echo "  help    - Show this help"
        ;;
    *)
        main "$@"
        ;;
esac