# Aurora OS v1.0.0 - Complete Build Guide

## 🎯 Overview

This guide provides comprehensive step-by-step instructions for building Aurora OS v1.0.0 from source, including kernel compilation, system integration, and ISO creation.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Repository Setup](#repository-setup)
3. [Build Environment](#build-environment)
4. [Kernel Configuration](#kernel-configuration)
5. [Kernel Compilation](#kernel-compilation)
6. [System Integration](#system-integration)
7. [ISO Creation](#iso-creation)
8. [Testing & Verification](#testing--verification)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Options](#advanced-options)

---

## 🔧 Prerequisites

### System Requirements

- **OS**: Ubuntu 20.04+ / Debian 11+ / Fedora 35+ / Arch Linux
- **RAM**: Minimum 8GB (16GB recommended for kernel compilation)
- **Storage**: 10GB free space (for kernel, build artifacts, and ISO)
- **CPU**: 64-bit x86_64 processor

### Required Packages

#### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install -y build-essential bc kmod cpio flex libelf-dev libssl-dev \
    bison dwarves libncurses-dev gcc-multilib libgcc-s1 \
    libncursesw6-dev libssl-dev rsync wget git qemu-system-x86 \
    grub-pc-bin xorriso mtools
```

#### Fedora/CentOS/RHEL:
```bash
sudo dnf install -y gcc gcc-c++ make bc kmod cpio flex elfutils-libelf-devel \
    openssl-devel bison dwarves ncurses-devel ncurses-libs \
    rsync wget git qemu-system-x86 grub2-tools xorriso mtools
```

#### Arch Linux:
```bash
sudo pacman -S --needed base-devel bc kmod cpio flex libelf \
    openssl bison dwarves ncurses rsync wget git qemu \
    grub xorriso mtools
```

### Development Tools

```bash
# Python build environment
pip3 install --user pyelftools

# Verify installation
gcc --version
make --version
python3 --version
```

---

## 📥 Repository Setup

### 1. Clone Aurora OS Repository

```bash
# Clone the main repository
gh repo clone Iteksmart/Aurora-OS
cd Aurora-OS

# OR using git directly
git clone https://github.com/Iteksmart/Aurora-OS.git
cd Aurora-OS
```

### 2. Verify Repository Structure

```bash
# Check key files exist
ls -la kernel/config/aurora_defconfig
ls -la tools/create_initramfs.sh
ls -la Makefile

# Verify kernel source will be downloaded
cat Makefile | grep KERNEL_URL
```

### 3. Setup Build Directories

```bash
# Create build environment
mkdir -p build/{kernel,system,ai,mcp,desktop,iso}
mkdir -p dist

# Set permissions
chmod +x tools/*.sh
```

---

## 🏗️ Build Environment

### 1. Environment Variables

```bash
# Set Aurora OS environment
export AURORA_HOME=$(pwd)
export AURORA_BUILD_DIR=$AURORA_HOME/build
export AURORA_DIST_DIR=$AURORA_HOME/dist
export KERNEL_VERSION=6.1

# Add to ~/.bashrc for persistence
echo 'export AURORA_HOME='"$AURORA_HOME" >> ~/.bashrc
echo 'export AURORA_BUILD_DIR='"$AURORA_BUILD_DIR" >> ~/.bashrc
echo 'export AURORA_DIST_DIR='"$AURORA_DIST_DIR" >> ~/.bashrc
```

### 2. Parallel Build Configuration

```bash
# Determine optimal parallel jobs
export MAKEFLAGS="-j$(nproc)"

# For systems with limited RAM, limit jobs
# export MAKEFLAGS="-j4"
```

---

## ⚙️ Kernel Configuration

### 1. Download Linux Kernel Source

```bash
# Method 1: Using Aurora OS Makefile (Recommended)
cd $AURORA_HOME
make kernel/linux-6.1/.config

# Method 2: Manual download
cd kernel
wget https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.1.tar.xz
tar -xf linux-6.1.tar.xz
```

### 2. Apply Aurora OS Configuration

```bash
cd kernel/linux-6.1

# Apply Aurora OS configuration
cp ../config/aurora_defconfig .config

# Verify configuration
make olddefconfig
```

### 3. Review Configuration (Optional)

```bash
# Browse kernel configuration
make menuconfig

# Search for Aurora-specific configs
grep -E "AURORA|MCP" .config

# Verify key features
grep -E "CONFIG_EXT4|CONFIG_SATA_AHCI|CONFIG_DRM_I915" .config
```

### 4. Configuration Validation

```bash
# Check for missing dependencies
make localmodconfig

# Verify kernel version
make kernelversion

# Expected output: 6.1.0
```

---

## 🔨 Kernel Compilation

### 1. Clean Build (Optional)

```bash
cd kernel/linux-6.1

# Clean previous builds
make clean
make mrproper

# Re-apply configuration if needed
cp ../config/aurora_defconfig .config
make olddefconfig
```

### 2. Compile Kernel

```bash
# Basic kernel compilation
make -j$(nproc)

# With verbose output for debugging
make -j$(nproc) V=1

# Monitor progress
watch -n 5 'ps aux | grep -E "(gcc|make)" | wc -l'
```

### 3. Compilation Verification

```bash
# Check kernel image exists
ls -la arch/x86/boot/bzImage

# Verify kernel size
stat arch/x86/boot/bzImage

# Check for compilation errors
echo $?
# Should return 0 for success
```

### 4. Build Kernel Modules

```bash
# Build all modules
make modules -j$(nproc)

# Install modules to build directory
make INSTALL_MOD_PATH=$AURORA_BUILD_DIR/kernel modules_install

# Verify modules
ls -la $AURORA_BUILD_DIR/kernel/lib/modules/$KERNEL_VERSION/
```

### 5. Compilation Statistics

```bash
# Build time and size
time make -j$(nproc) bzImage
du -sh kernel/linux-6.1

# Module count
find $AURORA_BUILD_DIR/kernel/lib/modules/$KERNEL_VERSION/ -name "*.ko" | wc -l
```

---

## 🔗 System Integration

### 1. Copy Kernel to Build Directory

```bash
# Copy kernel image
cp kernel/linux-6.1/arch/x86/boot/bzImage $AURORA_BUILD_DIR/kernel/vmlinuz-$KERNEL_VERSION

# Copy System.map for debugging
cp kernel/linux-6.1/System.map $AURORA_BUILD_DIR/kernel/

# Copy configuration
cp kernel/linux-6.1/.config $AURORA_BUILD_DIR/kernel/config-$KERNEL_VERSION
```

### 2. Build Aurora OS Components

```bash
cd $AURORA_HOME

# Build system services
make build-system

# Build AI control plane
make build-ai

# Build MCP system
make build-mcp

# Build desktop environment
make build-desktop
```

### 3. Create System Layout

```bash
# Create Aurora OS root structure
mkdir -p $AURORA_BUILD_DIR/aurora-os/{bin,etc,lib,opt,usr,var}

# Copy Aurora OS components
cp -r build/system/* $AURORA_BUILD_DIR/aurora-os/
cp -r build/ai/* $AURORA_BUILD_DIR/aurora-os/
cp -r build/mcp/* $AURORA_BUILD_DIR/aurora-os/
cp -r build/desktop/* $AURORA_BUILD_DIR/aurora-os/
```

---

## 💿 ISO Creation

### 1. Create Initramfs

```bash
# Build initramfs with Aurora OS components
make build/aurora-initramfs.img

# OR manually
chmod +x tools/create_initramfs.sh
tools/create_initramfs.sh

# Verify initramfs
ls -la build/aurora-initramfs.img
file build/aurora-initramfs.img
```

### 2. Create Bootable ISO

```bash
# Basic ISO creation
make iso

# Complete ISO with verification
make complete-iso

# ISO will be created at:
# $AURORA_BUILD_DIR/aurora-os.iso
```

### 3. ISO Verification

```bash
# Check ISO file
ls -la build/aurora-os.iso
file build/aurora-os.iso

# Verify ISO content
isoinfo -l -i build/aurora-os.iso

# Check bootable
isoinfo -d -i build/aurora-os.iso | grep -i bootable
```

---

## 🧪 Testing & Verification

### 1. QEMU Virtual Machine Testing

```bash
# Basic QEMU test
make run-vm

# Manual QEMU with specific options
qemu-system-x86_64 \
    -cdrom build/aurora-os.iso \
    -m 4096 \
    -enable-kvm \
    -cpu host \
    -boot d \
    -serial stdio \
    -display gtk

# Headless mode for automated testing
qemu-system-x86_64 \
    -cdrom build/aurora-os.iso \
    -m 2048 \
    -nographic \
    -serial mon:stdio \
    -boot d
```

### 2. Kernel Boot Testing

```bash
# Test kernel loading directly
qemu-system-x86_64 \
    -kernel build/kernel/vmlinuz-$KERNEL_VERSION \
    -initrd build/aurora-initramfs.img \
    -append "root=/dev/ram0 console=ttyS0" \
    -nographic \
    -m 1024
```

### 3. Build Verification Checklist

```bash
# Create verification script
cat > verify_build.sh << 'EOF'
#!/bin/bash

echo "🔍 Aurora OS Build Verification"
echo "==============================="

# Check kernel
if [ -f "build/kernel/vmlinuz-6.1" ]; then
    echo "✅ Kernel image exists"
    ls -lh build/kernel/vmlinuz-6.1
else
    echo "❌ Kernel image missing"
fi

# Check initramfs
if [ -f "build/aurora-initramfs.img" ]; then
    echo "✅ Initramfs exists"
    ls -lh build/aurora-initramfs.img
else
    echo "❌ Initramfs missing"
fi

# Check ISO
if [ -f "build/aurora-os.iso" ]; then
    echo "✅ ISO exists"
    ls -lh build/aurora-os.iso
else
    echo "❌ ISO missing"
fi

# Check Aurora OS components
if [ -d "build/aurora-os" ]; then
    echo "✅ Aurora OS components built"
    du -sh build/aurora-os
else
    echo "❌ Aurora OS components missing"
fi

echo "==============================="
echo "Verification complete!"
EOF

chmod +x verify_build.sh
./verify_build.sh
```

---

## 🔧 Troubleshooting

### Common Build Issues

#### 1. Kernel Compilation Errors

```bash
# Issue: Missing dependencies
# Solution: Install required packages
sudo apt install libelf-dev libssl-dev ncurses-dev

# Issue: Out of memory during compilation
# Solution: Reduce parallel jobs
export MAKEFLAGS="-j2"
make -j2

# Issue: Configuration errors
# Solution: Reset configuration
make mrproper
cp ../config/aurora_defconfig .config
make olddefconfig
```

#### 2. Module Loading Issues

```bash
# Check module dependencies
modprobe --show-depends ext4

# Verify module signatures
modinfo build/kernel/lib/modules/6.1/kernel/fs/ext4/ext4.ko

# Debug module loading
insmod build/kernel/lib/modules/6.1/kernel/fs/ext4/ext4.ko
dmesg | tail -10
```

#### 3. ISO Creation Problems

```bash
# Check GRUB installation
which grub-mkrescue
grub-mkrescue --version

# Verify ISO creation tools
which xorriso
xorriso --version

# Manual ISO creation (fallback)
grub-mkrescue -o build/aurora-os-manual.iso build/iso/
```

### Debug Mode Build

```bash
# Enable verbose build
export V=1
make -j1 V=1

# Debug kernel configuration
make kernelrelease
make kernelversion

# Check build logs
make 2>&1 | tee build.log
grep -i error build.log
```

---

## 🚀 Advanced Options

### 1. Cross-Compilation

```bash
# For ARM64 cross-compilation
export ARCH=arm64
export CROSS_COMPILE=aarch64-linux-gnu-

# Configure for ARM64
make menuconfig
# Select: System Type -> Platform selection -> arm64

# Build for ARM64
make -j$(nproc)
```

### 2. Custom Kernel Configuration

```bash
# Create minimal config
make localyesconfig
make localmodconfig

# Optimize for size
make allnoconfig
# Then manually enable required options

# Performance optimization
echo "CONFIG_CC_OPTIMIZE_FOR_PERFORMANCE=y" >> .config
make olddefconfig
```

### 3. Debug Kernel

```bash
# Enable debug options
echo "CONFIG_DEBUG_KERNEL=y" >> .config
echo "CONFIG_DEBUG_INFO=y" >> .config
echo "CONFIG_GDB_SCRIPTS=y" >> .config

# Build with debug symbols
make EXTRA_CFLAGS="-g" -j$(nproc)
```

### 4. Automated Build Script

```bash
cat > build_aurora_os.sh << 'EOF'
#!/bin/bash

set -e

AURORA_HOME=$(pwd)
KERNEL_VERSION=6.1

echo "🚀 Building Aurora OS v1.0.0"
echo "============================="

# Environment setup
export MAKEFLAGS="-j$(nproc)"

# Kernel build
echo "📦 Building Linux kernel..."
cd kernel/linux-6.1
make -j$(nproc) bzImage
make -j$(nproc) modules
make INSTALL_MOD_PATH=$AURORA_HOME/build/kernel modules_install
cd ../..

# System build
echo "🔧 Building Aurora OS components..."
make build-system
make build-ai
make build-mcp
make build-desktop

# ISO creation
echo "💿 Creating bootable ISO..."
make iso

# Verification
echo "✅ Verifying build..."
./verify_build.sh

echo "🎉 Aurora OS build complete!"
echo "📍 ISO location: build/aurora-os.iso"
EOF

chmod +x build_aurora_os.sh
```

---

## 📊 Build Statistics

### Expected Build Times

| Component | Time (8-core) | Time (4-core) | Time (2-core) |
|-----------|---------------|---------------|---------------|
| Kernel | 15-20 min | 30-40 min | 60-80 min |
| Modules | 10-15 min | 20-30 min | 40-60 min |
| System | 2-5 min | 5-10 min | 10-20 min |
| ISO | 1-2 min | 2-4 min | 4-8 min |

### Expected File Sizes

| Component | Size |
|-----------|------|
| Kernel (bzImage) | 8-12 MB |
| Modules | 100-200 MB |
| Initramfs | 20-50 MB |
| Aurora OS Components | 50-100 MB |
| Final ISO | 200-400 MB |

---

## 🎯 Success Checklist

After completing the build, verify:

- [ ] Kernel image exists: `build/kernel/vmlinuz-6.1`
- [ ] Modules installed: `build/kernel/lib/modules/6.1/`
- [ ] Initramfs created: `build/aurora-initramfs.img`
- [ ] ISO generated: `build/aurora-os.iso`
- [ ] ISO boots in QEMU
- [ ] Aurora OS components integrated
- [ ] All build logs show success

---

## 📞 Support

For build issues:

1. Check this guide first
2. Review build logs for errors
3. Verify all prerequisites are installed
4. Create an issue on GitHub: [Iteksmart/Aurora-OS Issues](https://github.com/Iteksmart/Aurora-OS/issues)

---

**Happy Building! 🚀**

*Aurora OS - The AI-Native Operating System*