"""
Aurora OS - Automatic Driver Manager
Automatically detects hardware and installs appropriate drivers
Windows-like driver detection and installation system
"""

import os
import sys
import json
import asyncio
import subprocess
import threading
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import logging
from datetime import datetime
import hashlib

try:
    import pci
    import usb.core
    HARDWARE_DETECTION_AVAILABLE = True
except ImportError:
    HARDWARE_DETECTION_AVAILABLE = False

try:
    import dbus
    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False

@dataclass
class HardwareDevice:
    """Hardware device information"""
    device_id: str
    vendor_id: str
    device_name: str
    vendor_name: str
    device_class: str
    driver_status: str  # 'installed', 'missing', 'outdated', 'generic'
    current_driver: Optional[str] = None
    recommended_driver: Optional[str] = None
    available_drivers: List[str] = field(default_factory=list)
    hardware_details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DriverPackage:
    """Driver package information"""
    package_name: str
    version: str
    description: str
    supported_devices: List[str]
    installation_commands: List[str]
    dependencies: List[str] = field(default_factory=list)
    post_install_actions: List[str] = field(default_factory=list)
    isproprietary: bool = False
    repository: str = "main"

class DriverManager:
    """
    Automatic driver detection and installation manager
    Windows-like hardware support for Aurora OS
    """
    
    def __init__(self):
        self.logger = logging.getLogger("Aurora.DriverManager")
        self.devices: Dict[str, HardwareDevice] = {}
        self.driver_database = {}
        self.scanning = False
        
        self.logger = logging.getLogger("Aurora.DriverManager")
        self._setup_logging()
        
        # Initialize hardware detection
        self._init_hardware_detection()
        
        # Load driver database
        self._load_driver_database()
        
        # Setup monitoring
        self._setup_hardware_monitoring()
    
    def _setup_logging(self):
        """Setup logging"""
        log_dir = Path("/var/log/aurora")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(log_dir / "driver_manager.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _init_hardware_detection(self):
        """Initialize hardware detection methods"""
        self.detection_methods = {
            'pci': self._detect_pci_devices,
            'usb': self._detect_usb_devices,
            'network': self._detect_network_devices,
            'audio': self._detect_audio_devices,
            'graphics': self._detect_graphics_devices,
            'storage': self._detect_storage_devices,
            'input': self._detect_input_devices,
        }
        
        if not HARDWARE_DETECTION_AVAILABLE:
            self.logger.warning("Hardware detection libraries not available")
    
    def _load_driver_database(self):
        """Load comprehensive driver database"""
        self.driver_database = {
            # Graphics drivers
            'nvidia': {
                'vendor_pattern': ['10de', '12d2'],
                'drivers': [
                    DriverPackage(
                        package_name="nvidia-driver-535",
                        version="535.154.05",
                        description="NVIDIA proprietary driver",
                        supported_devices=["10de:*"],
                        installation_commands=[
                            "apt install -y nvidia-driver-535",
                            "modprobe nvidia"
                        ],
                        dependencies=["linux-headers-$(uname -r)", "dkms"],
                        isproprietary=True,
                        repository="non-free"
                    ),
                    DriverPackage(
                        package_name="nouveau",
                        version="builtin",
                        description="NVIDIA open source driver",
                        supported_devices=["10de:*"],
                        installation_commands=["modprobe nouveau"],
                        isproprietary=False
                    )
                ]
            },
            
            # AMD graphics
            'amd': {
                'vendor_pattern': ['1002', '1022'],
                'drivers': [
                    DriverPackage(
                        package_name="amdgpu",
                        version="builtin",
                        description="AMD open source driver",
                        supported_devices=["1002:*"],
                        installation_commands=["modprobe amdgpu"],
                        isproprietary=False
                    )
                ]
            },
            
            # Intel graphics
            'intel': {
                'vendor_pattern': ['8086'],
                'drivers': [
                    DriverPackage(
                        package_name="intel-media-driver",
                        version="latest",
                        description="Intel media driver",
                        supported_devices=["8086:*"],
                        installation_commands=[
                            "apt install -y intel-media-driver",
                            "modprobe i915"
                        ],
                        isproprietary=False
                    )
                ]
            },
            
            # WiFi drivers
            'wifi': {
                'vendor_pattern': ['14e4', '10ec', '168c', '0bda'],
                'drivers': [
                    DriverPackage(
                        package_name="broadcom-sta-dkms",
                        version="latest",
                        description="Broadcom WiFi driver",
                        supported_devices=["14e4:*"],
                        installation_commands=[
                            "apt install -y broadcom-sta-dkms",
                            "modprobe wl"
                        ],
                        dependencies=["linux-headers-$(uname -r)", "dkms"],
                        isproprietary=True,
                        repository="non-free"
                    ),
                    DriverPackage(
                        package_name="firmware-linux-nonfree",
                        version="latest",
                        description="WiFi firmware",
                        supported_devices=["*"],
                        installation_commands=[
                            "apt install -y firmware-linux-nonfree"
                        ],
                        isproprietary=True,
                        repository="non-free"
                    )
                ]
            },
            
            # Audio drivers
            'audio': {
                'vendor_pattern': ['8086', '10de', '1002'],
                'drivers': [
                    DriverPackage(
                        package_name="alsa-utils",
                        version="latest",
                        description="ALSA audio utilities",
                        supported_devices=["*"],
                        installation_commands=[
                            "apt install -y alsa-utils",
                            "alsactl init"
                        ],
                        isproprietary=False
                    ),
                    DriverPackage(
                        package_name="pulseaudio",
                        version="latest",
                        description="PulseAudio sound server",
                        supported_devices=["*"],
                        installation_commands=[
                            "apt install -y pulseaudio pulseaudio-utils",
                            "systemctl --user enable pulseaudio"
                        ],
                        isproprietary=False
                    )
                ]
            },
            
            # Network drivers
            'network': {
                'vendor_pattern': ['10ec', '8086', '14e4'],
                'drivers': [
                    DriverPackage(
                        package_name="ethtool",
                        version="latest",
                        description="Network utility",
                        supported_devices=["*"],
                        installation_commands=["apt install -y ethtool"],
                        isproprietary=False
                    )
                ]
            },
            
            # Printer drivers
            'printer': {
                'vendor_pattern': ['03f0', '04b8', '04a9'],
                'drivers': [
                    DriverPackage(
                        package_name="cups",
                        version="latest",
                        description="CUPS printing system",
                        supported_devices=["*"],
                        installation_commands=[
                            "apt install -y cups",
                            "systemctl enable cups"
                        ],
                        isproprietary=False
                    ),
                    DriverPackage(
                        package_name="hplip",
                        version="latest",
                        description="HP Linux imaging and printing",
                        supported_devices=["03f0:*"],
                        installation_commands=[
                            "apt install -y hplip",
                            "hp-setup"
                        ],
                        dependencies=["cups"],
                        isproprietary=False
                    )
                ]
            }
        }
        
        self.logger.info("Driver database loaded")
    
    async def scan_hardware(self) -> List[HardwareDevice]:
        """Scan for all hardware devices"""
        self.scanning = True
        self.logger.info("Starting hardware scan")
        
        devices = []
        
        # Run all detection methods
        for device_type, detector in self.detection_methods.items():
            try:
                type_devices = await detector()
                devices.extend(type_devices)
                self.logger.info(f"Found {len(type_devices)} {device_type} devices")
            except Exception as e:
                self.logger.error(f"Error detecting {device_type}: {e}")
        
        # Update device registry
        for device in devices:
            self.devices[device.device_id] = device
        
        # Analyze driver status for each device
        await self._analyze_driver_status()
        
        self.scanning = False
        self.logger.info(f"Hardware scan complete. Found {len(devices)} devices")
        
        return devices
    
    async def _detect_pci_devices(self) -> List[HardwareDevice]:
        """Detect PCI devices"""
        devices = []
        
        try:
            # Use lspci to get PCI devices
            result = await self._run_command("lspci -vnn")
            
            for line in result.split('\n'):
                if 'Class' in line and 'Vender' in line:
                    device = self._parse_pci_device(line)
                    if device:
                        devices.append(device)
        
        except Exception as e:
            self.logger.error(f"PCI detection failed: {e}")
        
        return devices
    
    async def _detect_usb_devices(self) -> List[HardwareDevice]:
        """Detect USB devices"""
        devices = []
        
        try:
            # Use lsusb to get USB devices
            result = await self._run_command("lsusb -v")
            
            for line in result.split('\n'):
                if 'idVendor' in line and 'idProduct' in line:
                    device = self._parse_usb_device(line)
                    if device:
                        devices.append(device)
        
        except Exception as e:
            self.logger.error(f"USB detection failed: {e}")
        
        return devices
    
    async def _detect_network_devices(self) -> List[HardwareDevice]:
        """Detect network devices"""
        devices = []
        
        try:
            # Use ip link to get network devices
            result = await self._run_command("ip link show")
            
            for line in result.split('\n'):
                if ': ' in line and 'state' in line:
                    device = self._parse_network_device(line)
                    if device:
                        devices.append(device)
        
        except Exception as e:
            self.logger.error(f"Network detection failed: {e}")
        
        return devices
    
    async def _detect_audio_devices(self) -> List[HardwareDevice]:
        """Detect audio devices"""
        devices = []
        
        try:
            # Use aplay to get audio devices
            result = await self._run_command("aplay -l")
            
            for line in result.split('\n'):
                if 'card' in line and 'device' in line:
                    device = self._parse_audio_device(line)
                    if device:
                        devices.append(device)
        
        except Exception as e:
            self.logger.error(f"Audio detection failed: {e}")
        
        return devices
    
    async def _detect_graphics_devices(self) -> List[HardwareDevice]:
        """Detect graphics devices"""
        devices = []
        
        try:
            # Use lspci specifically for graphics
            result = await self._run_command("lspci -vnn | grep -i vga")
            
            for line in result.split('\n'):
                if 'VGA' in line:
                    device = self._parse_graphics_device(line)
                    if device:
                        devices.append(device)
        
        except Exception as e:
            self.logger.error(f"Graphics detection failed: {e}")
        
        return devices
    
    async def _detect_storage_devices(self) -> List[HardwareDevice]:
        """Detect storage devices"""
        devices = []
        
        try:
            # Use lsblk to get storage devices
            result = await self._run_command("lsblk -d -o NAME,MODEL,VENDOR,SIZE")
            
            for line in result.split('\n')[1:]:  # Skip header
                device = self._parse_storage_device(line)
                if device:
                    devices.append(device)
        
        except Exception as e:
            self.logger.error(f"Storage detection failed: {e}")
        
        return devices
    
    async def _detect_input_devices(self) -> List[HardwareDevice]:
        """Detect input devices"""
        devices = []
        
        try:
            # Use evtest to get input devices
            result = await self._run_command("cat /proc/bus/input/devices")
            
            device_info = {}
            for line in result.split('\n'):
                if line.startswith('I: Bus='):
                    device_info = {}
                elif line.startswith('N: Name='):
                    device_info['name'] = line.split('=')[1].strip('"')
                elif line.startswith('P: Phys='):
                    device_info['phys'] = line.split('=')[1]
                elif line.startswith('S: Sysfs='):
                    device_info['sysfs'] = line.split('=')[1]
                elif line.startswith('U: Uniq='):
                    device_info['uniq'] = line.split('=')[1]
                elif line.startswith('H: Handlers='):
                    device_info['handlers'] = line.split('=')[1].strip()
                    
                    # Create device if we have name
                    if 'name' in device_info:
                        hardware_device = HardwareDevice(
                            device_id=f"input_{hash(device_info['name'])}",
                            vendor_id="input",
                            device_name=device_info['name'],
                            vendor_name="Generic",
                            device_class="input",
                            driver_status="installed",
                            current_driver="evdev",
                            hardware_details=device_info
                        )
                        devices.append(hardware_device)
        
        except Exception as e:
            self.logger.error(f"Input detection failed: {e}")
        
        return devices
    
    def _parse_pci_device(self, line: str) -> Optional[HardwareDevice]:
        """Parse PCI device information"""
        try:
            # Extract PCI address, vendor, device ID, and class
            match = re.search(r'([0-9a-f]{2}:[0-9a-f]{2}\.[0-9a-f]) .*?([0-9a-f]{4}):([0-9a-f]{4})', line)
            if match:
                address, vendor_id, device_id = match.groups()
                
                # Get device name from class or description
                device_name = "Unknown PCI Device"
                if 'VGA' in line:
                    device_name = "Graphics Card"
                elif 'Audio' in line:
                    device_name = "Audio Device"
                elif 'Network' in line or 'Ethernet' in line:
                    device_name = "Network Adapter"
                elif 'USB' in line:
                    device_name = "USB Controller"
                elif 'SATA' in line or 'Storage' in line:
                    device_name = "Storage Controller"
                
                return HardwareDevice(
                    device_id=f"pci_{address}",
                    vendor_id=vendor_id,
                    device_name=device_name,
                    vendor_name=self._get_vendor_name(vendor_id),
                    device_class=self._get_device_class(vendor_id, device_id),
                    driver_status="unknown",
                    hardware_details={'pci_address': address, 'device_id': device_id}
                )
        except:
            pass
        
        return None
    
    def _parse_usb_device(self, line: str) -> Optional[HardwareDevice]:
        """Parse USB device information"""
        try:
            # Extract vendor and product ID
            match = re.search(r'([0-9a-f]{4}):([0-9a-f]{4})', line)
            if match:
                vendor_id, product_id = match.groups()
                
                return HardwareDevice(
                    device_id=f"usb_{vendor_id}_{product_id}",
                    vendor_id=vendor_id,
                    device_name="USB Device",
                    vendor_name=self._get_vendor_name(vendor_id),
                    device_class="usb",
                    driver_status="unknown",
                    hardware_details={'product_id': product_id}
                )
        except:
            pass
        
        return None
    
    def _parse_network_device(self, line: str) -> Optional[HardwareDevice]:
        """Parse network device information"""
        try:
            # Extract interface name
            match = re.search(r'^\d+: (\w+):', line)
            if match:
                interface = match.groups()[0]
                
                return HardwareDevice(
                    device_id=f"net_{interface}",
                    vendor_id="network",
                    device_name=f"Network Interface ({interface})",
                    vendor_name="Generic",
                    device_class="network",
                    driver_status="installed",
                    current_driver=interface,
                    hardware_details={'interface': interface}
                )
        except:
            pass
        
        return None
    
    def _parse_audio_device(self, line: str) -> Optional[HardwareDevice]:
        """Parse audio device information"""
        try:
            # Extract card and device info
            match = re.search(r'card (\d+): .*? \[(.*?)\], device (\d+): .*? \[(.*?)\]', line)
            if match:
                card_num, card_name, device_num, device_name = match.groups()
                
                return HardwareDevice(
                    device_id=f"audio_{card_num}_{device_num}",
                    vendor_id="audio",
                    device_name=f"{card_name} - {device_name}",
                    vendor_name=card_name,
                    device_class="audio",
                    driver_status="installed",
                    current_driver="snd_hda_intel",
                    hardware_details={'card': card_num, 'device': device_num}
                )
        except:
            pass
        
        return None
    
    def _parse_graphics_device(self, line: str) -> Optional[HardwareDevice]:
        """Parse graphics device information"""
        try:
            # Extract vendor and device IDs
            match = re.search(r'([0-9a-f]{4}):([0-9a-f]{4})', line)
            if match:
                vendor_id, device_id = match.groups()
                
                # Determine vendor name
                vendor_name = "Unknown"
                if vendor_id == '10de':
                    vendor_name = "NVIDIA"
                elif vendor_id == '1002':
                    vendor_name = "AMD"
                elif vendor_id == '8086':
                    vendor_name = "Intel"
                
                return HardwareDevice(
                    device_id=f"gpu_{vendor_id}_{device_id}",
                    vendor_id=vendor_id,
                    device_name=f"{vendor_name} Graphics Card",
                    vendor_name=vendor_name,
                    device_class="graphics",
                    driver_status="unknown",
                    hardware_details={'device_id': device_id}
                )
        except:
            pass
        
        return None
    
    def _parse_storage_device(self, line: str) -> Optional[HardwareDevice]:
        """Parse storage device information"""
        try:
            parts = line.split()
            if len(parts) >= 4:
                name = parts[0]
                model = parts[1] if parts[1] != '' else "Unknown"
                vendor = parts[2] if parts[2] != '' else "Unknown"
                size = parts[3] if len(parts) > 3 else ""
                
                return HardwareDevice(
                    device_id=f"storage_{name}",
                    vendor_id="storage",
                    device_name=f"{vendor} {model} ({size})",
                    vendor_name=vendor,
                    device_class="storage",
                    driver_status="installed",
                    current_driver="block",
                    hardware_details={'device': name, 'size': size}
                )
        except:
            pass
        
        return None
    
    def _get_vendor_name(self, vendor_id: str) -> str:
        """Get vendor name from vendor ID"""
        vendor_names = {
            '10de': 'NVIDIA',
            '1002': 'AMD',
            '8086': 'Intel',
            '14e4': 'Broadcom',
            '10ec': 'Realtek',
            '168c': 'Atheros',
            '0bda': 'Realtek',
            '03f0': 'HP',
            '04b8': 'Epson',
            '04a9': 'Canon',
        }
        return vendor_names.get(vendor_id, 'Unknown')
    
    def _get_device_class(self, vendor_id: str, device_id: str) -> str:
        """Get device class based on vendor and device IDs"""
        if vendor_id in ['10de', '1002', '8086']:
            return 'graphics'
        elif vendor_id in ['14e4', '10ec', '168c', '0bda']:
            return 'network'
        elif vendor_id == '03f0':
            return 'printer'
        else:
            return 'unknown'
    
    async def _analyze_driver_status(self):
        """Analyze driver status for all detected devices"""
        for device_id, device in self.devices.items():
            # Check if driver is loaded
            current_driver = await self._get_current_driver(device)
            device.current_driver = current_driver
            
            # Find available drivers
            available_drivers = await self._find_available_drivers(device)
            device.available_drivers = available_drivers
            
            # Determine status
            if current_driver and current_driver != "unknown":
                device.driver_status = "installed"
            elif available_drivers:
                device.driver_status = "missing"
            else:
                device.driver_status = "generic"
            
            # Recommend best driver
            device.recommended_driver = await self._recommend_driver(device)
    
    async def _get_current_driver(self, device: HardwareDevice) -> Optional[str]:
        """Get currently loaded driver for device"""
        try:
            if device.device_class == "graphics":
                # Check graphics driver
                result = await self._run_command("lsmod | grep -E '(nvidia|amdgpu|i915|nouveau)'")
                if result.strip():
                    return result.split()[0]
            
            elif device.device_class == "network":
                # Check network driver
                if device.hardware_details.get('interface'):
                    interface = device.hardware_details['interface']
                    result = await self._run_command(f"ethtool -i {interface} | grep driver")
                    if result and 'driver:' in result:
                        return result.split(':')[1].strip()
            
            elif device.device_class == "audio":
                # Audio is usually handled by snd_hda_intel
                return "snd_hda_intel"
            
            elif device.device_class == "storage":
                # Block devices are handled by block driver
                return "block"
        
        except Exception as e:
            self.logger.error(f"Error checking driver for {device.device_id}: {e}")
        
        return "unknown"
    
    async def _find_available_drivers(self, device: HardwareDevice) -> List[str]:
        """Find available drivers for a device"""
        available_drivers = []
        
        # Check driver database
        for category, data in self.driver_database.items():
            if device.vendor_id in data.get('vendor_pattern', []):
                for driver_package in data.get('drivers', []):
                    available_drivers.append(driver_package.package_name)
        
        # Check if generic drivers are available
        if not available_drivers:
            available_drivers = ["generic"]
        
        return available_drivers
    
    async def _recommend_driver(self, device: HardwareDevice) -> Optional[str]:
        """Recommend the best driver for a device"""
        if not device.available_drivers:
            return None
        
        # Prefer proprietary drivers for graphics
        if device.device_class == "graphics":
            if "nvidia-driver" in str(device.available_drivers):
                return "nvidia-driver"
            elif "amdgpu" in device.available_drivers:
                return "amdgpu"
            elif "intel-media-driver" in device.available_drivers:
                return "intel-media-driver"
        
        # For WiFi, prefer proprietary drivers
        elif device.device_class == "network":
            if "broadcom-sta-dkms" in device.available_drivers:
                return "broadcom-sta-dkms"
        
        # For other devices, prefer first available
        return device.available_drivers[0] if device.available_drivers else None
    
    async def install_driver(self, device_id: str, driver_package: str = None) -> bool:
        """Install driver for a device"""
        device = self.devices.get(device_id)
        if not device:
            self.logger.error(f"Device {device_id} not found")
            return False
        
        if driver_package is None:
            driver_package = device.recommended_driver
        
        if not driver_package:
            self.logger.error(f"No driver package specified for {device_id}")
            return False
        
        try:
            self.logger.info(f"Installing driver {driver_package} for {device.device_name}")
            
            # Find the driver package details
            driver_info = None
            for category, data in self.driver_database.values():
                for driver in data.get('drivers', []):
                    if driver.package_name == driver_package:
                        driver_info = driver
                        break
            
            if not driver_info:
                self.logger.error(f"Driver package {driver_package} not found in database")
                return False
            
            # Enable non-free repositories if needed
            if driver_info.isproprietary:
                await self._enable_non_free_repos()
            
            # Install dependencies
            for dep in driver_info.dependencies:
                await self._run_command(f"apt install -y {dep}")
            
            # Install the driver
            for command in driver_info.installation_commands:
                result = await self._run_command(command)
                if result and "error" in result.lower():
                    self.logger.error(f"Driver installation failed: {result}")
                    return False
            
            # Run post-install actions
            for action in driver_info.post_install_actions:
                await self._run_command(action)
            
            # Update device status
            await self._analyze_driver_status()
            
            self.logger.info(f"Driver {driver_package} installed successfully")
            return True
        
        except Exception as e:
            self.logger.error(f"Error installing driver: {e}")
            return False
    
    async def _enable_non_free_repos(self):
        """Enable non-free repositories"""
        try:
            # Add non-free and contrib to sources
            await self._run_command("add-apt-repository non-free")
            await self._run_command("add-apt-repository contrib")
            await self._run_command("apt update")
        except Exception as e:
            self.logger.error(f"Error enabling non-free repos: {e}")
    
    async def _run_command(self, command: str, timeout: int = 30) -> str:
        """Run system command asynchronously"""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            
            if process.returncode != 0:
                return stderr.decode().strip()
            
            return stdout.decode().strip()
        
        except asyncio.TimeoutError:
            raise RuntimeError(f"Command timed out: {command}")
    
    def _setup_hardware_monitoring(self):
        """Setup hardware change monitoring"""
        # Start background monitoring thread
        def monitor_changes():
            while True:
                try:
                    # Monitor /dev for changes
                    self._monitor_device_changes()
                    asyncio.sleep(10)  # Check every 10 seconds
                except Exception as e:
                    self.logger.error(f"Hardware monitoring error: {e}")
                    asyncio.sleep(30)
        
        threading.Thread(target=monitor_changes, daemon=True).start()
    
    def _monitor_device_changes(self):
        """Monitor for hardware changes"""
        # This would typically use udev or D-Bus to monitor hardware changes
        # For now, we'll periodically scan for changes
        pass
    
    async def auto_install_drivers(self) -> Dict[str, bool]:
        """Automatically install drivers for all devices"""
        results = {}
        
        await self.scan_hardware()
        
        for device_id, device in self.devices.items():
            if device.driver_status == "missing" and device.recommended_driver:
                success = await self.install_driver(device_id, device.recommended_driver)
                results[device_id] = success
        
        return results
    
    def get_devices_by_status(self, status: str) -> List[HardwareDevice]:
        """Get devices filtered by status"""
        return [device for device in self.devices.values() if device.driver_status == status]
    
    def get_device_by_id(self, device_id: str) -> Optional[HardwareDevice]:
        """Get device by ID"""
        return self.devices.get(device_id)
    
    def get_all_devices(self) -> List[HardwareDevice]:
        """Get all detected devices"""
        return list(self.devices.values())

# Global driver manager instance
_driver_manager = None

def get_driver_manager() -> DriverManager:
    """Get global driver manager instance"""
    global _driver_manager
    if _driver_manager is None:
        _driver_manager = DriverManager()
    return _driver_manager

async def initialize_driver_system():
    """Initialize the driver management system"""
    manager = get_driver_manager()
    devices = await manager.scan_hardware()
    
    # Auto-install missing drivers
    await manager.auto_install_drivers()
    
    return manager, devices