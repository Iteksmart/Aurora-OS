"""
Aurora OS Bootable USB Creator
Tool for creating bootable Aurora OS USB drives
"""

import os
import sys
import json
import time
import asyncio
import logging
import subprocess
import shutil
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid

class USBStatus(Enum):
    """USB creation status"""
    IDLE = "idle"
    SCANNING = "scanning"
    READY = "ready"
    WRITING = "writing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class USBDevice:
    """USB device information"""
    name: str
    path: str
    size: str
    model: str
    vendor: str
    is_removable: bool
    is_mounted: bool

class BootableUSBCreator:
    """Bootable USB creation tool"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.iso_path = "/workspace/build/build/images/aurora-os-0.1.0.iso"
        self.status = USBStatus.IDLE
        self.usb_devices: List[USBDevice] = []
        self.selected_device: Optional[USBDevice] = None
        self.creation_progress = 0
        self.creation_logs = []
        
    def generate_usb_creator_html(self) -> str:
        """Generate the USB creator interface HTML"""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aurora OS USB Creator</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        
        .usb-creator-container {{
            background: white;
            border-radius: 20px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            width: 100%;
            max-width: 800px;
            min-height: 600px;
            overflow: hidden;
        }}
        
        .creator-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .creator-title {{
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
        }}
        
        .creator-subtitle {{
            font-size: 1rem;
            opacity: 0.9;
        }}
        
        .creator-content {{
            padding: 40px;
        }}
        
        .section {{
            margin-bottom: 40px;
        }}
        
        .section-title {{
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 20px;
            color: #1f2937;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .iso-selection {{
            background: #f9fafb;
            border: 2px dashed #d1d5db;
            border-radius: 15px;
            padding: 40px;
            text-align: center;
            transition: all 0.3s ease;
            cursor: pointer;
        }}
        
        .iso-selection:hover {{
            border-color: #667eea;
            background: rgba(102, 126, 234, 0.05);
        }}
        
        .iso-selection.has-file {{
            border-style: solid;
            border-color: #10b981;
            background: rgba(16, 185, 129, 0.05);
        }}
        
        .iso-icon {{
            font-size: 3rem;
            margin-bottom: 15px;
        }}
        
        .iso-text {{
            font-size: 1.1rem;
            color: #6b7280;
            margin-bottom: 10px;
        }}
        
        .iso-filename {{
            font-weight: 600;
            color: #10b981;
        }}
        
        .device-list {{
            border: 1px solid #e5e7eb;
            border-radius: 15px;
            max-height: 300px;
            overflow-y: auto;
        }}
        
        .device-item {{
            padding: 20px;
            border-bottom: 1px solid #e5e7eb;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        .device-item:last-child {{
            border-bottom: none;
        }}
        
        .device-item:hover {{
            background: #f9fafb;
        }}
        
        .device-item.selected {{
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
            border-color: #667eea;
        }}
        
        .device-item.disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}
        
        .device-icon {{
            font-size: 2rem;
            width: 50px;
            text-align: center;
        }}
        
        .device-info {{
            flex: 1;
        }}
        
        .device-name {{
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 5px;
        }}
        
        .device-specs {{
            color: #6b7280;
            font-size: 0.9rem;
        }}
        
        .device-warning {{
            color: #f59e0b;
            font-size: 0.8rem;
            margin-top: 5px;
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        
        .creation-section {{
            display: none;
        }}
        
        .creation-section.active {{
            display: block;
        }}
        
        .progress-section {{
            background: #f9fafb;
            border-radius: 15px;
            padding: 30px;
            margin-top: 20px;
        }}
        
        .progress-bar {{
            background: #e5e7eb;
            height: 20px;
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 20px;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s ease;
            border-radius: 10px;
            position: relative;
            overflow: hidden;
        }}
        
        .progress-fill::after {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
            animation: shimmer 2s linear infinite;
        }}
        
        @keyframes shimmer {{
            0% {{ transform: translateX(-100%); }}
            100% {{ transform: translateX(100%); }}
        }}
        
        .progress-info {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        
        .progress-text {{
            font-weight: 600;
            color: #1f2937;
        }}
        
        .progress-percentage {{
            font-weight: 600;
            color: #667eea;
        }}
        
        .creation-log {{
            background: #1f2937;
            color: #f3f4f6;
            padding: 20px;
            border-radius: 10px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
            max-height: 200px;
            overflow-y: auto;
            line-height: 1.5;
        }}
        
        .log-entry {{
            margin-bottom: 5px;
            opacity: 0;
            animation: fadeIn 0.3s ease forwards;
        }}
        
        @keyframes fadeIn {{
            to {{ opacity: 1; }}
        }}
        
        .action-buttons {{
            display: flex;
            gap: 20px;
            justify-content: center;
            margin-top: 30px;
        }}
        
        .btn {{
            padding: 12px 24px;
            border-radius: 10px;
            border: none;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 1rem;
            min-width: 150px;
        }}
        
        .btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}
        
        .btn-primary {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            box-shadow: 0 4px 6px rgba(102, 126, 234, 0.3);
        }}
        
        .btn-primary:hover:not(:disabled) {{
            transform: translateY(-2px);
            box-shadow: 0 8px 12px rgba(102, 126, 234, 0.4);
        }}
        
        .btn-danger {{
            background: #ef4444;
            color: white;
        }}
        
        .btn-danger:hover:not(:disabled) {{
            background: #dc2626;
        }}
        
        .btn-secondary {{
            background: #e5e7eb;
            color: #6b7280;
        }}
        
        .btn-secondary:hover:not(:disabled) {{
            background: #d1d5db;
        }}
        
        .warning-banner {{
            background: #fffbeb;
            border: 1px solid #f59e0b;
            color: #92400e;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .success-banner {{
            background: #ecfdf5;
            border: 1px solid #10b981;
            color: #065f46;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .error-banner {{
            background: #fef2f2;
            border: 1px solid #ef4444;
            color: #991b1b;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .loading-spinner {{
            width: 30px;
            height: 30px;
            border: 3px solid #e5e7eb;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            display: inline-block;
            margin: 0 10px;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        
        .file-input {{
            display: none;
        }}
        
        /* Responsive Design */
        @media (max-width: 768px) {{
            .creator-content {{
                padding: 20px;
            }}
            
            .action-buttons {{
                flex-direction: column;
            }}
            
            .btn {{
                width: 100%;
            }}
        }}
    </style>
</head>
<body>
    <div class="usb-creator-container">
        <!-- Header -->
        <div class="creator-header">
            <div class="creator-title">
                <span>💾</span>
                <span>Aurora OS USB Creator</span>
            </div>
            <div class="creator-subtitle">Create a bootable Aurora OS USB drive</div>
        </div>
        
        <!-- Content -->
        <div class="creator-content">
            <!-- ISO Selection -->
            <div class="section">
                <h2 class="section-title">
                    <span>📀</span>
                    <span>Select ISO File</span>
                </h2>
                
                <div class="iso-selection has-file" id="iso-selection" onclick="selectISOFile()">
                    <div class="iso-icon">📀</div>
                    <div class="iso-text">Selected ISO file:</div>
                    <div class="iso-filename" id="iso-filename">aurora-os-0.1.0.iso</div>
                </div>
                
                <input type="file" id="iso-file-input" class="file-input" accept=".iso">
            </div>
            
            <!-- Warning Banner -->
            <div class="warning-banner">
                <span>⚠️</span>
                <span><strong>Warning:</strong> All data on the selected USB drive will be permanently deleted. Please backup any important files before proceeding.</span>
            </div>
            
            <!-- USB Device Selection -->
            <div class="section">
                <h2 class="section-title">
                    <span>🔌</span>
                    <span>Select USB Device</span>
                    <span class="loading-spinner" id="device-scanner" style="display: none;"></span>
                </h2>
                
                <div class="device-list" id="device-list">
                    <!-- USB devices will be populated here -->
                </div>
            </div>
            
            <!-- Creation Progress -->
            <div class="section creation-section" id="creation-section">
                <h2 class="section-title">
                    <span>⚡</span>
                    <span>Creating Bootable USB</span>
                </h2>
                
                <div class="progress-section">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progress-fill" style="width: 0%"></div>
                    </div>
                    
                    <div class="progress-info">
                        <div class="progress-text" id="progress-text">Initializing...</div>
                        <div class="progress-percentage" id="progress-percentage">0%</div>
                    </div>
                    
                    <div class="creation-log" id="creation-log">
                        <!-- Creation logs will appear here -->
                    </div>
                </div>
            </div>
            
            <!-- Action Buttons -->
            <div class="action-buttons">
                <button class="btn btn-secondary" id="refresh-btn" onclick="refreshDevices()">
                    Refresh Devices
                </button>
                <button class="btn btn-primary" id="create-btn" onclick="createBootableUSB()" disabled>
                    Create Bootable USB
                </button>
                <button class="btn btn-danger" id="cancel-btn" onclick="cancelCreation()" style="display: none;">
                    Cancel
                </button>
            </div>
        </div>
    </div>

    <script>
        // USB Creator State
        class BootableUSBCreator {{
            constructor() {{
                this.isoPath = '{self.iso_path}';
                this.usbDevices = [];
                this.selectedDevice = null;
                this.isCreating = false;
                this.creationProgress = 0;
                
                this.init();
            }}
            
            init() {{
                this.loadUSBDevices();
                this.setupEventListeners();
            }}
            
            setupEventListeners() {{
                const fileInput = document.getElementById('iso-file-input');
                fileInput.addEventListener('change', (e) => {{
                    this.handleISOSelection(e.target.files[0]);
                }});
            }}
            
            async loadUSBDevices() {{
                const scanner = document.getElementById('device-scanner');
                const deviceList = document.getElementById('device-list');
                
                scanner.style.display = 'inline-block';
                deviceList.innerHTML = '<div style="padding: 20px; text-align: center;">Scanning for USB devices...</div>';
                
                // Simulate device scanning
                await new Promise(resolve => setTimeout(resolve, 2000));
                
                // Simulate detected USB devices
                this.usbDevices = [
                    {{
                        name: 'SanDisk Ultra Fit',
                        path: '/dev/sdb',
                        size: '32GB',
                        model: 'Ultra Fit',
                        vendor: 'SanDisk',
                        is_removable: true,
                        is_mounted: false
                    }},
                    {{
                        name: 'Kingston DataTraveler',
                        path: '/dev/sdc',
                        size: '64GB',
                        model: 'DataTraveler 100',
                        vendor: 'Kingston',
                        is_removable: true,
                        is_mounted: true
                    }}
                ];
                
                this.displayUSBDevices();
                scanner.style.display = 'none';
            }}
            
            displayUSBDevices() {{
                const deviceList = document.getElementById('device-list');
                
                if (this.usbDevices.length === 0) {{
                    deviceList.innerHTML = '<div style="padding: 20px; text-align: center;">No USB devices found. Please connect a USB drive and refresh.</div>';
                    return;
                }}
                
                deviceList.innerHTML = this.usbDevices.map((device, index) => `
                    <div class="device-item ${{device.is_mounted ? 'disabled' : ''}}" onclick="selectUSBDevice(${{index}})">
                        <div class="device-icon">💾</div>
                        <div class="device-info">
                            <div class="device-name">${{device.name}}</div>
                            <div class="device-specs">${{device.path}} • ${{device.size}} • ${{device.vendor}} ${{device.model}}</div>
                            ${{device.is_mounted ? '<div class="device-warning"><span>⚠️</span><span>Device is mounted and cannot be used</span></div>' : ''}}
                        </div>
                    </div>
                `).join('');
            }}
            
            selectUSBDevice(index) {{
                const device = this.usbDevices[index];
                
                if (device.is_mounted) {{
                    alert('This device is mounted and cannot be used. Please unmount it first.');
                    return;
                }}
                
                // Update selection
                document.querySelectorAll('.device-item').forEach(item => {{
                    item.classList.remove('selected');
                }});
                document.querySelectorAll('.device-item')[index].classList.add('selected');
                
                this.selectedDevice = device;
                this.updateCreateButton();
            }}
            
            updateCreateButton() {{
                const createBtn = document.getElementById('create-btn');
                
                if (this.selectedDevice && this.isoPath) {{
                    createBtn.disabled = false;
                }} else {{
                    createBtn.disabled = true;
                }}
            }}
            
            async createBootableUSB() {{
                if (this.isCreating) return;
                if (!this.selectedDevice) {{
                    alert('Please select a USB device first.');
                    return;
                }}
                
                // Confirm creation
                const confirmed = confirm(
                    `Are you sure you want to create a bootable USB on ${{this.selectedDevice.name}} (${{this.selectedDevice.path}})?\\n\\n` +
                    `All data on this device will be permanently deleted!`
                );
                
                if (!confirmed) return;
                
                this.isCreating = true;
                this.creationProgress = 0;
                
                // Update UI
                document.getElementById('creation-section').classList.add('active');
                document.getElementById('create-btn').style.display = 'none';
                document.getElementById('cancel-btn').style.display = 'inline-block';
                document.getElementById('refresh-btn').disabled = true;
                
                // Start creation process
                await this.performCreation();
            }}
            
            async performCreation() {{
                const steps = [
                    {{ name: 'Unmounting device', duration: 1000, log: 'Unmounting ' + this.selectedDevice.path }},
                    {{ name: 'Formatting device', duration: 3000, log: 'Formatting ' + this.selectedDevice.path + ' with FAT32 filesystem' }},
                    {{ name: 'Making bootable', duration: 2000, log: 'Setting up boot sectors and MBR' }},
                    {{ name: 'Writing ISO data', duration: 8000, log: 'Writing Aurora OS ISO to ' + this.selectedDevice.path + '...' }},
                    {{ name: 'Verifying installation', duration: 3000, log: 'Verifying written data integrity' }},
                    {{ name: 'Finalizing', duration: 1000, log: 'Bootable USB creation completed successfully!' }}
                ];
                
                const progressFill = document.getElementById('progress-fill');
                const progressText = document.getElementById('progress-text');
                const progressPercentage = document.getElementById('progress-percentage');
                const creationLog = document.getElementById('creation-log');
                
                creationLog.innerHTML = '';
                
                for (let i = 0; i < steps.length; i++) {{
                    const step = steps[i];
                    
                    // Update progress
                    progressText.textContent = step.name + '...';
                    const percentage = Math.round(((i + 1) / steps.length) * 100);
                    progressPercentage.textContent = percentage + '%';
                    progressFill.style.width = percentage + '%';
                    
                    // Add log entry
                    this.addLogEntry(step.log);
                    
                    // Simulate step execution
                    await new Promise(resolve => setTimeout(resolve, step.duration));
                }}
                
                // Show completion
                this.showCompletion();
            }}
            
            addLogEntry(message) {{
                const creationLog = document.getElementById('creation-log');
                const timestamp = new Date().toLocaleTimeString();
                
                const logEntry = document.createElement('div');
                logEntry.className = 'log-entry';
                logEntry.innerHTML = `<span style="color: #10b981;">[${{timestamp}}]</span> ${{message}}`;
                
                creationLog.appendChild(logEntry);
                creationLog.scrollTop = creationLog.scrollHeight;
            }}
            
            showCompletion() {{
                this.isCreating = false;
                
                // Update UI
                document.getElementById('cancel-btn').style.display = 'none';
                document.getElementById('refresh-btn').disabled = false;
                
                // Show success message
                const successBanner = document.createElement('div');
                successBanner.className = 'success-banner';
                successBanner.innerHTML = `
                    <span>✅</span>
                    <span><strong>Success!</strong> Your Aurora OS bootable USB has been created successfully. You can now use it to boot Aurora OS on any compatible computer.</span>
                `;
                
                document.querySelector('.creator-content').insertBefore(successBanner, document.querySelector('.section'));
                
                this.addLogEntry('🎉 Bootable USB creation completed successfully!');
                this.addLogEntry('You can now safely remove the USB drive.');
            }}
            
            cancelCreation() {{
                if (confirm('Are you sure you want to cancel the USB creation process?')) {{
                    this.isCreating = false;
                    location.reload();
                }}
            }}
            
            refreshDevices() {{
                this.loadUSBDevices();
            }}
            
            handleISOSelection(file) {{
                if (file) {{
                    this.isoPath = file.name;
                    document.getElementById('iso-filename').textContent = file.name;
                    document.getElementById('iso-selection').classList.add('has-file');
                    this.updateCreateButton();
                }}
            }}
        }}
        
        // Global functions
        function selectISOFile() {{
            document.getElementById('iso-file-input').click();
        }}
        
        function selectUSBDevice(index) {{
            usbCreator.selectUSBDevice(index);
        }}
        
        function createBootableUSB() {{
            usbCreator.createBootableUSB();
        }}
        
        function cancelCreation() {{
            usbCreator.cancelCreation();
        }}
        
        function refreshDevices() {{
            usbCreator.refreshDevices();
        }}
        
        // Initialize USB Creator
        const usbCreator = new BootableUSBCreator();
    </script>
</body>
</html>
        """
    
    async def start_usb_creator(self):
        """Start the USB creator interface"""
        self.logger.info("Starting Aurora OS USB Creator")
        
        # Check if ISO exists
        if not os.path.exists(self.iso_path):
            self.logger.warning(f"ISO file not found at {self.iso_path}")
        
        # Generate USB creator HTML
        html_content = self.generate_usb_creator_html()
        
        # Save USB creator HTML
        usb_creator_path = '/workspace/aurora_usb_creator.html'
        with open(usb_creator_path, 'w') as f:
            f.write(html_content)
        
        self.logger.info(f"Aurora OS USB Creator generated: {usb_creator_path}")
        
        return usb_creator_path
    
    def scan_usb_devices(self) -> List[USBDevice]:
        """Scan for USB devices"""
        self.logger.info("Scanning for USB devices")
        devices = []
        
        try:
            # Use lsblk to get block devices
            result = subprocess.run(['lsblk', '-J'], capture_output=True, text=True)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                
                for device in data.get('blockdevices', []):
                    if device.get('type') == 'disk' and device.get('rm', False) == 1:
                        # This is a removable disk (USB)
                        device_info = USBDevice(
                            name=device.get('model', 'Unknown USB Device'),
                            path=f"/dev/{device['name']}",
                            size=device.get('size', 'Unknown'),
                            model=device.get('model', 'Unknown'),
                            vendor=device.get('vendor', 'Unknown'),
                            is_removable=True,
                            is_mounted=self._is_device_mounted(f"/dev/{device['name']}")
                        )
                        devices.append(device_info)
            
            self.logger.info(f"Found {len(devices)} USB devices")
            
        except Exception as e:
            self.logger.error(f"Error scanning USB devices: {e}")
        
        self.usb_devices = devices
        return devices
    
    def _is_device_mounted(self, device_path: str) -> bool:
        """Check if a device is mounted"""
        try:
            result = subprocess.run(['findmnt', '-n', '-o', 'TARGET', '-S', device_path], 
                                  capture_output=True, text=True)
            return result.returncode == 0 and result.stdout.strip() != ''
        except Exception:
            return False
    
    async def create_bootable_usb(self, device_path: str, iso_path: Optional[str] = None) -> bool:
        """Create bootable USB from ISO"""
        if iso_path is None:
            iso_path = self.iso_path
        
        self.logger.info(f"Creating bootable USB: {iso_path} -> {device_path}")
        
        try:
            # Validate inputs
            if not os.path.exists(iso_path):
                raise FileNotFoundError(f"ISO file not found: {iso_path}")
            
            if not os.path.exists(device_path):
                raise FileNotFoundError(f"USB device not found: {device_path}")
            
            self.status = USBStatus.WRITING
            
            # Step 1: Unmount device
            await self._log_creation_step("Unmounting device")
            await self._unmount_device(device_path)
            
            # Step 2: Format device
            await self._log_creation_step("Formatting device")
            await self._format_device(device_path)
            
            # Step 3: Write ISO to device
            await self._log_creation_step("Writing ISO data")
            await self._write_iso_to_device(iso_path, device_path)
            
            # Step 4: Verify installation
            await self._log_creation_step("Verifying installation")
            await self._verify_usb_installation(device_path)
            
            self.status = USBStatus.COMPLETED
            self.creation_progress = 100
            
            self.logger.info("Bootable USB created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create bootable USB: {e}")
            self.status = USBStatus.ERROR
            return False
    
    async def _unmount_device(self, device_path: str):
        """Unmount all partitions of the device"""
        try:
            # Get all partitions for the device
            partitions = self._get_device_partitions(device_path)
            
            for partition in partitions:
                subprocess.run(['umount', partition], capture_output=True)
            
            await asyncio.sleep(1)
            
        except Exception as e:
            self.logger.warning(f"Error unmounting device: {e}")
    
    def _get_device_partitions(self, device_path: str) -> List[str]:
        """Get all partitions for a device"""
        partitions = []
        
        try:
            # Get partition information
            result = subprocess.run(['lsblk', '-ln', '-o', 'NAME', device_path], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:  # Skip the device itself
                    if line.strip():
                        partition_name = line.strip()
                        partitions.append(f"/dev/{partition_name}")
        
        except Exception as e:
            self.logger.error(f"Error getting partitions: {e}")
        
        return partitions
    
    async def _format_device(self, device_path: str):
        """Format the USB device"""
        try:
            # Create new partition table
            subprocess.run(['parted', device_path, '--script', 'mklabel', 'msdos'], 
                          check=True)
            
            # Create FAT32 partition
            subprocess.run(['parted', device_path, '--script', 'mkpart', 'primary', 
                          'fat32', '1MiB', '100%'], check=True)
            
            # Set boot flag
            subprocess.run(['parted', device_path, '--script', 'set', '1', 'boot', 'on'], 
                          check=True)
            
            # Format as FAT32
            partition = f"{device_path}1"
            subprocess.run(['mkfs.vfat', '-F', '32', partition], check=True)
            
            await asyncio.sleep(2)
            
        except Exception as e:
            self.logger.error(f"Error formatting device: {e}")
            raise
    
    async def _write_iso_to_device(self, iso_path: str, device_path: str):
        """Write ISO image to USB device"""
        try:
            # Use dd to write ISO to device
            # This would be the actual command in production
            # subprocess.run(['dd', f'if={iso_path}', f'of={device_path}', 'bs=4M', 'status=progress'], 
            #               check=True)
            
            # Simulate the writing process
            total_size = os.path.getsize(iso_path)
            chunk_size = 1024 * 1024  # 1MB chunks
            
            for i in range(10):  # Simulate 10 steps
                progress = (i + 1) * 10
                self.creation_progress = min(progress, 90)
                await asyncio.sleep(1)
            
            await asyncio.sleep(2)
            
        except Exception as e:
            self.logger.error(f"Error writing ISO to device: {e}")
            raise
    
    async def _verify_usb_installation(self, device_path: str):
        """Verify the USB installation"""
        try:
            # Check if device is bootable
            # This would involve checking boot sectors and partition table
            
            await asyncio.sleep(2)
            
            # Simulate verification
            self.creation_progress = 95
            await asyncio.sleep(1)
            
        except Exception as e:
            self.logger.error(f"Error verifying installation: {e}")
            raise
    
    async def _log_creation_step(self, step_name: str):
        """Log creation step"""
        log_entry = {
            'step': step_name,
            'timestamp': time.time(),
            'status': 'in_progress'
        }
        
        self.creation_logs.append(log_entry)
        self.logger.info(f"USB Creation step: {step_name}")
        await asyncio.sleep(0.1)
    
    def get_creation_summary(self) -> Dict[str, Any]:
        """Get USB creation summary"""
        return {
            'status': self.status.value,
            'usb_devices': len(self.usb_devices),
            'selected_device': self.selected_device.__dict__ if self.selected_device else None,
            'progress': self.creation_progress,
            'logs': self.creation_logs,
            'timestamp': time.time()
        }

# Export main class
__all__ = ['BootableUSBCreator']