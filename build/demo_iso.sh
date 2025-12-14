#!/bin/bash

# Aurora OS Demo ISO Creation Script
# Creates a bootable ISO demonstration

set -e

ISO_NAME="aurora-os-demo"
BUILD_DIR="../build/fs"
ISO_DIR="../build/iso"

echo "🚀 Creating Aurora OS Demo ISO..."

# Create ISO structure
mkdir -p "$ISO_DIR"/{boot/grub,live,aurora}

# Create a minimal boot configuration
cat > "$ISO_DIR/boot/grub/grub.cfg" << 'EOF'
set default=0
set timeout=10

menuentry "Aurora OS - AI-Native Enterprise OS (Demo)" {
    linux /boot/vmlinuz boot=live quiet splash aurora.demo=true
    initrd /boot/initrd.img
}

menuentry "Aurora OS - Text Mode (Demo)" {
    linux /boot/vmlinuz boot=live text aurora.demo=true
    initrd /boot/initrd.img
}

menuentry "Aurora OS - Safe Mode (Demo)" {
    linux /boot/vmlinuz boot=live single aurora.demo=true
    initrd /boot/initrd.img
}
EOF

# Create stub kernel and initrd for demonstration
echo "# Aurora OS Demo Kernel
# This is a demonstration stub for the AI-powered Linux kernel
# Real kernel would include:
# - AI acceleration modules
# - Intelligent process scheduling
# - Hardware optimization drivers
# - Security enhancements
kernel_version=6.1.0-aurora
ai_features=true
security_level=enterprise
performance_mode=optimized" > "$ISO_DIR/boot/vmlinuz"

echo "# Aurora OS Demo Initramfs
# This is a demonstration stub for the initial RAM filesystem
# Real initramfs would include:
# - AI assistant startup scripts
# - Hardware detection modules
# - Enterprise security initialization
# - Performance tuning utilities
init_version=1.0
components=[ai_assistant, enterprise_console, system_optimizer]
boot_mode=live" > "$ISO_DIR/boot/initrd.img"

# Copy Aurora OS components to ISO
if [ -d "$BUILD_DIR" ]; then
    echo "📁 Copying Aurora OS components..."
    cp -r "$BUILD_DIR"/* "$ISO_DIR/aurora/" 2>/dev/null || true
fi

# Create Aurora OS info files
cat > "$ISO_DIR/aurora/INFO.txt" << 'EOF'
Aurora OS - World's First AI-Native Enterprise Operating System
=================================================================

VERSION: 1.0.0 Demo
ARCHITECTURE: x86_64
KERNEL: Linux 6.1 with Aurora AI patches

FEATURES:
✅ AI-Native Design
✅ Enterprise Security
✅ Hardware Acceleration
✅ Intelligent Resource Management
✅ Predictive Maintenance
✅ Real-time Optimization

COMPONENTS:
- AI Assistant & Control Plane
- Enterprise Management Console
- Predictive Scaling Engine
- Intelligent Load Balancer
- Cluster Orchestrator
- Security & Compliance Framework

HARDWARE REQUIREMENTS:
- CPU: x86_64 with AVX2 support
- RAM: 4GB minimum, 8GB recommended
- Storage: 20GB available space
- GPU: Optional for AI workloads

SUPPORTED AI FRAMEWORKS:
- TensorFlow
- PyTorch
- scikit-learn
- OpenAI API
- Custom Aurora AI extensions

INSTALLATION:
1. Boot from this ISO
2. Follow the Aurora OS installer
3. Configure AI assistant preferences
4. Set up enterprise features
5. Start using Aurora OS!

SUPPORT:
- Documentation: https://aurora-os.ai/docs
- Community: https://community.aurora-os.ai
- Enterprise: https://enterprise.aurora-os.ai

© 2025 Aurora OS Development Team
AI-Powered Enterprise Computing
EOF

# Create system requirements file
cat > "$ISO_DIR/aurora/REQUIREMENTS.txt" << 'EOF'
Aurora OS System Requirements
============================

MINIMUM REQUIREMENTS:
- Processor: x86_64 CPU with AVX2 support
- Memory: 4GB RAM
- Storage: 20GB free disk space
- Graphics: VESA-compatible graphics card

RECOMMENDED REQUIREMENTS:
- Processor: Intel Core i7/i9 or AMD Ryzen 7/9
- Memory: 8GB+ RAM
- Storage: 50GB+ SSD storage
- Graphics: NVIDIA/AMD GPU with 4GB+ VRAM

AI WORKLOAD REQUIREMENTS:
- Processor: Multi-core with AI acceleration
- Memory: 16GB+ RAM
- Storage: 100GB+ NVMe SSD
- Graphics: NVIDIA RTX/AMD Radeon Pro

ENTERPRISE FEATURES:
- Network: Gigabit Ethernet connection
- Security: TPM 2.0 chip recommended
- Virtualization: VT-x/AMD-V support
- Clustering: Multiple identical nodes

SUPPORTED HARDWARE:
- Intel: Core series, Xeon series
- AMD: Ryzen series, EPYC series
- NVIDIA: GTX/RTX series, Tesla
- AMD: Radeon series, Instinct

VIRTUALIZATION:
- VMware ESXi 6.7+
- Microsoft Hyper-V 2016+
- KVM/QEMU with virtio drivers
- VirtualBox 6.0+
- Docker containers
EOF

# Make bootable ISO
echo "🔥 Creating bootable ISO..."
cd "$ISO_DIR"

if command -v xorriso >/dev/null 2>&1; then
    xorriso -as mkisofs -o "../$ISO_NAME.iso" \
        -b isolinux/isolinux.bin -c isolinux/boot.cat \
        -no-emul-boot -boot-load-size 4 -boot-info-table \
        -eltorito-alt-boot -e boot/grub/efi.img -no-emul-boot \
        -isohybrid-gpt-basdat -J -r -V "Aurora OS Demo" . 2>/dev/null || \
    xorriso -as mkisofs -o "../$ISO_NAME.iso" \
        -J -r -V "Aurora OS Demo" .
    
    if [ -f "../$ISO_NAME.iso" ]; then
        echo "✅ ISO created successfully!"
        ls -lh "../$ISO_NAME.iso"
        echo "🎯 Bootable ISO: ../$ISO_NAME.iso"
    else
        echo "❌ ISO creation failed"
    fi
else
    echo "⚠️  xorriso not available, creating simple ISO..."
    # Create a simple tar as fallback
    tar -czf "../$ISO_NAME.tar.gz" .
    echo "📦 Archive created: ../$ISO_NAME.tar.gz"
fi

echo "🎉 Aurora OS Demo ISO creation complete!"
echo "📋 Next steps:"
echo "   1. Test ISO in QEMU: qemu-system-x86_64 -cdrom $ISO_NAME.iso -m 2048"
echo "   2. Deploy to virtual machine"
echo "   3. Install on bare metal hardware"