"""
Aurora OS Automatic Failover System
Advanced automatic failover mechanisms for high availability
"""

import asyncio
import json
import logging
import time
import uuid
import random
from typing import Dict, List, Optional, Any, Set, Tuple, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
from concurrent.futures import ThreadPoolExecutor

class FailoverMode(Enum):
    """Failover modes"""
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    SEMI_AUTOMATIC = "semi_automatic"

class FailoverStrategy(Enum):
    """Failover strategies"""
    ACTIVE_PASSIVE = "active_passive"
    ACTIVE_ACTIVE = "active_active"
    MULTI_MASTER = "multi_master"
    LEADER_FOLLOWER = "leader_follower"

class NodeState(Enum):
    """Node states"""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    STANDBY = "standby"
    FAILED = "failed"
    RECOVERING = "recovering"
    MAINTENANCE = "maintenance"

class HealthCheckType(Enum):
    """Health check types"""
    HEARTBEAT = "heartbeat"
    HTTP = "http"
    TCP = "tcp"
    DATABASE = "database"
    CUSTOM = "custom"

@dataclass
class HealthCheckResult:
    """Health check result"""
    node_id: str
    check_type: HealthCheckType
    status: str
    response_time: float
    timestamp: datetime
    error_message: Optional[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "node_id": self.node_id,
            "check_type": self.check_type.value,
            "status": self.status,
            "response_time": self.response_time,
            "timestamp": self.timestamp.isoformat(),
            "error_message": self.error_message,
            "metadata": self.metadata
        }

@dataclass
class FailoverEvent:
    """Failover event"""
    id: str
    timestamp: datetime
    primary_node: str
    secondary_node: str
    reason: str
    strategy: FailoverStrategy
    triggered_by: str
    status: str
    completion_time: Optional[datetime]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "primary_node": self.primary_node,
            "secondary_node": self.secondary_node,
            "reason": self.reason,
            "strategy": self.strategy.value,
            "triggered_by": self.triggered_by,
            "status": self.status,
            "completion_time": self.completion_time.isoformat() if self.completion_time else None,
            "metadata": self.metadata
        }

@dataclass
class Node:
    """Cluster node"""
    id: str
    name: str
    host: str
    port: int
    state: NodeState
    priority: int
    capabilities: Set[str]
    health_score: float
    last_heartbeat: datetime
    health_history: deque
    failover_count: int
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        """Post-initialization"""
        if self.capabilities is None:
            self.capabilities = set()
        if self.health_history is None:
            self.health_history = deque(maxlen=100)
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def is_healthy(self) -> bool:
        """Check if node is healthy"""
        if not self.health_history:
            return True
        
        recent_checks = [
            check for check in self.health_history
            if datetime.now() - check.timestamp < timedelta(seconds=60)
        ]
        
        if not recent_checks:
            return False
        
        success_rate = sum(1 for check in recent_checks if check.status == "healthy") / len(recent_checks)
        return success_rate >= 0.8
    
    @property
    def average_response_time(self) -> float:
        """Get average response time"""
        if not self.health_history:
            return 0.0
        
        recent_checks = [
            check for check in self.health_history
            if datetime.now() - check.timestamp < timedelta(seconds=300)
        ]
        
        if not recent_checks:
            return 0.0
        
        return sum(check.response_time for check in recent_checks) / len(recent_checks)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "state": self.state.value,
            "priority": self.priority,
            "capabilities": list(self.capabilities),
            "health_score": self.health_score,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "failover_count": self.failover_count,
            "metadata": self.metadata,
            "is_healthy": self.is_healthy,
            "average_response_time": self.average_response_time
        }

class HealthChecker:
    """Health checking service"""
    
    def __init__(self, check_interval: float = 10.0, timeout: float = 5.0):
        self.logger = logging.getLogger(__name__)
        self.check_interval = check_interval
        self.timeout = timeout
        self.running = False
        self.task = None
        
        # Health check functions
        self.check_functions = {
            HealthCheckType.HEARTBEAT: self._check_heartbeat,
            HealthCheckType.HTTP: self._check_http,
            HealthCheckType.TCP: self._check_tcp,
            HealthCheckType.DATABASE: self._check_database,
            HealthCheckType.CUSTOM: self._check_custom
        }
    
    async def start(self):
        """Start health checker"""
        self.running = True
        self.task = asyncio.create_task(self._health_check_loop())
        self.logger.info("Health checker started")
    
    async def stop(self):
        """Stop health checker"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        self.logger.info("Health checker stopped")
    
    async def _health_check_loop(self):
        """Main health check loop"""
        while self.running:
            # Health checks will be performed by AutomaticFailover
            await asyncio.sleep(self.check_interval)
    
    async def check_node(self, node: Node, check_types: List[HealthCheckType]) -> List[HealthCheckResult]:
        """Perform health checks on a node"""
        results = []
        
        for check_type in check_types:
            try:
                check_func = self.check_functions.get(check_type)
                if check_func:
                    result = await check_func(node)
                    results.append(result)
                else:
                    self.logger.warning(f"Unknown health check type: {check_type}")
            except Exception as e:
                self.logger.error(f"Health check failed for {check_type} on node {node.id}: {e}")
                results.append(HealthCheckResult(
                    node_id=node.id,
                    check_type=check_type,
                    status="error",
                    response_time=0.0,
                    timestamp=datetime.now(),
                    error_message=str(e),
                    metadata={}
                ))
        
        return results
    
    async def _check_heartbeat(self, node: Node) -> HealthCheckResult:
        """Check node heartbeat"""
        start_time = time.time()
        
        try:
            # Simulate heartbeat check
            await asyncio.sleep(random.uniform(0.1, 1.0))
            
            response_time = time.time() - start_time
            
            # Simulate occasional failures
            if random.random() < 0.05:  # 5% failure rate
                return HealthCheckResult(
                    node_id=node.id,
                    check_type=HealthCheckType.HEARTBEAT,
                    status="unhealthy",
                    response_time=response_time,
                    timestamp=datetime.now(),
                    error_message="Heartbeat timeout",
                    metadata={}
                )
            
            return HealthCheckResult(
                node_id=node.id,
                check_type=HealthCheckType.HEARTBEAT,
                status="healthy",
                response_time=response_time,
                timestamp=datetime.now(),
                error_message=None,
                metadata={}
            )
        
        except Exception as e:
            return HealthCheckResult(
                node_id=node.id,
                check_type=HealthCheckType.HEARTBEAT,
                status="error",
                response_time=time.time() - start_time,
                timestamp=datetime.now(),
                error_message=str(e),
                metadata={}
            )
    
    async def _check_http(self, node: Node) -> HealthCheckResult:
        """Check HTTP endpoint"""
        start_time = time.time()
        
        try:
            # Simulate HTTP check
            await asyncio.sleep(random.uniform(0.2, 1.5))
            
            response_time = time.time() - start_time
            
            # Simulate occasional failures
            if random.random() < 0.08:  # 8% failure rate
                return HealthCheckResult(
                    node_id=node.id,
                    check_type=HealthCheckType.HTTP,
                    status="unhealthy",
                    response_time=response_time,
                    timestamp=datetime.now(),
                    error_message="HTTP endpoint not responding",
                    metadata={}
                )
            
            return HealthCheckResult(
                node_id=node.id,
                check_type=HealthCheckType.HTTP,
                status="healthy",
                response_time=response_time,
                timestamp=datetime.now(),
                error_message=None,
                metadata={}
            )
        
        except Exception as e:
            return HealthCheckResult(
                node_id=node.id,
                check_type=HealthCheckType.HTTP,
                status="error",
                response_time=time.time() - start_time,
                timestamp=datetime.now(),
                error_message=str(e),
                metadata={}
            )
    
    async def _check_tcp(self, node: Node) -> HealthCheckResult:
        """Check TCP connection"""
        start_time = time.time()
        
        try:
            # Simulate TCP check
            await asyncio.sleep(random.uniform(0.05, 0.5))
            
            response_time = time.time() - start_time
            
            return HealthCheckResult(
                node_id=node.id,
                check_type=HealthCheckType.TCP,
                status="healthy",
                response_time=response_time,
                timestamp=datetime.now(),
                error_message=None,
                metadata={}
            )
        
        except Exception as e:
            return HealthCheckResult(
                node_id=node.id,
                check_type=HealthCheckType.TCP,
                status="error",
                response_time=time.time() - start_time,
                timestamp=datetime.now(),
                error_message=str(e),
                metadata={}
            )
    
    async def _check_database(self, node: Node) -> HealthCheckResult:
        """Check database connection"""
        start_time = time.time()
        
        try:
            # Simulate database check
            await asyncio.sleep(random.uniform(0.3, 2.0))
            
            response_time = time.time() - start_time
            
            # Simulate occasional failures
            if random.random() < 0.06:  # 6% failure rate
                return HealthCheckResult(
                    node_id=node.id,
                    check_type=HealthCheckType.DATABASE,
                    status="unhealthy",
                    response_time=response_time,
                    timestamp=datetime.now(),
                    error_message="Database connection failed",
                    metadata={}
                )
            
            return HealthCheckResult(
                node_id=node.id,
                check_type=HealthCheckType.DATABASE,
                status="healthy",
                response_time=response_time,
                timestamp=datetime.now(),
                error_message=None,
                metadata={}
            )
        
        except Exception as e:
            return HealthCheckResult(
                node_id=node.id,
                check_type=HealthCheckType.DATABASE,
                status="error",
                response_time=time.time() - start_time,
                timestamp=datetime.now(),
                error_message=str(e),
                metadata={}
            )
    
    async def _check_custom(self, node: Node) -> HealthCheckResult:
        """Custom health check"""
        start_time = time.time()
        
        try:
            # Simulate custom check
            await asyncio.sleep(random.uniform(0.1, 1.0))
            
            response_time = time.time() - start_time
            
            return HealthCheckResult(
                node_id=node.id,
                check_type=HealthCheckType.CUSTOM,
                status="healthy",
                response_time=response_time,
                timestamp=datetime.now(),
                error_message=None,
                metadata={}
            )
        
        except Exception as e:
            return HealthCheckResult(
                node_id=node.id,
                check_type=HealthCheckType.CUSTOM,
                status="error",
                response_time=time.time() - start_time,
                timestamp=datetime.now(),
                error_message=str(e),
                metadata={}
            )

class AutomaticFailover:
    """Automatic failover system"""
    
    def __init__(self, strategy: FailoverStrategy = FailoverStrategy.ACTIVE_PASSIVE):
        self.logger = logging.getLogger(__name__)
        self.strategy = strategy
        self.nodes: Dict[str, Node] = {}
        self.primary_node: Optional[str] = None
        self.health_checker = HealthChecker()
        self.failover_events: List[FailoverEvent] = []
        
        # Configuration
        self.health_check_interval = 10.0
        self.failover_threshold = 3  # Number of consecutive failures
        self.recovery_check_interval = 30.0
        
        # State
        self.running = False
        self.task = None
        
        # Event callbacks
        self.on_failover: Optional[Callable[[FailoverEvent], None]] = None
        self.on_recovery: Optional[Callable[[str], None]] = None
    
    async def start(self):
        """Start automatic failover system"""
        self.running = True
        await self.health_checker.start()
        self.task = asyncio.create_task(self._failover_monitor_loop())
        self.logger.info(f"Automatic failover system started with strategy: {self.strategy.value}")
    
    async def stop(self):
        """Stop automatic failover system"""
        self.running = False
        await self.health_checker.stop()
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        self.logger.info("Automatic failover system stopped")
    
    def add_node(self, node: Node):
        """Add node to cluster"""
        self.nodes[node.id] = node
        
        # Set first node as primary if none exists
        if self.primary_node is None and node.state == NodeState.PRIMARY:
            self.primary_node = node.id
        
        self.logger.info(f"Added node {node.name} ({node.id}) to cluster")
    
    def remove_node(self, node_id: str):
        """Remove node from cluster"""
        if node_id in self.nodes:
            node = self.nodes[node_id]
            del self.nodes[node_id]
            
            # Handle primary removal
            if self.primary_node == node_id:
                self.primary_node = None
                # Trigger failover to select new primary
                asyncio.create_task(self._trigger_failover("Primary node removed"))
            
            self.logger.info(f"Removed node {node.name} ({node_id}) from cluster")
    
    async def _failover_monitor_loop(self):
        """Main failover monitoring loop"""
        while self.running:
            try:
                await self._perform_health_checks()
                await self._check_failover_conditions()
                await self._check_recovery_conditions()
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                self.logger.error(f"Error in failover monitor loop: {e}")
                await asyncio.sleep(5)
    
    async def _perform_health_checks(self):
        """Perform health checks on all nodes"""
        check_types = [HealthCheckType.HEARTBEAT, HealthCheckType.HTTP, HealthCheckType.TCP]
        
        for node in self.nodes.values():
            if node.state != NodeState.FAILED:
                results = await self.health_checker.check_node(node, check_types)
                
                # Update node health history
                for result in results:
                    node.health_history.append(result)
                
                # Update health score
                node.health_score = self._calculate_health_score(node)
                node.last_heartbeat = datetime.now()
    
    def _calculate_health_score(self, node: Node) -> float:
        """Calculate node health score"""
        if not node.health_history:
            return 1.0
        
        recent_checks = [
            check for check in node.health_history
            if datetime.now() - check.timestamp < timedelta(seconds=60)
        ]
        
        if not recent_checks:
            return 0.0
        
        # Calculate success rate
        success_rate = sum(1 for check in recent_checks if check.status == "healthy") / len(recent_checks)
        
        # Calculate response time factor (lower is better)
        avg_response_time = sum(check.response_time for check in recent_checks) / len(recent_checks)
        response_factor = max(0, 1 - (avg_response_time / 5.0))  # Normalize to 5 seconds
        
        # Combine factors
        health_score = (success_rate * 0.7) + (response_factor * 0.3)
        
        return min(1.0, max(0.0, health_score))
    
    async def _check_failover_conditions(self):
        """Check if failover conditions are met"""
        if not self.primary_node:
            # No primary node, trigger failover
            await self._trigger_failover("No primary node available")
            return
        
        primary = self.nodes.get(self.primary_node)
        if not primary:
            await self._trigger_failover("Primary node not found")
            return
        
        # Check if primary is unhealthy
        if not primary.is_healthy or primary.health_score < 0.5:
            consecutive_failures = self._count_consecutive_failures(primary)
            
            if consecutive_failures >= self.failover_threshold:
                await self._trigger_failover(f"Primary node {primary.name} is unhealthy")
    
    def _count_consecutive_failures(self, node: Node) -> int:
        """Count consecutive health check failures"""
        if not node.health_history:
            return 0
        
        failures = 0
        for check in reversed(node.health_history):
            if check.status == "healthy":
                break
            failures += 1
        
        return failures
    
    async def _trigger_failover(self, reason: str):
        """Trigger failover process"""
        self.logger.warning(f"Triggering failover: {reason}")
        
        # Select new primary
        new_primary = self._select_new_primary()
        if not new_primary:
            self.logger.error("No suitable primary node found for failover")
            return
        
        old_primary = self.primary_node
        
        # Create failover event
        failover_event = FailoverEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            primary_node=old_primary or "unknown",
            secondary_node=new_primary,
            reason=reason,
            strategy=self.strategy,
            triggered_by="automatic",
            status="in_progress",
            completion_time=None,
            metadata={}
        )
        
        self.failover_events.append(failover_event)
        
        # Perform failover
        await self._perform_failover(old_primary, new_primary, failover_event)
    
    def _select_new_primary(self) -> Optional[str]:
        """Select new primary node"""
        candidates = [
            node for node in self.nodes.values()
            if node.state in [NodeState.SECONDARY, NodeState.STANDBY]
            and node.is_healthy
        ]
        
        if not candidates:
            return None
        
        # Sort by priority (higher first) and health score
        candidates.sort(key=lambda n: (n.priority, n.health_score), reverse=True)
        
        return candidates[0].id
    
    async def _perform_failover(self, old_primary: Optional[str], new_primary: str, event: FailoverEvent):
        """Perform the actual failover"""
        try:
            self.logger.info(f"Performing failover from {old_primary} to {new_primary}")
            
            # Update old primary state
            if old_primary and old_primary in self.nodes:
                self.nodes[old_primary].state = NodeState.FAILED
            
            # Update new primary state
            if new_primary in self.nodes:
                self.nodes[new_primary].state = NodeState.PRIMARY
                self.nodes[new_primary].failover_count += 1
            
            # Update primary reference
            self.primary_node = new_primary
            
            # Update event
            event.status = "completed"
            event.completion_time = datetime.now()
            
            self.logger.info(f"Failover completed: {new_primary} is now primary")
            
            # Trigger callback
            if self.on_failover:
                self.on_failover(event)
            
        except Exception as e:
            self.logger.error(f"Failover failed: {e}")
            event.status = "failed"
            event.completion_time = datetime.now()
    
    async def _check_recovery_conditions(self):
        """Check if failed nodes can be recovered"""
        for node_id, node in self.nodes.items():
            if node.state == NodeState.FAILED and node.is_healthy:
                self.logger.info(f"Node {node.name} ({node_id}) is healthy again, marking as recovering")
                node.state = NodeState.RECOVERING
                
                # Trigger recovery callback
                if self.on_recovery:
                    self.on_recovery(node_id)
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status"""
        nodes_status = {node_id: node.to_dict() for node_id, node in self.nodes.items()}
        
        return {
            "strategy": self.strategy.value,
            "primary_node": self.primary_node,
            "total_nodes": len(self.nodes),
            "healthy_nodes": sum(1 for node in self.nodes.values() if node.is_healthy),
            "failed_nodes": sum(1 for node in self.nodes.values() if node.state == NodeState.FAILED),
            "nodes": nodes_status,
            "recent_failovers": [event.to_dict() for event in self.failover_events[-10:]]
        }

# Example usage
async def main():
    """Example usage of automatic failover system"""
    failover = AutomaticFailover(FailoverStrategy.ACTIVE_PASSIVE)
    
    # Add nodes
    nodes = [
        Node(
            id="node-1",
            name="primary-server",
            host="192.168.1.10",
            port=8080,
            state=NodeState.PRIMARY,
            priority=100,
            capabilities={"web", "database"},
            health_score=1.0,
            last_heartbeat=datetime.now(),
            health_history=deque(maxlen=100),
            failover_count=0,
            metadata={}
        ),
        Node(
            id="node-2",
            name="secondary-server",
            host="192.168.1.11",
            port=8080,
            state=NodeState.SECONDARY,
            priority=90,
            capabilities={"web", "database"},
            health_score=1.0,
            last_heartbeat=datetime.now(),
            health_history=deque(maxlen=100),
            failover_count=0,
            metadata={}
        ),
        Node(
            id="node-3",
            name="standby-server",
            host="192.168.1.12",
            port=8080,
            state=NodeState.STANDBY,
            priority=80,
            capabilities={"web"},
            health_score=1.0,
            last_heartbeat=datetime.now(),
            health_history=deque(maxlen=100),
            failover_count=0,
            metadata={}
        )
    ]
    
    for node in nodes:
        failover.add_node(node)
    
    def on_failover(event):
        print(f"FAILOVER: {event.reason}")
        print(f"From: {event.primary_node} To: {event.secondary_node}")
    
    def on_recovery(node_id):
        print(f"RECOVERY: Node {node_id} has recovered")
    
    failover.on_failover = on_failover
    failover.on_recovery = on_recovery
    
    # Start failover system
    await failover.start()
    
    # Run for monitoring
    try:
        while True:
            status = failover.get_cluster_status()
            print(f"Cluster Status: {status['total_nodes']} nodes, {status['healthy_nodes']} healthy")
            print(f"Primary: {status['primary_node']}")
            await asyncio.sleep(30)
    except KeyboardInterrupt:
        print("\\nShutting down failover system...")
        await failover.stop()

if __name__ == "__main__":
    asyncio.run(main())