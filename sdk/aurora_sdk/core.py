"""
Core Aurora OS SDK Components
Provides fundamental classes for Aurora OS application development
"""

import asyncio
import logging
import json
import uuid
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import time

class AppType(Enum):
    """Types of Aurora OS applications"""
    PRODUCTIVITY = "productivity"
    CREATIVE = "creative"
    DEVELOPMENT = "development"
    COMMUNICATION = "communication"
    ENTERTAINMENT = "entertainment"
    EDUCATION = "education"
    SYSTEM = "system"
    UTILITY = "utility"

class ContextScope(Enum):
    """Context sharing scopes"""
    PRIVATE = "private"
    SESSION = "session"
    APPLICATION = "application"
    SYSTEM = "system"
    CLOUD = "cloud"

@dataclass
class AuroraContext:
    """Context object for Aurora applications"""
    context_id: str
    app_id: str
    data: Dict[str, Any]
    scope: ContextScope
    timestamp: float
    ttl: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if context has expired"""
        if self.ttl is None:
            return False
        return time.time() > (self.timestamp + self.ttl)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary"""
        return {
            "context_id": self.context_id,
            "app_id": self.app_id,
            "data": self.data,
            "scope": self.scope.value,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
            "metadata": self.metadata
        }

@dataclass
class AuroraIntent:
    """Intent object for Aurora AI interactions"""
    intent_id: str
    intent_type: str
    confidence: float
    parameters: Dict[str, Any]
    source_app: str
    timestamp: float
    entities: List[Dict[str, Any]] = field(default_factory=list)
    context_links: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert intent to dictionary"""
        return {
            "intent_id": self.intent_id,
            "intent_type": self.intent_type,
            "confidence": self.confidence,
            "parameters": self.parameters,
            "source_app": self.source_app,
            "timestamp": self.timestamp,
            "entities": self.entities,
            "context_links": self.context_links
        }

class AuroraApp:
    """Base class for Aurora OS applications"""
    
    def __init__(
        self,
        app_id: str,
        name: str,
        version: str,
        app_type: AppType,
        description: str = ""
    ):
        self.app_id = app_id
        self.name = name
        self.version = version
        self.app_type = app_type
        self.description = description
        
        # Runtime state
        self.is_running = False
        self.session_id = str(uuid.uuid4())
        self.start_time = None
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        # Context and AI services
        self.context_store: Dict[str, AuroraContext] = {}
        self.ai_services = None
        self.logger = logging.getLogger(f"aurora.app.{app_id}")
        
        # Capabilities
        self.capabilities = {
            "conversational": False,
            "context_aware": False,
            "predictive": False,
            "multimodal": False,
            "collaborative": False
        }
        
        # Permissions
        self.permissions = {
            "file_access": False,
            "network_access": False,
            "system_control": False,
            "user_data": False,
            "camera_access": False,
            "microphone_access": False
        }
        
        # Configuration
        self.config = self._load_default_config()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default application configuration"""
        return {
            "auto_save": True,
            "auto_backup": True,
            "crash_reporting": True,
            "telemetry": False,
            "auto_update": False,
            "theme": "aurora",
            "language": "en",
            "max_memory_mb": 512
        }
    
    async def initialize(self) -> bool:
        """Initialize the application"""
        try:
            self.start_time = time.time()
            self.is_running = True
            
            # Register with Aurora OS
            await self._register_with_aurora()
            
            # Initialize AI services if enabled
            if self.capabilities.get("context_aware", False):
                await self._initialize_ai_services()
            
            # Load saved state
            await self._load_state()
            
            self.logger.info(f"Application {self.app_id} initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize application: {e}")
            return False
    
    async def shutdown(self) -> bool:
        """Shutdown the application gracefully"""
        try:
            self.is_running = False
            
            # Save state
            await self._save_state()
            
            # Unregister from Aurora OS
            await self._unregister_from_aurora()
            
            # Cleanup resources
            await self._cleanup_resources()
            
            self.logger.info(f"Application {self.app_id} shutdown successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to shutdown application: {e}")
            return False
    
    async def _register_with_aurora(self):
        """Register application with Aurora OS"""
        # This would connect to the Aurora OS service registry
        pass
    
    async def _unregister_from_aurora(self):
        """Unregister application from Aurora OS"""
        # This would disconnect from the Aurora OS service registry
        pass
    
    async def _initialize_ai_services(self):
        """Initialize AI services for the application"""
        try:
            from .ai import AIServices
            self.ai_services = AIServices(self.app_id)
            await self.ai_services.initialize()
            self.logger.info("AI services initialized")
        except ImportError:
            self.logger.warning("AI services not available")
    
    async def _load_state(self):
        """Load application state from storage"""
        state_file = Path(f"~/.aurora/apps/{self.app_id}/state.json").expanduser()
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                self._restore_state(state)
                self.logger.info("Application state loaded")
            except Exception as e:
                self.logger.error(f"Failed to load state: {e}")
    
    async def _save_state(self):
        """Save application state to storage"""
        if not self.config.get("auto_save", True):
            return
        
        try:
            state = self._capture_state()
            state_file = Path(f"~/.aurora/apps/{self.app_id}/state.json").expanduser()
            state_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            self.logger.info("Application state saved")
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
    
    def _capture_state(self) -> Dict[str, Any]:
        """Capture current application state"""
        return {
            "session_id": self.session_id,
            "last_active": time.time(),
            "config": self.config,
            "context_count": len(self.context_store),
            "capabilities": self.capabilities,
            "permissions": self.permissions
        }
    
    def _restore_state(self, state: Dict[str, Any]):
        """Restore application state from saved data"""
        self.session_id = state.get("session_id", str(uuid.uuid4()))
        self.config.update(state.get("config", {}))
        self.capabilities.update(state.get("capabilities", {}))
        self.permissions.update(state.get("permissions", {}))
    
    async def _cleanup_resources(self):
        """Cleanup application resources"""
        # Clear expired contexts
        current_time = time.time()
        expired_contexts = [
            context_id for context_id, context in self.context_store.items()
            if context.is_expired()
        ]
        
        for context_id in expired_contexts:
            del self.context_store[context_id]
        
        # Shutdown AI services
        if self.ai_services:
            await self.ai_services.shutdown()
    
    # Context Management
    async def create_context(
        self,
        data: Dict[str, Any],
        scope: ContextScope = ContextScope.PRIVATE,
        ttl: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuroraContext:
        """Create a new context object"""
        
        context = AuroraContext(
            context_id=str(uuid.uuid4()),
            app_id=self.app_id,
            data=data,
            scope=scope,
            timestamp=time.time(),
            ttl=ttl,
            metadata=metadata or {}
        )
        
        self.context_store[context.context_id] = context
        
        # Share context if scope requires
        if scope in [ContextScope.SYSTEM, ContextScope.CLOUD]:
            await self._share_context(context)
        
        return context
    
    async def get_context(self, context_id: str) -> Optional[AuroraContext]:
        """Get context by ID"""
        context = self.context_store.get(context_id)
        if context and context.is_expired():
            del self.context_store[context_id]
            return None
        return context
    
    async def update_context(
        self,
        context_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update existing context"""
        context = await self.get_context(context_id)
        if not context:
            return False
        
        context.data.update(data)
        context.timestamp = time.time()
        if metadata:
            context.metadata.update(metadata)
        
        # Reshare if needed
        if context.scope in [ContextScope.SYSTEM, ContextScope.CLOUD]:
            await self._share_context(context)
        
        return True
    
    async def delete_context(self, context_id: str) -> bool:
        """Delete context"""
        if context_id in self.context_store:
            del self.context_store[context_id]
            return True
        return False
    
    async def _share_context(self, context: AuroraContext):
        """Share context with other applications or system"""
        if self.ai_services:
            await self.ai_services.share_context(context)
    
    # Event Handling
    def on(self, event: str, handler: Callable):
        """Register event handler"""
        if event not in self.event_handlers:
            self.event_handlers[event] = []
        self.event_handlers[event].append(handler)
    
    async def emit(self, event: str, data: Dict[str, Any]):
        """Emit event to registered handlers"""
        if event in self.event_handlers:
            for handler in self.event_handlers[event]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    self.logger.error(f"Event handler error: {e}")
    
    # Intent Processing
    async def process_intent(self, intent: AuroraIntent) -> Dict[str, Any]:
        """Process an intent from the AI system"""
        
        result = {
            "success": False,
            "message": "",
            "data": {}
        }
        
        try:
            # Validate intent
            if not await self._validate_intent(intent):
                result["message"] = "Invalid intent"
                return result
            
            # Get relevant context
            context_data = await self._get_relevant_context(intent)
            
            # Process intent based on type
            if intent.intent_type == "launch":
                result = await self._handle_launch_intent(intent, context_data)
            elif intent.intent_type == "configure":
                result = await self._handle_configure_intent(intent, context_data)
            elif intent.intent_type == "query":
                result = await self._handle_query_intent(intent, context_data)
            else:
                result = await self._handle_custom_intent(intent, context_data)
            
            # Emit intent processed event
            await self.emit("intent_processed", {
                "intent": intent.to_dict(),
                "result": result
            })
            
        except Exception as e:
            self.logger.error(f"Intent processing error: {e}")
            result["message"] = f"Processing error: {str(e)}"
        
        return result
    
    async def _validate_intent(self, intent: AuroraIntent) -> bool:
        """Validate incoming intent"""
        # Check confidence threshold
        if intent.confidence < 0.5:
            return False
        
        # Check if intent type is supported
        supported_types = ["launch", "configure", "query", "action"]
        if intent.intent_type not in supported_types:
            return False
        
        return True
    
    async def _get_relevant_context(self, intent: AuroraIntent) -> Dict[str, Any]:
        """Get context relevant to the intent"""
        context_data = {}
        
        # Get linked contexts
        for context_id in intent.context_links:
            context = await self.get_context(context_id)
            if context:
                context_data[context_id] = context.data
        
        return context_data
    
    async def _handle_launch_intent(
        self,
        intent: AuroraIntent,
        context_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle launch intent"""
        return {
            "success": True,
            "message": f"Launched {self.name}",
            "data": {"action": "launched", "app_id": self.app_id}
        }
    
    async def _handle_configure_intent(
        self,
        intent: AuroraIntent,
        context_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle configure intent"""
        setting = intent.parameters.get("setting")
        value = intent.parameters.get("value")
        
        if setting and setting in self.config:
            self.config[setting] = value
            return {
                "success": True,
                "message": f"Configuration updated: {setting} = {value}",
                "data": {"setting": setting, "value": value}
            }
        
        return {
            "success": False,
            "message": "Invalid configuration setting",
            "data": {}
        }
    
    async def _handle_query_intent(
        self,
        intent: AuroraIntent,
        context_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle query intent"""
        query_type = intent.parameters.get("query_type", "status")
        
        if query_type == "status":
            return {
                "success": True,
                "message": f"{self.name} status",
                "data": {
                    "app_id": self.app_id,
                    "name": self.name,
                    "version": self.version,
                    "is_running": self.is_running,
                    "uptime": time.time() - self.start_time if self.start_time else 0,
                    "context_count": len(self.context_store)
                }
            }
        elif query_type == "config":
            return {
                "success": True,
                "message": f"{self.name} configuration",
                "data": self.config
            }
        
        return {
            "success": False,
            "message": f"Unknown query type: {query_type}",
            "data": {}
        }
    
    async def _handle_custom_intent(
        self,
        intent: AuroraIntent,
        context_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle custom application-specific intents"""
        # Override in subclasses
        return {
            "success": False,
            "message": "Custom intent handling not implemented",
            "data": {}
        }
    
    # Application Information
    def get_info(self) -> Dict[str, Any]:
        """Get application information"""
        return {
            "app_id": self.app_id,
            "name": self.name,
            "version": self.version,
            "type": self.app_type.value,
            "description": self.description,
            "is_running": self.is_running,
            "session_id": self.session_id,
            "start_time": self.start_time,
            "capabilities": self.capabilities,
            "permissions": self.permissions,
            "context_count": len(self.context_store)
        }
    
    def get_manifest(self) -> Dict[str, Any]:
        """Get application manifest for Aurora OS"""
        return {
            "manifest_version": "1.0",
            "app_id": self.app_id,
            "name": self.name,
            "version": self.version,
            "type": self.app_type.value,
            "description": self.description,
            "author": "Aurora Developer",
            "website": "https://aurora-os.org",
            "icon": f"apps/{self.app_id}/icon.png",
            "entry_point": f"apps.{self.app_id}.main",
            "capabilities": list(self.capabilities.keys()),
            "permissions": list(self.permissions.keys()),
            "dependencies": [],
            "min_aurora_version": "0.1.0",
            "config_schema": {
                "type": "object",
                "properties": {
                    "auto_save": {"type": "boolean", "default": True},
                    "theme": {"type": "string", "enum": ["aurora", "dark", "light"]},
                    "language": {"type": "string", "default": "en"}
                }
            }
        }

# Utility functions for developers
def create_app(
    app_id: str,
    name: str,
    version: str,
    app_type: AppType,
    description: str = ""
) -> AuroraApp:
    """Create a new Aurora application instance"""
    return AuroraApp(app_id, name, version, app_type, description)

def enable_conversational(app: AuroraApp):
    """Enable conversational AI capability"""
    app.capabilities["conversational"] = True
    app.permissions["microphone_access"] = True

def enable_context_awareness(app: AuroraApp):
    """Enable context awareness capability"""
    app.capabilities["context_aware"] = True

def enable_predictive_features(app: AuroraApp):
    """Enable predictive features"""
    app.capabilities["predictive"] = True
    app.permissions["user_data"] = True

def enable_multimodal(app: AuroraApp):
    """Enable multimodal capabilities"""
    app.capabilities["multimodal"] = True
    app.permissions["camera_access"] = True
    app.permissions["microphone_access"] = True

def request_file_access(app: AuroraApp):
    """Request file system access permission"""
    app.permissions["file_access"] = True

def request_network_access(app: AuroraApp):
    """Request network access permission"""
    app.permissions["network_access"] = True

def request_system_control(app: AuroraApp):
    """Request system control permission"""
    app.permissions["system_control"] = True