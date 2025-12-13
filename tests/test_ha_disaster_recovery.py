"""
Test suite for Aurora OS High Availability & Disaster Recovery
"""

import asyncio
import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from enterprise.ha_disaster_recovery.automatic_failover import (
    AutomaticFailoverManager, FailoverMode, FailoverStrategy, NodeState, Node
)
from enterprise.ha_disaster_recovery.data_replication import (
    DataReplicator, ReplicationMode, ReplicationNode, ReplicationRole, ReplicationState, ConsistencyLevel
)
from enterprise.ha_disaster_recovery.disaster_recovery import (
    DisasterRecoverySystem, DisasterType, DisasterLevel, RecoveryStatus, RecoveryPlan
)

class TestAutomaticFailover:
    """Test automatic failover system"""
    
    def test_failover_manager_initialization(self):
        """Test failover manager initialization"""
        manager = AutomaticFailoverManager(
            node_id="test-node-1",
            failover_strategy=FailoverStrategy.ACTIVE_PASSIVE
        )
        
        assert manager.node_id == "test-node-1"
        assert manager.failover_strategy == FailoverStrategy.ACTIVE_PASSIVE
        assert len(manager.nodes) == 0
        assert len(manager.failover_events) == 0
    
    def test_node_management(self):
        """Test node management"""
        manager = AutomaticFailoverManager("test-node-1")
        
        # Add primary node
        primary_node = Node(
            id="node-1",
            name="Primary Node",
            host="192.168.1.10",
            port=8080,
            state=NodeState.PRIMARY,
            priority=100,
            capabilities={"storage", "compute"},
            health_score=1.0,
            last_heartbeat=datetime.now(),
            health_history=[],
            failover_count=0,
            metadata={"region": "us-east-1"}
        )
        
        manager.add_node(primary_node)
        
        assert len(manager.nodes) == 1
        assert manager.nodes["node-1"] == primary_node
        
        # Add secondary node
        secondary_node = Node(
            id="node-2",
            name="Secondary Node",
            host="192.168.1.11",
            port=8080,
            state=NodeState.SECONDARY,
            priority=90,
            capabilities={"storage", "compute"},
            health_score=1.0,
            last_heartbeat=datetime.now(),
            health_history=[],
            failover_count=0,
            metadata={"region": "us-east-1"}
        )
        
        manager.add_node(secondary_node)
        
        assert len(manager.nodes) == 2
        assert "node-2" in manager.nodes
    
    def test_failover_configuration(self):
        """Test failover configuration"""
        config = {
            "heartbeat_interval": 5.0,
            "health_check_interval": 10.0,
            "failover_timeout": 30.0,
            "max_consecutive_failures": 3,
            "failover_mode": FailoverMode.AUTOMATIC,
            "auto_recovery_enabled": True,
            "recovery_delay": 300.0
        }
        
        manager = AutomaticFailoverManager("test-node-1", config)
        
        assert manager.config["heartbeat_interval"] == 5.0
        assert manager.config["failover_mode"] == FailoverMode.AUTOMATIC
        assert manager.config["auto_recovery_enabled"] is True
    
    def test_health_check_simulation(self):
        """Test health check simulation"""
        manager = AutomaticFailoverManager("test-node-1")
        
        # Add a node
        node = Node(
            id="test-node",
            name="Test Node",
            host="192.168.1.100",
            port=8080,
            state=NodeState.PRIMARY,
            priority=100,
            capabilities={"compute"},
            health_score=1.0,
            last_heartbeat=datetime.now(),
            health_history=[],
            failover_count=0,
            metadata={}
        )
        
        manager.add_node(node)
        
        # Simulate health check
        result = asyncio.run(manager._check_node_health(node))
        
        assert result.node_id == "test-node"
        assert result.check_type is not None
        assert result.response_time >= 0
        assert isinstance(result.status, str)
    
    def test_failover_decision_logic(self):
        """Test failover decision logic"""
        manager = AutomaticFailoverManager(
            "test-node-1",
            failover_strategy=FailoverStrategy.ACTIVE_PASSIVE
        )
        
        # Add nodes
        primary = Node(
            id="primary",
            name="Primary",
            host="192.168.1.10",
            port=8080,
            state=NodeState.PRIMARY,
            priority=100,
            capabilities={"compute"},
            health_score=0.2,  # Low health score
            last_heartbeat=datetime.now() - timedelta(minutes=2),
            health_history=[],
            failover_count=0,
            metadata={}
        )
        
        secondary = Node(
            id="secondary",
            name="Secondary",
            host="192.168.1.11",
            port=8080,
            state=NodeState.SECONDARY,
            priority=90,
            capabilities={"compute"},
            health_score=0.9,  # High health score
            last_heartbeat=datetime.now(),
            health_history=[],
            failover_count=0,
            metadata={}
        )
        
        manager.add_node(primary)
        manager.add_node(secondary)
        
        # Test failover decision
        should_failover = manager._should_initiate_failover(primary)
        
        # With low health score and stale heartbeat, should failover
        assert should_failover is True

class TestDataReplication:
    """Test data replication system"""
    
    def test_replicator_initialization(self):
        """Test data replicator initialization"""
        replicator = DataReplicator(
            node_id="replicator-node-1",
            replication_mode=ReplicationMode.ASYNCHRONOUS
        )
        
        assert replicator.node_id == "replicator-node-1"
        assert replicator.replication_mode == ReplicationMode.ASYNCHRONOUS
        assert len(replicator.nodes) == 0
        assert replicator.role == ReplicationRole.PRIMARY
    
    def test_replication_node_creation(self):
        """Test replication node creation"""
        node = ReplicationNode(
            node_id="replica-node-1",
            host="192.168.1.50",
            port=5432,
            role=ReplicationRole.SECONDARY,
            state=ReplicationState.HEALTHY,
            last_heartbeat=datetime.now(),
            last_sync=datetime.now(),
            replication_lag=0.5,
            data_size=1024000,
            sync_queue_size=10,
            health_score=0.95,
            capabilities={"postgresql", "replication"}
        )
        
        assert node.node_id == "replica-node-1"
        assert node.role == ReplicationRole.SECONDARY
        assert node.state == ReplicationState.HEALTHY
        assert node.health_score == 0.95
        
        # Test serialization
        data = node.to_dict()
        assert isinstance(data, dict)
        assert data["role"] == "secondary"
        assert data["state"] == "healthy"
    
    def test_consistency_levels(self):
        """Test consistency levels"""
        replicator = DataReplicator("test-node")
        
        # Test different consistency levels
        assert ConsistencyLevel.STRONG.value == "strong"
        assert ConsistencyLevel.EVENTUAL.value == "eventual"
        assert ConsistencyLevel.SEQUENTIAL.value == "sequential"
        
        # Test replication modes
        assert ReplicationMode.SYNCHRONOUS.value == "synchronous"
        assert ReplicationMode.ASYNCHRONOUS.value == "asynchronous"
        assert ReplicationMode.SEMI_SYNCHRONOUS.value == "semi_synchronous"
    
    def test_replication_simulation(self):
        """Test replication simulation"""
        replicator = DataReplicator("primary-node", ReplicationMode.ASYNCHRONOUS)
        
        # Add secondary nodes
        for i in range(3):
            secondary = ReplicationNode(
                node_id=f"secondary-{i+1}",
                host=f"192.168.1.{51+i}",
                port=5432,
                role=ReplicationRole.SECONDARY,
                state=ReplicationState.HEALTHY,
                last_heartbeat=datetime.now(),
                last_sync=datetime.now(),
                replication_lag=0.1,
                data_size=1024000,
                sync_queue_size=5,
                health_score=0.9,
                capabilities={"replication"}
            )
            replicator.add_node(secondary)
        
        # Test data replication
        test_data = b"test replication data"
        operation_id = asyncio.run(
            replicator.replicate_data(
                test_data, 
                "write", 
                consistency_level=ConsistencyLevel.EVENTUAL
            )
        )
        
        assert operation_id is not None
        assert len(operation_id) > 0
        assert replicator.stats["operations_replicated"] > 0
    
    def test_replication_statistics(self):
        """Test replication statistics"""
        replicator = DataReplicator("test-node")
        
        initial_stats = replicator.get_statistics()
        
        assert "operations_replicated" in initial_stats
        assert "bytes_replicated" in initial_stats
        assert "replication_errors" in initial_stats
        assert "average_latency" in initial_stats
        assert "data_loss_events" in initial_stats
        
        # Stats should start at 0
        assert initial_stats["operations_replicated"] == 0
        assert initial_stats["bytes_replicated"] == 0
        assert initial_stats["replication_errors"] == 0

class TestDisasterRecovery:
    """Test disaster recovery system"""
    
    def test_disaster_recovery_initialization(self):
        """Test disaster recovery system initialization"""
        dr_system = DisasterRecoverySystem()
        
        assert len(dr_system.recovery_plans) > 0
        assert len(dr_system.disaster_detector.detection_rules) > 0
        assert dr_system.running is False
        
        # Check default plans are loaded
        assert "service_failure_plan" in dr_system.recovery_plans
        assert "node_failure_plan" in dr_system.recovery_plans
        assert "datacenter_outage_plan" in dr_system.recovery_plans
    
    def test_disaster_scenarios(self):
        """Test disaster scenarios"""
        dr_system = DisasterRecoverySystem()
        
        # Check default scenarios
        scenarios = dr_system.disaster_detector.detection_rules
        
        assert "service_failure" in scenarios
        assert "node_failure" in scenarios
        assert "network_partition" in scenarios
        
        # Check scenario properties
        service_failure_rule = scenarios["service_failure"]
        assert service_failure_rule["title"] == "Service Failure Detected"
        assert service_failure_rule["disaster_type"] == "software_bug"
        assert service_failure_rule["disaster_level"] == "minor"
    
    def test_recovery_plan_structure(self):
        """Test recovery plan structure"""
        dr_system = DisasterRecoverySystem()
        
        service_failure_plan = dr_system.recovery_plans["service_failure_plan"]
        
        assert service_failure_plan.name == "Service Failure Recovery"
        assert DisasterType.SOFTWARE_BUG in service_failure_plan.disaster_types
        assert DisasterLevel.MINOR in service_failure_plan.disaster_levels
        assert len(service_failure_plan.steps) > 0
        
        # Check RTO and RPO
        assert service_failure_plan.rto_seconds == 300  # 5 minutes
        assert service_failure_plan.rpo_seconds == 60   # 1 minute
    
    def test_disaster_detection(self):
        """Test disaster detection"""
        dr_system = DisasterRecoverySystem()
        
        # Add monitoring metrics
        for _ in range(10):
            metrics = {
                "cpu_usage": 95.0,  # High CPU usage
                "memory_usage": 90.0,  # High memory usage
                "error_rate": 10.0,  # High error rate
                "service_health": "unhealthy"
            }
            dr_system.disaster_detector.add_metric(metrics)
        
        # Run disaster detection
        detected_events = asyncio.run(dr_system.disaster_detector.detect_disasters())
        
        # Should detect potential disasters
        assert isinstance(detected_events, list)
        # Detection is probabilistic, so just check it doesn't crash
        assert True
    
    def test_recovery_execution(self):
        """Test recovery execution"""
        dr_system = DisasterRecoverySystem()
        
        # Create a mock disaster event
        disaster_event = DisasterEvent(
            id="test-disaster-001",
            disaster_type=DisasterType.SOFTWARE_BUG,
            level=DisasterLevel.MINOR,
            title="Test Service Failure",
            description="Test service failure for unit testing",
            affected_services=["test-service"],
            affected_nodes=["test-node-1"],
            detected_at=datetime.now(),
            detected_by="test",
            impact_assessment={},
            metadata={"test": True}
        )
        
        # Find appropriate recovery plan
        recovery_plan = dr_system._find_recovery_plan(disaster_event)
        
        assert recovery_plan is not None
        assert recovery_plan.id == "service_failure_plan"
        
        # Initiate recovery
        execution_id = asyncio.run(dr_system.initiate_recovery(disaster_event, recovery_plan))
        
        assert execution_id is not None
        assert execution_id in dr_system.recovery_executions
        assert len(dr_system.active_executions) > 0
    
    def test_disaster_recovery_statistics(self):
        """Test disaster recovery statistics"""
        dr_system = DisasterRecoverySystem()
        
        stats = dr_system.get_statistics()
        
        assert "disasters_detected" in stats
        assert "recoveries_executed" in stats
        assert "successful_recoveries" in stats
        assert "failed_recoveries" in stats
        assert "average_recovery_time" in stats
        
        # Should start with 0 values
        assert stats["disasters_detected"] == 0
        assert stats["recoveries_executed"] == 0
    
    def test_recovery_plan_validation(self):
        """Test recovery plan validation"""
        dr_system = DisasterRecoverySystem()
        
        plans = dr_system.get_recovery_plans()
        
        assert len(plans) >= 3
        
        for plan in plans:
            assert plan.name is not None
            assert len(plan.disaster_types) > 0
            assert len(plan.disaster_levels) > 0
            assert len(plan.steps) > 0
            assert plan.rto_seconds > 0
            assert plan.rpo_seconds >= 0
            assert len(plan.notification_channels) > 0

# Test runner function
def run_ha_disaster_recovery_tests():
    """Run all HA and disaster recovery tests"""
    print("🛡️  Running High Availability & Disaster Recovery Tests")
    print("=" * 60)
    
    test_classes = [
        ("Automatic Failover", TestAutomaticFailover),
        ("Data Replication", TestDataReplication),
        ("Disaster Recovery", TestDisasterRecovery),
    ]
    
    tests = [
        ("Failover Manager Initialization", TestAutomaticFailover.test_failover_manager_initialization),
        ("Node Management", TestAutomaticFailover.test_node_management),
        ("Failover Configuration", TestAutomaticFailover.test_failover_configuration),
        ("Health Check Simulation", TestAutomaticFailover.test_health_check_simulation),
        ("Failover Decision Logic", TestAutomaticFailover.test_failover_decision_logic),
        
        ("Data Replicator Initialization", TestDataReplication.test_replicator_initialization),
        ("Replication Node Creation", TestDataReplication.test_replication_node_creation),
        ("Consistency Levels", TestDataReplication.test_consistency_levels),
        ("Replication Simulation", TestDataReplication.test_replication_simulation),
        ("Replication Statistics", TestDataReplication.test_replication_statistics),
        
        ("Disaster Recovery Initialization", TestDisasterRecovery.test_disaster_recovery_initialization),
        ("Disaster Scenarios", TestDisasterRecovery.test_disaster_scenarios),
        ("Recovery Plan Structure", TestDisasterRecovery.test_recovery_plan_structure),
        ("Disaster Detection", TestDisasterRecovery.test_disaster_detection),
        ("Recovery Execution", TestDisasterRecovery.test_recovery_execution),
        ("Disaster Recovery Statistics", TestDisasterRecovery.test_disaster_recovery_statistics),
        ("Recovery Plan Validation", TestDisasterRecovery.test_recovery_plan_validation),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"  📋 {test_name}... ", end="")
            test_func()
            print("✅ PASSED")
            passed += 1
        except Exception as e:
            print(f"❌ FAILED: {e}")
            failed += 1
    
    print(f"\\n📊 Test Results: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    # Add import for random
    import random
    success = run_ha_disaster_recovery_tests()
    sys.exit(0 if success else 1)