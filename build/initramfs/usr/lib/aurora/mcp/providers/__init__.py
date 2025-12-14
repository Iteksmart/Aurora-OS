"""
Aurora OS - MCP Context Providers Package

This package contains all the Model Context Protocol providers for Aurora OS,
providing real-time context from various system components to the AI control plane.
"""

from .filesystem_provider import FileSystemContextProvider
from .system_provider import SystemContextProvider
from .security_provider import SecurityContextProvider

__all__ = [
    'FileSystemContextProvider',
    'SystemContextProvider', 
    'SecurityContextProvider'
]

# Provider registry
PROVIDER_REGISTRY = {
    'filesystem': FileSystemContextProvider,
    'system': SystemContextProvider,
    'security': SecurityContextProvider
}

def get_provider_class(provider_name: str):
    """Get provider class by name"""
    if provider_name not in PROVIDER_REGISTRY:
        raise ValueError(f"Unknown provider: {provider_name}")
    return PROVIDER_REGISTRY[provider_name]

def list_providers():
    """List all available providers"""
    return list(PROVIDER_REGISTRY.keys())