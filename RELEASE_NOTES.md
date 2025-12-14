# Aurora OS v0.1.0 - Initial Production Release

🎉 **First bootable release of Aurora OS - The AI-Native Operating System**

## 📦 Download

**aurora-os.iso** (519 MB)
- **SHA256**: `9140badda5ff8ed09de31e0adcd60dc969c478ab9c7f8a899935f369e5278a8e`
- **MD5**: `5e01b38a149432676fef8beb201ab4dd`

## ✨ What's Included

### Core System
- **Linux Kernel 6.1.115 LTS** (5.7 MB compiled)
- **Python 3.12** + complete standard library (~300 MB)
- **System Libraries**: glibc, libm, libdl, libpthread, libz
- **BusyBox**: 150+ Unix utilities
- **GRUB Bootloader**: Multiple boot modes (Normal, Safe, Debug, Recovery)

### Aurora Components
- **AI Control Plane**: Intent engine and context management
- **MCP Nervous System**: Model Context Protocol integration
- **AI Assistant**: Voice and text interface
- **System Services**: Core Aurora system services
- **Security Framework**: Zero-trust security foundation

## 🚀 Quick Start

### Test in QEMU:
```bash
qemu-system-x86_64 -cdrom aurora-os.iso -m 4G -smp 2
```

### VirtualBox:
1. Create new VM: Linux 64-bit, 4GB RAM, 2 CPUs
2. Attach aurora-os.iso as CD-ROM
3. Boot

### Bootable USB:
```bash
sudo dd if=aurora-os.iso of=/dev/sdX bs=4M status=progress
```

## 📋 System Requirements

### Minimum:
- 64-bit x86 CPU
- 4 GB RAM
- 20 GB storage

### Recommended:
- Quad-core 2.0 GHz+ CPU
- 8 GB+ RAM
- 50 GB+ SSD storage

## 🔧 Boot Options

Available from GRUB menu:
- **Normal Boot** - Standard boot with full features
- **Safe Mode** - Boot with minimal drivers
- **Debug Mode** - Verbose logging enabled
- **Recovery Mode** - System recovery and repair
- **Memory Test** - Hardware diagnostics

## 📖 Documentation

- [README](https://github.com/Iteksmart/Aurora-OS#readme)
- [Installation Guide](https://github.com/Iteksmart/Aurora-OS#-installation--deployment)
- [Build Guide](https://github.com/Iteksmart/Aurora-OS/blob/main/BUILD_SUCCESS.md)
- [Architecture Overview](https://github.com/Iteksmart/Aurora-OS/blob/main/architecture_overview.md)

## 🐛 Known Issues

- Live system only (no installer yet - coming in v0.2.0)
- Limited hardware support (basic drivers only)
- No WiFi support (Ethernet only)
- AI components require manual activation

## 🚧 Coming in v0.2.0

- Full system installer
- Enhanced hardware support
- WiFi support
- Automatic AI activation
- Desktop environment

## 💬 Feedback

Please report issues at: https://github.com/Iteksmart/Aurora-OS/issues

---

**Aurora OS: The Digital Operator - Your Intelligent Partner in Digital Life**
