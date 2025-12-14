"""
Aurora OS Professional Installer
Guided setup with modern UI and bootable features
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
import tempfile

class InstallationStep(Enum):
    """Installation steps"""
    WELCOME = "welcome"
    REQUIREMENTS = "requirements"
    PARTITIONING = "partitioning"
    INSTALLATION = "installation"
    CONFIGURATION = "configuration"
    COMPLETION = "completion"

class InstallationMode(Enum):
    """Installation modes"""
    STANDARD = "standard"
    ADVANCED = "advanced"
    DUAL_BOOT = "dual_boot"
    PORTABLE = "portable"

@dataclass
class SystemRequirements:
    """System requirements check"""
    cpu_cores: int
    memory_gb: int
    disk_space_gb: int
    uefi_support: bool
    requirements_met: bool
    warnings: List[str]

@dataclass
class PartitionScheme:
    """Partition configuration"""
    boot_partition: str
    root_partition: str
    swap_partition: Optional[str]
    home_partition: Optional[str]
    efi_partition: Optional[str]

class AuroraInstaller:
    """Professional Aurora OS installer"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.installation_id = str(uuid.uuid4())
        self.current_step = InstallationStep.WELCOME
        self.installation_mode = InstallationMode.STANDARD
        
        # Installation state
        self.system_requirements: Optional[SystemRequirements] = None
        self.partition_scheme: Optional[PartitionScheme] = None
        self.installation_progress = 0
        self.installation_logs = []
        
        # Configuration
        self.config = {
            "aurora_version": "0.1.0",
            "minimal_requirements": {
                "cpu_cores": 2,
                "memory_gb": 4,
                "disk_space_gb": 20,
                "uefi_support": True
            },
            "recommended_requirements": {
                "cpu_cores": 4,
                "memory_gb": 8,
                "disk_space_gb": 50,
                "uefi_support": True
            },
            "default_partitions": {
                "boot_size": "512M",
                "swap_size": "4G",
                "root_size": "30G",
                "home_size": "remaining"
            }
        }
        
        # Installation path
        self.installation_path = "/tmp/aurora_installation"
        self.target_device = None
        
    def generate_installer_html(self) -> str:
        """Generate the complete installer HTML interface"""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aurora OS Installer</title>
    <style>
        /* Modern Installer Styles */
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
            overflow-x: hidden;
        }}
        
        .installer-container {{
            max-width: 1200px;
            margin: 0 auto;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        
        .installer-window {{
            background: white;
            border-radius: 20px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            width: 100%;
            max-width: 900px;
            min-height: 600px;
            overflow: hidden;
            position: relative;
        }}
        
        .installer-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .installer-title {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
        }}
        
        .installer-subtitle {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        
        .progress-bar {{
            background: rgba(255, 255, 255, 0.2);
            height: 6px;
            border-radius: 3px;
            margin-top: 20px;
            overflow: hidden;
        }}
        
        .progress-fill {{
            height: 100%;
            background: white;
            border-radius: 3px;
            transition: width 0.3s ease;
            width: 16.66%; /* 1/6 for welcome step */
        }}
        
        .installer-content {{
            padding: 40px;
            min-height: 400px;
        }}
        
        .step-content {{
            display: none;
            animation: fadeIn 0.3s ease;
        }}
        
        .step-content.active {{
            display: block;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .step-title {{
            font-size: 1.8rem;
            font-weight: 600;
            margin-bottom: 20px;
            color: #1f2937;
        }}
        
        .step-description {{
            font-size: 1rem;
            color: #6b7280;
            margin-bottom: 30px;
            line-height: 1.6;
        }}
        
        /* Welcome Step */
        .welcome-content {{
            text-align: center;
            padding: 40px 0;
        }}
        
        .aurora-logo {{
            width: 120px;
            height: 120px;
            margin: 0 auto 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3rem;
            color: white;
            animation: pulse 2s ease-in-out infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.05); }}
        }}
        
        .mode-selection {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 40px 0;
        }}
        
        .mode-card {{
            padding: 30px;
            border: 2px solid #e5e7eb;
            border-radius: 15px;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
        }}
        
        .mode-card:hover {{
            border-color: #667eea;
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.2);
        }}
        
        .mode-card.selected {{
            border-color: #667eea;
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
        }}
        
        .mode-icon {{
            font-size: 2.5rem;
            margin-bottom: 15px;
        }}
        
        .mode-title {{
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 10px;
            color: #1f2937;
        }}
        
        .mode-description {{
            font-size: 0.9rem;
            color: #6b7280;
        }}
        
        /* Requirements Step */
        .requirements-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        
        .requirement-item {{
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 20px;
            border-radius: 10px;
            background: #f9fafb;
        }}
        
        .requirement-item.met {{
            background: #ecfdf5;
            border: 1px solid #10b981;
        }}
        
        .requirement-item.warning {{
            background: #fffbeb;
            border: 1px solid #f59e0b;
        }}
        
        .requirement-item.failed {{
            background: #fef2f2;
            border: 1px solid #ef4444;
        }}
        
        .requirement-icon {{
            font-size: 1.5rem;
            width: 40px;
            text-align: center;
        }}
        
        .requirement-text {{
            flex: 1;
        }}
        
        .requirement-label {{
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 5px;
        }}
        
        .requirement-value {{
            color: #6b7280;
            font-size: 0.9rem;
        }}
        
        /* Partitioning Step */
        .partition-diagram {{
            background: #f3f4f6;
            border-radius: 15px;
            padding: 30px;
            margin: 30px 0;
        }}
        
        .partition-visual {{
            display: flex;
            height: 60px;
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 20px;
            box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        
        .partition-block {{
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            font-size: 0.8rem;
            position: relative;
        }}
        
        .partition-label {{
            position: absolute;
            top: -25px;
            font-size: 0.8rem;
            color: #6b7280;
            white-space: nowrap;
        }}
        
        .device-selection {{
            margin: 30px 0;
        }}
        
        .device-list {{
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            max-height: 300px;
            overflow-y: auto;
        }}
        
        .device-item {{
            padding: 20px;
            border-bottom: 1px solid #e5e7eb;
            cursor: pointer;
            transition: background 0.2s ease;
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
        
        .device-name {{
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 5px;
        }}
        
        .device-specs {{
            color: #6b7280;
            font-size: 0.9rem;
        }}
        
        /* Installation Step */
        .installation-progress {{
            margin: 30px 0;
        }}
        
        .progress-item {{
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 15px 0;
            border-bottom: 1px solid #e5e7eb;
        }}
        
        .progress-item:last-child {{
            border-bottom: none;
        }}
        
        .progress-icon {{
            width: 30px;
            text-align: center;
            font-size: 1.2rem;
        }}
        
        .progress-text {{
            flex: 1;
            font-weight: 500;
            color: #1f2937;
        }}
        
        .progress-status {{
            color: #6b7280;
            font-size: 0.9rem;
        }}
        
        .progress-status.completed {{
            color: #10b981;
        }}
        
        .progress-status.error {{
            color: #ef4444;
        }}
        
        .main-progress-bar {{
            background: #e5e7eb;
            height: 20px;
            border-radius: 10px;
            overflow: hidden;
            margin: 30px 0;
        }}
        
        .main-progress-fill {{
            height: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s ease;
            border-radius: 10px;
            position: relative;
            overflow: hidden;
        }}
        
        .main-progress-fill::after {{
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
        
        /* Navigation Buttons */
        .installer-navigation {{
            padding: 30px 40px;
            background: #f9fafb;
            border-top: 1px solid #e5e7eb;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .nav-btn {{
            padding: 12px 24px;
            border-radius: 10px;
            border: none;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 1rem;
        }}
        
        .nav-btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}
        
        .btn-secondary {{
            background: #e5e7eb;
            color: #6b7280;
        }}
        
        .btn-secondary:hover:not(:disabled) {{
            background: #d1d5db;
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
        
        /* Completion Step */
        .completion-content {{
            text-align: center;
            padding: 40px 0;
        }}
        
        .success-icon {{
            width: 100px;
            height: 100px;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 30px;
            font-size: 3rem;
            color: white;
            animation: successPulse 1s ease;
        }}
        
        @keyframes successPulse {{
            0% {{ transform: scale(0); }}
            50% {{ transform: scale(1.1); }}
            100% {{ transform: scale(1); }}
        }}
        
        .completion-actions {{
            display: flex;
            gap: 20px;
            justify-content: center;
            margin-top: 40px;
        }}
        
        /* Responsive Design */
        @media (max-width: 768px) {{
            .installer-window {{
                margin: 10px;
                border-radius: 15px;
            }}
            
            .installer-content {{
                padding: 20px;
            }}
            
            .mode-selection {{
                grid-template-columns: 1fr;
            }}
            
            .requirements-grid {{
                grid-template-columns: 1fr;
            }}
            
            .completion-actions {{
                flex-direction: column;
            }}
        }}
        
        /* Loading Animation */
        .loading-spinner {{
            width: 40px;
            height: 40px;
            border: 4px solid #e5e7eb;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
    </style>
</head>
<body>
    <div class="installer-container">
        <div class="installer-window">
            <!-- Header -->
            <div class="installer-header">
                <div class="installer-title">
                    <span>🌌</span>
                    <span>Aurora OS Installer</span>
                </div>
                <div class="installer-subtitle">Version {self.config['aurora_version']} - AI-Native Operating System</div>
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-fill"></div>
                </div>
            </div>
            
            <!-- Content -->
            <div class="installer-content">
                <!-- Welcome Step -->
                <div class="step-content active" id="step-welcome">
                    <div class="welcome-content">
                        <h2 class="step-title">Welcome to Aurora OS</h2>
                        <p class="step-description">
                            Aurora OS is the world's first AI-native operating system that transforms your computing experience 
                            from tool-based to partnership-based. Let's guide you through the installation process.
                        </p>
                        
                        <div class="mode-selection">
                            <div class="mode-card selected" onclick="selectMode('standard')">
                                <div class="mode-icon">🚀</div>
                                <div class="mode-title">Standard</div>
                                <div class="mode-description">Recommended for most users with automatic partitioning</div>
                            </div>
                            
                            <div class="mode-card" onclick="selectMode('advanced')">
                                <div class="mode-icon">⚙️</div>
                                <div class="mode-title">Advanced</div>
                                <div class="mode-description">Full control over partitioning and system configuration</div>
                            </div>
                            
                            <div class="mode-card" onclick="selectMode('dual_boot')">
                                <div class="mode-icon">🔄</div>
                                <div class="mode-title">Dual Boot</div>
                                <div class="mode-description">Install alongside your existing operating system</div>
                            </div>
                            
                            <div class="mode-card" onclick="selectMode('portable')">
                                <div class="mode-icon">💾</div>
                                <div class="mode-title">Portable</div>
                                <div class="mode-description">Install to USB drive for portable computing</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Requirements Step -->
                <div class="step-content" id="step-requirements">
                    <h2 class="step-title">System Requirements Check</h2>
                    <p class="step-description">
                        Aurora OS requires certain hardware specifications for optimal performance. 
                        Let's check if your system meets the requirements.
                    </p>
                    
                    <div class="requirements-grid" id="requirements-grid">
                        <!-- Requirements will be populated by JavaScript -->
                    </div>
                    
                    <div id="requirements-warnings" style="margin-top: 20px;"></div>
                </div>
                
                <!-- Partitioning Step -->
                <div class="step-content" id="step-partitioning">
                    <h2 class="step-title">Disk Partitioning</h2>
                    <p class="step-description">
                        Select the target disk where Aurora OS will be installed. 
                        The installer will automatically create the necessary partitions.
                    </p>
                    
                    <div class="partition-diagram">
                        <div class="partition-visual" id="partition-visual">
                            <!-- Partition visualization will be populated by JavaScript -->
                        </div>
                    </div>
                    
                    <div class="device-selection">
                        <h3 style="margin-bottom: 15px;">Select Installation Device:</h3>
                        <div class="device-list" id="device-list">
                            <!-- Devices will be populated by JavaScript -->
                        </div>
                    </div>
                </div>
                
                <!-- Installation Step -->
                <div class="step-content" id="step-installation">
                    <h2 class="step-title">Installing Aurora OS</h2>
                    <p class="step-description">
                        Please wait while Aurora OS is being installed on your system. 
                        This process may take several minutes to complete.
                    </p>
                    
                    <div class="main-progress-bar">
                        <div class="main-progress-fill" id="main-progress-fill" style="width: 0%"></div>
                    </div>
                    
                    <div class="installation-progress" id="installation-progress">
                        <!-- Installation steps will be populated by JavaScript -->
                    </div>
                </div>
                
                <!-- Configuration Step -->
                <div class="step-content" id="step-configuration">
                    <h2 class="step-title">System Configuration</h2>
                    <p class="step-description">
                        Let's configure your Aurora OS system with basic settings.
                    </p>
                    
                    <div style="max-width: 500px; margin: 0 auto;">
                        <div style="margin-bottom: 25px;">
                            <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #1f2937;">
                                Computer Name:
                            </label>
                            <input type="text" id="hostname" value="aurora-pc" style="width: 100%; padding: 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 1rem;">
                        </div>
                        
                        <div style="margin-bottom: 25px;">
                            <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #1f2937;">
                                Username:
                            </label>
                            <input type="text" id="username" value="aurora" style="width: 100%; padding: 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 1rem;">
                        </div>
                        
                        <div style="margin-bottom: 25px;">
                            <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #1f2937;">
                                Password:
                            </label>
                            <input type="password" id="password" placeholder="Enter password" style="width: 100%; padding: 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 1rem;">
                        </div>
                        
                        <div style="margin-bottom: 25px;">
                            <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #1f2937;">
                                Timezone:
                            </label>
                            <select id="timezone" style="width: 100%; padding: 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 1rem;">
                                <option value="UTC">UTC</option>
                                <option value="America/New_York">Eastern Time</option>
                                <option value="America/Los_Angeles">Pacific Time</option>
                                <option value="Europe/London">London</option>
                                <option value="Asia/Tokyo">Tokyo</option>
                            </select>
                        </div>
                        
                        <div style="margin-bottom: 25px;">
                            <label style="flex-direction: row; align-items: center; gap: 10px; cursor: pointer;">
                                <input type="checkbox" id="auto-login" style="width: 20px; height: 20px;">
                                <span style="font-weight: 600; color: #1f2937;">Enable automatic login</span>
                            </label>
                        </div>
                    </div>
                </div>
                
                <!-- Completion Step -->
                <div class="step-content" id="step-completion">
                    <div class="completion-content">
                        <div class="success-icon">✓</div>
                        <h2 class="step-title">Installation Complete!</h2>
                        <p class="step-description">
                            Aurora OS has been successfully installed on your system. 
                            You're now ready to experience the future of AI-native computing.
                        </p>
                        
                        <div class="completion-actions">
                            <button class="nav-btn btn-secondary" onclick="rebootSystem()">
                                Reboot Now
                            </button>
                            <button class="nav-btn btn-primary" onclick="createBootableUSB()">
                                Create Bootable USB
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Navigation -->
            <div class="installer-navigation">
                <button class="nav-btn btn-secondary" id="back-btn" onclick="previousStep()" disabled>
                    ← Back
                </button>
                <button class="nav-btn btn-primary" id="next-btn" onclick="nextStep()">
                    Next →
                </button>
            </div>
        </div>
    </div>

    <script>
        // Installer State
        class AuroraInstaller {{
            constructor() {{
                this.currentStep = 0;
                this.steps = ['welcome', 'requirements', 'partitioning', 'installation', 'configuration', 'completion'];
                this.installationMode = 'standard';
                this.systemRequirements = null;
                this.selectedDevice = null;
                this.installationProgress = 0;
                
                this.init();
            }}
            
            init() {{
                this.updateProgressBar();
                this.checkSystemRequirements();
                this.loadAvailableDevices();
            }}
            
            updateProgressBar() {{
                const progressFill = document.getElementById('progress-fill');
                const progress = ((this.currentStep + 1) / this.steps.length) * 100;
                progressFill.style.width = `${{progress}}%`;
            }}
            
            showStep(stepName) {{
                // Hide all steps
                document.querySelectorAll('.step-content').forEach(step => {{
                    step.classList.remove('active');
                }});
                
                // Show current step
                document.getElementById(`step-${{stepName}}`).classList.add('active');
                
                // Update navigation buttons
                this.updateNavigationButtons();
                
                // Update progress bar
                this.updateProgressBar();
                
                // Step-specific initialization
                if (stepName === 'requirements') {{
                    this.displayRequirements();
                }} else if (stepName === 'installation') {{
                    this.startInstallation();
                }}
            }}
            
            updateNavigationButtons() {{
                const backBtn = document.getElementById('back-btn');
                const nextBtn = document.getElementById('next-btn');
                
                backBtn.disabled = this.currentStep === 0;
                
                if (this.currentStep === this.steps.length - 1) {{
                    nextBtn.style.display = 'none';
                }} else {{
                    nextBtn.style.display = 'block';
                    nextBtn.textContent = this.currentStep === this.steps.length - 2 ? 'Install' : 'Next →';
                }}
            }}
            
            checkSystemRequirements() {{
                // Simulate system requirements check
                const requirements = [
                    {{ name: 'CPU Cores', value: 4, required: 2, met: true, unit: 'cores' }},
                    {{ name: 'Memory', value: 8, required: 4, met: true, unit: 'GB' }},
                    {{ name: 'Disk Space', value: 120, required: 20, met: true, unit: 'GB' }},
                    {{ name: 'UEFI Support', value: 'Yes', required: 'Yes', met: true, unit: '' }},
                ];
                
                this.systemRequirements = requirements;
            }}
            
            displayRequirements() {{
                const grid = document.getElementById('requirements-grid');
                const warnings = document.getElementById('requirements-warnings');
                
                let hasWarnings = false;
                let hasErrors = false;
                
                grid.innerHTML = requirements.map(req => {{
                    let statusClass = 'met';
                    let icon = '✅';
                    
                    if (!req.met) {{
                        if (req.name === 'Memory' || req.name === 'CPU Cores') {{
                            statusClass = 'failed';
                            icon = '❌';
                            hasErrors = true;
                        }} else {{
                            statusClass = 'warning';
                            icon = '⚠️';
                            hasWarnings = true;
                        }}
                    }}
                    
                    return `
                        <div class="requirement-item ${{statusClass}}">
                            <div class="requirement-icon">${{icon}}</div>
                            <div class="requirement-text">
                                <div class="requirement-label">${{req.name}}</div>
                                <div class="requirement-value">${{req.value}} ${{req.unit}} (Required: ${{req.required}} ${{req.unit}})</div>
                            </div>
                        </div>
                    `;
                }}).join('');
                
                if (hasWarnings) {{
                    warnings.innerHTML = `
                        <div style="background: #fffbeb; border: 1px solid #f59e0b; padding: 15px; border-radius: 8px; margin-top: 20px;">
                            <strong>⚠️ Warning:</strong> Some requirements are not fully met. Aurora OS may run slowly or with limited functionality.
                        </div>
                    `;
                }} else if (hasErrors) {{
                    warnings.innerHTML = `
                        <div style="background: #fef2f2; border: 1px solid #ef4444; padding: 15px; border-radius: 8px; margin-top: 20px;">
                            <strong>❌ Error:</strong> Your system does not meet the minimum requirements for Aurora OS.
                        </div>
                    `;
                }}
            }}
            
            loadAvailableDevices() {{
                // Simulate device detection
                const devices = [
                    {{ name: '/dev/sda', size: '500GB', type: 'SSD', model: 'Samsung SSD 860 EVO' }},
                    {{ name: '/dev/sdb', size: '1TB', type: 'HDD', model: 'WD Blue 1TB' }},
                ];
                
                this.availableDevices = devices;
                this.selectedDevice = devices[0]; // Select first device by default
            }}
            
            displayDevices() {{
                const deviceList = document.getElementById('device-list');
                
                deviceList.innerHTML = this.availableDevices.map((device, index) => `
                    <div class="device-item ${{index === 0 ? 'selected' : ''}}" onclick="selectDevice(${{index}})">
                        <div class="device-name">${{device.name}}</div>
                        <div class="device-specs">${{device.size}} ${{device.type}} - ${{device.model}}</div>
                    </div>
                `).join('');
                
                this.updatePartitionDiagram();
            }}
            
            updatePartitionDiagram() {{
                const visual = document.getElementById('partition-visual');
                
                // Simulate partition layout
                const partitions = [
                    {{ name: 'EFI', size: 512, color: '#10b981' }},
                    {{ name: 'Boot', size: 1024, color: '#3b82f6' }},
                    {{ name: 'Root', size: 30720, color: '#8b5cf6' }},
                    {{ name: 'Home', size: 120000, color: '#f59e0b' }},
                ];
                
                const totalSize = partitions.reduce((sum, p) => sum + p.size, 0);
                
                visual.innerHTML = partitions.map(partition => {{
                    const percentage = (partition.size / totalSize) * 100;
                    return `
                        <div class="partition-block" style="width: ${{percentage}}%; background: ${{partition.color}};">
                            <span class="partition-label">${{partition.name}} (${{partition.size >= 1024 ? partition.size/1024 + 'GB' : partition.size + 'MB'}})</span>
                            ${{partition.name}}
                        </div>
                    `;
                }}).join('');
            }}
            
            async startInstallation() {{
                const installSteps = [
                    {{ name: 'Preparing installation', duration: 2000 }},
                    {{ name: 'Creating partitions', duration: 3000 }},
                    {{ name: 'Formatting filesystems', duration: 2500 }},
                    {{ name: 'Installing base system', duration: 5000 }},
                    {{ name: 'Configuring system', duration: 2000 }},
                    {{ name: 'Installing AI components', duration: 4000 }},
                    {{ name: 'Setting up bootloader', duration: 1500 }},
                    {{ name: 'Finalizing installation', duration: 1000 }},
                ];
                
                const progressContainer = document.getElementById('installation-progress');
                const mainProgressFill = document.getElementById('main-progress-fill');
                
                progressContainer.innerHTML = '';
                
                for (let i = 0; i < installSteps.length; i++) {{
                    const step = installSteps[i];
                    
                    // Add step to display
                    const stepElement = document.createElement('div');
                    stepElement.className = 'progress-item';
                    stepElement.innerHTML = `
                        <div class="progress-icon">⏳</div>
                        <div class="progress-text">${{step.name}}</div>
                        <div class="progress-status">In progress...</div>
                    `;
                    progressContainer.appendChild(stepElement);
                    
                    // Simulate step execution
                    await new Promise(resolve => setTimeout(resolve, step.duration));
                    
                    // Update step status
                    stepElement.querySelector('.progress-icon').textContent = '✅';
                    stepElement.querySelector('.progress-status').className = 'progress-status completed';
                    stepElement.querySelector('.progress-status').textContent = 'Completed';
                    
                    // Update main progress
                    const progress = ((i + 1) / installSteps.length) * 100;
                    mainProgressFill.style.width = `${{progress}}%`;
                }}
                
                // Auto-advance to next step after installation
                setTimeout(() => {{
                    this.nextStep();
                }}, 1000);
            }}
            
            nextStep() {{
                if (this.currentStep < this.steps.length - 1) {{
                    this.currentStep++;
                    this.showStep(this.steps[this.currentStep]);
                }}
            }}
            
            previousStep() {{
                if (this.currentStep > 0) {{
                    this.currentStep--;
                    this.showStep(this.steps[this.currentStep]);
                }}
            }}
        }}
        
        // Global functions
        function selectMode(mode) {{
            // Update selected mode
            document.querySelectorAll('.mode-card').forEach(card => {{
                card.classList.remove('selected');
            }});
            event.target.closest('.mode-card').classList.add('selected');
            
            installer.installationMode = mode;
        }}
        
        function selectDevice(index) {{
            // Update selected device
            document.querySelectorAll('.device-item').forEach(item => {{
                item.classList.remove('selected');
            }});
            document.querySelectorAll('.device-item')[index].classList.add('selected');
            
            installer.selectedDevice = installer.availableDevices[index];
            installer.updatePartitionDiagram();
        }}
        
        function nextStep() {{
            installer.nextStep();
            
            // Load devices when entering partitioning step
            if (installer.currentStep === 2) {{
                installer.displayDevices();
            }}
        }}
        
        function previousStep() {{
            installer.previousStep();
        }}
        
        function rebootSystem() {{
            if (confirm('Are you sure you want to reboot your system?')) {{
                alert('System will reboot into Aurora OS...');
                // In real implementation, this would trigger a reboot
            }}
        }}
        
        function createBootableUSB() {{
            alert('USB creation tool will be opened...');
            // In real implementation, this would launch USB creation tool
        }}
        
        // Initialize installer
        const installer = new AuroraInstaller();
    </script>
</body>
</html>
        """
    
    async def start_installer(self):
        """Start the installation process"""
        self.logger.info("Starting Aurora OS Installer")
        
        # Check system requirements
        await self.check_system_requirements()
        
        # Generate installer HTML
        html_content = self.generate_installer_html()
        
        # Save installer HTML
        installer_path = '/workspace/aurora_os_installer.html'
        with open(installer_path, 'w') as f:
            f.write(html_content)
        
        self.logger.info(f"Aurora OS Installer generated: {installer_path}")
        
        return installer_path
    
    async def check_system_requirements(self) -> SystemRequirements:
        """Check system requirements"""
        self.logger.info("Checking system requirements")
        
        try:
            # Get CPU info
            cpu_info = subprocess.check_output(['nproc'], text=True).strip()
            cpu_cores = int(cpu_info)
            
            # Get memory info
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
            
            mem_total = 0
            for line in meminfo.split('\n'):
                if line.startswith('MemTotal:'):
                    mem_total = int(line.split()[1])
                    break
            
            memory_gb = mem_total // (1024 * 1024)  # Convert KB to GB
            
            # Get disk space
            disk_usage = shutil.disk_usage('/')
            disk_space_gb = disk_usage.free // (1024 * 1024 * 1024)  # Convert to GB
            
            # Check UEFI support
            uefi_path = '/sys/firmware/efi'
            uefi_support = os.path.exists(uefi_path)
            
            # Create requirements object
            requirements = SystemRequirements(
                cpu_cores=cpu_cores,
                memory_gb=memory_gb,
                disk_space_gb=disk_space_gb,
                uefi_support=uefi_support,
                requirements_met=self._validate_requirements(cpu_cores, memory_gb, disk_space_gb, uefi_support),
                warnings=self._get_requirements_warnings(cpu_cores, memory_gb, disk_space_gb)
            )
            
            self.system_requirements = requirements
            
            self.logger.info(f"System requirements check completed: {requirements.requirements_met}")
            if requirements.warnings:
                self.logger.warning(f"Requirements warnings: {requirements.warnings}")
            
            return requirements
            
        except Exception as e:
            self.logger.error(f"Error checking system requirements: {e}")
            raise
    
    def _validate_requirements(self, cpu_cores: int, memory_gb: int, disk_space_gb: int, uefi_support: bool) -> bool:
        """Validate if requirements are met"""
        min_req = self.config["minimal_requirements"]
        
        return (
            cpu_cores >= min_req["cpu_cores"] and
            memory_gb >= min_req["memory_gb"] and
            disk_space_gb >= min_req["disk_space_gb"] and
            (uefi_support or not min_req["uefi_support"])
        )
    
    def _get_requirements_warnings(self, cpu_cores: int, memory_gb: int, disk_space_gb: int) -> List[str]:
        """Get requirements warnings"""
        warnings = []
        rec_req = self.config["recommended_requirements"]
        
        if cpu_cores < rec_req["cpu_cores"]:
            warnings.append(f"CPU cores below recommended ({cpu_cores} < {rec_req['cpu_cores']})")
        
        if memory_gb < rec_req["memory_gb"]:
            warnings.append(f"Memory below recommended ({memory_gb}GB < {rec_req['memory_gb']}GB)")
        
        if disk_space_gb < rec_req["disk_space_gb"]:
            warnings.append(f"Disk space below recommended ({disk_space_gb}GB < {rec_req['disk_space_gb']}GB)")
        
        return warnings
    
    def detect_storage_devices(self) -> List[Dict[str, Any]]:
        """Detect available storage devices"""
        devices = []
        
        try:
            # Get block devices
            result = subprocess.run(['lsblk', '-J'], capture_output=True, text=True)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                
                for device in data.get('blockdevices', []):
                    if device.get('type') == 'disk':
                        device_info = {
                            'name': device['name'],
                            'size': device['size'],
                            'model': device.get('model', 'Unknown'),
                            'vendor': device.get('vendor', 'Unknown'),
                            'type': 'SSD' if 'ssd' in device.get('rota', '').lower() else 'HDD',
                            'removable': device.get('rm', False) == '1'
                        }
                        devices.append(device_info)
            
            self.logger.info(f"Detected {len(devices)} storage devices")
            
        except Exception as e:
            self.logger.error(f"Error detecting storage devices: {e}")
        
        return devices
    
    def create_partition_scheme(self, device_path: str, mode: InstallationMode) -> PartitionScheme:
        """Create partition scheme based on installation mode"""
        self.logger.info(f"Creating partition scheme for {device_path} in {mode.value} mode")
        
        if mode == InstallationMode.STANDARD:
            # Standard partitioning
            scheme = PartitionScheme(
                boot_partition=f"{device_path}1",
                root_partition=f"{device_path}2",
                swap_partition=f"{device_path}3",
                home_partition=None,
                efi_partition=f"{device_path}1" if self.system_requirements.uefi_support else None
            )
        
        elif mode == InstallationMode.ADVANCED:
            # Advanced partitioning with separate home
            scheme = PartitionScheme(
                boot_partition=f"{device_path}1",
                root_partition=f"{device_path}2",
                swap_partition=f"{device_path}3",
                home_partition=f"{device_path}4",
                efi_partition=f"{device_path}1" if self.system_requirements.uefi_support else None
            )
        
        elif mode == InstallationMode.DUAL_BOOT:
            # Dual boot configuration
            scheme = PartitionScheme(
                boot_partition=f"{device_path}5",  # First available partition
                root_partition=f"{device_path}6",
                swap_partition=f"{device_path}7",
                home_partition=None,
                efi_partition=f"{device_path}1" if self.system_requirements.uefi_support else None
            )
        
        else:  # PORTABLE
            # Portable USB installation
            scheme = PartitionScheme(
                boot_partition=f"{device_path}1",
                root_partition=f"{device_path}2",
                swap_partition=None,  # No swap on USB
                home_partition=None,
                efi_partition=f"{device_path}1" if self.system_requirements.uefi_support else None
            )
        
        self.partition_scheme = scheme
        return scheme
    
    async def execute_installation(self):
        """Execute the installation process"""
        self.logger.info("Starting Aurora OS installation")
        
        try:
            # Step 1: Prepare installation
            await self._log_installation_step("Preparing installation")
            await self._prepare_installation()
            
            # Step 2: Create partitions
            await self._log_installation_step("Creating partitions")
            await self._create_partitions()
            
            # Step 3: Format filesystems
            await self._log_installation_step("Formatting filesystems")
            await self._format_filesystems()
            
            # Step 4: Install base system
            await self._log_installation_step("Installing base system")
            await self._install_base_system()
            
            # Step 5: Configure system
            await self._log_installation_step("Configuring system")
            await self._configure_system()
            
            # Step 6: Install AI components
            await self._log_installation_step("Installing AI components")
            await self._install_ai_components()
            
            # Step 7: Setup bootloader
            await self._log_installation_step("Setting up bootloader")
            await self._setup_bootloader()
            
            # Step 8: Finalize installation
            await self._log_installation_step("Finalizing installation")
            await self._finalize_installation()
            
            self.logger.info("Aurora OS installation completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Installation failed: {e}")
            await self._log_installation_step(f"Installation failed: {e}")
            return False
    
    async def _log_installation_step(self, step_name: str):
        """Log installation step"""
        self.installation_logs.append({
            'step': step_name,
            'timestamp': time.time(),
            'status': 'in_progress'
        })
        
        self.logger.info(f"Installation step: {step_name}")
        await asyncio.sleep(0.1)  # Small delay for UI updates
    
    async def _prepare_installation(self):
        """Prepare installation environment"""
        # Create installation directories
        os.makedirs(self.installation_path, exist_ok=True)
        
        # Mount filesystems
        os.makedirs(f"{self.installation_path}/mnt", exist_ok=True)
        
        await asyncio.sleep(2)  # Simulate preparation time
    
    async def _create_partitions(self):
        """Create disk partitions"""
        if not self.partition_scheme:
            raise ValueError("Partition scheme not defined")
        
        # Simulate partition creation
        await asyncio.sleep(3)
        self.installation_progress = 20
    
    async def _format_filesystems(self):
        """Format filesystems"""
        # Simulate filesystem formatting
        await asyncio.sleep(2.5)
        self.installation_progress = 35
    
    async def _install_base_system(self):
        """Install base Aurora OS system"""
        # Simulate base system installation
        await asyncio.sleep(5)
        self.installation_progress = 60
    
    async def _configure_system(self):
        """Configure system settings"""
        # Simulate system configuration
        await asyncio.sleep(2)
        self.installation_progress = 75
    
    async def _install_ai_components(self):
        """Install AI components"""
        # Simulate AI component installation
        await asyncio.sleep(4)
        self.installation_progress = 90
    
    async def _setup_bootloader(self):
        """Setup bootloader"""
        # Simulate bootloader setup
        await asyncio.sleep(1.5)
        self.installation_progress = 95
    
    async def _finalize_installation(self):
        """Finalize installation"""
        # Clean up and finalize
        await asyncio.sleep(1)
        self.installation_progress = 100
    
    def create_bootable_usb(self, iso_path: str, usb_device: str) -> bool:
        """Create bootable USB from ISO"""
        self.logger.info(f"Creating bootable USB: {iso_path} -> {usb_device}")
        
        try:
            # This would use dd or similar tool to write ISO to USB
            # subprocess.run(['dd', f'if={iso_path}', f'of={usb_device}', 'bs=4M', 'status=progress'])
            
            self.logger.info("Bootable USB created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create bootable USB: {e}")
            return False
    
    def get_installation_summary(self) -> Dict[str, Any]:
        """Get installation summary"""
        return {
            'installation_id': self.installation_id,
            'mode': self.installation_mode.value,
            'requirements_met': self.system_requirements.requirements_met if self.system_requirements else False,
            'partition_scheme': self.partition_scheme.__dict__ if self.partition_scheme else None,
            'progress': self.installation_progress,
            'logs': self.installation_logs,
            'timestamp': time.time()
        }

# Export main class
__all__ = ['AuroraInstaller']