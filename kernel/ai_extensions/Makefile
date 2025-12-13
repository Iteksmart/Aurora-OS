# Aurora OS - AI Extensions Makefile
# Builds the AI-enhanced kernel modules for Aurora OS

# Module configuration
obj-m += ai_scheduler.o
obj-m += ai_context_manager.o
obj-m += ai_security.o

# Compiler flags
ccflags-y := -Wall -Wextra -Wno-declaration-after-statement
ccflags-y += -DCONFIG_AURORA_AI
ccflags-y += -DCONFIG_AURORA_AI_HOOKS

# Include directories
ccflags-y += -I$(src)/../..
ccflags-y += -I$(src)/../../../system/ai_control_plane
ccflags-y += -I$(src)/../../../mcp/system

# Linker flags
ldflags-y += --strip-debug

# Default target
all:
	@echo "Building Aurora OS AI Extensions..."
	$(MAKE) -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules
	@echo "✓ AI kernel extensions built successfully"

# Clean target
clean:
	@echo "Cleaning AI kernel extensions..."
	$(MAKE) -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
	rm -f *.mod.c .*.cmd *.o *.ko *.symvers *.order
	rm -rf .tmp_versions
	@echo "✓ AI kernel extensions cleaned"

# Install target (for system installation)
install:
	@echo "Installing AI kernel extensions..."
	$(MAKE) -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules_install
	depmod -a
	@echo "✓ AI kernel extensions installed"

# Test compilation (syntax check)
test-compile:
	@echo "Testing AI kernel extensions compilation..."
	$(MAKE) -C /lib/modules/$(shell uname -r)/build M=$(PWD) C=2 CF="-D__CHECK_ENDIAN__" clean modules
	@echo "✓ Compilation test completed"

# Development targets
.PHONY: all clean install test-compile