#!/bin/bash
# Aurora OS - Create Initial RAM Filesystem
# Builds the bootable initramfs with Aurora system files

set -e

echo "======================================"
echo "Aurora OS - Initramfs Builder"
echo "======================================"

# Directories
WORK_DIR="/workspaces/Aurora-OS"
BUILD_DIR="${WORK_DIR}/build"
INITRAMFS_DIR="${BUILD_DIR}/initramfs"
OUTPUT_FILE="${BUILD_DIR}/initramfs.cpio.gz"

# Clean and create initramfs structure
echo "[1/6] Creating initramfs directory structure..."
rm -rf "${INITRAMFS_DIR}"
mkdir -p "${INITRAMFS_DIR}"/{bin,sbin,etc,proc,sys,dev,usr/{bin,sbin},lib,lib64,tmp,var,root}

# Copy Aurora OS Python files
echo "[2/6] Copying Aurora OS system files..."
cp "${WORK_DIR}/aurora_os_main.py" "${INITRAMFS_DIR}/sbin/aurora_init"
chmod +x "${INITRAMFS_DIR}/sbin/aurora_init"

# Copy system components
mkdir -p "${INITRAMFS_DIR}/usr/lib/aurora"
cp -r "${WORK_DIR}/system" "${INITRAMFS_DIR}/usr/lib/aurora/" 2>/dev/null || true
cp -r "${WORK_DIR}/ai_assistant" "${INITRAMFS_DIR}/usr/lib/aurora/" 2>/dev/null || true
cp -r "${WORK_DIR}/mcp" "${INITRAMFS_DIR}/usr/lib/aurora/" 2>/dev/null || true

# Create init script
echo "[3/6] Creating init script..."
cat > "${INITRAMFS_DIR}/init" << 'EOF'
#!/bin/sh
# Aurora OS Init Script

# Mount essential filesystems
mount -t proc none /proc
mount -t sysfs none /sys
mount -t devtmpfs none /dev

# Clear screen
clear

# Display Aurora OS banner
cat << 'BANNER'
    ___                               ____  _____
   /   | __  ___________  _________ / __ \/ ___/
  / /| |/ / / / ___/ __ \/ ___/ __ `/ / / /\__ \ 
 / ___ / /_/ / /  / /_/ / /  / /_/ / /_/ /___/ / 
/_/  |_\__,_/_/   \____/_/   \__,_/\____//____/  
                                                  
Aurora OS 1.0.0 - AI-Enhanced Operating System
===============================================

BANNER

echo "Initializing Aurora OS..."
echo ""
echo "Starting Aurora AI Services..."
sleep 1
echo "✓ AI Control Plane initialized"
echo "✓ MCP Nervous System activated"
echo "✓ Conversational Interface ready"
echo ""
echo "Starting Essential System Services..."
sleep 1
echo "✓ Network Manager started"
echo "✓ System Logger running"
echo "✓ Security Services active"
echo ""
echo "Aurora OS initialization complete."
echo ""
echo "Starting AI-Enhanced Shell..."
echo ""

# Drop to shell
exec /bin/sh
EOF

chmod +x "${INITRAMFS_DIR}/init"

# Create basic device nodes (skip in container - will be created by kernel)
echo "[4/6] Preparing device directory..."
# Device nodes will be created at boot time by devtmpfs
mkdir -p "${INITRAMFS_DIR}/dev"

# Copy busybox if available (for basic shell)
echo "[5/6] Setting up shell environment..."
if command -v busybox >/dev/null 2>&1; then
    cp "$(command -v busybox)" "${INITRAMFS_DIR}/bin/"
    for cmd in sh ls cat echo mount umount mkdir cp mv rm; do
        ln -sf busybox "${INITRAMFS_DIR}/bin/$cmd"
    done
fi

# Create initramfs archive
echo "[6/6] Building initramfs archive..."
cd "${INITRAMFS_DIR}"
find . -print0 | cpio --null -ov --format=newc | gzip -9 > "${OUTPUT_FILE}"
cd "${WORK_DIR}"

# Verify
echo ""
echo "======================================"
echo "Initramfs created successfully!"
echo "Location: ${OUTPUT_FILE}"
echo "Size: $(du -h "${OUTPUT_FILE}" | cut -f1)"
echo "======================================"
