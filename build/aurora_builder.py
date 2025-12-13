#!/usr/bin/env python3
"""
Aurora OS Builder - Creates bootable Aurora OS images
"""

import os
import sys
import subprocess
import shutil
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

class AuroraBuilder:
    """Builds Aurora OS images from source components"""
    
    def __init__(self, config_path: str = "build/config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.build_dir = Path("build/workspace")
        self.image_dir = Path("build/images")
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Ensure directories exist
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self.image_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self) -> Dict:
        """Load build configuration"""
        default_config = {
            "os_name": "Aurora OS",
            "version": "0.1.0",
            "arch": "x86_64",
            "base_distro": "ubuntu",
            "base_version": "22.04",
            "kernel_version": "6.x",
            "packages": [
                "python3",
                "python3-pip",
                "build-essential",
                "git",
                "curl",
                "wget",
                "grub-pc",
                "systemd",
                "xorg",
                "gnome-session"
            ],
            "aurora_components": {
                "kernel_extensions": True,
                "ai_control_plane": True,
                "desktop_shell": True,
                "system_services": True,
                "mcp_nervous_system": True
            }
        }
        
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            # Merge with defaults
            return {**default_config, **config}
        else:
            # Create default config
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config
    
    def create_base_system(self):
        """Create base system structure"""
        self.logger.info("Creating base system structure...")
        
        # Create directory structure
        dirs = [
            "boot/grub",
            "bin",
            "sbin",
            "usr/bin",
            "usr/sbin",
            "usr/lib",
            "lib",
            "etc",
            "var/log",
            "opt/aurora",
            "usr/share/aurora",
            "home/aurora"
        ]
        
        for dir_path in dirs:
            full_path = self.build_dir / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("Base system structure created")
    
    def install_kernel_extensions(self):
        """Install AI kernel extensions"""
        if not self.config["aurora_components"]["kernel_extensions"]:
            return
            
        self.logger.info("Installing AI kernel extensions...")
        
        # Copy kernel extension source
        kernel_src = Path("kernel/ai_extensions")
        if kernel_src.exists():
            shutil.copytree(kernel_src, self.build_dir / "opt/aurora/kernel_extensions")
        
        # Create kernel module installation script
        install_script = self.build_dir / "opt/aurora/install_kernel_modules.sh"
        install_script.write_text("""#!/bin/bash
# Install Aurora AI Kernel Extensions
cd /opt/aurora/kernel_extensions
make clean && make
make install
depmod -a
echo "Aurora AI Kernel Extensions installed successfully"
""")
        install_script.chmod(0o755)
        
        self.logger.info("AI kernel extensions installed")
    
    def install_ai_control_plane(self):
        """Install AI control plane components"""
        if not self.config["aurora_components"]["ai_control_plane"]:
            return
            
        self.logger.info("Installing AI control plane...")
        
        # Copy AI control plane
        control_plane_src = Path("system/ai_control_plane")
        if control_plane_src.exists():
            shutil.copytree(control_plane_src, self.build_dir / "opt/aurora/ai_control_plane")
        
        # Install Python dependencies
        requirements_src = Path("requirements.txt")
        if requirements_src.exists():
            shutil.copy(requirements_src, self.build_dir / "opt/aurora/requirements.txt")
        
        # Create AI control plane service
        service_dir = self.build_dir / "etc/systemd/system"
        service_dir.mkdir(parents=True, exist_ok=True)
        service_file = service_dir / "aurora-ai-control-plane.service"
        service_file.write_text("""[Unit]
Description=Aurora OS AI Control Plane
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/aurora/ai_control_plane
ExecStart=/usr/bin/python3 -m intent_engine
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
""")
        
        self.logger.info("AI control plane installed")
    
    def install_desktop_shell(self):
        """Install Aurora desktop shell"""
        if not self.config["aurora_components"]["desktop_shell"]:
            return
            
        self.logger.info("Installing Aurora desktop shell...")
        
        # Copy desktop shell
        desktop_src = Path("desktop/aurora_shell")
        if desktop_src.exists():
            shutil.copytree(desktop_src, self.build_dir / "opt/aurora/desktop")
        
        # Create desktop session file
        xsessions_dir = self.build_dir / "usr/share/xsessions"
        xsessions_dir.mkdir(parents=True, exist_ok=True)
        session_file = xsessions_dir / "aurora.desktop"
        session_file.write_text("""[Desktop Entry]
Name=Aurora OS
Comment=Aurora AI-Native Desktop Environment
Exec=/opt/aurora/desktop/launch_aurora.sh
Type=Application
""")
        
        # Create launch script
        desktop_dir = self.build_dir / "opt/aurora/desktop"
        desktop_dir.mkdir(parents=True, exist_ok=True)
        launch_script = desktop_dir / "launch_aurora.sh"
        launch_script.write_text("""#!/bin/bash
# Launch Aurora Desktop Environment
export PYTHONPATH=/opt/aurora:$PYTHONPATH
cd /opt/aurora/desktop
python3 compositor.py
""")
        launch_script.chmod(0o755)
        
        self.logger.info("Aurora desktop shell installed")
    
    def install_system_services(self):
        """Install Aurora system services"""
        if not self.config["aurora_components"]["system_services"]:
            return
            
        self.logger.info("Installing Aurora system services...")
        
        # Copy system services
        services_src = Path("system/services")
        if services_src.exists():
            shutil.copytree(services_src, self.build_dir / "opt/aurora/services")
        
        # Create service manager service
        service_dir = self.build_dir / "etc/systemd/system"
        service_dir.mkdir(parents=True, exist_ok=True)
        service_file = service_dir / "aurora-service-manager.service"
        service_file.write_text("""[Unit]
Description=Aurora OS Service Manager
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/aurora/services
ExecStart=/usr/bin/python3 service_manager.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
""")
        
        self.logger.info("Aurora system services installed")
    
    def install_mcp_nervous_system(self):
        """Install MCP nervous system"""
        if not self.config["aurora_components"]["mcp_nervous_system"]:
            return
            
        self.logger.info("Installing MCP nervous system...")
        
        # Copy MCP components
        mcp_src = Path("mcp")
        if mcp_src.exists():
            shutil.copytree(mcp_src, self.build_dir / "opt/aurora/mcp")
        
        # Create MCP service
        service_dir = self.build_dir / "etc/systemd/system"
        service_dir.mkdir(parents=True, exist_ok=True)
        service_file = service_dir / "aurora-mcp.service"
        service_file.write_text("""[Unit]
Description=Aurora OS MCP Nervous System
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/aurora/mcp
ExecStart=/usr/bin/python3 system/mcp_host.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
""")
        
        self.logger.info("MCP nervous system installed")
    
    def create_boot_configuration(self):
        """Create boot configuration (GRUB)"""
        self.logger.info("Creating boot configuration...")
        
        # Create GRUB configuration
        grub_dir = self.build_dir / "boot/grub"
        grub_dir.mkdir(parents=True, exist_ok=True)
        grub_cfg = grub_dir / "grub.cfg"
        grub_cfg.write_text(f"""set default=0
set timeout=5

menuentry "{self.config['os_name']} {self.config['version']}" {{
    linux /boot/vmlinuz-{self.config['kernel_version']} root=/dev/sda1 ro quiet splash
    initrd /boot/initrd.img-{self.config['kernel_version']}
}}

menuentry "{self.config['os_name']} {self.config['version']} (Recovery)" {{
    linux /boot/vmlinuz-{self.config['kernel_version']} root=/dev/sda1 ro recovery
    initrd /boot/initrd.img-{self.config['kernel_version']}
}}
""")
        
        self.logger.info("Boot configuration created")
    
    def create_system_config(self):
        """Create system configuration files"""
        self.logger.info("Creating system configuration...")
        
        # Create fstab
        fstab = self.build_dir / "etc/fstab"
        fstab.write_text("""# Aurora OS fstab
/dev/sda1 / ext4 errors=remount-ro 0 1
/dev/sda2 none swap sw 0 0
""")
        
        # Create hosts file
        hosts = self.build_dir / "etc/hosts"
        hosts.write_text("""127.0.0.1 localhost
127.0.1.1 aurora-os
# The following lines are desirable for IPv6 capable hosts
::1     ip6-localhost ip6-loopback
""")
        
        # Create hostname
        hostname = self.build_dir / "etc/hostname"
        hostname.write_text("aurora-os\n")
        
        self.logger.info("System configuration created")
    
    def create_iso_image(self):
        """Create bootable ISO image"""
        self.logger.info("Creating bootable ISO image...")
        
        image_name = f"aurora-os-{self.config['version']}.iso"
        image_path = self.image_dir / image_name
        
        # Create ISO using genisoimage or mkisofs
        cmd = [
            "genisoimage",
            "-o", str(image_path),
            "-b", "boot/grub/i386-pc/eltorito.img",
            "-no-emul-boot",
            "-boot-load-size", "4",
            "-boot-info-table",
            "-J", "-R", "-V", f"Aurora OS {self.config['version']}",
            str(self.build_dir)
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            self.logger.info(f"ISO image created: {image_path}")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to create ISO: {e}")
            # Fallback to simpler method
            self.logger.info("Creating basic ISO image...")
            subprocess.run([
                "tar", "-czf", f"{image_path}.tgz", 
                "-C", str(self.build_dir), "."
            ], check=True)
            self.logger.info(f"Archive created: {image_path}.tgz")
    
    def build(self):
        """Build complete Aurora OS image"""
        self.logger.info(f"Building {self.config['os_name']} {self.config['version']}")
        
        # Build steps
        self.create_base_system()
        self.install_kernel_extensions()
        self.install_ai_control_plane()
        self.install_desktop_shell()
        self.install_system_services()
        self.install_mcp_nervous_system()
        self.create_boot_configuration()
        self.create_system_config()
        self.create_iso_image()
        
        self.logger.info("Aurora OS build completed successfully!")

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
        builder = AuroraBuilder(config_path)
    else:
        builder = AuroraBuilder()
    
    builder.build()

if __name__ == "__main__":
    main()