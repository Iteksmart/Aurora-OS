"""
Aurora OS - Taskbar AI Assistant
AI assistant integrated directly into the taskbar for instant access
Provides voice, text, and visual interaction capabilities
"""

import os
import sys
import json
import asyncio
import threading
import time
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
except ImportError:
    # Fallback for non-GTK environments
    Gtk = None
    Adw = None

from .local_llm_engine import get_llm_engine, AIRequest, AIResponse
from ..voice.voice_interface import VoiceInterface
from ..agents.task_agent import TaskAgent

@dataclass
class TaskbarPosition:
    """Taskbar position configuration"""
    x: int = 0
    y: int = 0
    width: int = 400
    height: int = 600
    anchor: str = "bottom-right"  # bottom-right, bottom-left, top-right, top-left

class TaskbarAssistant:
    """
    AI Assistant integrated into the Aurora OS taskbar
    Provides instant access to AI capabilities
    """
    
    def __init__(self, position: TaskbarPosition = None):
        self.position = position or TaskbarPosition()
        self.llm_engine = get_llm_engine()
        self.voice_interface = VoiceInterface()
        self.task_agent = TaskAgent()
        
        # UI state
        self.is_visible = False
        self.is_listening = False
        self.current_theme = "aurora"
        self.conversation_history = []
        self.suggestions = []
        
        # GTK components (if available)
        self.window = None
        self.chat_container = None
        self.input_entry = None
        self.suggestion_box = None
        self.voice_button = None
        
        self.logger = logging.getLogger("Aurora.TaskbarAssistant")
        self._setup_logging()
        
        # Initialize UI
        self._init_ui()
        
    def _setup_logging(self):
        """Setup logging"""
        log_dir = Path("/var/log/aurora")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(log_dir / "taskbar_assistant.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _init_ui(self):
        """Initialize the user interface"""
        if Gtk is None:
            self.logger.warning("GTK not available, running in headless mode")
            return
        
        # Create main window
        self.window = Adw.Window()
        self.window.set_title("Aurora Assistant")
        self.window.set_default_size(self.position.width, self.position.height)
        self.window.set_resizable(True)
        
        # Set window properties for taskbar integration
        self.window.set_decorated(False)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_keep_above(True)
        
        # Apply Aurora theme
        self._apply_aurora_theme()
        
        # Create main layout
        self._create_main_layout()
        
        # Position window
        self._position_window()
        
        # Connect signals
        self._connect_signals()
        
        self.logger.info("Taskbar Assistant UI initialized")
    
    def _apply_aurora_theme(self):
        """Apply Aurora OS theme styling"""
        if self.window is None:
            return
            
        # Create CSS provider for Aurora theme
        css_provider = Gtk.CssProvider()
        css_data = """
        window {
            background: linear-gradient(135deg, rgba(88, 86, 214, 0.95), rgba(175, 82, 222, 0.95));
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            backdrop-filter: blur(20px);
        }
        
        .chat-container {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            margin: 10px;
            padding: 10px;
        }
        
        .message-bubble {
            background: rgba(255, 255, 255, 0.9);
            border-radius: 18px;
            padding: 12px 16px;
            margin: 4px;
            max-width: 80%;
        }
        
        .user-message {
            background: linear-gradient(135deg, #5856d6, #af52de);
            color: white;
            margin-left: auto;
        }
        
        .ai-message {
            background: rgba(255, 255, 255, 0.9);
            color: #333;
            margin-right: auto;
        }
        
        .input-box {
            background: rgba(255, 255, 255, 0.9);
            border-radius: 24px;
            border: none;
            padding: 12px 20px;
            margin: 10px;
            font-size: 14px;
        }
        
        .voice-button {
            background: linear-gradient(135deg, #ff3b30, #ff9500);
            border-radius: 50%;
            min-width: 48px;
            min-height: 48px;
            margin: 10px;
            border: none;
            color: white;
            font-weight: bold;
        }
        
        .voice-button.listening {
            background: linear-gradient(135deg, #30d158, #007aff);
            animation: pulse 1.5s infinite;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        
        .suggestion-chip {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 16px;
            padding: 6px 12px;
            margin: 2px;
            font-size: 12px;
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
        
        .suggestion-chip:hover {
            background: rgba(255, 255, 255, 0.3);
        }
        """
        
        css_provider.load_from_data(css_data.encode())
        
        # Apply to display
        style_context = self.window.get_style_context()
        style_context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    
    def _create_main_layout(self):
        """Create the main UI layout"""
        if self.window is None:
            return
            
        # Create main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window.set_child(main_box)
        
        # Header
        header_box = self._create_header()
        main_box.append(header_box)
        
        # Chat container
        self.chat_container = self._create_chat_container()
        main_box.append(self.chat_container)
        
        # Input area
        input_area = self._create_input_area()
        main_box.append(input_area)
    
    def _create_header(self):
        """Create the header section"""
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.set_margin_top(10)
        header_box.set_margin_start(10)
        header_box.set_margin_end(10)
        
        # Avatar
        avatar = Adw.Avatar.new(32, "Aurora", True)
        header_box.append(avatar)
        
        # Title
        title_label = Gtk.Label(label="Aurora Assistant")
        title_label.add_css_class("title-4")
        title_label.set_hexpand(True)
        title_label.set_halign(Gtk.Align.START)
        header_box.append(title_label)
        
        # Close button
        close_button = Gtk.Button(icon_name="window-close-symbolic")
        close_button.add_css_class("flat")
        close_button.connect("clicked", self._on_close_clicked)
        header_box.append(close_button)
        
        return header_box
    
    def _create_chat_container(self):
        """Create the chat message container"""
        # Scrolled window for messages
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        
        # Message list
        message_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        message_list.add_css_class("chat-container")
        scrolled.set_child(message_list)
        
        self.message_list = message_list
        return scrolled
    
    def _create_input_area(self):
        """Create the input area with text and voice"""
        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        input_box.set_margin_bottom(10)
        input_box.set_margin_start(10)
        input_box.set_margin_end(10)
        
        # Text input
        self.input_entry = Gtk.Entry()
        self.input_entry.set_placeholder_text("Ask Aurora anything...")
        self.input_entry.add_css_class("input-box")
        self.input_entry.set_hexpand(True)
        self.input_entry.connect("activate", self._on_text_input)
        self.input_entry.connect("changed", self._on_input_changed)
        input_box.append(self.input_entry)
        
        # Voice button
        self.voice_button = Gtk.Button(label="🎤")
        self.voice_button.add_css_class("voice-button")
        self.voice_button.connect("clicked", self._on_voice_clicked)
        input_box.append(self.voice_button)
        
        # Suggestions box
        self.suggestion_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.suggestion_box.set_margin_start(10)
        self.suggestion_box.set_margin_end(10)
        self.suggestion_box.set_margin_bottom(5)
        
        # Add suggestion area
        main_input_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_input_area.append(input_box)
        main_input_area.append(self.suggestion_box)
        
        return main_input_area
    
    def _position_window(self):
        """Position the window based on configuration"""
        if self.window is None:
            return
            
        display = Gdk.Display.get_default()
        monitor = display.get_monitor_at_point(0, 0)
        monitor_geometry = monitor.get_geometry()
        
        # Calculate position based on anchor
        if self.position.anchor == "bottom-right":
            x = monitor_geometry.width - self.position.width - 20
            y = monitor_geometry.height - self.position.height - 60
        elif self.position.anchor == "bottom-left":
            x = 20
            y = monitor_geometry.height - self.position.height - 60
        elif self.position.anchor == "top-right":
            x = monitor_geometry.width - self.position.width - 20
            y = 60
        else:  # top-left
            x = 20
            y = 60
        
        self.window.move(x, y)
    
    def _connect_signals(self):
        """Connect UI signals"""
        if self.window is None:
            return
            
        # Window focus out - hide assistant
        self.window.connect("focus-out-event", self._on_focus_out)
        
        # Escape key - hide assistant
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.window.add_controller(key_controller)
    
    def _on_close_clicked(self, button):
        """Handle close button click"""
        self.hide()
    
    def _on_focus_out(self, window, event):
        """Handle focus out event"""
        # Delay hiding to allow clicking on suggestions
        GLib.timeout_add(200, self.hide)
    
    def _on_key_pressed(self, controller, keyval, keycode, state):
        """Handle key press events"""
        if keyval == Gdk.KEY_Escape:
            self.hide()
            return True
        return False
    
    def _on_text_input(self, entry):
        """Handle text input submission"""
        text = entry.get_text().strip()
        if text:
            asyncio.create_task(self._process_text_input(text))
            entry.set_text("")
    
    def _on_input_changed(self, entry):
        """Handle input text changes for suggestions"""
        text = entry.get_text().strip()
        if len(text) > 2:
            self._update_suggestions(text)
        else:
            self._clear_suggestions()
    
    def _on_voice_clicked(self, button):
        """Handle voice button click"""
        if self.is_listening:
            self.stop_voice_input()
        else:
            self.start_voice_input()
    
    async def _process_text_input(self, text: str):
        """Process text input and generate response"""
        # Add user message to chat
        self._add_message(text, is_user=True)
        
        # Generate AI response
        request = AIRequest(
            prompt=text,
            context=self._get_current_context(),
            system_prompt=self._get_system_prompt_for_input(text)
        )
        
        response = await self.llm_engine.generate_response(request)
        
        # Add AI response to chat
        self._add_message(response.text, is_user=False)
        
        # Store in conversation history
        self.conversation_history.append({
            "user": text,
            "assistant": response.text,
            "timestamp": datetime.now().isoformat()
        })
        
        # Check if this is a task that needs execution
        await self._check_for_task_execution(text, response.text)
    
    def _add_message(self, text: str, is_user: bool):
        """Add a message to the chat"""
        if self.message_list is None:
            return
            
        # Create message bubble
        message_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        message_label = Gtk.Label(label=text)
        message_label.set_wrap(True)
        message_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        message_label.set_xalign(0 if is_user else 0)
        
        message_label.add_css_class("message-bubble")
        message_label.add_css_class("user-message" if is_user else "ai-message")
        
        if is_user:
            # User messages align right
            container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            container.set_halign(Gtk.Align.END)
            container.append(message_label)
            message_box.append(container)
        else:
            # AI messages align left
            message_box.append(message_label)
        
        self.message_list.append(message_box)
        
        # Scroll to bottom
        parent = self.message_list.get_parent()
        if hasattr(parent, 'get_vadjustment'):
            vadj = parent.get_vadjustment()
            vadj.set_value(vadj.get_upper() - vadj.get_page_size())
    
    def _get_current_context(self) -> str:
        """Get current context for AI"""
        context_parts = []
        
        # Add system context
        if hasattr(self.llm_engine, 'system_context'):
            system_context = self.llm_engine.system_context
            if system_context.get('system_resources'):
                resources = system_context['system_resources']
                context_parts.append(f"System: CPU {resources.get('cpu_percent', 0)}%, Memory {resources.get('memory_percent', 0)}%")
        
        # Add recent conversation context
        if len(self.conversation_history) > 0:
            recent = self.conversation_history[-1]
            context_parts.append(f"Previous: {recent['user'][:100]}...")
        
        return " | ".join(context_parts) if context_parts else None
    
    def _get_system_prompt_for_input(self, text: str) -> str:
        """Get appropriate system prompt based on input"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['fix', 'error', 'problem', 'troubleshoot']):
            return self.llm_engine.system_prompts["system_admin"]
        elif any(word in text_lower for word in ['do', 'execute', 'run', 'task', 'complete']):
            return self.llm_engine.system_prompts["task_executor"]
        elif any(word in text_lower for word in ['optimize', 'improve', 'schedule', 'plan']):
            return self.llm_engine.system_prompts["life_optimizer"]
        else:
            return self.llm_engine.system_prompts["assistant"]
    
    async def _check_for_task_execution(self, user_input: str, ai_response: str):
        """Check if the response contains tasks to execute"""
        # Use task agent to identify executable actions
        tasks = await self.task_agent.identify_tasks(user_input, ai_response)
        
        for task in tasks:
            # Execute tasks and show progress
            self._add_message(f"🔧 Executing: {task.description}", is_user=False)
            
            try:
                result = await self.task_agent.execute_task(task)
                self._add_message(f"✅ Completed: {result}", is_user=False)
            except Exception as e:
                self._add_message(f"❌ Failed: {str(e)}", is_user=False)
    
    def _update_suggestions(self, text: str):
        """Update suggestion chips based on input"""
        suggestions = self._generate_suggestions(text)
        self._show_suggestions(suggestions)
    
    def _generate_suggestions(self, text: str) -> List[str]:
        """Generate relevant suggestions"""
        text_lower = text.lower()
        
        if "open" in text_lower:
            return ["open firefox", "open settings", "open terminal", "open files"]
        elif "fix" in text_lower:
            return ["fix slow performance", "fix wifi", "fix audio", "fix display"]
        elif "check" in text_lower:
            return ["check system health", "check updates", "check battery", "check storage"]
        elif "optimize" in text_lower:
            return ["optimize battery", "optimize performance", "optimize storage", "optimize startup"]
        else:
            return ["help", "system status", "what can you do?", "settings"]
    
    def _show_suggestions(self, suggestions: List[str]):
        """Show suggestion chips"""
        if self.suggestion_box is None:
            return
            
        # Clear existing suggestions
        for child in self.suggestion_box.get_first_child().get_children():
            self.suggestion_box.remove(child)
        
        # Add new suggestions
        for suggestion in suggestions:
            button = Gtk.Button(label=suggestion)
            button.add_css_class("suggestion-chip")
            button.connect("clicked", lambda btn, s=suggestion: self._on_suggestion_clicked(s))
            self.suggestion_box.append(button)
        
        self.suggestion_box.show()
    
    def _clear_suggestions(self):
        """Clear suggestion chips"""
        if self.suggestion_box is None:
            return
            
        for child in self.suggestion_box.get_first_child().get_children():
            self.suggestion_box.remove(child)
    
    def _on_suggestion_clicked(self, suggestion: str):
        """Handle suggestion chip click"""
        self.input_entry.set_text(suggestion)
        self.input_entry.grab_focus()
    
    def show(self):
        """Show the taskbar assistant"""
        if self.window is None:
            return
            
        self.is_visible = True
        self.window.show()
        self.input_entry.grab_focus()
        
        # Generate welcome message if this is first interaction
        if len(self.conversation_history) == 0:
            welcome_msg = "Hi! I'm Aurora, your AI assistant. I can help you manage your system, find information, and complete tasks. What can I help you with today?"
            self._add_message(welcome_msg, is_user=False)
    
    def hide(self):
        """Hide the taskbar assistant"""
        if self.window is None:
            return
            
        self.is_visible = False
        self.window.hide()
        
        # Stop voice input if active
        if self.is_listening:
            self.stop_voice_input()
    
    def toggle(self):
        """Toggle visibility"""
        if self.is_visible:
            self.hide()
        else:
            self.show()
    
    def start_voice_input(self):
        """Start voice input"""
        if not self.voice_interface.is_available():
            self._add_message("🎤 Voice input not available. Please check microphone permissions.", is_user=False)
            return
        
        self.is_listening = True
        self.voice_button.add_css_class("listening")
        self.voice_button.set_label("⏹️")
        
        # Start listening in background
        threading.Thread(target=self._voice_input_loop, daemon=True).start()
    
    def stop_voice_input(self):
        """Stop voice input"""
        self.is_listening = False
        self.voice_button.remove_css_class("listening")
        self.voice_button.set_label("🎤")
        
        if self.voice_interface.is_listening():
            self.voice_interface.stop_listening()
    
    def _voice_input_loop(self):
        """Voice input loop"""
        try:
            # Start listening
            self.voice_interface.start_listening()
            
            # Wait for speech recognition
            while self.is_listening:
                text = self.voice_interface.get_recognized_text()
                if text:
                    # Update UI with recognized text
                    GLib.idle_add(self.input_entry.set_text, text)
                    GLib.idle_add(self._process_text_input, text)
                    break
                
                time.sleep(0.1)
                
        except Exception as e:
            self.logger.error(f"Voice input error: {e}")
            GLib.idle_add(self._add_message, f"🎤 Voice input error: {str(e)}", False)
        
        finally:
            GLib.idle_add(self.stop_voice_input)
    
    def update_theme(self, theme_name: str):
        """Update the assistant theme"""
        self.current_theme = theme_name
        # Re-apply theme styles
        self._apply_aurora_theme()
    
    def set_position(self, position: TaskbarPosition):
        """Update taskbar position"""
        self.position = position
        if self.window:
            self._position_window()

# Global taskbar assistant instance
_taskbar_assistant = None

def get_taskbar_assistant() -> TaskbarAssistant:
    """Get global taskbar assistant instance"""
    global _taskbar_assistant
    if _taskbar_assistant is None:
        _taskbar_assistant = TaskbarAssistant()
    return _taskbar_assistant

def show_assistant():
    """Show the taskbar assistant"""
    assistant = get_taskbar_assistant()
    assistant.show()

def hide_assistant():
    """Hide the taskbar assistant"""
    assistant = get_taskbar_assistant()
    assistant.hide()

def toggle_assistant():
    """Toggle taskbar assistant visibility"""
    assistant = get_taskbar_assistant()
    assistant.toggle()