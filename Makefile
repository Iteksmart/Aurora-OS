# Aurora OS Build System
# Builds the complete AI-native operating system

# Configuration
KERNEL_VERSION = 6.1
BUILD_DIR = build
DIST_DIR = dist
TEST_DIR = tests
DOCS_DIR = docs

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
	@echo "  test           - Run all tests"
	@echo "  test-kernel    - Run kernel tests"
	@echo "  test-system    - Run system tests"
	@echo "  test-ai        - Run AI tests"
	@echo "  test-mcp       - Run MCP tests"
	@echo "  install        - Install Aurora OS"
	@echo "  clean          - Clean build artifacts"
	@echo "  docs           - Generate documentation"
	@echo "  run-vm         - Run in virtual machine"
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
build-kernel: $(BUILD_DIR)
	@echo "Building AI-enhanced Linux kernel..."
	@cd kernel && make -C /usr/src/linux-$(KERNEL_VERSION) M=$(PWD)/kernel modules
	@cp kernel/*.ko $(BUILD_DIR)/kernel/ 2>/dev/null || true
	@cd kernel/ai_extensions && make -C /usr/src/linux-$(KERNEL_VERSION) M=$(PWD)/kernel/ai_extensions modules\n	@cp kernel/ai_extensions/*.ko $(BUILD_DIR)/kernel/ 2>/dev/null || true
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
	@cd kernel && make clean || true
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
run-vm: build
	@echo "Starting Aurora OS in virtual machine..."
	@./tools/run_vm.sh $(DIST_DIR)

# Development setup
.PHONY: setup
setup:
	@echo "Setting up development environment..."
	@./tools/setup_dev_environment.sh
	@echo "Development environment setup complete!"

# Continuous Integration
.PHONY: ci
ci: clean build test
	@echo "CI pipeline completed successfully!"

# Security audit
.PHONY: security-audit
security-audit:
	@echo "Running security audit..."
	@./tools/security_audit.sh
	@echo "Security audit complete!"

# Performance testing
.PHONY: benchmark
benchmark:
	@echo "Running performance benchmarks..."
	@./tools/benchmark.sh
	@echo "Benchmarks complete!"

# Release preparation
.PHONY: release
release: clean build test docs
	@echo "Preparing release..."
	@./tools/prepare_release.sh
	@echo "Release preparation complete!"

# Docker build
.PHONY: docker-build
docker-build:
	@echo "Building Aurora OS Docker image..."
	@docker build -t aurora-os:latest .
	@echo "Docker image built successfully!"

# Package for distribution
.PHONY: package
package: build
	@echo "Packaging Aurora OS for distribution..."
	@cd $(DIST_DIR) && tar -czf ../aurora-os-$(shell date +%Y%m%d).tar.gz .
	@echo "Package created: aurora-os-$(shell date +%Y%m%d).tar.gz"

# Check dependencies
.PHONY: check-deps
check-deps:
	@echo "Checking dependencies..."
	@./tools/check_dependencies.sh
	@echo "Dependency check complete!"

# Format code
.PHONY: format
format:
	@echo "Formatting code..."
	@find . -name "*.py" -exec python -m black {} \;
	@find . -name "*.c" -exec clang-format -i {} \;
	@echo "Code formatted!"

# Lint code
.PHONY: lint
lint:
	@echo "Linting code..."
	@find . -name "*.py" -exec python -m flake8 {} \;
	@find . -name "*.c" -exec clang-format --dry-run --Werror {} \;
	@echo "Linting complete!"

# Static analysis
.PHONY: static-analysis
static-analysis:
	@echo "Running static analysis..."
	@./tools/static_analysis.sh
	@echo "Static analysis complete!"

# Integration tests
.PHONY: integration-test
integration-test:
	@echo "Running integration tests..."
	@cd $(TEST_DIR)/integration && python -m pytest -v
	@echo "Integration tests complete!"

# End-to-end tests
.PHONY: e2e-test
e2e-test:
	@echo "Running end-to-end tests..."
	@cd $(TEST_DIR)/e2e && python -m pytest -v
	@echo "End-to-end tests complete!"

# Coverage report
.PHONY: coverage
coverage:
	@echo "Generating coverage report..."
	@cd $(TEST_DIR) && python -m pytest --cov=../ --cov-report=html
	@echo "Coverage report generated in $(TEST_DIR)/htmlcov/"

# Performance profiling
.PHONY: profile
profile:
	@echo "Running performance profiling..."
	@./tools/profile.sh
	@echo "Profiling complete!"

# Memory leak detection
.PHONY: memcheck
memcheck:
	@echo "Running memory leak detection..."
	@./tools/memcheck.sh
	@echo "Memory leak detection complete!"

# Update dependencies
.PHONY: update-deps
update-deps:
	@echo "Updating dependencies..."
	@./tools/update_dependencies.sh
	@echo "Dependencies updated!"

# Cross-compilation
.PHONY: cross-compile
cross-compile:
	@echo "Cross-compiling for different architectures..."
	@./tools/cross_compile.sh
	@echo "Cross-compilation complete!"

# Generate API documentation
.PHONY: api-docs
api-docs:
	@echo "Generating API documentation..."
	@./tools/generate_api_docs.sh
	@echo "API documentation generated!"

# Validate configuration
.PHONY: validate-config
validate-config:
	@echo "Validating configuration..."
	@./tools/validate_config.sh
	@echo "Configuration validation complete!"

# Boot test
.PHONY: boot-test
boot-test:
	@echo "Testing Aurora OS boot..."
	@./tools/boot_test.sh
	@echo "Boot test complete!"

# Compatibility test
.PHONY: compat-test
compat-test:
	@echo "Running compatibility tests..."
	@./tools/compat_test.sh
	@echo "Compatibility tests complete!"

# Stress test
.PHONY: stress-test
stress-test:
	@echo "Running stress tests..."
	@./tools/stress_test.sh
	@echo "Stress tests complete!"

# Backup build
.PHONY: backup
backup:
	@echo "Backing up build artifacts..."
	@tar -czf aurora-os-backup-$(shell date +%Y%m%d).tar.gz $(BUILD_DIR) $(DIST_DIR)
	@echo "Backup complete!"

# Restore from backup
.PHONY: restore
restore:
	@echo "Restoring from backup..."
	@tar -xzf aurora-os-backup-$(shell date +%Y%m%d).tar.gz
	@echo "Restore complete!"

# Monitor build
.PHONY: monitor
monitor:
	@echo "Monitoring build process..."
	@./tools/monitor_build.sh

# Status check
.PHONY: status
status:
	@echo "Aurora OS Build Status:"
	@echo "======================="
	@echo "Kernel: $$(ls -la $(BUILD_DIR)/kernel/ 2>/dev/null | wc -l) modules"
	@echo "System: $$(ls -la $(BUILD_DIR)/system/ 2>/dev/null | wc -l) components"
	@echo "AI: $$(ls -la $(BUILD_DIR)/ai/ 2>/dev/null | wc -l) modules"
	@echo "MCP: $$(ls -la $(BUILD_DIR)/mcp/ 2>/dev/null | wc -l) components"
	@echo "Desktop: $$(ls -la $(BUILD_DIR)/desktop/ 2>/dev/null | wc -l) components"

# Quick build (skips tests)
.PHONY: quick-build
quick-build: $(BUILD_DIR) build-kernel build-system build-ai build-mcp
	@echo "Quick build complete!"

# Development server
.PHONY: dev-server
dev-server:
	@echo "Starting development server..."
	@cd tools && python dev_server.py

# Watch mode for development
.PHONY: watch
watch:
	@echo "Starting watch mode..."
	@./tools/watch.sh

# Export environment variables
.PHONY: export-env
export-env:
	@echo "Exporting Aurora OS environment variables..."
	@export AURORA_HOME=$(PWD)
	@export AURORA_BUILD_DIR=$(BUILD_DIR)
	@export AURORA_VERSION=1.0.0
	@echo "Environment variables exported!"

# Phony targets list
.PHONY: list-targets
list-targets:
	@echo "Available targets:"
	@$(MAKE) -pRrq -f $(firstword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | grep -E -v -e '^[^[:alnum:]]' -e '^$@$$'
# Deployment targets
.PHONY: packages image pipeline deploy
packages:
	@echo "Creating Aurora OS packages..."
	python build/package_manager.py create-core

image:
	@echo "Creating bootable OS image..."
	python build/aurora_builder.py

pipeline:
	@echo "Running automated build pipeline..."
	python build/build_pipeline.py

pipeline-clean:
	@echo "Running clean build pipeline..."
	python build/build_pipeline.py --clean

deploy: image
	@echo "Deploying Aurora OS..."
	@echo "Deployment target to be implemented"

# Integration test shortcuts
.PHONY: test-integration
test-integration:
	@echo "Running integration tests..."
	python test_mcp_integration.py
	python test_desktop_shell_simple.py
	python test_system_services.py
	python test_ai_control_plane.py

# Full build workflow
.PHONY: full-build
full-build: build test-integration packages image
	@echo "Full build completed successfully!"

# Release workflow
.PHONY: release-build
release-build: clean
	@echo "Creating release build..."
	python build/build_pipeline.py --clean --publish

# Development setup
.PHONY: setup-dev
setup-dev: check-deps
	@echo "Setting up development environment..."
	pip install -r requirements.txt
	@echo "Development environment ready!"

# Continuous integration target
.PHONY: ci-build
ci-build: clean build test-integration packages
	@echo "CI pipeline completed successfully!"
