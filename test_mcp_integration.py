#!/usr/bin/env python3
"""
Aurora OS - MCP Integration Test Script

This script tests the integration of all MCP context providers and the provider manager,
verifying that the Aurora OS nervous system is working correctly.
"""

import asyncio
import sys
import time
import json
import logging
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from mcp.provider_manager import MCPProviderManager
from mcp.system.mcp_host import MCPContext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_provider_initialization():
    """Test provider initialization"""
    print("\n🚀 Testing Provider Initialization...")
    
    # Create provider manager with test configuration
    config = {
        'cache_ttl': 60,
        'providers': {
            'filesystem': {
                'monitored_paths': ['./'],  # Monitor current directory
                'max_files_cached': 100,
                'update_interval': 5
            },
            'system': {
                'update_interval': 2,
                'track_processes': True,
                'enable_predictions': True
            },
            'security': {
                'update_interval': 5,
                'enable_real_time': True,
                'auto_response': False  # Disable for testing
            }
        }
    }
    
    manager = MCPProviderManager(config)
    
    # Test initialization
    success = await manager.initialize()
    
    if success:
        print("✅ Provider manager initialized successfully")
        
        # Check provider status
        status = await manager.get_provider_status()
        print(f"✅ Initialized {len(status['providers'])} providers:")
        
        for name, provider_status in status['providers'].items():
            health_icon = "🟢" if provider_status['healthy'] else "🔴"
            enabled_icon = "✅" if provider_status['enabled'] else "❌"
            print(f"  {health_icon} {enabled_icon} {name}: {len(provider_status['capabilities'])} capabilities")
        
        return manager
    else:
        print("❌ Failed to initialize provider manager")
        return None


async def test_individual_providers(manager):
    """Test individual provider functionality"""
    print("\n🔍 Testing Individual Providers...")
    
    # Test filesystem provider
    print("\n📁 Testing Filesystem Provider...")
    try:
        fs_request = {
            'type': 'overview',
            'detailed': False
        }
        
        fs_response = await manager.get_context({
            'providers': ['filesystem'],
            'type': 'overview'
        })
        
        if 'filesystem' in fs_response.provider_responses:
            fs_data = fs_response.provider_responses['filesystem'].data
            print(f"✅ Filesystem provider responding")
            print(f"   - Cache size: {fs_data.get('cache_status', {}).get('total_files', 0)} files")
            print(f"   - Monitored paths: {len(fs_data.get('monitored_paths', []))}")
        else:
            print("❌ Filesystem provider not responding")
            
    except Exception as e:
        print(f"❌ Filesystem provider error: {e}")
    
    # Test system provider
    print("\n💻 Testing System Provider...")
    try:
        system_response = await manager.get_context({
            'providers': ['system'],
            'type': 'overview',
            'detailed': True
        })
        
        if 'system' in system_response.provider_responses:
            system_data = system_response.provider_responses['system'].data
            print(f"✅ System provider responding")
            print(f"   - CPU Usage: {system_data.get('cpu_usage', 0):.1f}%")
            print(f"   - Memory Usage: {system_data.get('memory_usage', 0):.1f}%")
            print(f"   - Process Count: {system_data.get('process_count', 0)}")
            print(f"   - Health Score: {system_data.get('health_score', 0):.1f}")
        else:
            print("❌ System provider not responding")
            
    except Exception as e:
        print(f"❌ System provider error: {e}")
    
    # Test security provider
    print("\n🔒 Testing Security Provider...")
    try:
        security_response = await manager.get_context({
            'providers': ['security'],
            'type': 'overview'
        })
        
        if 'security' in security_response.provider_responses:
            security_data = security_response.provider_responses['security'].data
            print(f"✅ Security provider responding")
            print(f"   - Monitoring Active: {security_data.get('current_status', {}).get('monitoring_active', False)}")
            print(f"   - Total Events: {security_data.get('current_status', {}).get('total_events', 0)}")
            print(f"   - Active Threats: {security_data.get('current_status', {}).get('active_threats', 0)}")
        else:
            print("❌ Security provider not responding")
            
    except Exception as e:
        print(f"❌ Security provider error: {e}")


async def test_context_correlation(manager):
    """Test context correlation across providers"""
    print("\n🔗 Testing Context Correlation...")
    
    try:
        # Request context from all providers
        all_response = await manager.get_context({
            'providers': ['filesystem', 'system', 'security'],
            'type': 'overview',
            'detailed': True
        })
        
        print(f"✅ Aggregated context from {len(all_response.provider_responses)} providers")
        print(f"   - Processing Time: {all_response.processing_time_ms:.2f}ms")
        print(f"   - Confidence Score: {all_response.confidence_score:.1f}%")
        
        # Check correlated insights
        insights = all_response.correlated_insights
        
        if 'system_security_correlation' in insights:
            correlation = insights['system_security_correlation']
            if correlation and 'error' not in correlation:
                print(f"✅ System-Security correlation active")
            else:
                print(f"ℹ️  System-Security correlation: {correlation.get('error', 'no correlation data')}")
        
        if 'performance_analysis' in insights:
            perf = insights['performance_analysis']
            if 'avg_response_time_ms' in perf:
                print(f"✅ Performance analysis: {perf['avg_response_time_ms']:.2f}ms avg response")
        
        if 'anomaly_detection' in insights:
            anomalies = insights['anomaly_detection']
            anomaly_count = len([k for k in anomalies.keys() if k != 'detection_error'])
            print(f"✅ Anomaly detection: {anomaly_count} anomalies found")
        
        if 'recommendations' in insights:
            recommendations = insights['recommendations']
            print(f"✅ Generated {len(recommendations)} recommendations")
            for rec in recommendations[:3]:  # Show first 3
                print(f"   - {rec}")
        
    except Exception as e:
        print(f"❌ Context correlation error: {e}")


async def test_provider_health(manager):
    """Test provider health monitoring"""
    print("\n🏥 Testing Provider Health Monitoring...")
    
    try:
        # Get provider status
        status = await manager.get_provider_status()
        
        print("📊 Provider Health Status:")
        for name, provider_status in status['providers'].items():
            health = "🟢 Healthy" if provider_status['healthy'] else "🔴 Unhealthy"
            enabled = "✅" if provider_status['enabled'] else "❌"
            response_time = provider_status['response_time_ms']
            error_count = provider_status['error_count']
            
            print(f"   {enabled} {name}: {health} ({response_time:.2f}ms, {error_count} errors)")
        
        # Manager statistics
        manager_stats = status['manager_stats']
        print(f"\n📈 Manager Statistics:")
        print(f"   - Uptime: {manager_stats['uptime_seconds']:.1f}s")
        print(f"   - Total Requests: {manager_stats['total_requests']}")
        print(f"   - Error Count: {manager_stats['error_count']}")
        print(f"   - Avg Response Time: {manager_stats['avg_response_time_ms']:.2f}ms")
        print(f"   - Cache Size: {manager_stats['cache_size']}")
        
    except Exception as e:
        print(f"❌ Health monitoring error: {e}")


async def test_caching_performance(manager):
    """Test caching performance"""
    print("\n⚡ Testing Caching Performance...")
    
    try:
        # First request (should miss cache)
        start_time = time.time()
        response1 = await manager.get_context({
            'providers': ['system'],
            'type': 'overview'
        })
        first_request_time = time.time() - start_time
        
        # Second request (should hit cache)
        start_time = time.time()
        response2 = await manager.get_context({
            'providers': ['system'],
            'type': 'overview'
        })
        second_request_time = time.time() - start_time
        
        print(f"📊 Cache Performance:")
        print(f"   - First request: {first_request_time*1000:.2f}ms")
        print(f"   - Second request: {second_request_time*1000:.2f}ms")
        
        if second_request_time < first_request_time:
            speedup = (first_request_time - second_request_time) / first_request_time * 100
            print(f"   - Cache speedup: {speedup:.1f}% faster ✅")
        else:
            print("   - Cache may not be working optimally ⚠️")
        
    except Exception as e:
        print(f"❌ Caching test error: {e}")


async def test_error_handling(manager):
    """Test error handling and recovery"""
    print("\n🛡️  Testing Error Handling...")
    
    try:
        # Test with non-existent provider
        error_response = await manager.get_context({
            'providers': ['nonexistent_provider'],
            'type': 'overview'
        })
        
        if error_response.confidence_score == 0.0:
            print("✅ Error handling: Gracefully handles non-existent providers")
        
        # Test with invalid request
        invalid_response = await manager.get_context({
            'providers': ['system'],
            'type': 'invalid_type'
        })
        
        # Should still get some response
        if invalid_response.provider_responses or invalid_response.correlated_insights:
            print("✅ Error handling: Gracefully handles invalid request types")
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")


async def cleanup_test(manager):
    """Clean up test resources"""
    print("\n🧹 Cleaning Up Test Resources...")
    
    try:
        await manager.cleanup()
        print("✅ All resources cleaned up successfully")
    except Exception as e:
        print(f"❌ Cleanup error: {e}")


async def main():
    """Main test function"""
    print("🌟 Aurora OS MCP Integration Test")
    print("=" * 50)
    
    manager = None
    
    try:
        # Run tests
        manager = await test_provider_initialization()
        
        if manager:
            await test_individual_providers(manager)
            await test_context_correlation(manager)
            await test_provider_health(manager)
            await test_caching_performance(manager)
            await test_error_handling(manager)
        
        print("\n" + "=" * 50)
        print("🎉 MCP Integration Test Completed!")
        
        if manager:
            # Final status check
            status = await manager.get_provider_status()
            healthy_providers = sum(1 for p in status['providers'].values() if p['healthy'])
            total_providers = len(status['providers'])
            
            print(f"Final Status: {healthy_providers}/{total_providers} providers healthy")
            
            if healthy_providers == total_providers:
                print("🟢 All systems operational - Aurora OS MCP is ready!")
            else:
                print("🟡 Some providers have issues - check logs for details")
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        logger.exception("Test failure details")
    finally:
        if manager:
            await cleanup_test(manager)


if __name__ == "__main__":
    # Run the test
    asyncio.run(main())