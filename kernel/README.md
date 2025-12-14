# Aurora OS - Kernel Source

This directory contains the Linux kernel source with Aurora OS AI extensions.

## Kernel Versions

- **linux-6.1/** - Linux kernel 6.1.115 (Current stable)
- **linux-6.18.1/** - Reserved for future kernel version
- **ai_extensions/** - Aurora OS AI-enhanced kernel modules

## Building the Kernel

### Quick Build
```bash
cd linux-6.1
make defconfig
make -j$(nproc)
```

### Aurora OS Configuration
```bash
cd linux-6.1
make aurora_defconfig  # Aurora-specific config (when available)
make -j$(nproc)
```

### Installing Kernel Modules
```bash
cd linux-6.1
sudo make modules_install
sudo make install
```

## AI Extensions

The `ai_extensions/` directory contains Aurora OS-specific kernel modules:

- **ai_scheduler.ko** - AI-enhanced process scheduler
- **intent_fs.ko** - Intent-aware filesystem
- **mcp_core.ko** - Model Context Protocol kernel interface
- **neural_cache.ko** - AI-powered caching system

### Building AI Extensions
```bash
cd ai_extensions
make
sudo insmod ai_scheduler.ko
```

## Kernel Configuration

Aurora OS uses a custom kernel configuration optimized for AI workloads:

- **CONFIG_AURORA_AI=y** - Enable Aurora AI features
- **CONFIG_AURORA_MCP=y** - Enable MCP nervous system
- **CONFIG_AURORA_INTENT_ENGINE=y** - Enable intent engine
- **CONFIG_PREEMPT_RT=y** - Real-time preemption for AI responsiveness
- **CONFIG_CGROUPS=y** - Container support for AI isolation

## Development

### Kernel Version
Linux 6.1.115 - Long Term Support (LTS)

### Source
Downloaded from: https://kernel.org/

### License
GPL v2 (see COPYING in linux-6.1/)

### Aurora Modifications
All Aurora OS-specific modifications are maintained separately in the `ai_extensions/` directory to keep the base kernel clean and updateable.

## Resources

- [Linux Kernel Documentation](https://www.kernel.org/doc/html/latest/)
- [Aurora OS Kernel Guide](../docs/kernel-development.md)
- [AI Extensions API](../docs/ai-extensions-api.md)
