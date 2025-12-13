"""
AI Services Module for Aurora OS SDK
Provides AI capabilities integration for third-party applications
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid

from .core import AuroraContext, AuroraIntent, ContextScope

class AIServiceType(Enum):
    """Types of AI services available"""
    INTENT_PROCESSING = "intent_processing"
    CONTEXT_MANAGEMENT = "context_management"
    PREDICTIVE_ANALYTICS = "predictive_analytics"
    NATURAL_LANGUAGE = "natural_language"
    VOICE_RECOGNITION = "voice_recognition"
    IMAGE_RECOGNITION = "image_recognition"
    RECOMMENDATION = "recommendation"
    ANOMALY_DETECTION = "anomaly_detection"

class IntentType(Enum):
    """Standard intent types"""
    LAUNCH = "launch"
    CONFIGURE = "configure"
    QUERY = "query"
    ACTION = "action"
    CREATE = "create"
    DELETE = "delete"
    MODIFY = "modify"
    SEARCH = "search"
    NAVIGATE = "navigate"
    COMMUNICATE = "communicate"

@dataclass
class AIRequest:
    """Request to AI service"""
    request_id: str
    service_type: AIServiceType
    parameters: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    timeout: float = 30.0
    priority: int = 1
    timestamp: float = field(default_factory=time.time)

@dataclass
class AIResponse:
    """Response from AI service"""
    request_id: str
    success: bool
    data: Any
    confidence: float
    processing_time: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class IntentProcessor:
    """Intent processing service for applications"""
    
    def __init__(self, app_id: str):
        self.app_id = app_id
        self.logger = logging.getLogger(f"aurora.ai.{app_id}.intent")
        self.custom_intents: Dict[str, Callable] = {}
        self.intent_patterns: Dict[str, List[str]] = {}
        self.training_data: List[Dict] = []
    
    def register_intent(
        self,
        intent_name: str,
        handler: Callable,
        patterns: Optional[List[str]] = None
    ):
        """Register a custom intent handler"""
        self.custom_intents[intent_name] = handler
        if patterns:
            self.intent_patterns[intent_name] = patterns
        self.logger.info(f"Registered custom intent: {intent_name}")
    
    async def process_text(self, text: str) -> AuroraIntent:
        """Process text to extract intent"""
        
        # This would connect to Aurora OS AI control plane
        # For now, provide a simplified implementation
        
        intent = AuroraIntent(
            intent_id=str(uuid.uuid4()),
            intent_type="custom",
            confidence=0.8,
            parameters={"text": text},
            source_app=self.app_id,
            timestamp=time.time()
        )
        
        # Try to match against custom intents
        for intent_name, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern.lower() in text.lower():
                    intent.intent_type = intent_name
                    intent.parameters["matched_pattern"] = pattern
                    intent.confidence = 0.9
                    break
        
        return intent
    
    async def train_intent(
        self,
        text: str,
        intent_type: str,
        entities: Optional[Dict[str, Any]] = None
    ):
        """Train the intent processor with examples"""
        
        training_example = {
            "text": text,
            "intent_type": intent_type,
            "entities": entities or {},
            "timestamp": time.time()
        }
        
        self.training_data.append(training_example)
        
        # In a real implementation, this would train the AI model
        self.logger.info(f"Added training example for intent: {intent_type}")
    
    def get_training_data(self) -> List[Dict]:
        """Get training data for export/analysis"""
        return self.training_data.copy()

class ContextManager:
    """Context management service for applications"""
    
    def __init__(self, app_id: str):
        self.app_id = app_id
        self.logger = logging.getLogger(f"aurora.ai.{app_id}.context")
        self.context_subscriptions: Dict[str, List[Callable]] = {}
        self.shared_contexts: Dict[str, AuroraContext] = {}
    
    async def share_context(self, context: AuroraContext):
        """Share context with other applications"""
        
        if context.scope in [ContextScope.SYSTEM, ContextScope.CLOUD]:
            self.shared_contexts[context.context_id] = context
            
            # Notify subscribers
            if context.context_id in self.context_subscriptions:
                for callback in self.context_subscriptions[context.context_id]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(context)
                        else:
                            callback(context)
                    except Exception as e:
                        self.logger.error(f"Context callback error: {e}")
            
            # In a real implementation, this would share with Aurora OS MCP system
            self.logger.info(f"Shared context: {context.context_id}")
    
    def subscribe_to_context(
        self,
        context_id: str,
        callback: Callable
    ):
        """Subscribe to context updates"""
        if context_id not in self.context_subscriptions:
            self.context_subscriptions[context_id] = []
        self.context_subscriptions[context_id].append(callback)
    
    def unsubscribe_from_context(
        self,
        context_id: str,
        callback: Callable
    ):
        """Unsubscribe from context updates"""
        if context_id in self.context_subscriptions:
            try:
                self.context_subscriptions[context_id].remove(callback)
                if not self.context_subscriptions[context_id]:
                    del self.context_subscriptions[context_id]
            except ValueError:
                pass
    
    async def find_related_contexts(
        self,
        query: Dict[str, Any],
        limit: int = 10
    ) -> List[AuroraContext]:
        """Find contexts related to the query"""
        
        related_contexts = []
        
        # Simple matching based on data overlap
        for context in self.shared_contexts.values():
            match_score = 0
            
            for key, value in query.items():
                if key in context.data and context.data[key] == value:
                    match_score += 1
            
            if match_score > 0:
                related_contexts.append((context, match_score))
        
        # Sort by match score and return top results
        related_contexts.sort(key=lambda x: x[1], reverse=True)
        return [ctx for ctx, _ in related_contexts[:limit]]

class PredictiveAnalytics:
    """Predictive analytics service for applications"""
    
    def __init__(self, app_id: str):
        self.app_id = app_id
        self.logger = logging.getLogger(f"aurora.ai.{app_id}.predictive")
        self.user_patterns: Dict[str, List[Dict]] = {}
        self.predictions: Dict[str, Dict] = {}
    
    async def record_action(
        self,
        user_id: str,
        action: str,
        context: Dict[str, Any],
        timestamp: Optional[float] = None
    ):
        """Record user action for pattern learning"""
        
        if timestamp is None:
            timestamp = time.time()
        
        action_record = {
            "action": action,
            "context": context,
            "timestamp": timestamp
        }
        
        if user_id not in self.user_patterns:
            self.user_patterns[user_id] = []
        
        self.user_patterns[user_id].append(action_record)
        
        # Keep only recent actions (last 1000)
        if len(self.user_patterns[user_id]) > 1000:
            self.user_patterns[user_id] = self.user_patterns[user_id][-1000:]
        
        # Update predictions
        await self._update_predictions(user_id)
    
    async def predict_next_action(
        self,
        user_id: str,
        current_context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Predict user's next action based on patterns"""
        
        if user_id not in self.user_patterns:
            return None
        
        user_actions = self.user_patterns[user_id]
        if len(user_actions) < 5:
            return None
        
        # Simple pattern matching based on context similarity
        predictions = []
        
        for i, action_record in enumerate(user_actions[:-1]):
            next_action = user_actions[i + 1]
            
            # Calculate context similarity
            similarity = self._calculate_context_similarity(
                action_record["context"],
                current_context
            )
            
            if similarity > 0.5:
                predictions.append({
                    "action": next_action["action"],
                    "confidence": similarity,
                    "context": next_action["context"]
                })
        
        if not predictions:
            return None
        
        # Return highest confidence prediction
        predictions.sort(key=lambda x: x["confidence"], reverse=True)
        return predictions[0]
    
    def _calculate_context_similarity(
        self,
        context1: Dict[str, Any],
        context2: Dict[str, Any]
    ) -> float:
        """Calculate similarity between two contexts"""
        
        common_keys = set(context1.keys()) & set(context2.keys())
        if not common_keys:
            return 0.0
        
        matches = 0
        for key in common_keys:
            if context1[key] == context2[key]:
                matches += 1
        
        return matches / len(common_keys)
    
    async def _update_predictions(self, user_id: str):
        """Update internal prediction models"""
        # In a real implementation, this would train ML models
        pass

class NaturalLanguageProcessor:
    """Natural language processing service"""
    
    def __init__(self, app_id: str):
        self.app_id = app_id
        self.logger = logging.getLogger(f"aurora.ai.{app_id}.nlp")
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text"""
        
        # Simple sentiment analysis
        positive_words = ["good", "great", "excellent", "amazing", "love", "wonderful"]
        negative_words = ["bad", "terrible", "awful", "hate", "worst", "horrible"]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            sentiment = "positive"
            confidence = min(0.9, 0.5 + (positive_count - negative_count) * 0.1)
        elif negative_count > positive_count:
            sentiment = "negative"
            confidence = min(0.9, 0.5 + (negative_count - positive_count) * 0.1)
        else:
            sentiment = "neutral"
            confidence = 0.5
        
        return {
            "sentiment": sentiment,
            "confidence": confidence,
            "positive_score": positive_count,
            "negative_score": negative_count
        }
    
    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities from text"""
        
        # Simple entity extraction using patterns
        entities = []
        
        # Extract emails
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for match in re.finditer(email_pattern, text):
            entities.append({
                "text": match.group(),
                "type": "email",
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.9
            })
        
        # Extract URLs
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        for match in re.finditer(url_pattern, text):
            entities.append({
                "text": match.group(),
                "type": "url",
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.9
            })
        
        # Extract numbers
        number_pattern = r'\b\d+(?:\.\d+)?\b'
        for match in re.finditer(number_pattern, text):
            entities.append({
                "text": match.group(),
                "type": "number",
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.8
            })
        
        return entities
    
    async def generate_summary(self, text: str, max_length: int = 100) -> str:
        """Generate summary of text"""
        
        sentences = text.split('.')
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= 2:
            return text[:max_length]
        
        # Simple extractive summarization - take first sentence
        summary = sentences[0]
        if len(summary) > max_length:
            summary = summary[:max_length - 3] + "..."
        
        return summary

class AIServices:
    """Main AI services coordinator for applications"""
    
    def __init__(self, app_id: str):
        self.app_id = app_id
        self.logger = logging.getLogger(f"aurora.ai.{app_id}")
        
        # Initialize service components
        self.intent_processor = IntentProcessor(app_id)
        self.context_manager = ContextManager(app_id)
        self.predictive_analytics = PredictiveAnalytics(app_id)
        self.nlp_processor = NaturalLanguageProcessor(app_id)
        
        # Service availability
        self.services_available = {
            AIServiceType.INTENT_PROCESSING: True,
            AIServiceType.CONTEXT_MANAGEMENT: True,
            AIServiceType.PREDICTIVE_ANALYTICS: True,
            AIServiceType.NATURAL_LANGUAGE: True,
            AIServiceType.VOICE_RECOGNITION: False,
            AIServiceType.IMAGE_RECOGNITION: False,
            AIServiceType.RECOMMENDATION: False,
            AIServiceType.ANOMALY_DETECTION: False
        }
        
        # Request queue
        self.request_queue: List[AIRequest] = []
        self.processing = False
    
    async def initialize(self):
        """Initialize AI services"""
        self.logger.info("AI services initialized")
    
    async def shutdown(self):
        """Shutdown AI services"""
        self.logger.info("AI services shutdown")
    
    def is_service_available(self, service_type: AIServiceType) -> bool:
        """Check if a service is available"""
        return self.services_available.get(service_type, False)
    
    async def request(
        self,
        service_type: AIServiceType,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> AIResponse:
        """Make a request to an AI service"""
        
        if not self.is_service_available(service_type):
            return AIResponse(
                request_id=str(uuid.uuid4()),
                success=False,
                data=None,
                confidence=0.0,
                processing_time=0.0,
                error=f"Service {service_type.value} not available"
            )
        
        request = AIRequest(
            request_id=str(uuid.uuid4()),
            service_type=service_type,
            parameters=parameters,
            context=context,
            timeout=timeout
        )
        
        start_time = time.time()
        
        try:
            result = await self._process_request(request)
            processing_time = time.time() - start_time
            
            return AIResponse(
                request_id=request.request_id,
                success=True,
                data=result,
                confidence=0.8,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            return AIResponse(
                request_id=request.request_id,
                success=False,
                data=None,
                confidence=0.0,
                processing_time=processing_time,
                error=str(e)
            )
    
    async def _process_request(self, request: AIRequest) -> Any:
        """Process an AI service request"""
        
        if request.service_type == AIServiceType.INTENT_PROCESSING:
            text = request.parameters.get("text", "")
            return await self.intent_processor.process_text(text)
        
        elif request.service_type == AIServiceType.NATURAL_LANGUAGE:
            operation = request.parameters.get("operation")
            text = request.parameters.get("text", "")
            
            if operation == "sentiment":
                return await self.nlp_processor.analyze_sentiment(text)
            elif operation == "entities":
                return await self.nlp_processor.extract_entities(text)
            elif operation == "summary":
                max_length = request.parameters.get("max_length", 100)
                return await self.nlp_processor.generate_summary(text, max_length)
        
        elif request.service_type == AIServiceType.PREDICTIVE_ANALYTICS:
            operation = request.parameters.get("operation")
            
            if operation == "record_action":
                user_id = request.parameters.get("user_id", "default")
                action = request.parameters.get("action")
                context = request.parameters.get("context", {})
                await self.predictive_analytics.record_action(user_id, action, context)
                return {"status": "recorded"}
            
            elif operation == "predict_next":
                user_id = request.parameters.get("user_id", "default")
                current_context = request.parameters.get("context", {})
                return await self.predictive_analytics.predict_next_action(user_id, current_context)
        
        # Default response
        return {"status": "unknown_operation"}
    
    # Convenience methods
    async def process_intent(self, text: str) -> AuroraIntent:
        """Convenience method for intent processing"""
        response = await self.request(
            AIServiceType.INTENT_PROCESSING,
            {"text": text}
        )
        return response.data if response.success else None
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Convenience method for sentiment analysis"""
        response = await self.request(
            AIServiceType.NATURAL_LANGUAGE,
            {"operation": "sentiment", "text": text}
        )
        return response.data if response.success else {}
    
    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Convenience method for entity extraction"""
        response = await self.request(
            AIServiceType.NATURAL_LANGUAGE,
            {"operation": "entities", "text": text}
        )
        return response.data if response.success else []
    
    async def share_context(self, context: AuroraContext):
        """Convenience method for context sharing"""
        await self.context_manager.share_context(context)
    
    async def predict_next_action(
        self,
        user_id: str,
        current_context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Convenience method for action prediction"""
        response = await self.request(
            AIServiceType.PREDICTIVE_ANALYTICS,
            {
                "operation": "predict_next",
                "user_id": user_id,
                "context": current_context
            }
        )
        return response.data if response.success else None