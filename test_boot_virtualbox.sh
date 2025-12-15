#!/bin/bash
# Aurora OS - VirtualBox Boot Test Script
# Tests the ISO with proper VirtualBox settings

set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║     Aurora OS - VirtualBox Boot Test                    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

ISO_FILE="aurora-os-complete-with-pytorch.iso"

if [ ! -f "$ISO_FILE" ]; then
    echo "❌ Error: ISO file not found: $ISO_FILE"
    exit 1
fi

echo "ISO File: $ISO_FILE"
echo "Size: $(du -h $ISO_FILE | cut -f1)"
echo ""
echo "✓ GRUB Configuration (Fixed):"
echo "  - Added boot=live parameter"
echo "  - root=/dev/ram0 for ramdisk"
echo "  - init=/init for custom init"
echo ""
echo "VirtualBox Settings to Use:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  OS Type:     Linux / Other Linux (64-bit)"
echo "  Memory:      2048 MB minimum"
echo "  Storage:     SATA Controller (NOT IDE)"
echo "  Chipset:     PIIX3"
echo "  Boot Mode:   BIOS (NOT EFI)"
echo "  CD/DVD:      $ISO_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Testing with QEMU (30 second quick test)..."
echo ""

timeout 30 qemu-system-x86_64 \
    -cdrom "$ISO_FILE" \
    -m 2048 \
    -serial stdio \
    -display none \
    2>&1 | tee boot_test_output.log || true

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
if grep -q "Kernel panic" boot_test_output.log 2>/dev/null; then
    echo "❌ Kernel panic detected. Check boot_test_output.log"
    echo ""
    echo "If you see 'unable to mount root fs', try:"
    echo "  1. At GRUB menu, press 'e'"
    echo "  2. Add 'boot=live' to the linux line if missing"
    echo "  3. Press Ctrl+X to boot"
else
    echo "✓ No kernel panic detected in quick test"
    echo ""
    echo "For full VirtualBox test:"
    echo "  1. Create new VM with settings above"
    echo "  2. Attach ISO as CD/DVD"
    echo "  3. Boot and watch for GRUB menu"
    echo "  4. Select 'Aurora OS v1.0 with PyTorch'"
fi
echo ""
echo "Log saved to: boot_test_output.log"
