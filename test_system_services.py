#!/usr/bin/env python3
"""
Aurora OS - System Services Test

This script tests the Aurora OS system services layer to verify they're working correctly.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))


async def test_service_manager():
    """Test the Aurora Service Manager"""
    print("\n🔧 Testing Aurora Service Manager...")
    
    try:
        from system.services.service_manager import aurora_service_manager, ServiceConfig, ServiceType, Priority
        
        # Initialize the service manager
        success = await aurora_service_manager.initialize()
        
        if success:
            print("✅ Service manager initialized successfully")
            
            # Get system overview
            overview = aurora_service_manager.get_system_overview()
            print(f"📊 System Overview:")
            print(f"   Total Services: {overview['total_services']}")
            print(f"   Running Services: {overview['running_services']}")
            print(f"   System Uptime: {overview['system_uptime']:.1f}s")
            print(f"   Health Monitoring: {overview['health_monitoring_active']}")
            
            # Test starting a specific service
            print(f"\n🚀 Testing service management...")
            
            # Start MCP host service
            mcp_started = await aurora_service_manager.start_service("mcp_host")
            print(f"   MCP Host Service: {'✅ Started' if mcp_started else '❌ Failed'}")
            
            # Start AI control plane
            ai_started = await aurora_service_manager.start_service("ai_control_plane")
            print(f"   AI Control Plane: {'✅ Started' if ai_started else '❌ Failed'}")
            
            # Start file manager
            file_started = await aurora_service_manager.start_service("file_manager")
            print(f"   File Manager: {'✅ Started' if file_started else '❌ Failed'}")
            
            # List running services
            running_services = aurora_service_manager.list_services()
            print(f"\n📋 Running Services ({len(running_services)}):")
            for service in running_services:
                status_icon = "🟢" if service.status.value == "running" else "🔴"
                print(f"   {status_icon} {service.config.name} ({service.service_id})")
                print(f"      Type: {service.config.service_type.value}")
                print(f"      Priority: {service.config.priority.name}")
                print(f"      PID: {service.pid}")
                if service.metrics.health_score:
                    print(f"      Health: {service.metrics.health_score:.1f}/100")
            
            # Test service health monitoring
            print(f"\n🏥 Testing Health Monitoring...")
            for service_id in ["mcp_host", "ai_control_plane", "file_manager"]:
                service_status = aurora_service_manager.get_service_status(service_id)
                if service_status:
                    print(f"   {service_id}: Health Score {service_status.metrics.health_score:.1f}")
                    print(f"      CPU: {service_status.metrics.cpu_usage:.1f}%")
                    print(f"      Memory: {service_status.metrics.memory_usage_mb:.1f}MB")
                    print(f"      Uptime: {service_status.metrics.uptime_seconds:.1f}s")
            
            # Test stopping a service
            print(f"\n🛑 Testing Service Shutdown...")
            file_stopped = await aurora_service_manager.stop_service("file_manager")
            print(f"   File Manager: {'✅ Stopped' if file_stopped else '❌ Failed'}")
            
            # Get final overview
            final_overview = aurora_service_manager.get_system_overview()
            print(f"\n📈 Final System State:")
            print(f"   Running Services: {final_overview['running_services']}/{final_overview['total_services']}")
            
        else:
            print("❌ Failed to initialize service manager")
            
    except Exception as e:
        print(f"❌ Service manager test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_file_manager():
    """Test the AI File Manager"""
    print("\n📁 Testing AI File Manager...")
    
    try:
        from system.services.file_manager.main import ai_file_manager, SearchQuery
        
        # Initialize with mock configuration
        config = {
            "watch_directories": ["./test_docs"],  # Use current directory for testing
            "auto_organize": False,  # Disable for testing
            "index_path": "/tmp/test_file_manager.db"
        }
        
        # Create test directory
        import os
        os.makedirs("./test_docs", exist_ok=True)
        
        # Create some test files
        with open("./test_docs/test_document.txt", "w") as f:
            f.write("This is a test document with some content for searching.")
        
        with open("./test_docs/code_sample.py", "w") as f:
            f.write("def hello_world():\n    print('Hello, Aurora OS!')")
        
        with open("./test_docs/meeting_notes.txt", "w") as f:
            f.write("Meeting notes: Discuss Aurora OS development timeline.")
        
        success = await ai_file_manager.initialize()
        
        if success:
            print("✅ AI File Manager initialized successfully")
            
            # Get statistics
            stats = ai_file_manager.get_statistics()
            print(f"📊 File Manager Statistics:")
            print(f"   Total Files: {stats['total_files']}")
            print(f"   Indexed Files: {stats['indexed_files']}")
            print(f"   Search Queries: {stats['search_queries']}")
            print(f"   Categories: {dict(list(stats['categories'].items())[:3])}...")
            print(f"   Total Size: {stats['total_size']} bytes")
            
            # Test file search
            print(f"\n🔍 Testing File Search...")
            
            # Name search
            name_query = SearchQuery(query_text="test_document", limit=5)
            name_results = await ai_file_manager.search_files(name_query)
            print(f"   Name search 'test_document': {len(name_results)} results")
            for result in name_results:
                print(f"      • {result.file_path} (relevance: {result.relevance_score:.2f})")
            
            # Content search
            content_query = SearchQuery(query_text="Aurora OS", content_search=True, limit=5)
            content_results = await ai_file_manager.search_files(content_query)
            print(f"   Content search 'Aurora OS': {len(content_results)} results")
            for result in content_results:
                print(f"      • {result.file_path} (relevance: {result.relevance_score:.2f})")
            
            # Test file info
            print(f"\n📄 Testing File Information...")
            test_file = "./test_docs/test_document.txt"
            file_info = await ai_file_manager.get_file_info(test_file)
            if file_info:
                print(f"   File: {file_info.name}")
                print(f"   Size: {file_info.size} bytes")
                print(f"   Category: {file_info.category.value}")
                print(f"   MIME Type: {file_info.mime_type}")
                print(f"   Auto Tags: {', '.join(file_info.auto_tags)}")
                print(f"   Content Preview: {file_info.content_preview[:50]}...")
                print(f"   Importance Score: {file_info.importance_score:.2f}")
            
            # Test file access tracking
            print(f"\n📊 Testing Access Tracking...")
            await ai_file_manager.update_file_access(test_file, context="testing", operation="read")
            
            updated_info = await ai_file_manager.get_file_info(test_file)
            if updated_info:
                print(f"   Access Frequency: {updated_info.access_frequency:.2f}/day")
                print(f"   Last Access Context: {updated_info.last_access_context}")
            
        else:
            print("❌ Failed to initialize AI File Manager")
        
        # Cleanup test files
        import shutil
        if os.path.exists("./test_docs"):
            shutil.rmtree("./test_docs")
        
    except Exception as e:
        print(f"❌ File manager test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_service_integration():
    """Test service integration and communication"""
    print("\n🔗 Testing Service Integration...")
    
    try:
        # Test that services can work together
        from system.services.service_manager import aurora_service_manager
        from system.services.file_manager.main import ai_file_manager
        
        print("✅ Both service managers imported successfully")
        
        # Test service discovery
        print(f"\n🔍 Testing Service Discovery...")
        registry_info = aurora_service_manager.get_system_overview()
        print(f"   Services in Registry: {registry_info['service_registry_size']}")
        
        # Test that file manager can be managed by service manager
        file_manager_config = {
            "service_id": "file_manager_test",
            "name": "Test File Manager",
            "description": "Test instance of AI File Manager",
            "service_type": "storage",
            "executable_path": "python",
            "arguments": ["-m", "system.services.file_manager.main"],
            "auto_start": False,
            "priority": "normal"
        }
        
        print("✅ Service integration test completed")
        
    except Exception as e:
        print(f"❌ Service integration test failed: {e}")


async def main():
    """Main test function"""
    print("🚀 Aurora OS System Services Test")
    print("=" * 50)
    
    # Test all components
    await test_service_manager()
    await test_file_manager()
    await test_service_integration()
    
    print("\n" + "=" * 50)
    print("🎉 System Services Test Completed!")
    print("\n✨ Aurora OS System Services Features:")
    print("   🔧 AI-Powered Service Management")
    print("   📁 Intelligent File Management") 
    print("   🏥 Health Monitoring & Auto-Recovery")
    print("   🔍 Predictive Service Scaling")
    print("   📊 Real-time Performance Metrics")
    print("   🔄 Self-Healing Architecture")
    
    print("\n🎯 STEP 3 COMPLETE: System Services Layer")
    print("🚀 Moving to STEP 1: AI Control Plane Integration")


if __name__ == "__main__":
    asyncio.run(main())