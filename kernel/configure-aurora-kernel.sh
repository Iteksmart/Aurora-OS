#!/bin/bash

# Aurora-OS Kernel Configuration Script
# Configures and builds Linux kernel with Aurora-specific patches

set -e

KERNEL_VERSION="6.6.1"
KERNEL_URL="https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-${KERNEL_VERSION}.tar.xz"
BUILD_DIR=$(pwd)
AURORA_CONFIG="$(dirname "$0")/aurora_kernel_config"

echo "🚀 Configuring Aurora-OS Kernel v${KERNEL_VERSION}"

# Check if kernel source exists
if [ ! -d "linux-${KERNEL_VERSION}" ]; then
    echo "📥 Downloading Linux kernel source..."
    wget -O "linux-${KERNEL_VERSION}.tar.xz" "$KERNEL_URL"
    tar -xf "linux-${KERNEL_VERSION}.tar.xz"
    rm "linux-${KERNEL_VERSION}.tar.xz"
fi

cd "linux-${KERNEL_VERSION}"

# Apply Aurora-OS specific patches
echo "🔧 Applying Aurora-OS patches..."
for patch in "$(dirname "$0")/../patches/"*.patch; do
    if [ -f "$patch" ]; then
        echo "Applying patch: $(basename "$patch")"
        patch -p1 < "$patch"
    fi
done

# Copy Aurora kernel configuration
echo "⚙️  Applying Aurora-OS kernel configuration..."
if [ -f "$AURORA_CONFIG" ]; then
    cp "$AURORA_CONFIG" .config
else
    echo "📋 Creating default Aurora-OS kernel configuration..."
    make defconfig
    
    # Aurora-OS specific kernel options
    scripts/config --enable MODULES
    scripts/config --enable MODULE_UNLOAD
    scripts/config --enable BPF
    scripts/config --enable BPF_SYSCALL
    scripts/config --enable BPF_PRELOAD
    scripts/config --enable BPF_JIT
    scripts/config --enable BPF_LSM
    scripts/config --enable BPF_LRU_MAP
    scripts/config --enable BPF_STREAM_PARSER
    
    # eBPF for Aurora Intent Engine
    scripts/config --enable BPF_EVENTS
    scripts/config --enable BPF_KPROBE_OVERRIDE
    scripts/config --enable FUNCTION_TRACER
    scripts/config --enable DYNAMIC_FTRACE
    scripts/config --enable FTRACE_SYSCALLS
    
    # Aurora Sense kernel observability
    scripts/config --enable PERF_EVENTS
    scripts/config --enable HW_BREAKPOINT
    scripts/config --enable KPROBES
    scripts/config --enable UPROBES
    scripts/config --enable TRACEPOINTS
    scripts/config --enable DEBUG_KERNEL
    
    # Aurora Flow compositor support
    scripts/config --enable DRM
    scripts/config --enable DRM_KMS_HELPER
    scripts/config --enable DRM_FBDEV_EMULATION
    scripts/config --enable FB
    scripts/config --enable FRAMEBUFFER_CONSOLE
    scripts/config --enable BACKLIGHT_CLASS_DEVICE
    
    # Universal App Runtime compatibility
    scripts/config --enable BINFMT_ELF
    scripts/config --enable COMPAT_BINFMT_ELF
    scripts/config --enable BINFMT_MISC
    scripts/config --enable BINFMT_SCRIPT
    scripts/config --enable IA32_EMULATION
    scripts/config --enable X86_X32
    
    # Security and FIPS compliance
    scripts/config --enable SECURITY
    scripts/config --enable SECURITY_DMESG_RESTRICT
    scripts/config --enable SECURITY_YAMA
    scripts/config --enable SECURITY_SAFESETID
    scripts/config --enable SECURITY_LOCKDOWN_LSM
    scripts/config --enable SECURITY_LOCKDOWN_LSM_EARLY
    scripts/config --enable FIPS_SIGNATURE_SELFTEST
    
    # Networking for zero-config
    scripts/config --enable NET
    scripts/config --enable INET
    scripts/config --enable NETWORK_FILESYSTEMS
    scripts/config --enable NETFILTER
    scripts/config --enable NF_NAT
    scripts/config --enable IP_NF_IPTABLES
    scripts/config --enable IP6_NF_IPTABLES
    
    # File systems
    scripts/config --enable EXT4_FS
    scripts/config --enable BTRFS_FS
    scripts/config --enable XFS_FS
    scripts/config --enable OVERLAY_FS
    scripts/config --enable AUFS_FS  # for app containers
    
    # Self-healing and monitoring
    scripts/config --enable WATCHDOG
    scripts/config --enable SOFT_WATCHDOG
    scripts/config --enable HW_WATCHDOG
    scripts/config --enable RTC_DS1307
    
    # Virtualization support
    scripts/config --enable KVM
    scripts/config --enable KVM_INTEL
    scripts/config --enable KVM_AMD
    scripts/config --enable VHOST_NET
    scripts/config --enable VHOST_SCSI
    
    # Save configuration
    make savedefconfig
    cp defconfig "$AURORA_CONFIG"
fi

# Run oldconfig to handle new options
echo "🔄 Updating configuration for new kernel options..."
make olddefconfig

# Enable Aurora-specific modules for loading
echo "📦 Configuring Aurora kernel modules..."
cat >> .config << EOF

# Aurora-OS Specific Modules
CONFIG_AURORA_AIE=m
CONFIG_AURORA_SENSE=m
CONFIG_AURORA_FLOW=m
CONFIG_AURORA_DESKTOP=m
CONFIG_AURORA_RUNTIME=m

# Aurora Security Features
CONFIG_AURORA_LSM=y
CONFIG_AURORA_SELF_HEAL=y
CONFIG_AURORA_ZERO_CONFIG=y
CONFIG_AURORA_FIPS=y

# Aurora Performance
CONFIG_AURORA_SUB_100MS_AI=y
CONFIG_AURORA_TIME_TRAVEL=y
CONFIG_AURORA_AUTONOMOUS=y
EOF

# Final configuration
make olddefconfig

echo "✅ Aurora-OS kernel configuration completed!"
echo "Ready to build with: make -j\$(nproc) ARCH=x86_64"