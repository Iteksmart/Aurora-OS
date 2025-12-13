"""
Test suite for Aurora OS Intent Engine
Tests natural language understanding and intent processing
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

from system.ai_control_plane.intent_engine import (
    IntentEngine, IntentType, ActionType, Entity, NLUCore, 
    EntityExtractor, IntentClassifier, ActionPlanner
)

class TestNLUCore:
    """Test the Natural Language Understanding Core"""
    
    @pytest.fixture
    def nlu_core(self):
        """Create NLU Core instance for testing"""
        return NLUCore()
    
    @pytest.mark.asyncio
    async def test_process_simple_command(self, nlu_core):
        """Test processing a simple command"""
        text = "open firefox"
        context = {"user_id": "test_user"}
        
        result = await nlu_core.process(text, context)
        
        assert result['text'] == text
        assert 'normalized_text' in result
        assert 'tokens' in result
        assert 'entities' in result
        assert 'action_info' in result
        assert 'context_info' in result
        assert 'confidence' in result
        assert result['confidence'] > 0
    
    @pytest.mark.asyncio
    async def test_process_complex_command(self, nlu_core):
        """Test processing a complex command with entities"""
        text = "open my document report.pdf from the desktop"
        context = {"user_id": "test_user"}
        
        result = await nlu_core.process(text, context)
        
        # Should extract file entity
        entities = result['entities']
        file_entities = [e for e in entities if e['entity_type'] == 'file']
        assert len(file_entities) > 0
        assert any('report.pdf' in e['value'] for e in file_entities)
    
    @pytest.mark.asyncio
    async def test_normalize_text(self, nlu_core):
        """Test text normalization"""
        text = "  OPEN   Firefox!!!  "
        normalized = nlu_core._normalize_text(text)
        
        assert normalized == "open firefox"
    
    def test_tokenize(self, nlu_core):
        """Test tokenization"""
        text = "open firefox browser"
        tokens = nlu_core._tokenize(text)
        
        assert tokens == ["open", "firefox", "browser"]
    
    def test_identify_action(self, nlu_core):
        """Test action identification"""
        text = "open firefox"
        tokens = ["open", "firefox"]
        
        action_info = nlu_core._identify_action(text, tokens)
        
        assert action_info['action_type'] == 'launch'
        assert action_info['score'] > 0

class TestEntityExtractor:
    """Test the Entity Extractor"""
    
    @pytest.fixture
    def entity_extractor(self):
        """Create Entity Extractor instance"""
        return EntityExtractor()
    
    @pytest.mark.asyncio
    async def test_extract_file_entity(self, entity_extractor):
        """Test file entity extraction"""
        nlu_result = {
            'entities': [
                {
                    'entity_type': 'file',
                    'value': 'report.pdf',
                    'confidence': 0.9,
                    'start_pos': 10,
                    'end_pos': 19
                }
            ]
        }
        
        entities = await entity_extractor.extract(nlu_result, {})
        
        assert len(entities) == 1
        entity = entities[0]
        assert entity.entity_type == 'file'
        assert entity.value == 'report.pdf'
        assert entity.confidence == 0.9

class TestIntentClassifier:
    """Test the Intent Classifier"""
    
    @pytest.fixture
    def intent_classifier(self):
        """Create Intent Classifier instance"""
        return IntentClassifier()
    
    @pytest.mark.asyncio
    async def test_classify_launch_intent(self, intent_classifier):
        """Test classification of launch intent"""
        nlu_result = {'action_info': {'action_type': 'launch'}}
        entities = [Entity('application', 'firefox', 0.9, 0, 7)]
        context = {}
        
        intent_type, action_type = await intent_classifier.classify(
            nlu_result, entities, context
        )
        
        assert intent_type == IntentType.IMMEDIATE_ACTION
        assert action_type == ActionType.LAUNCH_APPLICATION
    
    @pytest.mark.asyncio
    async def test_classify_search_intent(self, intent_classifier):
        """Test classification of search intent"""
        nlu_result = {'action_info': {'action_type': 'search'}}
        entities = []
        context = {}
        
        intent_type, action_type = await intent_classifier.classify(
            nlu_result, entities, context
        )
        
        assert intent_type == IntentType.INFORMATION_QUERY
        assert action_type == ActionType.SEARCH

class TestActionPlanner:
    """Test the Action Planner"""
    
    @pytest.fixture
    def action_planner(self):
        """Create Action Planner instance"""
        return ActionPlanner()
    
    @pytest.mark.asyncio
    async def test_plan_launch_action(self, action_planner):
        """Test planning a launch action"""
        intent = Intent(
            intent_type=IntentType.IMMEDIATE_ACTION,
            action_type=ActionType.LAUNCH_APPLICATION,
            primary_action="launch",
            entities=[Entity('application', 'firefox', 0.9, 0, 7)],
            confidence=0.8,
            context={},
            parameters={},
            timestamp=time.time(),
            original_input="open firefox"
        )
        
        plan = await action_planner.plan_actions(intent)
        
        assert plan['action_type'] == ActionType.LAUNCH_APPLICATION
        assert 'steps' in plan
        assert 'rollback_steps' in plan
        assert 'estimated_time' in plan
        assert len(plan['steps']) > 0
    
    @pytest.mark.asyncio
    async def test_customize_step(self, action_planner):
        """Test step customization with entities"""
        intent = Intent(
            intent_type=IntentType.IMMEDIATE_ACTION,
            action_type=ActionType.LAUNCH_APPLICATION,
            primary_action="launch",
            entities=[Entity('application', 'firefox', 0.9, 0, 7)],
            confidence=0.8,
            context={},
            parameters={},
            timestamp=time.time(),
            original_input="open firefox"
        )
        
        step = action_planner._customize_step("verify_application_exists", intent)
        
        assert 'application_name' in step['parameters']
        assert step['parameters']['application_name'] == 'firefox'

class TestIntentEngine:
    """Test the main Intent Engine"""
    
    @pytest.fixture
    def intent_engine(self):
        """Create Intent Engine instance"""
        engine = IntentEngine()
        engine.context_manager = AsyncMock()
        engine.ambiguity_resolver = AsyncMock()
        return engine
    
    @pytest.mark.asyncio
    async def test_process_simple_intent(self, intent_engine):
        """Test processing a simple intent"""
        user_input = "open firefox"
        context = {"user_id": "test_user"}
        
        intent = await intent_engine.process_intent(user_input, context)
        
        assert intent.original_input == user_input
        assert intent.intent_type in IntentType
        assert intent.action_type in ActionType
        assert intent.confidence >= 0
        assert isinstance(intent.entities, list)
    
    @pytest.mark.asyncio
    async def test_process_intent_with_entities(self, intent_engine):
        """Test processing intent with entities"""
        user_input = "open my document report.pdf"
        context = {"user_id": "test_user"}
        
        intent = await intent_engine.process_intent(user_input, context)
        
        # Should extract file entity
        file_entities = [e for e in intent.entities if e.entity_type == 'file']
        assert len(file_entities) > 0
    
    @pytest.mark.asyncio
    async def test_low_confidence_ambiguity_resolution(self, intent_engine):
        """Test ambiguity resolution for low confidence intents"""
        user_input = "do something"
        context = {"user_id": "test_user"}
        
        # Mock ambiguity resolver to return a resolved intent
        resolved_intent = Intent(
            intent_type=IntentType.UNKNOWN,
            action_type=ActionType.GET_INFO,
            primary_action="unknown",
            entities=[],
            confidence=0.3,
            context=context,
            parameters={},
            timestamp=time.time(),
            original_input=user_input
        )
        intent_engine.ambiguity_resolver.resolve.return_value = resolved_intent
        
        intent = await intent_engine.process_intent(user_input, context)
        
        # Should call ambiguity resolver
        intent_engine.ambiguity_resolver.resolve.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_handling(self, intent_engine):
        """Test error handling in intent processing"""
        user_input = "test input"
        context = {"user_id": "test_user"}
        
        # Mock NLU core to raise exception
        with patch.object(intent_engine.nlu_core, 'process', side_effect=Exception("Test error")):
            intent = await intent_engine.process_intent(user_input, context)
            
            # Should return fallback intent
            assert intent.intent_type == IntentType.UNKNOWN
            assert intent.confidence == 0.0
    
    def test_metrics_update(self, intent_engine):
        """Test metrics updating"""
        # Initial metrics
        initial_metrics = intent_engine.get_metrics()
        assert initial_metrics['total_processed'] == 0
        
        # Update with successful classification
        intent = Intent(
            intent_type=IntentType.IMMEDIATE_ACTION,
            action_type=ActionType.LAUNCH_APPLICATION,
            primary_action="launch",
            entities=[],
            confidence=0.8,
            context={},
            parameters={},
            timestamp=time.time(),
            original_input="test"
        )
        
        intent_engine._update_metrics(intent, 0.1)
        
        updated_metrics = intent_engine.get_metrics()
        assert updated_metrics['total_processed'] == 1
        assert updated_metrics['successful_classifications'] == 1
        assert updated_metrics['average_confidence'] > 0
    
    @pytest.mark.asyncio
    async def test_start_stop(self, intent_engine):
        """Test starting and stopping the intent engine"""
        await intent_engine.start()
        # Should start without errors
        
        await intent_engine.stop()
        # Should stop without errors

class TestIntentEngineIntegration:
    """Integration tests for Intent Engine"""
    
    @pytest.fixture
    def intent_engine(self):
        """Create fully configured Intent Engine"""
        return IntentEngine()
    
    @pytest.mark.asyncio
    async def test_end_to_end_processing(self, intent_engine):
        """Test complete end-to-end intent processing"""
        test_cases = [
            {
                'input': "open firefox",
                'expected_intent': IntentType.IMMEDIATE_ACTION,
                'expected_action': ActionType.LAUNCH_APPLICATION
            },
            {
                'input': "find my documents",
                'expected_intent': IntentType.INFORMATION_QUERY,
                'expected_action': ActionType.SEARCH
            },
            {
                'input': "set brightness to 80%",
                'expected_intent': IntentType.CONFIGURATION_TASK,
                'expected_action': ActionType.SET_SETTING
            },
            {
                'input': "help me fix my wifi",
                'expected_intent': IntentType.PROBLEM_RESOLUTION,
                'expected_action': ActionType.FIX_PROBLEM
            }
        ]
        
        await intent_engine.start()
        
        for test_case in test_cases:
            intent = await intent_engine.process_intent(
                test_case['input'], 
                {"user_id": "test_user"}
            )
            
            assert intent.intent_type == test_case['expected_intent']
            assert intent.action_type == test_case['expected_action']
            assert intent.confidence > 0
        
        await intent_engine.stop()
    
    @pytest.mark.asyncio
    async def test_context_aware_processing(self, intent_engine):
        """Test context-aware intent processing"""
        user_input = "open project files"
        
        # Test with work context
        work_context = {"user_id": "test_user", "context_type": "work"}
        intent = await intent_engine.process_intent(user_input, work_context)
        
        assert intent.context['context_type'] == 'work'
        
        # Test with personal context
        personal_context = {"user_id": "test_user", "context_type": "personal"}
        intent = await intent_engine.process_intent(user_input, personal_context)
        
        assert intent.context['context_type'] == 'personal'
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, intent_engine):
        """Test performance metrics collection"""
        await intent_engine.start()
        
        # Process multiple intents
        for i in range(10):
            await intent_engine.process_intent(
                f"open file {i}.txt", 
                {"user_id": "test_user"}
            )
        
        metrics = intent_engine.get_metrics()
        assert metrics['total_processed'] == 10
        assert metrics['successful_classifications'] > 0
        assert metrics['average_confidence'] > 0
        assert metrics['average_processing_time'] > 0
        
        await intent_engine.stop()

class TestIntentEngineEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture
    def intent_engine(self):
        """Create Intent Engine instance"""
        return IntentEngine()
    
    @pytest.mark.asyncio
    async def test_empty_input(self, intent_engine):
        """Test processing empty input"""
        intent = await intent_engine.process_intent("", {"user_id": "test_user"})
        
        assert intent.intent_type == IntentType.UNKNOWN
        assert intent.original_input == ""
    
    @pytest.mark.asyncio
    async def test_very_long_input(self, intent_engine):
        """Test processing very long input"""
        long_input = "open " + "very " * 1000 + "long file"
        
        intent = await intent_engine.process_intent(long_input, {"user_id": "test_user"})
        
        # Should not crash and should process some intent
        assert intent is not None
        assert intent.original_input == long_input
    
    @pytest.mark.asyncio
    async def test_special_characters(self, intent_engine):
        """Test processing input with special characters"""
        special_input = "open file@#$%^&*().txt"
        
        intent = await intent_engine.process_intent(special_input, {"user_id": "test_user"})
        
        # Should handle special characters gracefully
        assert intent is not None
        assert intent.original_input == special_input
    
    @pytest.mark.asyncio
    async def test_unicode_input(self, intent_engine):
        """Test processing Unicode input"""
        unicode_input = "ouvrir fichier français 🦊"
        
        intent = await intent_engine.process_intent(unicode_input, {"user_id": "test_user"})
        
        # Should handle Unicode gracefully
        assert intent is not None
        assert intent.original_input == unicode_input
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, intent_engine):
        """Test concurrent intent processing"""
        await intent_engine.start()
        
        inputs = [
            f"open file {i}.txt" 
            for i in range(50)
        ]
        
        # Process multiple intents concurrently
        tasks = [
            intent_engine.process_intent(input_text, {"user_id": "test_user"})
            for input_text in inputs
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should complete successfully
        assert len(results) == len(inputs)
        for intent in results:
            assert intent is not None
        
        await intent_engine.stop()

if __name__ == "__main__":
    pytest.main([__file__])