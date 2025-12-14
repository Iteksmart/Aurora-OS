# Aurora OS Kernel Build System
# Linux 6.1 LTS with AI acceleration patches

KERNEL_VERSION := 6.1.0
KERNEL_URL := https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-$(KERNEL_VERSION).tar.xz
KERNEL_DIR := linux-$(KERNEL_VERSION)
AURORA_PATCHES_DIR := patches

.PHONY: kernel-download kernel-patch kernel-build kernel-clean kernel-modules

all: kernel-build

# Download Linux kernel source
kernel-download:
	@echo "🔥 Downloading Linux kernel $(KERNEL_VERSION)..."
	wget -O $(KERNEL_DIR).tar.xz $(KERNEL_URL)
	tar -xf $(KERNEL_DIR).tar.xz
	rm $(KERNEL_DIR).tar.xz
	@echo "✅ Kernel source downloaded to $(KERNEL_DIR)/"

# Apply Aurora AI patches
kernel-patch: kernel-download
	@echo "🧠 Applying Aurora AI patches to kernel..."
	# Apply AI scheduler patch
	patch -p1 -d $(KERNEL_DIR) < $(AURORA_PATCHES_DIR)/aurora_ai_scheduler.patch
	# Apply AI acceleration patch
	patch -p1 -d $(KERNEL_DIR) < $(AURORA_PATCHES_DIR)/aurora_ai_accel.patch
	# Apply GPU driver integration patch
	patch -p1 -d $(KERNEL_DIR) < $(AURORA_PATCHES_DIR)/aurora_gpu_drivers.patch
	@echo "✅ Aurora AI patches applied successfully"

# Configure and build kernel
kernel-build: kernel-patch
	@echo "⚙️  Configuring Aurora OS kernel..."
	cd $(KERNEL_DIR) && make defconfig
	cd $(KERNEL_DIR) && make nconfig
	@echo "🔨 Building Aurora OS kernel (this will take ~2 hours)..."
	cd $(KERNEL_DIR) && make -j$(nproc)
	@echo "🎯 Building kernel modules..."
	cd $(KERNEL_DIR) && make modules -j$(nproc)
	@echo "✅ Aurora OS kernel built successfully"
	@echo "📦 Kernel image: $(KERNEL_DIR)/arch/x86/boot/bzImage"

# Install kernel and modules
kernel-install: kernel-build
	@echo "📥 Installing Aurora OS kernel..."
	cd $(KERNEL_DIR) && sudo make modules_install
	cd $(KERNEL_DIR) && sudo make install
	sudo update-grub
	@echo "✅ Aurora OS kernel installed"

# Clean kernel build
kernel-clean:
	@echo "🧹 Cleaning kernel build..."
	rm -rf $(KERNEL_DIR)
	@echo "✅ Kernel build cleaned"

# Create Aurora AI kernel modules
kernel-modules:
	@echo "🤖 Building Aurora AI kernel modules..."
	$(MAKE) -C drivers/ai_accel
	$(MAKE) -C drivers/aurora_scheduler
	@echo "✅ Aurora AI kernel modules built"

# Create kernel configuration for AI workloads
kernel-config:
	@echo "⚙️  Creating Aurora OS kernel configuration..."
	cd $(KERNEL_DIR) && ./scripts/config \
		--enable CONFIG_AURORA_AI_SCHEDULER \
		--enable CONFIG_AURORA_AI_ACCELERATION \
		--enable CONFIG_NVIDIA_GPU_DRIVERS \
		--enable CONFIG_AMD_GPU_DRIVERS \
		--enable CONFIG_INTEL_GPU_DRIVERS \
		--enable CONFIG_INTEGRITY \
		--enable CONFIG_SECURITY_SELINUX \
		--enable CONFIG_DM_CRYPT \
		--enable CONFIG_EFI_STUB \
		--enable CONFIG_MODULES \
		--enable CONFIG_MODULE_SIG \
		--enable CONFIG_MODULE_SIG_FORCE \
		--enable CONFIG_KEXEC
	@echo "✅ Aurora OS kernel configuration created"

help:
	@echo "Aurora OS Kernel Build System"
	@echo "=============================="
	@echo "make kernel-download  - Download Linux kernel source"
	@echo "make kernel-patch     - Apply Aurora AI patches"
	@echo "make kernel-build     - Configure and build kernel"
	@echo "make kernel-install   - Install kernel and modules"
	@echo "make kernel-modules   - Build Aurora AI modules"
	@echo "make kernel-config    - Configure kernel for AI workloads"
	@echo "make kernel-clean     - Clean kernel build"
	@echo "make help             - Show this help"