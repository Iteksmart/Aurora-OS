# Aurora OS Build System
# Builds the complete AI-native operating system

# Configuration
KERNEL_VERSION = 6.1
KERNEL_URL = https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-$(KERNEL_VERSION).tar.xz
KERNEL_DIR = kernel/linux-$(KERNEL_VERSION)
BUILD_DIR = build
DIST_DIR = dist
TEST_DIR = tests
DOCS_DIR = docs
ISO_DIR = $(BUILD_DIR)/iso

# Default target
.PHONY: all
all: build

# Help target
.PHONY: help
help:
	@echo "Aurora OS Build System"
	@echo ""
	@echo "Available targets:"
	@echo "  build          - Build complete Aurora OS"
	@echo "  build-kernel   - Build AI-enhanced kernel"
	@echo "  build-system   - Build system services"
	@echo "  build-ai       - Build AI control plane"
	@echo "  build-mcp      - Build MCP system"
	@echo "  build-desktop  - Build desktop environment"
	@echo "  iso            - Create bootable ISO image"
	@echo "  test           - Run all tests"
	@echo "  test-kernel    - Run kernel tests"
	@echo "  test-system    - Run system tests"
	@echo "  test-ai        - Run AI tests"
	@echo "  test-mcp       - Run MCP tests"
	@echo "  install        - Install Aurora OS"
	@echo "  clean          - Clean build artifacts"
	@echo "  docs           - Generate documentation"
	@echo "  run-vm         - Run in virtual machine"
	@echo "  complete-iso   - Complete ISO build with kernel activation"
	@echo "  help           - Show this help"

# Create build directories
$(BUILD_DIR):
	@echo "Creating build directories..."
	@mkdir -p $(BUILD_DIR)/kernel
	@mkdir -p $(BUILD_DIR)/system
	@mkdir -p $(BUILD_DIR)/ai
	@mkdir -p $(BUILD_DIR)/mcp
	@mkdir -p $(BUILD_DIR)/desktop
	@mkdir -p $(BUILD_DIR)/dist
	@mkdir -p $(BUILD_DIR)/docs
	@mkdir -p $(ISO_DIR)

# Fetch kernel source
$(KERNEL_DIR)/.config:
	@echo "Downloading Linux $(KERNEL_VERSION) kernel..."
	@if [ ! -f kernel/linux-$(KERNEL_VERSION).tar.xz ]; then \
		cd kernel && wget $(KERNEL_URL); \
	fi
	@echo "Extracting kernel..."
	@cd kernel && tar -xf linux-$(KERNEL_VERSION).tar.xz
	@echo "Applying Aurora OS configuration..."
	@cp kernel/config/aurora_defconfig $(KERNEL_DIR)/.config
	@echo "Preparing kernel build..."
	@cd $(KERNEL_DIR) && make olddefconfig

# Build complete OS
.PHONY: build
build: $(BUILD_DIR) build-kernel build-system build-ai build-mcp build-desktop
	@echo "Building complete Aurora OS..."
	@mkdir -p $(DIST_DIR)
	@echo "Creating Aurora OS distribution..."
	@cp -r $(BUILD_DIR)/* $(DIST_DIR)/
	@echo "Aurora OS build complete!"
	@echo "Distribution available in: $(DIST_DIR)"

# Build AI-enhanced kernel
.PHONY: build-kernel
build-kernel: $(KERNEL_DIR)/.config
	@echo "Building AI-enhanced Linux kernel..."
	@cd $(KERNEL_DIR) && make -j$$(nproc) bzImage
	@cd $(KERNEL_DIR) && make -j$$(nproc) modules
	@mkdir -p $(BUILD_DIR)/kernel
	@cp $(KERNEL_DIR)/arch/x86/boot/bzImage $(BUILD_DIR)/kernel/
	@cd $(KERNEL_DIR) && make INSTALL_MOD_PATH=$(BUILD_DIR)/kernel modules_install
	@echo "AI kernel modules built successfully"

# Build system services
.PHONY: build-system
build-system: $(BUILD_DIR)
	@echo "Building Aurora system services..."
	@cd system && python -m py_compile ai_control_plane/*.py
	@cp system/ai_control_plane/*.pyc $(BUILD_DIR)/system/
	@echo "System services built successfully"

# Build AI control plane
.PHONY: build-ai
build-ai: $(BUILD_DIR)
	@echo "Building AI control plane..."
	@cd ai && python -m py_compile **/*.py
	@cp -r ai/* $(BUILD_DIR)/ai/
	@echo "AI control plane built successfully"

# Build MCP system
.PHONY: build-mcp
build-mcp: $(BUILD_DIR)
	@echo "Building MCP nervous system..."
	@cd mcp && python -m py_compile **/*.py
	@cp -r mcp/* $(BUILD_DIR)/mcp/
	@echo "MCP system built successfully"

# Build desktop environment
.PHONY: build-desktop
build-desktop: $(BUILD_DIR)
	@echo "Building Aurora desktop environment..."
	@cd desktop && python -m py_compile **/*.py
	@cp -r desktop/* $(BUILD_DIR)/desktop/
	@echo "Desktop environment built successfully"

# Create initramfs
$(BUILD_DIR)/aurora-initramfs.img:
	@echo "Creating Aurora OS initramfs..."
	@chmod +x tools/create_initramfs.sh
	@tools/create_initramfs.sh

# Create bootable ISO
.PHONY: iso
iso: build-kernel $(BUILD_DIR)/aurora-initramfs.img
	@echo "Creating Aurora OS bootable ISO..."
	@mkdir -p $(ISO_DIR)/boot/grub
	@mkdir -p $(ISO_DIR)/aurora-os
	@cp $(BUILD_DIR)/kernel/bzImage $(ISO_DIR)/boot/vmlinuz-$(KERNEL_VERSION)
	@cp $(BUILD_DIR)/aurora-initramfs.img $(ISO_DIR)/boot/
	@cp -r $(BUILD_DIR)/system $(ISO_DIR)/aurora-os/
	@cp -r $(BUILD_DIR)/ai $(ISO_DIR)/aurora-os/
	@cp -r $(BUILD_DIR)/mcp $(ISO_DIR)/aurora-os/
	@cp -r $(BUILD_DIR)/desktop $(ISO_DIR)/aurora-os/
	@echo "Creating GRUB configuration..."
	@cat > $(ISO_DIR)/boot/grub/grub.cfg << 'GRUB_EOF'
set default=0
set timeout=10

menuentry "Aurora OS v1.0.0 - AI Native" {
    linux /boot/vmlinuz-6.1 root=/dev/ram0 rw quiet splash
    initrd /boot/aurora-initramfs.img
}

menuentry "Aurora OS v1.0.0 - Debug Mode" {
    linux /boot/vmlinuz-6.1 root=/dev/ram0 rw debug init=/bin/sh
    initrd /boot/aurora-initramfs.img
}

menuentry "Aurora OS v1.0.0 - Recovery Mode" {
    linux /boot/vmlinuz-6.1 root=/dev/ram0 rw single
    initrd /boot/aurora-initramfs.img
}
GRUB_EOF
	@echo "Creating ISO image..."
	@cd $(ISO_DIR) && grub-mkrescue -o ../aurora-os.iso .
	@echo "Aurora OS ISO created: $(BUILD_DIR)/aurora-os.iso"

# Complete ISO with verification
.PHONY: complete-iso
complete-iso: iso
	@echo "Verifying Aurora OS ISO..."
	@if [ -f $(BUILD_DIR)/aurora-os.iso ]; then \
		SIZE=$$(du -h $(BUILD_DIR)/aurora-os.iso | cut -f1); \
		echo "✓ ISO Size: $$SIZE"; \
		echo "✓ ISO Path: $(BUILD_DIR)/aurora-os.iso"; \
		file $(BUILD_DIR)/aurora-os.iso; \
		echo "✓ Aurora OS ISO verification complete!"; \
	else \
		echo "✗ ISO creation failed!"; \
		exit 1; \
	fi

# Testing
.PHONY: test
test: test-kernel test-system test-ai test-mcp
	@echo "All tests completed!"

.PHONY: test-kernel
test-kernel:
	@echo "Running kernel tests..."
	@cd $(TEST_DIR)/kernel && python -m pytest -v

.PHONY: test-system
test-system:
	@echo "Running system tests..."
	@cd $(TEST_DIR)/system && python -m pytest -v

.PHONY: test-ai
test-ai:
	@echo "Running AI tests..."
	@cd $(TEST_DIR)/ai && python -m pytest -v

.PHONY: test-mcp
test-mcp:
	@echo "Running MCP tests..."
	@cd $(TEST_DIR)/mcp && python -m pytest -v

# Install Aurora OS
.PHONY: install
install: build
	@echo "Installing Aurora OS..."
	@sudo mkdir -p /opt/aurora-os
	@sudo cp -r $(DIST_DIR)/* /opt/aurora-os/
	@sudo chmod +x /opt/aurora-os/tools/install.sh
	@sudo /opt/aurora-os/tools/install.sh
	@echo "Aurora OS installed successfully!"

# Clean build artifacts
.PHONY: clean
clean:
	@echo "Cleaning build artifacts..."
	@rm -rf $(BUILD_DIR)
	@rm -rf $(DIST_DIR)
	@rm -rf kernel/linux-$(KERNEL_VERSION)
	@cd kernel && make clean 2>/dev/null || true
	@echo "Clean complete!"

# Generate documentation
.PHONY: docs
docs:
	@echo "Generating documentation..."
	@mkdir -p $(BUILD_DIR)/docs
	@cd $(DOCS_DIR) && make html
	@cp -r $(DOCS_DIR)/_build/html/* $(BUILD_DIR)/docs/
	@echo "Documentation generated in $(BUILD_DIR)/docs/"

# Run in virtual machine
.PHONY: run-vm
run-vm: iso
	@echo "Starting Aurora OS in virtual machine..."
	@if [ -f $(BUILD_DIR)/aurora-os.iso ]; then \
		qemu-system-x86_64 \
			-cdrom $(BUILD_DIR)/aurora-os.iso \
			-m 4096 \
			-enable-kvm \
			-cpu host \
			-boot d; \
	else \
		echo "ISO not found. Run 'make iso' first."; \
		exit 1; \
	fi
