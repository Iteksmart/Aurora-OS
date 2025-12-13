# Aurora Desktop Environment - Makefile
# Modern desktop environment with Aurora Glass theme

obj-m += aurora_desktop.o
aurora_desktop-objs := desktop_main.o desktop_compositor.o desktop_theme.o desktop_window.o desktop_panel.o desktop_launcher.o

# Build configuration
KERNEL_DIR := /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)

# Compiler flags
ccflags-y := -DDEBUG -Wall -Wextra
ccflags-y += -DAURORA_DESKTOP_VERSION=&quot;1.0.0&quot;
ccflags-y += -DAURORA_ENTERPRISE=1

# Include directories
ccflags-y += -I$(src)/include
ccflags-y += -I$(src)/../include
ccflags-y += -I$(src)/theme/include

# Graphics and UI support
ccflags-y += -DDESKTOP_GRAPHICS=1
ccflags-y += -DAURORA_GLASS_THEME=1

# Wayland/X11 support
ccflags-y += -DWAYLAND_SUPPORT=1
ccflags-y += -DX11_SUPPORT=1

all:
	@echo "🖥️ Building Aurora Desktop Environment..."
	$(MAKE) -C $(KERNEL_DIR) M=$(PWD) modules
	$(MAKE) -C userland

userland:
	@echo "🎨 Building desktop userland components..."
	$(MAKE) -C theme
	$(MAKE) -C compositor
	$(MAKE) -C panel
	$(MAKE) -C launcher
	$(MAKE) -c settings

theme:
	@echo "✨ Building Aurora Glass theme..."
	$(MAKE) -C theme

compositor:
	@echo "🪟 Building Aurora Flow compositor..."
	$(MAKE) -C compositor

panel:
	@echo "📊 Building desktop panel..."
	$(MAKE) -C panel

launcher:
	@echo "🚀 Building application launcher..."
	$(MAKE) -C launcher

settings:
	@echo "⚙️ Building desktop settings..."
	$(MAKE) -C settings

clean:
	@echo "🧹 Cleaning Aurora Desktop build artifacts..."
	$(MAKE) -C $(KERNEL_DIR) M=$(PWD) clean
	$(MAKE) -C theme clean 2>/dev/null || true
	$(MAKE) -C compositor clean 2>/dev/null || true
	$(MAKE) -C panel clean 2>/dev/null || true
	$(MAKE) -C launcher clean 2>/dev/null || true
	$(MAKE) -C settings clean 2>/dev/null || true
	rm -f *.o *.ko *.mod.c .*.cmd *.order *.symvers

install:
	@echo "📦 Installing Aurora Desktop Environment..."
	$(MAKE) -C $(KERNEL_DIR) M=$(PWD) modules_install
	depmod -a
	
	# Install userland components
	$(MAKE) -C theme install
	$(MAKE) -C compositor install
	$(MAKE) -C panel install
	$(MAKE) -C launcher install
	$(MAKE) -C settings install
	
	@echo "✅ Aurora Desktop installation completed"

test:
	@echo "🧪 Running Aurora Desktop tests..."
	./tests/run_desktop_tests.sh

# Performance targets
perf:
	@echo "⚡ Building Aurora Desktop with performance optimizations..."
	$(MAKE) ccflags-y+=" -O3 -DNDEBUG -march=native"

# Development targets
dev-build:
	@echo "🔧 Building Aurora Desktop for development..."
	$(MAKE) DEBUG=1

debug:
	@echo "🐛 Building Aurora Desktop with debug symbols..."
	$(MAKE) ccflags-y+=" -g -DDEBUG"

# Theme customization
customize-theme:
	@echo "🎨 Customizing Aurora Glass theme..."
	./tools/customize-theme.sh

.PHONY: all clean install test perf dev-build debug userland theme compositor panel launcher settings customize-theme