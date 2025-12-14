#!/usr/bin/env python3
"""
Aurora Modes System
Implements different operating modes for Aurora OS with varying security postures,
UI densities, and AI autonomy levels.
"""

import enum
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

class AuroraMode(enum.Enum):
    """Aurora OS operating modes with different security and functionality levels."""
    
    PERSONAL = "personal"
    ENTERPRISE = "enterprise"
    DEVELOPER = "developer"
    LOCKED_DOWN = "locked_down"

@dataclass
class ModeConfiguration:
    """Configuration for a specific Aurora mode."""
    
    # Security Settings
    firewall_rules: str = "balanced"
    app_sandboxing: str = "moderate"
    data_encryption: bool = True
    biometric_auth: bool = False
    network_isolation: bool = False
    
    # UI Settings
    ui_density: str = "normal"  # compact, normal, spacious
    animations_enabled: bool = True
    transparency_effects: bool = True
    advanced_controls_visible: bool = False
    
    # AI Settings
    ai_autonomy_level: str = "moderate"  # conservative, moderate, aggressive
    proactive_suggestions: bool = True
    voice_commands: bool = True
    contextual_automation: bool = True
    
    # System Settings
    automatic_updates: bool = True
    telemetry_level: str = "minimal"  # none, minimal, full
    debugging_enabled: bool = False
    developer_tools: bool = False
    
    # Network Settings
    auto_wifi_connect: bool = True
    bluetooth_enabled: bool = True
    file_sharing: bool = False
    remote_access: bool = False

class AuroraModeManager:
    """Manages Aurora OS operating modes and transitions."""
    
    def __init__(self, config_path: str = "/etc/aurora/modes.json"):
        self.config_path = Path(config_path)
        self.current_mode = AuroraMode.PERSONAL
        self.mode_configs = self._load_default_configs()
        self.mode_history: List[Dict[str, Any]] = []
        
    def _load_default_configs(self) -> Dict[AuroraMode, ModeConfiguration]:
        """Load default mode configurations."""
        
        configs = {
            AuroraMode.PERSONAL: ModeConfiguration(
                firewall_rules="balanced",
                app_sandboxing="moderate",
                data_encryption=True,
                biometric_auth=True,
                network_isolation=False,
                ui_density="normal",
                animations_enabled=True,
                transparency_effects=True,
                advanced_controls_visible=False,
                ai_autonomy_level="moderate",
                proactive_suggestions=True,
                voice_commands=True,
                contextual_automation=True,
                automatic_updates=True,
                telemetry_level="minimal",
                debugging_enabled=False,
                developer_tools=False,
                auto_wifi_connect=True,
                bluetooth_enabled=True,
                file_sharing=True,
                remote_access=False
            ),
            
            AuroraMode.ENTERPRISE: ModeConfiguration(
                firewall_rules="strict",
                app_sandboxing="strict",
                data_encryption=True,
                biometric_auth=True,
                network_isolation=True,
                ui_density="normal",
                animations_enabled=False,
                transparency_effects=False,
                advanced_controls_visible=True,
                ai_autonomy_level="conservative",
                proactive_suggestions=False,
                voice_commands=False,
                contextual_automation=False,
                automatic_updates=False,
                telemetry_level="full",
                debugging_enabled=False,
                developer_tools=False,
                auto_wifi_connect=False,
                bluetooth_enabled=False,
                file_sharing=False,
                remote_access=True
            ),
            
            AuroraMode.DEVELOPER: ModeConfiguration(
                firewall_rules="permissive",
                app_sandboxing="minimal",
                data_encryption=False,
                biometric_auth=False,
                network_isolation=False,
                ui_density="compact",
                animations_enabled=False,
                transparency_effects=False,
                advanced_controls_visible=True,
                ai_autonomy_level="aggressive",
                proactive_suggestions=True,
                voice_commands=True,
                contextual_automation=True,
                automatic_updates=False,
                telemetry_level="minimal",
                debugging_enabled=True,
                developer_tools=True,
                auto_wifi_connect=True,
                bluetooth_enabled=True,
                file_sharing=True,
                remote_access=True
            ),
            
            AuroraMode.LOCKED_DOWN: ModeConfiguration(
                firewall_rules="strict",
                app_sandboxing="strict",
                data_encryption=True,
                biometric_auth=True,
                network_isolation=True,
                ui_density="spacious",
                animations_enabled=False,
                transparency_effects=False,
                advanced_controls_visible=False,
                ai_autonomy_level="conservative",
                proactive_suggestions=False,
                voice_commands=False,
                contextual_automation=False,
                automatic_updates=False,
                telemetry_level="none",
                debugging_enabled=False,
                developer_tools=False,
                auto_wifi_connect=False,
                bluetooth_enabled=False,
                file_sharing=False,
                remote_access=False
            )
        }
        
        return configs
    
    def get_current_mode(self) -> AuroraMode:
        """Get the current operating mode."""
        return self.current_mode
    
    def get_mode_config(self, mode: AuroraMode) -> ModeConfiguration:
        """Get configuration for a specific mode."""
        return self.mode_configs.get(mode, self.mode_configs[AuroraMode.PERSONAL])
    
    def get_current_config(self) -> ModeConfiguration:
        """Get configuration for the current mode."""
        return self.get_mode_config(self.current_mode)
    
    def switch_mode(self, new_mode: AuroraMode, reason: str = "User request") -> bool:
        """Switch to a new operating mode."""
        
        if new_mode == self.current_mode:
            logger.info(f"Already in {new_mode.value} mode")
            return True
        
        old_config = self.get_current_config()
        new_config = self.get_mode_config(new_mode)
        
        # Record mode change
        self.mode_history.append({
            "timestamp": self._get_timestamp(),
            "old_mode": self.current_mode.value,
            "new_mode": new_mode.value,
            "reason": reason,
            "old_config": asdict(old_config),
            "new_config": asdict(new_config)
        })
        
        logger.info(f"Switching from {self.current_mode.value} to {new_mode.value} mode: {reason}")
        
        # Apply new configuration
        success = self._apply_mode_configuration(new_config)
        
        if success:
            self.current_mode = new_mode
            logger.info(f"Successfully switched to {new_mode.value} mode")
            self._save_mode_history()
        else:
            logger.error(f"Failed to switch to {new_mode.value} mode")
            # Revert to old mode
            self._apply_mode_configuration(old_config)
        
        return success
    
    def _apply_mode_configuration(self, config: ModeConfiguration) -> bool:
        """Apply mode configuration to the system."""
        
        try:
            # Apply security settings
            self._apply_security_settings(config)
            
            # Apply UI settings
            self._apply_ui_settings(config)
            
            # Apply AI settings
            self._apply_ai_settings(config)
            
            # Apply system settings
            self._apply_system_settings(config)
            
            # Apply network settings
            self._apply_network_settings(config)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply mode configuration: {e}")
            return False
    
    def _apply_security_settings(self, config: ModeConfiguration):
        """Apply security-related settings."""
        
        logger.info(f"Applying security settings: firewall={config.firewall_rules}, sandboxing={config.app_sandboxing}")
        
        # Firewall rules
        if config.firewall_rules == "strict":
            self._set_strict_firewall()
        elif config.firewall_rules == "balanced":
            self._set_balanced_firewall()
        elif config.firewall_rules == "permissive":
            self._set_permissive_firewall()
        
        # App sandboxing
        if config.app_sandboxing == "strict":
            self._enable_strict_sandboxing()
        elif config.app_sandboxing == "moderate":
            self._enable_moderate_sandboxing()
        elif config.app_sandboxing == "minimal":
            self._enable_minimal_sandboxing()
        
        # Data encryption
        if config.data_encryption:
            self._enable_full_disk_encryption()
        else:
            self._disable_additional_encryption()
        
        # Network isolation
        if config.network_isolation:
            self._enable_network_isolation()
        else:
            self._disable_network_isolation()
    
    def _apply_ui_settings(self, config: ModeConfiguration):
        """Apply UI-related settings."""
        
        logger.info(f"Applying UI settings: density={config.ui_density}, animations={config.animations_enabled}")
        
        # UI density
        self._set_ui_density(config.ui_density)
        
        # Animations
        self._set_animations_enabled(config.animations_enabled)
        
        # Transparency effects
        self._set_transparency_effects(config.transparency_effects)
        
        # Advanced controls visibility
        self._set_advanced_controls_visibility(config.advanced_controls_visible)
    
    def _apply_ai_settings(self, config: ModeConfiguration):
        """Apply AI-related settings."""
        
        logger.info(f"Applying AI settings: autonomy={config.ai_autonomy_level}, suggestions={config.proactive_suggestions}")
        
        # AI autonomy level
        self._set_ai_autonomy_level(config.ai_autonomy_level)
        
        # Proactive suggestions
        self._set_proactive_suggestions(config.proactive_suggestions)
        
        # Voice commands
        self._set_voice_commands_enabled(config.voice_commands)
        
        # Contextual automation
        self._set_contextual_automation(config.contextual_automation)
    
    def _apply_system_settings(self, config: ModeConfiguration):
        """Apply system-related settings."""
        
        logger.info(f"Applying system settings: updates={config.automatic_updates}, telemetry={config.telemetry_level}")
        
        # Automatic updates
        self._set_automatic_updates(config.automatic_updates)
        
        # Telemetry level
        self._set_telemetry_level(config.telemetry_level)
        
        # Debugging
        self._set_debugging_enabled(config.debugging_enabled)
        
        # Developer tools
        self._set_developer_tools_enabled(config.developer_tools)
    
    def _apply_network_settings(self, config: ModeConfiguration):
        """Apply network-related settings."""
        
        logger.info(f"Applying network settings: wifi={config.auto_wifi_connect}, bluetooth={config.bluetooth_enabled}")
        
        # Auto Wi-Fi connect
        self._set_auto_wifi_connect(config.auto_wifi_connect)
        
        # Bluetooth
        self._set_bluetooth_enabled(config.bluetooth_enabled)
        
        # File sharing
        self._set_file_sharing_enabled(config.file_sharing)
        
        # Remote access
        self._set_remote_access_enabled(config.remote_access)
    
    # Placeholder methods for actual system integration
    def _set_strict_firewall(self): pass
    def _set_balanced_firewall(self): pass
    def _set_permissive_firewall(self): pass
    def _enable_strict_sandboxing(self): pass
    def _enable_moderate_sandboxing(self): pass
    def _enable_minimal_sandboxing(self): pass
    def _enable_full_disk_encryption(self): pass
    def _disable_additional_encryption(self): pass
    def _enable_network_isolation(self): pass
    def _disable_network_isolation(self): pass
    def _set_ui_density(self, density): pass
    def _set_animations_enabled(self, enabled): pass
    def _set_transparency_effects(self, enabled): pass
    def _set_advanced_controls_visibility(self, visible): pass
    def _set_ai_autonomy_level(self, level): pass
    def _set_proactive_suggestions(self, enabled): pass
    def _set_voice_commands_enabled(self, enabled): pass
    def _set_contextual_automation(self, enabled): pass
    def _set_automatic_updates(self, enabled): pass
    def _set_telemetry_level(self, level): pass
    def _set_debugging_enabled(self, enabled): pass
    def _set_developer_tools_enabled(self, enabled): pass
    def _set_auto_wifi_connect(self, enabled): pass
    def _set_bluetooth_enabled(self, enabled): pass
    def _set_file_sharing_enabled(self, enabled): pass
    def _set_remote_access_enabled(self, enabled): pass
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _save_mode_history(self):
        """Save mode history to file."""
        try:
            history_file = self.config_path.parent / "mode_history.json"
            with open(history_file, 'w') as f:
                json.dump(self.mode_history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save mode history: {e}")
    
    def get_mode_info(self) -> Dict[str, Any]:
        """Get information about current mode and available modes."""
        
        return {
            "current_mode": self.current_mode.value,
            "current_config": asdict(self.get_current_config()),
            "available_modes": [mode.value for mode in AuroraMode],
            "mode_descriptions": {
                AuroraMode.PERSONAL.value: "Balanced mode for personal use with AI assistance",
                AuroraMode.ENTERPRISE.value: "Secure mode for corporate environments with policy enforcement",
                AuroraMode.DEVELOPER.value: "Open mode for development with debugging tools",
                AuroraMode.LOCKED_DOWN.value: "Maximum security mode for sensitive operations"
            },
            "recent_changes": self.mode_history[-5:] if self.mode_history else []
        }
    
    def is_transition_allowed(self, from_mode: AuroraMode, to_mode: AuroraMode) -> bool:
        """Check if transition between modes is allowed."""
        
        # In enterprise environment, some transitions might require admin approval
        if from_mode == AuroraMode.ENTERPRISE and to_mode in [AuroraMode.DEVELOPER, AuroraMode.LOCKED_DOWN]:
            return False  # Requires admin approval
        
        # Locked down mode requires authentication to exit
        if from_mode == AuroraMode.LOCKED_DOWN and to_mode != AuroraMode.ENTERPRISE:
            return False  # Requires elevated authentication
        
        return True
    
    def get_security_level(self, mode: AuroraMode) -> int:
        """Get security level for a mode (1-10, where 10 is most secure)."""
        
        security_levels = {
            AuroraMode.PERSONAL: 6,
            AuroraMode.ENTERPRISE: 9,
            AuroraMode.DEVELOPER: 3,
            AuroraMode.LOCKED_DOWN: 10
        }
        
        return security_levels.get(mode, 6)