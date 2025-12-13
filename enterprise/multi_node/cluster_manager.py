"""
Aurora OS Multi-Node Cluster Manager
Distributed clustering system for Aurora OS enterprise deployments
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
import socket
import aiohttp
import hashlib
from datetime import datetime, timedelta

class NodeStatus(Enum):
    """Node status in cluster"""
    ONLINE = "online"
    OFFLINE = "offline"
    JOINING = "joining"
    LEAVING = "leaving"
    MAINTENANCE = "maintenance"
    FAILED = "failed"

class NodeRole(Enum):
    """Node role in cluster"""
    MANAGER = "manager"
    WORKER = "worker"
    STORAGE = "storage"
    AI_PROCESSOR = "ai_processor"
    LOAD_BALANCER = "load_balancer"

@dataclass
class ClusterNode:
    """Cluster node information"""
    id: str
    name: str
    host: str
    port: int
    role: NodeRole
    status: NodeStatus
    capabilities: Dict[str, Any]
    resources: Dict[str, Any]
    last_heartbeat: datetime
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['last_heartbeat'] = self.last_heartbeat.isoformat()
        data['role'] = self.role.value
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClusterNode':
        """Create from dictionary"""
        data['last_heartbeat'] = datetime.fromisoformat(data['last_heartbeat'])
        data['role'] = NodeRole(data['role'])
        data['status'] = NodeStatus(data['status'])
        return cls(**data)

@dataclass
class ClusterConfig:
    """Cluster configuration"""
    name: str
    version: str
    heartbeat_interval: int = 30
    node_timeout: int = 90
    load_balancing_algorithm: str = "round_robin"
    replication_factor: int = 3
    consistency_level: str = "eventual"
    auto_healing: bool = True
    max_nodes: int = 100

class ClusterManager:
    """Aurora OS Cluster Manager"""
    
    def __init__(self, config: ClusterConfig):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.node_id = str(uuid.uuid4())
        self.nodes: Dict[str, ClusterNode] = {}
        self.is_manager = False
        self.elected_manager: Optional[str] = None
        
        # Network state
        self.server = None
        self.client_session = None
        
        # Load balancing
        self.load_balancer = LoadBalancer(self)
        
        # Distributed context
        self.context_distributor = DistributedContextManager(self)
        
        # Health monitoring
        self.health_monitor = ClusterHealthMonitor(self)
        
        # Event handlers
        self.event_handlers = {
            'node_joined': [],
            'node_left': [],
            'node_failed': [],
            'manager_elected': [],
            'load_balanced': []
        }
    
    async def start_cluster(self, host: str = "0.0.0.0", port: int = 8081, is_manager: bool = False):
        """Start cluster node"""
        self.logger.info(f"Starting Aurora cluster node {self.node_id}")
        
        self.is_manager = is_manager
        
        # Initialize this node
        await self._initialize_local_node(host, port)
        
        # Start HTTP server for cluster communication
        await self._start_server(host, port)
        
        # Start heartbeat service
        asyncio.create_task(self._heartbeat_service())
        
        # Start health monitoring
        asyncio.create_task(self.health_monitor.start_monitoring())
        
        # Start manager election if not manager
        if not is_manager:
            asyncio.create_task(self._manager_election_service())
        
        # Start load balancing if manager
        if is_manager:
            asyncio.create_task(self.load_balancer.start_balancing())
        
        self.logger.info(f"Cluster node started on {host}:{port}")
    
    async def _initialize_local_node(self, host: str, port: int):
        """Initialize local node information"""
        local_node = ClusterNode(
            id=self.node_id,
            name=f"aurora-node-{socket.gethostname()}",
            host=host,
            port=port,
            role=NodeRole.MANAGER if self.is_manager else NodeRole.WORKER,
            status=NodeStatus.ONLINE,
            capabilities=await self._detect_capabilities(),
            resources=await self._detect_resources(),
            last_heartbeat=datetime.now(),
            metadata={
                'version': self.config.version,
                'startup_time': datetime.now().isoformat()
            }
        )
        
        self.nodes[self.node_id] = local_node
    
    async def _detect_capabilities(self) -> Dict[str, Any]:
        """Detect node capabilities"""
        return {
            'ai_processing': True,
            'storage': True,
            'networking': True,
            'gpu_acceleration': False,  # Would detect actual GPU
            'encryption': True,
            'compression': True,
            'caching': True,
            'monitoring': True
        }
    
    async def _detect_resources(self) -> Dict[str, Any]:
        """Detect node resources"""
        import psutil
        
        return {
            'cpu_cores': psutil.cpu_count(),
            'cpu_usage': psutil.cpu_percent(),
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available,
            'disk_total': psutil.disk_usage('/').total,
            'disk_free': psutil.disk_usage('/').free,
            'network_interfaces': list(psutil.net_if_addrs().keys())
        }
    
    async def _start_server(self, host: str, port: int):
        """Start HTTP server for cluster communication"""
        from aiohttp import web
        
        app = web.Application()
        
        # Cluster API endpoints
        app.router.add_post('/cluster/join', self.handle_join_request)
        app.router.add_post('/cluster/leave', self.handle_leave_request)
        app.router.add_post('/cluster/heartbeat', self.handle_heartbeat)
        app.router.add_get('/cluster/nodes', self.handle_get_nodes)
        app.router.add_post('/cluster/elect', self.handle_election)
        app.router.add_post('/cluster/balance', self.handle_load_balance)
        
        # Distributed context endpoints
        app.router.add_post('/context/update', self.context_distributor.handle_context_update)
        app.router.add_get('/context/sync', self.context_distributor.handle_context_sync)
        
        # Health check endpoint
        app.router.add_get('/health', self.handle_health_check)
        
        self.server = await web._run_server(app, host=host, port=port)
        self.logger.info(f"Cluster API server started on {host}:{port}")
    
    async def handle_join_request(self, request):
        """Handle node join request"""
        try:
            data = await request.json()
            node = ClusterNode.from_dict(data)
            
            # Validate node
            if await self._validate_node(node):
                node.status = NodeStatus.ONLINE
                self.nodes[node.id] = node
                
                self.logger.info(f"Node {node.id} joined cluster")
                await self._trigger_event('node_joined', node)
                
                return web.json_response({
                    'status': 'success',
                    'cluster_info': {
                        'name': self.config.name,
                        'manager': self.elected_manager,
                        'node_count': len(self.nodes)
                    }
                })
            else:
                return web.json_response(
                    {'status': 'error', 'message': 'Node validation failed'},
                    status=400
                )
                
        except Exception as e:
            self.logger.error(f"Error handling join request: {e}")
            return web.json_response(
                {'status': 'error', 'message': str(e)},
                status=500
            )
    
    async def handle_leave_request(self, request):
        """Handle node leave request"""
        try:
            data = await request.json()
            node_id = data.get('node_id')
            
            if node_id in self.nodes:
                node = self.nodes[node_id]
                node.status = NodeStatus.LEAVING
                
                self.logger.info(f"Node {node_id} leaving cluster")
                await self._trigger_event('node_left', node)
                
                # Remove node after grace period
                asyncio.create_task(self._remove_node_gracefully(node_id))
                
                return web.json_response({'status': 'success'})
            else:
                return web.json_response(
                    {'status': 'error', 'message': 'Node not found'},
                    status=404
                )
                
        except Exception as e:
            self.logger.error(f"Error handling leave request: {e}")
            return web.json_response(
                {'status': 'error', 'message': str(e)},
                status=500
            )
    
    async def handle_heartbeat(self, request):
        """Handle heartbeat from node"""
        try:
            data = await request.json()
            node_id = data.get('node_id')
            
            if node_id in self.nodes:
                self.nodes[node_id].last_heartbeat = datetime.now()
                self.nodes[node_id].resources = data.get('resources', {})
                
                if self.nodes[node_id].status == NodeStatus.OFFLINE:
                    self.nodes[node_id].status = NodeStatus.ONLINE
                    await self._trigger_event('node_recovered', self.nodes[node_id])
                
                return web.json_response({'status': 'success'})
            else:
                return web.json_response(
                    {'status': 'error', 'message': 'Node not found'},
                    status=404
                )
                
        except Exception as e:
            self.logger.error(f"Error handling heartbeat: {e}")
            return web.json_response(
                {'status': 'error', 'message': str(e)},
                status=500
            )
    
    async def handle_get_nodes(self, request):
        """Handle get nodes request"""
        try:
            nodes_data = [node.to_dict() for node in self.nodes.values()]
            return web.json_response({
                'status': 'success',
                'nodes': nodes_data,
                'manager': self.elected_manager,
                'node_count': len(self.nodes)
            })
        except Exception as e:
            self.logger.error(f"Error getting nodes: {e}")
            return web.json_response(
                {'status': 'error', 'message': str(e)},
                status=500
            )
    
    async def handle_election(self, request):
        """Handle manager election"""
        try:
            data = await request.json()
            candidate_id = data.get('candidate_id')
            
            # Simple election based on node ID (lowest ID wins)
            if not self.elected_manager or candidate_id < self.elected_manager:
                self.elected_manager = candidate_id
                await self._trigger_event('manager_elected', candidate_id)
                
                return web.json_response({
                    'status': 'success',
                    'manager': self.elected_manager
                })
            else:
                return web.json_response({
                    'status': 'declined',
                    'manager': self.elected_manager
                })
                
        except Exception as e:
            self.logger.error(f"Error in election: {e}")
            return web.json_response(
                {'status': 'error', 'message': str(e)},
                status=500
            )
    
    async def handle_health_check(self, request):
        """Handle health check"""
        try:
            return web.json_response({
                'status': 'healthy',
                'node_id': self.node_id,
                'is_manager': self.is_manager,
                'cluster_manager': self.elected_manager,
                'cluster_size': len(self.nodes),
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            return web.json_response(
                {'status': 'unhealthy', 'error': str(e)},
                status=500
            )
    
    async def join_cluster(self, manager_host: str, manager_port: int):
        """Join existing cluster"""
        self.logger.info(f"Joining cluster at {manager_host}:{manager_port}")
        
        if not self.client_session:
            self.client_session = aiohttp.ClientSession()
        
        try:
            local_node = self.nodes[self.node_id]
            join_data = local_node.to_dict()
            
            async with self.client_session.post(
                f"http://{manager_host}:{manager_port}/cluster/join",
                json=join_data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    self.elected_manager = result.get('cluster_info', {}).get('manager')
                    self.logger.info(f"Successfully joined cluster. Manager: {self.elected_manager}")
                    return True
                else:
                    self.logger.error(f"Failed to join cluster: {response.status}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error joining cluster: {e}")
            return False
    
    async def _heartbeat_service(self):
        """Send heartbeats to cluster manager"""
        while True:
            try:
                if self.elected_manager and self.elected_manager != self.node_id:
                    await self._send_heartbeat()
                
                await asyncio.sleep(self.config.heartbeat_interval)
                
            except Exception as e:
                self.logger.error(f"Error in heartbeat service: {e}")
                await asyncio.sleep(5)
    
    async def _send_heartbeat(self):
        """Send heartbeat to cluster manager"""
        if not self.client_session:
            self.client_session = aiohttp.ClientSession()
        
        try:
            local_node = self.nodes[self.node_id]
            heartbeat_data = {
                'node_id': self.node_id,
                'resources': local_node.resources,
                'timestamp': datetime.now().isoformat()
            }
            
            # Send to manager
            if self.elected_manager in self.nodes:
                manager_node = self.nodes[self.elected_manager]
                async with self.client_session.post(
                    f"http://{manager_node.host}:{manager_node.port}/cluster/heartbeat",
                    json=heartbeat_data
                ) as response:
                    if response.status != 200:
                        self.logger.warning(f"Heartbeat failed: {response.status}")
                        
        except Exception as e:
            self.logger.error(f"Error sending heartbeat: {e}")
    
    async def _manager_election_service(self):
        """Manager election service"""
        while True:
            try:
                if not self.elected_manager or self.nodes[self.elected_manager].status == NodeStatus.OFFLINE:
                    await self._start_election()
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in election service: {e}")
                await asyncio.sleep(30)
    
    async def _start_election(self):
        """Start manager election"""
        self.logger.info("Starting manager election")
        
        # Vote for self
        for node_id, node in self.nodes.items():
            if node.status == NodeStatus.ONLINE and node_id != self.node_id:
                try:
                    if not self.client_session:
                        self.client_session = aiohttp.ClientSession()
                    
                    async with self.client_session.post(
                        f"http://{node.host}:{node.port}/cluster/elect",
                        json={'candidate_id': self.node_id}
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            if result.get('status') == 'success':
                                self.elected_manager = self.node_id
                                self.logger.info(f"Elected as cluster manager")
                                break
                                
                except Exception as e:
                    self.logger.error(f"Error voting for node {node_id}: {e}")
    
    async def _validate_node(self, node: ClusterNode) -> bool:
        """Validate joining node"""
        # Check if node already exists
        if node.id in self.nodes:
            return False
        
        # Check cluster capacity
        if len(self.nodes) >= self.config.max_nodes:
            return False
        
        # Check version compatibility
        if node.metadata.get('version') != self.config.version:
            return False
        
        return True
    
    async def _remove_node_gracefully(self, node_id: str):
        """Remove node after grace period"""
        await asyncio.sleep(30)  # Grace period
        
        if node_id in self.nodes:
            del self.nodes[node_id]
            self.logger.info(f"Node {node_id} removed from cluster")
    
    async def _trigger_event(self, event_name: str, data: Any):
        """Trigger cluster event"""
        if event_name in self.event_handlers:
            for handler in self.event_handlers[event_name]:
                try:
                    await handler(data)
                except Exception as e:
                    self.logger.error(f"Error in event handler: {e}")
    
    def add_event_handler(self, event_name: str, handler):
        """Add event handler"""
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        self.event_handlers[event_name].append(handler)
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status"""
        online_nodes = [n for n in self.nodes.values() if n.status == NodeStatus.ONLINE]
        
        return {
            'cluster_name': self.config.name,
            'manager': self.elected_manager,
            'total_nodes': len(self.nodes),
            'online_nodes': len(online_nodes),
            'node_roles': {role.value: len([n for n in online_nodes if n.role == role]) 
                          for role in NodeRole},
            'is_healthy': len(online_nodes) > 0,
            'timestamp': datetime.now().isoformat()
        }

class LoadBalancer:
    """Cluster load balancer"""
    
    def __init__(self, cluster_manager: ClusterManager):
        self.cluster_manager = cluster_manager
        self.logger = logging.getLogger(__name__)
        self.round_robin_index = 0
    
    async def start_balancing(self):
        """Start load balancing service"""
        self.logger.info("Starting load balancer")
        
        while True:
            try:
                await self._balance_load()
                await asyncio.sleep(30)  # Balance every 30 seconds
            except Exception as e:
                self.logger.error(f"Error in load balancing: {e}")
                await asyncio.sleep(10)
    
    async def _balance_load(self):
        """Balance cluster load"""
        nodes = [n for n in self.cluster_manager.nodes.values() 
                if n.status == NodeStatus.ONLINE and n.role == NodeRole.WORKER]
        
        if not nodes:
            return
        
        # Check for overloaded nodes
        for node in nodes:
            cpu_usage = node.resources.get('cpu_usage', 0)
            memory_usage = (node.resources.get('memory_total', 0) - 
                          node.resources.get('memory_available', 0)) / node.resources.get('memory_total', 1)
            
            if cpu_usage > 80 or memory_usage > 0.8:
                self.logger.warning(f"Node {node.id} is overloaded: CPU {cpu_usage}%, Memory {memory_usage:.1%}")
                await self._redistribute_load(node)
    
    async def _redistribute_load(self, overloaded_node: ClusterNode):
        """Redistribute load from overloaded node"""
        # Find underutilized nodes
        underutilized_nodes = [
            n for n in self.cluster_manager.nodes.values()
            if (n.status == NodeStatus.ONLINE and 
                n.role == NodeRole.WORKER and 
                n.id != overloaded_node.id and
                n.resources.get('cpu_usage', 0) < 50)
        ]
        
        if underutilized_nodes:
            # Select node with lowest load
            target_node = min(underutilized_nodes, 
                            key=lambda n: n.resources.get('cpu_usage', 100))
            
            self.logger.info(f"Redistributing load from {overloaded_node.id} to {target_node.id}")
            
            # Trigger load redistribution event
            await self.cluster_manager._trigger_event('load_balanced', {
                'source': overloaded_node.id,
                'target': target_node.id
            })
    
    def select_node(self, algorithm: str = "round_robin") -> Optional[ClusterNode]:
        """Select node for task assignment"""
        nodes = [n for n in self.cluster_manager.nodes.values() 
                if n.status == NodeStatus.ONLINE and n.role == NodeRole.WORKER]
        
        if not nodes:
            return None
        
        if algorithm == "round_robin":
            node = nodes[self.round_robin_index % len(nodes)]
            self.round_robin_index += 1
            return node
        
        elif algorithm == "least_loaded":
            return min(nodes, key=lambda n: n.resources.get('cpu_usage', 100))
        
        elif algorithm == "random":
            import random
            return random.choice(nodes)
        
        return nodes[0]

class DistributedContextManager:
    """Distributed context management across cluster"""
    
    def __init__(self, cluster_manager: ClusterManager):
        self.cluster_manager = cluster_manager
        self.logger = logging.getLogger(__name__)
        self.local_context: Dict[str, Any] = {}
        self.context_version = 0
    
    async def handle_context_update(self, request):
        """Handle context update from other nodes"""
        try:
            data = await request.json()
            context_key = data.get('key')
            context_value = data.get('value')
            version = data.get('version')
            
            if version > self.context_version:
                self.local_context[context_key] = context_value
                self.context_version = version
                
                self.logger.debug(f"Context updated: {context_key} = {context_value}")
            
            return web.json_response({'status': 'success'})
            
        except Exception as e:
            self.logger.error(f"Error handling context update: {e}")
            return web.json_response(
                {'status': 'error', 'message': str(e)},
                status=500
            )
    
    async def handle_context_sync(self, request):
        """Handle context synchronization request"""
        try:
            return web.json_response({
                'status': 'success',
                'context': self.local_context,
                'version': self.context_version
            })
        except Exception as e:
            self.logger.error(f"Error in context sync: {e}")
            return web.json_response(
                {'status': 'error', 'message': str(e)},
                status=500
            )
    
    async def update_context(self, key: str, value: Any):
        """Update context and distribute to cluster"""
        self.context_version += 1
        self.local_context[key] = value
        
        # Distribute to other nodes
        await self._distribute_context_update(key, value, self.context_version)
    
    async def _distribute_context_update(self, key: str, value: Any, version: int):
        """Distribute context update to cluster nodes"""
        update_data = {
            'key': key,
            'value': value,
            'version': version,
            'timestamp': datetime.now().isoformat()
        }
        
        for node_id, node in self.cluster_manager.nodes.items():
            if (node_id != self.cluster_manager.node_id and 
                node.status == NodeStatus.ONLINE):
                
                try:
                    if not self.cluster_manager.client_session:
                        from aiohttp import ClientSession
                        self.cluster_manager.client_session = ClientSession()
                    
                    async with self.cluster_manager.client_session.post(
                        f"http://{node.host}:{node.port}/context/update",
                        json=update_data
                    ) as response:
                        if response.status != 200:
                            self.logger.warning(f"Failed to update context on {node_id}")
                            
                except Exception as e:
                    self.logger.error(f"Error distributing context to {node_id}: {e}")

class ClusterHealthMonitor:
    """Cluster health monitoring"""
    
    def __init__(self, cluster_manager: ClusterManager):
        self.cluster_manager = cluster_manager
        self.logger = logging.getLogger(__name__)
    
    async def start_monitoring(self):
        """Start health monitoring"""
        self.logger.info("Starting cluster health monitoring")
        
        while True:
            try:
                await self._check_node_health()
                await asyncio.sleep(self.cluster_manager.config.heartbeat_interval)
            except Exception as e:
                self.logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(10)
    
    async def _check_node_health(self):
        """Check health of all nodes"""
        current_time = datetime.now()
        timeout = timedelta(seconds=self.cluster_manager.config.node_timeout)
        
        for node_id, node in self.cluster_manager.nodes.items():
            if node_id == self.cluster_manager.node_id:
                continue  # Skip self
            
            time_since_heartbeat = current_time - node.last_heartbeat
            
            if time_since_heartbeat > timeout:
                if node.status != NodeStatus.OFFLINE:
                    node.status = NodeStatus.OFFLINE
                    self.logger.warning(f"Node {node_id} marked as offline")
                    await self.cluster_manager._trigger_event('node_failed', node)
                    
                    # Trigger auto-healing if enabled
                    if self.cluster_manager.config.auto_healing:
                        await self._auto_heal_node(node)
    
    async def _auto_heal_node(self, failed_node: ClusterNode):
        """Attempt to auto-heal failed node"""
        self.logger.info(f"Attempting to auto-heal node {failed_node.id}")
        
        try:
            # Try to reconnect to node
            from aiohttp import ClientSession
            
            async with ClientSession() as session:
                async with session.get(
                    f"http://{failed_node.host}:{failed_node.port}/health"
                ) as response:
                    if response.status == 200:
                        failed_node.status = NodeStatus.ONLINE
                        failed_node.last_heartbeat = datetime.now()
                        self.logger.info(f"Successfully healed node {failed_node.id}")
                        return True
                        
        except Exception as e:
            self.logger.error(f"Failed to heal node {failed_node.id}: {e}")
        
        return False

# Export main classes
__all__ = [
    'ClusterManager',
    'ClusterNode',
    'ClusterConfig',
    'NodeStatus',
    'NodeRole',
    'LoadBalancer',
    'DistributedContextManager',
    'ClusterHealthMonitor'
]