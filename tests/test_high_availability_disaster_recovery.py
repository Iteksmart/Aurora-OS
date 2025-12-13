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
    AutomaticFailoverManager, FailoverMode, FailoverStrategy, NodeState, HealthCheckType
)
from enterprise.ha_disaster_recovery.data_replication import (
    DataReplicator, ReplicationMode, ReplicationRole, ReplicationState, ConsistencyLevel
)
from enterprise.ha_disaster_recovery.disaster_recovery import (
    DisasterRecoverySystem, DisasterLevel, RecoveryPhase, RecoveryStatus, DisasterType
)

class TestAutomaticFailover:
    """Test Automatic Failover System"""
    
    def test_failover_manager_initialization(self):
        """Test failover manager initialization"""
        manager = AutomaticFailoverManager()
        
        assert manager.failover_mode == FailoverMode.AUTOMATIC
        assert manager.failover_strategy == FailoverStrategy.LEADER_FOLLOWER
        assert manager.nodes == {}
        assert manager.current_state == "normal"
        assert manager.health_check_interval == 5.0
        assert manager.failover_timeout == 30.0
    
    def test_node_registration(self):
        """Test node registration"""
        manager = AutomaticFailoverManager()
        
        # Register primary node
        primary_node = manager.register_node(
            node_id="node-1",
            name="Primary Node",
            host="192.168.1.10",
            port=8080,
            role="primary",
            priority=100
        )
        
        assert primary_node is not None
        assert primary_node.node_id == "node-1"
        assert primary_node.role == "primary"
        assert primary_node.state == NodeState.PRIMARY
        assert "node-1" in manager.nodes
        
        # Register secondary node
        secondary_node = manager.register_node(
            node_id="node-2",
            name="Secondary Node",
            host="192.168.1.11",
            port=8080,
            role="secondary",
            priority=90
        )
        
        assert secondary_node is not None
        assert secondary_node.role == "secondary"
        assert secondary_node.state == NodeState.SECONDARY
    
    def test_health_check_system(self):
        """Test health check system"""
        manager = AutomaticFailoverManager()
        
        # Add node
        manager.register_node("node-1", "Test Node", "192.168.1.10", 8080, "primary", 100)
        
        # Simulate health check
        health_result = manager.perform_health_check("node-1")
        assert health_result is not None
        assert health_result.node_id == "node-1"
        assert health_result.status in ["healthy", "unhealthy", "unknown"]
    
    def test_failover_detection(self):
        """Test failover detection"""
        manager = AutomaticFailoverManager()
        
        # Register nodes
        manager.register_node("node-1", "Primary", "192.168.1.10", 8080, "primary", 100)
        manager.register_node("node-2", "Secondary", "192.168.1.11", 8080, "secondary", 90)
        
        # Simulate primary node failure
        manager.update_node_health("node-1", "unhealthy")
        
        # Check if failover is triggered
        failover_triggered = manager.check_failover_conditions()
        assert failover_triggered == True
    
    def test_failover_execution(self):
        """Test failover execution"""
        manager = AutomaticFailoverManager()
        
        # Register nodes
        manager.register_node("node-1", "Primary", "192.168.1.10", 8080, "primary", 100)
        manager.register_node("node-2", "Secondary", "192.168.1.11", 8080, "secondary", 90)
        
        # Execute failover
        success = manager.execute_failover("node-1", "node-2", "Health check failure")
        assert success == True
        
        # Verify state changes
        assert manager.nodes["node-1"].state == NodeState.FAILED
        assert manager.nodes["node-2"].state == NodeState.PRIMARY
        assert manager.current_state == "failover_complete"

class TestDataReplication:
    """Test Data Replication System"""
    
    def test_data_replicator_initialization(self):
        """Test data replicator initialization"""
        replicator = DataReplicator("node-1", ReplicationMode.ASYNCHRONOUS)
        
        assert replicator.node_id == "node-1"
        assert replicator.replication_mode == ReplicationMode.ASYNCHRONOUS
        assert replicator.role == ReplicationRole.PRIMARY
        assert replicator.nodes == {}
        assert replicator.operation_sequence == 0
    
    def test_replication_node_management(self):
        """Test replication node management"""
        replicator = DataReplicator("node-1")
        
        # Add secondary node
        node = replicator.add_node(
            node_id="node-2",
            host="192.168.1.11",
            port=5432,
            role=ReplicationRole.SECONDARY,
            state=ReplicationState.HEALTHY
        )
        
        assert node is not None
        assert node.node_id == "node-2"
        assert node.role == ReplicationRole.SECONDARY
        assert "node-2" in replicator.nodes
    
    def test_data_replication(self):
        """Test data replication"""
        replicator = DataReplicator("node-1")
        
        # Add secondary node
        replicator.add_node("node-2", "192.168.1.11", 5432, ReplicationRole.SECONDARY, ReplicationState.HEALTHY)
        
        # Replicate data
        test_data = b"test data for replication"
        operation_id = asyncio.run(replicator.replicate_data(test_data, "write"))
        
        assert operation_id is not None
        assert operation_id in replicator.pending_operations
        assert len(replicator.pending_operations) == 1
    
    def test_consistency_levels(self):
        """Test different consistency levels"""
        replicator = DataReplicator("node-1")
        
        # Add multiple nodes
        replicator.add_node("node-2", "192.168.1.11", 5432, ReplicationRole.SECONDARY, ReplicationState.HEALTHY)
        replicator.add_node("node-3", "192.168.1.12", 5432, ReplicationRole.SECONDARY, ReplicationState.HEALTHY)
        
        # Test strong consistency
        test_data = b"strong consistency test"
        operation_id = asyncio.run(replicator.replicate_data(
            test_data, "write", 
            consistency_level=ConsistencyLevel.STRONG
        ))
        assert operation_id is not None
        
        # Test eventual consistency
        test_data2 = b"eventual consistency test"
        operation_id2 = asyncio.run(replicator.replicate_data(
            test_data2, "write",
            consistency_level=ConsistencyLevel.EVENTUAL
        ))
        assert operation_id2 is not None
    
    def test_replication_lag_monitoring(self):
        """Test replication lag monitoring"""
        replicator = DataReplicator("node-1")
        
        # Add node with simulated lag
        node = replicator.add_node("node-2", "192.168.1.11", 5432, ReplicationRole.SECONDARY, ReplicationState.HEALTHY)
        node.replication_lag = 45.0  # 45 seconds lag
        
        # Check if lag exceeds threshold
        lagging_nodes = replicator.get_lagging_nodes()
        assert "node-2" in lagging_nodes
        
        # Check if node state changes
        replicator.check_node_health()
        assert node.state == ReplicationState.LAGGING

class TestDisasterRecovery:
    """Test Disaster Recovery System"""
    
    def test_disaster_recovery_initialization(self):
        """Test disaster recovery system initialization"""
        dr_system = DisasterRecoverySystem()
        
        assert dr_system.disaster_detector is not None
        assert len(dr_system.recovery_plans) > 0  # Should have default plans
        assert len(dr_system.recovery_executions) == 0
        assert dr_system.running == False
    
    def test_disaster_detection_rules(self):
        """Test disaster detection rules"""
        dr_system = DisasterRecoverySystem()
        
        # Check if default rules exist
        assert len(dr_system.disaster_detector.detection_rules) > 0
        assert "service_failure" in dr_system.disaster_detector.detection_rules
        assert "node_failure" in dr_system.disaster_detector.detection_rules
        assert "network_partition" in dr_system.disaster_detector.detection_rules
    
    def test_recovery_plans(self):
        """Test recovery plans"""
        dr_system = DisasterRecoverySystem()
        
        plans = dr_system.get_recovery_plans()
        assert len(plans) >= 3  # Should have at least 3 default plans
        
        # Check specific plans
        plan_ids = [plan.id for plan in plans]
        assert "service_failure_plan" in plan_ids
        assert "node_failure_plan" in plan_ids
        assert "datacenter_outage_plan" in plan_ids
    
    def test_disaster_event_creation(self):
        """Test disaster event creation"""
        dr_system = DisasterRecoverySystem()
        
        # Simulate disaster detection
        detected_events = asyncio.run(dr_system.disaster_detector.detect_disasters())
        
        # Events might be detected based on random conditions
        assert isinstance(detected_events, list)
    
    def test_recovery_execution(self):
        """Test recovery execution"""
        dr_system = DisasterRecoverySystem()
        
        # Create mock disaster event
        mock_event = Mock()
        mock_event.title = "Test Service Failure"
        mock_event.disaster_type = DisasterType.SOFTWARE_BUG
        mock_event.level = DisasterLevel.MINOR
        
        # Find appropriate recovery plan
        plan = dr_system._find_recovery_plan(mock_event)
        assert plan is not None
        assert plan.id == "service_failure_plan"
        
        # Initiate recovery
        execution_id = asyncio.run(dr_system.initiate_recovery(mock_event, plan))
        assert execution_id is not None
        assert execution_id in dr_system.recovery_executions
        
        # Check execution status
        execution = dr_system.get_recovery_status(execution_id)
        assert execution is not None
        assert execution.status == RecoveryStatus.IN_PROGRESS
        assert execution.disaster_event == mock_event
        assert execution.recovery_plan == plan
    
    def test_recovery_plan_steps(self):
        """Test recovery plan steps"""
        dr_system = DisasterRecoverySystem()
        
        # Get service failure plan
        plan = dr_system.recovery_plans["service_failure_plan"]
        
        assert len(plan.steps) > 0
        
        # Check step phases
        phases = {step.phase for step in plan.steps}
        assert RecoveryPhase.DETECTION in phases
        assert RecoveryPhase.RECOVERY in phases
        assert RecoveryPhase.VERIFICATION in phases
        
        # Check step order
        assert all(step.order >= 1 for step in plan.steps)
    
    def test_disaster_recovery_statistics(self):
        """Test disaster recovery statistics"""
        dr_system = DisasterRecoverySystem()
        
        stats = dr_system.get_statistics()
        
        assert "disasters_detected" in stats
        assert "recoveries_executed" in stats
        assert "successful_recoveries" in stats
        assert "failed_recoveries" in stats
        assert "average_recovery_time" in stats
        
        # Initial values should be zero
        assert stats["disasters_detected"] == 0
        assert stats["recoveries_executed"] == 0
        assert stats["successful_recoveries"] == 0
        assert stats["failed_recoveries"] == 0

# Test runner function
def run_high_availability_disaster_recovery_tests():
    """Run all high availability and disaster recovery tests"""
    print("🛡️ Running High Availability & Disaster Recovery Tests")
    print("=" * 60)
    
    test_classes = [
        ("Automatic Failover", TestAutomaticFailover),
        ("Data Replication", TestDataReplication),
        ("Disaster Recovery", TestDisasterRecovery),
    ]
    
    tests = [
        ("Failover Manager Init", lambda: TestAutomaticFailover().test_failover_manager_initialization()),
        ("Node Registration", lambda: TestAutomaticFailover().test_node_registration()),
        ("Health Check System", lambda: TestAutomaticFailover().test_health_check_system()),
        ("Failover Detection", lambda: TestAutomaticFailover().test_failover_detection()),
        ("Failover Execution", lambda: TestAutomaticFailover().test_failover_execution()),
        ("Data Replicator Init", lambda: TestDataReplication().test_data_replicator_initialization()),
        ("Replication Node Mgmt", lambda: TestDataReplication().test_replication_node_management()),
        ("Data Replication", lambda: TestDataReplication().test_data_replication()),
        ("Consistency Levels", lambda: TestDataReplication().test_consistency_levels()),
        ("Replication Lag Monitoring", lambda: TestDataReplication().test_replication_lag_monitoring()),
        ("DR System Init", lambda: TestDisasterRecovery().test_disaster_recovery_initialization()),
        ("Disaster Detection Rules", lambda: TestDisasterRecovery().test_disaster_detection_rules()),
        ("Recovery Plans", lambda: TestDisasterRecovery().test_recovery_plans()),
        ("Disaster Event Creation", lambda: TestDisasterRecovery().test_disaster_event_creation()),
        ("Recovery Execution", lambda: TestDisasterRecovery().test_recovery_execution()),
        ("Recovery Plan Steps", lambda: TestDisasterRecovery().test_recovery_plan_steps()),
        ("DR Statistics", lambda: TestDisasterRecovery().test_disaster_recovery_statistics()),
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
    # Add missing import for random
    import random
    run_high_availability_disaster_recovery_tests()