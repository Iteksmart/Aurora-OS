#!/usr/bin/env python3
"""
Simple test suite for Aurora OS improvements without heavy dependencies.
Tests core functionality of Aurora Modes, Guardian, and Intent Engine.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class TestAuroraModesSimple:
    """Test Aurora Modes system - simple tests."""
    
    def test_mode_creation(self):
        """Test mode creation and basic functionality."""
        from system.core.aurora_modes import AuroraModeManager, AuroraMode
        
        mode_manager = AuroraModeManager("/tmp/test_modes_simple.json")
        
        # Test initialization
        assert mode_manager.current_mode == AuroraMode.PERSONAL
        assert len(mode_manager.mode_configs) == 4
        
        # Test mode switching
        success = mode_manager.switch_mode(AuroraMode.ENTERPRISE, "Test switch")
        assert success == True
        assert mode_manager.current_mode == AuroraMode.ENTERPRISE
        
        # Test security levels
        personal_security = mode_manager.get_security_level(AuroraMode.PERSONAL)
        enterprise_security = mode_manager.get_security_level(AuroraMode.ENTERPRISE)
        
        assert enterprise_security > personal_security
    
    def test_mode_configurations(self):
        """Test mode configurations are properly set."""
        from system.core.aurora_modes import AuroraModeManager, AuroraMode
        
        mode_manager = AuroraModeManager("/tmp/test_modes_config.json")
        
        # Enterprise mode should have strict security
        enterprise_config = mode_manager.get_mode_config(AuroraMode.ENTERPRISE)
        assert enterprise_config.firewall_rules == "strict"
        assert enterprise_config.animations_enabled == False
        
        # Developer mode should have debugging enabled
        developer_config = mode_manager.get_mode_config(AuroraMode.DEVELOPER)
        assert developer_config.debugging_enabled == True
        assert developer_config.developer_tools == True

class TestAuroraGuardianSimple:
    """Test Aurora Guardian security framework - simple tests."""
    
    def test_guardian_initialization(self):
        """Test Guardian initialization."""
        from system.security.aurora_guardian import AuroraGuardian, DriverSource
        
        guardian = AuroraGuardian("/tmp/test_guardian_simple.json")
        
        # Test basic properties
        assert hasattr(guardian, 'driver_database')
        assert hasattr(guardian, 'security_decisions')
        assert hasattr(guardian, 'compliance_rules')
        
        # Test driver database has entries
        assert len(guardian.driver_database) > 0
        
        # Check driver info structure
        intel_driver = guardian.driver_database.get("0001:8086:1234")
        if intel_driver:
            assert intel_driver.source == DriverSource.UPSTREAM_KERNEL
            assert intel_driver.recommended == True
    
    def test_driver_safety_verification(self):
        """Test driver safety verification."""
        from system.security.aurora_guardian import AuroraGuardian
        
        guardian = AuroraGuardian("/tmp/test_guardian_safety.json")
        
        # Test known safe drivers
        intel_safety = guardian._verify_driver_safety("0001:8086:1234", "i915")
        assert intel_safety["safe"] == True
        
        nvidia_safety = guardian._verify_driver_safety("0002:10de:5678", "nvidia")
        assert nvidia_safety["safe"] == True
        
        # Test unknown driver
        unknown_safety = guardian._verify_driver_safety("unknown", "unknown_driver")
        assert unknown_safety["safe"] == False
    
    def test_security_status(self):
        """Test security status reporting."""
        from system.security.aurora_guardian import AuroraGuardian
        
        guardian = AuroraGuardian("/tmp/test_guardian_status.json")
        
        status = guardian.get_security_status()
        
        # Check required fields
        assert "security_level" in status
        assert "total_decisions" in status
        assert "compliance_status" in status
        assert "recommendations" in status

class TestAuroraIntentEngineSimple:
    """Test Aurora Intent Engine - simple tests."""
    
    def test_engine_initialization(self):
        """Test AIE initialization without heavy models."""
        # Mock the AI models to avoid heavy dependencies
        import sys
        from unittest.mock import Mock
        
        # Mock spacy and transformers
        sys.modules['spacy'] = Mock()
        sys.modules['transformers'] = Mock()
        
        from system.ai_control_plane.aurora_intent_engine import AuroraIntentEngine
        
        engine = AuroraIntentEngine("/tmp/test_intent_simple.json")
        
        # Test basic properties
        assert hasattr(engine, 'config')
        assert hasattr(engine, 'intents_history')
        assert hasattr(engine, 'decisions_history')
        assert hasattr(engine, 'active_sessions')
        
        # Check configuration
        assert "confidence_threshold" in engine.config
        assert "intent_patterns" in engine.config
    
    def test_rule_based_classification(self):
        """Test rule-based intent classification."""
        # Mock the AI models
        import sys
        from unittest.mock import Mock
        
        sys.modules['spacy'] = Mock()
        sys.modules['transformers'] = Mock()
        
        from system.ai_control_plane.aurora_intent_engine import AuroraIntentEngine, IntentType
        
        engine = AuroraIntentEngine("/tmp/test_intent_classification.json")
        
        # Test application opening
        text = "open firefox"
        entities = {"applications": ["firefox"]}
        intent_type, confidence = engine._classify_intent_rule_based(text, entities)
        
        assert intent_type == IntentType.OPEN_APPLICATION
        assert confidence == 0.9
        
        # Test settings configuration
        text = "configure battery settings"
        entities = {"settings": ["battery"]}
        intent_type, confidence = engine._classify_intent_rule_based(text, entities)
        
        assert intent_type == IntentType.SYSTEM_SETTINGS
        assert confidence == 0.8
    
    def test_entity_extraction(self):
        """Test entity extraction."""
        # Mock the AI models
        import sys
        from unittest.mock import Mock
        
        sys.modules['spacy'] = Mock()
        sys.modules['transformers'] = Mock()
        
        from system.ai_control_plane.aurora_intent_engine import AuroraIntentEngine
        
        engine = AuroraIntentEngine("/tmp/test_intent_entities.json")
        
        text = "Open firefox and configure battery settings"
        entities = engine._extract_entities_rule_based(text)
        
        assert "applications" in entities
        assert "firefox" in entities["applications"]
        assert "settings" in entities
        assert "battery" in entities["settings"]
    
    def test_action_plan_generation(self):
        """Test action plan generation."""
        # Mock the AI models
        import sys
        from unittest.mock import Mock
        
        sys.modules['spacy'] = Mock()
        sys.modules['transformers'] = Mock()
        
        from system.ai_control_plane.aurora_intent_engine import AuroraIntentEngine, IntentType
        
        engine = AuroraIntentEngine("/tmp/test_intent_actions.json")
        
        # Test open application action plan
        entities = {"applications": ["firefox"]}
        action_plan = engine._generate_action_plan(IntentType.OPEN_APPLICATION, entities)
        
        assert len(action_plan) == 1
        assert action_plan[0]["action"] == "launch_application"
        assert action_plan[0]["parameters"]["app_name"] == "firefox"

class TestIntegrationSimple:
    """Integration tests for Aurora improvements."""
    
    def test_mode_guardian_integration(self):
        """Test integration between Aurora Modes and Guardian."""
        from system.core.aurora_modes import AuroraModeManager, AuroraMode
        from system.security.aurora_guardian import AuroraGuardian
        
        mode_manager = AuroraModeManager("/tmp/test_integration_modes.json")
        guardian = AuroraGuardian("/tmp/test_integration_guardian.json")
        
        # Switch to enterprise mode
        mode_manager.switch_mode(AuroraMode.ENTERPRISE, "Security test")
        
        # Guardian should provide security status
        security_status = guardian.get_security_status()
        assert "security_level" in security_status
        assert "compliance_status" in security_status
    
    def test_components_exist(self):
        """Test that all Aurora components exist and can be imported."""
        
        # Test Aurora Modes
        from system.core.aurora_modes import AuroraModeManager, AuroraMode
        assert AuroraModeManager is not None
        assert AuroraMode is not None
        
        # Test Aurora Guardian
        from system.security.aurora_guardian import AuroraGuardian, SecurityDecision
        assert AuroraGuardian is not None
        assert SecurityDecision is not None
        
        # Test Aurora Intent Engine (mock dependencies)
        import sys
        from unittest.mock import Mock
        sys.modules['spacy'] = Mock()
        sys.modules['transformers'] = Mock()
        
        from system.ai_control_plane.aurora_intent_engine import AuroraIntentEngine, IntentType
        assert AuroraIntentEngine is not None
        assert IntentType is not None

if __name__ == "__main__":
    # Run simple tests
    pytest.main([__file__, "-v"])