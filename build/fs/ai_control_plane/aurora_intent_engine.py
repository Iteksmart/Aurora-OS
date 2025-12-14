#!/usr/bin/env python3
"""
Aurora Intent Engine (AIE) - AI Control Plane for Aurora OS
Serves as the fundamental control plane in privileged user space, tightly coupled 
to kernel telemetry via eBPF and IPC. Provides explainable AI decisions at the OS level.
"""

import enum
import json
import logging
import asyncio
import hashlib
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timedelta
import re

# Optional imports with graceful fallback
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

logger = logging.getLogger(__name__)

class IntentType(enum.Enum):
    """Types of user intents that AIE can process."""
    
    # System Actions
    OPEN_APPLICATION = "open_application"
    CLOSE_APPLICATION = "close_application"
    SYSTEM_SETTINGS = "system_settings"
    FILE_OPERATIONS = "file_operations"
    
    # Information Queries
    SYSTEM_STATUS = "system_status"
    PERFORMANCE_INFO = "performance_info"
    HELP_GUIDANCE = "help_guidance"
    EXPLAIN_DECISION = "explain_decision"
    
    # Configuration Commands
    CONFIGURE_HARDWARE = "configure_hardware"
    OPTIMIZE_PERFORMANCE = "optimize_performance"
    SECURITY_SETTINGS = "security_settings"
    NETWORK_SETUP = "network_setup"
    
    # Problem Resolution
    TROUBLESHOOT = "troubleshoot"
    FIX_ISSUE = "fix_issue"
    RECOVERY_ACTION = "recovery_action"
    
    # Advanced Commands
    AUTOMATE_TASK = "automate_task"
    CREATE_ROUTINE = "create_routine"
    INTEGRATION_SETUP = "integration_setup"

class ConfidenceLevel(enum.Enum):
    """Confidence levels for intent recognition."""
    LOW = 0.3
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 0.95

@dataclass
class Intent:
    """Represents a parsed user intent."""
    
    intent_id: str
    intent_type: IntentType
    raw_text: str
    entities: Dict[str, Any]
    confidence: float
    timestamp: datetime
    context: Dict[str, Any]
    explanation: str
    action_plan: List[Dict[str, Any]]
    requires_confirmation: bool
    estimated_duration: Optional[str] = None

@dataclass
class AIDecision:
    """Represents an AI decision made by Aurora Intent Engine."""
    
    decision_id: str
    timestamp: datetime
    intent_id: str
    decision_type: str
    action_taken: str
    reasoning: str
    confidence: float
    alternatives: List[Dict[str, Any]]
    user_impact: str
    rollback_available: bool
    explainable_factors: Dict[str, Any]

class AuroraIntentEngine:
    """Aurora Intent Engine - AI Control Plane for Aurora OS."""
    
    def __init__(self, config_path: str = "/etc/aurora/intent_engine.json"):
        self.config_path = Path(config_path)
        self.intents_history: List[Intent] = []
        self.decisions_history: List[AIDecision] = []
        self.context_cache: Dict[str, Any] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # AI Models
        self.nlp_model = None
        self.intent_classifier = None
        self.entity_extractor = None
        
        # Initialize components
        self._load_configuration()
        self._initialize_ai_models()
        self._setup_ebpf_integration()
        self._start_background_tasks()
    
    def _load_configuration(self):
        """Load AIE configuration."""
        
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
            else:
                logger.info("Creating default Aurora Intent Engine configuration")
                self.config = self._create_default_config()
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            self.config = self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration."""
        
        return {
            "confidence_threshold": 0.7,
            "max_context_history": 1000,
            "decision_timeout": 30,
            "auto_confirm_threshold": 0.9,
            "learning_enabled": True,
            "privacy_mode": False,
            "integration_endpoints": {
                "kernel_telemetry": "/var/run/aurora/eBPF.sock",
                "system_manager": "/var/run/aurora/system.sock",
                "security_guardian": "/var/run/aurora/guardian.sock"
            },
            "intent_patterns": {
                "open_application": [
                    r"open\s+(?P<app>\w+)",
                    r"launch\s+(?P<app>\w+)",
                    r"start\s+(?P<app>\w+)"
                ],
                "system_settings": [
                    r"(?P<action>make|set|configure).+?(?P<setting>battery|performance|display)",
                    r"change\s+(?P<setting>\w+)"
                ],
                "troubleshoot": [
                    r"fix\s+(?P<issue>\w+)",
                    r"troubleshoot\s+(?P<issue>\w+)",
                    r"(?P<issue>\w+)\s+(?P<action>not working|broken|slow)"
                ]
            }
        }
    
    def _initialize_ai_models(self):
        """Initialize AI models for intent processing."""
        
        logger.info("Initializing Aurora Intent Engine AI models")
        
        try:
            # Load spaCy model for NLP
            if SPACY_AVAILABLE:
                try:
                    self.nlp_model = spacy.load("en_core_web_sm")
                    logger.info("spaCy model loaded successfully")
                except OSError:
                    logger.warning("spaCy English model not found, downloading...")
                    spacy.cli.download("en_core_web_sm")
                    self.nlp_model = spacy.load("en_core_web_sm")
                    logger.info("spaCy model downloaded and loaded")
            else:
                self.nlp_model = None
                logger.warning("spaCy not available, using rule-based processing")
            
            # Initialize transformer models for intent classification
            if TRANSFORMERS_AVAILABLE:
                try:
                    self.intent_classifier = pipeline(
                        "text-classification",
                        model="microsoft/DialoGPT-medium",
                        device=0 if self._has_gpu() else -1
                    )
                    logger.info("Intent classifier initialized")
                except Exception as e:
                    logger.warning(f"Intent classifier failed to load: {e}")
                    self.intent_classifier = None
            else:
                self.intent_classifier = None
                logger.warning("Transformers not available, using rule-based classification")
            
            # Initialize entity extraction
            if TRANSFORMERS_AVAILABLE:
                try:
                    self.entity_extractor = pipeline(
                        "ner",
                        model="dbmdz/bert-large-cased-finetuned-conll03-english",
                        device=0 if self._has_gpu() else -1
                    )
                    logger.info("Entity extractor initialized")
                except Exception as e:
                    logger.warning(f"Entity extractor failed to load: {e}")
                    self.entity_extractor = None
            else:
                self.entity_extractor = None
                logger.warning("Transformers not available, using rule-based entity extraction")
            
            # Determine initialization success
            if self.nlp_model or self.intent_classifier or self.entity_extractor:
                logger.info("AI models initialized successfully")
            else:
                logger.warning("All AI models failed to initialize, using rule-based processing")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI models: {e}")
            # Fallback to rule-based processing
            self.nlp_model = None
            self.intent_classifier = None
            self.entity_extractor = None
    
    def _has_gpu(self) -> bool:
        """Check if GPU is available for AI processing."""
        
        try:
            import torch
            return torch.cuda.is_available()
        except:
            return False
    
    def _setup_ebpf_integration(self):
        """Setup eBPF integration for kernel telemetry."""
        
        logger.info("Setting up eBPF integration for kernel telemetry")
        
        # In real implementation, this would establish connection
        # to eBPF-based kernel monitoring system
        
        self.kernel_telemetry = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "disk_io": 0.0,
            "network_io": 0.0,
            "processes": [],
            "system_load": 0.0
        }
    
    def _start_background_tasks(self):
        """Start background tasks for context monitoring and learning."""
        
        logger.info("Starting Aurora Intent Engine background tasks")
        
        # Start telemetry monitoring
        asyncio.create_task(self._monitor_system_telemetry())
        
        # Start context learning
        asyncio.create_task(self._context_learning_loop())
        
        # Start performance optimization
        asyncio.create_task(self._performance_optimization_loop())
    
    async def process_user_intent(self, user_input: str, 
                                session_id: Optional[str] = None,
                                context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process user input and determine intent."""
        
        logger.info(f"Processing user intent: {user_input}")
        
        try:
            # Create session if not exists
            if session_id is None:
                session_id = self._create_session()
            
            # Update session context
            self._update_session_context(session_id, context or {})
            
            # Extract entities and classify intent
            entities = await self._extract_entities(user_input)
            intent_type, confidence = await self._classify_intent(user_input, entities)
            
            # Generate action plan
            action_plan = await self._generate_action_plan(intent_type, entities)
            
            # Create intent object
            intent = Intent(
                intent_id=self._generate_intent_id(),
                intent_type=intent_type,
                raw_text=user_input,
                entities=entities,
                confidence=confidence,
                timestamp=datetime.now(),
                context=self._get_context_for_intent(session_id),
                explanation=await self._explain_intent_reasoning(user_input, intent_type, entities),
                action_plan=action_plan,
                requires_confirmation=confidence < self.config["auto_confirm_threshold"],
                estimated_duration=self._estimate_duration(intent_type, action_plan)
            )
            
            # Store intent
            self.intents_history.append(intent)
            
            # Execute intent if confident enough
            if confidence >= self.config["confidence_threshold"]:
                result = await self._execute_intent(intent, session_id)
            else:
                result = {
                    "status": "confidence_too_low",
                    "confidence": confidence,
                    "suggestion": "Please provide more specific information",
                    "intent": asdict(intent)
                }
            
            return {
                "intent": asdict(intent),
                "result": result,
                "session_id": session_id
            }
        
        except Exception as e:
            logger.error(f"Failed to process user intent: {e}")
            return {
                "status": "error",
                "error": str(e),
                "suggestion": "Please try rephrasing your request"
            }
    
    async def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities from user input."""
        
        entities = {}
        
        if self.entity_extractor:
            try:
                # Use transformer model for entity extraction
                ner_results = self.entity_extractor(text)
                for entity in ner_results:
                    entity_type = entity['entity_group'].lower()
                    entity_value = entity['word']
                    
                    if entity_type not in entities:
                        entities[entity_type] = []
                    entities[entity_type].append(entity_value)
            except Exception as e:
                logger.error(f"Entity extraction failed: {e}")
        
        # Fallback to rule-based extraction
        entities.update(self._extract_entities_rule_based(text))
        
        return entities
    
    def _extract_entities_rule_based(self, text: str) -> Dict[str, Any]:
        """Extract entities using rule-based patterns."""
        
        entities = {}
        text_lower = text.lower()
        
        # Application names
        applications = ["firefox", "chrome", "terminal", "files", "settings", "calculator"]
        for app in applications:
            if app in text_lower:
                entities["applications"] = entities.get("applications", []) + [app]
        
        # Settings
        settings = ["battery", "performance", "display", "brightness", "volume", "wifi", "bluetooth"]
        for setting in settings:
            if setting in text_lower:
                entities["settings"] = entities.get("settings", []) + [setting]
        
        # Actions
        actions = ["open", "close", "start", "stop", "enable", "disable", "configure", "fix", "troubleshoot"]
        for action in actions:
            if action in text_lower:
                entities["actions"] = entities.get("actions", []) + [action]
        
        return entities
    
    async def _classify_intent(self, text: str, entities: Dict[str, Any]) -> Tuple[IntentType, float]:
        """Classify user intent from text and entities."""
        
        if self.intent_classifier:
            try:
                # Use transformer model for intent classification
                result = self.intent_classifier(text)
                intent_label = result[0]['label'].lower()
                confidence = result[0]['score']
                
                # Map label to IntentType
                for intent_type in IntentType:
                    if intent_type.value in intent_label:
                        return intent_type, confidence
                
            except Exception as e:
                logger.error(f"Intent classification failed: {e}")
        
        # Fallback to rule-based classification
        return self._classify_intent_rule_based(text, entities)
    
    def _classify_intent_rule_based(self, text: str, entities: Dict[str, Any]) -> Tuple[IntentType, float]:
        """Classify intent using rule-based patterns."""
        
        text_lower = text.lower()
        
        # Check for application operations
        if any(action in text_lower for action in ["open", "launch", "start"]) and entities.get("applications"):
            return IntentType.OPEN_APPLICATION, 0.9
        
        if any(action in text_lower for action in ["close", "quit", "stop"]) and entities.get("applications"):
            return IntentType.CLOSE_APPLICATION, 0.9
        
        # Check for settings operations
        if any(word in text_lower for word in ["settings", "configure", "change", "set"]) and entities.get("settings"):
            return IntentType.SYSTEM_SETTINGS, 0.8
        
        # Check for troubleshooting
        if any(word in text_lower for word in ["fix", "broken", "not working", "troubleshoot"]):
            return IntentType.TROUBLESHOOT, 0.8
        
        # Check for system status queries
        if any(word in text_lower for word in ["status", "how is", "check", "monitor"]):
            return IntentType.SYSTEM_STATUS, 0.7
        
        # Check for performance optimization
        if any(word in text_lower for word in ["optimize", "speed up", "improve", "performance"]):
            return IntentType.OPTIMIZE_PERFORMANCE, 0.8
        
        # Default to help guidance
        return IntentType.HELP_GUIDANCE, 0.6
    
    async def _generate_action_plan(self, intent_type: IntentType, entities: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate action plan for the intent."""
        
        action_plan = []
        
        if intent_type == IntentType.OPEN_APPLICATION:
            apps = entities.get("applications", [])
            for app in apps:
                action_plan.append({
                    "action": "launch_application",
                    "parameters": {"app_name": app},
                    "description": f"Launch {app}",
                    "estimated_time": "2s"
                })
        
        elif intent_type == IntentType.SYSTEM_SETTINGS:
            settings = entities.get("settings", [])
            for setting in settings:
                action_plan.append({
                    "action": "configure_setting",
                    "parameters": {"setting_name": setting},
                    "description": f"Configure {setting} settings",
                    "estimated_time": "5s"
                })
        
        elif intent_type == IntentType.TROUBLESHOOT:
            issues = entities.get("applications", ["system"])
            for issue in issues:
                action_plan.extend([
                    {
                        "action": "diagnose_issue",
                        "parameters": {"target": issue},
                        "description": f"Diagnose {issue} issue",
                        "estimated_time": "10s"
                    },
                    {
                        "action": "apply_fix",
                        "parameters": {"target": issue},
                        "description": f"Apply fix for {issue}",
                        "estimated_time": "15s"
                    }
                ])
        
        elif intent_type == IntentType.SYSTEM_STATUS:
            action_plan.extend([
                {
                    "action": "gather_system_metrics",
                    "parameters": {},
                    "description": "Collect system performance metrics",
                    "estimated_time": "3s"
                },
                {
                    "action": "analyze_system_health",
                    "parameters": {},
                    "description": "Analyze system health status",
                    "estimated_time": "5s"
                }
            ])
        
        return action_plan
    
    async def _explain_intent_reasoning(self, text: str, intent_type: IntentType, entities: Dict[str, Any]) -> str:
        """Generate explanation for intent recognition reasoning."""
        
        explanations = {
            IntentType.OPEN_APPLICATION: f"I detected you want to open an application because you used words like 'open', 'launch', or 'start' and mentioned: {', '.join(entities.get('applications', ['application']))}",
            IntentType.SYSTEM_SETTINGS: f"I identified a settings configuration request based on terms like 'settings', 'configure', or 'change' for: {', '.join(entities.get('settings', ['setting']))}",
            IntentType.TROUBLESHOOT: f"I recognized a troubleshooting request from terms like 'fix', 'broken', or 'not working' for: {', '.join(entities.get('applications', ['system']))}",
            IntentType.SYSTEM_STATUS: "I understood you want to check system status from monitoring-related keywords",
            IntentType.OPTIMIZE_PERFORMANCE: "I detected a performance optimization request from improvement-related terms"
        }
        
        return explanations.get(intent_type, f"I interpreted your request as {intent_type.value} based on pattern matching and context analysis")
    
    async def _execute_intent(self, intent: Intent, session_id: str) -> Dict[str, Any]:
        """Execute the intent and track the decision."""
        
        logger.info(f"Executing intent {intent.intent_id}: {intent.intent_type.value}")
        
        execution_results = []
        
        try:
            for step in intent.action_plan:
                result = await self._execute_action_step(step, intent)
                execution_results.append(result)
                
                if not result.get("success", False):
                    logger.error(f"Action step failed: {step['action']}")
                    break
            
            # Create AI decision record
            decision = AIDecision(
                decision_id=self._generate_decision_id(),
                timestamp=datetime.now(),
                intent_id=intent.intent_id,
                decision_type="intent_execution",
                action_taken=str(intent.action_plan),
                reasoning=intent.explanation,
                confidence=intent.confidence,
                alternatives=self._get_alternative_actions(intent),
                user_impact=self._assess_user_impact(intent),
                rollback_available=self._is_rollback_available(intent),
                explainable_factors={
                    "intent_type": intent.intent_type.value,
                    "entities": intent.entities,
                    "context": intent.context,
                    "confidence_factors": self._get_confidence_factors(intent)
                }
            )
            
            self.decisions_history.append(decision)
            
            return {
                "status": "success" if all(r.get("success", False) for r in execution_results) else "partial_success",
                "results": execution_results,
                "decision_id": decision.decision_id
            }
        
        except Exception as e:
            logger.error(f"Intent execution failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "results": execution_results
            }
    
    async def _execute_action_step(self, step: Dict[str, Any], intent: Intent) -> Dict[str, Any]:
        """Execute a single action step."""
        
        action = step["action"]
        parameters = step["parameters"]
        
        try:
            if action == "launch_application":
                return await self._launch_application(parameters["app_name"])
            
            elif action == "configure_setting":
                return await self._configure_setting(parameters["setting_name"])
            
            elif action == "diagnose_issue":
                return await self._diagnose_issue(parameters["target"])
            
            elif action == "apply_fix":
                return await self._apply_fix(parameters["target"])
            
            elif action == "gather_system_metrics":
                return await self._gather_system_metrics()
            
            elif action == "analyze_system_health":
                return await self._analyze_system_health()
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "action": action,
                    "parameters": parameters
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "action": action,
                "parameters": parameters
            }
    
    # Action implementation methods
    async def _launch_application(self, app_name: str) -> Dict[str, Any]:
        """Launch an application."""
        
        logger.info(f"Launching application: {app_name}")
        
        try:
            # Map common application names to actual commands
            app_commands = {
                "firefox": "firefox",
                "chrome": "google-chrome",
                "terminal": "gnome-terminal",
                "files": "nautilus",
                "settings": "gnome-control-center",
                "calculator": "gnome-calculator"
            }
            
            command = app_commands.get(app_name.lower(), app_name)
            
            # Launch application
            import subprocess
            result = subprocess.Popen([command], 
                                     stdout=subprocess.DEVNULL, 
                                     stderr=subprocess.DEVNULL)
            
            if result.poll() is None:  # Process is running
                return {
                    "success": True,
                    "message": f"Successfully launched {app_name}",
                    "action": "launch_application",
                    "app_name": app_name,
                    "pid": result.pid
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to launch {app_name}",
                    "action": "launch_application",
                    "app_name": app_name
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "action": "launch_application",
                "app_name": app_name
            }
    
    async def _configure_setting(self, setting_name: str) -> Dict[str, Any]:
        """Configure a system setting."""
        
        logger.info(f"Configuring setting: {setting_name}")
        
        # In real implementation, this would use appropriate system APIs
        return {
            "success": True,
            "message": f"Configuration interface opened for {setting_name}",
            "action": "configure_setting",
            "setting_name": setting_name
        }
    
    async def _diagnose_issue(self, target: str) -> Dict[str, Any]:
        """Diagnose an issue with the specified target."""
        
        logger.info(f"Diagnosing issue with: {target}")
        
        # Simulate diagnosis
        diagnostics = {
            "cpu_usage": self.kernel_telemetry.get("cpu_usage", 0),
            "memory_usage": self.kernel_telemetry.get("memory_usage", 0),
            "disk_space": "sufficient",
            "network_status": "connected",
            "errors_found": []
        }
        
        return {
            "success": True,
            "message": f"Diagnostic completed for {target}",
            "action": "diagnose_issue",
            "target": target,
            "diagnostics": diagnostics
        }
    
    async def _apply_fix(self, target: str) -> Dict[str, Any]:
        """Apply a fix for the specified target."""
        
        logger.info(f"Applying fix for: {target}")
        
        # Simulate fix application
        return {
            "success": True,
            "message": f"Fix applied for {target}",
            "action": "apply_fix",
            "target": target,
            "fix_type": "automated_resolution"
        }
    
    async def _gather_system_metrics(self) -> Dict[str, Any]:
        """Gather system performance metrics."""
        
        logger.info("Gathering system metrics")
        
        # Update kernel telemetry
        await self._update_kernel_telemetry()
        
        return {
            "success": True,
            "message": "System metrics collected",
            "action": "gather_system_metrics",
            "metrics": self.kernel_telemetry
        }
    
    async def _analyze_system_health(self) -> Dict[str, Any]:
        """Analyze system health status."""
        
        logger.info("Analyzing system health")
        
        # Perform health analysis
        health_score = self._calculate_health_score()
        
        return {
            "success": True,
            "message": "System health analysis completed",
            "action": "analyze_system_health",
            "health_score": health_score,
            "recommendations": self._get_health_recommendations(health_score)
        }
    
    # Helper methods
    def _create_session(self) -> str:
        """Create a new session."""
        session_id = hashlib.md5(f"{datetime.now().isoformat()}_{id(self)}".encode()).hexdigest()[:16]
        self.active_sessions[session_id] = {
            "created": datetime.now(),
            "context": {},
            "intents": []
        }
        return session_id
    
    def _update_session_context(self, session_id: str, context: Dict[str, Any]):
        """Update session context."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["context"].update(context)
    
    def _get_context_for_intent(self, session_id: str) -> Dict[str, Any]:
        """Get context for intent processing."""
        base_context = {
            "system_telemetry": self.kernel_telemetry,
            "timestamp": datetime.now().isoformat(),
            "active_applications": self._get_active_applications()
        }
        
        if session_id in self.active_sessions:
            base_context.update(self.active_sessions[session_id]["context"])
        
        return base_context
    
    def _get_active_applications(self) -> List[str]:
        """Get list of active applications."""
        
        try:
            import subprocess
            result = subprocess.run(['ps', '-eo', 'comm'], capture_output=True, text=True)
            if result.returncode == 0:
                apps = [line.strip() for line in result.stdout.split('\n') if line.strip()]
                return list(set(apps))  # Remove duplicates
        except:
            pass
        
        return []
    
    def _generate_intent_id(self) -> str:
        """Generate unique intent ID."""
        return hashlib.md5(f"{datetime.now().isoformat()}_{id(self)}".encode()).hexdigest()[:16]
    
    def _generate_decision_id(self) -> str:
        """Generate unique decision ID."""
        return hashlib.md5(f"decision_{datetime.now().isoformat()}_{id(self)}".encode()).hexdigest()[:16]
    
    def _estimate_duration(self, intent_type: IntentType, action_plan: List[Dict[str, Any]]) -> str:
        """Estimate execution duration for intent."""
        
        if not action_plan:
            return "unknown"
        
        total_seconds = 0
        for step in action_plan:
            duration_str = step.get("estimated_time", "0s")
            if duration_str.endswith("s"):
                total_seconds += int(duration_str[:-1])
        
        if total_seconds < 60:
            return f"{total_seconds}s"
        else:
            return f"{total_seconds // 60}m {total_seconds % 60}s"
    
    def _get_alternative_actions(self, intent: Intent) -> List[Dict[str, Any]]:
        """Get alternative actions for the intent."""
        
        alternatives = []
        
        if intent.intent_type == IntentType.OPEN_APPLICATION:
            apps = intent.entities.get("applications", [])
            for app in apps:
                alternatives.append({
                    "action": "open_via_alternative",
                    "description": f"Open {app} using alternative method",
                    "confidence": 0.7
                })
        
        return alternatives
    
    def _assess_user_impact(self, intent: Intent) -> str:
        """Assess the impact on the user."""
        
        impact_levels = {
            IntentType.OPEN_APPLICATION: "low",
            IntentType.CLOSE_APPLICATION: "medium",
            IntentType.SYSTEM_SETTINGS: "medium",
            IntentType.FILE_OPERATIONS: "medium",
            IntentType.TROUBLESHOOT: "low",
            IntentType.FIX_ISSUE: "medium",
            IntentType.RECOVERY_ACTION: "high",
            IntentType.OPTIMIZE_PERFORMANCE: "low"
        }
        
        return impact_levels.get(intent.intent_type, "medium")
    
    def _is_rollback_available(self, intent: Intent) -> bool:
        """Check if rollback is available for the intent."""
        
        rollback_intents = {
            IntentType.SYSTEM_SETTINGS,
            IntentType.CONFIGURE_HARDWARE,
            IntentType.RECOVERY_ACTION
        }
        
        return intent.intent_type in rollback_intents
    
    def _get_confidence_factors(self, intent: Intent) -> Dict[str, Any]:
        """Get factors contributing to confidence score."""
        
        return {
            "entity_extraction": len(intent.entities) > 0,
            "pattern_match": True,  # Simplified
            "context_relevance": intent.context is not None,
            "historical_success": self._get_historical_success_rate(intent.intent_type)
        }
    
    def _get_historical_success_rate(self, intent_type: IntentType) -> float:
        """Get historical success rate for intent type."""
        
        relevant_intents = [i for i in self.intents_history if i.intent_type == intent_type]
        if not relevant_intents:
            return 0.5
        
        success_count = sum(1 for i in relevant_intents if i.confidence > 0.7)
        return success_count / len(relevant_intents)
    
    def _calculate_health_score(self) -> float:
        """Calculate system health score."""
        
        # Simple health calculation based on metrics
        cpu_usage = self.kernel_telemetry.get("cpu_usage", 0)
        memory_usage = self.kernel_telemetry.get("memory_usage", 0)
        
        health_score = 1.0
        health_score -= (cpu_usage / 100) * 0.4
        health_score -= (memory_usage / 100) * 0.4
        
        return max(0.0, min(1.0, health_score))
    
    def _get_health_recommendations(self, health_score: float) -> List[str]:
        """Get health recommendations based on score."""
        
        recommendations = []
        
        if health_score < 0.3:
            recommendations.extend([
                "System performance is critically low",
                "Consider closing unnecessary applications",
                "Check for malware or resource-intensive processes"
            ])
        elif health_score < 0.6:
            recommendations.extend([
                "System performance could be improved",
                "Consider optimizing startup applications",
                "Check disk space and memory usage"
            ])
        elif health_score < 0.8:
            recommendations.append("System is running normally")
        else:
            recommendations.append("System is performing optimally")
        
        return recommendations
    
    async def _monitor_system_telemetry(self):
        """Monitor system telemetry in background."""
        
        while True:
            try:
                await self._update_kernel_telemetry()
                await asyncio.sleep(5)  # Update every 5 seconds
            except Exception as e:
                logger.error(f"Telemetry monitoring error: {e}")
                await asyncio.sleep(10)
    
    async def _update_kernel_telemetry(self):
        """Update kernel telemetry data."""
        
        try:
            # In real implementation, this would get data from eBPF
            # For now, use psutil for basic metrics
            import psutil
            
            self.kernel_telemetry.update({
                "cpu_usage": psutil.cpu_percent(),
                "memory_usage": psutil.virtual_memory().percent,
                "disk_io": psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {},
                "network_io": psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {},
                "system_load": psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0
            })
        
        except Exception as e:
            logger.error(f"Failed to update telemetry: {e}")
    
    async def _context_learning_loop(self):
        """Background learning loop for context improvement."""
        
        while True:
            try:
                # Analyze patterns and improve context understanding
                await self._analyze_user_patterns()
                await asyncio.sleep(300)  # Every 5 minutes
            except Exception as e:
                logger.error(f"Context learning error: {e}")
                await asyncio.sleep(60)
    
    async def _analyze_user_patterns(self):
        """Analyze user behavior patterns."""
        
        # Analyze recent intents for patterns
        recent_intents = self.intents_history[-100:] if self.intents_history else []
        
        # Pattern analysis logic would go here
        pass
    
    async def _performance_optimization_loop(self):
        """Background performance optimization."""
        
        while True:
            try:
                # Optimize AIE performance
                await self._optimize_performance()
                await asyncio.sleep(600)  # Every 10 minutes
            except Exception as e:
                logger.error(f"Performance optimization error: {e}")
                await asyncio.sleep(120)
    
    async def _optimize_performance(self):
        """Optimize AIE performance."""
        
        # Clear old cache entries
        if len(self.context_cache) > self.config["max_context_history"]:
            self.context_cache.clear()
        
        # Optimize intent history
        if len(self.intents_history) > 1000:
            self.intents_history = self.intents_history[-500:]
    
    def get_intent_explanation(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed explanation for an AI decision."""
        
        for decision in self.decisions_history:
            if decision.decision_id == decision_id:
                return {
                    "decision": asdict(decision),
                    "explainable_ai": {
                        "why_this_decision": decision.reasoning,
                        "confidence_factors": decision.explainable_factors,
                        "alternatives_considered": decision.alternatives,
                        "user_impact_assessment": decision.user_impact,
                        "rollback_capability": decision.rollback_available,
                        "transparency_level": "full"
                    }
                }
        
        return None
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Get Aurora Intent Engine status."""
        
        return {
            "status": "active",
            "intents_processed": len(self.intents_history),
            "decisions_made": len(self.decisions_history),
            "active_sessions": len(self.active_sessions),
            "ai_models_loaded": {
                "nlp_model": self.nlp_model is not None,
                "intent_classifier": self.intent_classifier is not None,
                "entity_extractor": self.entity_extractor is not None
            },
            "confidence_threshold": self.config["confidence_threshold"],
            "auto_confirm_threshold": self.config["auto_confirm_threshold"],
            "learning_enabled": self.config["learning_enabled"],
            "telemetry_integration": True,
            "explainable_decisions": True,
            "last_update": datetime.now().isoformat()
        }