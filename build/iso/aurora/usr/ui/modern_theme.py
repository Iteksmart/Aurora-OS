"""
Modern Aurora UI Theme with Animations and Transitions
Professional, polished user interface for Aurora OS
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time

class ThemeColor(Enum):
    """Modern Aurora color palette"""
    PRIMARY = "#2563eb"      # Modern blue
    SECONDARY = "#7c3aed"    # Purple accent
    SUCCESS = "#10b981"      # Green
    WARNING = "#f59e0b"      # Amber
    ERROR = "#ef4444"        # Red
    DARK = "#1f2937"         # Dark background
    LIGHT = "#f3f4f6"        # Light text
    AURORA_GRADIENT = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"

@dataclass
class AnimationConfig:
    """Animation configuration"""
    duration: float = 0.3
    easing: str = "cubic-bezier(0.4, 0, 0.2, 1)"
    delay: float = 0.0
    iterations: int = 1

class ModernTheme:
    """Modern Aurora UI theme with animations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.animations = {}
        self.transitions = {}
        self.current_theme = "dark"
        
        # Initialize animations
        self._init_animations()
        self._init_transitions()
    
    def _init_animations(self):
        """Initialize animation definitions"""
        self.animations = {
            "fade_in": AnimationConfig(duration=0.3, easing="ease-in-out"),
            "fade_out": AnimationConfig(duration=0.2, easing="ease-in-out"),
            "slide_up": AnimationConfig(duration=0.4, easing="cubic-bezier(0.4, 0, 0.2, 1)"),
            "slide_down": AnimationConfig(duration=0.4, easing="cubic-bezier(0.4, 0, 0.2, 1)"),
            "slide_left": AnimationConfig(duration=0.3, easing="ease-out"),
            "slide_right": AnimationConfig(duration=0.3, easing="ease-out"),
            "scale_in": AnimationConfig(duration=0.2, easing="ease-out"),
            "scale_out": AnimationConfig(duration=0.2, easing="ease-in"),
            "rotate": AnimationConfig(duration=0.5, easing="linear"),
            "pulse": AnimationConfig(duration=1.0, easing="ease-in-out", iterations=2),
            "bounce": AnimationConfig(duration=0.6, easing="cubic-bezier(0.68, -0.55, 0.265, 1.55)"),
            "aurora_glow": AnimationConfig(duration=2.0, easing="ease-in-out", iterations=-1),  # Infinite
            "typing_indicator": AnimationConfig(duration=1.5, easing="ease-in-out", iterations=-1),
        }
    
    def _init_transitions(self):
        """Initialize transition effects"""
        self.transitions = {
            "hover": "all 0.2s ease-in-out",
            "focus": "all 0.1s ease-out",
            "active": "all 0.1s ease-in",
            "smooth": "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
            "quick": "all 0.15s ease-out",
        }
    
    def get_css_variables(self) -> str:
        """Generate CSS custom properties for the theme"""
        return f"""
        :root {{
            /* Aurora Modern Colors */
            --aurora-primary: {ThemeColor.PRIMARY.value};
            --aurora-secondary: {ThemeColor.SECONDARY.value};
            --aurora-success: {ThemeColor.SUCCESS.value};
            --aurora-warning: {ThemeColor.WARNING.value};
            --aurora-error: {ThemeColor.ERROR.value};
            --aurora-dark: {ThemeColor.DARK.value};
            --aurora-light: {ThemeColor.LIGHT.value};
            
            /* Gradients */
            --aurora-gradient: {ThemeColor.AURORA_GRADIENT.value};
            --aurora-glow: radial-gradient(circle, rgba(102, 126, 234, 0.3) 0%, transparent 70%);
            
            /* Shadows */
            --aurora-shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            --aurora-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            --aurora-shadow-md: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            --aurora-shadow-lg: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            --aurora-shadow-xl: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            --aurora-glow-shadow: 0 0 20px rgba(102, 126, 234, 0.6);
            
            /* Border Radius */
            --aurora-radius-sm: 0.25rem;
            --aurora-radius: 0.5rem;
            --aurora-radius-md: 0.75rem;
            --aurora-radius-lg: 1rem;
            --aurora-radius-xl: 1.5rem;
            --aurora-radius-full: 9999px;
            
            /* Spacing */
            --aurora-space-1: 0.25rem;
            --aurora-space-2: 0.5rem;
            --aurora-space-3: 0.75rem;
            --aurora-space-4: 1rem;
            --aurora-space-5: 1.25rem;
            --aurora-space-6: 1.5rem;
            --aurora-space-8: 2rem;
            --aurora-space-10: 2.5rem;
            --aurora-space-12: 3rem;
            
            /* Typography */
            --aurora-font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            --aurora-font-mono: 'JetBrains Mono', 'Fira Code', monospace;
            
            /* Z-index layers */
            --aurora-z-dropdown: 1000;
            --aurora-z-sticky: 1020;
            --aurora-z-fixed: 1030;
            --aurora-z-modal-backdrop: 1040;
            --aurora-z-modal: 1050;
            --aurora-z-popover: 1060;
            --aurora-z-tooltip: 1070;
        }}
        """
    
    def get_animation_keyframes(self) -> str:
        """Generate CSS keyframe animations"""
        return """
        /* Aurora Animations */
        @keyframes aurora-fade-in {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        @keyframes aurora-fade-out {
            from { opacity: 1; }
            to { opacity: 0; }
        }
        
        @keyframes aurora-slide-up {
            from { transform: translateY(20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        
        @keyframes aurora-slide-down {
            from { transform: translateY(-20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        
        @keyframes aurora-slide-left {
            from { transform: translateX(20px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes aurora-slide-right {
            from { transform: translateX(-20px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes aurora-scale-in {
            from { transform: scale(0.9); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
        }
        
        @keyframes aurora-scale-out {
            from { transform: scale(1); opacity: 1; }
            to { transform: scale(0.9); opacity: 0; }
        }
        
        @keyframes aurora-pulse {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.05); opacity: 0.8; }
        }
        
        @keyframes aurora-bounce {
            0%, 20%, 53%, 80%, 100% { transform: translateY(0); }
            40%, 43% { transform: translateY(-30px); }
            70% { transform: translateY(-15px); }
            90% { transform: translateY(-4px); }
        }
        
        @keyframes aurora-glow {
            0%, 100% { box-shadow: 0 0 20px rgba(102, 126, 234, 0.6); }
            50% { box-shadow: 0 0 40px rgba(102, 126, 234, 0.8); }
        }
        
        @keyframes aurora-typing {
            0%, 60%, 100% { transform: translateY(0); }
            30% { transform: translateY(-10px); }
        }
        
        @keyframes aurora-gradient-shift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        @keyframes aurora-float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }
        
        @keyframes aurora-rotate {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        
        @keyframes aurora-shimmer {
            0% { background-position: -1000px 0; }
            100% { background-position: 1000px 0; }
        }
        """
    
    def get_component_styles(self) -> str:
        """Generate modern component styles"""
        return f"""
        /* Aurora Modern Components */
        
        /* Button Styles */
        .aurora-btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: var(--aurora-space-3) var(--aurora-space-6);
            border: none;
            border-radius: var(--aurora-radius);
            font-family: var(--aurora-font-sans);
            font-weight: 500;
            font-size: 0.875rem;
            line-height: 1.25rem;
            cursor: pointer;
            transition: {self.transitions['hover']};
            position: relative;
            overflow: hidden;
        }}
        
        .aurora-btn::before {{
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            transition: left 0.5s;
        }}
        
        .aurora-btn:hover::before {{
            left: 100%;
        }}
        
        .aurora-btn-primary {{
            background: var(--aurora-primary);
            color: white;
            box-shadow: var(--aurora-shadow);
        }}
        
        .aurora-btn-primary:hover {{
            background: #1d4ed8;
            box-shadow: var(--aurora-shadow-md);
            transform: translateY(-2px);
        }}
        
        .aurora-btn-secondary {{
            background: var(--aurora-secondary);
            color: white;
            box-shadow: var(--aurora-shadow);
        }}
        
        .aurora-btn-ghost {{
            background: transparent;
            color: var(--aurora-primary);
            border: 1px solid var(--aurora-primary);
        }}
        
        .aurora-btn-ghost:hover {{
            background: var(--aurora-primary);
            color: white;
        }}
        
        /* Card Styles */
        .aurora-card {{
            background: white;
            border-radius: var(--aurora-radius-lg);
            box-shadow: var(--aurora-shadow);
            padding: var(--aurora-space-6);
            transition: {self.transitions['hover']};
            position: relative;
            overflow: hidden;
        }}
        
        .aurora-card::after {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--aurora-gradient);
            transform: scaleX(0);
            transform-origin: left;
            transition: transform 0.3s ease;
        }}
        
        .aurora-card:hover::after {{
            transform: scaleX(1);
        }}
        
        .aurora-card:hover {{
            box-shadow: var(--aurora-shadow-lg);
            transform: translateY(-4px);
        }}
        
        /* Input Styles */
        .aurora-input {{
            width: 100%;
            padding: var(--aurora-space-3) var(--aurora-space-4);
            border: 2px solid #e5e7eb;
            border-radius: var(--aurora-radius);
            font-family: var(--aurora-font-sans);
            font-size: 0.875rem;
            transition: {self.transitions['focus']};
            background: white;
        }}
        
        .aurora-input:focus {{
            outline: none;
            border-color: var(--aurora-primary);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }}
        
        /* Modal Styles */
        .aurora-modal {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: var(--aurora-z-modal);
            backdrop-filter: blur(4px);
        }}
        
        .aurora-modal-content {{
            background: white;
            border-radius: var(--aurora-radius-xl);
            box-shadow: var(--aurora-shadow-xl);
            max-width: 90vw;
            max-height: 90vh;
            overflow: auto;
            animation: aurora-scale-in 0.3s ease-out;
        }}
        
        /* Loading Spinner */
        .aurora-spinner {{
            width: 40px;
            height: 40px;
            border: 4px solid #e5e7eb;
            border-top: 4px solid var(--aurora-primary);
            border-radius: 50%;
            animation: aurora-rotate 1s linear infinite;
        }}
        
        /* Typing Indicator */
        .aurora-typing {{
            display: flex;
            align-items: center;
            gap: 4px;
            padding: var(--aurora-space-3);
        }}
        
        .aurora-typing-dot {{
            width: 8px;
            height: 8px;
            background: var(--aurora-primary);
            border-radius: 50%;
            animation: aurora-typing 1.5s ease-in-out infinite;
        }}
        
        .aurora-typing-dot:nth-child(2) {{ animation-delay: 0.2s; }}
        .aurora-typing-dot:nth-child(3) {{ animation-delay: 0.4s; }}
        
        /* Notification Toast */
        .aurora-toast {{
            position: fixed;
            bottom: var(--aurora-space-6);
            right: var(--aurora-space-6);
            background: white;
            padding: var(--aurora-space-4) var(--aurora-space-6);
            border-radius: var(--aurora-radius-lg);
            box-shadow: var(--aurora-shadow-lg);
            display: flex;
            align-items: center;
            gap: var(--aurora-space-3);
            z-index: var(--aurora-z-tooltip);
            animation: aurora-slide-up 0.3s ease-out;
            max-width: 400px;
        }}
        
        .aurora-toast-success {{ border-left: 4px solid var(--aurora-success); }}
        .aurora-toast-warning {{ border-left: 4px solid var(--aurora-warning); }}
        .aurora-toast-error {{ border-left: 4px solid var(--aurora-error); }}
        .aurora-toast-info {{ border-left: 4px solid var(--aurora-primary); }}
        
        /* Progress Bar */
        .aurora-progress {{
            width: 100%;
            height: 8px;
            background: #e5e7eb;
            border-radius: var(--aurora-radius-full);
            overflow: hidden;
        }}
        
        .aurora-progress-bar {{
            height: 100%;
            background: var(--aurora-gradient);
            border-radius: var(--aurora-radius-full);
            transition: width 0.3s ease-out;
            position: relative;
            overflow: hidden;
        }}
        
        .aurora-progress-bar::after {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
            animation: aurora-shimmer 2s linear infinite;
        }}
        
        /* Floating Action Button */
        .aurora-fab {{
            position: fixed;
            bottom: var(--aurora-space-6);
            right: var(--aurora-space-6);
            width: 56px;
            height: 56px;
            border-radius: 50%;
            background: var(--aurora-gradient);
            color: white;
            border: none;
            box-shadow: var(--aurora-shadow-lg);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: {self.transitions['hover']};
            z-index: var(--aurora-z-fixed);
        }}
        
        .aurora-fab:hover {{
            transform: scale(1.1);
            box-shadow: var(--aurora-glow-shadow);
        }}
        
        /* Aurora Glow Effect */
        .aurora-glow {{
            position: relative;
        }}
        
        .aurora-glow::before {{
            content: '';
            position: absolute;
            top: -2px;
            left: -2px;
            right: -2px;
            bottom: -2px;
            background: var(--aurora-gradient);
            border-radius: inherit;
            opacity: 0;
            transition: opacity 0.3s ease;
            filter: blur(8px);
            z-index: -1;
        }}
        
        .aurora-glow:hover::before {{
            opacity: 0.7;
            animation: aurora-glow 2s ease-in-out infinite;
        }}
        """
    
    def get_animation_class(self, animation_name: str) -> str:
        """Get CSS class for an animation"""
        if animation_name not in self.animations:
            return ""
        
        config = self.animations[animation_name]
        iterations = "infinite" if config.iterations == -1 else str(config.iterations)
        
        return f"""
        .aurora-animate-{animation_name} {{
            animation: aurora-{animation_name} {config.duration}s {config.easing} {config.delay}s {iterations};
        }}
        """
    
    def generate_theme_css(self) -> str:
        """Generate complete theme CSS"""
        css_parts = [
            self.get_css_variables(),
            self.get_animation_keyframes(),
            self.get_component_styles(),
        ]
        
        # Add animation classes
        for animation_name in self.animations.keys():
            css_parts.append(self.get_animation_class(animation_name))
        
        return "\n".join(css_parts)
    
    def apply_theme_to_element(self, element_selector: str, theme_modifications: Dict[str, str]) -> str:
        """Apply theme modifications to a specific element"""
        styles = []
        for property_name, value in theme_modifications.items():
            styles.append(f"{property_name}: {value};")
        
        return f"""
        {element_selector} {{
            {' '.join(styles)}
        }}
        """
    
    async def animate_element(self, element_id: str, animation_name: str, duration: Optional[float] = None):
        """Trigger animation on an element"""
        if animation_name not in self.animations:
            self.logger.warning(f"Animation '{animation_name}' not found")
            return
        
        config = self.animations[animation_name]
        anim_duration = duration or config.duration
        
        # This would integrate with the UI framework
        # For now, we'll just log the animation
        self.logger.info(f"Animating element '{element_id}' with '{animation_name}' for {anim_duration}s")
        
        await asyncio.sleep(anim_duration)
    
    def get_theme_colors(self) -> Dict[str, str]:
        """Get current theme color palette"""
        return {
            "primary": ThemeColor.PRIMARY.value,
            "secondary": ThemeColor.SECONDARY.value,
            "success": ThemeColor.SUCCESS.value,
            "warning": ThemeColor.WARNING.value,
            "error": ThemeColor.ERROR.value,
            "dark": ThemeColor.DARK.value,
            "light": ThemeColor.LIGHT.value,
        }

class AnimationManager:
    """Manager for coordinating UI animations"""
    
    def __init__(self, theme: ModernTheme):
        self.theme = theme
        self.logger = logging.getLogger(__name__)
        self.active_animations = {}
    
    async def orchestrate_animation_sequence(self, sequence: List[Tuple[str, str, float]]):
        """Orchestrate a sequence of animations"""
        for element_id, animation_name, delay in sequence:
            if delay > 0:
                await asyncio.sleep(delay)
            
            await self.theme.animate_element(element_id, animation_name)
    
    async def create_loading_animation(self, container_id: str, message: str = "Loading..."):
        """Create a loading animation with message"""
        self.logger.info(f"Creating loading animation in '{container_id}': {message}")
        # Implementation would create loading UI elements
        await asyncio.sleep(0.1)  # Simulate UI creation
    
    async def show_notification(self, message: str, notification_type: str = "info", duration: float = 3.0):
        """Show a notification toast"""
        self.logger.info(f"Showing {notification_type} notification: {message}")
        # Implementation would create and show notification
        await asyncio.sleep(duration)
    
    def create_micro_interaction(self, element_id: str, interaction_type: str):
        """Create micro-interaction for user feedback"""
        animations = {
            "hover": "pulse",
            "click": "scale-in",
            "success": "bounce",
            "error": "shake",
            "loading": "aurora-glow",
        }
        
        animation = animations.get(interaction_type, "fade-in")
        return f"aurora-animate-{animation}"

# Export main components
__all__ = [
    'ModernTheme',
    'ThemeColor',
    'AnimationConfig',
    'AnimationManager',
]