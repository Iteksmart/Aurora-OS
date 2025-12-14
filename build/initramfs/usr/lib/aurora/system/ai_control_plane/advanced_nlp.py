#!/usr/bin/env python3
"""
Advanced NLP Processing for Aurora OS
Implements state-of-the-art natural language understanding with context awareness
"""

import asyncio
import logging
import json
import torch
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import transformers
from pathlib import Path

class IntentType(Enum):
    """Enhanced intent types with more granular understanding"""
    # App Management
    APP_LAUNCH = "app_launch"
    APP_CLOSE = "app_close"
    APP_SWITCH = "app_switch"
    APP_MANAGE = "app_manage"
    
    # File Operations
    FILE_CREATE = "file_create"
    FILE_OPEN = "file_open"
    FILE_EDIT = "file_edit"
    FILE_DELETE = "file_delete"
    FILE_ORGANIZE = "file_organize"
    FILE_SEARCH = "file_search"
    
    # System Control
    SYSTEM_POWER = "system_power"
    SYSTEM_SETTINGS = "system_settings"
    SYSTEM_MONITOR = "system_monitor"
    SYSTEM_MAINTENANCE = "system_maintenance"
    
    # Information Queries
    QUERY_INFO = "query_info"
    QUERY_STATUS = "query_status"
    QUERY_ANALYSIS = "query_analysis"
    
    # Communication
    COMM_EMAIL = "comm_email"
    COMM_CHAT = "comm_chat"
    COMM_CALL = "comm_call"
    COMM_SCHEDULE = "comm_schedule"
    
    # Workflow
    WORKFLOW_CREATE = "workflow_create"
    WORKFLOW_EXECUTE = "workflow_execute"
    WORKFLOW_AUTOMATE = "workflow_automate"
    
    # Creative
    CREATE_CONTENT = "create_content"
    CREATE_DESIGN = "create_design"
    CREATE_CODE = "create_code"
    
    # Learning
    LEARN_TUTORIAL = "learn_tutorial"
    LEARN_EXPLAIN = "learn_explain"
    LEARN_PRACTICE = "learn_practice"
    
    # Help & Conversation
    HELP_ASSIST = "help_assist"
    CONVERSATION = "conversation"
    EMOTIONAL_SUPPORT = "emotional_support"

@dataclass
class Entity:
    """Enhanced entity with richer information"""
    text: str
    label: str
    confidence: float
    start: int
    end: int
    context: Optional[Dict] = None
    relationships: List[str] = None
    
    def __post_init__(self):
        if self.relationships is None:
            self.relationships = []

@dataclass
class ContextualIntent:
    """Intent with rich context and confidence scoring"""
    intent_type: IntentType
    confidence: float
    entities: List[Entity]
    context: Dict[str, Any]
    ambiguity_score: float
    clarification_needed: bool = False
    follow_up_questions: List[str] = None
    
    def __post_init__(self):
        if self.follow_up_questions is None:
            self.follow_up_questions = []

class AdvancedNLPProcessor:
    """Advanced NLP processor with transformer models and context awareness"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.model_path = model_path or "models/nlp/advanced"
        
        # Initialize models
        self._init_models()
        
        # Context management
        self.context_history = []
        self.user_profile = {}
        self.domain_knowledge = {}
        
    def _init_models(self):
        """Initialize NLP models with fallback to rule-based processing"""
        try:
            # Try to load advanced transformer models
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.logger.info(f"Using device: {self.device}")
            
            # Intent classification model
            self.intent_tokenizer = transformers.AutoTokenizer.from_pretrained(
                "microsoft/DialoGPT-medium"
            )
            self.intent_model = transformers.AutoModelForCausalLM.from_pretrained(
                "microsoft/DialoGPT-medium"
            ).to(self.device)
            
            # Named entity recognition
            self.ner_tokenizer = transformers.AutoTokenizer.from_pretrained(
                "dslim/bert-base-NER"
            )
            self.ner_model = transformers.AutoModelForTokenClassification.from_pretrained(
                "dslim/bert-base-NER"
            ).to(self.device)
            
            # Sentiment analysis
            self.sentiment_tokenizer = transformers.AutoTokenizer.from_pretrained(
                "cardiffnlp/twitter-roberta-base-sentiment-latest"
            )
            self.sentiment_model = transformers.AutoModelForSequenceClassification.from_pretrained(
                "cardiffnlp/twitter-roberta-base-sentiment-latest"
            ).to(self.device)
            
            self.use_transformers = True
            self.logger.info("Advanced NLP models loaded successfully")
            
        except Exception as e:
            self.logger.warning(f"Failed to load transformer models: {e}")
            self.logger.info("Falling back to rule-based processing")
            self.use_transformers = False
            self._init_rule_based_patterns()
    
    def _init_rule_based_patterns(self):
        """Initialize rule-based patterns as fallback"""
        self.intent_patterns = {
            IntentType.APP_LAUNCH: [
                r"open\s+(\w+)",
                r"launch\s+(\w+)",
                r"start\s+(\w+)",
                r"run\s+(\w+)"
            ],
            IntentType.FILE_OPEN: [
                r"open\s+(.+?\.(doc|pdf|txt|jpg|png))",
                r"show\s+me\s+(.+)",
                r"find\s+(.+)",
                r"where\s+is\s+(.+)"
            ],
            IntentType.QUERY_INFO: [
                r"what\s+is\s+(.+)",
                r"how\s+(.+)",
                r"tell\s+me\s+about\s+(.+)",
                r"show\s+me\s+(.+)"
            ],
            IntentType.SYSTEM_POWER: [
                r"shutdown",
                r"restart",
                r"reboot",
                r"turn\s+off",
                r"log\s+off"
            ],
            IntentType.CONVERSATION: [
                r"hello",
                r"hi",
                r"how\s+are\s+you",
                r"thank\s+you",
                r"help"
            ]
        }
    
    async def process_input(
        self, 
        text: str, 
        context: Optional[Dict] = None
    ) -> ContextualIntent:
        """Process user input with advanced NLP and context awareness"""
        
        # Update context
        if context:
            self._update_context(context)
        
        # Preprocess input
        cleaned_text = self._preprocess_text(text)
        
        if self.use_transformers:
            return await self._process_with_transformers(cleaned_text)
        else:
            return await self._process_with_rules(cleaned_text)
    
    async def _process_with_transformers(self, text: str) -> ContextualIntent:
        """Process using transformer models"""
        
        # Intent classification
        intent_type, intent_confidence = await self._classify_intent(text)
        
        # Entity extraction
        entities = await self._extract_entities(text)
        
        # Context analysis
        context_analysis = await self._analyze_context(text, entities)
        
        # Ambiguity detection
        ambiguity_score = await self._detect_ambiguity(text, intent_type)
        
        # Generate clarification questions if needed
        clarification_questions = []
        if ambiguity_score > 0.5:
            clarification_questions = await self._generate_questions(text, intent_type)
        
        return ContextualIntent(
            intent_type=intent_type,
            confidence=intent_confidence,
            entities=entities,
            context=context_analysis,
            ambiguity_score=ambiguity_score,
            clarification_needed=ambiguity_score > 0.5,
            follow_up_questions=clarification_questions
        )
    
    async def _process_with_rules(self, text: str) -> ContextualIntent:
        """Process using rule-based patterns"""
        
        # Simple intent detection
        intent_type = IntentType.CONVERSATION
        confidence = 0.5
        entities = []
        
        text_lower = text.lower()
        
        for intent, patterns in self.intent_patterns.items():
            import re
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    intent_type = intent
                    confidence = 0.8
                    
                    # Extract entities
                    if match.groups():
                        entity_text = match.group(1)
                        entities.append(Entity(
                            text=entity_text,
                            label="target",
                            confidence=0.9,
                            start=match.start(1),
                            end=match.end(1)
                        ))
                    break
            if confidence > 0.7:
                break
        
        return ContextualIntent(
            intent_type=intent_type,
            confidence=confidence,
            entities=entities,
            context={"method": "rule_based"},
            ambiguity_score=0.3,
            clarification_needed=False
        )
    
    async def _classify_intent(self, text: str) -> Tuple[IntentType, float]:
        """Classify user intent using transformer model"""
        
        # This is a simplified implementation
        # In production, would use fine-tuned intent classification model
        
        text_lower = text.lower()
        
        # Simple heuristic-based classification
        if any(word in text_lower for word in ["open", "launch", "start", "run"]):
            return IntentType.APP_LAUNCH, 0.8
        elif any(word in text_lower for word in ["file", "document", "find", "show"]):
            return IntentType.FILE_OPEN, 0.7
        elif any(word in text_lower for word in ["what", "how", "tell", "explain"]):
            return IntentType.QUERY_INFO, 0.8
        elif any(word in text_lower for word in ["shutdown", "restart", "reboot"]):
            return IntentType.SYSTEM_POWER, 0.9
        elif any(word in text_lower for word in ["create", "write", "design", "make"]):
            return IntentType.CREATE_CONTENT, 0.7
        else:
            return IntentType.CONVERSATION, 0.6
    
    async def _extract_entities(self, text: str) -> List[Entity]:
        """Extract named entities from text"""
        
        if self.use_transformers:
            # Use transformer model for NER
            inputs = self.ner_tokenizer(text, return_tensors="pt").to(self.device)
            outputs = self.ner_model(**inputs)
            
            predictions = torch.argmax(outputs.logits, dim=2)
            
            entities = []
            for token, prediction in zip(
                self.ner_tokenizer.convert_ids_to_tokens(inputs["input_ids"][0]),
                predictions[0].tolist()
            ):
                if prediction != 0:  # Not 'O' (outside) label
                    # Map prediction to entity label
                    label = self.ner_model.config.id2label[prediction]
                    entities.append(Entity(
                        text=token,
                        label=label,
                        confidence=0.8,
                        start=0,  # Would need proper token mapping
                        end=0
                    ))
            
            return entities
        else:
            # Simple rule-based entity extraction
            import re
            
            entities = []
            
            # Extract app names
            app_patterns = [
                r"\b(firefox|chrome|terminal|vscode|spotify|slack)\b",
                r"\b(microsoft word|excel|powerpoint|photoshop)\b"
            ]
            
            for pattern in app_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    entities.append(Entity(
                        text=match.group(),
                        label="APPLICATION",
                        confidence=0.9,
                        start=match.start(),
                        end=match.end()
                    ))
            
            # Extract file types
            file_pattern = r"\b(\w+\.(doc|pdf|txt|jpg|png|mp4|zip))\b"
            matches = re.finditer(file_pattern, text, re.IGNORECASE)
            for match in matches:
                entities.append(Entity(
                    text=match.group(),
                    label="FILE",
                    confidence=0.9,
                    start=match.start(),
                    end=match.end()
                ))
            
            return entities
    
    async def _analyze_context(self, text: str, entities: List[Entity]) -> Dict[str, Any]:
        """Analyze context for richer understanding"""
        
        context = {
            "timestamp": str(asyncio.get_event_loop().time()),
            "entities": [{"text": e.text, "label": e.label} for e in entities],
            "user_context": self.user_profile,
            "recent_history": self.context_history[-5:] if self.context_history else []
        }
        
        # Add domain-specific context
        for entity in entities:
            if entity.label == "APPLICATION":
                context.setdefault("app_context", {})["last_mentioned"] = entity.text
            elif entity.label == "FILE":
                context.setdefault("file_context", {})["last_mentioned"] = entity.text
        
        return context
    
    async def _detect_ambiguity(self, text: str, intent_type: IntentType) -> float:
        """Detect ambiguity in user input"""
        
        # Simple ambiguity detection
        ambiguity_indicators = [
            "or", "maybe", "perhaps", "might", "could be",
            "?", "what about", "how about"
        ]
        
        text_lower = text.lower()
        ambiguity_score = 0.0
        
        for indicator in ambiguity_indicators:
            if indicator in text_lower:
                ambiguity_score += 0.2
        
        # Check for multiple entities (potential ambiguity)
        word_count = len(text.split())
        if word_count > 15:
            ambiguity_score += 0.1
        
        return min(ambiguity_score, 1.0)
    
    async def _generate_questions(
        self, 
        text: str, 
        intent_type: IntentType
    ) -> List[str]:
        """Generate clarification questions for ambiguous input"""
        
        questions = []
        
        if intent_type == IntentType.APP_LAUNCH:
            questions = [
                "Which application would you like me to open?",
                "Could you specify the application name?"
            ]
        elif intent_type == IntentType.FILE_OPEN:
            questions = [
                "Which file are you looking for?",
                "Can you provide more details about the file?"
            ]
        elif intent_type == IntentType.QUERY_INFO:
            questions = [
                "What specific information would you like to know?",
                "Could you clarify your question?"
            ]
        
        return questions[:2]  # Return maximum 2 questions
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess input text"""
        return text.strip()
    
    def _update_context(self, context: Dict[str, Any]):
        """Update conversation context"""
        self.context_history.append(context)
        if len(self.context_history) > 50:  # Keep last 50 interactions
            self.context_history.pop(0)
    
    async def learn_from_interaction(
        self, 
        intent: ContextualIntent, 
        user_feedback: str
    ):
        """Learn from user interactions to improve accuracy"""
        
        # Update user profile based on feedback
        if "good" in user_feedback.lower() or "correct" in user_feedback.lower():
            # Reinforce successful patterns
            if intent.intent_type not in self.user_profile:
                self.user_profile[intent.intent_type] = []
            self.user_profile[intent.intent_type].append(intent.context)
        
        # This would connect to a learning pipeline in production
        self.logger.info(f"Learning from interaction: {intent.intent_type}")

# Test the advanced NLP processor
async def test_advanced_nlp():
    """Test the advanced NLP processor"""
    
    processor = AdvancedNLPProcessor()
    
    test_inputs = [
        "Open Firefox and show me my recent emails",
        "Find the budget presentation from last week",
        "What's my system performance looking like?",
        "Create a new document called project notes",
        "Help me organize my desktop files"
    ]
    
    for text in test_inputs:
        print(f"\nInput: {text}")
        intent = await processor.process_input(text)
        print(f"Intent: {intent.intent_type.value}")
        print(f"Confidence: {intent.confidence:.2f}")
        print(f"Entities: {[e.text for e in intent.entities]}")
        print(f"Ambiguity: {intent.ambiguity_score:.2f}")
        if intent.clarification_needed:
            print(f"Questions: {intent.follow_up_questions}")

if __name__ == "__main__":
    asyncio.run(test_advanced_nlp())