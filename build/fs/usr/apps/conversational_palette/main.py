"""
Aurora OS - Conversational Palette

This module implements the revolutionary conversational interface for Aurora OS,
replacing traditional UI elements with natural language interaction.

Key Features:
- Natural language command processing
- Context-aware suggestions
- AI-powered workflow automation
- Real-time intent understanding
- Conversational system control
"""

import asyncio
import time
import logging
import json
import re
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import threading
from queue import Queue
import uuid

# AI and NLP
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False
    logging.warning("NLP libraries not available, using rule-based processing")

# Aurora components
from ...ai.prediction_engine import UIPredictionEngine, PredictionType
from ...ai.intent_processor import IntentProcessor, IntentType
from system.ai_control_plane.intent_engine import IntentEngine
from mcp.provider_manager import MCPProviderManager


class InteractionMode(Enum):
    """Types of interaction modes"""
    COMMAND = "command"           # Direct command: "open firefox"
    QUERY = "query"              # Information request: "what's my battery level?"
    CONVERSATION = "conversation" # Natural conversation: "hey aurora, can you help me?"
    WORKFLOW = "workflow"         # Workflow automation: "when I start coding, open my dev tools"


class IntentCategory(Enum):
    """Categories of user intents"""
    SYSTEM_CONTROL = "system_control"     # System operations
    APP_MANAGEMENT = "app_management"     # Application management
    FILE_OPERATIONS = "file_operations"   # File management
    INFORMATION = "information"           # Information requests
    WORKFLOW = "workflow"                # Workflow automation
    HELP = "help"                        # Help and assistance
    SOCIAL = "social"                    # Social interaction


@dataclass
class ConversationTurn:
    """Represents a single turn in conversation"""
    turn_id: str
    user_input: str
    intent: Optional[str]
    entities: Dict[str, Any]
    response: str
    actions_taken: List[str]
    confidence: float
    timestamp: float
    context: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.turn_id:
            self.turn_id = str(uuid.uuid4())


@dataclass
class SuggestedAction:
    """AI-suggested action"""
    suggestion_id: str
    title: str
    description: str
    command: str
    probability: float
    confidence: float
    category: IntentCategory
    context_relevance: float


@dataclass
class WorkflowStep:
    """Single step in a workflow"""
    step_id: str
    action: str
    parameters: Dict[str, Any]
    description: str
    estimated_time: float
    dependencies: List[str] = field(default_factory=list)


class ConversationalPalette:
    """AI-powered conversational interface for Aurora OS"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Interface configuration
        self.max_conversation_history = config.get("max_history", 100)
        self.suggestion_count = config.get("suggestion_count", 5)
        self.response_timeout = config.get("response_timeout", 30)
        self.enable_voice_input = config.get("voice_input", True)
        self.enable_proactive_suggestions = config.get("proactive_suggestions", True)
        
        # Conversation state
        self.conversation_history: List[ConversationTurn] = []
        self.current_context: Dict[str, Any] = {}
        self.active_session: bool = False
        self.session_start_time: Optional[float] = None
        
        # AI components
        self.intent_engine = IntentEngine()
        self.prediction_engine = None
        self.nlp_model = None
        self.tokenizer = None
        
        # Workflow management
        self.active_workflows: Dict[str, List[WorkflowStep]] = {}
        self.workflow_templates: Dict[str, List[WorkflowStep]] = {}
        
        # Suggestion system
        self.current_suggestions: List[SuggestedAction] = []
        self.suggestion_queue = Queue()
        
        # Action execution
        self.action_queue = Queue()
        self.execution_thread = None
        
        # Performance tracking
        self.interaction_count = 0
        self.successful_interactions = 0
        self.avg_response_time = 0.0
        self.last_suggestion_update = 0.0
        
        # Integration
        self.mcp_manager = None
        self.app_manager = None
        self.system_controller = None
        
        # Voice input (if enabled)
        self.voice_recognition = None
        
        # Logging
        self.logger = logging.getLogger("conversational_palette")
        
        # Initialize workflow templates
        self._initialize_workflow_templates()
    
    async def initialize(self) -> bool:
        """Initialize the conversational palette"""
        try:
            # Initialize NLP components
            await self._initialize_nlp()
            
            # Initialize intent engine
            await self.intent_engine.initialize()
            
            # Connect to system components
            await self._connect_to_system()
            
            # Start background tasks
            self._start_background_tasks()
            
            # Load conversation history
            await self._load_conversation_history()
            
            self.logger.info("Conversational palette initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize conversational palette: {e}")
            return False
    
    async def _initialize_nlp(self) -> None:
        """Initialize NLP components"""
        try:
            if NLP_AVAILABLE:
                # Load lightweight language model
                model_name = self.config.get("nlp_model", "microsoft/DialoGPT-small")
                
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.nlp_model = AutoModelForCausalLM.from_pretrained(model_name)
                
                # Add padding token if missing
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
                
                self.logger.info(f"Loaded NLP model: {model_name}")
            else:
                self.logger.info("Using rule-based NLP processing")
                
        except Exception as e:
            self.logger.warning(f"Failed to initialize NLP: {e}")
            self.nlp_model = None
    
    async def _connect_to_system(self) -> None:
        """Connect to system components"""
        try:
            # Connect to MCP provider for context
            self.mcp_manager = MCPProviderManager()
            await self.mcp_manager.initialize()
            
            # Connect to app manager (would be system component)
            self.app_manager = "mock_app_manager"
            
            # Connect to system controller
            self.system_controller = "mock_system_controller"
            
            self.logger.info("Connected to system components")
            
        except Exception as e:
            self.logger.warning(f"Failed to connect to system: {e}")
    
    def _start_background_tasks(self) -> None:
        """Start background processing tasks"""
        # Start action execution thread
        self.execution_thread = threading.Thread(
            target=self._action_execution_loop,
            daemon=True
        )
        self.execution_thread.start()
        
        # Start suggestion update thread
        suggestion_thread = threading.Thread(
            target=self._suggestion_update_loop,
            daemon=True
        )
        suggestion_thread.start()
        
        self.logger.info("Background tasks started")
    
    async def _load_conversation_history(self) -> None:
        """Load conversation history from storage"""
        try:
            # Would load from persistent storage
            # For now, start with empty history
            self.conversation_history = []
            self.logger.info("Conversation history loaded")
            
        except Exception as e:
            self.logger.warning(f"Failed to load conversation history: {e}")
    
    def _initialize_workflow_templates(self) -> None:
        """Initialize workflow templates"""
        # Development workflow
        dev_workflow = [
            WorkflowStep(
                step_id="open_editor",
                action="open_app",
                parameters={"app_id": "vscode", "workspace": "current_project"},
                description="Open code editor",
                estimated_time=2.0
            ),
            WorkflowStep(
                step_id="open_terminal",
                action="open_app", 
                parameters={"app_id": "terminal", "directory": "current_project"},
                description="Open terminal in project directory",
                estimated_time=1.0,
                dependencies=["open_editor"]
            ),
            WorkflowStep(
                step_id="open_browser",
                action="open_app",
                parameters={"app_id": "firefox", "tabs": ["documentation", "github"]},
                description="Open browser with development tabs",
                estimated_time=3.0,
                dependencies=["open_editor"]
            )
        ]
        
        self.workflow_templates["development"] = dev_workflow
        
        # Research workflow
        research_workflow = [
            WorkflowStep(
                step_id="open_browser",
                action="open_app",
                parameters={"app_id": "firefox", "search": "research_topic"},
                description="Open browser for research",
                estimated_time=2.0
            ),
            WorkflowStep(
                step_id="open_notes",
                action="open_app",
                parameters={"app_id": "notes", "topic": "research_notes"},
                description="Open notes application",
                estimated_time=1.0
            )
        ]
        
        self.workflow_templates["research"] = research_workflow
        
        self.logger.info(f"Initialized {len(self.workflow_templates)} workflow templates")
    
    async def start_conversation(self) -> bool:
        """Start a new conversation session"""
        try:
            self.active_session = True
            self.session_start_time = time.time()
            
            # Generate initial greeting
            greeting = await self._generate_greeting()
            
            self.logger.info("Conversation session started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start conversation: {e}")
            return False
    
    async def end_conversation(self) -> bool:
        """End the current conversation session"""
        try:
            self.active_session = False
            
            # Save conversation history
            await self._save_conversation_history()
            
            # Generate farewell
            farewell = await self._generate_farewell()
            
            self.logger.info("Conversation session ended")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to end conversation: {e}")
            return False
    
    async def process_input(self, user_input: str) -> ConversationTurn:
        """Process user input and generate response"""
        start_time = time.time()
        
        try:
            # Preprocess input
            processed_input = self._preprocess_input(user_input)
            
            # Extract intent and entities
            intent_result = await self._extract_intent(processed_input)
            
            # Generate response
            response = await self._generate_response(processed_input, intent_result)
            
            # Execute actions
            actions_taken = await self._execute_actions(intent_result)
            
            # Create conversation turn
            turn = ConversationTurn(
                turn_id=str(uuid.uuid4()),
                user_input=user_input,
                intent=intent_result.get("intent"),
                entities=intent_result.get("entities", {}),
                response=response,
                actions_taken=actions_taken,
                confidence=intent_result.get("confidence", 0.0),
                timestamp=time.time(),
                context=self.current_context.copy()
            )
            
            # Update conversation history
            self.conversation_history.append(turn)
            if len(self.conversation_history) > self.max_conversation_history:
                self.conversation_history.pop(0)
            
            # Update performance metrics
            response_time = time.time() - start_time
            self._update_performance_metrics(response_time, True)
            
            # Update context
            self._update_context(intent_result)
            
            # Record interaction for learning
            if self.prediction_engine:
                self.prediction_engine.record_user_action(
                    f"conversational_input_{intent_result.get('intent', 'unknown')}",
                    {"input": user_input, "context": self.current_context}
                )
            
            self.interaction_count += 1
            self.successful_interactions += 1
            
            return turn
            
        except Exception as e:
            self.logger.error(f"Failed to process input: {e}")
            
            # Create error response turn
            error_turn = ConversationTurn(
                turn_id=str(uuid.uuid4()),
                user_input=user_input,
                intent=None,
                entities={},
                response="I'm sorry, I had trouble understanding that. Could you rephrase it?",
                actions_taken=[],
                confidence=0.0,
                timestamp=time.time(),
                context=self.current_context.copy()
            )
            
            self.conversation_history.append(error_turn)
            self._update_performance_metrics(time.time() - start_time, False)
            
            return error_turn
    
    def _preprocess_input(self, user_input: str) -> str:
        """Preprocess user input"""
        # Basic preprocessing
        processed = user_input.strip().lower()
        
        # Remove extra whitespace
        processed = re.sub(r'\s+', ' ', processed)
        
        # Handle common abbreviations
        abbreviations = {
            "pls": "please",
            "thx": "thanks",
            "gonna": "going to",
            "wanna": "want to",
            "gotta": "got to"
        }
        
        for abbr, expansion in abbreviations.items():
            processed = processed.replace(abbr, expansion)
        
        return processed
    
    async def _extract_intent(self, processed_input: str) -> Dict[str, Any]:
        """Extract intent and entities from processed input"""
        try:
            # Use intent engine if available
            if hasattr(self.intent_engine, 'process_intent'):
                return await self.intent_engine.process_intent(processed_input)
            
            # Fallback to rule-based intent extraction
            return self._extract_intent_rule_based(processed_input)
            
        except Exception as e:
            self.logger.debug(f"Intent extraction failed: {e}")
            return {"intent": "unknown", "entities": {}, "confidence": 0.0}
    
    def _extract_intent_rule_based(self, processed_input: str) -> Dict[str, Any]:
        """Rule-based intent extraction"""
        # Command patterns
        command_patterns = {
            (r"open|launch|start", "system_control"): IntentCategory.APP_MANAGEMENT,
            (r"close|quit|exit", "system_control"): IntentCategory.APP_MANAGEMENT,
            (r"find|search|locate", "information"): IntentCategory.FILE_OPERATIONS,
            (r"create|make|new", "system_control"): IntentCategory.FILE_OPERATIONS,
            (r"delete|remove|trash", "system_control"): IntentCategory.FILE_OPERATIONS,
            (r"show|display|what is", "query"): IntentCategory.INFORMATION,
            (r"help|how to|assist", "help"): IntentCategory.HELP,
            (r"workflow|automate|when", "workflow"): IntentCategory.WORKFLOW
        }
        
        # Extract entities
        entities = {}
        
        # App names
        app_names = ["firefox", "chrome", "vscode", "terminal", "settings", "files"]
        for app in app_names:
            if app in processed_input:
                entities["app_name"] = app
        
        # File paths
        file_path_pattern = r'(/[^ ]+|~[^ ]+|[a-zA-Z]:\\[^ ]+)'
        file_matches = re.findall(file_path_pattern, processed_input)
        if file_matches:
            entities["file_path"] = file_matches[0]
        
        # Determine intent and category
        intent = "unknown"
        category = IntentCategory.HELP
        confidence = 0.0
        
        for pattern, intent_category in command_patterns:
            if re.search(pattern[0], processed_input):
                intent = pattern[1]
                category = intent_category
                confidence = 0.8
                break
        
        return {
            "intent": intent,
            "category": category.value,
            "entities": entities,
            "confidence": confidence
        }
    
    async def _generate_response(self, processed_input: str, 
                                intent_result: Dict[str, Any]) -> str:
        """Generate natural language response"""
        try:
            intent = intent_result.get("intent", "unknown")
            entities = intent_result.get("entities", {})
            confidence = intent_result.get("confidence", 0.0)
            
            # Use NLP model if available and confidence is low
            if self.nlp_model and confidence < 0.7:
                return await self._generate_response_with_nlp(processed_input)
            
            # Use rule-based response generation
            return self._generate_response_rule_based(intent, entities, confidence)
            
        except Exception as e:
            self.logger.debug(f"Response generation failed: {e}")
            return "I'm processing your request..."
    
    async def _generate_response_with_nlp(self, processed_input: str) -> str:
        """Generate response using NLP model"""
        try:
            # Prepare conversation history for context
            context = []
            for turn in self.conversation_history[-3:]:  # Last 3 turns
                context.append(f"User: {turn.user_input}")
                context.append(f"Aurora: {turn.response}")
            
            context.append(f"User: {processed_input}")
            
            # Generate response using the model
            input_text = " ".join(context)
            inputs = self.tokenizer.encode(input_text, return_tensors="pt", 
                                         truncation=True, max_length=512)
            
            with torch.no_grad():
                outputs = self.nlp_model.generate(
                    inputs,
                    max_length=inputs.shape[1] + 50,
                    num_return_sequences=1,
                    temperature=0.7,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract only the new part of the response
            if "Aurora:" in response:
                response = response.split("Aurora:")[-1].strip()
            
            return response
            
        except Exception as e:
            self.logger.debug(f"NLP response generation failed: {e}")
            return "I'm working on that..."
    
    def _generate_response_rule_based(self, intent: str, entities: Dict[str, Any], 
                                    confidence: float) -> str:
        """Generate response using rules"""
        responses = {
            "open": self._generate_open_response(entities),
            "close": self._generate_close_response(entities),
            "find": self._generate_find_response(entities),
            "show": self._generate_show_response(entities),
            "help": self._generate_help_response(),
            "workflow": self._generate_workflow_response(entities),
            "unknown": self._generate_fallback_response(entities)
        }
        
        base_response = responses.get(intent, responses["unknown"])
        
        # Add confidence indicator if needed
        if confidence < 0.5:
            base_response = "I think you want to " + base_response.lower()
        
        return base_response
    
    def _generate_open_response(self, entities: Dict[str, Any]) -> str:
        """Generate response for open intent"""
        app_name = entities.get("app_name")
        if app_name:
            return f"Opening {app_name}..."
        return "What would you like me to open?"
    
    def _generate_close_response(self, entities: Dict[str, Any]) -> str:
        """Generate response for close intent"""
        app_name = entities.get("app_name")
        if app_name:
            return f"Closing {app_name}..."
        return "What would you like me to close?"
    
    def _generate_find_response(self, entities: Dict[str, Any]) -> str:
        """Generate response for find intent"""
        file_path = entities.get("file_path")
        if file_path:
            return f"Looking for {file_path}..."
        return "What would you like me to find?"
    
    def _generate_show_response(self, entities: Dict[str, Any]) -> str:
        """Generate response for show intent"""
        return "Here's what you asked for..."
    
    def _generate_help_response(self) -> str:
        """Generate help response"""
        help_text = """I can help you with various tasks:
• Open applications: "open firefox" or "launch vscode"
• Find files: "find my documents" or "search for config.txt"
• Get system info: "show battery level" or "what's my cpu usage?"
• Automate workflows: "when I start coding, open my dev tools"
• General assistance: just ask me anything!

What would you like help with?"""
        return help_text
    
    def _generate_workflow_response(self, entities: Dict[str, Any]) -> str:
        """Generate workflow response"""
        return "I can help you automate that workflow. Let me set that up for you..."
    
    def _generate_fallback_response(self, entities: Dict[str, Any]) -> str:
        """Generate fallback response"""
        return "I'm not sure what you want to do. Can you be more specific or say 'help' for assistance?"
    
    async def _execute_actions(self, intent_result: Dict[str, Any]) -> List[str]:
        """Execute actions based on intent"""
        actions_taken = []
        
        try:
            intent = intent_result.get("intent", "unknown")
            entities = intent_result.get("entities", {})
            
            # Queue actions for execution
            if intent == "open" and "app_name" in entities:
                action = {
                    "type": "open_app",
                    "app_id": entities["app_name"],
                    "parameters": entities
                }
                self.action_queue.put(action)
                actions_taken.append(f"Queued opening {entities['app_name']}")
            
            elif intent == "close" and "app_name" in entities:
                action = {
                    "type": "close_app",
                    "app_id": entities["app_name"],
                    "parameters": entities
                }
                self.action_queue.put(action)
                actions_taken.append(f"Queued closing {entities['app_name']}")
            
            elif intent == "find" and "file_path" in entities:
                action = {
                    "type": "find_file",
                    "path": entities["file_path"],
                    "parameters": entities
                }
                self.action_queue.put(action)
                actions_taken.append(f"Queued finding {entities['file_path']}")
            
        except Exception as e:
            self.logger.debug(f"Action execution failed: {e}")
        
        return actions_taken
    
    def _action_execution_loop(self) -> None:
        """Background loop for executing actions"""
        while True:
            try:
                if not self.action_queue.empty():
                    action = self.action_queue.get()
                    self._execute_single_action(action)
                else:
                    time.sleep(0.1)
                    
            except Exception as e:
                self.logger.error(f"Action execution error: {e}")
    
    def _execute_single_action(self, action: Dict[str, Any]) -> None:
        """Execute a single action"""
        try:
            action_type = action.get("type")
            
            if action_type == "open_app":
                app_id = action.get("app_id")
                self.logger.info(f"Opening application: {app_id}")
                # Would actually open the app
                
            elif action_type == "close_app":
                app_id = action.get("app_id")
                self.logger.info(f"Closing application: {app_id}")
                # Would actually close the app
                
            elif action_type == "find_file":
                path = action.get("path")
                self.logger.info(f"Finding file: {path}")
                # Would actually find the file
                
        except Exception as e:
            self.logger.error(f"Failed to execute action {action}: {e}")
    
    def _suggestion_update_loop(self) -> None:
        """Background loop for updating suggestions"""
        while True:
            try:
                if self.enable_proactive_suggestions:
                    self._update_suggestions()
                
                time.sleep(10)  # Update every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Suggestion update error: {e}")
    
    def _update_suggestions(self) -> None:
        """Update proactive suggestions"""
        try:
            current_time = time.time()
            
            # Don't update too frequently
            if current_time - self.last_suggestion_update < 30:
                return
            
            # Get predictions from prediction engine
            if self.prediction_engine:
                predictions = self.prediction_engine.get_predictions(
                    PredictionType.APP_LAUNCH
                )
                
                # Convert predictions to suggestions
                suggestions = []
                for pred in predictions[:self.suggestion_count]:
                    suggestion = SuggestedAction(
                        suggestion_id=str(uuid.uuid4()),
                        title=f"Open {pred.target_id}",
                        description=f"Based on your usage patterns",
                        command=f"open {pred.target_id}",
                        probability=pred.probability,
                        confidence=pred.confidence,
                        category=IntentCategory.APP_MANAGEMENT,
                        context_relevance=self._calculate_context_relevance(pred)
                    )
                    suggestions.append(suggestion)
                
                self.current_suggestions = suggestions
                self.last_suggestion_update = current_time
                
        except Exception as e:
            self.logger.debug(f"Suggestion update failed: {e}")
    
    def _calculate_context_relevance(self, prediction) -> float:
        """Calculate context relevance for a prediction"""
        # Simplified relevance calculation
        return prediction.confidence * 0.8 + prediction.probability * 0.2
    
    def _update_performance_metrics(self, response_time: float, success: bool) -> None:
        """Update performance metrics"""
        if success:
            # Update average response time
            total_interactions = self.interaction_count + 1
            self.avg_response_time = (
                (self.avg_response_time * self.interaction_count + response_time) / 
                total_interactions
            )
    
    def _update_context(self, intent_result: Dict[str, Any]) -> None:
        """Update current conversation context"""
        self.current_context.update({
            "last_intent": intent_result.get("intent"),
            "last_entities": intent_result.get("entities", {}),
            "last_confidence": intent_result.get("confidence", 0.0),
            "conversation_length": len(self.conversation_history),
            "session_duration": time.time() - self.session_start_time if self.session_start_time else 0
        })
    
    async def _generate_greeting(self) -> str:
        """Generate initial greeting"""
        greetings = [
            "Hello! I'm Aurora, your AI assistant. How can I help you today?",
            "Hi there! I'm ready to assist you. What would you like to do?",
            "Good day! I'm here to help make your computing experience better. What's on your mind?"
        ]
        
        # Select greeting based on time of day
        hour = time.localtime().tm_hour
        if 6 <= hour < 12:
            greetings.insert(0, "Good morning! I'm Aurora, your AI assistant. How can I help you start your day?")
        elif 12 <= hour < 18:
            greetings.insert(0, "Good afternoon! I'm here to help you stay productive. What do you need?")
        elif 18 <= hour < 22:
            greetings.insert(0, "Good evening! I'm Aurora, ready to assist you. How can I help?")
        
        return greetings[0]
    
    async def _generate_farewell(self) -> str:
        """Generate farewell message"""
        farewells = [
            "Goodbye! It was great helping you today.",
            "See you later! Feel free to ask for help anytime.",
            "Take care! I'll be here when you need me next."
        ]
        
        # Add personalization based on conversation
        if self.interaction_count > 5:
            farewells.insert(0, f"It was great helping you with {self.interaction_count} tasks today. See you next time!")
        
        return farewells[0]
    
    def get_conversation_history(self, limit: Optional[int] = None) -> List[ConversationTurn]:
        """Get conversation history"""
        if limit:
            return self.conversation_history[-limit:]
        return self.conversation_history.copy()
    
    def get_current_suggestions(self) -> List[SuggestedAction]:
        """Get current proactive suggestions"""
        return self.current_suggestions.copy()
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics"""
        return {
            "interaction_count": self.interaction_count,
            "success_rate": (self.successful_interactions / max(1, self.interaction_count)) * 100,
            "avg_response_time": self.avg_response_time,
            "session_duration": time.time() - self.session_start_time if self.session_start_time else 0,
            "active_suggestions": len(self.current_suggestions)
        }
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            # End current session
            if self.active_session:
                await self.end_conversation()
            
            # Save conversation history
            await self._save_conversation_history()
            
            # Cleanup NLP model
            if self.nlp_model:
                del self.nlp_model
                self.nlp_model = None
            if self.tokenizer:
                del self.tokenizer
                self.tokenizer = None
            
            self.logger.info("Conversational palette cleaned up")
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
    
    async def _save_conversation_history(self) -> None:
        """Save conversation history to storage"""
        try:
            # Convert to serializable format
            history_data = []
            for turn in self.conversation_history:
                turn_data = {
                    "turn_id": turn.turn_id,
                    "user_input": turn.user_input,
                    "intent": turn.intent,
                    "entities": turn.entities,
                    "response": turn.response,
                    "actions_taken": turn.actions_taken,
                    "confidence": turn.confidence,
                    "timestamp": turn.timestamp,
                    "context": turn.context
                }
                history_data.append(turn_data)
            
            # Would save to file/database
            self.logger.info(f"Saved {len(history_data)} conversation turns")
            
        except Exception as e:
            self.logger.warning(f"Failed to save conversation history: {e}")


# Global conversational palette instance
aurora_conversational_palette = ConversationalPalette()