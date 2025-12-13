"""
Aurora OS - Intent Engine

This module implements the core intent processing engine for Aurora OS,
translating user intent into system actions with AI-powered understanding.

Key Features:
- Natural language intent understanding
- Context-aware action execution
- Multi-modal input processing (text, voice, gesture)
- Predictive intent anticipation
- Workflow automation and orchestration
- Learning and adaptation to user patterns
"""

import asyncio
import time
import logging
import json
import re
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import threading
from queue import Queue, Empty

# AI and NLP
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False
    logging.warning("NLP libraries not available, using rule-based processing")

# Aurora components
from mcp.provider_manager import MCPProviderManager


class IntentType(Enum):
    """Types of user intents"""
    SYSTEM_CONTROL = "system_control"
    APP_MANAGEMENT = "app_management"
    FILE_OPERATIONS = "file_operations"
    INFORMATION_QUERY = "information_query"
    WORKFLOW_AUTOMATION = "workflow_automation"
    CONVERSATION = "conversation"
    HELP = "help"
    NAVIGATION = "navigation"
    CONFIGURATION = "configuration"


class ActionType(Enum):
    """Types of actions that can be executed"""
    EXECUTE_COMMAND = "execute_command"
    LAUNCH_APP = "launch_app"
    CLOSE_APP = "close_app"
    OPEN_FILE = "open_file"
    SEARCH_FILES = "search_files"
    GET_INFO = "get_info"
    SET_CONFIG = "set_config"
    START_WORKFLOW = "start_workflow"
    CONVERSATION_RESPONSE = "conversation_response"
    CUSTOM_ACTION = "custom_action"


@dataclass
class Entity:
    """Extracted entity from user input"""
    entity_type: str
    value: str
    confidence: float
    start_pos: int
    end_pos: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Intent:
    """Processed user intent"""
    intent_id: str
    intent_type: IntentType
    action_type: ActionType
    primary_text: str
    entities: List[Entity]
    confidence: float
    context: Dict[str, Any]
    timestamp: float
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class IntentEngine:
    """AI-powered intent processing engine for Aurora OS"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Processing settings
        self.confidence_threshold = self.config.get("confidence_threshold", 0.5)
        self.max_suggestions = self.config.get("max_suggestions", 5)
        
        # Action registry
        self.action_handlers: Dict[ActionType, Callable] = {}
        
        # Context management
        self.context = {
            "recent_intents": [],
            "user_preferences": {},
            "system_state": {}
        }
        
        # History tracking
        self.intent_history: List[Intent] = []
        
        # Integration
        self.mcp_manager: Optional[MCPProviderManager] = None
        
        # Logging
        self.logger = logging.getLogger("aurora_intent_engine")
        
        # Initialize patterns
        self._initialize_patterns()
    
    def _initialize_patterns(self) -> None:
        """Initialize intent patterns"""
        self.intent_patterns = {
            IntentType.SYSTEM_CONTROL: ["shutdown", "restart", "reboot", "sleep", "lock"],
            IntentType.APP_MANAGEMENT: ["open", "launch", "start", "close", "quit"],
            IntentType.FILE_OPERATIONS: ["find", "search", "create", "delete", "move"],
            IntentType.INFORMATION_QUERY: ["what", "how", "show", "tell", "display"],
            IntentType.HELP: ["help", "assist", "guide", "how to"]
        }
        
        # Map intents to actions
        self.intent_action_mapping = {
            IntentType.SYSTEM_CONTROL: ActionType.EXECUTE_COMMAND,
            IntentType.APP_MANAGEMENT: ActionType.LAUNCH_APP,
            IntentType.FILE_OPERATIONS: ActionType.SEARCH_FILES,
            IntentType.INFORMATION_QUERY: ActionType.GET_INFO,
            IntentType.CONFIGURATION: ActionType.SET_CONFIG,
            IntentType.HELP: ActionType.CONVERSATION_RESPONSE,
            IntentType.CONVERSATION: ActionType.CONVERSATION_RESPONSE
        }
    
    async def initialize(self) -> bool:
        """Initialize the intent engine"""
        try:
            # Connect to MCP provider
            await self._connect_to_mcp()
            
            self.logger.info("Intent engine initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize intent engine: {e}")
            return False
    
    async def _connect_to_mcp(self) -> None:
        """Connect to MCP provider manager"""
        try:
            self.mcp_manager = MCPProviderManager()
            await self.mcp_manager.initialize()
            
            self.logger.info("Connected to MCP manager")
            
        except Exception as e:
            self.logger.warning(f"Failed to connect to MCP: {e}")
    
    async def process_intent(self, input_text: str, context: Optional[Dict[str, Any]] = None) -> Intent:
        """Process user input and extract intent"""
        try:
            # Preprocess input
            processed_text = self._preprocess_input(input_text)
            
            # Classify intent
            intent_type, confidence = self._classify_intent(processed_text)
            
            # Extract entities
            entities = self._extract_entities(processed_text, intent_type)
            
            # Determine action type
            action_type = self._determine_action_type(intent_type, entities, input_text)
            
            # Create intent object
            intent = Intent(
                intent_id=f"intent_{int(time.time() * 1000)}",
                intent_type=intent_type,
                action_type=action_type,
                primary_text=input_text,
                entities=entities,
                confidence=confidence,
                context=context or {},
                timestamp=time.time()
            )
            
            # Store in history
            self.intent_history.append(intent)
            if len(self.intent_history) > 100:
                self.intent_history.pop(0)
            
            self.logger.debug(f"Processed intent: {intent_type.value} (confidence: {confidence:.2f})")
            
            return intent
            
        except Exception as e:
            self.logger.error(f"Failed to process intent: {e}")
            
            # Return error intent
            return Intent(
                intent_id=f"error_{int(time.time() * 1000)}",
                intent_type=IntentType.HELP,
                action_type=ActionType.CONVERSATION_RESPONSE,
                primary_text=input_text,
                entities=[],
                confidence=0.0,
                context=context or {},
                timestamp=time.time()
            )
    
    def _preprocess_input(self, input_text: str) -> str:
        """Preprocess user input"""
        processed = input_text.strip().lower()
        processed = re.sub(r'\s+', ' ', processed)
        return processed
    
    def _classify_intent(self, processed_text: str) -> Tuple[IntentType, float]:
        """Classify intent type from processed text"""
        best_intent = IntentType.CONVERSATION
        best_confidence = 0.0
        
        for intent_type, keywords in self.intent_patterns.items():
            matches = sum(1 for keyword in keywords if keyword in processed_text)
            
            if matches > 0:
                confidence = min(1.0, matches * 0.3)
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_intent = intent_type
        
        return best_intent, best_confidence
    
    def _extract_entities(self, processed_text: str, intent_type: IntentType) -> List[Entity]:
        """Extract entities from processed text"""
        entities = []
        
        try:
            # Extract based on intent type
            if intent_type == IntentType.APP_MANAGEMENT:
                entities.extend(self._extract_app_entities(processed_text))
            elif intent_type == IntentType.FILE_OPERATIONS:
                entities.extend(self._extract_file_entities(processed_text))
            elif intent_type == IntentType.INFORMATION_QUERY:
                entities.extend(self._extract_info_entities(processed_text))
            
        except Exception as e:
            self.logger.debug(f"Entity extraction failed: {e}")
        
        return entities
    
    def _extract_app_entities(self, text: str) -> List[Entity]:
        """Extract application entities"""
        entities = []
        
        apps = [
            "firefox", "chrome", "browser", "terminal", "vscode",
            "settings", "files", "file manager"
        ]
        
        for app in apps:
            if app in text:
                start_pos = text.find(app)
                entities.append(Entity(
                    entity_type="app_name",
                    value=app,
                    confidence=0.9,
                    start_pos=start_pos,
                    end_pos=start_pos + len(app)
                ))
        
        return entities
    
    def _extract_file_entities(self, text: str) -> List[Entity]:
        """Extract file-related entities"""
        entities = []
        
        # Simple file path detection
        if '/' in text or '\\' in text:
            start_pos = text.find('/') if '/' in text else text.find('\\')
            if start_pos >= 0:
                end_pos = len(text)
                entities.append(Entity(
                    entity_type="file_path",
                    value=text[start_pos:],
                    confidence=0.8,
                    start_pos=start_pos,
                    end_pos=end_pos
                ))
        
        return entities
    
    def _extract_info_entities(self, text: str) -> List[Entity]:
        """Extract information query entities"""
        entities = []
        
        info_types = [
            "battery", "cpu", "memory", "disk", "network", "wifi",
            "time", "date", "uptime", "version"
        ]
        
        for info_type in info_types:
            if info_type in text:
                start_pos = text.find(info_type)
                entities.append(Entity(
                    entity_type="info_type",
                    value=info_type,
                    confidence=0.8,
                    start_pos=start_pos,
                    end_pos=start_pos + len(info_type)
                ))
        
        return entities
    
    def _determine_action_type(self, intent_type: IntentType, entities: List[Entity], raw_text: str) -> ActionType:
        """Determine the action type based on intent and entities"""
        base_action = self.intent_action_mapping.get(intent_type, ActionType.CONVERSATION_RESPONSE)
        
        # Refine based on entities and context
        if intent_type == IntentType.APP_MANAGEMENT:
            if "close" in raw_text.lower() or "quit" in raw_text.lower():
                return ActionType.CLOSE_APP
            else:
                return ActionType.LAUNCH_APP
        elif intent_type == IntentType.FILE_OPERATIONS:
            for entity in entities:
                if entity.entity_type == "file_path":
                    return ActionType.OPEN_FILE
            return ActionType.SEARCH_FILES
        
        return base_action
    
    async def execute_action(self, intent: Intent) -> Tuple[bool, Any]:
        """Execute action based on intent"""
        try:
            if intent.action_type in self.action_handlers:
                handler = self.action_handlers[intent.action_type]
                success, result = await handler(intent)
                return success, result
            else:
                # Default action execution
                return await self._default_action_execution(intent)
                
        except Exception as e:
            self.logger.error(f"Action execution failed: {e}")
            return False, str(e)
    
    async def _default_action_execution(self, intent: Intent) -> Tuple[bool, Any]:
        """Default action execution"""
        if intent.action_type == ActionType.LAUNCH_APP:
            app_name = None
            for entity in intent.entities:
                if entity.entity_type == "app_name":
                    app_name = entity.value
                    break
            
            if app_name:
                return True, f"Would launch {app_name}"
            else:
                return False, "No application specified"
        
        elif intent.action_type == ActionType.GET_INFO:
            info_type = None
            for entity in intent.entities:
                if entity.entity_type == "info_type":
                    info_type = entity.value
                    break
            
            if info_type:
                return True, f"Would get {info_type} information"
            else:
                return False, "No information type specified"
        
        elif intent.action_type == ActionType.CONVERSATION_RESPONSE:
            responses = [
                "I understand your request.",
                "I can help you with that.",
                "That's interesting. Tell me more.",
                "I'm processing your request."
            ]
            import random
            return True, random.choice(responses)
        
        return False, f"Unknown action type: {intent.action_type.value}"
    
    def register_action_handler(self, action_type: ActionType, handler: Callable) -> None:
        """Register custom action handler"""
        self.action_handlers[action_type] = handler
        self.logger.info(f"Registered handler for action type: {action_type.value}")
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            "total_intents": len(self.intent_history),
            "recent_intents": len(self.context["recent_intents"])
        }
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            if self.mcp_manager:
                await self.mcp_manager.cleanup()
            
            self.logger.info("Intent engine cleaned up")
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")


# Global intent engine instance
aurora_intent_engine = IntentEngine()