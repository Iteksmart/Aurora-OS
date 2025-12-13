#!/usr/bin/env python3
"""
Phase 5 Enhancement Tests for Aurora OS
Tests advanced AI capabilities, multimodal processing, and SDK functionality
"""

import asyncio
import logging
import json
import time
import sys
import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
import tempfile
import shutil

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "system" / "ai_control_plane"))
sys.path.insert(0, str(Path(__file__).parent / "sdk"))

# Import Aurora OS components
from advanced_nlp import AdvancedNLPProcessor, ContextualIntent, IntentType
from multimodal_ai import MultimodalAI, ModalityType, EmotionType
from model_manager import ModelManager, ModelType, ModelStatus
from enhanced_intent_engine import EnhancedIntentEngine, IntentEngineMode
from aurora_sdk.core import AuroraApp, AppType, create_app, enable_conversational
from aurora_sdk.ai import AIServices, IntentProcessor

class TestAdvancedNLP(unittest.TestCase):
    """Test advanced NLP processing capabilities"""
    
    def setUp(self):
        self.processor = AdvancedNLPProcessor()
    
    def test_intent_classification(self):
        """Test intent classification accuracy"""
        
        test_cases = [
            ("open firefox", IntentType.APP_LAUNCH),
            ("show my documents", IntentType.FILE_OPEN),
            ("what's the weather", IntentType.QUERY_INFO),
            ("restart computer", IntentType.SYSTEM_POWER)
        ]
        
        for text, expected_intent in test_cases:
            with self.subTest(text=text):
                # This would normally be async, but for testing we'll use sync method
                intent = asyncio.run(self.processor.process_input(text))
                self.assertIsInstance(intent, ContextualIntent)
                self.assertEqual(intent.intent_type, expected_intent)
                self.assertGreater(intent.confidence, 0.5)
    
    def test_entity_extraction(self):
        """Test entity extraction from text"""
        
        test_text = "Open Firefox and find budget_presentation.pdf"
        intent = asyncio.run(self.processor.process_input(test_text))
        
        # Check that entities were extracted
        self.assertGreater(len(intent.entities), 0)
        
        # Look for application entity
        app_entities = [e for e in intent.entities if e.label == "APPLICATION"]
        self.assertGreater(len(app_entities), 0)
        
        # Look for file entity
        file_entities = [e for e in intent.entities if e.label == "FILE"]
        self.assertGreater(len(file_entities), 0)
    
    def test_context_awareness(self):
        """Test context-aware processing"""
        
        context = {"recent_files": ["budget.pdf", "report.docx"]}
        intent = asyncio.run(self.processor.process_input("open the budget", context))
        
        # Should have context information
        self.assertIn("context", intent.__dict__.keys())
        self.assertIsNotNone(intent.context)
    
    def test_ambiguity_detection(self):
        """Test ambiguity detection in user input"""
        
        ambiguous_inputs = [
            "open or close the file",
            "maybe start the application",
            "what about the settings?"
        ]
        
        for text in ambiguous_inputs:
            with self.subTest(text=text):
                intent = asyncio.run(self.processor.process_input(text))
                # Ambiguous inputs should have higher ambiguity scores
                self.assertGreater(intent.ambiguity_score, 0.3)

class TestMultimodalAI(unittest.TestCase):
    """Test multimodal AI processing"""
    
    def setUp(self):
        self.multimodal_ai = MultimodalAI()
    
    def test_voice_processing(self):
        """Test voice input processing"""
        
        # Test voice processor initialization
        self.assertIsNotNone(self.multimodal_ai.voice_processor)
        self.assertIsNotNone(self.multimodal_ai.vision_processor)
        self.assertIsNotNone(self.multimodal_ai.gesture_processor)
    
    def test_emotion_detection(self):
        """Test emotion detection from voice"""
        
        # Create mock audio data
        mock_audio_data = b"mock_audio_data"
        emotion = self.multimodal_ai.voice_processor._detect_emotion(mock_audio_data)
        
        # Should return an emotion type
        self.assertIsInstance(emotion, EmotionType)
        self.assertIsNotNone(emotion)
    
    def test_vision_processing(self):
        """Test vision processing capabilities"""
        
        # Create a mock frame
        import numpy as np
        mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Process frame
        modality_input = self.multimodal_ai.vision_processor._process_frame(mock_frame)
        
        # Should return valid modality input
        self.assertEqual(modality_input.modality, ModalityType.VISION)
        self.assertIn("faces", modality_input.data)
        self.assertIn("attention", modality_input.data)
    
    def test_cross_modal_correlation(self):
        """Test correlation between different modalities"""
        
        from multimodal_ai import ModalityInput
        
        # Create mock inputs
        voice_input = ModalityInput(
            modality=ModalityType.VOICE,
            data={"text": "open firefox"},
            confidence=0.9,
            timestamp=time.time(),
            metadata={}
        )
        
        vision_input = ModalityInput(
            modality=ModalityType.VISION,
            data={"attention": "focused"},
            confidence=0.8,
            timestamp=time.time() + 0.1,
            metadata={}
        )
        
        # Test correlation
        correlations = self.multimodal_ai._compute_cross_modal_correlations([
            voice_input, vision_input
        ])
        
        # Should have correlation data
        self.assertGreater(len(correlations), 0)

class TestModelManager(unittest.TestCase):
    """Test AI model management system"""
    
    def setUp(self):
        # Create temporary directory for models
        self.temp_dir = tempfile.mkdtemp()
        self.model_manager = ModelManager(self.temp_dir)
    
    def tearDown(self):
        # Clean up temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_model_registration(self):
        """Test model registration"""
        
        # Create a mock model file
        model_file = Path(self.temp_dir) / "test_model.model"
        model_file.write_text("mock model data")
        
        # Register model
        success = asyncio.run(self.model_manager.register_model(
            name="test_model",
            version="1.0.0",
            model_type=ModelType.NLP_INTENT,
            model_path=str(model_file)
        ))
        
        self.assertTrue(success)
        
        # Check that model is in registry
        model_info = self.model_manager.get_model_info("test_model", "1.0.0")
        self.assertIsNotNone(model_info)
        self.assertEqual(model_info["name"], "test_model")
        self.assertEqual(model_info["version"], "1.0.0")
    
    def test_model_loading(self):
        """Test model loading and caching"""
        
        # Create and register a model
        model_file = Path(self.temp_dir) / "test_model.model"
        model_file.write_text("mock model data")
        
        asyncio.run(self.model_manager.register_model(
            name="test_model",
            version="1.0.0",
            model_type=ModelType.NLP_INTENT,
            model_path=str(model_file)
        ))
        
        # Load model
        model = asyncio.run(self.model_manager.load_model("test_model", "1.0.0"))
        
        # Should return some model object
        self.assertIsNotNone(model)
        
        # Check system stats
        stats = self.model_manager.get_system_stats()
        self.assertGreater(stats["total_models"], 0)
    
    def test_model_caching(self):
        """Test model caching functionality"""
        
        # Create and register a model
        model_file = Path(self.temp_dir) / "cache_test.model"
        model_file.write_text("mock model data")
        
        asyncio.run(self.model_manager.register_model(
            name="cache_test",
            version="1.0.0",
            model_type=ModelType.NLP_INTENT,
            model_path=str(model_file)
        ))
        
        # Load model twice
        model1 = asyncio.run(self.model_manager.load_model("cache_test", "1.0.0"))
        model2 = asyncio.run(self.model_manager.load_model("cache_test", "1.0.0"))
        
        # Both should be the same object (cached)
        self.assertIs(model1, model2)
    
    def test_performance_tracking(self):
        """Test performance metric tracking"""
        
        # Update performance metrics
        asyncio.run(self.model_manager.update_model_performance(
            name="test_model",
            version="1.0.0",
            metrics={"accuracy": 0.95, "inference_time": 0.1}
        ))
        
        # Check that metrics were recorded
        model_info = self.model_manager.get_model_info("test_model", "1.0.0")
        if model_info:  # Only check if model exists
            self.assertIn("performance_metrics", model_info)

class TestEnhancedIntentEngine(unittest.TestCase):
    """Test enhanced AI intent engine"""
    
    def setUp(self):
        self.intent_engine = EnhancedIntentEngine()
    
    def test_engine_initialization(self):
        """Test intent engine initialization"""
        
        # Should initialize without errors
        self.assertIsNotNone(self.intent_engine.nlp_processor)
        self.assertIsNotNone(self.intent_engine.multimodal_ai)
        self.assertIsNotNone(self.intent_engine.model_manager)
    
    def test_adaptive_mode_processing(self):
        """Test adaptive processing mode"""
        
        self.intent_engine.mode = IntentEngineMode.ADAPTIVE
        
        # Test input processing
        action, metadata = asyncio.run(self.intent_engine.process_input(
            "open firefox",
            user_id="test_user"
        ))
        
        # Should return valid action and metadata
        self.assertIsNotNone(action)
        self.assertIsNotNone(metadata)
        self.assertIn("processing_time", metadata)
        self.assertIn("intent_confidence", metadata)
    
    def test_multimodal_mode_processing(self):
        """Test multimodal processing mode"""
        
        self.intent_engine.mode = IntentEngineMode.MULTIMODAL
        
        # Test input processing
        action, metadata = asyncio.run(self.intent_engine.process_input(
            {"text": "open firefox", "voice_data": b"mock"},
            user_id="test_user"
        ))
        
        # Should indicate multimodal usage
        self.assertTrue(metadata.get("multimodal_used", False))
    
    def test_user_adaptation(self):
        """Test user learning and adaptation"""
        
        # Process multiple interactions for the same user
        for i in range(5):
            asyncio.run(self.intent_engine.process_input(
                f"open firefox {i}",
                user_id="adaptive_user"
            ))
        
        # Check user profile was created and adapted
        user_profile = asyncio.run(self.intent_engine._get_user_profile("adaptive_user"))
        self.assertIsNotNone(user_profile)
        self.assertGreater(len(user_profile.interaction_history), 0)
    
    def test_system_status(self):
        """Test system status reporting"""
        
        status = asyncio.run(self.intent_engine.get_system_status())
        
        # Should contain comprehensive status information
        self.assertIn("engine_status", status)
        self.assertIn("performance_metrics", status)
        self.assertIn("model_status", status)
        self.assertIn("multimodal_status", status)

class TestAuroraSDK(unittest.TestCase):
    """Test Aurora OS SDK functionality"""
    
    def setUp(self):
        self.app = create_app(
            app_id="test_app",
            name="Test Application",
            version="1.0.0",
            app_type=AppType.PRODUCTIVITY,
            description="A test application for Aurora OS"
        )
    
    def test_app_creation(self):
        """Test application creation and configuration"""
        
        # Check basic properties
        self.assertEqual(self.app.app_id, "test_app")
        self.assertEqual(self.app.name, "Test Application")
        self.assertEqual(self.app.app_type, AppType.PRODUCTIVITY)
        
        # Check default configuration
        self.assertIn("auto_save", self.app.config)
        self.assertTrue(self.app.config["auto_save"])
    
    def test_capability_enabling(self):
        """Test capability enabling functions"""
        
        # Enable conversational capability
        enable_conversational(self.app)
        self.assertTrue(self.app.capabilities["conversational"])
        self.assertTrue(self.app.permissions["microphone_access"])
    
    def test_context_management(self):
        """Test context creation and management"""
        
        # Create context
        context = asyncio.run(self.app.create_context(
            data={"project": "test_project", "files": ["file1.txt", "file2.txt"]},
            scope=ContextScope.APPLICATION
        ))
        
        # Check context properties
        self.assertIsNotNone(context.context_id)
        self.assertEqual(context.app_id, "test_app")
        self.assertEqual(context.scope, ContextScope.APPLICATION)
        
        # Retrieve context
        retrieved_context = asyncio.run(self.app.get_context(context.context_id))
        self.assertIsNotNone(retrieved_context)
        self.assertEqual(retrieved_context.context_id, context.context_id)
    
    def test_intent_processing(self):
        """Test intent processing"""
        
        from aurora_sdk.core import AuroraIntent
        
        # Create test intent
        intent = AuroraIntent(
            intent_id="test_intent",
            intent_type="launch",
            confidence=0.9,
            parameters={"app_name": "test_app"},
            source_app="system",
            timestamp=time.time()
        )
        
        # Process intent
        result = asyncio.run(self.app.process_intent(intent))
        
        # Should return successful result
        self.assertTrue(result.get("success", False))
    
    def test_app_manifest(self):
        """Test application manifest generation"""
        
        manifest = self.app.get_manifest()
        
        # Should contain required manifest fields
        self.assertIn("app_id", manifest)
        self.assertIn("name", manifest)
        self.assertIn("version", manifest)
        self.assertIn("capabilities", manifest)
        self.assertIn("permissions", manifest)
        self.assertEqual(manifest["app_id"], "test_app")
    
    def test_ai_services_integration(self):
        """Test AI services integration"""
        
        # Initialize AI services
        ai_services = AIServices("test_app")
        
        # Test intent processing
        intent = asyncio.run(ai_services.process_intent("open the application"))
        self.assertIsNotNone(intent)
        
        # Test sentiment analysis
        sentiment = asyncio.run(ai_services.analyze_sentiment("I love this app!"))
        self.assertIn("sentiment", sentiment)
        
        # Test entity extraction
        entities = asyncio.run(ai_services.extract_entities("Contact me at test@example.com"))
        self.assertGreater(len(entities), 0)

class TestPhase5Integration(unittest.TestCase):
    """Integration tests for Phase 5 enhancements"""
    
    def test_end_to_end_ai_processing(self):
        """Test complete AI processing pipeline"""
        
        # Initialize enhanced intent engine
        engine = EnhancedIntentEngine()
        
        # Process complex input
        action, metadata = asyncio.run(engine.process_input(
            "Open Firefox and navigate to aurora-os.org",
            user_id="integration_test_user",
            context={"current_app": "terminal", "time_of_day": "morning"}
        ))
        
        # Validate complete processing
        self.assertIsNotNone(action)
        self.assertIsNotNone(metadata)
        self.assertGreater(action.confidence, 0.5)
        self.assertLess(metadata["processing_time"], 5.0)
    
    def test_multimodal_context_integration(self):
        """Test multimodal context integration"""
        
        # Test that multimodal data enhances intent processing
        multimodal_ai = MultimodalAI()
        
        # Simulate multimodal context
        from multimodal_ai import ModalityInput, ModalityType, EmotionType
        
        voice_input = ModalityInput(
            modality=ModalityType.VOICE,
            data={"text": "open file", "emotion": EmotionType.FOCUSED},
            confidence=0.9,
            timestamp=time.time(),
            metadata={}
        )
        
        # Test correlation with context
        context = asyncio.run(multimodal_ai._correlate_modalities([voice_input]))
        
        self.assertIsNotNone(context)
        self.assertEqual(context.primary_intent, "open file")
    
    def test_sdk_ai_integration(self):
        """Test SDK integration with AI services"""
        
        # Create app with AI capabilities
        app = create_app(
            app_id="ai_integration_test",
            name="AI Integration Test",
            version="1.0.0",
            app_type=AppType.PRODUCTIVITY
        )
        
        enable_conversational(app)
        
        # Initialize AI services
        ai_services = AIServices("ai_integration_test")
        
        # Test intent processing through SDK
        intent = asyncio.run(ai_services.process_intent("help me organize my files"))
        
        # Process intent through app
        from aurora_sdk.core import AuroraIntent
        
        app_intent = AuroraIntent(
            intent_id=intent.intent_id,
            intent_type=intent.intent_type.value,
            confidence=intent.confidence,
            parameters=intent.parameters,
            source_app="ai_integration_test",
            timestamp=time.time()
        )
        
        result = asyncio.run(app.process_intent(app_intent))
        
        self.assertTrue(result.get("success", False))

def run_phase5_tests():
    """Run all Phase 5 enhancement tests"""
    
    print("🚀 Running Aurora OS Phase 5 Enhancement Tests")
    print("=" * 60)
    
    # Create test suite
    test_classes = [
        TestAdvancedNLP,
        TestMultimodalAI,
        TestModelManager,
        TestEnhancedIntentEngine,
        TestAuroraSDK,
        TestPhase5Integration
    ]
    
    suite = unittest.TestSuite()
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("🧪 Phase 5 Enhancement Test Results:")
    print(f"   Tests Run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\n💥 Errors:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback.split('Exception:')[-1].strip()}")
    
    if result.wasSuccessful():
        print("\n✅ All Phase 5 enhancement tests passed!")
        return True
    else:
        print("\n❌ Some Phase 5 enhancement tests failed!")
        return False

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Run tests
    success = run_phase5_tests()
    sys.exit(0 if success else 1)