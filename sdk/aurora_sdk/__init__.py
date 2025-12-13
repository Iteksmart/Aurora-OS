"""
Aurora OS SDK - Development Kit for Third-Party Applications
Enables developers to create AI-enhanced applications for Aurora OS
"""

__version__ = "0.1.0"
__author__ = "Aurora OS Team"

from .core import AuroraApp, AuroraContext, AuroraIntent
from .ai import AIServices, IntentProcessor, ContextManager
# from .ui import AuroraUI, ConversationalInterface, PredictiveUI
# from .security import AuroraSecurity, Permissions, DataProtection
# from .utils import Helpers, Configuration, Logging

__all__ = [
    # Core classes
    'AuroraApp',
    'AuroraContext', 
    'AuroraIntent',
    
    # AI services
    'AIServices',
    'IntentProcessor',
    'ContextManager',
    
    # UI components (coming soon)
    # 'AuroraUI',
    # 'ConversationalInterface',
    # 'PredictiveUI',
    
    # Security (coming soon)
    # 'AuroraSecurity',
    # 'Permissions',
    # 'DataProtection',
    
    # Utilities (coming soon)
    # 'Helpers',
    # 'Configuration',
    # 'Logging'
]