#!/usr/bin/env python3
"""
Aurora OS Package Manager - Manages Aurora OS packages and dependencies
"""

import os
import sys
import json
import hashlib
import subprocess
import shutil
import tarfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class PackageType(Enum):
    """Package types supported by Aurora OS"""
    SYSTEM = "system"
    AI_MODULE = "ai_module"
    DESKTOP = "desktop"
    SERVICE = "service"
    LIBRARY = "library"

@dataclass
class PackageInfo:
    """Package information structure"""
    name: str
    version: str
    description: str
    package_type: PackageType
    dependencies: List[str]
    conflicts: List[str]
    provides: List[str]
    size: int
    checksum: str
    install_path: str
    maintainer: str = "Aurora OS Team"

class AuroraPackageManager:
    """Package manager for Aurora OS"""
    
    def __init__(self, repo_path: str = "build/packages"):
        self.repo_path = Path(repo_path)
        self.installed_db = Path("build/installed_packages.json")
        self.packages_db = Path("build/packages.json")
        
        # Ensure directories exist
        self.repo_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize package databases
        self.installed_packages = self._load_installed_db()
        self.available_packages = self._load_packages_db()
    
    def _load_installed_db(self) -> Dict[str, PackageInfo]:
        """Load installed packages database"""
        if self.installed_db.exists():
            with open(self.installed_db, 'r') as f:
                data = json.load(f)
            return {name: PackageInfo(**pkg) for name, pkg in data.items()}
        return {}
    
    def _save_installed_db(self):
        """Save installed packages database"""
        data = {name: {
            'name': pkg.name,
            'version': pkg.version,
            'description': pkg.description,
            'package_type': pkg.package_type.value,
            'dependencies': pkg.dependencies,
            'conflicts': pkg.conflicts,
            'provides': pkg.provides,
            'size': pkg.size,
            'checksum': pkg.checksum,
            'install_path': pkg.install_path,
            'maintainer': pkg.maintainer
        } for name, pkg in self.installed_packages.items()}
        
        with open(self.installed_db, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_packages_db(self) -> Dict[str, PackageInfo]:
        """Load available packages database"""
        if self.packages_db.exists():
            with open(self.packages_db, 'r') as f:
                data = json.load(f)
            return {name: PackageInfo(**pkg) for name, pkg in data.items()}
        return {}
    
    def _save_packages_db(self):
        """Save available packages database"""
        data = {name: {
            'name': pkg.name,
            'version': pkg.version,
            'description': pkg.description,
            'package_type': pkg.package_type.value,
            'dependencies': pkg.dependencies,
            'conflicts': pkg.conflicts,
            'provides': pkg.provides,
            'size': pkg.size,
            'checksum': pkg.checksum,
            'install_path': pkg.install_path,
            'maintainer': pkg.maintainer
        } for name, pkg in self.available_packages.items()}
        
        with open(self.packages_db, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def create_package(self, source_path: str, package_info: PackageInfo, 
                      output_dir: str = "build/packages") -> str:
        """Create an Aurora package from source"""
        source = Path(source_path)
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        
        # Create package filename
        package_file = output / f"{package_info.name}-{package_info.version}.aurora"
        
        # Calculate package size and checksum
        if source.is_file():
            package_info.size = source.stat().st_size
            package_info.checksum = self._calculate_checksum(source)
        else:
            # Calculate for directory
            total_size = 0
            for file_path in source.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            package_info.size = total_size
        
        # Create package metadata
        metadata = {
            'package_info': {
                'name': package_info.name,
                'version': package_info.version,
                'description': package_info.description,
                'package_type': package_info.package_type.value,
                'dependencies': package_info.dependencies,
                'conflicts': package_info.conflicts,
                'provides': package_info.provides,
                'size': package_info.size,
                'checksum': package_info.checksum,
                'install_path': package_info.install_path,
                'maintainer': package_info.maintainer
            }
        }
        
        # Create package archive
        with tarfile.open(package_file, 'w:gz') as tar:
            # Add metadata
            metadata_path = Path("metadata.json")
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            tar.add(metadata_path, arcname="metadata.json")
            Path(metadata_path).unlink()  # Remove temp file
            
            # Add source files
            if source.is_file():
                tar.add(source, arcname=f"data/{source.name}")
            else:
                for item in source.rglob('*'):
                    if item.is_file():
                        arcname = f"data/{item.relative_to(source)}"
                        tar.add(item, arcname=arcname)
        
        # Add to available packages
        self.available_packages[package_info.name] = package_info
        self._save_packages_db()
        
        print(f"Package created: {package_file}")
        return str(package_file)
    
    def install_package(self, package_path: str, target_path: str = "/opt/aurora") -> bool:
        """Install an Aurora package"""
        package_file = Path(package_path)
        
        if not package_file.exists():
            print(f"Package not found: {package_path}")
            return False
        
        # Extract and read metadata
        with tarfile.open(package_file, 'r:gz') as tar:
            try:
                metadata_member = tar.getmember("metadata.json")
                metadata_file = tar.extractfile(metadata_member)
                metadata = json.load(metadata_file)
                pkg_info = PackageInfo(**metadata['package_info'])
            except (KeyError, json.JSONDecodeError) as e:
                print(f"Invalid package format: {e}")
                return False
        
        # Check dependencies
        for dep in pkg_info.dependencies:
            if dep not in self.installed_packages:
                print(f"Missing dependency: {dep}")
                return False
        
        # Check conflicts
        for conflict in pkg_info.conflicts:
            if conflict in self.installed_packages:
                print(f"Package conflicts with installed: {conflict}")
                return False
        
        # Install package
        install_target = Path(target_path) / pkg_info.install_path
        install_target.mkdir(parents=True, exist_ok=True)
        
        with tarfile.open(package_file, 'r:gz') as tar:
            for member in tar.getmembers():
                if member.name.startswith("data/"):
                    member.name = member.name[5:]  # Remove "data/" prefix
                    tar.extract(member, path=install_target)
        
        # Add to installed packages
        self.installed_packages[pkg_info.name] = pkg_info
        self._save_installed_db()
        
        print(f"Package installed: {pkg_info.name} v{pkg_info.version}")
        return True
    
    def remove_package(self, package_name: str) -> bool:
        """Remove an installed package"""
        if package_name not in self.installed_packages:
            print(f"Package not installed: {package_name}")
            return False
        
        pkg_info = self.installed_packages[package_name]
        
        # Check if other packages depend on this
        for name, pkg in self.installed_packages.items():
            if package_name in pkg.dependencies and name != package_name:
                print(f"Cannot remove {package_name}: required by {name}")
                return False
        
        # Remove package files
        install_path = Path(f"/opt/aurora/{pkg_info.install_path}")
        if install_path.exists():
            shutil.rmtree(install_path)
        
        # Remove from installed packages
        del self.installed_packages[package_name]
        self._save_installed_db()
        
        print(f"Package removed: {package_name}")
        return True
    
    def list_installed(self) -> List[PackageInfo]:
        """List all installed packages"""
        return list(self.installed_packages.values())
    
    def list_available(self) -> List[PackageInfo]:
        """List all available packages"""
        return list(self.available_packages.values())
    
    def search(self, query: str) -> List[PackageInfo]:
        """Search for packages"""
        results = []
        query_lower = query.lower()
        
        for pkg in self.available_packages.values():
            if (query_lower in pkg.name.lower() or 
                query_lower in pkg.description.lower()):
                results.append(pkg)
        
        return results
    
    def update(self) -> bool:
        """Update package database"""
        # In a real implementation, this would download from a remote repository
        print("Package database updated (local mode)")
        return True

def create_core_packages():
    """Create core Aurora OS packages"""
    pm = AuroraPackageManager()
    
    # AI Kernel Extensions package
    kernel_pkg = PackageInfo(
        name="aurora-kernel-extensions",
        version="0.1.0",
        description="AI-enhanced kernel extensions for Aurora OS",
        package_type=PackageType.SYSTEM,
        dependencies=["linux-headers-generic"],
        conflicts=[],
        provides=["ai-scheduler", "ai-context-manager", "ai-security"],
        size=0,  # Will be calculated
        checksum="",  # Will be calculated
        install_path="kernel_extensions",
        maintainer="Aurora OS Team"
    )
    
    if Path("../kernel/ai_extensions").exists():
        pm.create_package("../kernel/ai_extensions", kernel_pkg)
    
    # AI Control Plane package
    control_plane_pkg = PackageInfo(
        name="aurora-ai-control-plane",
        version="0.1.0",
        description="AI control plane for natural language interface",
        package_type=PackageType.AI_MODULE,
        dependencies=["python3", "python3-pip", "aurora-mcp-nervous-system"],
        conflicts=[],
        provides=["intent-engine", "nlu-core"],
        size=0,
        checksum="",
        install_path="ai_control_plane",
        maintainer="Aurora OS Team"
    )
    
    if Path("../system/ai_control_plane").exists():
        pm.create_package("../system/ai_control_plane", control_plane_pkg)
    
    # Desktop Shell package
    desktop_pkg = PackageInfo(
        name="aurora-desktop-shell",
        version="0.1.0",
        description="AI-native desktop environment",
        package_type=PackageType.DESKTOP,
        dependencies=["python3", "xorg", "python3-tk"],
        conflicts=[],
        provides=["aurora-shell", "conversational-palette"],
        size=0,
        checksum="",
        install_path="desktop",
        maintainer="Aurora OS Team"
    )
    
    if Path("../desktop/aurora_shell").exists():
        pm.create_package("../desktop/aurora_shell", desktop_pkg)
    
    # System Services package
    services_pkg = PackageInfo(
        name="aurora-system-services",
        version="0.1.0",
        description="Aurora OS system services and utilities",
        package_type=PackageType.SERVICE,
        dependencies=["python3", "systemd"],
        conflicts=[],
        provides=["file-manager", "service-manager"],
        size=0,
        checksum="",
        install_path="services",
        maintainer="Aurora OS Team"
    )
    
    if Path("../system/services").exists():
        pm.create_package("../system/services", services_pkg)
    
    # MCP Nervous System package
    mcp_pkg = PackageInfo(
        name="aurora-mcp-nervous-system",
        version="0.1.0",
        description="Model Context Protocol nervous system for Aurora OS",
        package_type=PackageType.AI_MODULE,
        dependencies=["python3", "python3-pip"],
        conflicts=[],
        provides=["mcp-host", "context-providers"],
        size=0,
        checksum="",
        install_path="mcp",
        maintainer="Aurora OS Team"
    )
    
    if Path("../mcp").exists():
        pm.create_package("../mcp", mcp_pkg)
    
    print("Core Aurora OS packages created successfully!")

def main():
    """Main entry point for package manager"""
    if len(sys.argv) < 2:
        print("Usage: python package_manager.py <command> [args]")
        print("Commands:")
        print("  create-core       Create core Aurora packages")
        print("  list-installed    List installed packages")
        print("  list-available    List available packages")
        print("  search <query>    Search for packages")
        print("  install <package> Install a package")
        print("  remove <package>  Remove a package")
        return
    
    command = sys.argv[1]
    pm = AuroraPackageManager()
    
    if command == "create-core":
        create_core_packages()
    elif command == "list-installed":
        for pkg in pm.list_installed():
            print(f"{pkg.name} v{pkg.version} - {pkg.description}")
    elif command == "list-available":
        for pkg in pm.list_available():
            print(f"{pkg.name} v{pkg.version} - {pkg.description}")
    elif command == "search":
        if len(sys.argv) < 3:
            print("Usage: python package_manager.py search <query>")
            return
        results = pm.search(sys.argv[2])
        for pkg in results:
            print(f"{pkg.name} v{pkg.version} - {pkg.description}")
    elif command == "install":
        if len(sys.argv) < 3:
            print("Usage: python package_manager.py install <package_path>")
            return
        pm.install_package(sys.argv[2])
    elif command == "remove":
        if len(sys.argv) < 3:
            print("Usage: python package_manager.py remove <package_name>")
            return
        pm.remove_package(sys.argv[2])
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()