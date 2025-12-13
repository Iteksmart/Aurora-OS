# Aurora Intent Engine (AIE) Makefile
# eBPF-based intent recognition and automation

obj-m += aurora_aie.o
aurora_aie-objs := aie_main.o aie_ebpf.o aie_intent.o aie_automation.o aie_security.o

# Build configuration
KERNEL_DIR := /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)

# Compiler flags
ccflags-y := -DDEBUG -Wall -Wextra
ccflags-y += -DAURORA_AIE_VERSION=&quot;1.0.0&quot;
ccflags-y += -DAURORA_ENTERPRISE=1

# Include directories
ccflags-y += -I$(src)/include
ccflags-y += -I$(src)/../include

# eBPF compilation
BPF_CFLAGS := -O2 -target bpf -c
BPF_INCLUDE := -I/usr/include/$(shell uname -m)-linux-gnu

all:
	@echo "🧠 Building Aurora Intent Engine (AIE)..."
	$(MAKE) -C $(KERNEL_DIR) M=$(PWD) modules
	$(MAKE) -C ebpf

ebpf:
	@echo "🔧 Building AIE eBPF programs..."
	cd ebpf && $(MAKE) all

clean:
	@echo "🧹 Cleaning AIE build artifacts..."
	$(MAKE) -C $(KERNEL_DIR) M=$(PWD) clean
	cd ebpf && $(MAKE) clean
	rm -f *.o *.ko *.mod.c .*.cmd *.order *.symvers

install:
	@echo "📦 Installing Aurora Intent Engine..."
	$(MAKE) -C $(KERNEL_DIR) M=$(PWD) modules_install
	depmod -a
	@echo "✅ AIE installation completed"

test:
	@echo "🧪 Running AIE tests..."
	./tests/run_aie_tests.sh

# Development targets
dev-build:
	@echo "🔧 Building AIE for development..."
	$(MAKE) DEBUG=1

debug:
	@echo "🐛 Building AIE with debug symbols..."
	$(MAKE) ccflags-y+=" -g -DDEBUG"

# Performance targets
perf:
	@echo "⚡ Building AIE with performance optimizations..."
	$(MAKE) ccflags-y+=" -O3 -DNDEBUG -march=native"

# Security targets
fips:
	@echo "🔒 Building AIE with FIPS compliance..."
	$(MAKE) ccflags-y+=" -DAURORA_FIPS=1"

.PHONY: all clean install test dev-build debug perf fips ebpf