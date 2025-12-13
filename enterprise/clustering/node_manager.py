"""
Aurora OS Distributed Node Manager
Multi-node clustering system for Aurora OS enterprise deployment
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import socket
import hashlib
from datetime import datetime, timedelta

class NodeStatus(Enum):
    """Node status in cluster"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    JOINING = "joining"
    LEAVING = "leaving"
    FAILED = "failed"
    MAINTENANCE = "maintenance"

class NodeType(Enum):
    """Node types in cluster"""
    CONTROL = "control"           # Control plane node
    WORKER = "worker"            # Worker node
    STORAGE = "storage"          # Storage node
    AI = "ai"                   # AI processing node
    EDGE = "edge"               # Edge computing node
    HYBRID = "hybrid"           # Multi-purpose node

class ClusterRole(Enum):
    """Cluster roles"""
    LEADER = "leader"
    FOLLOWER = "follower"
    CANDIDATE = "candidate"

@dataclass
class NodeInfo:
    """Node information"""
    id: str
    name: str
    ip_address: str
    port: int
    node_type: NodeType
    status: NodeStatus
    cluster_role: ClusterRole
    last_heartbeat: float
    capabilities: Dict[str, Any]
    resources: Dict[str, Any]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NodeInfo':
        """Create from dictionary"""
        return cls(**data)

@dataclass
class ClusterConfig:
    """Cluster configuration"""
    name: str
    version: str
    heartbeat_interval: float = 5.0
    heartbeat_timeout: float = 15.0
    election_timeout: float = 10.0
    replication_factor: int = 3
    max_nodes: int = 100
    auto_failover: bool = True
    load_balancing: str = "round_robin"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

class NodeManager:
    """Manages Aurora OS distributed nodes"""
    
    def __init__(self, node_info: NodeInfo, cluster_config: ClusterConfig):
        self.logger = logging.getLogger(__name__)
        self.node_info = node_info
        self.cluster_config = cluster_config
        
        # Cluster state
        self.nodes: Dict[str, NodeInfo] = {}
        self.leader_node: Optional[str] = None
        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.cluster_state = "forming"
        
        # Networking
        self.server_socket: Optional[socket.socket] = None
        self.client_connections: Dict[str, socket.socket] = {}
        
        # Background tasks
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.leader_election_task: Optional[asyncio.Task] = None
        self.health_check_task: Optional[asyncio.Task] = None
        
        # Load balancing
        self.load_balancer = LoadBalancer(cluster_config.load_balancing)
        
        # Event callbacks
        self.on_node_join: Optional[callable] = None
        self.on_node_leave: Optional[callable] = None
        self.on_leader_change: Optional[callable] = None
        
    async def start(self):
        """Start the node manager"""
        self.logger.info(f"Starting Node Manager for {self.node_info.name}")
        
        # Add self to nodes
        self.nodes[self.node_info.id] = self.node_info
        
        # Start server
        await self._start_server()
        
        # Start background tasks
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self.leader_election_task = asyncio.create_task(self._leader_election_loop())
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        
        # Discover other nodes
        await self._discover_nodes()
        
        self.logger.info("Node Manager started successfully")
    
    async def stop(self):
        """Stop the node manager"""
        self.logger.info("Stopping Node Manager")
        
        # Cancel background tasks
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        if self.leader_election_task:
            self.leader_election_task.cancel()
        if self.health_check_task:
            self.health_check_task.cancel()
        
        # Close connections
        for conn in self.client_connections.values():
            conn.close()
        
        if self.server_socket:
            self.server_socket.close()
        
        self.logger.info("Node Manager stopped")
    
    async def _start_server(self):
        """Start the server socket"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.node_info.ip_address, self.node_info.port))
        self.server_socket.listen(10)
        
        self.logger.info(f"Server listening on {self.node_info.ip_address}:{self.node_info.port}")
        
        # Start accepting connections
        asyncio.create_task(self._accept_connections())
    
    async def _accept_connections(self):
        """Accept incoming connections"""
        while True:
            try:
                client_socket, address = await asyncio.get_event_loop().sock_accept(self.server_socket)
                node_id = await self._handshake(client_socket)
                if node_id:
                    self.client_connections[node_id] = client_socket
                    self.logger.info(f"Connected to node {node_id} from {address}")
                
            except Exception as e:
                self.logger.error(f"Error accepting connection: {e}")
                await asyncio.sleep(1)
    
    async def _handshake(self, client_socket: socket.socket) -> Optional[str]:
        """Perform handshake with client"""
        try:
            # Send node info
            handshake_data = {
                "type": "handshake",
                "node_info": self.node_info.to_dict(),
                "cluster_config": self.cluster_config.to_dict()
            }
            
            message = json.dumps(handshake_data).encode() + b'\n'
            await asyncio.get_event_loop().sock_sendall(client_socket, message)
            
            # Receive client response
            response_data = await asyncio.get_event_loop().sock_recv(client_socket, 4096)
            response = json.loads(response_data.decode())
            
            if response.get("type") == "handshake_response":
                node_id = response.get("node_id")
                if node_id:
                    # Add node to cluster
                    node_info = NodeInfo.from_dict(response.get("node_info"))
                    self.nodes[node_id] = node_info
                    
                    # Trigger callback
                    if self.on_node_join:
                        await self.on_node_join(node_info)
                
                return node_id
            
        except Exception as e:
            self.logger.error(f"Handshake failed: {e}")
        
        return None
    
    async def _discover_nodes(self):
        """Discover other nodes in the cluster"""
        self.logger.info("Discovering cluster nodes")
        
        # For now, simulate node discovery
        # In production, this would use service discovery, mDNS, or configuration
        await asyncio.sleep(2)
        
        # Simulate finding other nodes
        if self.node_info.id != "node-001":
            # Connect to seed node
            await self._connect_to_node("127.0.0.1", 8081, "node-001")
    
    async def _connect_to_node(self, ip_address: str, port: int, node_id: str):
        """Connect to another node"""
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            await asyncio.get_event_loop().sock_connect(client_socket, (ip_address, port))
            
            # Perform handshake
            await self._perform_client_handshake(client_socket)
            
            self.client_connections[node_id] = client_socket
            self.logger.info(f"Connected to node {node_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to node {node_id}: {e}")
    
    async def _perform_client_handshake(self, client_socket: socket.socket):
        """Perform client handshake"""
        try:
            # Receive server handshake
            data = await asyncio.get_event_loop().sock_recv(client_socket, 4096)
            handshake = json.loads(data.decode())
            
            if handshake.get("type") == "handshake":
                # Send response
                response = {
                    "type": "handshake_response",
                    "node_id": self.node_info.id,
                    "node_info": self.node_info.to_dict()
                }
                
                message = json.dumps(response).encode() + b'\n'
                await asyncio.get_event_loop().sock_sendall(client_socket, message)
        
        except Exception as e:
            self.logger.error(f"Client handshake failed: {e}")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats"""
        while True:
            try:
                await asyncio.sleep(self.cluster_config.heartbeat_interval)
                
                # Update heartbeat
                self.node_info.last_heartbeat = time.time()
                
                # Send heartbeat to all connected nodes
                heartbeat_msg = {
                    "type": "heartbeat",
                    "node_id": self.node_info.id,
                    "timestamp": self.node_info.last_heartbeat,
                    "term": self.current_term
                }
                
                await self._broadcast_message(heartbeat_msg)
                
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
    
    async def _leader_election_loop(self):
        """Leader election loop"""
        while True:
            try:
                await asyncio.sleep(self.cluster_config.election_timeout)
                
                # Check if leader is alive
                if self.leader_node and self.leader_node in self.nodes:
                    leader = self.nodes[self.leader_node]
                    if time.time() - leader.last_heartbeat > self.cluster_config.heartbeat_timeout:
                        self.logger.warning(f"Leader {self.leader_node} appears to be down")
                        self.leader_node = None
                        await self._start_election()
                elif not self.leader_node:
                    # No leader, start election
                    await self._start_election()
                
            except Exception as e:
                self.logger.error(f"Leader election error: {e}")
    
    async def _start_election(self):
        """Start leader election"""
        self.logger.info("Starting leader election")
        
        # Increment term
        self.current_term += 1
        self.node_info.cluster_role = ClusterRole.CANDIDATE
        self.voted_for = self.node_info.id
        
        # Request votes from other nodes
        vote_request = {
            "type": "vote_request",
            "candidate_id": self.node_info.id,
            "term": self.current_term,
            "last_heartbeat": self.node_info.last_heartbeat
        }
        
        votes_received = 1  # Vote for self
        await self._broadcast_message(vote_request)
        
        # Wait for responses
        await asyncio.sleep(2)
        
        # Count votes (simplified - would handle responses in real implementation)
        total_nodes = len(self.nodes)
        if votes_received > total_nodes // 2:
            # Won election
            await self._become_leader()
    
    async def _become_leader(self):
        """Become cluster leader"""
        self.logger.info(f"Node {self.node_info.id} became leader")
        
        self.leader_node = self.node_info.id
        self.node_info.cluster_role = ClusterRole.LEADER
        self.cluster_state = "active"
        
        # Notify all nodes
        leader_announcement = {
            "type": "leader_announcement",
            "leader_id": self.node_info.id,
            "term": self.current_term
        }
        
        await self._broadcast_message(leader_announcement)
        
        # Trigger callback
        if self.on_leader_change:
            await self.on_leader_change(self.node_info.id)
    
    async def _health_check_loop(self):
        """Health check for all nodes"""
        while True:
            try:
                await asyncio.sleep(self.cluster_config.heartbeat_interval * 2)
                
                current_time = time.time()
                failed_nodes = []
                
                for node_id, node in self.nodes.items():
                    if node_id == self.node_info.id:
                        continue
                    
                    # Check if node is responsive
                    if current_time - node.last_heartbeat > self.cluster_config.heartbeat_timeout:
                        if node.status == NodeStatus.ACTIVE:
                            node.status = NodeStatus.FAILED
                            failed_nodes.append(node_id)
                            self.logger.warning(f"Node {node_id} marked as failed")
                
                # Handle failed nodes
                for node_id in failed_nodes:
                    if self.cluster_config.auto_failover:
                        await self._handle_node_failure(node_id)
                
            except Exception as e:
                self.logger.error(f"Health check error: {e}")
    
    async def _handle_node_failure(self, node_id: str):
        """Handle node failure"""
        self.logger.info(f"Handling failure of node {node_id}")
        
        node = self.nodes.get(node_id)
        if not node:
            return
        
        # Remove from load balancer
        self.load_balancer.remove_node(node_id)
        
        # Trigger callback
        if self.on_node_leave:
            await self.on_node_leave(node)
        
        # Close connection
        if node_id in self.client_connections:
            self.client_connections[node_id].close()
            del self.client_connections[node_id]
    
    async def _broadcast_message(self, message: Dict[str, Any]):
        """Broadcast message to all connected nodes"""
        message_data = json.dumps(message).encode() + b'\n'
        
        for node_id, conn in list(self.client_connections.items()):
            try:
                await asyncio.get_event_loop().sock_sendall(conn, message_data)
            except Exception as e:
                self.logger.error(f"Failed to send message to {node_id}: {e}")
                # Connection might be broken
                if node_id in self.client_connections:
                    del self.client_connections[node_id]
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status"""
        active_nodes = [n for n in self.nodes.values() if n.status == NodeStatus.ACTIVE]
        
        return {
            "cluster_name": self.cluster_config.name,
            "cluster_state": self.cluster_state,
            "total_nodes": len(self.nodes),
            "active_nodes": len(active_nodes),
            "leader_node": self.leader_node,
            "current_term": self.current_term,
            "node_types": {
                node_type.value: len([n for n in active_nodes if n.node_type == node_type])
                for node_type in NodeType
            }
        }
    
    def get_node_info(self, node_id: str) -> Optional[NodeInfo]:
        """Get information about a specific node"""
        return self.nodes.get(node_id)
    
    def get_all_nodes(self) -> List[NodeInfo]:
        """Get all nodes in cluster"""
        return list(self.nodes.values())
    
    def get_active_nodes(self) -> List[NodeInfo]:
        """Get active nodes in cluster"""
        return [n for n in self.nodes.values() if n.status == NodeStatus.ACTIVE]
    
    async def add_node(self, node_info: NodeInfo) -> bool:
        """Add a node to the cluster"""
        if len(self.nodes) >= self.cluster_config.max_nodes:
            self.logger.warning("Cluster is at maximum capacity")
            return False
        
        self.nodes[node_info.id] = node_info
        self.load_balancer.add_node(node_info.id, node_info.resources)
        
        # Trigger callback
        if self.on_node_join:
            await self.on_node_join(node_info)
        
        self.logger.info(f"Added node {node_info.id} to cluster")
        return True
    
    async def remove_node(self, node_id: str) -> bool:
        """Remove a node from the cluster"""
        if node_id not in self.nodes:
            return False
        
        node = self.nodes[node_id]
        node.status = NodeStatus.LEAVING
        
        await self._handle_node_failure(node_id)
        
        self.logger.info(f"Removed node {node_id} from cluster")
        return True
    
    def get_load_balancer(self) -> 'LoadBalancer':
        """Get the load balancer instance"""
        return self.load_balancer

class LoadBalancer:
    """Load balancer for distributing requests across nodes"""
    
    def __init__(self, strategy: str = "round_robin"):
        self.logger = logging.getLogger(__name__)
        self.strategy = strategy
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.round_robin_index = 0
        
        # Statistics
        self.request_counts: Dict[str, int] = {}
        self.response_times: Dict[str, List[float]] = {}
    
    def add_node(self, node_id: str, resources: Dict[str, Any]):
        """Add a node to the load balancer"""
        self.nodes[node_id] = {
            "resources": resources,
            "weight": self._calculate_weight(resources),
            "healthy": True
        }
        self.request_counts[node_id] = 0
        self.response_times[node_id] = []
        
        self.logger.info(f"Added node {node_id} to load balancer")
    
    def remove_node(self, node_id: str):
        """Remove a node from the load balancer"""
        if node_id in self.nodes:
            del self.nodes[node_id]
            if node_id in self.request_counts:
                del self.request_counts[node_id]
            if node_id in self.response_times:
                del self.response_times[node_id]
            
            self.logger.info(f"Removed node {node_id} from load balancer")
    
    def select_node(self) -> Optional[str]:
        """Select a node based on load balancing strategy"""
        if not self.nodes:
            return None
        
        healthy_nodes = [node_id for node_id, info in self.nodes.items() if info["healthy"]]
        if not healthy_nodes:
            return None
        
        if self.strategy == "round_robin":
            return self._round_robin_select(healthy_nodes)
        elif self.strategy == "weighted":
            return self._weighted_select(healthy_nodes)
        elif self.strategy == "least_connections":
            return self._least_connections_select(healthy_nodes)
        elif self.strategy == "resource_based":
            return self._resource_based_select(healthy_nodes)
        else:
            return healthy_nodes[0]
    
    def _round_robin_select(self, nodes: List[str]) -> str:
        """Round-robin selection"""
        node = nodes[self.round_robin_index % len(nodes)]
        self.round_robin_index += 1
        return node
    
    def _weighted_select(self, nodes: List[str]) -> str:
        """Weighted selection based on node resources"""
        total_weight = sum(self.nodes[node]["weight"] for node in nodes)
        if total_weight == 0:
            return nodes[0]
        
        import random
        r = random.uniform(0, total_weight)
        current_weight = 0
        
        for node in nodes:
            current_weight += self.nodes[node]["weight"]
            if current_weight >= r:
                return node
        
        return nodes[0]
    
    def _least_connections_select(self, nodes: List[str]) -> str:
        """Select node with least connections"""
        min_connections = min(self.request_counts.get(node, 0) for node in nodes)
        candidates = [node for node in nodes if self.request_counts.get(node, 0) == min_connections]
        
        import random
        return random.choice(candidates)
    
    def _resource_based_select(self, nodes: List[str]) -> str:
        """Select node based on available resources"""
        best_node = None
        best_score = -1
        
        for node in nodes:
            resources = self.nodes[node]["resources"]
            # Simple scoring based on CPU and memory availability
            cpu_score = resources.get("cpu_available", 0) / max(resources.get("cpu_total", 1), 1)
            memory_score = resources.get("memory_available", 0) / max(resources.get("memory_total", 1), 1)
            total_score = (cpu_score + memory_score) / 2
            
            if total_score > best_score:
                best_score = total_score
                best_node = node
        
        return best_node or nodes[0]
    
    def _calculate_weight(self, resources: Dict[str, Any]) -> float:
        """Calculate node weight based on resources"""
        cpu_weight = resources.get("cpu_total", 1) * 2
        memory_weight = resources.get("memory_total", 1) * 0.5
        return cpu_weight + memory_weight
    
    def record_request(self, node_id: str, response_time: Optional[float] = None):
        """Record a request to a node"""
        if node_id in self.request_counts:
            self.request_counts[node_id] += 1
        
        if response_time is not None and node_id in self.response_times:
            self.response_times[node_id].append(response_time)
            # Keep only last 100 response times
            if len(self.response_times[node_id]) > 100:
                self.response_times[node_id] = self.response_times[node_id][-100:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get load balancer statistics"""
        stats = {
            "total_nodes": len(self.nodes),
            "healthy_nodes": sum(1 for info in self.nodes.values() if info["healthy"]),
            "strategy": self.strategy,
            "request_counts": self.request_counts.copy(),
            "average_response_times": {}
        }
        
        for node_id, times in self.response_times.items():
            if times:
                stats["average_response_times"][node_id] = sum(times) / len(times)
        
        return stats
    
    def set_node_health(self, node_id: str, healthy: bool):
        """Set node health status"""
        if node_id in self.nodes:
            self.nodes[node_id]["healthy"] = healthy
            self.logger.info(f"Set node {node_id} health to {healthy}")

# Export classes
__all__ = [
    'NodeManager',
    'LoadBalancer',
    'NodeInfo',
    'ClusterConfig',
    'NodeStatus',
    'NodeType',
    'ClusterRole',
]