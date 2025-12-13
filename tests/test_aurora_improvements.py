#!/usr/bin/env python3
"""
Test suite for Aurora OS improvements including:
- Aurora Modes system
- Aurora Guardian security framework  
- Aurora Intent Engine (AIE)
"""

import asyncio
import pytest
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from system.core.aurora_modes import AuroraModeManager, AuroraMode
from system.security.aurora_guardian import AuroraGuardian, SecurityDecision, DriverSource
from system.ai_control_plane.aurora_intent_engine import AuroraIntentEngine, IntentType

class TestAuroraModes:
    """Test Aurora Modes system."""
    
    def setup_method(self):
        """Setup test environment."""
        self.mode_manager = AuroraModeManager("/tmp/test_aurora_modes.json")
    
    def test_mode_initialization(self):
        """Test mode manager initialization."""
        assert self.mode_manager.current_mode == AuroraMode.PERSONAL
        assert len(self.mode_manager.mode_configs) == 4
        
        # Check all modes are available
        for mode in AuroraMode:
            assert mode in self.mode_manager.mode_configs
    
    def test_mode_configurations(self):
        """Test mode configurations."""
        
        # Personal mode should have balanced settings
        personal_config = self.mode_manager.get_mode_config(AuroraMode.PERSONAL)
        assert personal_config.ui_density == "normal"
        assert personal_config.animations_enabled == True
        assert personal_config.ai_autonomy_level == "moderate"
        
        # Enterprise mode should have strict security
        enterprise_config = self.mode_manager.get_mode_config(AuroraMode.ENTERPRISE)
        assert enterprise_config.firewall_rules == "strict"
        assert enterprise_config.animations_enabled == False
        assert enterprise_config.ai_autonomy_level == "conservative"
        assert enterprise_config.network_isolation == True
        
        # Developer mode should have open settings
        developer_config = self.mode_manager.get_mode_config(AuroraMode.DEVELOPER)
        assert developer_config.firewall_rules == "permissive"
        assert developer_config.debugging_enabled == True
        assert developer_config.developer_tools == True
        
        # Locked down mode should have maximum security
        locked_config = self.mode_manager.get_mode_config(AuroraMode.LOCKED_DOWN)
        assert locked_config.firewall_rules == "strict"
        assert locked_config.telemetry_level == "none"
        assert locked_config.bluetooth_enabled == False
    
    def test_mode_switching(self):
        """Test mode switching."""
        
        # Switch to enterprise mode
        success = self.mode_manager.switch_mode(AuroraMode.ENTERPRISE, "Test switch")
        assert success == True
        assert self.mode_manager.current_mode == AuroraMode.ENTERPRISE
        
        # Verify configuration changed
        current_config = self.mode_manager.get_current_config()
        assert current_config.firewall_rules == "strict"
        assert current_config.animations_enabled == False
        
        # Switch to developer mode
        success = self.mode_manager.switch_mode(AuroraMode.DEVELOPER, "Testing")
        assert success == True
        assert self.mode_manager.current_mode == AuroraMode.DEVELOPER
        
        # Verify developer settings
        current_config = self.mode_manager.get_current_config()
        assert current_config.debugging_enabled == True
        assert current_config.developer_tools == True
    
    def test_mode_info(self):
        """Test mode information retrieval."""
        
        info = self.mode_manager.get_mode_info()
        
        assert "current_mode" in info
        assert "current_config" in info
        assert "available_modes" in info
        assert "mode_descriptions" in info
        assert "recent_changes" in info
        
        # Check all modes are listed
        for mode in AuroraMode:
            assert mode.value in info["available_modes"]
        
        # Check descriptions exist
        assert len(info["mode_descriptions"]) == 4
    
    def test_security_levels(self):
        """Test security level calculation."""
        
        personal_security = self.mode_manager.get_security_level(AuroraMode.PERSONAL)
        enterprise_security = self.mode_manager.get_security_level(AuroraMode.ENTERPRISE)
        developer_security = self.mode_manager.get_security_level(AuroraMode.DEVELOPER)
        locked_security = self.mode_manager.get_security_level(AuroraMode.LOCKED_DOWN)
        
        assert personal_security == 6
        assert enterprise_security == 9
        assert developer_security == 3
        assert locked_security == 10
        
        # Security levels should be ordered correctly
        assert locked_security > enterprise_security > personal_security > developer_security
    
    def test_transition_allowed(self):
        """Test mode transition rules."""
        
        # Personal to enterprise should be allowed
        assert self.mode_manager.is_transition_allowed(AuroraMode.PERSONAL, AuroraMode.ENTERPRISE) == True
        
        # Enterprise to developer should be restricted (requires admin)
        assert self.mode_manager.is_transition_allowed(AuroraMode.ENTERPRISE, AuroraMode.DEVELOPER) == False
        
        # Locked down to personal should be restricted (requires elevated auth)
        assert self.mode_manager.is_transition_allowed(AuroraMode.LOCKED_DOWN, AuroraMode.PERSONAL) == False

class TestAuroraGuardian:
    """Test Aurora Guardian security framework."""
    
    def setup_method(self):
        """Setup test environment."""
        self.guardian = AuroraGuardian("/tmp/test_aurora_guardian.json")
    
    def test_guardian_initialization(self):
        """Test Guardian initialization."""
        assert self.guardian.config_path.name == "test_aurora_guardian.json"
        assert len(self.guardian.driver_database) > 0
        assert len(self.guardian.compliance_rules) > 0
        assert len(self.guardian.security_decisions) == 0
    
    def test_driver_database_initialization(self):
        """Test driver database initialization."""
        
        # Check sample drivers are loaded
        assert "0001:8086:1234" in self.guardian.driver_database  # Intel GPU
        assert "0002:10de:5678" in self.guardian.driver_database  # NVIDIA GPU
        
        # Check driver info structure
        intel_driver = self.guardian.driver_database["0001:8086:1234"]
        assert intel_driver.device_name == "Intel Graphics Controller"
        assert intel_driver.source == DriverSource.UPSTREAM_KERNEL
        assert intel_driver.recommended == True
        assert intel_driver.ai_recommendation is not None
    
    def test_hardware_scanning(self):
        """Test hardware scanning functionality."""
        
        # Mock lspci and lsusb commands
        with patch('subprocess.run') as mock_run:
            # Mock lspci output
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "00:02.0 VGA compatible controller [0300]: Intel Corporation Device [8086:1234]\n"
            
            devices = self.guardian.scan_hardware()
            
            # Should find the Intel GPU
            assert len(devices) > 0
            intel_device = None
            for device in devices:
                if "8086:1234" in device.device_id:
                    intel_device = device
                    break
            
            assert intel_device is not None
            assert intel_device.vendor_id == "8086"
    
    def test_driver_recommendations(self):
        """Test AI-powered driver recommendations."""
        
        # Mock hardware scan
        with patch.object(self.guardian, 'scan_hardware') as mock_scan:
            mock_devices = [
                self.guardian.driver_database["0001:8086:1234"],  # Recommended Intel driver
                self.guardian.driver_database["0002:10de:5678"]   # Recommended NVIDIA driver
            ]
            mock_scan.return_value = mock_devices
            
            recommendations = self.guardian.get_driver_recommendations()
            
            assert len(recommendations) >= 2
            
            # Check that recommended drivers are included
            intel_found = False
            nvidia_found = False
            
            for rec in recommendations:
                if "8086:1234" in rec.device_id:
                    intel_found = True
                elif "10de:5678" in rec.device_id:
                    nvidia_found = True
            
            assert intel_found
            assert nvidia_found
    
    def test_driver_safety_verification(self):
        """Test driver safety verification."""
        
        # Test safe drivers
        intel_safety = self.guardian._verify_driver_safety("0001:8086:1234", "i915")
        assert intel_safety["safe"] == True
        assert "upstream kernel" in intel_safety["ai_reasoning"]
        
        nvidia_safety = self.guardian._verify_driver_safety("0002:10de:5678", "nvidia")
        assert nvidia_safety["safe"] == True
        # The exact wording might vary, just check it contains the right info
        assert "vendor" in nvidia_safety["ai_reasoning"].lower() or "proprietary" in nvidia_safety["ai_reasoning"].lower()
        
        # Test unknown driver
        unknown_safety = self.guardian._verify_driver_safety("unknown", "unknown_driver")
        assert unknown_safety["safe"] == False
        assert "insufficient safety data" in unknown_safety["reason"]
    
    def test_security_decision_logging(self):
        """Test security decision logging."""
        
        initial_count = len(self.guardian.security_decisions)
        
        self.guardian._log_security_decision(
            action="block",
            target="driver_installation",
            target_id="test_device",
            reason="Test decision",
            confidence=0.8,
            ai_reasoning="Test AI reasoning"
        )
        
        # Should have one more decision
        assert len(self.guardian.security_decisions) == initial_count + 1
        
        # Check decision details
        latest_decision = self.guardian.security_decisions[-1]
        assert latest_decision.action == "block"
        assert latest_decision.target == "driver_installation"
        assert latest_decision.confidence == 0.8
        assert latest_decision.ai_reasoning == "Test AI reasoning"
    
    def test_security_status(self):
        """Test security status reporting."""
        
        # Add some test decisions
        self.guardian._log_security_decision("allow", "test", "test1", "test", 0.9, "test")
        self.guardian._log_security_decision("block", "test", "test2", "test", 0.8, "test")
        self.guardian._log_security_decision("allow", "test", "test3", "test", 0.7, "test")
        
        status = self.guardian.get_security_status()
        
        assert "security_level" in status
        assert "total_decisions" in status
        assert "blocked_actions" in status
        assert "allowed_actions" in status
        assert "compliance_status" in status
        assert "recommendations" in status
        
        # Check counts
        assert status["blocked_actions"] == 1
        assert status["allowed_actions"] == 2
        assert status["total_decisions"] == 3
    
    def test_explainable_security_decisions(self):
        """Test explainable security decision feature."""
        
        # Log a test decision
        self.guardian._log_security_decision(
            action="block",
            target="driver_installation",
            target_id="test_device",
            reason="Safety concern",
            confidence=0.85,
            ai_reasoning="Driver not verified for security"
        )
        
        decision = self.guardian.security_decisions[-1]
        explanation = self.guardian.explain_security_decision(decision.decision_id)
        
        assert explanation is not None
        assert "decision" in explanation
        assert "explanation" in explanation
        assert "context" in explanation
        
        # Check explanation details
        assert explanation["explanation"]["what_happened"] == "Security action 'block' was applied to driver_installation"
        assert explanation["explanation"]["why"] == "Driver not verified for security"
        assert "85%" in explanation["explanation"]["confidence"]

class TestAuroraIntentEngine:
    """Test Aurora Intent Engine (AIE)."""
    
    def setup_method(self):
        """Setup test environment."""
        # Mock AI models to avoid heavy dependencies
        with patch('spacy.load'), \
             patch('transformers.pipeline'):
            self.intent_engine = AuroraIntentEngine("/tmp/test_aurora_intent_engine.json")
    
    def test_engine_initialization(self):
        """Test AIE initialization."""
        assert self.intent_engine.config_path.name == "test_aurora_intent_engine.json"
        assert len(self.intent_engine.intents_history) == 0
        assert len(self.intent_engine.decisions_history) == 0
        assert len(self.intent_engine.config) > 0
    
    def test_rule_based_intent_classification(self):
        """Test rule-based intent classification."""
        
        # Test application opening
        text = "open firefox"
        entities = {"applications": ["firefox"]}
        intent_type, confidence = self.intent_engine._classify_intent_rule_based(text, entities)
        
        assert intent_type == IntentType.OPEN_APPLICATION
        assert confidence == 0.9
        
        # Test settings configuration
        text = "configure battery settings"
        entities = {"settings": ["battery"]}
        intent_type, confidence = self.intent_engine._classify_intent_rule_based(text, entities)
        
        assert intent_type == IntentType.SYSTEM_SETTINGS
        assert confidence == 0.8
        
        # Test troubleshooting
        text = "fix my laptop"
        entities = {"applications": ["laptop"]}
        intent_type, confidence = self.intent_engine._classify_intent_rule_based(text, entities)
        
        assert intent_type == IntentType.TROUBLESHOOT
        assert confidence == 0.8
    
    def test_entity_extraction(self):
        """Test entity extraction."""
        
        text = "Open firefox and configure battery settings"
        entities = self.intent_engine._extract_entities_rule_based(text)
        
        assert "applications" in entities
        assert "firefox" in entities["applications"]
        assert "settings" in entities
        assert "battery" in entities["settings"]
    
    def test_action_plan_generation(self):
        """Test action plan generation."""
        
        # Test open application action plan
        entities = {"applications": ["firefox", "chrome"]}
        action_plan = self.intent_engine._generate_action_plan(
            IntentType.OPEN_APPLICATION, entities
        )
        
        assert len(action_plan) == 2
        assert action_plan[0]["action"] == "launch_application"
        assert action_plan[0]["parameters"]["app_name"] == "firefox"
        assert action_plan[1]["parameters"]["app_name"] == "chrome"
        
        # Test troubleshooting action plan
        entities = {"applications": ["system"]}
        action_plan = self.intent_engine._generate_action_plan(
            IntentType.TROUBLESHOOT, entities
        )
        
        assert len(action_plan) == 2  # diagnose + fix
        assert action_plan[0]["action"] == "diagnose_issue"
        assert action_plan[1]["action"] == "apply_fix"
    
    def test_application_launch(self):
        """Test application launching."""
        
        # Test successful launch (mocked)
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = None  # Process running
            mock_process.pid = 12345
            mock_popen.return_value = mock_process
            
            result = asyncio.run(self.intent_engine._launch_application("firefox"))
            
            assert result["success"] == True
            assert result["app_name"] == "firefox"
            assert result["pid"] == 12345
            mock_popen.assert_called_once()
    
    def test_system_metrics_gathering(self):
        """Test system metrics gathering."""
        
        # Mock psutil
        with patch('system.ai_control_plane.aurora_intent_engine.psutil') as mock_psutil:
            mock_psutil.cpu_percent.return_value = 45.2
            mock_psutil.virtual_memory.return_value.percent = 67.8
            
            result = asyncio.run(self.intent_engine._gather_system_metrics())
            
            assert result["success"] == True
            assert "metrics" in result
            assert result["metrics"]["cpu_usage"] == 45.2
            assert result["metrics"]["memory_usage"] == 67.8
    
    def test_health_analysis(self):
        """Test system health analysis."""
        
        # Mock metrics
        self.intent_engine.kernel_telemetry = {
            "cpu_usage": 30.0,
            "memory_usage": 40.0
        }
        
        result = asyncio.run(self.intent_engine._analyze_system_health())
        
        assert result["success"] == True
        assert "health_score" in result
        assert "recommendations" in result
        assert 0.0 <= result["health_score"] <= 1.0
        
        # With low usage, health score should be good
        assert result["health_score"] > 0.7
    
    def test_session_management(self):
        """Test session management."""
        
        session_id = self.intent_engine._create_session()
        
        assert session_id in self.intent_engine.active_sessions
        assert "created" in self.intent_engine.active_sessions[session_id]
        assert "context" in self.intent_engine.active_sessions[session_id]
        assert "intents" in self.intent_engine.active_sessions[session_id]
        
        # Update context
        test_context = {"user_preference": "test"}
        self.intent_engine._update_session_context(session_id, test_context)
        
        context = self.intent_engine._get_context_for_intent(session_id)
        assert context["user_preference"] == "test"
    
    def test_engine_status(self):
        """Test engine status reporting."""
        
        status = self.intent_engine.get_engine_status()
        
        assert "status" in status
        assert "intents_processed" in status
        assert "decisions_made" in status
        assert "active_sessions" in status
        assert "ai_models_loaded" in status
        assert "explainable_decisions" in status
        
        assert status["status"] == "active"
        assert status["explainable_decisions"] == True

class TestIntegration:
    """Integration tests for Aurora improvements."""
    
    def test_mode_guardian_integration(self):
        """Test integration between Aurora Modes and Guardian."""
        
        mode_manager = AuroraModeManager("/tmp/test_modes.json")
        guardian = AuroraGuardian("/tmp/test_guardian.json")
        
        # Switch to enterprise mode
        mode_manager.switch_mode(AuroraMode.ENTERPRISE, "Security test")
        
        # Guardian should respect enterprise security settings
        status = guardian.get_security_status()
        
        # Should have compliance checking
        assert "compliance_status" in status
        assert "score" in status["compliance_status"]
    
    def test_intent_guardian_integration(self):
        """Test integration between AIE and Guardian."""
        
        with patch('spacy.load'), \
             patch('transformers.pipeline'):
            
            intent_engine = AuroraIntentEngine("/tmp/test_intent.json")
            guardian = AuroraGuardian("/tmp/test_guardian.json")
            
            # Process security-related intent
            result = asyncio.run(intent_engine.process_user_intent("check security status"))
            
            assert "intent" in result
            assert "result" in result
            
            # Guardian should provide security context
            security_status = guardian.get_security_status()
            assert security_status["security_level"] is not None

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])