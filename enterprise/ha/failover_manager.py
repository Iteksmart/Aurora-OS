"""
Aurora OS High Availability Failover Manager
Automatic failover mechanisms for Aurora OS enterprise deployment
"""

import asyncio
import json
import logging
import time
import uuid
import socket
from typing import Dict, List, Optional, Any, Set, Tuple, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
from concurrent.futures import ThreadPoolExecutor

class FailoverMode(Enum):
    """Failover modes"""
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    HEALTH_BASED = "health_based"

class FailoverState(Enum):
    """Failover states"""
    NORMAL = "normal"
    DEGRADED = "degraded"
    FAILOVER_IN_PROGRESS = "failover_in_progress"
    FAILOVER_COMPLETE = "failover_complete"
    RECOVERY_IN_PROGRESS = "recovery_in_progress"
    RECOVERY_COMPLETE = "recovery_complete"

class NodeRole(Enum):
    """Node roles for failover"""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    BACKUP = "backup"
    STANDBY = "standby"
    HOT_SPARE = "hot_spare"

class HealthStatus(Enum):
    """Node health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    MAINTENANCE = "maintenance"

@dataclass
class FailoverNode:
    """Failover node information"""
    node_id: str
    name: str
    host: str
    port: int
    role: NodeRole
    health_status: HealthStatus
    last_heartbeat: datetime
    health_score: float
    capabilities: Dict[str, Any]
    resource_usage: Dict[str, float]
    network_latency: float
    is_active: bool
    is_primary: bool
    failover_priority: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "node_id": self.node_id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "role": self.role.value,
            "health_status": self.health_status.value,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "health_score": self.health_score,
            "capabilities": self.capabilities,
            "resource_usage": self.resource_usage,
            "network_latency": self.network_latency,
            "is_active": self.is_active,
            "is_primary": self.is_primary,
            "failover_priority": self.failover_priority
        }

@dataclass
class FailoverEvent:
    """Failover event"""
    event_id: str
    event_type: str
    trigger_node: str
    target_node: str
    old_state: FailoverState
    new_state: FailoverState
    timestamp: datetime
    reason: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "trigger_node": self.trigger_node,
            "target_node": self.target_node,
            "old_state": self.old_state.value,
            "new_state": self.new_state.value,
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason,
            "metadata": self.metadata
        }

@dataclass
class FailoverConfig:
    """Failover configuration"""
    heartbeat_interval: float = 5.0
    heartbeat_timeout: float = 15.0
    health_check_interval: float = 10.0
    failover_timeout: float = 30.0
    max_consecutive_failures: int = 3
    failover_mode: FailoverMode = FailoverMode.AUTOMATIC
    auto_recovery_enabled: bool = True
    recovery_delay: float = 300.0
    quorum_size: int = 2
    priority_weights: Dict[str, float] = None
    health_thresholds: Dict[str, float] = None
    
    def __post_init__(self):
        """Initialize default values"""
        if self.priority_weights is None:
            self.priority_weights = {
                "health_score": 0.4,
                "resource_usage": 0.2,
                "network_latency": 0.2,
                "node_role": 0.2
            }
        
        if self.health_thresholds is None:
            self.health_thresholds = {
                "cpu_usage": 80.0,
                "memory_usage": 85.0,
                "disk_usage": 90.0,
                "network_latency": 100.0,
                "error_rate": 5.0
            }

class HealthChecker:
    """Health checker for nodes"""
    
    def __init__(self, config: FailoverConfig):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.health_checks: Dict[str, Dict[str, Any]] = {}
        self.last_checks: Dict[str, datetime] = {}
    
    async def check_node_health(self, node: FailoverNode) -> Tuple[HealthStatus, float]:
        """Check health of a node"""
        try:
            # Basic connectivity check
            start_time = time.time()
            is_connected = await self._check_connectivity(node.host, node.port)
            if not is_connected:
                return HealthStatus.UNHEALTHY, 0.0
            
            # Resource usage check
            resource_metrics = await self._check_resource_usage(node.host, node.port)
            resource_score = self._calculate_resource_score(resource_metrics)
            
            # Service health check
            service_health = await self._check_service_health(node.host, node.port)
            service_score = self._calculate_service_score(service_health)
            
            # Network latency
            latency = (time.time() - start_time) * 1000  # Convert to ms
            latency_score = self._calculate_latency_score(latency)
            
            # Overall health score
            overall_score = (
                resource_score * 0.4 +
                service_score * 0.4 +
                latency_score * 0.2
            )
            
            # Determine health status
            if overall_score >= 0.8:
                status = HealthStatus.HEALTHY
            elif overall_score >= 0.6:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY
            
            return status, overall_score
            
        except Exception as e:
            self.logger.error(f"Health check failed for node {node.node_id}: {e}")
            return HealthStatus.UNKNOWN, 0.0
    
    async def _check_connectivity(self, host: str, port: int) -> bool:
        """Check basic TCP connectivity"""
        try:
            future = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(future, timeout=5.0)
            writer.close()
            await writer.wait_closed()
            return True
        except:
            return False
    
    async def _check_resource_usage(self, host: str, port: int) -> Dict[str, float]:
        """Check resource usage metrics"""
        # Simulated resource check - in real implementation, this would
        # connect to node's monitoring endpoint
        return {
            "cpu_usage": 45.0,
            "memory_usage": 60.0,
            "disk_usage": 30.0,
            "network_io": 1000.0
        }
    
    async def _check_service_health(self, host: str, port: int) -> Dict[str, Any]:
        """Check service health"""
        # Simulated service health check
        return {
            "services_running": 5,
            "services_total": 5,
            "response_time": 50.0,
            "error_rate": 1.0
        }
    
    def _calculate_resource_score(self, metrics: Dict[str, float]) -> float:
        """Calculate resource health score"""
        score = 1.0
        
        for metric, threshold in self.config.health_thresholds.items():
            if metric in metrics:
                usage = metrics[metric]
                if usage > threshold:
                    score *= 0.8
        
        return max(0.0, score)
    
    def _calculate_service_score(self, health: Dict[str, Any]) -> float:
        """Calculate service health score"""
        running = health.get("services_running", 0)
        total = health.get("services_total", 1)
        error_rate = health.get("error_rate", 0)
        
        service_score = running / total if total > 0 else 0.0
        error_score = max(0.0, 1.0 - (error_rate / 100.0))
        
        return (service_score + error_score) / 2.0
    
    def _calculate_latency_score(self, latency_ms: float) -> float:
        """Calculate latency score"""
        threshold = self.config.health_thresholds.get("network_latency", 100.0)
        return max(0.0, 1.0 - (latency_ms / threshold))

class FailoverManager:
    """Main failover manager"""
    
    def __init__(self, node_id: str, config: FailoverConfig):
        self.logger = logging.getLogger(__name__)
        self.node_id = node_id
        self.config = config
        
        # Failover state
        self.current_state = FailoverState.NORMAL
        self.current_primary: Optional[str] = None
        self.failover_history: deque = deque(maxlen=1000)
        
        # Node management
        self.nodes: Dict[str, FailoverNode] = {}
        self.node_heartbeat: Dict[str, datetime] = {}
        self.node_health: Dict[str, Tuple[HealthStatus, float]] = {}
        
        # Health checker
        self.health_checker = HealthChecker(config)
        
        # Background tasks
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.health_check_task: Optional[asyncio.Task] = None
        self.failover_task: Optional[asyncio.Task] = None
        
        # Event callbacks
        self.on_failover: Optional[Callable] = None
        self.on_recovery: Optional[Callable] = None
        self.on_state_change: Optional[Callable] = None
        
        # Statistics
        self.stats = {
            "failovers_initiated": 0,
            "failovers_completed": 0,
            "recoveries_completed": 0,
            "false_alarms": 0,
            "average_failover_time": 0.0
        }
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        # Running flag
        self._running = False
    
    async def start(self):
        """Start failover manager"""
        self.logger.info(f"Starting failover manager for node {self.node_id}")
        
        self._running = True
        
        # Start background tasks
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        self.failover_task = asyncio.create_task(self._failover_monitor_loop())
        
        self.logger.info("Failover manager started")
    
    async def stop(self):
        """Stop failover manager"""
        self.logger.info("Stopping failover manager")
        
        self._running = False
        
        # Cancel background tasks
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        if self.health_check_task:
            self.health_check_task.cancel()
        if self.failover_task:
            self.failover_task.cancel()
        
        self.logger.info("Failover manager stopped")
    
    def add_node(self, node: FailoverNode):
        """Add node to failover cluster"""
        with self._lock:
            self.nodes[node.node_id] = node
            self.node_heartbeat[node.node_id] = datetime.now()
            
            # Set initial primary if none exists
            if self.current_primary is None and node.role == NodeRole.PRIMARY:
                self.current_primary = node.node_id
                node.is_primary = True
            
            self.logger.info(f"Added node {node.node_id} to failover cluster")
    
    def remove_node(self, node_id: str):
        """Remove node from failover cluster"""
        with self._lock:
            if node_id in self.nodes:
                del self.nodes[node_id]
                del self.node_heartbeat[node_id]
                if node_id in self.node_health:
                    del self.node_health[node_id]
                
                # Update primary if removed node was primary
                if self.current_primary == node_id:
                    self.current_primary = None
                    # Promote another node to primary
                    self._promote_new_primary()
                
                self.logger.info(f"Removed node {node_id} from failover cluster")
    
    async def _heartbeat_loop(self):
        """Heartbeat loop"""
        while self._running:
            try:
                await asyncio.sleep(self.config.heartbeat_interval)
                await self._send_heartbeat()
                await self._check_heartbeat_timeouts()
            except Exception as e:
                self.logger.error(f"Error in heartbeat loop: {e}")
    
    async def _health_check_loop(self):
        """Health check loop"""
        while self._running:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._perform_health_checks()
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
    
    async def _failover_monitor_loop(self):
        """Failover monitoring loop"""
        while self._running:
            try:
                await asyncio.sleep(1.0)
                await self._monitor_failover_conditions()
            except Exception as e:
                self.logger.error(f"Error in failover monitor loop: {e}")
    
    async def _send_heartbeat(self):
        """Send heartbeat to all nodes"""
        current_time = datetime.now()
        
        for node_id, node in self.nodes.items():
            if node.is_active:
                try:
                    # Simulate sending heartbeat
                    self.node_heartbeat[node_id] = current_time
                    self.logger.debug(f"Sent heartbeat to node {node_id}")
                except Exception as e:
                    self.logger.error(f"Failed to send heartbeat to {node_id}: {e}")
    
    async def _check_heartbeat_timeouts(self):
        """Check for heartbeat timeouts"""
        current_time = datetime.now()
        timeout_threshold = timedelta(seconds=self.config.heartbeat_timeout)
        
        for node_id, last_heartbeat in self.node_heartbeat.items():
            if current_time - last_heartbeat > timeout_threshold:
                node = self.nodes.get(node_id)
                if node and node.is_active:
                    self.logger.warning(f"Heartbeat timeout for node {node_id}")
                    await self._handle_node_failure(node_id)
    
    async def _perform_health_checks(self):
        """Perform health checks on all active nodes"""
        for node_id, node in self.nodes.items():
            if node.is_active:
                try:
                    health_status, health_score = await self.health_checker.check_node_health(node)
                    
                    # Update node health
                    self.node_health[node_id] = (health_status, health_score)
                    node.health_status = health_status
                    node.health_score = health_score
                    node.last_heartbeat = datetime.now()
                    
                    self.logger.debug(f"Health check for {node_id}: {health_status.value} ({health_score:.2f})")
                    
                    # Check if node needs failover
                    if health_status == HealthStatus.UNHEALTHY:
                        await self._handle_unhealthy_node(node_id, health_status)
                
                except Exception as e:
                    self.logger.error(f"Health check failed for node {node_id}: {e}")
    
    async def _monitor_failover_conditions(self):
        """Monitor for failover conditions"""
        with self._lock:
            if self.current_state not in [FailoverState.NORMAL, FailoverState.DEGRADED]:
                return
        
        # Check if primary is unhealthy
        if self.current_primary:
            primary_node = self.nodes.get(self.current_primary)
            if primary_node:
                health_status, health_score = self.node_health.get(self.current_primary, (HealthStatus.UNKNOWN, 0.0))
                
                if health_status in [HealthStatus.UNHEALTHY, HealthStatus.UNKNOWN]:
                    self.logger.warning(f"Primary node {self.current_primary} is {health_status.value}")
                    await self._initiate_failover(f"Primary node {self.current_primary} is {health_status.value}")
    
    async def _handle_node_failure(self, node_id: str):
        """Handle node failure"""
        node = self.nodes.get(node_id)
        if not node:
            return
        
        self.logger.error(f"Node {node_id} failed")
        
        # Mark node as inactive
        node.is_active = False
        node.health_status = HealthStatus.UNHEALTHY
        
        # Initiate failover if this was primary
        if node.is_primary:
            await self._initiate_failover(f"Primary node {node_id} failed")
    
    async def _handle_unhealthy_node(self, node_id: str, health_status: HealthStatus):
        """Handle unhealthy node"""
        if self.config.failover_mode != FailoverMode.AUTOMATIC:
            return
        
        node = self.nodes.get(node_id)
        if not node or not node.is_primary:
            return
        
        # Check if we have consecutive failures
        consecutive_failures = self._get_consecutive_failures(node_id)
        if consecutive_failures >= self.config.max_consecutive_failures:
            await self._initiate_failover(f"Primary node {node_id} has {consecutive_failures} consecutive health failures")
    
    def _get_consecutive_failures(self, node_id: str) -> int:
        """Get number of consecutive failures for node"""
        # Simplified - in real implementation, track history
        return 1
    
    async def _initiate_failover(self, reason: str):
        """Initiate failover process"""
        if self.current_state != FailoverState.NORMAL:
            return  # Already in failover
        
        self.logger.warning(f"Initiating failover: {reason}")
        
        with self._lock:
            self.current_state = FailoverState.FAILOVER_IN_PROGRESS
        
        # Create failover event
        event = FailoverEvent(
            event_id=str(uuid.uuid4()),
            event_type="failover_initiated",
            trigger_node=self.current_primary or "unknown",
            target_node="tbd",
            old_state=FailoverState.NORMAL,
            new_state=FailoverState.FAILOVER_IN_PROGRESS,
            timestamp=datetime.now(),
            reason=reason,
            metadata={"initiator": self.node_id}
        )
        
        self.failover_history.append(event)
        self.stats["failovers_initiated"] += 1
        
        # Notify callback
        if self.on_failover:
            await self._safe_callback(self.on_failover, event)
        
        # Select new primary
        new_primary = await self._select_new_primary()
        if new_primary:
            await self._promote_node(new_primary)
        else:
            self.logger.error("No suitable node found for failover")
            await self._failover_failed()
    
    async def _select_new_primary(self) -> Optional[str]:
        """Select new primary node"""
        candidates = []
        
        for node_id, node in self.nodes.items():
            if not node.is_active or node_id == self.current_primary:
                continue
            
            health_status, health_score = self.node_health.get(node_id, (HealthStatus.UNKNOWN, 0.0))
            
            if health_status == HealthStatus.HEALTHY:
                # Calculate priority score
                priority_score = self._calculate_priority_score(node, health_score)
                candidates.append((node_id, priority_score))
        
        if not candidates:
            return None
        
        # Sort by priority score (descending)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        return candidates[0][0]
    
    def _calculate_priority_score(self, node: FailoverNode, health_score: float) -> float:
        """Calculate priority score for node selection"""
        weights = self.config.priority_weights
        
        # Resource usage score (lower is better)
        resource_score = 1.0
        if node.resource_usage:
            avg_usage = sum(node.resource_usage.values()) / len(node.resource_usage)
            resource_score = max(0.0, 1.0 - (avg_usage / 100.0))
        
        # Latency score (lower is better)
        latency_score = max(0.0, 1.0 - (node.network_latency / 1000.0))
        
        # Role score
        role_scores = {
            NodeRole.SECONDARY: 1.0,
            NodeRole.STANDBY: 0.8,
            NodeRole.BACKUP: 0.6,
            NodeRole.HOT_SPARE: 0.9
        }
        role_score = role_scores.get(node.role, 0.5)
        
        # Calculate weighted score
        total_score = (
            health_score * weights["health_score"] +
            resource_score * weights["resource_usage"] +
            latency_score * weights["network_latency"] +
            role_score * weights["node_role"]
        )
        
        # Add node's failover priority
        total_score += node.failover_priority * 0.1
        
        return total_score
    
    async def _promote_node(self, node_id: str):
        """Promote node to primary"""
        self.logger.info(f"Promoting node {node_id} to primary")
        
        # Update current primary
        old_primary = self.current_primary
        self.current_primary = node_id
        
        # Update node roles
        if old_primary and old_primary in self.nodes:
            self.nodes[old_primary].is_primary = False
            self.nodes[old_primary].role = NodeRole.SECONDARY
        
        self.nodes[node_id].is_primary = True
        self.nodes[node_id].role = NodeRole.PRIMARY
        
        # Update state
        with self._lock:
            self.current_state = FailoverState.FAILOVER_COMPLETE
        
        # Create completion event
        event = FailoverEvent(
            event_id=str(uuid.uuid4()),
            event_type="failover_completed",
            trigger_node=old_primary or "unknown",
            target_node=node_id,
            old_state=FailoverState.FAILOVER_IN_PROGRESS,
            new_state=FailoverState.FAILOVER_COMPLETE,
            timestamp=datetime.now(),
            reason=f"Node {node_id} promoted to primary",
            metadata={"failover_time": 1.0}
        )
        
        self.failover_history.append(event)
        self.stats["failovers_completed"] += 1
        
        self.logger.info(f"Failover completed: {old_primary} -> {node_id}")
    
    async def _promote_new_primary(self):
        """Promote a new primary from remaining nodes"""
        new_primary = await self._select_new_primary()
        if new_primary:
            await self._promote_node(new_primary)
    
    async def _failover_failed(self):
        """Handle failed failover"""
        self.logger.error("Failover failed")
        
        with self._lock:
            self.current_state = FailoverState.DEGRADED
    
    async def _safe_callback(self, callback: Callable, *args, **kwargs):
        """Safely execute callback"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args, **kwargs)
            else:
                callback(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"Callback error: {e}")
    
    def get_failover_status(self) -> Dict[str, Any]:
        """Get failover status"""
        with self._lock:
            return {
                "current_state": self.current_state.value,
                "current_primary": self.current_primary,
                "total_nodes": len(self.nodes),
                "active_nodes": len([n for n in self.nodes.values() if n.is_active]),
                "healthy_nodes": len([n for n in self.nodes.values() if n.health_status == HealthStatus.HEALTHY]),
                "failover_mode": self.config.failover_mode.value,
                "stats": self.stats.copy(),
                "last_failover": self.failover_history[-1].to_dict() if self.failover_history else None
            }
    
    def get_node_status(self) -> Dict[str, Any]:
        """Get status of all nodes"""
        with self._lock:
            nodes_status = {}
            
            for node_id, node in self.nodes.items():
                health_status, health_score = self.node_health.get(node_id, (HealthStatus.UNKNOWN, 0.0))
                
                nodes_status[node_id] = {
                    "name": node.name,
                    "host": node.host,
                    "port": node.port,
                    "role": node.role.value,
                    "is_primary": node.is_primary,
                    "is_active": node.is_active,
                    "health_status": health_status.value,
                    "health_score": health_score,
                    "resource_usage": node.resource_usage,
                    "network_latency": node.network_latency,
                    "last_heartbeat": self.node_heartbeat.get(node_id, datetime.now()).isoformat()
                }
            
            return nodes_status

# Global failover manager instance
_failover_manager = None

def get_failover_manager() -> Optional[FailoverManager]:
    """Get global failover manager instance"""
    return _failover_manager

async def init_failover_manager(node_id: str, config: FailoverConfig = None) -> FailoverManager:
    """Initialize global failover manager"""
    global _failover_manager
    
    if config is None:
        config = FailoverConfig()
    
    _failover_manager = FailoverManager(node_id, config)
    await _failover_manager.start()
    
    return _failover_manager