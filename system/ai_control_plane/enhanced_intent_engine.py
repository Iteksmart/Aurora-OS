#!/usr/bin/env python3
"""
Enhanced AI Control Plane for Aurora OS
Integrates advanced NLP, multimodal AI, and model management
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

# Import our advanced components
from advanced_nlp import AdvancedNLPProcessor, ContextualIntent
from multimodal_ai import MultimodalAI, MultimodalContext
from model_manager import ModelManager, ModelType

class IntentEngineMode(Enum):
    """Intent engine operating modes"""
    TEXT_ONLY = "text_only"
    MULTIMODAL = "multimodal"
    ADAPTIVE = "adaptive"
    LEARNING = "learning"

class ActionPriority(Enum):
    """Action execution priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    URGENT = 5

@dataclass
class EnhancedAction:
    """Enhanced action with multimodal context"""
    action_type: str
    parameters: Dict[str, Any]
    confidence: float
    priority: ActionPriority
    execution_plan: List[Dict[str, Any]]
    multimodal_context: Optional[MultimodalContext]
    estimated_duration: float
    resource_requirements: Dict[str, Any]
    rollback_plan: Optional[List[Dict[str, Any]]] = None

@dataclass
class UserProfile:
    """User profile for personalized interactions"""
    user_id: str
    preferences: Dict[str, Any]
    interaction_history: List[Dict]
    learning_patterns: Dict[str, Any]
    adaptation_rate: float
    privacy_settings: Dict[str, Any]
    accessibility_settings: Dict[str, Any]

class EnhancedIntentEngine:
    """Enhanced AI intent engine with advanced capabilities"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        
        # Initialize core components
        self.nlp_processor = AdvancedNLPProcessor(
            self.config.get("nlp_model_path")
        )
        self.multimodal_ai = MultimodalAI()
        self.model_manager = ModelManager(
            self.config.get("model_dir", "models")
        )
        
        # Operating mode
        self.mode = IntentEngineMode.ADAPTIVE
        
        # User profiles
        self.user_profiles: Dict[str, UserProfile] = {}
        
        # Learning and adaptation
        self.interaction_history: List[Dict] = []
        self.performance_metrics: Dict[str, List[float]] = {}
        
        # State management
        self.current_context = None
        self.last_interaction_time = 0
        self.active_sessions: Dict[str, Dict] = {}
        
        # Start background processes
        self.is_running = False
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file"""
        
        default_config = {
            "nlp_model_path": "models/nlp/advanced",
            "model_dir": "models",
            "multimodal_enabled": True,
            "learning_enabled": True,
            "privacy_mode": "balanced",
            "adaptation_rate": 0.1,
            "max_history_size": 1000,
            "cache_size_mb": 2048
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                self.logger.warning(f"Failed to load config: {e}")
        
        return default_config
    
    async def start(self):
        """Start the enhanced intent engine"""
        
        self.is_running = True
        
        # Start multimodal AI if enabled
        if self.config.get("multimodal_enabled", True):
            await self.multimodal_ai.start()
        
        # Load essential AI models
        await self._load_essential_models()
        
        self.logger.info("Enhanced intent engine started")
    
    async def stop(self):
        """Stop the enhanced intent engine"""
        
        self.is_running = False
        
        # Stop multimodal AI
        await self.multimodal_ai.stop()
        
        # Save user profiles and learning data
        await self._save_learning_data()
        
        self.logger.info("Enhanced intent engine stopped")
    
    async def _load_essential_models(self):
        """Load essential AI models for intent processing"""
        
        essential_models = [
            ("nlp_intent", "1.0.0"),
            ("nlp_entity", "1.0.0"),
            ("context_embedding", "1.0.0")
        ]
        
        for model_name, version in essential_models:
            try:
                await self.model_manager.load_model(model_name, version)
                self.logger.info(f"Loaded essential model: {model_name}")
            except Exception as e:
                self.logger.warning(f"Failed to load model {model_name}: {e}")
    
    async def process_input(
        self,
        input_data: Union[str, Dict[str, Any]],
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[EnhancedAction, Dict[str, Any]]:
        """Process user input with enhanced AI capabilities"""
        
        start_time = time.time()
        
        # Get or create user profile
        user_profile = await self._get_user_profile(user_id)
        
        # Process based on mode
        if self.mode == IntentEngineMode.MULTIMODAL:
            intent, multimodal_context = await self._process_multimodal_input(
                input_data, user_profile, context
            )
        elif self.mode == IntentEngineMode.ADAPTIVE:
            intent, multimodal_context = await self._process_adaptive_input(
                input_data, user_profile, context
            )
        else:
            # Text-only processing
            intent = await self._process_text_input(input_data, user_profile, context)
            multimodal_context = None
        
        # Generate enhanced action plan
        action = await self._generate_enhanced_action(intent, multimodal_context)
        
        # Adapt to user feedback
        await self._adapt_to_user(user_profile, intent, action)
        
        # Update interaction history
        await self._update_interaction_history(
            user_id, input_data, intent, action, multimodal_context
        )
        
        # Calculate performance metrics
        processing_time = time.time() - start_time
        await self._update_performance_metrics(processing_time, intent, action)
        
        # Prepare response metadata
        response_metadata = {
            "processing_time": processing_time,
            "intent_confidence": intent.confidence,
            "multimodal_used": multimodal_context is not None,
            "adaptations_made": len(user_profile.learning_patterns),
            "model_performance": self.model_manager.get_system_stats()
        }
        
        return action, response_metadata
    
    async def _process_multimodal_input(
        self,
        input_data: Union[str, Dict[str, Any]],
        user_profile: UserProfile,
        context: Optional[Dict[str, Any]]
    ) -> Tuple[ContextualIntent, Optional[MultimodalContext]]:
        """Process input with multimodal AI"""
        
        # Get multimodal context
        multimodal_context = await self.multimodal_ai.process_multimodal_input()
        
        # Extract text input
        text_input = ""
        if isinstance(input_data, str):
            text_input = input_data
        elif isinstance(input_data, dict) and "text" in input_data:
            text_input = input_data["text"]
        
        # Process with enhanced context
        enhanced_context = self._create_enhanced_context(
            user_profile, context, multimodal_context
        )
        
        # Process text with advanced NLP
        intent = await self.nlp_processor.process_input(
            text_input, enhanced_context
        )
        
        # Enhance intent with multimodal information
        if multimodal_context:
            intent = self._enhance_intent_with_multimodal(intent, multimodal_context)
        
        return intent, multimodal_context
    
    async def _process_adaptive_input(
        self,
        input_data: Union[str, Dict[str, Any]],
        user_profile: UserProfile,
        context: Optional[Dict[str, Any]]
    ) -> Tuple[ContextualIntent, Optional[MultimodalContext]]:
        """Process input with adaptive intelligence"""
        
        # Determine if multimodal processing is beneficial
        should_use_multimodal = await self._should_use_multimodal(
            input_data, user_profile, context
        )
        
        if should_use_multimodal:
            return await self._process_multimodal_input(input_data, user_profile, context)
        else:
            # Use enhanced text processing
            text_input = input_data if isinstance(input_data, str) else input_data.get("text", "")
            enhanced_context = self._create_enhanced_context(user_profile, context)
            intent = await self.nlp_processor.process_input(text_input, enhanced_context)
            return intent, None
    
    async def _process_text_input(
        self,
        input_data: str,
        user_profile: UserProfile,
        context: Optional[Dict[str, Any]]
    ) -> ContextualIntent:
        """Process text-only input"""
        
        enhanced_context = self._create_enhanced_context(user_profile, context)
        return await self.nlp_processor.process_input(input_data, enhanced_context)
    
    def _create_enhanced_context(
        self,
        user_profile: UserProfile,
        context: Optional[Dict[str, Any]],
        multimodal_context: Optional[MultimodalContext] = None
    ) -> Dict[str, Any]:
        """Create enhanced context for NLP processing"""
        
        enhanced_context = {
            "user_profile": {
                "preferences": user_profile.preferences,
                "interaction_patterns": user_profile.interaction_history[-10:],
                "adaptation_rate": user_profile.adaptation_rate
            }
        }
        
        if context:
            enhanced_context.update(context)
        
        if multimodal_context:
            enhanced_context["multimodal"] = {
                "emotion": multimodal_context.emotion.value if multimodal_context.emotion else None,
                "attention": multimodal_context.attention_state,
                "user_state": multimodal_context.user_state
            }
        
        return enhanced_context
    
    def _enhance_intent_with_multimodal(
        self,
        intent: ContextualIntent,
        multimodal_context: MultimodalContext
    ) -> ContextualIntent:
        """Enhance intent with multimodal information"""
        
        # Adjust confidence based on multimodal agreement
        if multimodal_context.confidence > 0.8:
            intent.confidence = min(1.0, intent.confidence * 1.2)
        
        # Add emotional context
        if multimodal_context.emotion:
            intent.context["emotion"] = multimodal_context.emotion.value
        
        # Add attention state
        intent.context["attention"] = multimodal_context.attention_state
        
        # Adjust based on user state
        if multimodal_context.user_state.get("engagement_level") == "low":
            intent.clarification_needed = True
            if not intent.follow_up_questions:
                intent.follow_up_questions = [
                    "Would you like me to explain this in more detail?",
                    "Is there anything specific you'd like me to help with?"
                ]
        
        return intent
    
    async def _generate_enhanced_action(
        self,
        intent: ContextualIntent,
        multimodal_context: Optional[MultimodalContext]
    ) -> EnhancedAction:
        """Generate enhanced action plan with multimodal context"""
        
        # Determine action type and parameters
        action_type, parameters = await self._map_intent_to_action(intent)
        
        # Calculate priority based on context
        priority = self._calculate_action_priority(intent, multimodal_context)
        
        # Generate execution plan
        execution_plan = await self._generate_execution_plan(
            action_type, parameters, intent, multimodal_context
        )
        
        # Estimate duration and resource requirements
        estimated_duration = self._estimate_execution_duration(action_type, parameters)
        resource_requirements = self._estimate_resource_requirements(action_type, parameters)
        
        # Generate rollback plan for critical actions
        rollback_plan = None
        if priority.value >= ActionPriority.HIGH.value:
            rollback_plan = await self._generate_rollback_plan(action_type, parameters)
        
        return EnhancedAction(
            action_type=action_type,
            parameters=parameters,
            confidence=intent.confidence,
            priority=priority,
            execution_plan=execution_plan,
            multimodal_context=multimodal_context,
            estimated_duration=estimated_duration,
            resource_requirements=resource_requirements,
            rollback_plan=rollback_plan
        )
    
    async def _map_intent_to_action(
        self,
        intent: ContextualIntent
    ) -> Tuple[str, Dict[str, Any]]:
        """Map intent to specific action"""
        
        # Enhanced action mapping with context consideration
        intent_type = intent.intent_type.value
        
        if intent_type == "app_launch":
            app_name = None
            for entity in intent.entities:
                if entity.label == "APPLICATION":
                    app_name = entity.text
                    break
            
            return "launch_application", {
                "app_name": app_name or "unknown",
                "focus_window": True,
                "additional_params": intent.context
            }
        
        elif intent_type == "file_open":
            file_name = None
            for entity in intent.entities:
                if entity.label == "FILE":
                    file_name = entity.text
                    break
            
            return "open_file", {
                "file_path": file_name or "unknown",
                "application": "default",
                "context": intent.context
            }
        
        elif intent_type == "query_info":
            return "get_information", {
                "query": intent.context.get("raw_text", ""),
                "context": intent.context
            }
        
        elif intent_type == "system_settings":
            return "configure_system", {
                "setting": intent.context.get("setting", "unknown"),
                "value": intent.context.get("value", None)
            }
        
        else:
            return "conversation_response", {
                "response_type": intent_type,
                "context": intent.context,
                "entities": [asdict(e) for e in intent.entities]
            }
    
    def _calculate_action_priority(
        self,
        intent: ContextualIntent,
        multimodal_context: Optional[MultimodalContext]
    ) -> ActionPriority:
        """Calculate action priority based on intent and context"""
        
        base_priority = ActionPriority.NORMAL
        
        # Adjust based on intent urgency
        if "urgent" in intent.context.get("raw_text", "").lower():
            base_priority = ActionPriority.HIGH
        elif "emergency" in intent.context.get("raw_text", "").lower():
            base_priority = ActionPriority.URGENT
        
        # Adjust based on user emotional state
        if multimodal_context and multimodal_context.emotion:
            if multimodal_context.emotion.value in ["frustrated", "angry"]:
                base_priority = max(base_priority, ActionPriority.HIGH)
        
        # Adjust based on user attention state
        if multimodal_context and multimodal_context.attention_state == "distracted":
            base_priority = min(base_priority, ActionPriority.LOW)
        
        return base_priority
    
    async def _generate_execution_plan(
        self,
        action_type: str,
        parameters: Dict[str, Any],
        intent: ContextualIntent,
        multimodal_context: Optional[MultimodalContext]
    ) -> List[Dict[str, Any]]:
        """Generate detailed execution plan"""
        
        plan = []
        
        # Add validation step
        plan.append({
            "step": "validate",
            "action": "validate_parameters",
            "parameters": parameters,
            "required_confidence": 0.7
        })
        
        # Add pre-execution steps
        if action_type == "launch_application":
            plan.extend([
                {
                    "step": "check_availability",
                    "action": "verify_app_installed",
                    "parameters": {"app_name": parameters["app_name"]}
                },
                {
                    "step": "prepare_environment",
                    "action": "setup_app_environment",
                    "parameters": parameters
                }
            ])
        
        # Add main execution step
        plan.append({
            "step": "execute",
            "action": action_type,
            "parameters": parameters,
            "expected_duration": self._estimate_execution_duration(action_type, parameters)
        })
        
        # Add post-execution verification
        plan.append({
            "step": "verify",
            "action": "verify_execution_success",
            "parameters": {"action_type": action_type}
        })
        
        return plan
    
    def _estimate_execution_duration(
        self,
        action_type: str,
        parameters: Dict[str, Any]
    ) -> float:
        """Estimate execution duration in seconds"""
        
        duration_map = {
            "launch_application": 2.0,
            "open_file": 1.5,
            "get_information": 1.0,
            "configure_system": 3.0,
            "conversation_response": 0.5
        }
        
        return duration_map.get(action_type, 1.0)
    
    def _estimate_resource_requirements(
        self,
        action_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Estimate resource requirements for action execution"""
        
        requirements = {
            "cpu_usage": "low",
            "memory_usage": "low",
            "network_required": False,
            "storage_required": False
        }
        
        if action_type == "launch_application":
            requirements.update({
                "cpu_usage": "medium",
                "memory_usage": "medium"
            })
        elif action_type == "get_information":
            requirements.update({
                "network_required": True,
                "cpu_usage": "low"
            })
        
        return requirements
    
    async def _generate_rollback_plan(
        self,
        action_type: str,
        parameters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate rollback plan for critical actions"""
        
        plan = []
        
        if action_type == "launch_application":
            plan.append({
                "step": "terminate",
                "action": "close_application",
                "parameters": {"app_name": parameters["app_name"]}
            })
        
        elif action_type == "configure_system":
            plan.append({
                "step": "restore",
                "action": "restore_previous_setting",
                "parameters": {"setting": parameters["setting"]}
            })
        
        return plan
    
    async def _get_user_profile(self, user_id: Optional[str]) -> UserProfile:
        """Get or create user profile"""
        
        if not user_id:
            user_id = "default"
        
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserProfile(
                user_id=user_id,
                preferences={
                    "response_style": "balanced",
                    "proactivity_level": "medium",
                    "privacy_level": "standard"
                },
                interaction_history=[],
                learning_patterns={},
                adaptation_rate=self.config.get("adaptation_rate", 0.1),
                privacy_settings={
                    "data_collection": True,
                    "personalization": True,
                    "analytics": False
                },
                accessibility_settings={
                    "voice_feedback": True,
                    "visual_aids": False,
                    "high_contrast": False
                }
            )
        
        return self.user_profiles[user_id]
    
    async def _should_use_multimodal(
        self,
        input_data: Union[str, Dict[str, Any]],
        user_profile: UserProfile,
        context: Optional[Dict[str, Any]]
    ) -> bool:
        """Determine if multimodal processing should be used"""
        
        # Always enable if user prefers it
        if user_profile.preferences.get("multimodal_preference", True):
            return True
        
        # Use for complex or ambiguous inputs
        if isinstance(input_data, str):
            complexity_score = len(input_data.split()) / 10.0
            if complexity_score > 1.5:  # Complex input
                return True
        
        return False
    
    async def _adapt_to_user(
        self,
        user_profile: UserProfile,
        intent: ContextualIntent,
        action: EnhancedAction
    ):
        """Adapt system behavior based on user interaction"""
        
        if not self.config.get("learning_enabled", True):
            return
        
        # Update learning patterns
        pattern_key = f"{intent.intent_type.value}_to_{action.action_type}"
        if pattern_key not in user_profile.learning_patterns:
            user_profile.learning_patterns[pattern_key] = {
                "count": 0,
                "success_rate": 0.0,
                "avg_confidence": 0.0
            }
        
        pattern = user_profile.learning_patterns[pattern_key]
        pattern["count"] += 1
        pattern["avg_confidence"] = (
            pattern["avg_confidence"] * (pattern["count"] - 1) + intent.confidence
        ) / pattern["count"]
        
        # Adapt response style based on interaction patterns
        recent_interactions = user_profile.interaction_history[-10:]
        if len(recent_interactions) >= 5:
            avg_confidence = sum(
                interaction.get("confidence", 0.0) 
                for interaction in recent_interactions
            ) / len(recent_interactions)
            
            if avg_confidence > 0.9:
                # User is confident, reduce verbosity
                user_profile.preferences["response_style"] = "concise"
            elif avg_confidence < 0.6:
                # User needs more help, increase detail
                user_profile.preferences["response_style"] = "detailed"
    
    async def _update_interaction_history(
        self,
        user_id: Optional[str],
        input_data: Union[str, Dict[str, Any]],
        intent: ContextualIntent,
        action: EnhancedAction,
        multimodal_context: Optional[MultimodalContext]
    ):
        """Update interaction history"""
        
        interaction = {
            "timestamp": time.time(),
            "user_id": user_id or "default",
            "input": input_data if isinstance(input_data, str) else input_data.get("text", ""),
            "intent": {
                "type": intent.intent_type.value,
                "confidence": intent.confidence,
                "entities": [asdict(e) for e in intent.entities]
            },
            "action": {
                "type": action.action_type,
                "priority": action.priority.value,
                "confidence": action.confidence
            },
            "multimodal": {
                "used": multimodal_context is not None,
                "emotion": multimodal_context.emotion.value if multimodal_context and multimodal_context.emotion else None,
                "attention": multimodal_context.attention_state if multimodal_context else "unknown"
            }
        }
        
        self.interaction_history.append(interaction)
        
        # Limit history size
        max_history = self.config.get("max_history_size", 1000)
        if len(self.interaction_history) > max_history:
            self.interaction_history.pop(0)
        
        # Update user profile
        if user_id:
            user_profile = await self._get_user_profile(user_id)
            user_profile.interaction_history.append(interaction)
            if len(user_profile.interaction_history) > 100:
                user_profile.interaction_history.pop(0)
    
    async def _update_performance_metrics(
        self,
        processing_time: float,
        intent: ContextualIntent,
        action: EnhancedAction
    ):
        """Update performance metrics"""
        
        metrics = {
            "processing_time": processing_time,
            "intent_confidence": intent.confidence,
            "action_confidence": action.confidence,
            "ambiguity_score": intent.ambiguity_score
        }
        
        for key, value in metrics.items():
            if key not in self.performance_metrics:
                self.performance_metrics[key] = []
            self.performance_metrics[key].append(value)
            
            # Keep only last 100 measurements
            if len(self.performance_metrics[key]) > 100:
                self.performance_metrics[key].pop(0)
    
    async def _save_learning_data(self):
        """Save learning data and user profiles"""
        
        try:
            # Save user profiles
            profiles_file = Path("data/user_profiles.json")
            profiles_file.parent.mkdir(parents=True, exist_ok=True)
            
            profiles_data = {
                user_id: asdict(profile) 
                for user_id, profile in self.user_profiles.items()
            }
            
            with open(profiles_file, 'w') as f:
                json.dump(profiles_data, f, indent=2)
            
            # Save interaction history
            history_file = Path("data/interaction_history.json")
            with open(history_file, 'w') as f:
                json.dump(self.interaction_history[-1000:], f, indent=2)  # Save last 1000
            
            self.logger.info("Learning data saved successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to save learning data: {e}")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        
        return {
            "engine_status": {
                "is_running": self.is_running,
                "mode": self.mode.value,
                "total_interactions": len(self.interaction_history),
                "active_users": len(self.user_profiles)
            },
            "performance_metrics": {
                key: {
                    "current": values[-1] if values else 0,
                    "average": sum(values) / len(values) if values else 0,
                    "count": len(values)
                }
                for key, values in self.performance_metrics.items()
            },
            "model_status": self.model_manager.get_system_stats(),
            "multimodal_status": {
                "active": self.multimodal_ai.is_active,
                "correlations": len(self.multimodal_ai.cross_modal_patterns)
            }
        }

# Test the enhanced intent engine
async def test_enhanced_intent_engine():
    """Test the enhanced intent engine"""
    
    engine = EnhancedIntentEngine()
    
    try:
        await engine.start()
        
        # Test various inputs
        test_inputs = [
            "Open Firefox and maximize the window",
            "Find my presentation slides from yesterday",
            "What's the weather like outside?",
            "Help me organize my desktop files",
            "Set up a coding environment for Python development"
        ]
        
        for test_input in test_inputs:
            print(f"\nProcessing: {test_input}")
            
            action, metadata = await engine.process_input(test_input, "test_user")
            
            print(f"Action: {action.action_type}")
            print(f"Confidence: {action.confidence:.2f}")
            print(f"Priority: {action.priority.name}")
            print(f"Processing Time: {metadata['processing_time']:.3f}s")
            print(f"Multimodal Used: {metadata['multimodal_used']}")
            print(f"Execution Steps: {len(action.execution_plan)}")
        
        # Get system status
        status = await engine.get_system_status()
        print(f"\nSystem Status:")
        print(f"Total Interactions: {status['engine_status']['total_interactions']}")
        print(f"Average Processing Time: {status['performance_metrics']['processing_time']['average']:.3f}s")
        
    finally:
        await engine.stop()

if __name__ == "__main__":
    asyncio.run(test_enhanced_intent_engine())