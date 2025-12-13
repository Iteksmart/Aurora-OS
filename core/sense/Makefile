# Aurora Sense - Real-time Kernel Observability
# eBPF-based system monitoring and analytics

obj-m += aurora_sense.o
aurora_sense-objs := sense_main.o sense_ebpf.o sense_metrics.o sense_analytics.o sense_security.o

# Build configuration
KERNEL_DIR := /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)

# Compiler flags
ccflags-y := -DDEBUG -Wall -Wextra
ccflags-y += -DAURORA_SENSE_VERSION=&quot;1.0.0&quot;
ccflags-y += -DAURORA_ENTERPRISE=1

# Include directories
ccflags-y += -I$(src)/include
ccflags-y += -I$(src)/../include

# eBPF compilation
BPF_CFLAGS := -O2 -target bpf -c
BPF_INCLUDE := -I/usr/include/$(shell uname -m)-linux-gnu

all:
	@echo "🔍 Building Aurora Sense monitoring system..."
	$(MAKE) -C $(KERNEL_DIR) M=$(PWD) modules
	$(MAKE) -C ebpf

ebpf:
	@echo "🔧 Building Sense eBPF programs..."
	cd ebpf && $(MAKE) all

clean:
	@echo "🧹 Cleaning Sense build artifacts..."
	$(MAKE) -C $(KERNEL_DIR) M=$(PWD) clean
	cd ebpf && $(MAKE) clean
	rm -f *.o *.ko *.mod.c .*.cmd *.order *.symvers

install:
	@echo "📦 Installing Aurora Sense..."
	$(MAKE) -C $(KERNEL_DIR) M=$(PWD) modules_install
	depmod -a
	@echo "✅ Sense installation completed"

test:
	@echo "🧪 Running Sense tests..."
	./tests/run_sense_tests.sh

# Performance targets
perf:
	@echo "⚡ Building Sense with performance optimizations..."
	$(MAKE) ccflags-y+=" -O3 -DNDEBUG -march=native"

# Security targets
fips:
	@echo "🔒 Building Sense with FIPS compliance..."
	$(MAKE) ccflags-y+=" -DAURORA_FIPS=1"

# Development targets
dev-build:
	@echo "🔧 Building Sense for development..."
	$(MAKE) DEBUG=1

debug:
	@echo "🐛 Building Sense with debug symbols..."
	$(MAKE) ccflags-y+=" -g -DDEBUG"

.PHONY: all clean install test perf fips dev-build debug ebpf