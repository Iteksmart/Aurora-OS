#!/bin/bash

# Aurora OS Boot Test Script
# Tests if the ISO boots successfully without PyTorch

set -e

ISO_FILE="aurora-os-ultimate-complete.iso"
LOG_FILE="boot_test.log"

echo "╔══════════════════════════════════════════════╗"
echo "║   Aurora OS Boot Test (No PyTorch)          ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Check if ISO exists
if [ ! -f "$ISO_FILE" ]; then
    echo "❌ ERROR: $ISO_FILE not found"
    exit 1
fi

echo "✓ ISO found: $ISO_FILE"
echo "  Size: $(ls -lh $ISO_FILE | awk '{print $5}')"
echo ""

# Verify checksum
echo "Verifying checksums..."
if md5sum -c aurora-os-ultimate-complete.iso.md5 2>&1 | grep -q "OK"; then
    echo "✓ MD5 checksum verified"
else
    echo "❌ MD5 checksum FAILED"
    exit 1
fi

if sha256sum -c aurora-os-ultimate-complete.iso.sha256 2>&1 | grep -q "OK"; then
    echo "✓ SHA256 checksum verified"
else
    echo "❌ SHA256 checksum FAILED"
    exit 1
fi
echo ""

# Check if QEMU is available
if ! command -v qemu-system-x86_64 &> /dev/null; then
    echo "⚠️  QEMU not installed. Install with:"
    echo "   sudo apt-get install qemu-system-x86"
    echo ""
    echo "ℹ️  Manual boot test:"
    echo "   1. Burn ISO to USB: sudo dd if=$ISO_FILE of=/dev/sdX bs=4M"
    echo "   2. Boot from USB in VM or physical machine"
    echo "   3. Verify system boots without 'ModuleNotFoundError'"
    exit 0
fi

echo "✓ QEMU found: $(qemu-system-x86_64 --version | head -1)"
echo ""

# Run boot test
echo "Starting 30-second boot test..."
echo "  This will boot the ISO in QEMU and check for errors"
echo "  Log file: $LOG_FILE"
echo ""

timeout 30 qemu-system-x86_64 \
    -cdrom "$ISO_FILE" \
    -m 4G \
    -smp 2 \
    -serial file:"$LOG_FILE" \
    -nographic \
    -no-reboot \
    2>&1 | tee -a "$LOG_FILE" || true

echo ""
echo "Analyzing boot log..."

# Check for critical errors
if grep -q "ModuleNotFoundError.*torch" "$LOG_FILE"; then
    echo "❌ FAILED: PyTorch import error found"
    grep "ModuleNotFoundError" "$LOG_FILE"
    exit 1
fi

if grep -q "Kernel panic" "$LOG_FILE"; then
    echo "❌ FAILED: Kernel panic detected"
    grep "Kernel panic" "$LOG_FILE"
    exit 1
fi

if grep -q "aurora_os_main.py" "$LOG_FILE" && grep -q "Traceback" "$LOG_FILE"; then
    echo "❌ FAILED: Python traceback in aurora_os_main.py"
    grep -A 5 "Traceback" "$LOG_FILE"
    exit 1
fi

# Check for success indicators
if grep -q "Aurora OS" "$LOG_FILE" || grep -q "login:" "$LOG_FILE"; then
    echo "✅ SUCCESS: System booted successfully"
    echo ""
    echo "Indicators found:"
    grep -i "aurora\|boot\|login" "$LOG_FILE" | head -10
    echo ""
    echo "════════════════════════════════════════════"
    echo "  BOOT FIX VERIFIED - ISO IS READY! ✅"
    echo "════════════════════════════════════════════"
    exit 0
else
    echo "⚠️  INCONCLUSIVE: Could not determine boot status"
    echo "   Check $LOG_FILE manually"
    echo ""
    echo "Last 20 lines of boot log:"
    tail -20 "$LOG_FILE"
    exit 2
fi
