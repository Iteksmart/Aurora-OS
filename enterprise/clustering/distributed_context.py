"""
Aurora OS Distributed Context Management
Manages context across multiple nodes in the cluster
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import hashlib
import pickle
import zlib

class ContextType(Enum):
    """Context types"""
    USER_SESSION = "user_session"
    APPLICATION_STATE = "application_state"
    SYSTEM_CONFIG = "system_config"
    AI_MODEL = "ai_model"
    TEMPORARY = "temporary"
    PERSISTENT = "persistent"

class ReplicationStrategy(Enum):
    """Replication strategies"""
    LEADER = "leader"          # Leader-based replication
    QUORUM = "quorum"          # Quorum-based replication
    EVENTUAL = "eventual"      # Eventual consistency
    STRONG = "strong"          # Strong consistency

class ContextPriority(Enum):
    """Context priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class ContextMetadata:
    """Context metadata"""
    context_id: str
    context_type: ContextType
    priority: ContextPriority
    created_at: float
    updated_at: float
    expires_at: Optional[float]
    owner_node: str
    version: int
    replication_factor: int
    consistency_level: str
    tags: Set[str]
    size_bytes: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['tags'] = list(self.tags)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContextMetadata':
        """Create from dictionary"""
        data['tags'] = set(data['tags'])
        return cls(**data)

@dataclass
class ContextData:
    """Context data wrapper"""
    metadata: ContextMetadata
    data: Any
    checksum: str
    compressed: bool = False
    
    def calculate_checksum(self) -> str:
        """Calculate checksum of data"""
        data_bytes = pickle.dumps(self.data)
        return hashlib.sha256(data_bytes).hexdigest()
    
    def compress_data(self):
        """Compress the data"""
        if not self.compressed and self.metadata.size_bytes > 1024:  # Only compress if > 1KB
            data_bytes = pickle.dumps(self.data)
            compressed = zlib.compress(data_bytes)
            self.data = compressed
            self.compressed = True
            self.metadata.size_bytes = len(compressed)
    
    def decompress_data(self) -> Any:
        """Decompress the data if needed"""
        if self.compressed:
            decompressed = zlib.decompress(self.data)
            return pickle.loads(decompressed)
        return self.data

class DistributedContextManager:
    """Manages distributed context across cluster nodes"""
    
    def __init__(self, node_id: str, replication_strategy: ReplicationStrategy = ReplicationStrategy.QUORUM):
        self.logger = logging.getLogger(__name__)
        self.node_id = node_id
        self.replication_strategy = replication_strategy
        
        # Context storage
        self.local_contexts: Dict[str, ContextData] = {}
        self.context_index: Dict[str, Set[str]] = {}  # Index by tags
        self.context_by_type: Dict[ContextType, Set[str]] = {ct: set() for ct in ContextType}
        
        # Replication
        self.replicated_contexts: Dict[str, Set[str]] = {}  # context_id -> set of node_ids
        self.pending_replications: Dict[str, asyncio.Task] = {}
        
        # Cache
        self.cache: Dict[str, Tuple[ContextData, float]] = {}  # context_id -> (data, timestamp)
        self.cache_ttl = 300  # 5 minutes
        
        # Statistics
        self.stats = {
            "contexts_stored": 0,
            "contexts_retrieved": 0,
            "replications_sent": 0,
            "replications_received": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # Event callbacks
        self.on_context_created: Optional[callable] = None
        self.on_context_updated: Optional[callable] = None
        self.on_context_deleted: Optional[callable] = None
        
    async def store_context(self, context_id: str, data: Any, context_type: ContextType,
                           priority: ContextPriority = ContextPriority.NORMAL,
                           expires_in: Optional[float] = None,
                           replication_factor: int = 3,
                           tags: Optional[Set[str]] = None,
                           owner_node: Optional[str] = None) -> bool:
        """Store context data"""
        try:
            # Create metadata
            now = time.time()
            expires_at = now + expires_in if expires_in else None
            
            metadata = ContextMetadata(
                context_id=context_id,
                context_type=context_type,
                priority=priority,
                created_at=now,
                updated_at=now,
                expires_at=expires_at,
                owner_node=owner_node or self.node_id,
                version=1,
                replication_factor=replication_factor,
                consistency_level=self._get_consistency_level(priority),
                tags=tags or set(),
                size_bytes=0  # Will be calculated after compression
            )
            
            # Create context data
            context_data = ContextData(
                metadata=metadata,
                data=data,
                checksum="",  # Will be calculated
                compressed=False
            )
            
            # Calculate checksum and compress
            context_data.checksum = context_data.calculate_checksum()
            context_data.compress_data()
            
            # Store locally
            self.local_contexts[context_id] = context_data
            
            # Update indexes
            self._update_indexes(context_id, context_data)
            
            # Replicate to other nodes
            await self._replicate_context(context_data)
            
            # Update statistics
            self.stats["contexts_stored"] += 1
            
            # Trigger callback
            if self.on_context_created:
                await self.on_context_created(context_data)
            
            self.logger.debug(f"Stored context {context_id} (type: {context_type.value})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store context {context_id}: {e}")
            return False
    
    async def get_context(self, context_id: str) -> Optional[Any]:
        """Retrieve context data"""
        try:
            # Check cache first
            cached_data = self._get_from_cache(context_id)
            if cached_data:
                self.stats["cache_hits"] += 1
                return cached_data
            
            self.stats["cache_misses"] += 1
            
            # Check local storage
            context_data = self.local_contexts.get(context_id)
            if not context_data:
                # Try to fetch from other nodes
                context_data = await self._fetch_from_nodes(context_id)
                if context_data:
                    self.local_contexts[context_id] = context_data
                    self._update_indexes(context_id, context_data)
            
            if context_data:
                # Check expiration
                if context_data.metadata.expires_at and time.time() > context_data.metadata.expires_at:
                    await self.delete_context(context_id)
                    return None
                
                # Decompress and cache
                data = context_data.decompress_data()
                self._add_to_cache(context_id, context_data)
                
                self.stats["contexts_retrieved"] += 1
                return data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get context {context_id}: {e}")
            return None
    
    async def update_context(self, context_id: str, data: Any, 
                           version: Optional[int] = None) -> bool:
        """Update existing context"""
        try:
            context_data = self.local_contexts.get(context_id)
            if not context_data:
                return False
            
            # Check version if provided
            if version is not None and context_data.metadata.version != version:
                self.logger.warning(f"Version conflict for context {context_id}")
                return False
            
            # Update data and metadata
            context_data.data = data
            context_data.metadata.updated_at = time.time()
            context_data.metadata.version += 1
            
            # Recalculate checksum and compress
            context_data.checksum = context_data.calculate_checksum()
            context_data.compressed = False
            context_data.compress_data()
            
            # Replicate changes
            await self._replicate_context(context_data, update=True)
            
            # Trigger callback
            if self.on_context_updated:
                await self.on_context_updated(context_data)
            
            self.logger.debug(f"Updated context {context_id} to version {context_data.metadata.version}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update context {context_id}: {e}")
            return False
    
    async def delete_context(self, context_id: str) -> bool:
        """Delete context"""
        try:
            context_data = self.local_contexts.get(context_id)
            if not context_data:
                return False
            
            # Remove from local storage
            del self.local_contexts[context_id]
            
            # Remove from indexes
            self._remove_from_indexes(context_id, context_data)
            
            # Remove from cache
            if context_id in self.cache:
                del self.cache[context_id]
            
            # Replicate deletion
            await self._replicate_deletion(context_id)
            
            # Trigger callback
            if self.on_context_deleted:
                await self.on_context_deleted(context_id)
            
            self.logger.debug(f"Deleted context {context_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete context {context_id}: {e}")
            return False
    
    async def find_contexts(self, context_type: Optional[ContextType] = None,
                          tags: Optional[Set[str]] = None,
                          owner_node: Optional[str] = None,
                          limit: int = 100) -> List[str]:
        """Find contexts by criteria"""
        try:
            candidate_ids = set(self.local_contexts.keys())
            
            # Filter by type
            if context_type:
                candidate_ids &= self.context_by_type.get(context_type, set())
            
            # Filter by tags
            if tags:
                tag_matches = set()
                for tag in tags:
                    tag_matches |= self.context_index.get(tag, set())
                candidate_ids &= tag_matches
            
            # Filter by owner
            if owner_node:
                owner_matches = {
                    cid for cid, data in self.local_contexts.items()
                    if data.metadata.owner_node == owner_node
                }
                candidate_ids &= owner_matches
            
            # Sort by priority and updated time
            sorted_contexts = sorted(
                list(candidate_ids),
                key=lambda cid: (
                    self.local_contexts[cid].metadata.priority.value,
                    self.local_contexts[cid].metadata.updated_at
                ),
                reverse=True
            )
            
            return sorted_contexts[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to find contexts: {e}")
            return []
    
    async def cleanup_expired_contexts(self):
        """Clean up expired contexts"""
        try:
            now = time.time()
            expired_contexts = []
            
            for context_id, context_data in self.local_contexts.items():
                if (context_data.metadata.expires_at and 
                    now > context_data.metadata.expires_at):
                    expired_contexts.append(context_id)
            
            for context_id in expired_contexts:
                await self.delete_context(context_id)
            
            if expired_contexts:
                self.logger.info(f"Cleaned up {len(expired_contexts)} expired contexts")
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup expired contexts: {e}")
    
    def _update_indexes(self, context_id: str, context_data: ContextData):
        """Update internal indexes"""
        # Update type index
        self.context_by_type[context_data.metadata.context_type].add(context_id)
        
        # Update tag index
        for tag in context_data.metadata.tags:
            if tag not in self.context_index:
                self.context_index[tag] = set()
            self.context_index[tag].add(context_id)
    
    def _remove_from_indexes(self, context_id: str, context_data: ContextData):
        """Remove from internal indexes"""
        # Remove from type index
        self.context_by_type[context_data.metadata.context_type].discard(context_id)
        
        # Remove from tag index
        for tag in context_data.metadata.tags:
            if tag in self.context_index:
                self.context_index[tag].discard(context_id)
    
    def _get_consistency_level(self, priority: ContextPriority) -> str:
        """Get consistency level based on priority"""
        if priority == ContextPriority.CRITICAL:
            return "strong"
        elif priority == ContextPriority.HIGH:
            return "quorum"
        else:
            return "eventual"
    
    async def _replicate_context(self, context_data: ContextData, update: bool = False):
        """Replicate context to other nodes"""
        try:
            # This would integrate with the node manager to get cluster nodes
            # For now, simulate replication
            replication_nodes = self._get_replication_nodes(context_data.metadata.replication_factor)
            
            for node_id in replication_nodes:
                if node_id != self.node_id:
                    # Simulate async replication
                    task = asyncio.create_task(self._replicate_to_node(node_id, context_data, update))
                    if not update:
                        self.pending_replications[context_data.metadata.context_id] = task
            
            self.stats["replications_sent"] += len(replication_nodes)
            
        except Exception as e:
            self.logger.error(f"Failed to replicate context: {e}")
    
    async def _replicate_to_node(self, node_id: str, context_data: ContextData, update: bool):
        """Replicate context to specific node"""
        try:
            # Simulate network delay
            await asyncio.sleep(0.1)
            
            # In real implementation, this would send the context data to the target node
            self.logger.debug(f"Replicated context {context_data.metadata.context_id} to node {node_id}")
            
            if not update:
                self.replicated_contexts.setdefault(context_data.metadata.context_id, set()).add(node_id)
            
        except Exception as e:
            self.logger.error(f"Failed to replicate to node {node_id}: {e}")
    
    async def _replicate_deletion(self, context_id: str):
        """Replicate deletion to other nodes"""
        try:
            replication_nodes = self.replicated_contexts.get(context_id, set())
            
            for node_id in replication_nodes:
                # Simulate deletion replication
                await asyncio.sleep(0.05)
                self.logger.debug(f"Replicated deletion of {context_id} to node {node_id}")
            
            # Clean up replication tracking
            if context_id in self.replicated_contexts:
                del self.replicated_contexts[context_id]
            
        except Exception as e:
            self.logger.error(f"Failed to replicate deletion: {e}")
    
    async def _fetch_from_nodes(self, context_id: str) -> Optional[ContextData]:
        """Fetch context from other nodes"""
        try:
            # In real implementation, this would query other nodes in the cluster
            # For now, simulate not finding the context
            await asyncio.sleep(0.2)
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to fetch context from nodes: {e}")
            return None
    
    def _get_replication_nodes(self, replication_factor: int) -> List[str]:
        """Get nodes for replication"""
        # This would integrate with node manager to get available nodes
        # For now, return mock node IDs
        mock_nodes = ["node-002", "node-003", "node-004", "node-005"]
        return mock_nodes[:replication_factor]
    
    def _add_to_cache(self, context_id: str, context_data: ContextData):
        """Add context to cache"""
        self.cache[context_id] = (context_data, time.time())
    
    def _get_from_cache(self, context_id: str) -> Optional[Any]:
        """Get context from cache"""
        if context_id in self.cache:
            context_data, timestamp = self.cache[context_id]
            
            # Check if cache entry is still valid
            if time.time() - timestamp < self.cache_ttl:
                return context_data.decompress_data()
            else:
                # Remove expired cache entry
                del self.cache[context_id]
        
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get context manager statistics"""
        return {
            **self.stats,
            "local_contexts": len(self.local_contexts),
            "cached_contexts": len(self.cache),
            "context_types": {
                ct.value: len(contexts) 
                for ct, contexts in self.context_by_type.items()
            },
            "replicated_contexts": len(self.replicated_contexts),
            "pending_replications": len(self.pending_replications)
        }
    
    async def export_contexts(self, context_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Export contexts for backup"""
        try:
            if context_ids is None:
                context_ids = list(self.local_contexts.keys())
            
            exported = {}
            for context_id in context_ids:
                if context_id in self.local_contexts:
                    context_data = self.local_contexts[context_id]
                    exported[context_id] = {
                        "metadata": context_data.metadata.to_dict(),
                        "data": context_data.data,  # Would be serialized in real implementation
                        "checksum": context_data.checksum,
                        "compressed": context_data.compressed
                    }
            
            return {
                "export_time": time.time(),
                "node_id": self.node_id,
                "contexts": exported
            }
            
        except Exception as e:
            self.logger.error(f"Failed to export contexts: {e}")
            return {}
    
    async def import_contexts(self, export_data: Dict[str, Any]) -> int:
        """Import contexts from backup"""
        try:
            imported_count = 0
            contexts = export_data.get("contexts", {})
            
            for context_id, context_info in contexts.items():
                # Check if context already exists
                if context_id not in self.local_contexts:
                    # Recreate context data
                    metadata = ContextMetadata.from_dict(context_info["metadata"])
                    context_data = ContextData(
                        metadata=metadata,
                        data=context_info["data"],
                        checksum=context_info["checksum"],
                        compressed=context_info["compressed"]
                    )
                    
                    self.local_contexts[context_id] = context_data
                    self._update_indexes(context_id, context_data)
                    imported_count += 1
            
            self.logger.info(f"Imported {imported_count} contexts")
            return imported_count
            
        except Exception as e:
            self.logger.error(f"Failed to import contexts: {e}")
            return 0

class ContextCache:
    """High-performance context cache with LRU eviction"""
    
    def __init__(self, max_size: int = 1000, ttl: float = 300):
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Tuple[ContextData, float]] = {}
        self.access_order: List[str] = []
        self.lock = asyncio.Lock()
    
    async def get(self, context_id: str) -> Optional[ContextData]:
        """Get context from cache"""
        async with self.lock:
            if context_id in self.cache:
                context_data, timestamp = self.cache[context_id]
                
                # Check TTL
                if time.time() - timestamp < self.ttl:
                    # Update access order
                    self.access_order.remove(context_id)
                    self.access_order.append(context_id)
                    return context_data
                else:
                    # Remove expired entry
                    del self.cache[context_id]
                    self.access_order.remove(context_id)
            
            return None
    
    async def put(self, context_id: str, context_data: ContextData):
        """Put context in cache"""
        async with self.lock:
            # Remove existing entry if present
            if context_id in self.cache:
                self.access_order.remove(context_id)
            # Evict if at capacity
            elif len(self.cache) >= self.max_size:
                oldest = self.access_order.pop(0)
                del self.cache[oldest]
            
            # Add new entry
            self.cache[context_id] = (context_data, time.time())
            self.access_order.append(context_id)
    
    async def invalidate(self, context_id: str):
        """Invalidate context in cache"""
        async with self.lock:
            if context_id in self.cache:
                del self.cache[context_id]
                self.access_order.remove(context_id)
    
    async def clear(self):
        """Clear all cache entries"""
        async with self.lock:
            self.cache.clear()
            self.access_order.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl": self.ttl,
            "utilization": len(self.cache) / self.max_size
        }

# Export classes
__all__ = [
    'DistributedContextManager',
    'ContextCache',
    'ContextData',
    'ContextMetadata',
    'ContextType',
    'ReplicationStrategy',
    'ContextPriority',
]