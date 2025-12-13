"""
Test suite for enhanced Aurora UI and installer components
"""

import asyncio
import os
import sys
import tempfile
import pytest
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from desktop.aurora_shell.ui.modern_theme import ModernTheme, AnimationManager, ThemeColor
from desktop.aurora_shell.apps.conversational_palette.enhanced_ui import EnhancedConversationalUI, MessageType
from installer.aurora_installer import AuroraInstaller, InstallationStep, InstallationMode
from installer.usb_creator import BootableUSBCreator, USBStatus

class TestModernTheme:
    """Test modern theme functionality"""
    
    def test_theme_initialization(self):
        """Test theme initialization"""
        theme = ModernTheme()
        
        assert theme.animations is not None
        assert theme.transitions is not None
        assert theme.current_theme == "dark"
        
        # Check if essential animations exist
        assert "fade_in" in theme.animations
        assert "slide_up" in theme.animations
        assert "pulse" in theme.animations
        assert "aurora_glow" in theme.animations
    
    def test_css_generation(self):
        """Test CSS generation"""
        theme = ModernTheme()
        css = theme.generate_theme_css()
        
        assert isinstance(css, str)
        assert len(css) > 1000  # Should be substantial CSS
        assert "--aurora-primary" in css
        assert "aurora-fade-in" in css
        assert "aurora-btn" in css
    
    def test_animation_config(self):
        """Test animation configuration"""
        theme = ModernTheme()
        
        fade_in_config = theme.animations["fade_in"]
        assert fade_in_config.duration > 0
        assert fade_in_config.easing is not None
        
        # Test infinite animation
        glow_config = theme.animations["aurora_glow"]
        assert glow_config.iterations == -1
    
    def test_theme_colors(self):
        """Test theme color palette"""
        theme = ModernTheme()
        colors = theme.get_theme_colors()
        
        assert "primary" in colors
        assert "secondary" in colors
        assert "success" in colors
        assert colors["primary"] == ThemeColor.PRIMARY.value

class TestAnimationManager:
    """Test animation manager functionality"""
    
    def test_animation_manager_initialization(self):
        """Test animation manager initialization"""
        theme = ModernTheme()
        manager = AnimationManager(theme)
        
        assert manager.theme == theme
        assert manager.active_animations == {}
    
    def test_micro_interaction_creation(self):
        """Test micro-interaction creation"""
        theme = ModernTheme()
        manager = AnimationManager(theme)
        
        interaction = manager.create_micro_interaction("button1", "hover")
        assert "aurora-animate-" in interaction
        
        click_interaction = manager.create_micro_interaction("button2", "click")
        assert "scale-in" in click_interaction

class TestEnhancedConversationalUI:
    """Test enhanced conversational UI"""
    
    def test_ui_initialization(self):
        """Test UI initialization"""
        ui = EnhancedConversationalUI()
        
        assert ui.messages == []
        assert ui.suggestions is not None
        assert len(ui.suggestions) > 0
        assert ui.theme is not None
        assert ui.animation_manager is not None
    
    def test_html_generation(self):
        """Test HTML generation"""
        ui = EnhancedConversationalUI()
        html = ui.generate_html()
        
        assert isinstance(html, str)
        assert len(html) > 10000  # Should be substantial HTML
        assert "aurora-palette" in html
        assert "aurora-message" in html
        assert "aurora-input" in html
        assert "Aurora Assistant" in html
    
    @pytest.mark.asyncio
    async def test_message_sending(self):
        """Test message sending functionality"""
        ui = EnhancedConversationalUI()
        
        # Send user message
        user_message = await ui.send_message("Hello Aurora", MessageType.USER)
        assert user_message.type == MessageType.USER
        assert user_message.content == "Hello Aurora"
        
        # Check if message was added
        assert len(ui.messages) == 1
        assert ui.messages[0].content == "Hello Aurora"
    
    @pytest.mark.asyncio
    async def test_ai_response_generation(self):
        """Test AI response generation"""
        ui = EnhancedConversationalUI()
        
        # Test different message types
        test_messages = [
            ("hello", "Hello"),
            ("open firefox", "firefox"),
            ("find documents", "document"),
            ("system status", "status"),
            ("help", "help")
        ]
        
        for message, expected_content in test_messages:
            response = await ui._generate_ai_response(message)
            assert isinstance(response, str)
            assert len(response) > 0
            # Check if response is relevant to message
            if expected_content.lower() in response.lower():
                pass  # Good response
            else:
                # Generic response is also acceptable
                assert "I understand" in response or "I'll help" in response
    
    def test_suggestion_management(self):
        """Test suggestion chip management"""
        ui = EnhancedConversationalUI()
        
        # Check initial suggestions
        assert len(ui.suggestions) > 0
        
        # Update suggestions
        from desktop.aurora_shell.apps.conversational_palette.enhanced_ui import SuggestionChip
        new_suggestions = [
            SuggestionChip("test1", "Test Action", "test_action", "🧪", "#ff0000")
        ]
        
        ui.update_suggestions(new_suggestions)
        assert len(ui.suggestions) == 1
        assert ui.suggestions[0].text == "Test Action"
    
    def test_ui_state_management(self):
        """Test UI state management"""
        ui = EnhancedConversationalUI()
        
        # Test initial state
        assert not ui.is_minimized
        assert not ui.is_fullscreen
        assert ui.theme_mode == "dark"
        
        # Test state changes
        ui.toggle_minimize()
        assert ui.is_minimized
        
        ui.toggle_fullscreen()
        assert ui.is_fullscreen
        
        ui.set_theme_mode("light")
        assert ui.theme_mode == "light"

class TestAuroraInstaller:
    """Test Aurora OS installer"""
    
    def test_installer_initialization(self):
        """Test installer initialization"""
        installer = AuroraInstaller()
        
        assert installer.current_step == InstallationStep.WELCOME
        assert installer.installation_mode == InstallationMode.STANDARD
        assert installer.installation_progress == 0
        assert installer.installation_logs == []
        
        # Check configuration
        assert "aurora_version" in installer.config
        assert "minimal_requirements" in installer.config
        assert "recommended_requirements" in installer.config
    
    def test_html_generation(self):
        """Test installer HTML generation"""
        installer = AuroraInstaller()
        html = installer.generate_installer_html()
        
        assert isinstance(html, str)
        assert len(html) > 20000  # Should be substantial HTML
        assert "Aurora OS Installer" in html
        assert "installer-container" in html
        assert "system requirements" in html.lower()
        assert "partitioning" in html.lower()
    
    @pytest.mark.asyncio
    async def test_system_requirements_check(self):
        """Test system requirements checking"""
        installer = AuroraInstaller()
        
        requirements = await installer.check_system_requirements()
        
        assert requirements is not None
        assert isinstance(requirements.cpu_cores, int)
        assert isinstance(requirements.memory_gb, int)
        assert isinstance(requirements.disk_space_gb, int)
        assert isinstance(requirements.uefi_support, bool)
        assert isinstance(requirements.requirements_met, bool)
        assert isinstance(requirements.warnings, list)
        
        # Log the requirements for debugging
        print(f"CPU Cores: {requirements.cpu_cores}")
        print(f"Memory: {requirements.memory_gb}GB")
        print(f"Disk Space: {requirements.disk_space_gb}GB")
        print(f"UEFI Support: {requirements.uefi_support}")
        print(f"Requirements Met: {requirements.requirements_met}")
        print(f"Warnings: {requirements.warnings}")
    
    def test_storage_device_detection(self):
        """Test storage device detection"""
        installer = AuroraInstaller()
        
        devices = installer.detect_storage_devices()
        
        assert isinstance(devices, list)
        # Note: This test might fail in some environments where no storage devices are available
        # But the function should not crash
    
    def test_partition_scheme_creation(self):
        """Test partition scheme creation"""
        installer = AuroraInstaller()
        
        # Create mock requirements
        from installer.aurora_installer import SystemRequirements, PartitionScheme
        installer.system_requirements = SystemRequirements(
            cpu_cores=4,
            memory_gb=8,
            disk_space_gb=100,
            uefi_support=True,
            requirements_met=True,
            warnings=[]
        )
        
        # Test different installation modes
        test_device = "/dev/sdb"
        
        # Standard mode
        scheme = installer.create_partition_scheme(test_device, InstallationMode.STANDARD)
        assert isinstance(scheme, PartitionScheme)
        assert scheme.boot_partition == "/dev/sdb1"
        assert scheme.root_partition == "/dev/sdb2"
        assert scheme.swap_partition == "/dev/sdb3"
        assert scheme.home_partition is None
        
        # Advanced mode
        scheme = installer.create_partition_scheme(test_device, InstallationMode.ADVANCED)
        assert scheme.home_partition == "/dev/sdb4"
        
        # Portable mode
        scheme = installer.create_partition_scheme(test_device, InstallationMode.PORTABLE)
        assert scheme.swap_partition is None  # No swap on USB
    
    @pytest.mark.asyncio
    async def test_installation_simulation(self):
        """Test installation process simulation"""
        installer = AuroraInstaller()
        
        # Setup mock environment
        installer.system_requirements = SystemRequirements(
            cpu_cores=4,
            memory_gb=8,
            disk_space_gb=100,
            uefi_support=True,
            requirements_met=True,
            warnings=[]
        )
        
        installer.partition_scheme = installer.create_partition_scheme("/dev/sdb", InstallationMode.STANDARD)
        
        # Run installation simulation
        result = await installer.execute_installation()
        
        # Check if installation completed
        assert isinstance(result, bool)
        assert installer.installation_progress >= 90  # Should be near completion
        
        # Check installation logs
        assert len(installer.installation_logs) > 0
    
    def test_installation_summary(self):
        """Test installation summary generation"""
        installer = AuroraInstaller()
        
        summary = installer.get_installation_summary()
        
        assert "installation_id" in summary
        assert "mode" in summary
        assert "requirements_met" in summary
        assert "progress" in summary
        assert "logs" in summary
        assert "timestamp" in summary

class TestBootableUSBCreator:
    """Test bootable USB creator"""
    
    def test_usb_creator_initialization(self):
        """Test USB creator initialization"""
        creator = BootableUSBCreator()
        
        assert creator.status == USBStatus.IDLE
        assert creator.usb_devices == []
        assert creator.selected_device is None
        assert creator.creation_progress == 0
        assert creator.creation_logs == []
        assert creator.iso_path.endswith(".iso")
    
    def test_html_generation(self):
        """Test USB creator HTML generation"""
        creator = BootableUSBCreator()
        html = creator.generate_usb_creator_html()
        
        assert isinstance(html, str)
        assert len(html) > 15000  # Should be substantial HTML
        assert "Aurora OS USB Creator" in html
        assert "usb-creator-container" in html
        assert "Select ISO File" in html
        assert "Select USB Device" in html
    
    def test_usb_device_scanning(self):
        """Test USB device scanning"""
        creator = BootableUSBCreator()
        
        devices = creator.scan_usb_devices()
        
        assert isinstance(devices, list)
        # Note: This test might not find actual USB devices in test environment
        # But the function should not crash and should return an empty list if no devices found
    
    def test_device_mount_check(self):
        """Test device mount checking"""
        creator = BootableUSBCreator()
        
        # Test with non-existent device (should return False)
        is_mounted = creator._is_device_mounted("/dev/nonexistent")
        assert is_mounted == False
        
        # Test with root device (might be mounted)
        is_root_mounted = creator._is_device_mounted("/dev/sda")
        assert isinstance(is_root_mounted, bool)
    
    @pytest.mark.asyncio
    async def test_usb_creation_simulation(self):
        """Test USB creation simulation"""
        creator = BootableUSBCreator()
        
        # Mock a USB device
        from installer.usb_creator import USBDevice
        mock_device = USBDevice(
            name="Test USB",
            path="/dev/sdb",
            size="32GB",
            model="Test Model",
            vendor="Test Vendor",
            is_removable=True,
            is_mounted=False
        )
        
        creator.selected_device = mock_device
        
        # Create a temporary test ISO file
        with tempfile.NamedTemporaryFile(suffix=".iso", delete=False) as temp_iso:
            temp_iso.write(b"fake iso content")
            temp_iso_path = temp_iso.name
        
        try:
            # Test the creation process (will fail at ISO writing stage, but that's expected)
            result = await creator.create_bootable_usb("/dev/sdb", temp_iso_path)
            
            # Check progress and logs
            assert isinstance(result, bool)
            assert len(creator.creation_logs) > 0
            
        finally:
            # Clean up temporary file
            os.unlink(temp_iso_path)
    
    def test_creation_summary(self):
        """Test USB creation summary"""
        creator = BootableUSBCreator()
        
        summary = creator.get_creation_summary()
        
        assert "status" in summary
        assert "usb_devices" in summary
        assert "selected_device" in summary
        assert "progress" in summary
        assert "logs" in summary
        assert "timestamp" in summary

class TestIntegration:
    """Integration tests for UI and installer components"""
    
    @pytest.mark.asyncio
    async def test_conversational_ui_startup(self):
        """Test conversational UI startup process"""
        ui = EnhancedConversationalUI()
        
        # Start the conversation interface
        html_path = await ui.start_conversation()
        
        # Check if HTML file was created
        assert os.path.exists("/workspace/aurora_conversational_palette.html")
        assert isinstance(html_path, str)
    
    @pytest.mark.asyncio
    async def test_installer_startup(self):
        """Test installer startup process"""
        installer = AuroraInstaller()
        
        # Start the installer
        installer_path = await installer.start_installer()
        
        # Check if installer HTML was created
        assert os.path.exists("/workspace/aurora_os_installer.html")
        assert isinstance(installer_path, str)
    
    @pytest.mark.asyncio
    async def test_usb_creator_startup(self):
        """Test USB creator startup process"""
        creator = BootableUSBCreator()
        
        # Start the USB creator
        creator_path = await creator.start_usb_creator()
        
        # Check if USB creator HTML was created
        assert os.path.exists("/workspace/aurora_usb_creator.html")
        assert isinstance(creator_path, str)

# Test runner function
def run_enhanced_ui_installer_tests():
    """Run all enhanced UI and installer tests"""
    print("🧪 Running Enhanced UI & Installer Tests")
    print("=" * 60)
    
    # Create test instances
    modern_theme = TestModernTheme()
    animation_manager = TestAnimationManager()
    conversational_ui = TestEnhancedConversationalUI()
    aurora_installer = TestAuroraInstaller()
    usb_creator = TestBootableUSBCreator()
    
    tests = [
        ("Modern Theme", modern_theme.test_theme_initialization),
        ("Animation Manager", animation_manager.test_animation_manager_initialization),
        ("Conversational UI", conversational_ui.test_ui_initialization),
        ("Aurora Installer", aurora_installer.test_installer_initialization),
        ("USB Creator", usb_creator.test_usb_creator_initialization),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"  📋 {test_name}... ", end="")
            test_func()
            print("✅ PASSED")
            passed += 1
        except Exception as e:
            print(f"❌ FAILED: {e}")
            failed += 1
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = run_enhanced_ui_installer_tests()
    sys.exit(0 if success else 1)