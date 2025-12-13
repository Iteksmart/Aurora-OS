"""
Test suite for Aurora OS Multi-Node Architecture
"""

import asyncio
import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from enterprise.clustering.node_manager import NodeManager, NodeInfo, ClusterConfig, NodeStatus, NodeType, ClusterRole
from enterprise.clustering.distributed_context import DistributedContextManager, ContextData, ContextMetadata, ContextType, ReplicationStrategy
from enterprise.multi_node.cluster_manager import ClusterManager, ClusterNode, ClusterConfig as MultiNodeConfig
from enterprise.load_balancing.distributed_load_balancer import DistributedLoadBalancer, BackendNode, LoadBalancingConfig, LoadBalancingAlgorithm

class TestNodeManager:
    """Test Node Manager functionality"""
    
    def test_node_info_creation(self):
        """Test NodeInfo creation and serialization"""
        node_info = NodeInfo(
            id="node-001",
            name="test-node",
            ip_address="192.168.1.100",
            port=8081,
            node_type=NodeType.WORKER,
            status=NodeStatus.ACTIVE,
            cluster_role=ClusterRole.FOLLOWER,
            last_heartbeat=1234567890,
            capabilities={"ai_processing": True, "storage": True},
            resources={"cpu_cores": 4, "memory_gb": 8},
            metadata={"version": "0.1.0"}
        )
        
        # Test serialization
        data = node_info.to_dict()
        assert isinstance(data, dict)
        assert data["id"] == "node-001"
        assert data["node_type"] == NodeType.WORKER.value
        
        # Test deserialization
        restored_node = NodeInfo.from_dict(data)
        assert restored_node.id == node_info.id
        assert restored_node.node_type == node_info.node_type
    
    def test_cluster_config(self):
        """Test Cluster configuration"""
        config = ClusterConfig(
            name="test-cluster",
            version="0.1.0",
            heartbeat_interval=5.0,
            heartbeat_timeout=15.0,
            auto_failover=True
        )
        
        assert config.name == "test-cluster"
        assert config.heartbeat_interval == 5.0
        assert config.auto_failover is True
        
        # Test serialization
        data = config.to_dict()
        assert data["name"] == "test-cluster"
        assert data["auto_failover"] is True
    
    def test_node_manager_initialization(self):
        """Test Node Manager initialization"""
        node_info = NodeInfo(
            id="test-node",
            name="test-node",
            ip_address="127.0.0.1",
            port=8081,
            node_type=NodeType.WORKER,
            status=NodeStatus.ACTIVE,
            cluster_role=ClusterRole.FOLLOWER,
            last_heartbeat=1234567890,
            capabilities={},
            resources={},
            metadata={}
        )
        
        config = ClusterConfig(
            name="test-cluster",
            version="0.1.0"
        )
        
        manager = NodeManager(node_info, config)
        
        assert manager.node_info == node_info
        assert manager.cluster_config == config
        assert manager.leader_node is None
        assert len(manager.nodes) == 1  # Self is added
    
    def test_load_balancer_integration(self):
        """Test load balancer integration"""
        node_info = NodeInfo(
            id="test-node",
            name="test-node",
            ip_address="127.0.0.1",
            port=8081,
            node_type=NodeType.WORKER,
            status=NodeStatus.ACTIVE,
            cluster_role=ClusterRole.FOLLOWER,
            last_heartbeat=1234567890,
            capabilities={},
            resources={},
            metadata={}
        )
        
        config = ClusterConfig(
            name="test-cluster",
            version="0.1.0"
        )
        
        manager = NodeManager(node_info, config)
        load_balancer = manager.get_load_balancer()
        
        assert load_balancer is not None
        
        # Test adding nodes to load balancer
        load_balancer.add_node("node-002", {"cpu_total": 4, "memory_total": 8})
        assert "node-002" in load_balancer.nodes
        
        # Test node selection
        selected = load_balancer.select_node()
        assert selected in ["node-002"]
        
        # Test statistics
        stats = load_balancer.get_statistics()
        assert "total_nodes" in stats
        assert stats["total_nodes"] == 1

class TestDistributedContextManager:
    """Test Distributed Context Manager"""
    
    def test_context_metadata(self):
        """Test context metadata creation and serialization"""
        metadata = ContextMetadata(
            context_id="test-context",
            context_type=ContextType.USER_SESSION,
            priority=3,  # HIGH priority enum value
            created_at=1234567890,
            updated_at=1234567890,
            expires_at=1234567950,
            owner_node="node-001",
            version=1,
            replication_factor=3,
            consistency_level="quorum",
            tags={"user", "session"},
            size_bytes=1024
        )
        
        # Test serialization
        data = metadata.to_dict()
        assert isinstance(data, dict)
        assert data["context_type"] == ContextType.USER_SESSION.value
        assert "user" in data["tags"]
        
        # Test deserialization
        restored = ContextMetadata.from_dict(data)
        assert restored.context_id == metadata.context_id
        assert restored.context_type == metadata.context_type
        assert restored.tags == metadata.tags
    
    def test_context_data_compression(self):
        """Test context data compression"""
        metadata = ContextMetadata(
            context_id="test-context",
            context_type=ContextType.APPLICATION_STATE,
            priority=2,
            created_at=1234567890,
            updated_at=1234567890,
            expires_at=None,
            owner_node="node-001",
            version=1,
            replication_factor=3,
            consistency_level="eventual",
            tags={"app", "state"},
            size_bytes=100
        )
        
        # Small data (should not compress)
        small_data = "test"
        context_data = ContextData(
            metadata=metadata,
            data=small_data,
            checksum="",
            compressed=False
        )
        
        context_data.compress_data()
        assert not context_data.compressed  # Should not compress small data
        
        # Large data (should compress)
        large_data = "x" * 2000
        context_data.data = large_data
        context_data.compress_data()
        assert context_data.compressed  # Should compress large data
        
        # Test decompression
        decompressed = context_data.decompress_data()
        assert decompressed == large_data
    
    def test_context_manager_initialization(self):
        """Test context manager initialization"""
        manager = DistributedContextManager("node-001")
        
        assert manager.node_id == "node-001"
        assert manager.replication_strategy == ReplicationStrategy.QUORUM
        assert len(manager.local_contexts) == 0
        assert len(manager.cache) == 0
    
    @pytest.mark.asyncio
    async def test_context_storage_and_retrieval(self):
        """Test context storage and retrieval"""
        manager = DistributedContextManager("node-001")
        
        # Store context
        test_data = {"key": "value", "nested": {"data": "test"}}
        success = await manager.store_context(
            "test-context",
            test_data,
            ContextType.USER_SESSION,
            tags={"test", "user"}
        )
        
        assert success
        assert "test-context" in manager.local_contexts
        
        # Retrieve context
        retrieved_data = await manager.get_context("test-context")
        assert retrieved_data == test_data
        
        # Check statistics
        stats = manager.get_statistics()
        assert stats["contexts_stored"] == 1
        assert stats["contexts_retrieved"] == 1
    
    @pytest.mark.asyncio
    async def test_context_update(self):
        """Test context update"""
        manager = DistributedContextManager("node-001")
        
        # Store initial context
        initial_data = {"version": 1}
        await manager.store_context("update-test", initial_data, ContextType.APPLICATION_STATE)
        
        # Update context
        updated_data = {"version": 2, "updated": True}
        success = await manager.update_context("update-test", updated_data, version=1)
        
        assert success
        
        # Verify update
        retrieved_data = await manager.get_context("update-test")
        assert retrieved_data["version"] == 2
        assert retrieved_data["updated"] is True
    
    @pytest.mark.asyncio
    async def test_context_deletion(self):
        """Test context deletion"""
        manager = DistributedContextManager("node-001")
        
        # Store context
        await manager.store_context("delete-test", {"data": "test"}, ContextType.TEMPORARY)
        assert "delete-test" in manager.local_contexts
        
        # Delete context
        success = await manager.delete_context("delete-test")
        assert success
        assert "delete-test" not in manager.local_contexts
    
    @pytest.mark.asyncio
    async def test_context_search(self):
        """Test context search functionality"""
        manager = DistributedContextManager("node-001")
        
        # Store multiple contexts
        await manager.store_context("context1", {"data": "test1"}, ContextType.USER_SESSION, tags={"user", "session"})
        await manager.store_context("context2", {"data": "test2"}, ContextType.APPLICATION_STATE, tags={"app", "state"})
        await manager.store_context("context3", {"data": "test3"}, ContextType.USER_SESSION, tags={"user", "active"})
        
        # Search by type
        user_sessions = await manager.find_contexts(context_type=ContextType.USER_SESSION)
        assert len(user_sessions) == 2
        assert "context1" in user_sessions
        assert "context3" in user_sessions
        
        # Search by tags
        tagged_contexts = await manager.find_contexts(tags={"user"})
        assert len(tagged_contexts) == 2
        
        # Search by multiple criteria
        specific_contexts = await manager.find_contexts(
            context_type=ContextType.USER_SESSION,
            tags={"session"}
        )
        assert len(specific_contexts) == 1
        assert "context1" in specific_contexts

class TestClusterManager:
    """Test Multi-Node Cluster Manager"""
    
    def test_cluster_node_creation(self):
        """Test cluster node creation and serialization"""
        node = ClusterNode(
            id="node-001",
            name="test-node",
            host="192.168.1.100",
            port=8081,
            role="manager",
            status="online",
            capabilities={"ai_processing": True},
            resources={"cpu_cores": 4},
            last_heartbeat=datetime.now(),
            metadata={"version": "0.1.0"}
        )
        
        # Test serialization
        data = node.to_dict()
        assert isinstance(data, dict)
        assert data["id"] == "node-001"
        assert data["role"] == "manager"
        
        # Test deserialization
        restored = ClusterNode.from_dict(data)
        assert restored.id == node.id
        assert restored.role.value == node.role
    
    def test_cluster_config_creation(self):
        """Test cluster configuration"""
        config = MultiNodeConfig(
            name="test-cluster",
            version="0.1.0",
            heartbeat_interval=30,
            node_timeout=90,
            auto_healing=True
        )
        
        assert config.name == "test-cluster"
        assert config.heartbeat_interval == 30
        assert config.auto_healing is True
    
    def test_cluster_manager_initialization(self):
        """Test cluster manager initialization"""
        config = MultiNodeConfig(
            name="test-cluster",
            version="0.1.0"
        )
        
        manager = ClusterManager(config)
        
        assert manager.config == config
        assert manager.node_id is not None
        assert len(manager.nodes) == 0
        assert manager.is_manager is False
    
    def test_cluster_status(self):
        """Test cluster status reporting"""
        config = MultiNodeConfig(
            name="test-cluster",
            version="0.1.0"
        )
        
        manager = ClusterManager(config)
        
        # Add some test nodes
        from datetime import datetime
        test_node = ClusterNode(
            id="node-001",
            name="test-node",
            host="192.168.1.100",
            port=8081,
            role="worker",
            status="online",
            capabilities={},
            resources={},
            last_heartbeat=datetime.now(),
            metadata={}
        )
        
        manager.nodes[test_node.id] = test_node
        
        status = manager.get_cluster_status()
        
        assert "cluster_name" in status
        assert status["cluster_name"] == "test-cluster"
        assert status["total_nodes"] == 1
        assert status["online_nodes"] == 1

class TestDistributedLoadBalancer:
    """Test Distributed Load Balancer"""
    
    def test_backend_node_creation(self):
        """Test backend node creation"""
        node = BackendNode(
            id="backend-001",
            host="192.168.1.100",
            port=8080,
            weight=2,
            max_connections=1000,
            region="us-west"
        )
        
        assert node.id == "backend-001"
        assert node.weight == 2
        assert node.region == "us-west"
        assert node.is_healthy is True
        assert node.load_score == 0.0
    
    def test_load_balancer_config(self):
        """Test load balancer configuration"""
        config = LoadBalancingConfig(
            algorithm=LoadBalancingAlgorithm.RESOURCE_BASED,
            sticky_sessions=True,
            failover_enabled=True
        )
        
        assert config.algorithm == LoadBalancingAlgorithm.RESOURCE_BASED
        assert config.sticky_sessions is True
        assert config.failover_enabled is True
    
    def test_load_balancer_initialization(self):
        """Test load balancer initialization"""
        config = LoadBalancingConfig(
            algorithm=LoadBalancingAlgorithm.ROUND_ROBIN
        )
        
        balancer = DistributedLoadBalancer(config)
        
        assert balancer.config == config
        assert len(balancer.backend_nodes) == 0
    
    def test_node_management(self):
        """Test node management"""
        config = LoadBalancingConfig()
        balancer = DistributedLoadBalancer(config)
        
        # Add nodes
        node1 = BackendNode("node1", "192.168.1.100", 8080)
        node2 = BackendNode("node2", "192.168.1.101", 8080, weight=2)
        
        balancer.add_backend_node(node1)
        balancer.add_backend_node(node2)
        
        assert len(balancer.backend_nodes) == 2
        assert "node1" in balancer.backend_nodes
        assert "node2" in balancer.backend_nodes
        
        # Test healthy nodes
        healthy_nodes = balancer.get_healthy_nodes()
        assert len(healthy_nodes) == 2
        
        # Remove node
        balancer.remove_backend_node("node1")
        assert len(balancer.backend_nodes) == 1
        assert "node1" not in balancer.backend_nodes
    
    @pytest.mark.asyncio
    async def test_load_balancing_algorithms(self):
        """Test different load balancing algorithms"""
        
        # Test Round Robin
        config = LoadBalancingConfig(algorithm=LoadBalancingAlgorithm.ROUND_ROBIN)
        balancer = DistributedLoadBalancer(config)
        
        # Add test nodes
        for i in range(3):
            node = BackendNode(f"node{i}", f"192.168.1.{100+i}", 8080)
            balancer.add_backend_node(node)
        
        # Test selections
        selections = []
        for _ in range(6):
            node = await balancer.select_node()
            selections.append(node.id)
        
        # Should cycle through nodes
        assert len(set(selections)) == 3
        
        # Test Least Connections
        config.algorithm = LoadBalancingAlgorithm.LEAST_CONNECTIONS
        balancer = DistributedLoadBalancer(config)
        
        # Re-add nodes
        for i in range(3):
            node = BackendNode(f"node{i}", f"192.168.1.{100+i}", 8080)
            if i == 1:
                node.current_connections = 5  # Higher load
            balancer.add_backend_node(node)
        
        # Should select node with least connections
        selected = await balancer.select_node()
        assert selected.current_connections == 0  # Should pick node 0 or 2
    
    @pytest.mark.asyncio
    async def test_node_release_and_metrics(self):
        """Test node release and metrics collection"""
        config = LoadBalancingConfig()
        balancer = DistributedLoadBalancer(config)
        
        node = BackendNode("test-node", "192.168.1.100", 8080)
        balancer.add_backend_node(node)
        
        # Select node (increments connections)
        selected = await balancer.select_node()
        assert selected.current_connections == 1
        assert selected.total_requests == 1
        
        # Release node with success
        await balancer.release_node(selected, True, 0.1)
        
        assert selected.current_connections == 0
        assert selected.success_count == 1
        assert 0.1 in selected.response_times
        
        # Release node with failure
        selected = await balancer.select_node()
        await balancer.release_node(selected, False, 0.2)
        
        assert selected.error_count == 1
        assert selected.total_requests == 2
    
    def test_statistics(self):
        """Test load balancer statistics"""
        config = LoadBalancingConfig()
        balancer = DistributedLoadBalancer(config)
        
        # Add test nodes
        for i in range(2):
            node = BackendNode(f"node{i}", f"192.168.1.{100+i}", 8080)
            if i == 0:
                node.health_status = "healthy"
            else:
                node.health_status = "unhealthy"
            balancer.add_backend_node(node)
        
        stats = balancer.get_statistics()
        
        assert "total_nodes" in stats
        assert "healthy_nodes" in stats
        assert stats["total_nodes"] == 2
        assert stats["healthy_nodes"] == 1
        assert "algorithm" in stats

# Test runner function
def run_multi_node_tests():
    """Run all multi-node architecture tests"""
    print("🌐 Running Multi-Node Architecture Tests")
    print("=" * 60)
    
    # Synchronous tests
    sync_tests = [
        ("Node Info", TestNodeManager().test_node_info_creation),
        ("Cluster Config", TestNodeManager().test_cluster_config),
        ("Node Manager Init", TestNodeManager().test_node_manager_initialization),
        ("Load Balancer Integration", TestNodeManager().test_load_balancer_integration),
        ("Context Metadata", TestDistributedContextManager().test_context_metadata),
        ("Context Data Compression", TestDistributedContextManager().test_context_data_compression),
        ("Context Manager Init", TestDistributedContextManager().test_context_manager_initialization),
        ("Cluster Node", TestClusterManager().test_cluster_node_creation),
        ("Cluster Config", TestClusterManager().test_cluster_config_creation),
        ("Cluster Manager Init", TestClusterManager().test_cluster_manager_initialization),
        ("Cluster Status", TestClusterManager().test_cluster_status),
        ("Backend Node", TestDistributedLoadBalancer().test_backend_node_creation),
        ("Load Balancer Config", TestDistributedLoadBalancer().test_load_balancer_config),
        ("Load Balancer Init", TestDistributedLoadBalancer().test_load_balancer_initialization),
        ("Node Management", TestDistributedLoadBalancer().test_node_management),
        ("Load Balancer Stats", TestDistributedLoadBalancer().test_statistics),
    ]
    
    # Run synchronous tests
    passed = 0
    failed = 0
    
    for test_name, test_func in sync_tests:
        try:
            print(f"  📋 {test_name}... ", end="")
            test_func()
            print("✅ PASSED")
            passed += 1
        except Exception as e:
            print(f"❌ FAILED: {e}")
            failed += 1
    
    # Run async tests
    async_tests = [
        ("Context Storage/Retrieval", TestDistributedContextManager().test_context_storage_and_retrieval),
        ("Context Update", TestDistributedContextManager().test_context_update),
        ("Context Deletion", TestDistributedContextManager().test_context_deletion),
        ("Context Search", TestDistributedContextManager().test_context_search),
        ("Load Balancing Algorithms", TestDistributedLoadBalancer().test_load_balancing_algorithms),
        ("Node Release Metrics", TestDistributedLoadBalancer().test_node_release_and_metrics),
    ]
    
    async def run_async_tests():
        nonlocal passed, failed
        
        for test_name, test_func in async_tests:
            try:
                print(f"  📋 {test_name}... ", end="")
                await test_func()
                print("✅ PASSED")
                passed += 1
            except Exception as e:
                print(f"❌ FAILED: {e}")
                failed += 1
    
    # Run async tests
    asyncio.run(run_async_tests())
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = run_multi_node_tests()
    sys.exit(0 if success else 1)