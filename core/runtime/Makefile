# Aurora Universal App Runtime - Makefile
# Cross-platform application compatibility layer

obj-m += aurora_runtime.o
aurora_runtime-objs := runtime_main.o runtime_wine.o runtime_linux.o runtime_web.o runtime_ai.o runtime_sandbox.o

# Build configuration
KERNEL_DIR := /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)

# Compiler flags
ccflags-y := -DDEBUG -Wall -Wextra
ccflags-y += -DAURORA_RUNTIME_VERSION=&quot;1.0.0&quot;
ccflags-y += -DAURORA_ENTERPRISE=1

# Include directories
ccflags-y += -I$(src)/include
ccflags-y += -I$(src)/../include
ccflags-y += -I$(src)/wine/include
ccflags-y += -I$(src)/web/include

# Wine integration (if available)
ifdef WINE_BUILD_ROOT
ccflags-y += -I$(WINE_BUILD_ROOT)/include
ccflags-y += -DWINE_INTEGRATION=1
endif

# Web runtime integration
ccflags-y += -DWEB_RUNTIME=1

# AI runtime integration
ccflags-y += -DAI_RUNTIME=1

all:
	@echo "🚀 Building Aurora Universal App Runtime..."
	$(MAKE) -C $(KERNEL_DIR) M=$(PWD) modules
	$(MAKE) -C userland

userland:
	@echo "🔧 Building runtime userland components..."
	$(MAKE) -C wine 2>/dev/null || echo "Wine integration not available"
	$(MAKE) -C web
	$(MAKE) -C ai
	$(MAKE) -C sandbox

wine:
	@echo "🍷 Building Wine compatibility layer..."
	$(MAKE) -C wine

web:
	@echo "🌐 Building Web runtime..."
	$(MAKE) -C web

ai:
	@echo "🧠 Building AI runtime..."
	$(MAKE) -C ai

sandbox:
	@echo "🔒 Building application sandbox..."
	$(MAKE) -C sandbox

clean:
	@echo "🧹 Cleaning Aurora Runtime build artifacts..."
	$(MAKE) -C $(KERNEL_DIR) M=$(PWD) clean
	$(MAKE) -C wine clean 2>/dev/null || true
	$(MAKE) -C web clean 2>/dev/null || true
	$(MAKE) -C ai clean 2>/dev/null || true
	$(MAKE) -C sandbox clean 2>/dev/null || true
	rm -f *.o *.ko *.mod.c .*.cmd *.order *.symvers

install:
	@echo "📦 Installing Aurora Universal App Runtime..."
	$(MAKE) -C $(KERNEL_DIR) M=$(PWD) modules_install
	depmod -a
	
	# Install userland components
	$(MAKE) -C web install
	$(MAKE) -C ai install
	$(MAKE) -C sandbox install
	
	@echo "✅ Aurora Runtime installation completed"

test:
	@echo "🧪 Running Aurora Runtime tests..."
	./tests/run_runtime_tests.sh

# Performance targets
perf:
	@echo "⚡ Building Aurora Runtime with performance optimizations..."
	$(MAKE) ccflags-y+=" -O3 -DNDEBUG -march=native"

# Security targets
fips:
	@echo "🔒 Building Aurora Runtime with FIPS compliance..."
	$(MAKE) ccflags-y+=" -DAURORA_FIPS=1"

# Development targets
dev-build:
	@echo "🔧 Building Aurora Runtime for development..."
	$(MAKE) DEBUG=1

debug:
	@echo "🐛 Building Aurora Runtime with debug symbols..."
	$(MAKE) ccflags-y+=" -g -DDEBUG"

# Application compatibility testing
test-windows:
	@echo "🪟 Testing Windows application compatibility..."
	./tests/test_windows_apps.sh

test-linux:
	@echo "🐧 Testing Linux application compatibility..."
	./tests/test_linux_apps.sh

test-web:
	@echo "🌐 Testing Web application compatibility..."
	./tests/test_web_apps.sh

.PHONY: all clean install test perf fips dev-build debug userland wine web ai sandbox test-windows test-linux test-web