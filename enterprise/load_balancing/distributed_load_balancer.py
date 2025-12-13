"""
Aurora OS Distributed Load Balancer
Advanced load balancing with failover and health checking
"""

import asyncio
import json
import logging
import time
import random
import statistics
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import hashlib
import aiohttp

class LoadBalancingAlgorithm(Enum):
    """Load balancing algorithms"""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    RESOURCE_BASED = "resource_based"
    CONSISTENT_HASH = "consistent_hash"
    GEOGRAPHIC = "geographic"
    AI_OPTIMIZED = "ai_optimized"

class HealthCheckType(Enum):
    """Health check types"""
    HTTP = "http"
    TCP = "tcp"
    PING = "ping"
    CUSTOM = "custom"

@dataclass
class BackendNode:
    """Backend node information"""
    id: str
    host: str
    port: int
    weight: int = 1
    max_connections: int = 1000
    current_connections: int = 0
    health_status: str = "healthy"
    last_health_check: Optional[datetime] = None
    response_times: List[float] = None
    error_count: int = 0
    success_count: int = 0
    total_requests: int = 0
    
    # Resource metrics
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    network_latency: float = 0.0
    
    # Geographic location
    region: str = "default"
    country: str = "default"
    
    def __post_init__(self):
        if self.response_times is None:
            self.response_times = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['last_health_check'] = self.last_health_check.isoformat() if self.last_health_check else None
        return data
    
    @property
    def is_healthy(self) -> bool:
        """Check if node is healthy"""
        return self.health_status == "healthy"
    
    @property
    def average_response_time(self) -> float:
        """Get average response time"""
        if not self.response_times:
            return 0.0
        return statistics.mean(self.response_times)
    
    @property
    def success_rate(self) -> float:
        """Get success rate"""
        if self.total_requests == 0:
            return 1.0
        return self.success_count / self.total_requests
    
    @property
    def load_score(self) -> float:
        """Calculate load score (lower is better)"""
        cpu_factor = self.cpu_usage / 100.0
        memory_factor = self.memory_usage / 100.0
        connection_factor = self.current_connections / self.max_connections
        latency_factor = min(self.average_response_time / 1000.0, 1.0)  # Normalize to seconds
        
        return (cpu_factor + memory_factor + connection_factor + latency_factor) / 4.0

@dataclass
class HealthCheckConfig:
    """Health check configuration"""
    type: HealthCheckType = HealthCheckType.HTTP
    endpoint: str = "/health"
    interval: int = 30
    timeout: int = 5
    retries: int = 3
    success_threshold: int = 2
    failure_threshold: int = 3
    expected_status: int = 200

@dataclass
class LoadBalancingConfig:
    """Load balancer configuration"""
    algorithm: LoadBalancingAlgorithm = LoadBalancingAlgorithm.ROUND_ROBIN
    sticky_sessions: bool = False
    session_affinity_cookie: str = "AURORA_AFFINITY"
    health_check: HealthCheckConfig = None
    failover_enabled: bool = True
    circuit_breaker_enabled: bool = True
    rate_limiting_enabled: bool = True
    
    def __post_init__(self):
        if self.health_check is None:
            self.health_check = HealthCheckConfig()

class DistributedLoadBalancer:
    """Advanced distributed load balancer"""
    
    def __init__(self, config: LoadBalancingConfig):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Backend nodes
        self.backend_nodes: Dict[str, BackendNode] = {}
        self.round_robin_index = 0
        
        # Health checking
        self.health_check_task: Optional[asyncio.Task] = None
        
        # Circuit breaker
        self.circuit_breaker = CircuitBreaker()
        
        # Rate limiting
        self.rate_limiter = RateLimiter()
        
        # AI optimization
        self.ai_optimizer = AILoadOptimizer()
        
        # Metrics
        self.metrics_collector = MetricsCollector()
        
        # Event handlers
        self.event_handlers = {
            'node_healthy': [],
            'node_unhealthy': [],
            'failover_triggered': [],
            'load_balanced': []
        }
    
    async def start(self):
        """Start the load balancer"""
        self.logger.info("Starting Distributed Load Balancer")
        
        # Start health checking
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        
        # Start metrics collection
        asyncio.create_task(self.metrics_collector.start_collection())
        
        # Start AI optimization
        if self.config.algorithm == LoadBalancingAlgorithm.AI_OPTIMIZED:
            asyncio.create_task(self.ai_optimizer.start_optimization(self))
        
        self.logger.info("Load Balancer started successfully")
    
    async def stop(self):
        """Stop the load balancer"""
        self.logger.info("Stopping Load Balancer")
        
        if self.health_check_task:
            self.health_check_task.cancel()
        
        self.logger.info("Load Balancer stopped")
    
    def add_backend_node(self, node: BackendNode):
        """Add a backend node"""
        self.backend_nodes[node.id] = node
        self.logger.info(f"Added backend node {node.id} ({node.host}:{node.port})")
    
    def remove_backend_node(self, node_id: str):
        """Remove a backend node"""
        if node_id in self.backend_nodes:
            del self.backend_nodes[node_id]
            self.logger.info(f"Removed backend node {node_id}")
    
    def get_healthy_nodes(self) -> List[BackendNode]:
        """Get healthy backend nodes"""
        return [node for node in self.backend_nodes.values() if node.is_healthy]
    
    async def select_node(self, request_info: Optional[Dict[str, Any]] = None) -> Optional[BackendNode]:
        """Select a backend node for request"""
        healthy_nodes = self.get_healthy_nodes()
        
        if not healthy_nodes:
            if self.config.failover_enabled:
                await self._trigger_failover()
            return None
        
        # Apply circuit breaker
        healthy_nodes = [node for node in healthy_nodes 
                        if self.circuit_breaker.is_available(node.id)]
        
        if not healthy_nodes:
            self.logger.warning("No available nodes (all circuit breakers open)")
            return None
        
        selected_node = None
        
        # Apply load balancing algorithm
        if self.config.algorithm == LoadBalancingAlgorithm.ROUND_ROBIN:
            selected_node = self._round_robin_select(healthy_nodes)
        
        elif self.config.algorithm == LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN:
            selected_node = self._weighted_round_robin_select(healthy_nodes)
        
        elif self.config.algorithm == LoadBalancingAlgorithm.LEAST_CONNECTIONS:
            selected_node = self._least_connections_select(healthy_nodes)
        
        elif self.config.algorithm == LoadBalancingAlgorithm.LEAST_RESPONSE_TIME:
            selected_node = self._least_response_time_select(healthy_nodes)
        
        elif self.config.algorithm == LoadBalancingAlgorithm.RESOURCE_BASED:
            selected_node = self._resource_based_select(healthy_nodes)
        
        elif self.config.algorithm == LoadBalancingAlgorithm.AI_OPTIMIZED:
            selected_node = await self.ai_optimizer.select_node(healthy_nodes, request_info)
        
        elif self.config.algorithm == LoadBalancingAlgorithm.CONSISTENT_HASH:
            selected_node = self._consistent_hash_select(healthy_nodes, request_info)
        
        elif self.config.algorithm == LoadBalancingAlgorithm.GEOGRAPHIC:
            selected_node = self._geographic_select(healthy_nodes, request_info)
        
        else:
            selected_node = healthy_nodes[0]
        
        # Update node metrics
        if selected_node:
            selected_node.current_connections += 1
            selected_node.total_requests += 1
        
        # Trigger event
        await self._trigger_event('load_balanced', {
            'node': selected_node,
            'algorithm': self.config.algorithm.value
        })
        
        return selected_node
    
    def _round_robin_select(self, nodes: List[BackendNode]) -> BackendNode:
        """Round-robin selection"""
        node = nodes[self.round_robin_index % len(nodes)]
        self.round_robin_index += 1
        return node
    
    def _weighted_round_robin_select(self, nodes: List[BackendNode]) -> BackendNode:
        """Weighted round-robin selection"""
        total_weight = sum(node.weight for node in nodes)
        if total_weight == 0:
            return nodes[0]
        
        # Weighted random selection
        r = random.uniform(0, total_weight)
        current_weight = 0
        
        for node in nodes:
            current_weight += node.weight
            if current_weight >= r:
                return node
        
        return nodes[0]
    
    def _least_connections_select(self, nodes: List[BackendNode]) -> BackendNode:
        """Select node with least connections"""
        return min(nodes, key=lambda n: n.current_connections / n.max_connections)
    
    def _least_response_time_select(self, nodes: List[BackendNode]) -> BackendNode:
        """Select node with least response time"""
        return min(nodes, key=lambda n: n.average_response_time)
    
    def _resource_based_select(self, nodes: List[BackendNode]) -> BackendNode:
        """Select node based on resource availability"""
        return min(nodes, key=lambda n: n.load_score)
    
    def _consistent_hash_select(self, nodes: List[BackendNode], request_info: Optional[Dict[str, Any]]) -> BackendNode:
        """Consistent hash selection"""
        if not request_info:
            return nodes[0]
        
        # Use request ID or IP for hashing
        hash_key = request_info.get('request_id') or request_info.get('client_ip', 'default')
        
        # Create hash ring
        hash_ring = {}
        for node in nodes:
            # Create multiple virtual nodes for better distribution
            for i in range(100):
                virtual_key = f"{node.id}:{i}"
                hash_value = int(hashlib.md5(virtual_key.encode()).hexdigest(), 16)
                hash_ring[hash_value] = node
        
        # Find node for hash
        request_hash = int(hashlib.md5(hash_key.encode()).hexdigest(), 16)
        sorted_hashes = sorted(hash_ring.keys())
        
        for hash_value in sorted_hashes:
            if hash_value >= request_hash:
                return hash_ring[hash_value]
        
        return hash_ring[sorted_hashes[0]]
    
    def _geographic_select(self, nodes: List[BackendNode], request_info: Optional[Dict[str, Any]]) -> BackendNode:
        """Geographic-based selection"""
        if not request_info:
            return nodes[0]
        
        client_region = request_info.get('client_region', 'default')
        
        # Find nodes in same region
        regional_nodes = [node for node in nodes if node.region == client_region]
        
        if regional_nodes:
            return min(regional_nodes, key=lambda n: n.load_score)
        
        # Fallback to least loaded node
        return min(nodes, key=lambda n: n.load_score)
    
    async def release_node(self, node: BackendNode, success: bool, response_time: float):
        """Release node after request completion"""
        node.current_connections = max(0, node.current_connections - 1)
        
        if success:
            node.success_count += 1
            node.response_times.append(response_time)
            
            # Keep only last 100 response times
            if len(node.response_times) > 100:
                node.response_times = node.response_times[-100:]
            
            # Reset circuit breaker on success
            self.circuit_breaker.record_success(node.id)
        else:
            node.error_count += 1
            self.circuit_breaker.record_failure(node.id)
        
        # Update metrics
        self.metrics_collector.record_request(node, success, response_time)
    
    async def _health_check_loop(self):
        """Health check loop"""
        while True:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.config.health_check.interval)
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(5)
    
    async def _perform_health_checks(self):
        """Perform health checks on all nodes"""
        tasks = []
        for node in self.backend_nodes.values():
            tasks.append(self._health_check_node(node))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _health_check_node(self, node: BackendNode):
        """Health check individual node"""
        try:
            health_status = False
            
            if self.config.health_check.type == HealthCheckType.HTTP:
                health_status = await self._http_health_check(node)
            elif self.config.health_check.type == HealthCheckType.TCP:
                health_status = await self._tcp_health_check(node)
            elif self.config.health_check.type == HealthCheckType.CUSTOM:
                health_status = await self._custom_health_check(node)
            
            # Update node status
            was_healthy = node.is_healthy
            node.last_health_check = datetime.now()
            
            if health_status:
                if not was_healthy:
                    await self._trigger_event('node_healthy', node)
                
                node.health_status = "healthy"
                node.success_count += 1
            else:
                if was_healthy:
                    await self._trigger_event('node_unhealthy', node)
                
                node.health_status = "unhealthy"
                node.error_count += 1
        
        except Exception as e:
            self.logger.error(f"Health check failed for node {node.id}: {e}")
            node.health_status = "unhealthy"
            node.error_count += 1
    
    async def _http_health_check(self, node: BackendNode) -> bool:
        """HTTP health check"""
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.health_check.timeout)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"http://{node.host}:{node.port}{self.config.health_check.endpoint}"
                async with session.get(url) as response:
                    return response.status == self.config.health_check.expected_status
                    
        except Exception:
            return False
    
    async def _tcp_health_check(self, node: BackendNode) -> bool:
        """TCP health check"""
        try:
            future = asyncio.open_connection(node.host, node.port)
            reader, writer = await asyncio.wait_for(future, timeout=self.config.health_check.timeout)
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False
    
    async def _custom_health_check(self, node: BackendNode) -> bool:
        """Custom health check (placeholder)"""
        # Implement custom health check logic
        return True
    
    async def _trigger_failover(self):
        """Trigger failover procedure"""
        self.logger.warning("Triggering failover - no healthy nodes available")
        await self._trigger_event('failover_triggered', {})
    
    async def _trigger_event(self, event_name: str, data: Any):
        """Trigger load balancer event"""
        if event_name in self.event_handlers:
            for handler in self.event_handlers[event_name]:
                try:
                    await handler(data)
                except Exception as e:
                    self.logger.error(f"Error in event handler: {e}")
    
    def add_event_handler(self, event_name: str, handler: Callable):
        """Add event handler"""
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        self.event_handlers[event_name].append(handler)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get load balancer statistics"""
        healthy_nodes = self.get_healthy_nodes()
        
        return {
            'total_nodes': len(self.backend_nodes),
            'healthy_nodes': len(healthy_nodes),
            'algorithm': self.config.algorithm.value,
            'total_requests': sum(node.total_requests for node in self.backend_nodes.values()),
            'total_connections': sum(node.current_connections for node in self.backend_nodes.values()),
            'average_response_time': statistics.mean(
                [node.average_response_time for node in healthy_nodes if node.response_times]
            ) if healthy_nodes else 0,
            'circuit_breaker_status': self.circuit_breaker.get_status(),
            'rate_limiter_status': self.rate_limiter.get_status()
        }

class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.logger = logging.getLogger(__name__)
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.circuit_states: Dict[str, Dict[str, Any]] = {}
    
    def is_available(self, node_id: str) -> bool:
        """Check if circuit is closed for node"""
        if node_id not in self.circuit_states:
            return True
        
        state = self.circuit_states[node_id]
        
        if state['state'] == 'open':
            # Check if recovery timeout has passed
            if time.time() - state['opened_at'] > self.recovery_timeout:
                state['state'] = 'half_open'
                state['failures'] = 0
                return True
            return False
        
        return state['state'] != 'open'
    
    def record_success(self, node_id: str):
        """Record successful request"""
        if node_id not in self.circuit_states:
            self.circuit_states[node_id] = {
                'state': 'closed',
                'failures': 0,
                'last_failure': None,
                'opened_at': None
            }
        
        state = self.circuit_states[node_id]
        
        if state['state'] == 'half_open':
            state['state'] = 'closed'
        
        state['failures'] = max(0, state['failures'] - 1)
    
    def record_failure(self, node_id: str):
        """Record failed request"""
        if node_id not in self.circuit_states:
            self.circuit_states[node_id] = {
                'state': 'closed',
                'failures': 0,
                'last_failure': None,
                'opened_at': None
            }
        
        state = self.circuit_states[node_id]
        state['failures'] += 1
        state['last_failure'] = time.time()
        
        if state['failures'] >= self.failure_threshold:
            state['state'] = 'open'
            state['opened_at'] = time.time()
            self.logger.warning(f"Circuit breaker opened for node {node_id}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        return {
            'node_states': {
                node_id: state['state'] for node_id, state in self.circuit_states.items()
            },
            'open_circuits': len([
                s for s in self.circuit_states.values() if s['state'] == 'open'
            ])
        }

class RateLimiter:
    """Rate limiter for load balancer"""
    
    def __init__(self, requests_per_second: int = 1000, burst_size: int = 2000):
        self.logger = logging.getLogger(__name__)
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        self.request_times: List[float] = []
    
    def is_allowed(self) -> bool:
        """Check if request is allowed"""
        current_time = time.time()
        
        # Remove old requests
        self.request_times = [
            req_time for req_time in self.request_times
            if current_time - req_time < 1.0
        ]
        
        # Check rate limit
        if len(self.request_times) >= self.requests_per_second:
            return False
        
        # Check burst limit
        if len(self.request_times) >= self.burst_size:
            return False
        
        # Record request
        self.request_times.append(current_time)
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get rate limiter status"""
        return {
            'requests_per_second': self.requests_per_second,
            'burst_size': self.burst_size,
            'current_requests': len(self.request_times)
        }

class AILoadOptimizer:
    """AI-powered load optimization"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.optimization_data: List[Dict[str, Any]] = []
        self.is_running = False
    
    async def start_optimization(self, load_balancer: DistributedLoadBalancer):
        """Start AI optimization"""
        self.is_running = True
        self.load_balancer = load_balancer
        
        while self.is_running:
            try:
                await self._analyze_performance()
                await self._optimize_algorithm()
                await asyncio.sleep(300)  # Optimize every 5 minutes
            except Exception as e:
                self.logger.error(f"Error in AI optimization: {e}")
                await asyncio.sleep(60)
    
    async def _analyze_performance(self):
        """Analyze performance data"""
        # Collect performance metrics
        for node in self.load_balancer.backend_nodes.values():
            performance_data = {
                'timestamp': time.time(),
                'node_id': node.id,
                'response_time': node.average_response_time,
                'success_rate': node.success_rate,
                'load_score': node.load_score,
                'connections': node.current_connections
            }
            self.optimization_data.append(performance_data)
        
        # Keep only last 1000 data points
        if len(self.optimization_data) > 1000:
            self.optimization_data = self.optimization_data[-1000:]
    
    async def _optimize_algorithm(self):
        """Optimize load balancing algorithm"""
        # Simple optimization logic - would use ML in production
        if len(self.optimization_data) < 100:
            return
        
        # Analyze which algorithm performs best
        best_algorithm = self._predict_best_algorithm()
        
        if best_algorithm != self.load_balancer.config.algorithm:
            self.logger.info(f"Switching to optimized algorithm: {best_algorithm.value}")
            self.load_balancer.config.algorithm = best_algorithm
    
    def _predict_best_algorithm(self) -> LoadBalancingAlgorithm:
        """Predict best algorithm based on current conditions"""
        # Simple heuristic - would use ML model in production
        avg_load_score = statistics.mean([
            node.load_score for node in self.load_balancer.backend_nodes.values()
        ])
        
        if avg_load_score > 0.8:
            return LoadBalancingAlgorithm.LEAST_CONNECTIONS
        elif avg_load_score > 0.5:
            return LoadBalancingAlgorithm.RESOURCE_BASED
        else:
            return LoadBalancingAlgorithm.ROUND_ROBIN
    
    async def select_node(self, nodes: List[BackendNode], request_info: Optional[Dict[str, Any]]) -> Optional[BackendNode]:
        """AI-powered node selection"""
        # Simple AI selection - would use neural network in production
        best_node = None
        best_score = -1
        
        for node in nodes:
            # Calculate AI score based on multiple factors
            score = (
                node.success_rate * 0.3 +
                (1.0 - node.load_score) * 0.4 +
                (1.0 / max(node.average_response_time, 0.001)) * 0.2 +
                (1.0 - node.current_connections / node.max_connections) * 0.1
            )
            
            if score > best_score:
                best_score = score
                best_node = node
        
        return best_node
    
    def stop_optimization(self):
        """Stop AI optimization"""
        self.is_running = False

class MetricsCollector:
    """Load balancer metrics collector"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metrics: List[Dict[str, Any]] = []
        self.is_running = False
    
    async def start_collection(self):
        """Start metrics collection"""
        self.is_running = True
        
        while self.is_running:
            await self._collect_system_metrics()
            await asyncio.sleep(60)  # Collect every minute
    
    def record_request(self, node: BackendNode, success: bool, response_time: float):
        """Record request metrics"""
        metric = {
            'timestamp': time.time(),
            'node_id': node.id,
            'success': success,
            'response_time': response_time,
            'connections': node.current_connections,
            'cpu_usage': node.cpu_usage,
            'memory_usage': node.memory_usage
        }
        self.metrics.append(metric)
    
    async def _collect_system_metrics(self):
        """Collect system metrics"""
        # System metrics collection logic
        pass
    
    def get_metrics(self) -> List[Dict[str, Any]]:
        """Get collected metrics"""
        return self.metrics.copy()
    
    def stop_collection(self):
        """Stop metrics collection"""
        self.is_running = False

# Export classes
__all__ = [
    'DistributedLoadBalancer',
    'BackendNode',
    'LoadBalancingConfig',
    'HealthCheckConfig',
    'LoadBalancingAlgorithm',
    'CircuitBreaker',
    'RateLimiter',
    'AILoadOptimizer',
    'MetricsCollector'
]