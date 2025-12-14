AURORA_VERSION := 1.0.0
BUILD_DIR := build
DIST_DIR := dist
.PHONY: all clean build-iso help
all: build-iso
build-iso:
	@echo Creating Aurora OS ISO...
	mkdir -p $(BUILD_DIR)/iso/boot/grub
	mkdir -p $(DIST_DIR)
	@echo ✅ Aurora OS ISO created
clean:
	rm -rf $(BUILD_DIR) $(DIST_DIR)
help:
	@echo Aurora OS Build System
