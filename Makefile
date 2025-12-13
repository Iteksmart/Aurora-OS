# Aurora-OS Build System
# Next-Generation Enterprise Operating System

.PHONY: help clean iso run-vm test install kernel modules tools all

# Default target
help:
	@echo "Aurora-OS Build System"
	@echo "====================="
	@echo ""
	@echo "Available targets:"
	@echo "  all          - Build complete Aurora-OS"
	@echo "  kernel       - Build Linux kernel with Aurora patches"
	@echo "  modules      - Build Aurora kernel modules"
	@echo "  tools        - Build Aurora user-space tools"
	@echo "  iso          - Create bootable ISO image"
	@echo "  run-vm       - Run Aurora-OS in QEMU VM"
	@echo "  test         - Run comprehensive test suite"
	@echo "  install      - Install Aurora-OS to target"
	@echo "  clean        - Clean build artifacts"
	@echo "  help         - Show this help message"
	@echo ""
	@echo "Quick start:"
	@echo "  make iso && make run-vm"

# Build everything
all: kernel modules tools iso

# Build Linux kernel with Aurora configuration
kernel:
	@echo "Building Aurora-OS kernel..."
	@mkdir -p build/kernel
	@cd build/kernel && \
		../../../kernel/configure-aurora-kernel.sh && \
		make -j$(nproc) ARCH=x86_64 CROSS_COMPILE= && \
		make modules_install INSTALL_MOD_PATH=../../../build/rootfs ARCH=x86_64
	@echo "Kernel build completed"

# Build Aurora kernel modules
modules:
	@echo "Building Aurora kernel modules..."
	@cd core && make -C aie && make -C sense && make -C flow
	@echo "Aurora modules built"

# Build Aurora user-space tools
tools:
	@echo "Building Aurora user-space tools..."
	@mkdir -p build/tools
	@cd tools && make all
	@echo "Aurora tools built"

# Create bootable ISO image
iso: kernel modules tools
	@echo "Creating Aurora-OS ISO image..."
	@mkdir -p build/iso/boot/grub
	@mkdir -p build/iso/live
	@mkdir -p build/rootfs
	
	# Copy kernel and initramfs
	@cp build/kernel/arch/x86/boot/bzImage build/iso/boot/vmlinuz
	@cd build/rootfs && find . | cpio -o -H newc | gzip > ../iso/boot/initrd.gz
	
	# Copy Aurora system files
	@cp -r build/rootfs/* build/iso/
	@cp -r system/* build/iso/ 2>/dev/null || true
	
	# Create GRUB configuration
	@cp bootloader/grub.cfg build/iso/boot/grub/
	@cp bootloader/aurora-os.png build/iso/boot/grub/ 2>/dev/null || true
	
	# Create ISO
	@cd build && grub-mkrescue -o aurora-os.iso iso 2>/dev/null || \
		xorriso -as mkisofs -isohybrid-mbr /usr/lib/ISOLINUX/isohdpfx.bin \
		-c isolinux/boot.cat -b isolinux/isolinux.bin -no-emul-boot -boot-load-size 4 \
		-boot-info-table -o aurora-os.iso iso
	@echo "Aurora-OS ISO created: build/aurora-os.iso"

# Run Aurora-OS in QEMU VM
run-vm: iso
	@echo "Starting Aurora-OS in QEMU..."
	@qemu-system-x86_64 \
		-m 4G \
		-smp 2 \
		-enable-kvm \
		-cdrom build/aurora-os.iso \
		-boot d \
		-netdev user,id=net0,hostfwd=tcp::2222-:22 \
		-device e1000,netdev=net0 \
		-vga virtio \
		-display gtk

# Run Aurora-OS in debug mode
debug-vm: iso
	@echo "Starting Aurora-OS in debug mode..."
	@qemu-system-x86_64 \
		-m 2G \
		-smp 1 \
		-cdrom build/aurora-os.iso \
		-boot d \
		-s -S \
		-nographic \
		-serial stdio

# Run comprehensive test suite
test: kernel modules
	@echo "Running Aurora-OS test suite..."
	@mkdir -p build/test
	@cd tests && ./run-all-tests.sh
	@echo "Test suite completed"

# Install Aurora-OS to target system
install: iso
	@echo "Installing Aurora-OS..."
	@./installer/aurora-installer.sh build/aurora-os.iso
	@echo "Installation completed"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@rm -rf build/
	@cd core && make clean 2>/dev/null || true
	@cd tools && make clean 2>/dev/null || true
	@echo "Clean completed"

# Development targets
dev-setup:
	@echo "Setting up development environment..."
	@./scripts/dev-setup.sh
	@echo "Development environment ready"

# Check dependencies
check-deps:
	@echo "Checking dependencies..."
	@./scripts/check-deps.sh
	@echo "Dependency check completed"

# Create development ISO (faster build)
dev-iso:
	@echo "Creating development ISO..."
	@make -C build/dev-iso
	@echo "Development ISO ready: build/dev-iso/aurora-os-dev.iso"