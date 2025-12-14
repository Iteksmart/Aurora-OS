"""
Aurora OS Hardware Driver Manager
Central management system for all hardware drivers and AI acceleration
"""

import os
import sys
import json
import logging
import subprocess
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

class DriverType(Enum):
    GPU = "gpu"
    NETWORK = "network"
    STORAGE = "storage"
    AI_ACCELERATOR = "ai_accelerator"
    SECURITY = "security"
    AUDIO = "audio"
    USB = "usb"
    BLUETOOTH = "bluetooth"

class DriverStatus(Enum):
    NOT_INSTALLED = "not_installed"
    INSTALLED = "installed"
    LOADED = "loaded"
    ACTIVE = "active"
    ERROR = "error"

@dataclass
class DriverInfo:
    """Driver information and status"""
    name: str
    driver_type: DriverType
    version: str
    status: DriverStatus
    description: str
    hardware_ids: List[str]
    dependencies: List[str]
    loaded_modules: List[str]
    performance_metrics: Dict[str, Any]
    last_updated: float

class HardwareDriverManager:
    """Central hardware driver management system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.drivers: Dict[str, DriverInfo] = {}
        self.hardware_registry = {}
        self.performance_monitor = None
        self.ai_optimizer = None
        
        # Initialize driver registry
        self._initialize_driver_registry()
        
    def _initialize_driver_registry(self):
        """Initialize the driver registry with known drivers"""
        self.drivers = {
            # GPU Drivers
            'nvidia': DriverInfo(
                name='nvidia',
                driver_type=DriverType.GPU,
                version='535.129.03',
                status=DriverStatus.NOT_INSTALLED,
                description='NVIDIA GPU driver for AI acceleration',
                hardware_ids=['10de:'],
                dependencies=['nvidia-drm', 'nvidia-uvm'],
                loaded_modules=[],
                performance_metrics={},
                last_updated=0
            ),
            'amdgpu': DriverInfo(
                name='amdgpu',
                driver_type=DriverType.GPU,
                version='6.1.0',
                status=DriverStatus.NOT_INSTALLED,
                description='AMD GPU driver for ROCm support',
                hardware_ids=['1002:'],
                dependencies=['amdgpu', 'amdkfd'],
                loaded_modules=[],
                performance_metrics={},
                last_updated=0
            ),
            'i915': DriverInfo(
                name='i915',
                driver_type=DriverType.GPU,
                version='6.1.0',
                status=DriverStatus.NOT_INSTALLED,
                description='Intel GPU driver',
                hardware_ids=['8086:'],
                dependencies=['i915'],
                loaded_modules=[],
                performance_metrics={},
                last_updated=0
            ),
            
            # AI Accelerator Drivers
            'intel_npu': DriverInfo(
                name='intel_npu',
                driver_type=DriverType.AI_ACCELERATOR,
                version='1.0.0',
                status=DriverStatus.NOT_INSTALLED,
                description='Intel Neural Processing Unit driver',
                hardware_ids=['8086:7d1c'],
                dependencies=['intel_npu'],
                loaded_modules=[],
                performance_metrics={},
                last_updated=0
            ),
            
            # Network Drivers
            'mlx5_core': DriverInfo(
                name='mlx5_core',
                driver_type=DriverType.NETWORK,
                version='5.0.0',
                status=DriverStatus.NOT_INSTALLED,
                description='Mellanox ConnectX network driver',
                hardware_ids=['15b3:'],
                dependencies=['mlx5_core'],
                loaded_modules=[],
                performance_metrics={},
                last_updated=0
            ),
            
            # Storage Drivers
            'nvme': DriverInfo(
                name='nvme',
                driver_type=DriverType.STORAGE,
                version='1.0.0',
                status=DriverStatus.NOT_INSTALLED,
                description='NVMe storage driver',
                hardware_ids=['144d:', '1e0f:'],
                dependencies=['nvme'],
                loaded_modules=[],
                performance_metrics={},
                last_updated=0
            ),
            
            # Security Drivers
            'tpm': DriverInfo(
                name='tpm',
                driver_type=DriverType.SECURITY,
                version='0.8.0',
                status=DriverStatus.NOT_INSTALLED,
                description='TPM security chip driver',
                hardware_ids=[''],
                dependencies=['tpm_tis', 'tpm_crb'],
                loaded_modules=[],
                performance_metrics={},
                last_updated=0
            )
        }
        
        self.logger.info(f"Initialized driver registry with {len(self.drivers)} drivers")
    
    def scan_hardware(self) -> Dict[str, List[str]]:
        """Scan system for hardware and map to required drivers"""
        self.logger.info("Scanning system hardware...")
        
        hardware_map = {
            driver_type.value: [] for driver_type in DriverType
        }
        
        try:
            # Scan PCI devices
            result = subprocess.run(['lspci', '-nn'], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                self._parse_pci_devices(result.stdout, hardware_map)
            
            # Scan USB devices
            result = subprocess.run(['lsusb'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self._parse_usb_devices(result.stdout, hardware_map)
            
            # Scan for special devices
            self._scan_special_devices(hardware_map)
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
            self.logger.warning(f"Hardware scan incomplete: {e}")
        
        self.hardware_registry = hardware_map
        return hardware_map
    
    def _parse_pci_devices(self, lspci_output: str, hardware_map: Dict):
        """Parse PCI devices from lspci output"""
        for line in lspci_output.split('\n'):
            if not line.strip():
                continue
                
            # Extract vendor ID
            if '[' in line and ']:' in line:
                vendor_id = line.split('[')[1].split(']')[0]
                
                # Check against driver hardware IDs
                for driver_name, driver_info in self.drivers.items():
                    for hw_id in driver_info.hardware_ids:
                        if vendor_id.startswith(hw_id):
                            hardware_map[driver_info.driver_type.value].append({
                                'vendor_id': vendor_id,
                                'description': line.split(':')[1].strip() if ':' in line else 'Unknown',
                                'driver': driver_name
                            })
    
    def _parse_usb_devices(self, lsusb_output: str, hardware_map: Dict):
        """Parse USB devices from lsusb output"""
        for line in lsusb_output.split('\n'):
            if not line.strip():
                continue
            
            # Extract vendor ID from USB output
            if 'ID ' in line:
                vendor_id = line.split('ID ')[1].split(':')[0]
                
                # Check for USB drivers
                for driver_name, driver_info in self.drivers.items():
                    if driver_info.driver_type == DriverType.USB:
                        if vendor_id in driver_info.hardware_ids or not driver_info.hardware_ids:
                            hardware_map[driver_info.driver_type.value].append({
                                'vendor_id': vendor_id,
                                'description': line.split('ID ')[1].split('(')[0].strip() if '(' in line else 'Unknown',
                                'driver': driver_name
                            })
    
    def _scan_special_devices(self, hardware_map: Dict):
        """Scan for special devices not detected by PCI/USB"""
        
        # Check for TPM
        if os.path.exists('/dev/tpm0') or os.path.exists('/dev/tpmrm0'):
            hardware_map[DriverType.SECURITY.value].append({
                'device': 'tpm',
                'description': 'TPM Security Chip',
                'driver': 'tpm'
            })
        
        # Check for NPU (Neural Processing Unit)
        if os.path.exists('/dev/accel/accel0'):
            hardware_map[DriverType.AI_ACCELERATOR.value].append({
                'device': 'npu',
                'description': 'Neural Processing Unit',
                'driver': 'intel_npu'
            })
    
    def install_required_drivers(self) -> Dict[str, bool]:
        """Install all required drivers based on detected hardware"""
        self.logger.info("Installing required drivers...")
        
        # First scan hardware
        hardware_map = self.scan_hardware()
        
        installation_results = {}
        
        # Install drivers for detected hardware
        for driver_type, devices in hardware_map.items():
            if not devices:
                continue
                
            for device in devices:
                driver_name = device.get('driver')
                if driver_name and driver_name in self.drivers:
                    success = self.install_driver(driver_name)
                    installation_results[driver_name] = success
        
        # Install AI GPU driver if available
        try:
            from .ai_gpu_driver import AIGPUDriver
            ai_gpu = AIGPUDriver()
            ai_gpu.detect_gpus()
            ai_gpu.install_drivers()
            self.logger.info("AI GPU driver installation completed")
        except ImportError:
            self.logger.warning("AI GPU driver not available")
        
        return installation_results
    
    def install_driver(self, driver_name: str) -> bool:
        """Install a specific driver"""
        if driver_name not in self.drivers:
            self.logger.error(f"Unknown driver: {driver_name}")
            return False
        
        driver_info = self.drivers[driver_name]
        self.logger.info(f"Installing driver: {driver_name}")
        
        try:
            # Update status
            driver_info.status = DriverStatus.INSTALLED
            driver_info.last_updated = time.time()
            
            # Load kernel modules
            for module in driver_info.dependencies:
                try:
                    subprocess.run(['modprobe', module], check=True, timeout=10)
                    driver_info.loaded_modules.append(module)
                    self.logger.info(f"Loaded module: {module}")
                except subprocess.CalledProcessError as e:
                    self.logger.warning(f"Failed to load module {module}: {e}")
            
            # Additional driver-specific installation steps
            if driver_name == 'nvidia':
                self._install_nvidia_extra(driver_info)
            elif driver_name == 'amdgpu':
                self._install_amd_extra(driver_info)
            elif driver_name == 'mlx5_core':
                self._install_mellanox_extra(driver_info)
            
            driver_info.status = DriverStatus.ACTIVE
            self.logger.info(f"Driver {driver_name} installed successfully")
            return True
            
        except Exception as e:
            driver_info.status = DriverStatus.ERROR
            self.logger.error(f"Failed to install driver {driver_name}: {e}")
            return False
    
    def _install_nvidia_extra(self, driver_info: DriverInfo):
        """Additional NVIDIA driver setup"""
        # Set up GPU persistence mode
        try:
            subprocess.run(['nvidia-smi', '-pm', '1'], check=True, timeout=10)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Create device nodes
        try:
            subprocess.run(['mknod', '-m', '666', '/dev/nvidia0', 'c', '195', '0'], check=True)
            subprocess.run(['mknod', '-m', '666', '/dev/nvidiactl', 'c', '195', '255'], check=True)
        except subprocess.CalledProcessError:
            pass
    
    def _install_amd_extra(self, driver_info: DriverInfo):
        """Additional AMD driver setup"""
        # Set up ROCm permissions
        try:
            subprocess.run(['usermod', '-a', '-G', 'render', 'aurora'], check=True)
        except subprocess.CalledProcessError:
            pass
        
        # Enable amdgpu driver for all cards
        try:
            with open('/etc/modprobe.d/amdgpu.conf', 'w') as f:
                f.write('options amdgpu si_support=1\n')
                f.write('options amdgpu cik_support=1\n')
        except IOError:
            pass
    
    def _install_mellanox_extra(self, driver_info: DriverInfo):
        """Additional Mellanox driver setup"""
        # Enable SR-IOV if available
        try:
            subprocess.run(['echo', '8', '>', '/sys/class/infiniband/mlx5_0/device/sriov_numvfs'], 
                         shell=True, check=True)
        except (subprocess.CalledProcessError, IOError):
            pass

def main():
    """Main function for testing the driver manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Aurora OS Hardware Driver Manager')
    parser.add_argument('--scan', action='store_true', help='Scan for hardware')
    parser.add_argument('--install', action='store_true', help='Install required drivers')
    parser.add_argument('--status', action='store_true', help='Show driver status')
    parser.add_argument('--optimize', action='store_true', help='Optimize for AI workloads')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    manager = HardwareDriverManager()
    
    if args.scan:
        hardware = manager.scan_hardware()
        print(json.dumps(hardware, indent=2))
    
    if args.install:
        results = manager.install_required_drivers()
        print(f"Installation results: {results}")
    
    if args.status:
        status = manager.get_driver_status()
        print(json.dumps(status, indent=2))
    
    if args.optimize:
        success = manager.optimize_for_ai()
        print(f"Optimization: {'Success' if success else 'Failed'}")

if __name__ == '__main__':
    main()