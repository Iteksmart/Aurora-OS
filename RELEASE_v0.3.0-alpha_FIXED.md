# Aurora OS v0.3.0-alpha - AI-Enhanced Linux Distribution

## 🎯 What is Aurora OS?

Aurora OS is a **Linux-based distribution** with integrated AI capabilities, built on **Linux kernel 6.1.115 LTS**. This alpha release demonstrates the core concept: a standard Linux system enhanced with optional AI automation features.

**Release Date:** December 13, 2025  
**Status:** Alpha - Testing & Feedback Phase  
**License:** GPL v2

---

## 📦 Available Editions

| Edition | Size | Description | Use Case |
|---------|------|-------------|----------|
| **Complete Edition** | 519 MB | Full system + Python stdlib + AI features | **Recommended** - Full experience |
| **Framework Lite** | 42 MB | Minimal system + AI framework scripts only | Developers, minimal installs |

**Note:** Currently, both Complete and Base editions share the same 519MB ISO. The AI features (8 Python scripts totaling ~6KB) are runtime-optional. Future releases will provide a distinct minimal base ISO (~250-300 MB).

---

## 🚀 Key Features

### Core System
- **Linux Kernel:** 6.1.115 LTS (5.7 MB compiled binary)
- **Python Runtime:** 3.12 with complete standard library (54 MB)
- **Init System:** systemd (PID 1) + Aurora AI services
- **Package Manager:** Custom Aurora package system
- **Shell:** BusyBox utilities + Aurora shell extensions

### AI Capabilities (Runtime-Optional)
These features are **offline-capable after initial model download**:

1. **Local AI Assistant** - Llama/Ollama integration (requires model download ~4GB)
2. **AI Taskbar Integration** - Click-to-chat interface
3. **Agentic Task Completion** - Automated workflow execution
4. **System Intelligence** - Auto-configuration and optimization

### System Features
5. **Auto Driver Detection** - Plug-and-play hardware support
6. **3-Tier Settings UI** - System/Admin/User configuration panels
7. **Theme Manager** - 7+ professional themes (Nord, Catppuccin, Tokyo Night, etc.)
8. **Windows App Support** - Wine/Proton compatibility layer

**Important:** AI models are **NOT included** in the ISO. First boot will prompt for model download (~4GB) or you can skip to use the system without AI features.

---

## 📥 Downloads

### Complete Edition (Recommended)

**File:** `aurora-os-ultimate-complete.iso`  
**Size:** 519 MB  
**SHA256:** `f3190ed23314773a75f0425a336368246d8779ceb4e314e4b4d6274c39a74b8d`

```bash
# Download
wget https://github.com/Iteksmart/Aurora-OS/releases/download/v0.3.0-alpha/aurora-os-ultimate-complete.iso

# Verify checksum
wget https://github.com/Iteksmart/Aurora-OS/releases/download/v0.3.0-alpha/aurora-os-ultimate-complete.iso.sha256
sha256sum -c aurora-os-ultimate-complete.iso.sha256
# Expected: aurora-os-ultimate-complete.iso: OK
```

### Framework Lite Edition

**File:** `aurora-os-ultimate.iso`  
**Size:** 42 MB  
**Use:** Minimal installation, developer testing

### Kernel Binary

**File:** `vmlinuz`  
**Size:** 5.7 MB  
**Version:** Linux 6.1.115 LTS

---

## 🧪 Quick Test (5 Minutes)

### 1. Verify ISO Integrity
```bash
# Check file type
file aurora-os-ultimate-complete.iso
# Expected: ISO 9660 CD-ROM filesystem data

# Verify bootability
xorriso -indev aurora-os-ultimate-complete.iso -report_el_torito as_mkisofs
# Should show El-Torito boot information
```

### 2. Boot in QEMU
```bash
qemu-system-x86_64 \
  -cdrom aurora-os-ultimate-complete.iso \
  -m 4096 \
  -smp 2 \
  -enable-kvm
```

### 3. Expected First Boot
```bash
# After boot, verify:
uname -a
# Should show: Linux aurora 6.1.115 ...

ls /usr/lib/systemd
# Should show systemd installation

ps aux | grep aurora
# Should show Aurora services (if AI features enabled)
```

---

## 🔧 What's Included (Technical Details)

### Base System (~519 MB breakdown)
- **Kernel:** 5.7 MB (Linux 6.1.115 LTS compiled binary)
- **Python 3.12 stdlib:** 54 MB (complete standard library)
- **System libraries:** ~100 MB (glibc, libm, libdl, libpthread, libz)
- **BusyBox:** ~1 MB (150+ Unix utilities)
- **Initramfs:** ~340 MB (compressed root filesystem)
- **GRUB bootloader:** ~20 MB
- **AI feature scripts:** ~6 KB (8 Python scripts)

### Init Sequence
1. **GRUB** loads `vmlinuz` and `initramfs`
2. **Kernel** (6.1.115) initializes hardware
3. **systemd** (PID 1) starts as init system
4. **Aurora services** start as systemd units:
   - `aurora-ai.service` - AI engine (optional)
   - `aurora-shell.service` - Desktop environment
   - `aurora-drivers.service` - Hardware detection

### File System Structure
```
/
├── bin/          # BusyBox symlinks + Aurora commands
├── etc/          # Configuration files
│   └── systemd/  # systemd unit files
├── lib/          # System libraries
├── opt/          # Aurora AI components
│   ├── aurora/   # Core Aurora system
│   ├── ollama/   # AI engine (models separate)
│   └── wine/     # Windows compatibility
├── usr/
│   ├── bin/      # User commands (aurora-ai, aurora-aura, etc.)
│   └── lib/
│       └── python3.12/  # Python standard library (54 MB)
└── var/          # Variable data
```

---

## 🎯 Command Reference

Once booted, use these commands:

```bash
# AI Commands (require model download on first use)
aurora-ai "help me configure wifi"    # Local AI assistant
aurora-aura                            # Life OS assistant

# System Commands
aurora-settings                        # Open settings UI
aurora-theme catppuccin               # Change theme
aurora-drivers                        # Manage drivers
aurora-status                         # System status

# Standard Linux commands work as expected
ls, cat, grep, find, etc.
```

---

## ⚠️ Known Limitations (Alpha Release)

1. **AI Models Not Included** - First boot requires ~4GB download for AI features (or skip to use base system)
2. **No Persistence Yet** - Changes don't survive reboot (live ISO only)
3. **Limited Hardware Support** - Tested primarily on QEMU/VirtualBox
4. **No Installer** - Currently live-boot only; installer coming in v0.4.0-beta
5. **systemd Init Only** - No alternative init system support yet

---

## 📋 Verification Checklist

Use this to verify Aurora OS authenticity:

- [ ] ISO file downloads completely (519 MB)
- [ ] SHA256 checksum matches
- [ ] `file` command shows ISO 9660 filesystem
- [ ] `xorriso` reports El-Torito boot capability
- [ ] Boots successfully in QEMU
- [ ] `uname -a` shows Linux 6.1.115
- [ ] `ls /usr/lib/systemd` shows systemd installation
- [ ] `ls /usr/bin/aurora-*` shows Aurora commands

---

## 🐛 Reporting Issues

Found a bug? Help us improve:

1. **Boot Issues:** Check QEMU/VirtualBox logs
2. **Feature Requests:** Open GitHub issue with `[Feature]` tag
3. **Security Concerns:** Email via GitHub profile (security@...)

**Include in reports:**
- ISO edition and size
- VM software and version
- RAM allocated
- Boot logs (if available)

---

## 🔜 Roadmap to v0.4.0-beta

**Target:** Q1 2026

- [ ] Reduce base ISO to 250-300 MB (separate from complete)
- [ ] Add disk installer (not just live-boot)
- [ ] Include pre-downloaded AI models (optional)
- [ ] Expand hardware compatibility
- [ ] Add persistence layer
- [ ] GPU acceleration for AI

---

## 📚 Documentation

- **[README.md](../README.md)** - Project overview
- **[PUBLIC_VERIFICATION.md](../PUBLIC_VERIFICATION.md)** - Complete verification guide
- **[VERIFICATION_COMPLETE.md](../VERIFICATION_COMPLETE.md)** - Status report
- **[Build Instructions](../tools/)** - Build from source

---

## 🏆 Credits

- **Linux Kernel:** https://kernel.org (GPL v2)
- **Python:** https://python.org (PSF License)
- **Llama/Ollama:** https://ollama.ai
- **systemd:** https://systemd.io
- **Aurora Team:** https://github.com/Iteksmart

---

## 📞 Contact & Community

- **Repository:** https://github.com/Iteksmart/Aurora-OS
- **Issues:** https://github.com/Iteksmart/Aurora-OS/issues
- **Discussions:** https://github.com/Iteksmart/Aurora-OS/discussions
- **CI/CD Status:** https://github.com/Iteksmart/Aurora-OS/actions

---

**Aurora OS v0.3.0-alpha** - An honest Linux distribution with AI capabilities.  
Not production-ready. Not perfect. But **real, testable, and verifiable.**

*Built with transparency. Licensed under GPL v2.*
