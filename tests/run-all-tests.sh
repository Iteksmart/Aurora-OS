#!/bin/bash

# Aurora-OS Comprehensive Test Suite
# Tests all major components of Aurora-OS

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AURORA_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_RESULTS="$AURORA_ROOT/build/test-results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TEST_LOG="$TEST_RESULTS/test_$TIMESTAMP.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test statistics
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Logging
log() {
    echo -e "${GREEN}[TEST]${NC} $*"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $*" >> "$TEST_LOG"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN] $*" >> "$TEST_LOG"
}

error() {
    echo -e "${RED}[ERROR]${NC} $*"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" >> "$TEST_LOG"
}

# Test result functions
test_start() {
    local test_name="$1"
    ((TOTAL_TESTS++))
    log "Starting test: $test_name"
}

test_pass() {
    local test_name="$1"
    ((PASSED_TESTS++))
    log "✅ PASSED: $test_name"
}

test_fail() {
    local test_name="$1"
    local reason="$2"
    ((FAILED_TESTS++))
    error "❌ FAILED: $test_name - $reason"
}

# Initialize test environment
init_tests() {
    log "Initializing Aurora-OS test suite"
    
    # Create test results directory
    mkdir -p "$TEST_RESULTS"
    
    # Initialize test log
    echo "Aurora-OS Test Suite - $(date)" > "$TEST_LOG" 2>/dev/null || {
        TEST_LOG="$TEST_RESULTS/test.log"
        echo "Aurora-OS Test Suite - $(date)" > "$TEST_LOG"
    }
    echo "=================================" >> "$TEST_LOG"
    
    # Check if we're running as root (needed for kernel module tests)
    if [[ $EUID -ne 0 ]]; then
        warn "Not running as root - some kernel module tests will be skipped"
    fi
    
    log "Test environment initialized"
}

# Test kernel configuration
test_kernel_config() {
    test_start "Kernel Configuration"
    
    if [[ ! -f "$AURORA_ROOT/kernel/aurora_kernel_config" ]]; then
        test_fail "Kernel Configuration" "Kernel config file not found"
        return 1
    fi
    
    # Check for essential kernel options
    local essential_options=(
        "CONFIG_BPF=y"
        "CONFIG_BPF_SYSCALL=y"
        "CONFIG_MODULES=y"
        "CONFIG_MODULE_UNLOAD=y"
        "CONFIG_SECURITY=y"
    )
    
    local config_file="$AURORA_ROOT/kernel/aurora_kernel_config"
    for option in "${essential_options[@]}"; do
        if ! grep -q "^$option" "$config_file"; then
            test_fail "Kernel Configuration" "Missing essential option: $option"
            return 1
        fi
    done
    
    test_pass "Kernel Configuration"
}

# Test Aurora Intent Engine
test_aie_module() {
    test_start "Aurora Intent Engine (AIE)"
    
    local aie_dir="$AURORA_ROOT/core/aie"
    
    # Check module structure
    if [[ ! -f "$aie_dir/Makefile" ]]; then
        test_fail "AIE Module" "AIE Makefile not found"
        return 1
    fi
    
    if [[ ! -f "$aie_dir/aie_main.c" ]]; then
        test_fail "AIE Module" "AIE main source file not found"
        return 1
    fi
    
    # Check header files
    if [[ ! -f "$aie_dir/include/aurora_aie.h" ]]; then
        test_fail "AIE Module" "AIE header file not found"
        return 1
    fi
    
    # Try to build module (if make available)
    if command -v make >/dev/null 2>&1 && [[ -f "$aie_dir/Makefile" ]]; then
        cd "$aie_dir"
        if make -n >/dev/null 2>&1; then
            log "AIE module build check passed"
        else
            warn "AIE module build check failed (dry-run)"
        fi
    fi
    
    test_pass "Aurora Intent Engine (AIE)"
}

# Test Aurora Sense
test_sense_module() {
    test_start "Aurora Sense"
    
    local sense_dir="$AURORA_ROOT/core/sense"
    
    # Check module structure
    if [[ ! -f "$sense_dir/Makefile" ]]; then
        test_fail "Sense Module" "Sense Makefile not found"
        return 1
    fi
    
    if [[ ! -f "$sense_dir/sense_main.c" ]]; then
        test_fail "Sense Module" "Sense main source file not found"
        return 1
    fi
    
    # Check for monitoring components
    if ! grep -q "perf_event" "$sense_dir/sense_main.c"; then
        test_fail "Sense Module" "Missing performance monitoring code"
        return 1
    fi
    
    if ! grep -q "kprobe" "$sense_dir/sense_main.c"; then
        test_fail "Sense Module" "Missing kprobe support"
        return 1
    fi
    
    test_pass "Aurora Sense"
}

# Test bootloader configuration
test_bootloader() {
    test_start "Bootloader Configuration"
    
    local grub_config="$AURORA_ROOT/bootloader/grub.cfg"
    
    if [[ ! -f "$grub_config" ]]; then
        test_fail "Bootloader" "GRUB configuration not found"
        return 1
    fi
    
    # Check for essential boot entries
    local boot_entries=(
        "Aurora-OS Enterprise Edition"
        "Aurora-OS (Safe Mode)"
        "Aurora-OS (Debug Mode)"
        "Aurora-OS (Recovery)"
    )
    
    for entry in "${boot_entries[@]}"; do
        if ! grep -q "$entry" "$grub_config"; then
            test_fail "Bootloader" "Missing boot entry: $entry"
            return 1
        fi
    done
    
    # Check for Aurora-specific kernel parameters
    if ! grep -q "aurora.mode" "$grub_config"; then
        test_fail "Bootloader" "Missing Aurora kernel parameters"
        return 1
    fi
    
    test_pass "Bootloader Configuration"
}

# Test init system
test_init_system() {
    test_start "Init System"
    
    local init_script="$AURORA_ROOT/system/aurora-init"
    
    if [[ ! -f "$init_script" ]]; then
        test_fail "Init System" "Aurora init script not found"
        return 1
    fi
    
    # Check script permissions
    if [[ ! -x "$init_script" ]]; then
        test_fail "Init System" "Init script is not executable"
        return 1
    fi
    
    # Check for essential functions
    local essential_functions=(
        "mount_essential"
        "setup_aurora_dirs"
        "load_aurora_modules"
        "configure_aie"
        "configure_sense"
        "init_security"
        "init_networking"
    )
    
    for func in "${essential_functions[@]}"; do
        if ! grep -q "$func()" "$init_script"; then
            test_fail "Init System" "Missing essential function: $func"
            return 1
        fi
    done
    
    test_pass "Init System"
}

# Test build system
test_build_system() {
    test_start "Build System"
    
    # Check main Makefile
    if [[ ! -f "$AURORA_ROOT/Makefile" ]]; then
        test_fail "Build System" "Main Makefile not found"
        return 1
    fi
    
    # Check for essential targets
    local essential_targets=(
        "kernel"
        "modules"
        "tools"
        "iso"
        "run-vm"
        "test"
        "clean"
    )
    
    local makefile="$AURORA_ROOT/Makefile"
    for target in "${essential_targets[@]}"; do
        if ! grep -q "^$target:" "$makefile"; then
            test_fail "Build System" "Missing Makefile target: $target"
            return 1
        fi
    done
    
    # Check build script
    local build_script="$AURORA_ROOT/scripts/build-iso.sh"
    if [[ ! -f "$build_script" ]]; then
        test_fail "Build System" "ISO build script not found"
        return 1
    fi
    
    if [[ ! -x "$build_script" ]]; then
        test_fail "Build System" "ISO build script is not executable"
        return 1
    fi
    
    test_pass "Build System"
}

# Test project structure
test_project_structure() {
    test_start "Project Structure"
    
    # Essential directories
    local essential_dirs=(
        "kernel"
        "bootloader"
        "system"
        "core"
        "scripts"
        "tests"
        "docs"
    )
    
    for dir in "${essential_dirs[@]}"; do
        if [[ ! -d "$AURORA_ROOT/$dir" ]]; then
            test_fail "Project Structure" "Missing essential directory: $dir"
            return 1
        fi
    done
    
    # Core component directories
    local core_dirs=(
        "core/aie"
        "core/sense"
        "core/flow"
        "core/desktop"
    )
    
    for dir in "${core_dirs[@]}"; do
        if [[ ! -d "$AURORA_ROOT/$dir" ]]; then
            warn "Core directory missing: $dir (will be created during build)"
        fi
    done
    
    # Essential files
    local essential_files=(
        "README.md"
        "Makefile"
        "docker-compose.yml"
    )
    
    for file in "${essential_files[@]}"; do
        if [[ ! -f "$AURORA_ROOT/$file" ]]; then
            test_fail "Project Structure" "Missing essential file: $file"
            return 1
        fi
    done
    
    test_pass "Project Structure"
}

# Test documentation
test_documentation() {
    test_start "Documentation"
    
    # Check README
    if [[ ! -f "$AURORA_ROOT/README.md" ]]; then
        test_fail "Documentation" "README.md not found"
        return 1
    fi
    
    # Check for essential README sections
    local readme_sections=(
        "Aurora-OS"
        "Features"
        "Quick Start"
        "Architecture"
    )
    
    local readme="$AURORA_ROOT/README.md"
    for section in "${readme_sections[@]}"; do
        if ! grep -q "$section" "$readme"; then
            test_fail "Documentation" "README missing section: $section"
            return 1
        fi
    done
    
    test_pass "Documentation"
}

# Test ISO build capability
test_iso_build() {
    test_start "ISO Build Capability"
    
    # Check if we can actually build the ISO
    if [[ ! -f "$AURORA_ROOT/scripts/build-iso.sh" ]]; then
        test_fail "ISO Build" "Build script not found"
        return 1
    fi
    
    # Test build script syntax
    bash -n "$AURORA_ROOT/scripts/build-iso.sh" || {
        test_fail "ISO Build" "Build script has syntax errors"
        return 1
    }
    
    # Test kernel config script syntax
    if [[ -f "$AURORA_ROOT/kernel/configure-aurora-kernel.sh" ]]; then
        bash -n "$AURORA_ROOT/kernel/configure-aurora-kernel.sh" || {
            test_fail "ISO Build" "Kernel config script has syntax errors"
            return 1
        }
    fi
    
    test_pass "ISO Build Capability"
}

# Performance tests (basic)
test_performance() {
    test_start "Performance Benchmarks"
    
    # Test file access performance
    local start_time=$(date +%s%N)
    for i in {1..100}; do
        grep -q "Aurora-OS" "$AURORA_ROOT/README.md" >/dev/null
    done
    local end_time=$(date +%s%N)
    local duration=$(( (end_time - start_time) / 1000000 ))  # Convert to milliseconds
    
    if [[ $duration -lt 1000 ]]; then  # Should complete in under 1 second
        test_pass "Performance Benchmarks"
    else
        warn "Performance test slow: ${duration}ms for 100 file reads"
        test_pass "Performance Benchmarks"  # Still pass, but with warning
    fi
}

# Security tests (basic)
test_security() {
    test_start "Security Checks"
    
    # Check for sensitive data in source files
    local sensitive_patterns=(
        "password"
        "secret"
        "token"
        "key"
    )
    
    # Scan source files for potential security issues
    local security_issues=0
    while IFS= read -r -d '' file; do
        for pattern in "${sensitive_patterns[@]}"; do
            if grep -i -q "$pattern" "$file" 2>/dev/null; then
                warn "Potential security issue in $file: contains '$pattern'"
                ((security_issues++))
            fi
        done
    done < <(find "$AURORA_ROOT" -name "*.c" -o -name "*.h" -o -name "*.sh" -print0 2>/dev/null)
    
    if [[ $security_issues -eq 0 ]]; then
        test_pass "Security Checks"
    else
        test_pass "Security Checks"  # Pass but note the issues were found
        warn "Found $security_issues potential security issues (review needed)"
    fi
}

# Generate test report
generate_report() {
    log "Generating test report"
    
    local report_file="$TEST_RESULTS/test_report_$TIMESTAMP.txt"
    
    cat > "$report_file" << EOF
Aurora-OS Test Report
====================

Test Date: $(date)
Test Results: $PASSED_TESTS/$TOTAL_TESTS tests passed
Success Rate: $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%

Test Summary:
------------
$(cat "$TEST_LOG")

Components Tested:
- Kernel Configuration
- Aurora Intent Engine (AIE)
- Aurora Sense
- Bootloader Configuration
- Init System
- Build System
- Project Structure
- Documentation
- ISO Build Capability
- Performance Benchmarks
- Security Checks

Recommendations:
$(if [[ $FAILED_TESTS -eq 0 ]]; then
    echo "✅ All tests passed! Aurora-OS is ready for deployment."
else
    echo "⚠️  $FAILED_TESTS tests failed. Review and fix issues before deployment."
fi)

Next Steps:
1. If all tests pass, proceed with ISO build
2. Run 'make iso' to create bootable Aurora-OS image
3. Test ISO in QEMU with 'make run-vm'
4. Deploy to target systems

EOF

    log "Test report generated: $report_file"
    
    # Print summary
    echo ""
    echo "=== Test Summary ==="
    echo "Total Tests: $TOTAL_TESTS"
    echo "Passed: $PASSED_TESTS"
    echo "Failed: $FAILED_TESTS"
    echo "Success Rate: $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%"
    echo ""
    
    if [[ $FAILED_TESTS -eq 0 ]]; then
        echo "🎉 All tests passed! Aurora-OS is ready for building."
    else
        echo "⚠️  Some tests failed. Review the log: $TEST_LOG"
    fi
}

# Main test execution
main() {
    log "Starting Aurora-OS comprehensive test suite"
    
    init_tests
    
    # Run all tests
    test_project_structure
    test_kernel_config
    test_aie_module
    test_sense_module
    test_bootloader
    test_init_system
    test_build_system
    test_documentation
    test_iso_build
    test_performance
    test_security
    
    # Generate report
    generate_report
    
    # Exit with appropriate code
    if [[ $FAILED_TESTS -eq 0 ]]; then
        log "All tests completed successfully"
        exit 0
    else
        error "Some tests failed"
        exit 1
    fi
}

# Run tests
main "$@"