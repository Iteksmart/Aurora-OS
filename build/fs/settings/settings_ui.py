"""
Aurora OS - System Settings UI
Modern settings interface that combines traditional settings with intent-based configuration
Provides System Settings, Administrator Settings, and User Settings sections
"""

import os
import sys
import json
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from pathlib import Path
import logging
from datetime import datetime

try:
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
    from gi.repository import Gtk, Adw, Gdk, Gio, GLib, Pango
    GTK_AVAILABLE = True
except ImportError:
    GTK_AVAILABLE = False

from .intent_settings import get_intent_engine, Intent, IntentCategory
from ..hardware.driver_manager import get_driver_manager

@dataclass
class SettingsSection:
    """Settings section definition"""
    id: str
    title: str
    description: str
    icon_name: str
    category: str
    is_admin_only: bool = False
    requires_restart: bool = False

class SettingsUI:
    """
    Modern settings interface for Aurora OS
    Combines traditional settings with AI-powered intent configuration
    """
    
    def __init__(self):
        self.intent_engine = get_intent_engine()
        self.driver_manager = get_driver_manager()
        
        # UI components
        self.window = None
        self.main_stack = None
        self.sidebar_list = None
        self.content_area = None
        
        # Settings sections
        self.sections = self._define_sections()
        self.current_section = None
        
        # Theme system
        self.current_theme = "aurora"
        
        self.logger = logging.getLogger("Aurora.SettingsUI")
        self._setup_logging()
        
        # Initialize UI
        if GTK_AVAILABLE:
            self._init_ui()
    
    def _setup_logging(self):
        """Setup logging"""
        log_dir = Path("/var/log/aurora")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(log_dir / "settings_ui.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _define_sections(self) -> Dict[str, SettingsSection]:
        """Define all settings sections"""
        return {
            # User Settings
            'user_profile': SettingsSection(
                id='user_profile',
                title='User Profile',
                description='Manage your account and personal information',
                icon_name='user-info',
                category='user'
            ),
            'personalization': SettingsSection(
                id='personalization',
                title='Personalization',
                description='Themes, fonts, colors, and appearance',
                icon_name='applications-graphics',
                category='user'
            ),
            'notifications': SettingsSection(
                id='notifications',
                title='Notifications',
                description='Manage system and app notifications',
                icon_name='notification-symbolic',
                category='user'
            ),
            'privacy': SettingsSection(
                id='privacy',
                title='Privacy & Security',
                description='Control your data and security settings',
                icon_name='security-high-symbolic',
                category='user'
            ),
            'accessibility': SettingsSection(
                id='accessibility',
                title='Accessibility',
                description='Make Aurora easier to use',
                icon_name='preferences-desktop-accessibility',
                category='user'
            ),
            
            # System Settings
            'intent_config': SettingsSection(
                id='intent_config',
                title='AI Intent Configuration',
                description='Tell Aurora what you want to accomplish',
                icon_name='brain-symbolic',
                category='system',
                requires_restart=False
            ),
            'devices': SettingsSection(
                id='devices',
                title='Devices & Drivers',
                description='Manage hardware and device drivers',
                icon_name='computer-symbolic',
                category='system'
            ),
            'power': SettingsSection(
                id='power',
                title='Power & Battery',
                description='Power management and battery settings',
                icon_name='battery-symbolic',
                category='system'
            ),
            'network': SettingsSection(
                id='network',
                title='Network & Internet',
                description='WiFi, VPN, and network settings',
                icon_name='network-wired-symbolic',
                category='system'
            ),
            'sound': SettingsSection(
                id='sound',
                title='Sound',
                description='Audio devices and sound settings',
                icon_name='audio-speakers-symbolic',
                category='system'
            ),
            'display': SettingsSection(
                id='display',
                title='Display',
                description='Screen resolution, brightness, and graphics',
                icon_name='display-symbolic',
                category='system'
            ),
            'storage': SettingsSection(
                id='storage',
                title='Storage',
                description='Disk space and storage management',
                icon_name='drive-harddisk-symbolic',
                category='system'
            ),
            
            # Administrator Settings
            'system_admin': SettingsSection(
                id='system_admin',
                title='System Administration',
                description='Advanced system configuration',
                icon_name='system-settings-symbolic',
                category='admin',
                is_admin_only=True
            ),
            'security_admin': SettingsSection(
                id='security_admin',
                title='Security Administration',
                description='Advanced security and firewall settings',
                icon_name='security-symbolic',
                category='admin',
                is_admin_only=True
            ),
            'updates': SettingsSection(
                id='updates',
                title='System Updates',
                description='Manage system updates and maintenance',
                icon_name='software-update-available-symbolic',
                category='admin',
                is_admin_only=True,
                requires_restart=True
            ),
            'logs': SettingsSection(
                id='logs',
                title='System Logs',
                description='View and manage system logs',
                icon_name='document-open-recent-symbolic',
                category='admin',
                is_admin_only=True
            )
        }
    
    def _init_ui(self):
        """Initialize the settings UI"""
        # Create main window
        self.window = Adw.Window()
        self.window.set_title("Aurora OS Settings")
        self.window.set_default_size(1200, 800)
        self.window.set_resizable(True)
        
        # Apply Aurora theme
        self._apply_theme()
        
        # Create main layout
        self._create_main_layout()
        
        # Connect signals
        self._connect_signals()
        
        self.logger.info("Settings UI initialized")
    
    def _apply_theme(self):
        """Apply Aurora theme to settings"""
        if self.window is None:
            return
        
        css_provider = Gtk.CssProvider()
        css_data = """
        window {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        
        .sidebar-item {
            padding: 12px 16px;
            border-radius: 8px;
            margin: 2px;
            transition: all 0.3s ease;
        }
        
        .sidebar-item:hover {
            background: rgba(88, 86, 214, 0.1);
        }
        
        .sidebar-item:selected {
            background: linear-gradient(135deg, #5856d6, #af52de);
            color: white;
        }
        
        .settings-group {
            background: rgba(255, 255, 255, 0.8);
            border-radius: 12px;
            margin: 16px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
        
        .settings-title {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 8px;
            color: #1d1d1f;
        }
        
        .settings-description {
            color: #86868b;
            margin-bottom: 20px;
        }
        
        .intent-input {
            background: rgba(255, 255, 255, 0.9);
            border: 2px solid #5856d6;
            border-radius: 24px;
            padding: 16px 20px;
            font-size: 16px;
            margin: 16px 0;
        }
        
        .intent-button {
            background: linear-gradient(135deg, #5856d6, #af52de);
            color: white;
            border: none;
            border-radius: 24px;
            padding: 12px 24px;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        
        .intent-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(88, 86, 214, 0.3);
        }
        
        .device-card {
            background: rgba(255, 255, 255, 0.9);
            border-radius: 12px;
            padding: 16px;
            margin: 8px;
            border-left: 4px solid #5856d6;
        }
        
        .device-name {
            font-weight: bold;
            font-size: 16px;
        }
        
        .device-status {
            color: #86868b;
            font-size: 14px;
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }
        
        .status-good { background: #30d158; }
        .status-warning { background: #ff9500; }
        .status-error { background: #ff3b30; }
        """
        
        css_provider.load_from_data(css_data.encode())
        
        # Apply to display
        style_context = self.window.get_style_context()
        style_context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    
    def _create_main_layout(self):
        """Create the main settings layout"""
        # Create horizontal box for sidebar and content
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.window.set_child(main_box)
        
        # Create sidebar
        self.sidebar_list = self._create_sidebar()
        main_box.append(self.sidebar_list)
        
        # Create content area
        self.content_area = self._create_content_area()
        main_box.append(self.content_area)
    
    def _create_sidebar(self):
        """Create the settings sidebar"""
        # Scrollable sidebar
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_width(280)
        
        # Sidebar list
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        box.set_margin_start(12)
        box.set_margin_end(12)
        
        # Add header
        header_label = Gtk.Label(label="Settings")
        header_label.add_css_class("title-2")
        header_label.set_margin_bottom(16)
        box.append(header_label)
        
        # Add section headers and items
        categories = {
            'user': ('User Settings', 'user-symbolic'),
            'system': ('System Settings', 'computer-symbolic'),
            'admin': ('Administrator Settings', 'security-symbolic')
        }
        
        for category, (title, icon) in categories.items():
            # Category header
            category_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            category_box.set_margin_top(16)
            
            icon_widget = Gtk.Image.new_from_icon_name(icon)
            icon_widget.add_css_class("dim-label")
            category_box.append(icon_widget)
            
            label = Gtk.Label(label=title)
            label.add_css_class("caption-heading")
            label.add_css_class("dim-label")
            label.set_halign(Gtk.Align.START)
            category_box.append(label)
            
            box.append(category_box)
            
            # Add sections for this category
            for section_id, section in self.sections.items():
                if section.category == category:
                    # Skip admin-only if not root
                    if section.is_admin_only and os.geteuid() != 0:
                        continue
                    
                    item = self._create_sidebar_item(section)
                    box.append(item)
        
        scrolled.set_child(box)
        return scrolled
    
    def _create_sidebar_item(self, section: SettingsSection):
        """Create a sidebar item for a section"""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.add_css_class("sidebar-item")
        box.set_margin_top(2)
        box.set_margin_bottom(2)
        
        # Icon
        icon = Gtk.Image.new_from_icon_name(section.icon_name)
        icon.set_pixel_size(20)
        box.append(icon)
        
        # Title
        label = Gtk.Label(label=section.title)
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        box.append(label)
        
        # Add badge for admin-only sections
        if section.is_admin_only:
            badge = Gtk.Label(label="🔒")
            badge.add_css_class("dim-label")
            box.append(badge)
        
        # Store section ID and connect click
        box.section_id = section.id
        gesture_click = Gtk.GestureClick()
        gesture_click.connect("pressed", self._on_sidebar_item_clicked)
        box.add_controller(gesture_click)
        
        return box
    
    def _create_content_area(self):
        """Create the main content area"""
        # Stack for different sections
        self.main_stack = Gtk.Stack()
        self.main_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        
        # Create all section pages
        for section_id, section in self.sections.items():
            # Skip admin-only if not root
            if section.is_admin_only and os.geteuid() != 0:
                continue
            
            page = self._create_section_page(section)
            self.main_stack.add_titled(page, section_id, section.title)
        
        return self.main_stack
    
    def _create_section_page(self, section: SettingsSection) -> Gtk.Widget:
        """Create a page for a settings section"""
        if section.id == 'intent_config':
            return self._create_intent_page(section)
        elif section.id == 'devices':
            return self._create_devices_page(section)
        elif section.id == 'personalization':
            return self._create_personalization_page(section)
        elif section.id == 'privacy':
            return self._create_privacy_page(section)
        else:
            return self._create_generic_page(section)
    
    def _create_intent_page(self, section: SettingsSection) -> Gtk.Widget:
        """Create the intent configuration page"""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        
        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        header_box.add_css_class("settings-group")
        
        title = Gtk.Label(label=section.title)
        title.add_css_class("settings-title")
        header_box.append(title)
        
        description = Gtk.Label(label=section.description)
        description.add_css_class("settings-description")
        description.set_wrap(True)
        header_box.append(description)
        
        box.append(header_box)
        
        # Intent input section
        intent_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        intent_box.add_css_class("settings-group")
        
        intent_label = Gtk.Label(label="What would you like Aurora to do?")
        intent_label.add_css_class("title-4")
        intent_box.append(intent_label)
        
        # Intent input field
        self.intent_entry = Gtk.Entry()
        self.intent_entry.set_placeholder_text("e.g., 'Make my battery last 12 hours' or 'Optimize for gaming'")
        self.intent_entry.add_css_class("intent-input")
        intent_box.append(self.intent_entry)
        
        # Execute button
        execute_button = Gtk.Button(label="Apply Intent")
        execute_button.add_css_class("intent-button")
        execute_button.connect("clicked", self._on_execute_intent_clicked)
        intent_box.append(execute_button)
        
        box.append(intent_box)
        
        # Suggested intents
        suggestions_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        suggestions_box.add_css_class("settings-group")
        
        suggestions_label = Gtk.Label(label="Suggested Configurations")
        suggestions_label.add_css_class("title-4")
        suggestions_box.append(suggestions_label)
        
        # Get suggested intents
        suggestions = self.intent_engine.get_suggested_intents()
        
        suggestions_flow = Gtk.FlowBox()
        suggestions_flow.set_max_children_per_line(3)
        suggestions_flow.set_row_spacing(8)
        suggestions_flow.set_column_spacing(8)
        
        for suggestion in suggestions:
            suggestion_button = Gtk.Button(label=suggestion)
            suggestion_button.add_css_class("suggestion-chip")
            suggestion_button.connect("clicked", self._on_suggestion_clicked, suggestion)
            suggestions_flow.append(suggestion_button)
        
        suggestions_box.append(suggestions_flow)
        box.append(suggestions_box)
        
        # Active intents section
        active_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        active_box.add_css_class("settings-group")
        
        active_label = Gtk.Label(label="Recent Intent Executions")
        active_label.add_css_class("title-4")
        active_box.append(active_label)
        
        # Active intents list
        self.active_intents_list = Gtk.ListBox()
        self.active_intents_list.add_css_class("boxed-list")
        active_box.append(self.active_intents_list)
        
        box.append(active_box)
        
        scrolled.set_child(box)
        return scrolled
    
    def _create_devices_page(self, section: SettingsSection) -> Gtk.Widget:
        """Create the devices and drivers page"""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        
        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        header_box.add_css_class("settings-group")
        
        title = Gtk.Label(label=section.title)
        title.add_css_class("settings-title")
        header_box.append(title)
        
        description = Gtk.Label(label=section.description)
        description.add_css_class("settings-description")
        description.set_wrap(True)
        header_box.append(description)
        
        box.append(header_box)
        
        # Scan devices button
        scan_button = Gtk.Button(label="Scan for Hardware Changes")
        scan_button.add_css_class("suggested-action")
        scan_button.connect("clicked", self._on_scan_devices_clicked)
        box.append(scan_button)
        
        # Devices list
        self.devices_list = Gtk.ListBox()
        self.devices_list.add_css_class("boxed-list")
        box.append(self.devices_list)
        
        # Populate devices list
        self._populate_devices_list()
        
        scrolled.set_child(box)
        return scrolled
    
    def _create_personalization_page(self, section: SettingsSection) -> Gtk.Widget:
        """Create the personalization page"""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        
        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        header_box.add_css_class("settings-group")
        
        title = Gtk.Label(label=section.title)
        title.add_css_class("settings-title")
        header_box.append(title)
        
        description = Gtk.Label(label=section.description)
        description.add_css_class("settings-description")
        description.set_wrap(True)
        header_box.append(description)
        
        box.append(header_box)
        
        # Theme selection
        theme_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        theme_box.add_css_class("settings-group")
        
        theme_label = Gtk.Label(label="Theme Selection")
        theme_label.add_css_class("title-4")
        theme_box.append(theme_label)
        
        # Theme options
        themes = [
            ("Aurora", "Default Aurora theme with gradient colors"),
            ("Dark", "Dark theme for low-light environments"),
            ("Light", "Light theme for bright environments"),
            ("High Contrast", "High contrast theme for accessibility")
        ]
        
        for theme_name, theme_desc in themes:
            theme_row = Adw.ActionRow()
            theme_row.set_title(theme_name)
            theme_row.set_subtitle(theme_desc)
            
            theme_radio = Gtk.CheckButton()
            theme_radio.set_group(self.theme_radio_group if hasattr(self, 'theme_radio_group') else None)
            theme_radio.connect("toggled", self._on_theme_changed, theme_name.lower().replace(' ', '_'))
            
            theme_row.add_suffix(theme_radio)
            theme_box.append(theme_row)
        
        box.append(theme_box)
        
        scrolled.set_child(box)
        return scrolled
    
    def _create_privacy_page(self, section: SettingsSection) -> Gtk.Widget:
        """Create the privacy page"""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        
        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        header_box.add_css_class("settings-group")
        
        title = Gtk.Label(label=section.title)
        title.add_css_class("settings-title")
        header_box.append(title)
        
        description = Gtk.Label(label=section.description)
        description.add_css_class("settings-description")
        description.set_wrap(True)
        header_box.append(description)
        
        box.append(header_box)
        
        # Privacy options
        privacy_options = [
            ("Location Services", "Allow apps to access your location", True),
            ("Microphone Access", "Allow apps to access the microphone", True),
            ("Camera Access", "Allow apps to access the camera", True),
            ("Telemetry", "Share anonymous usage data to improve Aurora", False),
            ("Crash Reports", "Send crash reports to help fix issues", False),
            ("Activity History", "Track your activity across the system", False)
        ]
        
        for option_title, option_subtitle, default_value in privacy_options:
            option_row = Adw.ActionRow()
            option_row.set_title(option_title)
            option_row.set_subtitle(option_subtitle)
            
            option_switch = Gtk.Switch()
            option_switch.set_active(default_value)
            option_switch.connect("notify::active", self._on_privacy_switch_changed, option_title.lower().replace(' ', '_'))
            
            option_row.add_suffix(option_switch)
            box.append(option_row)
        
        scrolled.set_child(box)
        return scrolled
    
    def _create_generic_page(self, section: SettingsSection) -> Gtk.Widget:
        """Create a generic settings page"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        
        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        header_box.add_css_class("settings-group")
        
        title = Gtk.Label(label=section.title)
        title.add_css_class("settings-title")
        header_box.append(title)
        
        description = Gtk.Label(label=section.description)
        description.add_css_class("settings-description")
        description.set_wrap(True)
        header_box.append(description)
        
        box.append(header_box)
        
        # Placeholder content
        placeholder_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        placeholder_box.add_css_class("settings-group")
        placeholder_box.set_valign(Gtk.Align.CENTER)
        
        placeholder_label = Gtk.Label(label=f"{section.title} configuration coming soon...")
        placeholder_label.add_css_class("body")
        placeholder_label.set_wrap(True)
        placeholder_box.append(placeholder_label)
        
        box.append(placeholder_box)
        
        return box
    
    def _connect_signals(self):
        """Connect UI signals"""
        if self.window is None:
            return
        
        self.window.connect("close-request", self._on_window_close)
    
    def _on_sidebar_item_clicked(self, gesture, n_press, x, y):
        """Handle sidebar item click"""
        widget = gesture.get_widget()
        section_id = getattr(widget, 'section_id', None)
        
        if section_id:
            self.main_stack.set_visible_child_name(section_id)
            
            # Update selection styling
            for child in widget.get_parent().get_children():
                child.remove_css_class("selected")
            widget.add_css_class("selected")
            
            self.current_section = section_id
    
    async def _on_execute_intent_clicked(self, button):
        """Handle intent execution button click"""
        intent_text = self.intent_entry.get_text().strip()
        
        if not intent_text:
            return
        
        try:
            # Process intent
            intent = await self.intent_engine.process_intent(intent_text)
            
            if intent.confidence < 0.5:
                self._show_error_dialog("Low confidence", "I'm not sure what you want to do. Please be more specific.")
                return
            
            if intent.requires_confirmation:
                confirmed = self._show_confirmation_dialog(
                    "Confirm Intent", 
                    f"I will {intent.estimated_impact.lower()}. Proceed?",
                    intent.execution_plan
                )
                if not confirmed:
                    return
            
            # Execute intent
            results = await self.intent_engine.execute_intent(intent)
            
            # Show results
            if results['success']:
                self._show_success_dialog("Intent Applied", "\n".join(results['user_messages']))
                self.intent_entry.set_text("")
            else:
                self._show_error_dialog("Execution Failed", "\n".join(results['user_messages']))
        
        except Exception as e:
            self._show_error_dialog("Error", f"Failed to execute intent: {str(e)}")
    
    def _on_suggestion_clicked(self, button, suggestion: str):
        """Handle suggestion chip click"""
        self.intent_entry.set_text(suggestion)
        self.intent_entry.grab_focus()
    
    async def _on_scan_devices_clicked(self, button):
        """Handle device scan button click"""
        button.set_sensitive(False)
        button.set_label("Scanning...")
        
        try:
            devices = await self.driver_manager.scan_hardware()
            self._populate_devices_list()
            
            self._show_success_dialog("Scan Complete", f"Found {len(devices)} devices")
        except Exception as e:
            self._show_error_dialog("Scan Failed", f"Could not scan devices: {str(e)}")
        finally:
            button.set_sensitive(True)
            button.set_label("Scan for Hardware Changes")
    
    def _on_theme_changed(self, toggle, theme_name: str):
        """Handle theme selection change"""
        if toggle.get_active():
            self.current_theme = theme_name
            # Apply theme changes
            self._apply_theme()
            self.logger.info(f"Theme changed to: {theme_name}")
    
    def _on_privacy_switch_changed(self, switch, param_spec, option_name: str):
        """Handle privacy switch changes"""
        is_enabled = switch.get_active()
        self.logger.info(f"Privacy option {option_name} changed to: {is_enabled}")
        # Apply privacy changes
    
    def _populate_devices_list(self):
        """Populate the devices list"""
        # Clear existing items
        for child in self.devices_list.get_first_child():
            self.devices_list.remove(child)
        
        # Add devices
        devices = self.driver_manager.get_all_devices()
        
        for device in devices:
            device_row = self._create_device_row(device)
            self.devices_list.append(device_row)
    
    def _create_device_row(self, device) -> Gtk.Widget:
        """Create a row for a device"""
        row = Adw.ActionRow()
        row.set_title(device.device_name)
        row.set_subtitle(device.vendor_name)
        
        # Status indicator
        status_class = "status-good" if device.driver_status == "installed" else "status-warning" if device.driver_status == "missing" else "status-error"
        status_indicator = Gtk.Label()
        status_indicator.add_css_class(f"status-indicator {status_class}")
        row.add_prefix(status_indicator)
        
        # Status text
        status_text = "Driver Installed" if device.driver_status == "installed" else "Driver Missing" if device.driver_status == "missing" else "Generic Driver"
        status_label = Gtk.Label(label=status_text)
        status_label.add_css_class("caption")
        row.add_suffix(status_label)
        
        # Install button if driver missing
        if device.driver_status == "missing" and device.recommended_driver:
            install_button = Gtk.Button(label="Install")
            install_button.add_css_class("suggested-action")
            install_button.connect("clicked", self._on_install_driver_clicked, device.device_id)
            row.add_suffix(install_button)
        
        return row
    
    async def _on_install_driver_clicked(self, button, device_id: str):
        """Handle driver install button click"""
        button.set_sensitive(False)
        button.set_label("Installing...")
        
        try:
            success = await self.driver_manager.install_driver(device_id)
            
            if success:
                self._show_success_dialog("Driver Installed", "Driver was successfully installed")
                self._populate_devices_list()
            else:
                self._show_error_dialog("Installation Failed", "Could not install the driver")
        except Exception as e:
            self._show_error_dialog("Installation Error", f"Error: {str(e)}")
        finally:
            button.set_sensitive(True)
            button.set_label("Install")
    
    def _show_confirmation_dialog(self, title: str, message: str, details: List[str] = None) -> bool:
        """Show confirmation dialog"""
        dialog = Adw.MessageDialog.new()
        dialog.set_heading(title)
        dialog.set_body(message)
        
        if details:
            for detail in details:
                dialog.add_response(detail, detail)
        
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("confirm", "Confirm")
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        
        dialog.connect("response", lambda dialog, response: dialog.destroy())
        dialog.show()
        
        # For now, always return False - in a real implementation, this would be async
        return False
    
    def _show_success_dialog(self, title: str, message: str):
        """Show success dialog"""
        dialog = Adw.MessageDialog.new()
        dialog.set_heading(title)
        dialog.set_body(message)
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.connect("response", lambda dialog, response: dialog.destroy())
        dialog.show()
    
    def _show_error_dialog(self, title: str, message: str):
        """Show error dialog"""
        dialog = Adw.MessageDialog.new()
        dialog.set_heading(title)
        dialog.set_body(message)
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.connect("response", lambda dialog, response: dialog.destroy())
        dialog.show()
    
    def _on_window_close(self, window):
        """Handle window close"""
        window.destroy()
    
    def show(self):
        """Show the settings window"""
        if self.window:
            self.window.show()

# Global settings UI instance
_settings_ui = None

def get_settings_ui() -> SettingsUI:
    """Get global settings UI instance"""
    global _settings_ui
    if _settings_ui is None:
        _settings_ui = SettingsUI()
    return _settings_ui

def show_settings():
    """Show the settings window"""
    settings_ui = get_settings_ui()
    settings_ui.show()