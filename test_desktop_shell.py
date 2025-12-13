#!/usr/bin/env python3
"""
Aurora OS - Desktop Shell Test

This script tests the Aurora desktop shell components to verify they're working correctly.
"""

import asyncio
import sys
import time
import logging
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_conversational_palette():
    """Test the conversational palette"""
    print("\n🎨 Testing Conversational Palette...")
    
    try:
        from desktop.aurora_shell.apps.conversational_palette.main import aurora_conversational_palette
        
        # Initialize the palette
        success = await aurora_conversational_palette.initialize()
        
        if success:
            print("✅ Conversational palette initialized successfully")
            
            # Start conversation
            await aurora_conversational_palette.start_conversation()
            print("✅ Conversation session started")
            
            # Test some inputs
            test_inputs = [
                "open firefox",
                "what's my battery level?",
                "help me with something",
                "find my documents"
            ]
            
            for user_input in test_inputs:
                print(f"\n👤 User: {user_input}")
                turn = await aurora_conversational_palette.process_input(user_input)
                print(f"🤖 Aurora: {turn.response}")
                print(f"   Intent: {turn.intent} (confidence: {turn.confidence:.2f})")
                if turn.actions_taken:
                    print(f"   Actions: {', '.join(turn.actions_taken)}")
            
            # Get session stats
            stats = aurora_conversational_palette.get_session_stats()
            print(f"\n📊 Session Stats:")
            print(f"   Interactions: {stats['interaction_count']}")
            print(f"   Success Rate: {stats['success_rate']:.1f}%")
            print(f"   Avg Response Time: {stats['avg_response_time']:.3f}s")
            
            # Test suggestions
            suggestions = aurora_conversational_palette.get_current_suggestions()
            if suggestions:
                print(f"\n💡 Suggestions:")
                for suggestion in suggestions[:3]:
                    print(f"   • {suggestion.title}: {suggestion.description}")
            
            # End conversation
            await aurora_conversational_palette.end_conversation()
            print("\n✅ Conversation session ended")
            
        else:
            print("❌ Failed to initialize conversational palette")
            
    except Exception as e:
        print(f"❌ Conversational palette test failed: {e}")


async def test_compositor():
    """Test the Aurora compositor"""
    print("\n🖼️ Testing Aurora Compositor...")
    
    try:
        from desktop.aurora_shell.core.compositor import aurora_compositor
        
        # Initialize the compositor
        success = await aurora_compositor.initialize()
        
        if success:
            print("✅ Aurora compositor initialized successfully")
            print(f"   Render mode: {aurora_compositor.render_mode.value}")
            print(f"   Display: {aurora_compositor.display_width}x{aurora_compositor.display_height}")
            print(f"   Refresh rate: {aurora_compositor.refresh_rate}Hz")
            print(f"   Layers: {len(aurora_compositor.render_layers)}")
            
            # Create some test windows
            window1 = aurora_compositor.create_window(
                "test_window_1", "Firefox", "firefox", 
                100, 100, 800, 600
            )
            window2 = aurora_compositor.create_window(
                "test_window_2", "Terminal", "terminal",
                200, 200, 600, 400
            )
            
            print(f"✅ Created {len(aurora_compositor.window_surfaces)} test windows")
            
            # Focus a window
            aurora_compositor.focus_window("test_window_1")
            print("✅ Focused test window")
            
            # Get performance metrics
            metrics = aurora_compositor.get_performance_metrics()
            print(f"📊 Performance Metrics:")
            print(f"   FPS: {metrics.fps:.1f}")
            print(f"   Frame Time: {metrics.frame_time_ms:.2f}ms")
            print(f"   Draw Calls: {metrics.draw_calls}")
            
            # Cleanup test windows
            aurora_compositor.destroy_window("test_window_1")
            aurora_compositor.destroy_window("test_window_2")
            print("✅ Cleaned up test windows")
            
        else:
            print("❌ Failed to initialize Aurora compositor")
            
    except Exception as e:
        print(f"❌ Compositor test failed: {e}")


async def test_ui_prediction_engine():
    """Test the UI prediction engine"""
    print("\n🧠 Testing UI Prediction Engine...")
    
    try:
        from desktop.aurora_shell.ai.prediction_engine import UIPredictionEngine
        
        # Create prediction engine
        predictor = UIPredictionEngine()
        
        # Initialize
        success = await predictor.initialize()
        
        if success:
            print("✅ UI prediction engine initialized successfully")
            print(f"   Usage patterns: {len(predictor.usage_patterns)}")
            print(f"   ML available: {predictor.model is not None}")
            
            # Test window usage prediction
            mock_windows = [
                type('MockWindow', (), {'app_id': 'firefox'}),
                type('MockWindow', (), {'app_id': 'terminal'})
            ]
            
            predictions = await predictor.predict_window_usage(mock_windows)
            print(f"✅ Window usage predictions: {len(predictions)} apps")
            for app_id, probability in predictions.items():
                print(f"   • {app_id}: {probability:.2f}")
            
            # Test general predictions
            await predictor.update_predictions(1.0, {"mock": "windows"})
            
            current_predictions = predictor.get_predictions()
            print(f"✅ Current predictions: {len(current_predictions)}")
            for pred in current_predictions[:3]:
                print(f"   • {pred.target_id}: {pred.probability:.2f} ({pred.prediction_type.value})")
            
            # Record some user actions
            predictor.record_user_action("open_firefox", {"app_id": "firefox", "context": "work"})
            predictor.record_user_action("open_terminal", {"app_id": "terminal", "context": "development"})
            
            # Get updated patterns
            patterns = predictor.get_usage_patterns()
            print(f"✅ Updated usage patterns: {len(patterns)}")
            
        else:
            print("❌ Failed to initialize UI prediction engine")
            
    except Exception as e:
        print(f"❌ UI prediction engine test failed: {e}")


async def main():
    """Main test function"""
    print("🚀 Aurora OS Desktop Shell Test")
    print("=" * 50)
    
    # Test all components
    await test_ui_prediction_engine()
    await test_conversational_palette()
    await test_compositor()
    
    print("\n" + "=" * 50)
    print("🎉 Desktop Shell Test Completed!")
    print("\n✨ Aurora OS Desktop Shell Features:")
    print("   🎨 Conversational AI Interface")
    print("   🖼️ Hardware-Accelerated Compositor") 
    print("   🧠 Predictive UI Engine")
    print("   ⚡ Adaptive Performance")
    print("   🔄 Real-time Optimization")
    print("\n🎯 Next: Implementing System Services Layer")


if __name__ == "__main__":
    asyncio.run(main())