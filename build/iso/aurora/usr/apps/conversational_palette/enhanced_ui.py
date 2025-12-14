"""
Enhanced Aurora Conversational Palette
Modern, animated conversational interface with AI integration
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import uuid

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../..'))
from desktop.aurora_shell.ui.modern_theme import ModernTheme, AnimationManager, ThemeColor

class MessageType(Enum):
    """Message types in conversation"""
    USER = "user"
    AI = "ai"
    SYSTEM = "system"
    ERROR = "error"

@dataclass
class Message:
    """Conversation message"""
    id: str
    type: MessageType
    content: str
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class SuggestionChip:
    """Suggestion chip for quick actions"""
    id: str
    text: str
    action: str
    icon: Optional[str] = None
    color: Optional[str] = None

class EnhancedConversationalUI:
    """Enhanced conversational palette with modern UI"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.theme = ModernTheme()
        self.animation_manager = AnimationManager(self.theme)
        
        # Conversation state
        self.messages: List[Message] = []
        self.current_input = ""
        self.is_typing = False
        self.suggestions: List[SuggestionChip] = []
        
        # UI state
        self.is_minimized = False
        self.is_fullscreen = False
        self.theme_mode = "dark"
        
        # Initialize UI components
        self._init_suggestions()
        self._init_ui_state()
    
    def _init_suggestions(self):
        """Initialize default suggestion chips"""
        self.suggestions = [
            SuggestionChip("1", "Open Firefox", "open_firefox", "🌐", ThemeColor.PRIMARY.value),
            SuggestionChip("2", "Find Documents", "find_documents", "📁", ThemeColor.SECONDARY.value),
            SuggestionChip("3", "System Status", "system_status", "💻", ThemeColor.SUCCESS.value),
            SuggestionChip("4", "Help & Support", "help_support", "❓", ThemeColor.WARNING.value),
        ]
    
    def _init_ui_state(self):
        """Initialize UI state"""
        self.ui_config = {
            "width": 400,
            "height": 600,
            "min_width": 300,
            "min_height": 400,
            "max_width": 800,
            "max_height": 1000,
            "position": {"x": 100, "y": 100},
            "always_on_top": False,
            "show_timestamps": True,
            "show_typing_indicator": True,
            "auto_suggestions": True,
        }
    
    def generate_html(self) -> str:
        """Generate the complete HTML for the conversational palette"""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aurora Conversational Palette</title>
    <style>
        {self.theme.generate_theme_css()}
        
        /* Conversational Palette Specific Styles */
        .aurora-palette {{
            position: fixed;
            width: {self.ui_config['width']}px;
            height: {self.ui_config['height']}px;
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
            border-radius: var(--aurora-radius-xl);
            box-shadow: var(--aurora-shadow-xl), 0 0 40px rgba(102, 126, 234, 0.3);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            z-index: var(--aurora-z-modal);
            font-family: var(--aurora-font-sans);
            color: var(--aurora-light);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .aurora-palette-header {{
            padding: var(--aurora-space-4);
            background: rgba(0, 0, 0, 0.2);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: move;
        }}
        
        .aurora-palette-title {{
            display: flex;
            align-items: center;
            gap: var(--aurora-space-3);
            font-weight: 600;
            font-size: 1rem;
        }}
        
        .aurora-palette-controls {{
            display: flex;
            gap: var(--aurora-space-2);
        }}
        
        .aurora-control-btn {{
            width: 32px;
            height: 32px;
            border-radius: 50%;
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
            background: rgba(255, 255, 255, 0.1);
            color: var(--aurora-light);
        }}
        
        .aurora-control-btn:hover {{
            background: rgba(255, 255, 255, 0.2);
            transform: scale(1.1);
        }}
        
        .aurora-messages-container {{
            flex: 1;
            overflow-y: auto;
            padding: var(--aurora-space-4);
            display: flex;
            flex-direction: column;
            gap: var(--aurora-space-4);
        }}
        
        .aurora-message {{
            display: flex;
            gap: var(--aurora-space-3);
            animation: aurora-slide-up 0.3s ease-out;
            max-width: 85%;
        }}
        
        .aurora-message.user {{
            align-self: flex-end;
            flex-direction: row-reverse;
        }}
        
        .aurora-message.ai {{
            align-self: flex-start;
        }}
        
        .aurora-message.system {{
            align-self: center;
            max-width: 70%;
        }}
        
        .aurora-message-avatar {{
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            flex-shrink: 0;
        }}
        
        .aurora-message.user .aurora-message-avatar {{
            background: var(--aurora-gradient);
        }}
        
        .aurora-message.ai .aurora-message-avatar {{
            background: var(--aurora-secondary);
        }}
        
        .aurora-message.system .aurora-message-avatar {{
            background: var(--aurora-dark);
        }}
        
        .aurora-message-content {{
            background: rgba(255, 255, 255, 0.1);
            padding: var(--aurora-space-3) var(--aurora-space-4);
            border-radius: var(--aurora-radius-lg);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .aurora-message.user .aurora-message-content {{
            background: var(--aurora-gradient);
        }}
        
        .aurora-message-timestamp {{
            font-size: 0.75rem;
            opacity: 0.7;
            margin-top: var(--aurora-space-1);
        }}
        
        .aurora-suggestions {{
            padding: var(--aurora-space-4);
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .aurora-suggestion-chips {{
            display: flex;
            flex-wrap: wrap;
            gap: var(--aurora-space-2);
            margin-bottom: var(--aurora-space-3);
        }}
        
        .aurora-suggestion-chip {{
            padding: var(--aurora-space-2) var(--aurora-space-3);
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: var(--aurora-radius-full);
            font-size: 0.875rem;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: var(--aurora-space-1);
        }}
        
        .aurora-suggestion-chip:hover {{
            background: rgba(255, 255, 255, 0.2);
            transform: translateY(-2px);
        }}
        
        .aurora-input-container {{
            padding: var(--aurora-space-4);
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .aurora-input-wrapper {{
            display: flex;
            gap: var(--aurora-space-2);
            align-items: flex-end;
        }}
        
        .aurora-input {{
            flex: 1;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: var(--aurora-light);
            border-radius: var(--aurora-radius-lg);
            padding: var(--aurora-space-3) var(--aurora-space-4);
            font-size: 0.875rem;
            resize: none;
            min-height: 44px;
            max-height: 120px;
            transition: all 0.2s ease;
        }}
        
        .aurora-input:focus {{
            outline: none;
            border-color: var(--aurora-primary);
            background: rgba(255, 255, 255, 0.15);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2);
        }}
        
        .aurora-send-btn {{
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: var(--aurora-gradient);
            border: none;
            color: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
        }}
        
        .aurora-send-btn:hover:not(:disabled) {{
            transform: scale(1.1);
            box-shadow: var(--aurora-glow-shadow);
        }}
        
        .aurora-send-btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}
        
        .aurora-typing-indicator {{
            display: none;
            align-items: center;
            gap: var(--aurora-space-3);
            padding: var(--aurora-space-3);
        }}
        
        .aurora-typing-indicator.active {{
            display: flex;
        }}
        
        /* Scrollbar Styling */
        .aurora-messages-container::-webkit-scrollbar {{
            width: 6px;
        }}
        
        .aurora-messages-container::-webkit-scrollbar-track {{
            background: rgba(255, 255, 255, 0.05);
        }}
        
        .aurora-messages-container::-webkit-scrollbar-thumb {{
            background: rgba(255, 255, 255, 0.2);
            border-radius: 3px;
        }}
        
        .aurora-messages-container::-webkit-scrollbar-thumb:hover {{
            background: rgba(255, 255, 255, 0.3);
        }}
        
        /* Responsive Design */
        @media (max-width: 480px) {{
            .aurora-palette {{
                width: 100vw;
                height: 100vh;
                border-radius: 0;
            }}
            
            .aurora-message {{
                max-width: 95%;
            }}
        }}
        
        /* Minimized State */
        .aurora-palette.minimized {{
            height: 60px;
        }}
        
        .aurora-palette.minimized .aurora-messages-container,
        .aurora-palette.minimized .aurora-suggestions,
        .aurora-palette.minimized .aurora-input-container {{
            display: none;
        }}
        
        /* Fullscreen State */
        .aurora-palette.fullscreen {{
            width: 100vw;
            height: 100vh;
            border-radius: 0;
        }}
        
        .aurora-palette.fullscreen .aurora-messages-container {{
            max-width: 800px;
            margin: 0 auto;
        }}
    </style>
</head>
<body>
    <div class="aurora-palette" id="aurora-palette">
        <!-- Header -->
        <div class="aurora-palette-header">
            <div class="aurora-palette-title">
                <span style="font-size: 1.5rem;">✨</span>
                <span>Aurora Assistant</span>
                <span class="aurora-typing-indicator" id="typing-indicator">
                    <div class="aurora-typing-dot"></div>
                    <div class="aurora-typing-dot"></div>
                    <div class="aurora-typing-dot"></div>
                </span>
            </div>
            <div class="aurora-palette-controls">
                <button class="aurora-control-btn" onclick="toggleMinimize()" title="Minimize">−</button>
                <button class="aurora-control-btn" onclick="toggleFullscreen()" title="Fullscreen">⛶</button>
                <button class="aurora-control-btn" onclick="closePalette()" title="Close">✕</button>
            </div>
        </div>
        
        <!-- Messages Container -->
        <div class="aurora-messages-container" id="messages-container">
            <!-- Welcome Message -->
            <div class="aurora-message ai">
                <div class="aurora-message-avatar">🤖</div>
                <div>
                    <div class="aurora-message-content">
                        Hello! I'm Aurora, your AI assistant. I can help you with tasks, find information, and optimize your system. How can I assist you today?
                    </div>
                    <div class="aurora-message-timestamp">Just now</div>
                </div>
            </div>
        </div>
        
        <!-- Suggestions -->
        <div class="aurora-suggestions">
            <div class="aurora-suggestion-chips" id="suggestion-chips">
                <!-- Suggestion chips will be added here -->
            </div>
        </div>
        
        <!-- Input Area -->
        <div class="aurora-input-container">
            <div class="aurora-input-wrapper">
                <textarea 
                    class="aurora-input" 
                    id="message-input" 
                    placeholder="Type your message..."
                    rows="1"
                    onkeydown="handleInputKeydown(event)"
                    oninput="adjustTextareaHeight(this)"
                ></textarea>
                <button class="aurora-send-btn" id="send-btn" onclick="sendMessage()" title="Send">
                    <span>➤</span>
                </button>
            </div>
        </div>
    </div>

    <script>
        // Initialize Aurora Conversational Palette
        class AuroraPalette {{
            constructor() {{
                this.messages = [];
                this.isTyping = false;
                this.suggestions = [
                    {{ id: "1", text: "Open Firefox", action: "open_firefox", icon: "🌐" }},
                    {{ id: "2", text: "Find Documents", action: "find_documents", icon: "📁" }},
                    {{ id: "3", text: "System Status", action: "system_status", icon: "💻" }},
                    {{ id: "4", text: "Help & Support", action: "help_support", icon: "❓" }},
                ];
                
                this.init();
            }}
            
            init() {{
                this.renderSuggestions();
                this.setupEventListeners();
                this.focusInput();
            }}
            
            setupEventListeners() {{
                const input = document.getElementById('message-input');
                const sendBtn = document.getElementById('send-btn');
                
                input.addEventListener('keypress', (e) => {{
                    if (e.key === 'Enter' && !e.shiftKey) {{
                        e.preventDefault();
                        this.sendMessage();
                    }}
                }});
                
                sendBtn.addEventListener('click', () => this.sendMessage());
            }}
            
            focusInput() {{
                document.getElementById('message-input').focus();
            }}
            
            renderSuggestions() {{
                const container = document.getElementById('suggestion-chips');
                container.innerHTML = this.suggestions.map(suggestion => `
                    <div class="aurora-suggestion-chip" onclick="handleSuggestion('${{suggestion.action}}')">
                        <span>${{suggestion.icon}}</span>
                        <span>${{suggestion.text}}</span>
                    </div>
                `).join('');
            }}
            
            addMessage(type, content, timestamp = new Date()) {{
                const message = {{
                    id: uuidv4(),
                    type: type,
                    content: content,
                    timestamp: timestamp
                }};
                
                this.messages.push(message);
                this.renderMessage(message);
                this.scrollToBottom();
            }}
            
            renderMessage(message) {{
                const container = document.getElementById('messages-container');
                const messageEl = document.createElement('div');
                messageEl.className = `aurora-message ${{message.type}}`;
                messageEl.innerHTML = `
                    <div class="aurora-message-avatar">
                        ${{message.type === 'user' ? '👤' : message.type === 'ai' ? '🤖' : '⚙️'}}
                    </div>
                    <div>
                        <div class="aurora-message-content">${{message.content}}</div>
                        <div class="aurora-message-timestamp">${{this.formatTime(message.timestamp)}}</div>
                    </div>
                `;
                
                container.appendChild(messageEl);
                
                // Animate message appearance
                messageEl.style.animation = 'aurora-slide-up 0.3s ease-out';
            }}
            
            sendMessage() {{
                const input = document.getElementById('message-input');
                const message = input.value.trim();
                
                if (!message) return;
                
                // Add user message
                this.addMessage('user', message);
                
                // Clear input
                input.value = '';
                this.adjustTextareaHeight(input);
                
                // Show typing indicator
                this.showTypingIndicator();
                
                // Simulate AI response
                setTimeout(() => {{
                    this.hideTypingIndicator();
                    this.processUserMessage(message);
                }}, 1500);
            }}
            
            processUserMessage(message) {{
                // Simple response logic (would connect to actual AI)
                const responses = {{
                    'open_firefox': 'Opening Firefox for you...',
                    'find_documents': 'Searching for your documents...',
                    'system_status': 'Checking system status...',
                    'help_support': 'I\'m here to help! What do you need assistance with?'
                }};
                
                const response = responses[message] || 
                    `I understand you said: "${{message}}". I'm processing your request...`;
                
                this.addMessage('ai', response);
            }}
            
            showTypingIndicator() {{
                const indicator = document.getElementById('typing-indicator');
                indicator.classList.add('active');
                this.isTyping = true;
            }}
            
            hideTypingIndicator() {{
                const indicator = document.getElementById('typing-indicator');
                indicator.classList.remove('active');
                this.isTyping = false;
            }}
            
            scrollToBottom() {{
                const container = document.getElementById('messages-container');
                container.scrollTop = container.scrollHeight;
            }}
            
            formatTime(timestamp) {{
                const now = new Date();
                const diff = now - timestamp;
                
                if (diff < 60000) return 'Just now';
                if (diff < 3600000) return `${{Math.floor(diff / 60000)}}m ago`;
                if (diff < 86400000) return `${{Math.floor(diff / 3600000)}}h ago`;
                return timestamp.toLocaleDateString();
            }}
            
            adjustTextareaHeight(textarea) {{
                textarea.style.height = 'auto';
                textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
            }}
        }}
        
        // Global functions
        function toggleMinimize() {{
            const palette = document.getElementById('aurora-palette');
            palette.classList.toggle('minimized');
        }}
        
        function toggleFullscreen() {{
            const palette = document.getElementById('aurora-palette');
            palette.classList.toggle('fullscreen');
        }}
        
        function closePalette() {{
            const palette = document.getElementById('aurora-palette');
            palette.style.display = 'none';
        }}
        
        function handleSuggestion(action) {{
            const input = document.getElementById('message-input');
            const suggestionTexts = {{
                'open_firefox': 'Open Firefox',
                'find_documents': 'Find my documents',
                'system_status': 'Show system status',
                'help_support': 'Help and support'
            }};
            
            input.value = suggestionTexts[action] || action;
            input.focus();
        }}
        
        function handleInputKeydown(event) {{
            if (event.key === 'Enter' && !event.shiftKey) {{
                event.preventDefault();
                auroraPalette.sendMessage();
            }}
        }}
        
        function adjustTextareaHeight(textarea) {{
            auroraPalette.adjustTextareaHeight(textarea);
        }}
        
        function sendMessage() {{
            auroraPalette.sendMessage();
        }}
        
        // UUID generator
        function uuidv4() {{
            return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
                (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
            );
        }}
        
        // Initialize the palette
        const auroraPalette = new AuroraPalette();
        
        // Make palette draggable
        let isDragging = false;
        let currentX;
        let currentY;
        let initialX;
        let initialY;
        let xOffset = 0;
        let yOffset = 0;
        
        const palette = document.getElementById('aurora-palette');
        const header = document.querySelector('.aurora-palette-header');
        
        header.addEventListener('mousedown', dragStart);
        document.addEventListener('mousemove', drag);
        document.addEventListener('mouseup', dragEnd);
        
        function dragStart(e) {{
            if (e.target.closest('.aurora-palette-controls')) return;
            
            initialX = e.clientX - xOffset;
            initialY = e.clientY - yOffset;
            
            if (e.target === header || header.contains(e.target)) {{
                isDragging = true;
            }}
        }}
        
        function drag(e) {{
            if (isDragging) {{
                e.preventDefault();
                currentX = e.clientX - initialX;
                currentY = e.clientY - initialY;
                
                xOffset = currentX;
                yOffset = currentY;
                
                palette.style.transform = `translate(${{currentX}}px, ${{currentY}}px)`;
            }}
        }}
        
        function dragEnd(e) {{
            initialX = currentX;
            initialY = currentY;
            isDragging = false;
        }}
    </script>
</body>
</html>
        """
    
    async def start_conversation(self):
        """Start the conversational interface"""
        self.logger.info("Starting Aurora Conversational Palette")
        
        # Generate and save HTML
        html_content = self.generate_html()
        
        # Save to file
        with open('/workspace/aurora_conversational_palette.html', 'w') as f:
            f.write(html_content)
        
        self.logger.info("Aurora Conversational Palette HTML generated")
        
        # Show notification
        await self.animation_manager.show_notification(
            "Aurora Conversational Palette ready!",
            "success"
        )
        
        return html_content
    
    async def send_message(self, message: str, message_type: MessageType = MessageType.USER):
        """Send a message in the conversation"""
        msg = Message(
            id=str(uuid.uuid4()),
            type=message_type,
            content=message,
            timestamp=time.time()
        )
        
        self.messages.append(msg)
        
        # Trigger typing indicator for AI response
        if message_type == MessageType.USER:
            await self._simulate_ai_response(message)
        
        return msg
    
    async def _simulate_ai_response(self, user_message: str):
        """Simulate AI response to user message"""
        # Show typing indicator
        self.is_typing = True
        
        # Simulate processing time
        await asyncio.sleep(1.5)
        
        # Generate response based on message content
        response = await self._generate_ai_response(user_message)
        
        # Add AI message
        ai_message = Message(
            id=str(uuid.uuid4()),
            type=MessageType.AI,
            content=response,
            timestamp=time.time()
        )
        
        self.messages.append(ai_message)
        self.is_typing = False
        
        return ai_message
    
    async def _generate_ai_response(self, user_message: str) -> str:
        """Generate AI response based on user message"""
        message_lower = user_message.lower()
        
        # Simple response patterns
        if any(word in message_lower for word in ['hello', 'hi', 'hey']):
            return "Hello! I'm Aurora, your AI assistant. How can I help you today?"
        
        elif 'firefox' in message_lower:
            return "Opening Firefox browser for you..."
        
        elif 'document' in message_lower:
            return "I'll help you find your documents. Searching through your files now..."
        
        elif 'system' in message_lower and 'status' in message_lower:
            return "Checking system status... All systems are running optimally. CPU usage: 23%, Memory: 4.2GB/16GB, Disk: 120GB free."
        
        elif 'help' in message_lower:
            return "I can help you with:\n• Opening applications\n• Finding files\n• System monitoring\n• Answering questions\n• Optimizing performance\n\nWhat would you like to do?"
        
        else:
            return f"I understand you're asking about: '{user_message}'. I'm processing your request and will help you with that."
    
    def update_suggestions(self, suggestions: List[SuggestionChip]):
        """Update suggestion chips"""
        self.suggestions = suggestions
        self.logger.info(f"Updated {len(suggestions)} suggestion chips")
    
    def set_theme_mode(self, mode: str):
        """Set theme mode (dark/light)"""
        self.theme_mode = mode
        self.logger.info(f"Theme mode set to: {mode}")
    
    def toggle_minimize(self):
        """Toggle minimized state"""
        self.is_minimized = not self.is_minimized
        self.logger.info(f"Palette minimized: {self.is_minimized}")
    
    def toggle_fullscreen(self):
        """Toggle fullscreen state"""
        self.is_fullscreen = not self.is_fullscreen
        self.logger.info(f"Palette fullscreen: {self.is_fullscreen}")

# Export main class
__all__ = ['EnhancedConversationalUI']