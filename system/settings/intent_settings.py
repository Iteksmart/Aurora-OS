"""
Aurora OS - Intent-Based Settings System
Replaces traditional settings menus with natural language goal-setting
Users express intent, AI determines optimal configuration
"""

import os
import sys
import json
import asyncio
import re
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import logging
from datetime import datetime
from enum import Enum

class IntentCategory(Enum):
    PERFORMANCE = "performance"
    BATTERY = "battery"
    PRIVACY = "privacy"
    SECURITY = "security"
    ACCESSIBILITY = "accessibility"
    NETWORK = "network"
    DISPLAY = "display"
    AUDIO = "audio"
    PRODUCTIVITY = "productivity"
    GAMING = "gaming"

class IntentComplexity(Enum):
    SIMPLE = "simple"      # Single setting change
    MODERATE = "moderate"  # Multiple related settings
    COMPLEX = "complex"    # System-wide changes
    EXPERT = "expert"      # Advanced configuration

@dataclass
class SettingParameter:
    """Individual system setting parameter"""
    name: str
    current_value: Any
    target_value: Any
    description: str
    category: str
    impact_level: str  # low, medium, high, critical
    requires_restart: bool = False
    validation_rules: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Intent:
    """User intent for system configuration"""
    id: str
    text: str
    category: IntentCategory
    complexity: IntentComplexity
    confidence: float
    parameters: List[SettingParameter] = field(default_factory=list)
    execution_plan: List[str] = field(default_factory=list)
    estimated_impact: str = ""
    requires_confirmation: bool = False
    created_at: datetime = field(default_factory=datetime.now)

class IntentEngine:
    """
    Intent processing engine for Aurora OS
    Converts natural language goals into system configurations
    """
    
    def __init__(self):
        self.logger = logging.getLogger("Aurora.IntentEngine")
        self.system_knowledge = self._load_system_knowledge()
        self.intent_patterns = self._load_intent_patterns()
        self.setting_handlers = self._load_setting_handlers()
        
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging"""
        log_dir = Path("/var/log/aurora")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(log_dir / "intent_engine.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _load_system_knowledge(self) -> Dict[str, Any]:
        """Load system knowledge base"""
        return {
            'hardware_capabilities': {
                'cpu': {'cores': 4, 'freq': 2.4, 'architecture': 'x86_64'},
                'gpu': {'vendor': 'intel', 'memory': 1024, 'supports_acceleration': True},
                'battery': {'present': True, 'capacity': 50},
                'memory': {'total': 8589934592, 'type': 'DDR4'},
                'storage': {'type': 'SSD', 'capacity': 500000000000}
            },
            'current_settings': {
                'power_profile': 'balanced',
                'display_brightness': 75,
                'sleep_timeout': 300,
                'wifi_enabled': True,
                'bluetooth_enabled': True,
                'theme': 'aurora',
                'animations_enabled': True,
                'notifications_enabled': True,
                'location_services': True,
                'microphone_access': 'prompt',
                'camera_access': 'prompt'
            },
            'constraints': {
                'battery_optimizable': True,
                'performance_tunable': True,
                'privacy_enhanceable': True,
                'accessibility_features': True,
                'network_configurable': True
            }
        }
    
    def _load_intent_patterns(self) -> Dict[str, Dict]:
        """Load intent recognition patterns"""
        return {
            # Performance intents
            'make_faster': {
                'keywords': ['faster', 'quick', 'speed', 'performance', 'optimize', 'boost'],
                'category': IntentCategory.PERFORMANCE,
                'complexity': IntentComplexity.MODERATE,
                'settings': [
                    'power_profile=performance',
                    'disable_animations=True',
                    'cpu_governor=performance',
                    'memory_compression=False'
                ]
            },
            'make_slower': {
                'keywords': ['slower', 'quiet', 'cool', 'conservative', 'battery'],
                'category': IntentCategory.BATTERY,
                'complexity': IntentComplexity.MODERATE,
                'settings': [
                    'power_profile=powersave',
                    'cpu_governor=powersave',
                    'display_brightness=40',
                    'sleep_timeout=120'
                ]
            },
            
            # Battery intents
            'long_battery': {
                'keywords': ['battery life', 'last longer', '12 hours', 'all day', 'extend battery'],
                'category': IntentCategory.BATTERY,
                'complexity': IntentComplexity.COMPLEX,
                'settings': [
                    'power_profile=powersave',
                    'display_brightness=30',
                    'sleep_timeout=60',
                    'wifi_timeout=300',
                    'bluetooth_timeout=60',
                    'background_apps=False',
                    'animations_enabled=False',
                    'location_services=False'
                ]
            },
            'max_performance': {
                'keywords': ['gaming', 'max performance', 'full power', 'no limits'],
                'category': IntentCategory.GAMING,
                'complexity': IntentComplexity.COMPLEX,
                'settings': [
                    'power_profile=performance',
                    'cpu_governor=performance',
                    'gpu_performance=high',
                    'display_refresh_rate=maximum',
                    'background_processes=minimal',
                    'network_priority=high'
                ]
            },
            
            # Privacy intents
            'private_mode': {
                'keywords': ['private', 'secure', 'anonymous', 'no tracking', 'privacy'],
                'category': IntentCategory.PRIVACY,
                'complexity': IntentComplexity.MODERATE,
                'settings': [
                    'location_services=False',
                    'microphone_access=denied',
                    'camera_access=denied',
                    'telemetry=False',
                    'crash_reports=False',
                    'dns_private=True'
                ]
            },
            
            # Security intents
            'secure_public': {
                'keywords': ['public wifi', 'coffee shop', 'airport', 'secure network'],
                'category': IntentCategory.SECURITY,
                'complexity': IntentComplexity.MODERATE,
                'settings': [
                    'firewall=strict',
                    'vpn_enabled=True',
                    'file_sharing=False',
                    'network_discovery=False',
                    'auto_connect_wifi=False'
                ]
            },
            
            # Accessibility intents
            'vision_impaired': {
                'keywords': ['visually impaired', 'large text', 'screen reader', 'high contrast'],
                'category': IntentCategory.ACCESSIBILITY,
                'complexity': IntentComplexity.MODERATE,
                'settings': [
                    'font_size=large',
                    'high_contrast=True',
                    'screen_reader=True',
                    'cursor_size=large',
                    'animations_disabled=True'
                ]
            },
            
            # Productivity intents
            'focus_mode': {
                'keywords': ['focus', 'work', 'study', 'distraction free', 'deep work'],
                'category': IntentCategory.PRODUCTIVITY,
                'complexity': IntentComplexity.MODERATE,
                'settings': [
                    'notifications=False',
                    'social_media_blocked=True',
                    'email_notifications=False',
                    'do_not_disturb=True',
                    'ambient_sounds=True'
                ]
            },
            
            # Display intents
            'dark_mode': {
                'keywords': ['dark mode', 'night mode', 'dim', 'easy on eyes'],
                'category': IntentCategory.DISPLAY,
                'complexity': IntentComplexity.SIMPLE,
                'settings': [
                    'theme=dark',
                    'display_brightness=50',
                    'blue_light_filter=True'
                ]
            },
            
            # Audio intents
            'quiet_mode': {
                'keywords': ['quiet', 'silent', 'mute', 'no sound'],
                'category': IntentCategory.AUDIO,
                'complexity': IntentComplexity.SIMPLE,
                'settings': [
                    'system_volume=0',
                    'notification_sounds=False',
                    'keyboard_clicks=False'
                ]
            }
        }
    
    def _load_setting_handlers(self) -> Dict[str, Callable]:
        """Load handlers for different setting types"""
        return {
            'power_profile': self._handle_power_profile,
            'display_brightness': self._handle_display_brightness,
            'sleep_timeout': self._handle_sleep_timeout,
            'wifi_enabled': self._handle_wifi_enabled,
            'bluetooth_enabled': self._handle_bluetooth_enabled,
            'theme': self._handle_theme,
            'animations_enabled': self._handle_animations,
            'notifications_enabled': self._handle_notifications,
            'location_services': self._handle_location_services,
            'microphone_access': self._handle_microphone_access,
            'camera_access': self._handle_camera_access,
            'firewall': self._handle_firewall,
            'vpn_enabled': self._handle_vpn,
            'font_size': self._handle_font_size,
            'high_contrast': self._handle_high_contrast,
            'screen_reader': self._handle_screen_reader,
            'system_volume': self._handle_system_volume,
            'dns_private': self._handle_dns_private,
            'telemetry': self._handle_telemetry
        }
    
    async def process_intent(self, user_input: str) -> Intent:
        """Process user input and create intent"""
        self.logger.info(f"Processing intent: {user_input}")
        
        # Normalize input
        normalized_input = user_input.lower().strip()
        
        # Match intent pattern
        matched_intent = self._match_intent_pattern(normalized_input)
        
        if matched_intent:
            intent = await self._create_intent_from_pattern(user_input, matched_intent)
        else:
            # Use AI to interpret custom intent
            intent = await self._interpret_custom_intent(user_input)
        
        # Validate intent feasibility
        await self._validate_intent(intent)
        
        # Generate execution plan
        await self._generate_execution_plan(intent)
        
        return intent
    
    def _match_intent_pattern(self, input_text: str) -> Optional[Dict]:
        """Match input text against known patterns"""
        best_match = None
        best_score = 0
        
        for pattern_name, pattern_data in self.intent_patterns.items():
            score = self._calculate_pattern_score(input_text, pattern_data['keywords'])
            
            if score > best_score and score > 0.6:  # Minimum confidence threshold
                best_score = score
                best_match = {**pattern_data, 'name': pattern_name, 'score': score}
        
        return best_match
    
    def _calculate_pattern_score(self, input_text: str, keywords: List[str]) -> float:
        """Calculate match score between input and keywords"""
        matches = sum(1 for keyword in keywords if keyword in input_text)
        return matches / len(keywords) if keywords else 0
    
    async def _create_intent_from_pattern(self, user_input: str, pattern_data: Dict) -> Intent:
        """Create intent from matched pattern"""
        intent_id = f"intent_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Parse settings from pattern
        parameters = []
        for setting_str in pattern_data['settings']:
            if '=' in setting_str:
                name, value = setting_str.split('=', 1)
                
                # Convert value to appropriate type
                converted_value = self._convert_setting_value(name, value)
                current_value = self._get_current_setting_value(name)
                
                param = SettingParameter(
                    name=name,
                    current_value=current_value,
                    target_value=converted_value,
                    description=self._get_setting_description(name),
                    category=self._get_setting_category(name),
                    impact_level=self._get_setting_impact(name)
                )
                parameters.append(param)
        
        return Intent(
            id=intent_id,
            text=user_input,
            category=pattern_data['category'],
            complexity=pattern_data['complexity'],
            confidence=pattern_data['score'],
            parameters=parameters,
            requires_confirmation=pattern_data['complexity'] in [IntentComplexity.COMPLEX, IntentComplexity.EXPERT]
        )
    
    async def _interpret_custom_intent(self, user_input: str) -> Intent:
        """Interpret custom intent using AI"""
        # This would integrate with the LLM engine
        # For now, return a simple intent
        intent_id = f"intent_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return Intent(
            id=intent_id,
            text=user_input,
            category=IntentCategory.PERFORMANCE,
            complexity=IntentComplexity.SIMPLE,
            confidence=0.5,
            requires_confirmation=True,
            execution_plan=["Analyze custom intent", "Consult AI assistant", "Propose configuration"]
        )
    
    def _convert_setting_value(self, name: str, value: str) -> Any:
        """Convert string value to appropriate type"""
        if value.lower() in ['true', 'false']:
            return value.lower() == 'true'
        elif value.isdigit():
            return int(value)
        elif value.replace('.', '').isdigit():
            return float(value)
        else:
            return value
    
    def _get_current_setting_value(self, name: str) -> Any:
        """Get current value of a setting"""
        return self.system_knowledge['current_settings'].get(name, 'unknown')
    
    def _get_setting_description(self, name: str) -> str:
        """Get human-readable description of setting"""
        descriptions = {
            'power_profile': 'System power management profile',
            'display_brightness': 'Screen brightness level',
            'sleep_timeout': 'Time before system sleeps',
            'wifi_enabled': 'WiFi adapter status',
            'bluetooth_enabled': 'Bluetooth adapter status',
            'theme': 'Visual theme and appearance',
            'animations_enabled': 'UI animations and transitions',
            'notifications_enabled': 'System notifications',
            'location_services': 'GPS and location tracking',
            'microphone_access': 'Microphone access permissions',
            'camera_access': 'Camera access permissions',
            'firewall': 'Network firewall settings',
            'vpn_enabled': 'Virtual private network status',
            'font_size': 'System font size',
            'high_contrast': 'High contrast display mode',
            'screen_reader': 'Text-to-speech screen reader',
            'system_volume': 'Master audio volume',
            'dns_private': 'Private DNS service',
            'telemetry': 'System usage data collection'
        }
        return descriptions.get(name, f'Setting: {name}')
    
    def _get_setting_category(self, name: str) -> str:
        """Get category of setting"""
        categories = {
            'power_profile': 'power',
            'display_brightness': 'display',
            'sleep_timeout': 'power',
            'wifi_enabled': 'network',
            'bluetooth_enabled': 'network',
            'theme': 'display',
            'animations_enabled': 'display',
            'notifications_enabled': 'productivity',
            'location_services': 'privacy',
            'microphone_access': 'privacy',
            'camera_access': 'privacy',
            'firewall': 'security',
            'vpn_enabled': 'security',
            'font_size': 'accessibility',
            'high_contrast': 'accessibility',
            'screen_reader': 'accessibility',
            'system_volume': 'audio',
            'dns_private': 'security',
            'telemetry': 'privacy'
        }
        return categories.get(name, 'general')
    
    def _get_setting_impact(self, name: str) -> str:
        """Get impact level of setting"""
        high_impact = ['power_profile', 'firewall', 'vpn_enabled', 'telemetry']
        medium_impact = ['display_brightness', 'theme', 'animations_enabled', 'notifications_enabled']
        
        if name in high_impact:
            return 'high'
        elif name in medium_impact:
            return 'medium'
        else:
            return 'low'
    
    async def _validate_intent(self, intent: Intent):
        """Validate if intent is feasible"""
        # Check hardware constraints
        if intent.category == IntentCategory.BATTERY:
            if not self.system_knowledge['hardware_capabilities']['battery']['present']:
                intent.confidence *= 0.5
                intent.execution_plan.append("Warning: No battery detected")
        
        # Check system capabilities
        if intent.category == IntentCategory.GAMING:
            gpu = self.system_knowledge['hardware_capabilities']['gpu']
            if not gpu.get('supports_acceleration'):
                intent.confidence *= 0.7
                intent.execution_plan.append("Warning: Limited GPU capabilities")
        
        # Validate each parameter
        for param in intent.parameters:
            if param.current_value == param.target_value:
                intent.execution_plan.append(f"Info: {param.name} already set to desired value")
    
    async def _generate_execution_plan(self, intent: Intent):
        """Generate step-by-step execution plan"""
        if not intent.parameters:
            return
        
        # Group parameters by category and dependency
        execution_steps = []
        
        # Add pre-execution steps
        if intent.complexity in [IntentComplexity.COMPLEX, IntentComplexity.EXPERT]:
            execution_steps.append("Create system backup")
            execution_steps.append("Inform user of changes")
        
        # Add setting-specific steps
        for param in intent.parameters:
            if param.impact_level == 'critical':
                execution_steps.insert(0, f"Critical: Prepare to change {param.name}")
            else:
                execution_steps.append(f"Change {param.name} from {param.current_value} to {param.target_value}")
        
        # Add post-execution steps
        if any(p.requires_restart for p in intent.parameters):
            execution_steps.append("Schedule system restart if needed")
        
        execution_steps.append("Apply new configuration")
        execution_steps.append("Verify changes applied")
        
        intent.execution_plan = execution_steps
        
        # Calculate estimated impact
        high_count = sum(1 for p in intent.parameters if p.impact_level == 'high')
        if high_count > 3:
            intent.estimated_impact = "Major system changes"
        elif high_count > 0:
            intent.estimated_impact = "Moderate changes"
        else:
            intent.estimated_impact = "Minor adjustments"
    
    async def execute_intent(self, intent: Intent) -> Dict[str, Any]:
        """Execute the intent and apply settings"""
        self.logger.info(f"Executing intent: {intent.text}")
        
        results = {
            'success': True,
            'applied_settings': [],
            'failed_settings': [],
            'requires_restart': False,
            'user_messages': []
        }
        
        try:
            # Create backup if complex intent
            if intent.complexity in [IntentComplexity.COMPLEX, IntentComplexity.EXPERT]:
                await self._create_system_backup()
                results['user_messages'].append("System backup created")
            
            # Execute each setting change
            for param in intent.parameters:
                try:
                    handler = self.setting_handlers.get(param.name)
                    if handler:
                        success = await handler(param.current_value, param.target_value)
                        
                        if success:
                            results['applied_settings'].append(param.name)
                            # Update current settings
                            self.system_knowledge['current_settings'][param.name] = param.target_value
                            
                            if param.requires_restart:
                                results['requires_restart'] = True
                        else:
                            results['failed_settings'].append(param.name)
                    else:
                        results['failed_settings'].append(param.name)
                        self.logger.warning(f"No handler for setting: {param.name}")
                
                except Exception as e:
                    results['failed_settings'].append(param.name)
                    self.logger.error(f"Error applying {param.name}: {e}")
            
            # Generate summary
            if results['applied_settings']:
                results['user_messages'].append(f"Successfully applied {len(results['applied_settings'])} settings")
            
            if results['failed_settings']:
                results['success'] = False
                results['user_messages'].append(f"Failed to apply {len(results['failed_settings'])} settings")
            
            if results['requires_restart']:
                results['user_messages'].append("Some changes require a restart to take effect")
        
        except Exception as e:
            results['success'] = False
            results['user_messages'].append(f"Intent execution failed: {str(e)}")
            self.logger.error(f"Intent execution error: {e}")
        
        return results
    
    # Setting handlers
    async def _handle_power_profile(self, current: Any, target: str) -> bool:
        """Handle power profile changes"""
        try:
            # Set power profile using power-profiles-daemon
            import subprocess
            result = subprocess.run(['powerprofilesctl', 'set', target], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    async def _handle_display_brightness(self, current: Any, target: int) -> bool:
        """Handle display brightness changes"""
        try:
            import subprocess
            result = subprocess.run(['brightnessctl', 'set', f'{target}%'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    async def _handle_sleep_timeout(self, current: Any, target: int) -> bool:
        """Handle sleep timeout changes"""
        try:
            # Update systemd logind.conf
            config_path = "/etc/systemd/logind.conf"
            with open(config_path, 'a') as f:
                f.write(f"\n# Aurora OS Intent Setting\nIdleActionSec={target}s\n")
            
            # Restart systemd-logind
            import subprocess
            subprocess.run(['systemctl', 'restart', 'systemd-logind'], 
                          capture_output=True, text=True)
            return True
        except:
            return False
    
    async def _handle_wifi_enabled(self, current: Any, target: bool) -> bool:
        """Handle WiFi enable/disable"""
        try:
            import subprocess
            action = 'enable' if target else 'disable'
            result = subprocess.run(['nmcli', 'radio', 'wifi', action], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    async def _handle_bluetooth_enabled(self, current: Any, target: bool) -> bool:
        """Handle Bluetooth enable/disable"""
        try:
            import subprocess
            action = 'enable' if target else 'disable'
            result = subprocess.run(['rfkill', 'block' if not target else 'unblock', 'bluetooth'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    async def _handle_theme(self, current: Any, target: str) -> bool:
        """Handle theme changes"""
        try:
            # Update theme settings
            theme_config = Path.home() / ".config" / "aurora" / "theme.json"
            theme_config.parent.mkdir(parents=True, exist_ok=True)
            
            with open(theme_config, 'w') as f:
                json.dump({'theme': target}, f)
            
            return True
        except:
            return False
    
    async def _handle_animations(self, current: Any, target: bool) -> bool:
        """Handle animation settings"""
        try:
            # Update GNOME settings (if using GNOME)
            import subprocess
            value = 'true' if target else 'false'
            result = subprocess.run(['gsettings', 'set', 'org.gnome.desktop.interface', 
                                   'enable-animations', value], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    async def _handle_notifications(self, current: Any, target: bool) -> bool:
        """Handle notification settings"""
        try:
            # Update notification daemon settings
            config_path = Path.home() / ".config" / "aurora" / "notifications.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w') as f:
                json.dump({'enabled': target}, f)
            
            return True
        except:
            return False
    
    async def _handle_location_services(self, current: Any, target: bool) -> bool:
        """Handle location services"""
        try:
            # Update geoclue settings
            import subprocess
            action = 'enable' if target else 'disable'
            result = subprocess.run(['systemctl', '--user', f'{action}', 'geoclue.service'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    async def _handle_microphone_access(self, current: Any, target: str) -> bool:
        """Handle microphone access permissions"""
        try:
            config_path = Path.home() / ".config" / "aurora" / "privacy.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w') as f:
                json.dump({'microphone': target}, f)
            
            return True
        except:
            return False
    
    async def _handle_camera_access(self, current: Any, target: str) -> bool:
        """Handle camera access permissions"""
        try:
            config_path = Path.home() / ".config" / "aurora" / "privacy.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing config if present
            config = {}
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
            
            config['camera'] = target
            
            with open(config_path, 'w') as f:
                json.dump(config, f)
            
            return True
        except:
            return False
    
    async def _handle_firewall(self, current: Any, target: str) -> bool:
        """Handle firewall settings"""
        try:
            import subprocess
            
            if target == 'strict':
                # Set up strict firewall rules
                subprocess.run(['ufw', '--force', 'reset'], capture_output=True)
                subprocess.run(['ufw', 'default', 'deny', 'incoming'], capture_output=True)
                subprocess.run(['ufw', 'default', 'allow', 'outgoing'], capture_output=True)
                subprocess.run(['ufw', '--force', 'enable'], capture_output=True)
            elif target == 'off':
                subprocess.run(['ufw', '--force', 'disable'], capture_output=True)
            
            return True
        except:
            return False
    
    async def _handle_vpn(self, current: Any, target: bool) -> bool:
        """Handle VPN settings"""
        try:
            import subprocess
            action = 'up' if target else 'down'
            result = subprocess.run(['nmcli', 'connection', action, 'aurora-vpn'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    async def _handle_font_size(self, current: Any, target: str) -> bool:
        """Handle font size changes"""
        try:
            import subprocess
            result = subprocess.run(['gsettings', 'set', 'org.gnome.desktop.interface', 
                                   'text-scaling-factor', 
                                   '1.5' if target == 'large' else '1.0'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    async def _handle_high_contrast(self, current: Any, target: bool) -> bool:
        """Handle high contrast mode"""
        try:
            import subprocess
            value = 'true' if target else 'false'
            result = subprocess.run(['gsettings', 'set', 'org.gnome.desktop.a11y.interface', 
                                   'high-contrast', value], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    async def _handle_screen_reader(self, current: Any, target: bool) -> bool:
        """Handle screen reader settings"""
        try:
            import subprocess
            action = 'enable' if target else 'disable'
            result = subprocess.run(['systemctl', '--user', f'{action}', 'orca.service'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    async def _handle_system_volume(self, current: Any, target: int) -> bool:
        """Handle system volume"""
        try:
            import subprocess
            result = subprocess.run(['amixer', 'set', 'Master', f'{target}%'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    async def _handle_dns_private(self, current: Any, target: bool) -> bool:
        """Handle private DNS settings"""
        try:
            import subprocess
            if target:
                # Set to known private DNS provider
                result = subprocess.run(['networksetup', '-setdnsservers', 'Wi-Fi', '1.1.1.1'], 
                                      capture_output=True, text=True)
            else:
                # Reset to default
                result = subprocess.run(['networksetup', '-setdnsservers', 'Wi-Fi', 'Empty'], 
                                      capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    async def _handle_telemetry(self, current: Any, target: bool) -> bool:
        """Handle telemetry settings"""
        try:
            config_path = Path("/etc/aurora/telemetry.conf")
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w') as f:
                f.write(f"enabled={target}\n")
            
            return True
        except:
            return False
    
    async def _create_system_backup(self):
        """Create system backup before major changes"""
        try:
            backup_dir = Path("/var/backups/aurora")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_dir / f"intent_backup_{timestamp}.tar.gz"
            
            import subprocess
            subprocess.run(['tar', 'czf', str(backup_file), 
                          '/etc/systemd/logind.conf', 
                          '/home/*/.config/aurora'], 
                          capture_output=True)
            
            self.logger.info(f"System backup created: {backup_file}")
        except Exception as e:
            self.logger.error(f"Backup creation failed: {e}")
    
    def get_suggested_intents(self) -> List[str]:
        """Get suggested intents based on current system state"""
        suggestions = []
        
        # Battery optimization suggestions
        if self.system_knowledge['hardware_capabilities']['battery']['present']:
            if self.system_knowledge['current_settings']['display_brightness'] > 70:
                suggestions.append("Optimize for longer battery life")
        
        # Performance suggestions
        if self.system_knowledge['current_settings']['power_profile'] == 'balanced':
            suggestions.append("Boost performance for intensive tasks")
        
        # Privacy suggestions
        if self.system_knowledge['current_settings']['location_services']:
            suggestions.append("Enhance privacy and security")
        
        return suggestions

# Global intent engine instance
_intent_engine = None

def get_intent_engine() -> IntentEngine:
    """Get global intent engine instance"""
    global _intent_engine
    if _intent_engine is None:
        _intent_engine = IntentEngine()
    return _intent_engine