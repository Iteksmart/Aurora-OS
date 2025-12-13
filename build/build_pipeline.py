#!/usr/bin/env python3
"""
Aurora OS Automated Build Pipeline
"""

import os
import sys
import json
import time
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

class BuildStatus(Enum):
    """Build status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

class BuildStep(Enum):
    """Build pipeline steps"""
    VALIDATE = "validate"
    CLEAN = "clean"
    BUILD_KERNEL = "build_kernel"
    BUILD_PACKAGES = "build_packages"
    CREATE_IMAGE = "create_image"
    TEST_IMAGE = "test_image"
    PUBLISH = "publish"

@dataclass
class BuildResult:
    """Build result information"""
    step: BuildStep
    status: BuildStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    output: str = ""
    error: str = ""
    duration: float = 0.0

@dataclass
class BuildConfig:
    """Build configuration"""
    build_id: str = field(default_factory=lambda: f"build_{int(time.time())}")
    parallel_jobs: int = 4
    clean_build: bool = True
    run_tests: bool = True
    publish_artifacts: bool = False
    target_architectures: List[str] = field(default_factory=lambda: ["x86_64"])
    components: Dict[str, bool] = field(default_factory=lambda: {
        "kernel_extensions": True,
        "ai_control_plane": True,
        "desktop_shell": True,
        "system_services": True,
        "mcp_nervous_system": True
    })

class AuroraBuildPipeline:
    """Automated build pipeline for Aurora OS"""
    
    def __init__(self, config: Optional[BuildConfig] = None):
        self.config = config or BuildConfig()
        self.build_dir = Path("build/workspace")
        self.logs_dir = Path("build/logs")
        self.artifacts_dir = Path("build/artifacts")
        
        # Ensure directories exist
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        # Build state
        self.build_results: Dict[BuildStep, BuildResult] = {}
        self.current_step = None
        self.build_log = []
        
        # Initialize build steps
        self.build_steps = [
            BuildStep.VALIDATE,
            BuildStep.CLEAN,
            BuildStep.BUILD_KERNEL,
            BuildStep.BUILD_PACKAGES,
            BuildStep.CREATE_IMAGE,
            BuildStep.TEST_IMAGE,
            BuildStep.PUBLISH
        ]
        
        # Step handlers
        self.step_handlers = {
            BuildStep.VALIDATE: self._validate_environment,
            BuildStep.CLEAN: self._clean_workspace,
            BuildStep.BUILD_KERNEL: self._build_kernel_extensions,
            BuildStep.BUILD_PACKAGES: self._build_packages,
            BuildStep.CREATE_IMAGE: self._create_system_image,
            BuildStep.TEST_IMAGE: self._test_system_image,
            BuildStep.PUBLISH: self._publish_artifacts
        }
    
    def _log(self, message: str, level: str = "INFO"):
        """Log build message"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {level}: {message}"
        self.build_log.append(log_entry)
        print(log_entry)
    
    def _execute_step(self, step: BuildStep) -> BuildResult:
        """Execute a single build step"""
        start_time = datetime.now()
        result = BuildResult(step=step, status=BuildStatus.RUNNING, start_time=start_time)
        
        self._log(f"Starting build step: {step.value}")
        
        try:
            handler = self.step_handlers.get(step)
            if handler:
                output, error = handler()
                result.output = output
                result.error = error
                result.status = BuildStatus.SUCCESS if not error else BuildStatus.FAILED
            else:
                result.error = f"No handler for step: {step.value}"
                result.status = BuildStatus.FAILED
                
        except Exception as e:
            result.error = str(e)
            result.status = BuildStatus.FAILED
            self._log(f"Step {step.value} failed: {e}", "ERROR")
        
        result.end_time = datetime.now()
        result.duration = (result.end_time - result.start_time).total_seconds()
        
        self._log(f"Step {step.value} completed with status: {result.status.value}")
        return result
    
    def _validate_environment(self) -> tuple[str, str]:
        """Validate build environment"""
        output = []
        error = ""
        
        # Check required tools
        required_tools = ["gcc", "make", "python3", "pip", "git"]
        for tool in required_tools:
            try:
                result = subprocess.run(["which", tool], capture_output=True, text=True)
                if result.returncode == 0:
                    output.append(f"✓ {tool}: {result.stdout.strip()}")
                else:
                    error += f"Missing required tool: {tool}\n"
            except Exception as e:
                error += f"Error checking {tool}: {e}\n"
        
        # Check Python dependencies
        try:
            result = subprocess.run([
                "python3", "-c", 
                "import torch, transformers, fastapi; print('✓ Python dependencies OK')"
            ], capture_output=True, text=True)
            output.append(result.stdout.strip())
            if result.stderr:
                error += result.stderr
        except Exception as e:
            error += f"Python dependencies check failed: {e}\n"
        
        # Check source directories
        required_dirs = [
            "kernel/ai_extensions",
            "system/ai_control_plane",
            "desktop/aurora_shell",
            "system/services",
            "mcp"
        ]
        
        for dir_path in required_dirs:
            if Path(dir_path).exists():
                output.append(f"✓ Source directory: {dir_path}")
            else:
                output.append(f"⚠ Missing source directory: {dir_path}")
        
        return "\n".join(output), error
    
    def _clean_workspace(self) -> tuple[str, str]:
        """Clean build workspace"""
        output = []
        error = ""
        
        if self.config.clean_build:
            try:
                # Clean previous build artifacts
                if self.build_dir.exists():
                    shutil.rmtree(self.build_dir)
                    output.append("✓ Cleaned build directory")
                
                # Clean previous logs
                if self.logs_dir.exists():
                    for log_file in self.logs_dir.glob("*.log"):
                        log_file.unlink()
                    output.append("✓ Cleaned log files")
                
                # Recreate directories
                self.build_dir.mkdir(parents=True, exist_ok=True)
                output.append("✓ Recreated build directory")
                
            except Exception as e:
                error = f"Clean failed: {e}\n"
        else:
            output.append("✓ Skipped clean (incremental build)")
        
        return "\n".join(output), error
    
    def _build_kernel_extensions(self) -> tuple[str, str]:
        """Build AI kernel extensions"""
        if not self.config.components["kernel_extensions"]:
            return "✓ Skipped kernel extensions (disabled in config)", ""
        
        output = []
        error = ""
        
        try:
            # Build kernel extensions
            kernel_dir = Path("kernel/ai_extensions")
            if kernel_dir.exists():
                # Run make in kernel extensions directory
                result = subprocess.run([
                    "make", "-j", str(self.config.parallel_jobs)
                ], cwd=kernel_dir, capture_output=True, text=True, timeout=300)
                
                output.append(result.stdout)
                if result.returncode == 0:
                    output.append("✓ Kernel extensions built successfully")
                else:
                    error += result.stderr
            else:
                error += "Kernel extensions directory not found\n"
                
        except subprocess.TimeoutExpired:
            error += "Kernel build timed out\n"
        except Exception as e:
            error += f"Kernel build failed: {e}\n"
        
        return "\n".join(output), error
    
    def _build_packages(self) -> tuple[str, str]:
        """Build Aurora OS packages"""
        output = []
        error = ""
        
        try:
            # Import and run package manager
            sys.path.insert(0, str(Path("build")))
            from package_manager import create_core_packages
            
            create_core_packages()
            output.append("✓ Core packages created successfully")
            
            # List created packages
            packages_dir = Path("build/packages")
            if packages_dir.exists():
                for package in packages_dir.glob("*.aurora"):
                    output.append(f"✓ Package: {package.name}")
            
        except Exception as e:
            error += f"Package building failed: {e}\n"
        
        return "\n".join(output), error
    
    def _create_system_image(self) -> tuple[str, str]:
        """Create system image"""
        output = []
        error = ""
        
        try:
            # Import and run Aurora builder
            sys.path.insert(0, str(Path("build")))
            from aurora_builder import AuroraBuilder
            
            builder = AuroraBuilder()
            builder.build()
            output.append("✓ System image created successfully")
            
            # List created images
            images_dir = Path("build/images")
            if images_dir.exists():
                for image in images_dir.glob("*"):
                    output.append(f"✓ Image: {image.name}")
            
        except Exception as e:
            error += f"System image creation failed: {e}\n"
        
        return "\n".join(output), error
    
    def _test_system_image(self) -> tuple[str, str]:
        """Test system image"""
        if not self.config.run_tests:
            return "✓ Skipped testing (disabled in config)", ""
        
        output = []
        error = ""
        
        try:
            # Run integration tests
            test_files = [
                "test_mcp_integration.py",
                "test_desktop_shell_simple.py",
                "test_system_services.py",
                "test_ai_control_plane.py"
            ]
            
            for test_file in test_files:
                if Path(test_file).exists():
                    result = subprocess.run([
                        "python3", test_file
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        output.append(f"✓ Test passed: {test_file}")
                    else:
                        error += f"Test failed: {test_file}\n{result.stderr}\n"
                else:
                    output.append(f"⚠ Test not found: {test_file}")
            
        except Exception as e:
            error += f"Testing failed: {e}\n"
        
        return "\n".join(output), error
    
    def _publish_artifacts(self) -> tuple[str, str]:
        """Publish build artifacts"""
        if not self.config.publish_artifacts:
            return "✓ Skipped publishing (disabled in config)", ""
        
        output = []
        error = ""
        
        try:
            # Copy artifacts to artifacts directory
            artifacts = []
            
            # Add packages
            packages_dir = Path("build/packages")
            if packages_dir.exists():
                for package in packages_dir.glob("*.aurora"):
                    dest = self.artifacts_dir / package.name
                    shutil.copy2(package, dest)
                    artifacts.append(dest.name)
            
            # Add images
            images_dir = Path("build/images")
            if images_dir.exists():
                for image in images_dir.glob("*"):
                    dest = self.artifacts_dir / image.name
                    shutil.copy2(image, dest)
                    artifacts.append(dest.name)
            
            # Create build manifest
            manifest = {
                "build_id": self.config.build_id,
                "timestamp": datetime.now().isoformat(),
                "config": self.config.__dict__,
                "artifacts": artifacts,
                "build_results": {
                    step.value: {
                        "status": result.status.value,
                        "duration": result.duration
                    }
                    for step, result in self.build_results.items()
                }
            }
            
            manifest_file = self.artifacts_dir / f"build_{self.config.build_id}_manifest.json"
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            output.append(f"✓ Published {len(artifacts)} artifacts")
            output.append(f"✓ Build manifest: {manifest_file}")
            
        except Exception as e:
            error += f"Publishing failed: {e}\n"
        
        return "\n".join(output), error
    
    def build(self) -> bool:
        """Execute the complete build pipeline"""
        self._log(f"Starting Aurora OS build: {self.config.build_id}")
        
        for step in self.build_steps:
            self.current_step = step
            result = self._execute_step(step)
            self.build_results[step] = result
            
            # Stop pipeline on failure
            if result.status == BuildStatus.FAILED:
                self._log(f"Pipeline failed at step: {step.value}", "ERROR")
                return False
        
        self._log("Aurora OS build completed successfully!")
        return True
    
    def generate_report(self) -> str:
        """Generate build report"""
        report = []
        report.append(f"# Aurora OS Build Report")
        report.append(f"Build ID: {self.config.build_id}")
        report.append(f"Timestamp: {datetime.now().isoformat()}")
        report.append("")
        
        # Summary
        total_steps = len(self.build_results)
        successful_steps = sum(1 for r in self.build_results.values() if r.status == BuildStatus.SUCCESS)
        
        report.append(f"## Summary")
        report.append(f"- Total Steps: {total_steps}")
        report.append(f"- Successful: {successful_steps}")
        report.append(f"- Failed: {total_steps - successful_steps}")
        report.append("")
        
        # Step details
        report.append(f"## Build Steps")
        for step, result in self.build_results.items():
            status_icon = "✓" if result.status == BuildStatus.SUCCESS else "✗"
            report.append(f"- {status_icon} **{step.value}** ({result.duration:.2f}s)")
            if result.error:
                report.append(f"  - Error: {result.error}")
        
        # Configuration
        report.append(f"## Configuration")
        report.append(f"- Parallel Jobs: {self.config.parallel_jobs}")
        report.append(f"- Clean Build: {self.config.clean_build}")
        report.append(f"- Run Tests: {self.config.run_tests}")
        report.append(f"- Components: {self.config.components}")
        
        return "\n".join(report)
    
    def save_report(self):
        """Save build report to file"""
        report = self.generate_report()
        report_file = self.logs_dir / f"build_{self.config.build_id}_report.md"
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        # Save detailed log
        log_file = self.logs_dir / f"build_{self.config.build_id}_log.txt"
        with open(log_file, 'w') as f:
            f.write("\n".join(self.build_log))
        
        self._log(f"Build report saved: {report_file}")
        self._log(f"Build log saved: {log_file}")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Aurora OS Build Pipeline")
    parser.add_argument("--clean", action="store_true", help="Force clean build")
    parser.add_argument("--no-tests", action="store_true", help="Skip tests")
    parser.add_argument("--jobs", type=int, default=4, help="Parallel jobs")
    parser.add_argument("--publish", action="store_true", help="Publish artifacts")
    
    args = parser.parse_args()
    
    # Create build configuration
    config = BuildConfig(
        clean_build=args.clean,
        run_tests=not args.no_tests,
        parallel_jobs=args.jobs,
        publish_artifacts=args.publish
    )
    
    # Run build pipeline
    pipeline = AuroraBuildPipeline(config)
    success = pipeline.build()
    
    # Save report
    pipeline.save_report()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()