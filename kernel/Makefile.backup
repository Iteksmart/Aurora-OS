# Aurora OS Kernel Makefile
# Placeholder for kernel build system

# Configuration
KERNEL_VERSION = 6.1
obj-m += aurora_core.o
obj-m += ai_scheduler.o

# Default target
all:
	@echo "Building Aurora OS kernel modules..."
	@if [ -d "/usr/src/linux-$(KERNEL_VERSION)" ]; then \
		make -C /usr/src/linux-$(KERNEL_VERSION) M=$(PWD) modules; \
	else \
		echo "⚠️  Kernel source not available - creating placeholder"; \
		mkdir -p ../build/kernel; \
		touch ../build/kernel/.kernel_placeholder; \
	fi

# Clean target
clean:
	@echo "Cleaning kernel build artifacts..."
	@rm -f *.o *.ko *.mod.c .*.cmd *.markers *.symvers *.order
	@rm -rf .tmp_versions
	@rm -f Module.markers Module.symvers modules.order
	@if [ -d "/usr/src/linux-$(KERNEL_VERSION)" ]; then \
		make -C /usr/src/linux-$(KERNEL_VERSION) M=$(PWD) clean 2>/dev/null || true; \
	fi
	@echo "✅ Kernel cleanup complete"

# Install target
install:
	@echo "Installing kernel modules..."
	@if [ -f "*.ko" ]; then \
		install -m 644 *.ko ../build/kernel/; \
	fi

.PHONY: all clean install