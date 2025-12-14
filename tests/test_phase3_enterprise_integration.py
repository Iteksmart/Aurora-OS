"""
Aurora OS Phase 3 Enterprise Integration Tests
Tests for enterprise clustering, load balancing, and management console
"""

import asyncio
import pytest
import json
import time
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
import aiohttp
from typing import Dict, Any

# Import the enterprise components
from enterprise.clustering.cluster_orchestrator import (
    ClusterOrchestrator, ClusterConfig, ScalingConfig, ClusterState
)
from enterprise.clustering.predictive_scaling import (
    PredictiveScalingEngine, PredictionResult
)
from enterprise.load_balancing.intelligent_load_balancer import (
    IntelligentLoadBalancer, LoadBalancingConfig, BackendServer, LoadBalancingAlgorithm
)
from enterprise.management_console.enterprise_dashboard import (
    EnterpriseDashboard, DashboardConfig, AlertLevel
)

class TestPhase3EnterpriseIntegration:
    """Integration tests for Phase 3 enterprise features"""
    
    @pytest.fixture
    async def cluster_config(self):
        """Create test cluster configuration"""
        return ClusterConfig(
            cluster_name="test-cluster",
            region="us-west-2",
            availability_zones=["us-west-2a", "us-west-2b"],
            network_config={
                "auto_discovery": False,
                "nodes": [
                    {
                        "id": "node-1",
                        "name": "Test Node 1",
                        "ip_address": "192.168.1.10",
                        "port": 8080,
                        "type": "control",
                        "capabilities": ["control", "ai"],
                        "resources": {"cpu_cores": 4, "memory_gb": 16}
                    }
                ]
            },
            storage_config={},
            security_config={},
            scaling_config=ScalingConfig(
                policy="threshold_based",
                min_nodes=3,
                max_nodes=10,
                cpu_threshold=80.0,
                memory_threshold=85.0
            ),
            backup_config={},
            monitoring_config={}
        )
    
    @pytest.fixture
    async def load_balancer_config(self):
        """Create test load balancer configuration"""
        return LoadBalancingConfig(
            algorithm=LoadBalancingAlgorithm.AI_POWERED,
            health_check_interval=30,
            sticky_sessions=False,
            ai_weight_factor=0.3
        )
    
    @pytest.fixture
    async def dashboard_config(self):
        """Create test dashboard configuration"""
        return DashboardConfig(
            title="Test Aurora OS Dashboard",
            refresh_interval=5,
            enable_auto_refresh=True
        )

class TestClusterOrchestrator:
    """Test cluster orchestrator functionality"""
    
    @pytest.mark.asyncio
    async def test_cluster_initialization(self, cluster_config):
        """Test cluster initialization"""
        orchestrator = ClusterOrchestrator(cluster_config)
        
        # Mock node manager
        orchestrator.node_manager = Mock()
        orchestrator.node_manager.initialize = AsyncMock(return_value=True)
        orchestrator.node_manager.get_active_nodes = AsyncMock(return_value=[])
        
        # Test initialization
        result = await orchestrator.initialize_cluster()
        assert result is True
        assert orchestrator.state != ClusterState.INITIALIZING
    
    @pytest.mark.asyncio
    async def test_node_registration(self, cluster_config):
        """Test node registration"""
        orchestrator = ClusterOrchestrator(cluster_config)
        
        # Mock validation
        with patch.object(orchestrator, 'validate_node_connectivity', return_value=True):
            orchestrator.node_manager = Mock()
            orchestrator.node_manager.add_node = AsyncMock(return_value=True)
            
            node_config = {
                "id": "test-node",
                "name": "Test Node",
                "ip_address": "192.168.1.100",
                "port": 8080,
                "type": "worker"
            }
            
            result = await orchestrator.register_node(node_config)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self, cluster_config):
        """Test cluster metrics collection"""
        orchestrator = ClusterOrchestrator(cluster_config)
        
        # Mock node manager with test data
        mock_nodes = [
            Mock(
                resources={"cpu_cores": 4, "cpu_used": 2, "memory_gb": 16, "memory_used_gb": 8},
                status=Mock(value="active")
            ),
            Mock(
                resources={"cpu_cores": 4, "cpu_used": 3, "memory_gb": 16, "memory_used_gb": 12},
                status=Mock(value="active")
            )
        ]
        
        orchestrator.node_manager = Mock()
        orchestrator.node_manager.get_active_nodes = AsyncMock(return_value=mock_nodes)
        
        # Collect metrics
        metrics = await orchestrator.collect_cluster_metrics()
        
        assert metrics.total_nodes == 2
        assert metrics.active_nodes == 2
        assert 0 <= metrics.cpu_utilization <= 100
        assert 0 <= metrics.memory_utilization <= 100

class TestPredictiveScalingEngine:
    """Test predictive scaling engine"""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test engine initialization"""
        engine = PredictiveScalingEngine("/tmp/test_models")
        
        assert engine.model_version is not None
        assert engine.metrics_history == []
        assert engine.cpu_model is not None
    
    @pytest.mark.asyncio
    async def test_prediction_with_insufficient_data(self):
        """Test prediction with insufficient historical data"""
        engine = PredictiveScalingEngine("/tmp/test_models")
        
        prediction = await engine.predict_scaling_needs(60)
        
        assert isinstance(prediction, PredictionResult)
        assert prediction.confidence_score < 0.5  # Low confidence with insufficient data
        assert prediction.scaling_recommendation in ["maintain", "scale_up", "scale_down", "immediate_scale_up", "urgent_scale_up", "moderate_scale_up"]
    
    @pytest.mark.asyncio
    async def test_metrics_addition(self):
        """Test adding metrics to history"""
        engine = PredictiveScalingEngine("/tmp/test_models")
        
        from enterprise.clustering.cluster_orchestrator import ClusterMetrics
        
        test_metrics = ClusterMetrics(
            total_nodes=3,
            active_nodes=3,
            cpu_utilization=75.5,
            memory_utilization=82.3,
            network_throughput=1000.0,
            storage_utilization=45.0,
            request_rate=850.0,
            error_rate=1.5,
            response_time=125.0
        )
        
        await engine.add_metrics(test_metrics)
        assert len(engine.metrics_history) == 1
    
    @pytest.mark.asyncio
    async def test_anomaly_detection(self):
        """Test anomaly detection"""
        engine = PredictiveScalingEngine("/tmp/test_models")
        
        from enterprise.clustering.cluster_orchestrator import ClusterMetrics
        
        # Add normal metrics first
        normal_metrics = ClusterMetrics(
            total_nodes=3, active_nodes=3, cpu_utilization=50.0, memory_utilization=60.0,
            network_throughput=800.0, storage_utilization=40.0, request_rate=500.0,
            error_rate=0.5, response_time=100.0
        )
        
        # Add multiple normal metrics
        for _ in range(60):
            await engine.add_metrics(normal_metrics)
        
        # Add anomalous metrics
        anomalous_metrics = ClusterMetrics(
            total_nodes=3, active_nodes=3, cpu_utilization=95.0, memory_utilization=98.0,
            network_throughput=5000.0, storage_utilization=95.0, request_rate=2000.0,
            error_rate=15.0, response_time=500.0
        )
        
        detection = await engine.detect_anomalies(anomalous_metrics)
        
        assert isinstance(detection.severity, str)
        assert detection.severity in ["low", "medium", "high"]

class TestIntelligentLoadBalancer:
    """Test intelligent load balancer"""
    
    @pytest.mark.asyncio
    async def test_load_balancer_initialization(self, load_balancer_config):
        """Test load balancer initialization"""
        lb = IntelligentLoadBalancer(load_balancer_config)
        
        assert lb.config.algorithm == LoadBalancingAlgorithm.AI_POWERED
        assert len(lb.backends) == 0
        assert lb.performance_predictor is not None
    
    @pytest.mark.asyncio
    async def test_backend_management(self, load_balancer_config):
        """Test backend server management"""
        lb = IntelligentLoadBalancer(load_balancer_config)
        
        # Add backend
        backend = BackendServer(
            id="backend-1",
            name="Test Backend",
            ip_address="192.168.1.100",
            port=8080,
            weight=1
        )
        
        lb.add_backend(backend)
        
        assert "backend-1" in lb.backends
        assert "backend-1" in lb.circuit_breakers
        
        # Remove backend
        lb.remove_backend("backend-1")
        
        assert "backend-1" not in lb.backends
        assert "backend-1" not in lb.circuit_breakers
    
    @pytest.mark.asyncio
    async def test_request_routing(self, load_balancer_config):
        """Test request routing"""
        lb = IntelligentLoadBalancer(load_balancer_config)
        
        # Add test backends
        backend1 = BackendServer(
            id="backend-1", name="Backend 1", ip_address="192.168.1.100", port=8080
        )
        backend2 = BackendServer(
            id="backend-2", name="Backend 2", ip_address="192.168.1.101", port=8080
        )
        
        lb.add_backend(backend1)
        lb.add_backend(backend2)
        
        # Test routing
        request_info = {
            "client_ip": "192.168.1.50",
            "path": "/api/test",
            "user_agent": "test-agent"
        }
        
        backend, method = await lb.route_request(request_info)
        
        # Should return a backend even without health checks
        assert backend is not None
        assert method in ["round_robin", "ai_powered", "no_available_backends"]
    
    @pytest.mark.asyncio
    async def test_circuit_breaker(self, load_balancer_config):
        """Test circuit breaker functionality"""
        lb = IntelligentLoadBalancer(load_balancer_config)
        
        backend = BackendServer(
            id="backend-1", name="Test Backend", ip_address="192.168.1.100", port=8080
        )
        
        lb.add_backend(backend)
        
        # Simulate failures
        for i in range(6):  # Exceed failure threshold
            await lb.record_request_result("backend-1", 5000, 500, {"path": "/test"})
        
        # Check circuit breaker state
        circuit_breaker = lb.circuit_breakers["backend-1"]
        assert circuit_breaker["state"] == "open"
    
    @pytest.mark.asyncio
    async def test_load_balancer_stats(self, load_balancer_config):
        """Test load balancer statistics"""
        lb = IntelligentLoadBalancer(load_balancer_config)
        
        # Add test backends
        backend = BackendServer(
            id="backend-1", name="Test Backend", ip_address="192.168.1.100", port=8080,
            total_requests=100, failed_requests=5
        )
        backend.status = "healthy"
        backend.response_time = 150.0
        
        lb.add_backend(backend)
        
        stats = lb.get_load_balancer_stats()
        
        assert stats["algorithm"] == "ai_powered"
        assert stats["total_backends"] == 1
        assert stats["healthy_backends"] == 1
        assert len(stats["backend_stats"]) == 1

class TestEnterpriseDashboard:
    """Test enterprise management dashboard"""
    
    @pytest.mark.asyncio
    async def test_dashboard_initialization(self, dashboard_config):
        """Test dashboard initialization"""
        dashboard = EnterpriseDashboard(dashboard_config)
        
        assert dashboard.config.title == "Test Aurora OS Dashboard"
        assert dashboard.config.refresh_interval == 5
        assert len(dashboard.alerts) == 0
        assert len(dashboard.connected_clients) == 0
    
    @pytest.mark.asyncio
    async def test_alert_management(self, dashboard_config):
        """Test alert creation and management"""
        dashboard = EnterpriseDashboard(dashboard_config)
        
        # Create test alert
        await dashboard.create_alert(
            AlertLevel.WARNING,
            "Test Alert",
            "This is a test alert",
            "test_source"
        )
        
        assert len(dashboard.alerts) == 1
        assert dashboard.alerts[0].level == AlertLevel.WARNING
        assert dashboard.alerts[0].title == "Test Alert"
        assert not dashboard.alerts[0].acknowledged
        assert not dashboard.alerts[0].resolved
    
    @pytest.mark.asyncio
    async def test_dashboard_data_collection(self, dashboard_config):
        """Test dashboard data collection"""
        dashboard = EnterpriseDashboard(dashboard_config)
        
        data = await dashboard.get_dashboard_data()
        
        assert "timestamp" in data
        assert "cluster_metrics" in data
        assert "cluster_nodes" in data
        assert "load_balancer_stats" in data
        assert "alerts" in data
        assert "system_info" in data
    
    @pytest.mark.asyncio
    async def test_metrics_data_api(self, dashboard_config):
        """Test metrics data API endpoint"""
        dashboard = EnterpriseDashboard(dashboard_config)
        
        # Mock request object
        request = Mock()
        request.query = {"type": "all", "hours": "24"}
        
        # Test metrics data retrieval
        data = await dashboard.get_metrics_data(request)
        
        assert "timestamps" in data
        assert "cpu_utilization" in data
        assert "memory_utilization" in data
        assert "request_rate" in data
        assert "response_time" in data
        assert "error_rate" in data

class TestPhase3Integration:
    """Integration tests for all Phase 3 components"""
    
    @pytest.mark.asyncio
    async def test_full_enterprise_stack(self):
        """Test full enterprise stack integration"""
        # Create configurations
        cluster_config = ClusterConfig(
            cluster_name="integration-test",
            region="us-west-2",
            availability_zones=["us-west-2a"],
            network_config={"auto_discovery": False, "nodes": []},
            storage_config={},
            security_config={},
            scaling_config=ScalingConfig(policy="threshold_based"),
            backup_config={},
            monitoring_config={}
        )
        
        load_balancer_config = LoadBalancingConfig(
            algorithm=LoadBalancingAlgorithm.AI_POWERED
        )
        
        dashboard_config = DashboardConfig(refresh_interval=1)
        
        # Initialize components
        orchestrator = ClusterOrchestrator(cluster_config)
        scaling_engine = PredictiveScalingEngine("/tmp/integration_test_models")
        load_balancer = IntelligentLoadBalancer(load_balancer_config)
        dashboard = EnterpriseDashboard(dashboard_config)
        
        # Mock dependencies
        orchestrator.node_manager = Mock()
        orchestrator.node_manager.initialize = AsyncMock(return_value=True)
        orchestrator.node_manager.get_active_nodes = AsyncMock(return_value=[])
        
        # Test initialization
        assert await orchestrator.initialize_cluster() is True
        assert scaling_engine.model_version is not None
        assert load_balancer.performance_predictor is not None
        assert dashboard.config.title == "Aurora OS Enterprise Dashboard"
        
        # Test component integration
        # Add some test metrics
        from enterprise.clustering.cluster_orchestrator import ClusterMetrics
        
        test_metrics = ClusterMetrics(
            total_nodes=3, active_nodes=3, cpu_utilization=75.0, memory_utilization=80.0,
            network_throughput=1200.0, storage_utilization=50.0, request_rate=900.0,
            error_rate=2.0, response_time=150.0
        )
        
        await scaling_engine.add_metrics(test_metrics)
        prediction = await scaling_engine.predict_scaling_needs(60)
        assert isinstance(prediction, PredictionResult)
        
        # Test load balancer with backend
        backend = BackendServer(
            id="test-backend", name="Test Backend", 
            ip_address="192.168.1.100", port=8080
        )
        load_balancer.add_backend(backend)
        
        request_info = {"client_ip": "192.168.1.50", "path": "/api/test"}
        routed_backend, method = await load_balancer.route_request(request_info)
        assert routed_backend is not None
        
        # Test dashboard integration
        dashboard.cluster_orchestrator = orchestrator
        dashboard.load_balancer = load_balancer
        
        dashboard_data = await dashboard.get_dashboard_data()
        assert "cluster_metrics" in dashboard_data
        assert "load_balancer_stats" in dashboard_data
        
        # Create an alert to test alert system
        await dashboard.create_alert(
            AlertLevel.INFO,
            "Integration Test",
            "Components integrated successfully",
            "integration_test"
        )
        
        assert len(dashboard.alerts) == 1
        
        self.logger.info("Full enterprise stack integration test passed")

# Performance and stress tests
class TestPhase3Performance:
    """Performance tests for Phase 3 components"""
    
    @pytest.mark.asyncio
    async def test_load_balancer_performance(self):
        """Test load balancer performance under load"""
        config = LoadBalancingConfig(algorithm=LoadBalancingAlgorithm.LEAST_CONNECTIONS)
        lb = IntelligentLoadBalancer(config)
        
        # Add multiple backends
        for i in range(10):
            backend = BackendServer(
                id=f"backend-{i}",
                name=f"Backend {i}",
                ip_address=f"192.168.1.{100+i}",
                port=8080,
                max_connections=100
            )
            lb.add_backend(backend)
        
        # Simulate high request volume
        start_time = time.time()
        
        for i in range(1000):
            request_info = {
                "client_ip": f"192.168.1.{i%255}",
                "path": f"/api/test/{i}",
                "user_agent": "performance-test"
            }
            
            backend, method = await lb.route_request(request_info)
            assert backend is not None
        
        end_time = time.time()
        routing_time = end_time - start_time
        
        # Performance assertion - should handle 1000 requests quickly
        assert routing_time < 5.0  # Should complete in under 5 seconds
        
        stats = lb.get_load_balancer_stats()
        assert stats["total_requests"] == 1000
    
    @pytest.mark.asyncio
    async def test_predictive_scaling_performance(self):
        """Test predictive scaling engine performance"""
        engine = PredictiveScalingEngine("/tmp/performance_test_models")
        
        from enterprise.clustering.cluster_orchestrator import ClusterMetrics
        
        # Add large amount of metrics data
        start_time = time.time()
        
        for i in range(1000):
            metrics = ClusterMetrics(
                total_nodes=5, active_nodes=5,
                cpu_utilization=50 + (i % 30),
                memory_utilization=60 + (i % 25),
                network_throughput=800 + (i % 400),
                storage_utilization=40 + (i % 20),
                request_rate=500 + (i % 500),
                error_rate=0.5 + (i % 3),
                response_time=100 + (i % 100)
            )
            await engine.add_metrics(metrics)
        
        # Test prediction performance
        prediction = await engine.predict_scaling_needs(60)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        assert processing_time < 10.0  # Should process 1000 metrics and predict in under 10 seconds
        assert len(engine.metrics_history) == 1000
        assert isinstance(prediction, PredictionResult)

if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])