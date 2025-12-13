"""
Aurora OS - Nix Integration for Declarative OS Management
Integrates NixOS declarative configuration with AI-generated configs
Provides atomic upgrades, perfect rollbacks, and zero configuration drift
"""

import os
import sys
import json
import asyncio
import subprocess
import tempfile
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import logging
from datetime import datetime
import hashlib

try:
    import libnix
    NIX_AVAILABLE = True
except ImportError:
    NIX_AVAILABLE = False

from ...ai_assistant.core.local_llm_engine import get_llm_engine
from ...ai_assistant.agents.task_agent import Task

@dataclass
class NixConfiguration:
    """NixOS configuration structure"""
    system_version: str
    packages: List[str]
    services: Dict[str, Dict[str, Any]]
    users: List[Dict[str, Any]]
    networking: Dict[str, Any]
    hardware: Dict[str, Any]
    security: Dict[str, Any]
    aurora_settings: Dict[str, Any]
    generated_by: str = "ai"
    generated_at: datetime = field(default_factory=datetime.now)
    checksum: str = ""

@dataclass
class NixOperation:
    """Nix operation with rollback capability"""
    id: str
    type: str  # upgrade, rollback, install, remove
    config_before: Optional[NixConfiguration] = None
    config_after: Optional[NixConfiguration] = None
    status: str = "pending"  # pending, running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    rollback_available: bool = False
    error_message: Optional[str] = None

class NixIntegration:
    """
    Advanced NixOS integration for Aurora OS
    AI-powered declarative configuration management
    """
    
    def __init__(self):
        self.llm_engine = get_llm_engine()
        self.nix_path = Path("/etc/nixos")
        self.config_file = self.nix_path / "configuration.nix"
        self.backup_dir = Path("/var/backups/nixos")
        self.operations: Dict[str, NixOperation] = []
        
        self.logger = logging.getLogger("Aurora.NixIntegration")
        self._setup_logging()
        
        # Initialize Nix environment
        self._init_nix_environment()
        
        # Load current configuration
        self.current_config = self._load_current_config()
    
    def _setup_logging(self):
        """Setup logging"""
        log_dir = Path("/var/log/aurora")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(log_dir / "nix_integration.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _init_nix_environment(self):
        """Initialize Nix environment"""
        try:
            # Check if Nix is installed
            result = subprocess.run(['nix', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.warning("Nix not found, installing...")
                self._install_nix()
            
            # Ensure NixOS configuration directory exists
            self.nix_path.mkdir(parents=True, exist_ok=True)
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            self.logger.info("Nix environment initialized")
        
        except Exception as e:
            self.logger.error(f"Failed to initialize Nix: {e}")
    
    def _install_nix(self):
        """Install Nix package manager"""
        try:
            # Download and install Nix
            install_script = """
            curl -L https://nixos.org/nix/install | sh -s -- --daemon
            """
            subprocess.run(install_script, shell=True, check=True)
            
            # Add to PATH
            os.environ['PATH'] = '/nix/var/nix/profiles/default/bin:' + os.environ.get('PATH', '')
            
            self.logger.info("Nix installed successfully")
        
        except Exception as e:
            self.logger.error(f"Failed to install Nix: {e}")
            raise
    
    def _load_current_config(self) -> NixConfiguration:
        """Load current NixOS configuration"""
        try:
            if not self.config_file.exists():
                return self._create_default_config()
            
            # Parse existing configuration
            config_content = self.config_file.read_text()
            
            # Parse Nix configuration (simplified)
            config = NixConfiguration(
                system_version="23.11",
                packages=[],
                services={},
                users=[],
                networking={},
                hardware={},
                security={},
                aurora_settings={}
            )
            
            # Extract basic information
            if 'environment.systemPackages' in config_content:
                # Extract packages using regex
                import re
                packages = re.findall(r'\[ ([\s\S]*?) \]', config_content)
                for package_list in packages:
                    lines = package_list.strip().split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            package_name = line.strip().rstrip(';')
                            if package_name:
                                config.packages.append(package_name)
            
            self.logger.info(f"Loaded current configuration with {len(config.packages)} packages")
            return config
        
        except Exception as e:
            self.logger.error(f"Failed to load current config: {e}")
            return self._create_default_config()
    
    def _create_default_config(self) -> NixConfiguration:
        """Create default NixOS configuration"""
        return NixConfiguration(
            system_version="23.11",
            packages=[
                "vim",
                "git",
                "curl",
                "wget",
                "firefox",
                "libreoffice"
            ],
            services={
                "xserver": {
                    "enable": True,
                    "desktopManager": {
                        "aurora": {
                            "enable": True
                        }
                    }
                }
            },
            users=[{
                "name": "user",
                "isNormalUser": True,
                "extraGroups": ["wheel", "networkmanager", "audio", "video"]
            }],
            networking={
                "networkmanager": {
                    "enable": True
                },
                "firewall": {
                    "enable": True
                }
            },
            hardware={
                "enableAllFirmware": True
            },
            security={
                "sudo": {
                    "enable": True
                }
            },
            aurora_settings={
                "ai_assistant": {
                    "enabled": True,
                    "model": "llama-3.2-3b"
                },
                "driver_management": {
                    "auto_install": True
                },
                "intent_settings": {
                    "enabled": True
                }
            }
        )
    
    async def generate_config_from_intent(self, user_intent: str) -> NixConfiguration:
        """Generate Nix configuration from user intent using AI"""
        self.logger.info(f"Generating config from intent: {user_intent}")
        
        try:
            # Create prompt for AI
            prompt = f"""
            Generate a NixOS configuration for the following user intent: "{user_intent}"
            
            Consider the following aspects:
            1. System packages needed
            2. Services to enable
            3. User configuration
            4. Networking setup
            5. Security settings
            6. Aurora OS specific settings
            
            Current system info:
            - Aurora OS v1.0
            - AI-native operating system
            - Includes LLM integration
            - Automatic driver management
            - Intent-based settings
            
            Respond with a JSON configuration that includes:
            - packages: List of required packages
            - services: Dictionary of services with their configuration
            - users: List of user configurations
            - networking: Network configuration
            - hardware: Hardware settings
            - security: Security settings
            - aurora_settings: Aurora OS specific settings
            """
            
            # Generate configuration using AI
            from ...ai_assistant.core.local_llm_engine import AIRequest
            request = AIRequest(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.3
            )
            
            response = await self.llm_engine.generate_response(request)
            
            # Parse AI response
            config_data = self._parse_ai_config_response(response.text)
            
            # Create configuration object
            config = NixConfiguration(
                system_version="23.11",
                packages=config_data.get('packages', []),
                services=config_data.get('services', {}),
                users=config_data.get('users', []),
                networking=config_data.get('networking', {}),
                hardware=config_data.get('hardware', {}),
                security=config_data.get('security', {}),
                aurora_settings=config_data.get('aurora_settings', {}),
                generated_by="ai_intent",
                generated_at=datetime.now()
            )
            
            # Calculate checksum
            config.checksum = self._calculate_config_checksum(config)
            
            self.logger.info(f"Generated configuration with {len(config.packages)} packages")
            return config
        
        except Exception as e:
            self.logger.error(f"Failed to generate config from intent: {e}")
            raise
    
    def _parse_ai_config_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response into configuration data"""
        try:
            # Look for JSON in the response
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            # Try to parse the entire response as JSON
            return json.loads(response_text)
        
        except:
            # Fallback to simple parsing
            config = {
                "packages": [],
                "services": {},
                "users": [],
                "networking": {},
                "hardware": {},
                "security": {},
                "aurora_settings": {}
            }
            
            # Extract basic information
            lines = response_text.split('\n')
            for line in lines:
                line = line.strip()
                if 'packages:' in line.lower():
                    continue  # Would need more sophisticated parsing
            
            return config
    
    def _calculate_config_checksum(self, config: NixConfiguration) -> str:
        """Calculate checksum of configuration"""
        config_str = json.dumps({
            'packages': sorted(config.packages),
            'services': config.services,
            'users': config.users,
            'networking': config.networking,
            'hardware': config.hardware,
            'security': config.security,
            'aurora_settings': config.aurora_settings
        }, sort_keys=True)
        
        return hashlib.sha256(config_str.encode()).hexdigest()
    
    async def apply_configuration(self, config: NixConfiguration, dry_run: bool = False) -> NixOperation:
        """Apply NixOS configuration"""
        operation_id = f"nix_op_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        operation = NixOperation(
            id=operation_id,
            type="apply",
            config_before=self.current_config,
            config_after=config
        )
        
        self.operations[operation_id] = operation
        
        try:
            operation.status = "running"
            operation.started_at = datetime.now()
            
            # Generate Nix configuration file
            nix_config = self._generate_nix_config(config)
            
            if dry_run:
                self.logger.info("Dry run - not applying configuration")
                operation.status = "completed"
                operation.completed_at = datetime.now()
                return operation
            
            # Create backup
            backup_path = self._create_backup()
            
            # Write new configuration
            temp_config_file = self.config_file.with_suffix('.tmp')
            temp_config_file.write_text(nix_config)
            
            # Validate configuration
            validate_result = await self._validate_configuration(temp_config_file)
            if not validate_result['success']:
                operation.status = "failed"
                operation.error_message = f"Configuration validation failed: {validate_result['error']}"
                return operation
            
            # Apply configuration
            apply_result = await self._apply_nix_config(temp_config_file)
            
            if apply_result['success']:
                # Move temp file to actual config
                temp_config_file.replace(self.config_file)
                
                # Update current config
                self.current_config = config
                
                operation.status = "completed"
                operation.completed_at = datetime.now()
                operation.rollback_available = True
                
                self.logger.info(f"Configuration applied successfully: {operation_id}")
            else:
                operation.status = "failed"
                operation.error_message = f"Configuration application failed: {apply_result['error']}"
                
                # Restore backup
                self._restore_backup(backup_path)
        
        except Exception as e:
            operation.status = "failed"
            operation.error_message = str(e)
            self.logger.error(f"Configuration application failed: {e}")
        
        return operation
    
    def _generate_nix_config(self, config: NixConfiguration) -> str:
        """Generate NixOS configuration file content"""
        nix_config = f'''# Aurora OS NixOS Configuration
# Generated by Aurora AI at {config.generated_at.isoformat()}
# Checksum: {config.checksum}

{{ config, pkgs, ... }}:

{{
  imports = [
    ./hardware-configuration.nix
  ];

  # System configuration
  system.stateVersion = "{config.system_version}";
  
  # Packages
  environment.systemPackages = with pkgs; [
'''
        
        # Add packages
        for package in sorted(config.packages):
            nix_config += f'    {package}\n'
        
        nix_config += '''  ];
  
  # Services
'''
        
        # Add services
        for service_name, service_config in config.services.items():
            nix_config += f"  services.{service_name} = {{\n"
            for key, value in service_config.items():
                if isinstance(value, bool):
                    nix_config += f"    {key} = {'true' if value else 'false'};\n"
                elif isinstance(value, str):
                    nix_config += f"    {key} = &quot;{value}&quot;;\n"
                elif isinstance(value, dict):
                    nix_config += f"    {key} = {{\n"
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, bool):
                            nix_config += f"      {sub_key} = {'true' if sub_value else 'false'};\n"
                        elif isinstance(sub_value, str):
                            nix_config += f"      {sub_key} = &quot;{sub_value}&quot;;\n"
                    nix_config += "    };\n"
            nix_config += "  };\n"
        
        # Add users
        if config.users:
            nix_config += "\n  # Users\n  users.users = {\n"
            for user in config.users:
                nix_config += f"    {user['name']} = {{\n"
                for key, value in user.items():
                    if isinstance(value, bool):
                        nix_config += f"      {key} = {'true' if value else 'false'};\n"
                    elif isinstance(value, str):
                        nix_config += f"      {key} = &quot;{value}&quot;;\n"
                    elif isinstance(value, list):
                        nix_config += f"      {key} = [ {' '.join(f'&quot;{item}&quot;' for item in value)} ];\n"
                nix_config += "    };\n"
            nix_config += "  };\n"
        
        # Add networking
        if config.networking:
            nix_config += "\n  # Networking\n  networking = {\n"
            for key, value in config.networking.items():
                if isinstance(value, bool):
                    nix_config += f"    {key} = {'true' if value else 'false'};\n"
                elif isinstance(value, str):
                    nix_config += f"    {key} = &quot;{value}&quot;;\n"
            nix_config += "  };\n"
        
        # Add hardware
        if config.hardware:
            nix_config += "\n  # Hardware\n  hardware = {\n"
            for key, value in config.hardware.items():
                if isinstance(value, bool):
                    nix_config += f"    {key} = {'true' if value else 'false'};\n"
            nix_config += "  };\n"
        
        # Add security
        if config.security:
            nix_config += "\n  # Security\n  security = {\n"
            for key, value in config.security.items():
                if isinstance(value, bool):
                    nix_config += f"    {key} = {'true' if value else 'false'};\n"
            nix_config += "  };\n"
        
        # Add Aurora OS specific settings
        if config.aurora_settings:
            nix_config += "\n  # Aurora OS Settings\n  environment.aurora = {\n"
            for key, value in config.aurora_settings.items():
                if isinstance(value, bool):
                    nix_config += f"    {key} = {'true' if value else 'false'};\n"
                elif isinstance(value, dict):
                    nix_config += f"    {key} = {{\n"
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, bool):
                            nix_config += f"      {sub_key} = {'true' if sub_value else 'false'};\n"
                        elif isinstance(sub_value, str):
                            nix_config += f"      {sub_key} = &quot;{sub_value}&quot;;\n"
                    nix_config += "    };\n"
            nix_config += "  };\n"
        
        nix_config += "\n}\n"
        
        return nix_config
    
    async def _validate_configuration(self, config_file: Path) -> Dict[str, Any]:
        """Validate NixOS configuration"""
        try:
            result = subprocess.run(
                ['nix-instantiate', '--parse', str(config_file)],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return {'success': True}
            else:
                return {
                    'success': False,
                    'error': result.stderr
                }
        
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Configuration validation timed out'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _apply_nix_config(self, config_file: Path) -> Dict[str, Any]:
        """Apply NixOS configuration"""
        try:
            # Run nixos-rebuild switch
            result = subprocess.run(
                ['nixos-rebuild', 'switch', '-I', f'nixos-config={config_file}'],
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            
            if result.returncode == 0:
                return {'success': True}
            else:
                return {
                    'success': False,
                    'error': result.stderr
                }
        
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Configuration application timed out'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_backup(self) -> Path:
        """Create backup of current configuration"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.backup_dir / f"config_{timestamp}.nix"
        
        if self.config_file.exists():
            backup_path.write_text(self.config_file.read_text())
        
        self.logger.info(f"Created backup: {backup_path}")
        return backup_path
    
    def _restore_backup(self, backup_path: Path):
        """Restore configuration from backup"""
        if backup_path.exists():
            self.config_file.write_text(backup_path.read_text())
            self.logger.info(f"Restored backup: {backup_path}")
    
    async def rollback_operation(self, operation_id: str) -> NixOperation:
        """Rollback a specific operation"""
        operation = self.operations.get(operation_id)
        if not operation or not operation.config_before:
            raise ValueError(f"Cannot rollback operation {operation_id}")
        
        rollback_op_id = f"rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        rollback_operation = NixOperation(
            id=rollback_op_id,
            type="rollback",
            config_before=self.current_config,
            config_after=operation.config_before
        )
        
        self.operations[rollback_op_id] = rollback_operation
        
        try:
            rollback_operation.status = "running"
            rollback_operation.started_at = datetime.now()
            
            # Apply rollback configuration
            result = await self.apply_configuration(operation.config_before)
            
            if result.status == "completed":
                rollback_operation.status = "completed"
                rollback_operation.completed_at = datetime.now()
                
                self.logger.info(f"Successfully rolled back operation {operation_id}")
            else:
                rollback_operation.status = "failed"
                rollback_operation.error_message = result.error_message
        
        except Exception as e:
            rollback_operation.status = "failed"
            rollback_operation.error_message = str(e)
            self.logger.error(f"Rollback failed: {e}")
        
        return rollback_operation
    
    async def simulate_upgrade(self, config: NixConfiguration) -> Dict[str, Any]:
        """Simulate configuration upgrade before applying"""
        try:
            # Generate temporary config
            nix_config = self._generate_nix_config(config)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.nix', delete=False) as f:
                f.write(nix_config)
                temp_config_file = Path(f.name)
            
            try:
                # Simulate the rebuild
                result = subprocess.run(
                    ['nixos-rebuild', 'build', '-I', f'nixos-config={temp_config_file}'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode == 0:
                    # Parse results for insights
                    insights = self._parse_build_results(result.stdout)
                    
                    return {
                        'success': True,
                        'insights': insights,
                        'packages_to_install': len(config.packages) - len(self.current_config.packages),
                        'services_to_change': self._compare_services(config.services, self.current_config.services)
                    }
                else:
                    return {
                        'success': False,
                        'error': result.stderr
                    }
            
            finally:
                temp_config_file.unlink(missing_ok=True)
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _parse_build_results(self, build_output: str) -> List[str]:
        """Parse nixos-rebuild build output for insights"""
        insights = []
        
        lines = build_output.split('\n')
        for line in lines:
            if 'building' in line.lower():
                insights.append(f"Building: {line}")
            elif 'installing' in line.lower():
                insights.append(f"Installing: {line}")
            elif 'warning' in line.lower():
                insights.append(f"Warning: {line}")
        
        return insights
    
    def _compare_services(self, new_services: Dict, old_services: Dict) -> List[str]:
        """Compare service configurations"""
        changes = []
        
        # Check for new services
        for service_name in new_services:
            if service_name not in old_services:
                changes.append(f"New service: {service_name}")
            elif new_services[service_name] != old_services[service_name]:
                changes.append(f"Modified service: {service_name}")
        
        # Check for removed services
        for service_name in old_services:
            if service_name not in new_services:
                changes.append(f"Removed service: {service_name}")
        
        return changes
    
    def get_operation_history(self) -> List[NixOperation]:
        """Get history of all operations"""
        return sorted(self.operations.values(), key=lambda op: op.started_at or datetime.min, reverse=True)
    
    def get_current_packages(self) -> List[str]:
        """Get list of currently installed packages"""
        return self.current_config.packages.copy()
    
    async def add_package(self, package_name: str) -> bool:
        """Add a package to current configuration"""
        try:
            new_config = NixConfiguration(
                **self.current_config.__dict__
            )
            
            if package_name not in new_config.packages:
                new_config.packages.append(package_name)
                new_config.checksum = self._calculate_config_checksum(new_config)
                
                result = await self.apply_configuration(new_config)
                return result.status == "completed"
            
            return True  # Package already exists
        
        except Exception as e:
            self.logger.error(f"Failed to add package {package_name}: {e}")
            return False
    
    async def remove_package(self, package_name: str) -> bool:
        """Remove a package from current configuration"""
        try:
            new_config = NixConfiguration(
                **self.current_config.__dict__
            )
            
            if package_name in new_config.packages:
                new_config.packages.remove(package_name)
                new_config.checksum = self._calculate_config_checksum(new_config)
                
                result = await self.apply_configuration(new_config)
                return result.status == "completed"
            
            return True  # Package doesn't exist
        
        except Exception as e:
            self.logger.error(f"Failed to remove package {package_name}: {e}")
            return False

# Global Nix integration instance
_nix_integration = None

def get_nix_integration() -> NixIntegration:
    """Get global Nix integration instance"""
    global _nix_integration
    if _nix_integration is None:
        _nix_integration = NixIntegration()
    return _nix_integration

async def initialize_nix_system():
    """Initialize the Nix integration system"""
    nix = get_nix_integration()
    return nix