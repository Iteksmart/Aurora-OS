#!/usr/bin/env python3
"""
Simple Phase 5 Enhancement Tests for Aurora OS
Tests core functionality without heavy ML dependencies
"""

import asyncio
import sys
import time
from pathlib import Path

# Test basic file structure and imports
def test_file_structure():
    """Test that all Phase 5 files were created"""
    
    print("🔍 Testing file structure...")
    
    required_files = [
        "system/ai_control_plane/advanced_nlp.py",
        "system/ai_control_plane/multimodal_ai.py", 
        "system/ai_control_plane/model_manager.py",
        "system/ai_control_plane/enhanced_intent_engine.py",
        "sdk/aurora_sdk/__init__.py",
        "sdk/aurora_sdk/core.py",
        "sdk/aurora_sdk/ai.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files created successfully")
        return True

def test_sdk_imports():
    """Test that SDK modules can be imported"""
    
    print("🔍 Testing SDK imports...")
    
    try:
        # Add SDK to path
        sys.path.insert(0, str(Path("sdk")))
        
        # Test core import
        from aurora_sdk.core import AuroraApp, AppType, create_app
        print("✅ Core SDK module imports successfully")
        
        # Test basic app creation
        app = create_app(
            app_id="test_app",
            name="Test App",
            version="1.0.0",
            app_type=AppType.PRODUCTIVITY
        )
        print("✅ Aurora app creation works")
        
        # Test AI services import
        from aurora_sdk.ai import AIServices
        print("✅ AI services module imports successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ SDK import failed: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality of created components"""
    
    print("🔍 Testing basic functionality...")
    
    try:
        # Test app basic operations
        sys.path.insert(0, str(Path("sdk")))
        from aurora_sdk.core import AuroraApp, AppType, ContextScope, create_app
        
        app = create_app(
            app_id="basic_test",
            name="Basic Test",
            version="1.0.0",
            app_type=AppType.UTILITY
        )
        
        # Test context creation
        async def test_context():
            context = await app.create_context(
                data={"test": "data"},
                scope=ContextScope.PRIVATE
            )
            
            # Test context retrieval
            retrieved = await app.get_context(context.context_id)
            return retrieved is not None
        
        # Run async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        context_works = loop.run_until_complete(test_context())
        loop.close()
        
        if context_works:
            print("✅ Context management works")
        else:
            print("❌ Context management failed")
            return False
        
        # Test manifest generation
        manifest = app.get_manifest()
        if "app_id" in manifest and manifest["app_id"] == "basic_test":
            print("✅ App manifest generation works")
        else:
            print("❌ App manifest generation failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def test_code_quality():
    """Test code quality and structure"""
    
    print("🔍 Testing code quality...")
    
    try:
        # Check that main classes exist in files
        files_to_check = {
            "system/ai_control_plane/advanced_nlp.py": ["AdvancedNLPProcessor"],
            "system/ai_control_plane/multimodal_ai.py": ["MultimodalAI"],
            "system/ai_control_plane/model_manager.py": ["ModelManager"],
            "system/ai_control_plane/enhanced_intent_engine.py": ["EnhancedIntentEngine"],
            "sdk/aurora_sdk/core.py": ["AuroraApp"],
            "sdk/aurora_sdk/ai.py": ["AIServices"]
        }
        
        for file_path, expected_classes in files_to_check.items():
            with open(file_path, 'r') as f:
                content = f.read()
                
                for class_name in expected_classes:
                    if f"class {class_name}" not in content:
                        print(f"❌ Class {class_name} not found in {file_path}")
                        return False
        
        print("✅ All expected classes found")
        return True
        
    except Exception as e:
        print(f"❌ Code quality test failed: {e}")
        return False

def test_documentation():
    """Test that documentation exists"""
    
    print("🔍 Testing documentation...")
    
    try:
        # Check for docstrings in main classes
        files_to_check = [
            "sdk/aurora_sdk/core.py",
            "system/ai_control_plane/enhanced_intent_engine.py"
        ]
        
        for file_path in files_to_check:
            with open(file_path, 'r') as f:
                content = f.read()
                
                # Check for documentation
                if '"""' not in content:
                    print(f"❌ No docstrings found in {file_path}")
                    return False
        
        print("✅ Documentation found in key files")
        return True
        
    except Exception as e:
        print(f"❌ Documentation test failed: {e}")
        return False

def run_all_tests():
    """Run all Phase 5 tests"""
    
    print("🚀 Running Aurora OS Phase 5 Simple Tests")
    print("=" * 50)
    
    tests = [
        ("File Structure", test_file_structure),
        ("SDK Imports", test_sdk_imports), 
        ("Basic Functionality", test_basic_functionality),
        ("Code Quality", test_code_quality),
        ("Documentation", test_documentation)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} Test:")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} test failed")
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"   Passed: {passed}/{total}")
    print(f"   Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n✅ All Phase 5 simple tests passed!")
        return True
    else:
        print(f"\n⚠️  {total-passed} tests failed")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)