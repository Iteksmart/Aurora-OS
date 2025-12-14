#!/bin/bash

# Aurora OS v1.0.0 - Quick Start Build Script
# This script automates the basic Aurora OS build process

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Aurora OS banner
echo -e "${CYAN}"
echo "    ____             __       __          "
echo "   / __ \____ ______/ /______/ /_  __  __ "
echo "  / /_/ / __  / ___/ __/ ___/ __ \/ / / / "
echo " / ____/ /_/ (__  ) /_/ /  / /_/ / /_/ /  "
echo "/_/    \__,_/____/\__/_/  /_.___/\__, /   "
echo "    Aurora OS v1.0.0 Build System   /____/    "
echo ""
echo -e "${NC}"

# Check if we're in Aurora OS directory
if [ ! -f "Makefile" ] || [ ! -d "kernel" ]; then
    echo -e "${RED}❌ Error: Not in Aurora OS repository directory!${NC}"
    echo "Please run this script from the Aurora-OS repository root."
    exit 1
fi

# System check
echo -e "${BLUE}🔍 Checking build environment...${NC}"

# Check for required tools
missing_tools=()
tools=("gcc" "make" "python3" "wget" "git" "qemu-system-x86_64")

for tool in "${tools[@]}"; do
    if ! command -v "$tool" &> /dev/null; then
        missing_tools+=("$tool")
    fi
done

if [ ${#missing_tools[@]} -ne 0 ]; then
    echo -e "${RED}❌ Missing required tools: ${missing_tools[*]}${NC}"
    echo -e "${YELLOW}Please install them before continuing.${NC}"
    echo ""
    echo "Ubuntu/Debian: sudo apt install build-essential bc kmod cpio flex libelf-dev libssl-dev bison dwarves libncurses-dev gcc-multilib wget git qemu-system-x86 grub-pc-bin xorriso"
    echo "Fedora: sudo dnf install gcc gcc-c++ make bc kmod cpio flex elfutils-libelf-devel openssl-devel bison dwarves ncurses-devel rsync wget git qemu-system-x86 grub2-tools xorriso"
    exit 1
fi

# Check available memory
TOTAL_MEM=$(free -g | awk '/^Mem:/{print $2}')
if [ "$TOTAL_MEM" -lt 4 ]; then
    echo -e "${YELLOW}⚠️  Warning: Low RAM detected (${TOTAL_MEM}GB)${NC}"
    echo "Consider using fewer parallel jobs: export MAKEFLAGS=&quot;-j2&quot;"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check available disk space
FREE_SPACE=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$FREE_SPACE" -lt 5 ]; then
    echo -e "${RED}❌ Error: Insufficient disk space (${FREE_SPACE}GB available, need 5GB+)${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Build environment OK${NC}"

# Set environment variables
export AURORA_HOME=$(pwd)
export AURORA_BUILD_DIR=$AURORA_HOME/build
export AURORA_DIST_DIR=$AURORA_HOME/dist
export KERNEL_VERSION=6.1
export MAKEFLAGS="-j$(nproc)"

echo -e "${BLUE}🏗️  Build Configuration:${NC}"
echo "  Aurora Home: $AURORA_HOME"
echo "  Build Dir: $AURORA_BUILD_DIR"
echo "  Kernel Version: $KERNEL_VERSION"
echo "  Parallel Jobs: $(nproc)"
echo "  Free Memory: ${TOTAL_MEM}GB"
echo "  Free Disk: ${FREE_SPACE}GB"
echo ""

# Build options
echo -e "${PURPLE}🚀 Aurora OS Build Options:${NC}"
echo "1. Quick Build (ISO only) - Recommended"
echo "2. Full Build (All components + ISO)"
echo "3. Kernel Only"
echo "4. Exit"
echo ""
read -p "Select build option (1-4): " -n 1 -r
echo ""

case $REPLY in
    1)
        echo -e "${GREEN}🔥 Starting Quick Build (ISO)...${NC}"
        make iso
        ;;
    2)
        echo -e "${GREEN}🔥 Starting Full Build...${NC}"
        make complete-iso
        ;;
    3)
        echo -e "${GREEN}🔥 Starting Kernel Build...${NC}"
        make build-kernel
        ;;
    4)
        echo -e "${YELLOW}👋 Goodbye!${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}❌ Invalid option${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}🔍 Verifying build results...${NC}"

# Verification
BUILD_SUCCESS=true

if [ -f "build/aurora-os.iso" ]; then
    ISO_SIZE=$(du -h build/aurora-os.iso | cut -f1)
    echo -e "${GREEN}✅ Aurora OS ISO created: ${ISO_SIZE}${NC}"
else
    echo -e "${RED}❌ ISO not found${NC}"
    BUILD_SUCCESS=false
fi

if [ -f "build/kernel/vmlinuz-6.1" ]; then
    KERNEL_SIZE=$(du -h build/kernel/vmlinuz-6.1 | cut -f1)
    echo -e "${GREEN}✅ Kernel built: ${KERNEL_SIZE}${NC}"
else
    echo -e "${RED}❌ Kernel not found${NC}"
    BUILD_SUCCESS=false
fi

if [ -f "build/aurora-initramfs.img" ]; then
    INITRAMFS_SIZE=$(du -h build/aurora-initramfs.img | cut -f1)
    echo -e "${GREEN}✅ Initramfs created: ${INITRAMFS_SIZE}${NC}"
else
    echo -e "${RED}❌ Initramfs not found${NC}"
    BUILD_SUCCESS=false
fi

echo ""
if [ "$BUILD_SUCCESS" = true ]; then
    echo -e "${GREEN}🎉 Aurora OS build completed successfully!${NC}"
    echo ""
    echo -e "${CYAN}📁 Build Artifacts:${NC}"
    echo "  🖥️  Kernel: build/kernel/vmlinuz-6.1"
    echo "  📦 Initramfs: build/aurora-initramfs.img"
    echo "  💿 ISO Image: build/aurora-os.iso"
    echo ""
    echo -e "${CYAN}🚀 Next Steps:${NC}"
    echo "1. Test in QEMU: make run-vm"
    echo "2. Check the build guide: cat AURORA_OS_BUILD_GUIDE.md"
    echo "3. Burn ISO to USB or run in VM"
else
    echo -e "${RED}❌ Build failed! Check the output above for errors.${NC}"
    echo -e "${YELLOW}💡 Tip: Check AURORA_OS_BUILD_GUIDE.md for troubleshooting${NC}"
    exit 1
fi

echo ""
echo -e "${PURPLE}🌟 Thank you for building Aurora OS!${NC}"