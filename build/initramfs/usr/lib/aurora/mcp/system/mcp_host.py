"""
Aurora OS MCP Host Implementation
Manages MCP protocol and context distribution across the operating system

The Model Context Protocol (MCP) serves as the nervous system of Aurora OS,
enabling seamless context flow between AI components, system services,
and applications.
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PermissionLevel(Enum):
    """Permission levels for MCP access"""
    PUBLIC = "public"
    PRIVATE = "private"
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"

class ContextType(Enum):
    """Types of context data"""
    SYSTEM = "system"
    USER = "user"
    APPLICATION = "application"
    FILESYSTEM = "filesystem"
    NETWORK = "network"
    SECURITY = "security"
    PERFORMANCE = "performance"
    WELLNESS = "wellness"

@dataclass
class MCPContext:
    """Represents a piece of context data"""
    context_id: str
    provider_id: str
    context_type: ContextType
    data: Dict[str, Any]
    timestamp: float
    ttl: Optional[float] = None  # Time to live
    permissions: List[PermissionLevel] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def is_expired(self) -> bool:
        """Check if context has expired"""
        if self.ttl is None:
            return False
        return time.time() > (self.timestamp + self.ttl)
    
    def has_permission(self, level: PermissionLevel) -> bool:
        """Check if context has specific permission level"""
        return level in self.permissions

@dataclass
class MCPRequest:
    """Represents a request for context"""
    request_id: str
    consumer_id: str
    context_types: List[ContextType]
    filters: Dict[str, Any] = field(default_factory=dict)
    permissions: List[PermissionLevel] = field(default_factory=list)
    max_results: int = 100
    timeout: float = 30.0
    timestamp: float = field(default_factory=time.time)

@dataclass
class MCPResponse:
    """Represents a response to an MCP request"""
    request_id: str
    contexts: List[MCPContext]
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

class MCPProvider(ABC):
    """Abstract base class for MCP context providers"""
    
    def __init__(self, provider_id: str, name: str, version: str):
        self.provider_id = provider_id
        self.name = name
        self.version = version
        self.enabled = True
        self.permissions: List[PermissionLevel] = []
        self.context_types: List[ContextType] = []
        self.metadata: Dict[str, Any] = {}
        self._started = False
    
    @abstractmethod
    async def start(self) -> bool:
        """Start the provider"""
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """Stop the provider"""
        pass
    
    @abstractmethod
    async def get_context(self, request: MCPRequest) -> List[MCPContext]:
        """Get context data based on request"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check provider health"""
        pass
    
    def set_permissions(self, permissions: List[PermissionLevel]):
        """Set permission levels for this provider"""
        self.permissions = permissions
    
    def set_context_types(self, context_types: List[ContextType]):
        """Set the types of context this provider provides"""
        self.context_types = context_types
    
    def set_metadata(self, metadata: Dict[str, Any]):
        """Set provider metadata"""
        self.metadata = metadata
    
    @property
    def is_started(self) -> bool:
        """Check if provider is started"""
        return self._started

class FilesystemMCPProvider(MCPProvider):
    """Filesystem context provider"""
    
    def __init__(self):
        super().__init__("filesystem", "Filesystem Provider", "1.0.0")
        self.set_permissions([PermissionLevel.PUBLIC, PermissionLevel.PRIVATE])
        self.set_context_types([ContextType.FILESYSTEM])
        self.set_metadata({
            "description": "Provides filesystem context including file operations, "
                          "metadata, and usage patterns",
            "capabilities": ["file_search", "file_metadata", "usage_patterns"]
        })
    
    async def start(self) -> bool:
        """Start filesystem provider"""
        try:
            logger.info("Starting Filesystem MCP Provider...")
            # Initialize filesystem monitoring
            self._started = True
            logger.info("Filesystem MCP Provider started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start Filesystem Provider: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop filesystem provider"""
        try:
            logger.info("Stopping Filesystem MCP Provider...")
            # Clean up resources
            self._started = False
            logger.info("Filesystem MCP Provider stopped successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to stop Filesystem Provider: {e}")
            return False
    
    async def get_context(self, request: MCPRequest) -> List[MCPContext]:
        """Get filesystem context"""
        contexts = []
        
        # Example: Get recent files context
        if ContextType.FILESYSTEM in request.context_types:
            recent_files = await self._get_recent_files(request.filters)
            
            context = MCPContext(
                context_id=f"filesystem_recent_{int(time.time())}",
                provider_id=self.provider_id,
                context_type=ContextType.FILESYSTEM,
                data={"recent_files": recent_files},
                timestamp=time.time(),
                ttl=300.0,  # 5 minutes
                permissions=[PermissionLevel.PRIVATE],
                metadata={"source": "filesystem_monitor"},
                tags=["recent", "files"]
            )
            contexts.append(context)
        
        return contexts
    
    async def _get_recent_files(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get recent files with metadata"""
        # Placeholder implementation
        # In real implementation, this would query the filesystem
        return [
            {
                "path": "/home/user/documents/report.pdf",
                "last_accessed": time.time() - 3600,
                "size": 1024000,
                "type": "pdf"
            },
            {
                "path": "/home/user/projects/aurora/kernel/ai_scheduler.c",
                "last_accessed": time.time() - 1800,
                "size": 15360,
                "type": "source_code"
            }
        ]
    
    async def health_check(self) -> bool:
        """Check filesystem provider health"""
        return self._started and True

class SystemMCPProvider(MCPProvider):
    """System information context provider"""
    
    def __init__(self):
        super().__init__("system", "System Provider", "1.0.0")
        self.set_permissions([PermissionLevel.PUBLIC, PermissionLevel.PRIVATE])
        self.set_context_types([ContextType.SYSTEM, ContextType.PERFORMANCE])
        self.set_metadata({
            "description": "Provides system information including CPU, memory, "
                          "processes, and performance metrics",
            "capabilities": ["system_info", "performance_metrics", "process_info"]
        })
    
    async def start(self) -> bool:
        """Start system provider"""
        try:
            logger.info("Starting System MCP Provider...")
            # Initialize system monitoring
            self._started = True
            logger.info("System MCP Provider started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start System Provider: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop system provider"""
        try:
            logger.info("Stopping System MCP Provider...")
            self._started = False
            logger.info("System MCP Provider stopped successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to stop System Provider: {e}")
            return False
    
    async def get_context(self, request: MCPRequest) -> List[MCPContext]:
        """Get system context"""
        contexts = []
        
        # System information
        if ContextType.SYSTEM in request.context_types:
            system_info = await self._get_system_info()
            
            context = MCPContext(
                context_id=f"system_info_{int(time.time())}",
                provider_id=self.provider_id,
                context_type=ContextType.SYSTEM,
                data=system_info,
                timestamp=time.time(),
                ttl=60.0,  # 1 minute
                permissions=[PermissionLevel.PUBLIC],
                metadata={"source": "system_monitor"},
                tags=["system", "info"]
            )
            contexts.append(context)
        
        # Performance metrics
        if ContextType.PERFORMANCE in request.context_types:
            performance_info = await self._get_performance_info()
            
            context = MCPContext(
                context_id=f"performance_{int(time.time())}",
                provider_id=self.provider_id,
                context_type=ContextType.PERFORMANCE,
                data=performance_info,
                timestamp=time.time(),
                ttl=30.0,  # 30 seconds
                permissions=[PermissionLevel.PUBLIC],
                metadata={"source": "performance_monitor"},
                tags=["performance", "metrics"]
            )
            contexts.append(context)
        
        return contexts
    
    async def _get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        # Placeholder implementation
        return {
            "hostname": "aurora-os",
            "os_version": "Aurora OS 1.0.0",
            "kernel_version": "6.1.0-aurora",
            "uptime": 86400,
            "load_average": [0.5, 0.3, 0.2],
            "cpu_count": 8,
            "memory_total": 16777216000,  # 16GB
            "memory_available": 8388608000   # 8GB
        }
    
    async def _get_performance_info(self) -> Dict[str, Any]:
        """Get performance information"""
        # Placeholder implementation
        return {
            "cpu_usage": 25.5,
            "memory_usage": 50.2,
            "disk_usage": 35.7,
            "network_io": {
                "bytes_sent": 1048576,
                "bytes_received": 2097152
            },
            "process_count": 156,
            "active_processes": 12
        }
    
    async def health_check(self) -> bool:
        """Check system provider health"""
        return self._started and True

class SecurityMCPProvider(MCPProvider):
    """Security events and policy context provider"""
    
    def __init__(self):
        super().__init__("security", "Security Provider", "1.0.0")
        self.set_permissions([PermissionLevel.PRIVATE, PermissionLevel.SENSITIVE])
        self.set_context_types([ContextType.SECURITY])
        self.set_metadata({
            "description": "Provides security context including events, "
                          "policies, and threat intelligence",
            "capabilities": ["security_events", "policy_status", "threat_intel"]
        })
    
    async def start(self) -> bool:
        """Start security provider"""
        try:
            logger.info("Starting Security MCP Provider...")
            self._started = True
            logger.info("Security MCP Provider started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start Security Provider: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop security provider"""
        try:
            logger.info("Stopping Security MCP Provider...")
            self._started = False
            logger.info("Security MCP Provider stopped successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to stop Security Provider: {e}")
            return False
    
    async def get_context(self, request: MCPRequest) -> List[MCPContext]:
        """Get security context"""
        contexts = []
        
        if ContextType.SECURITY in request.context_types:
            security_info = await self._get_security_info()
            
            context = MCPContext(
                context_id=f"security_{int(time.time())}",
                provider_id=self.provider_id,
                context_type=ContextType.SECURITY,
                data=security_info,
                timestamp=time.time(),
                ttl=120.0,  # 2 minutes
                permissions=[PermissionLevel.SENSITIVE],
                metadata={"source": "security_monitor"},
                tags=["security", "events"]
            )
            contexts.append(context)
        
        return contexts
    
    async def _get_security_info(self) -> Dict[str, Any]:
        """Get security information"""
        # Placeholder implementation
        return {
            "security_status": "secure",
            "threat_level": "low",
            "recent_events": [
                {
                    "timestamp": time.time() - 3600,
                    "type": "login_success",
                    "user": "aurora_user",
                    "severity": "info"
                }
            ],
            "policies": [
                {
                    "name": "password_policy",
                    "status": "enforced",
                    "compliance": 100.0
                }
            ],
            "last_scan": time.time() - 86400,
            "next_scan": time.time() + 86400
        }
    
    async def health_check(self) -> bool:
        """Check security provider health"""
        return self._started and True

class PermissionGuard:
    """Manages permissions and access control for MCP"""
    
    def __init__(self):
        self.consumer_permissions: Dict[str, Dict[str, Any]] = {}
        self.role_permissions: Dict[str, List[PermissionLevel]] = {
            "system": [PermissionLevel.PUBLIC, PermissionLevel.PRIVATE, PermissionLevel.SENSITIVE],
            "user": [PermissionLevel.PUBLIC, PermissionLevel.PRIVATE],
            "guest": [PermissionLevel.PUBLIC]
        }
    
    def register_consumer(self, consumer_id: str, role: str = "user"):
        """Register a new consumer with permissions"""
        if role not in self.role_permissions:
            role = "user"
        
        self.consumer_permissions[consumer_id] = {
            "role": role,
            "permissions": self.role_permissions[role],
            "registered_at": time.time()
        }
    
    async def can_access(self, consumer_id: str, request: MCPRequest) -> bool:
        """Check if consumer can access requested context"""
        if consumer_id not in self.consumer_permissions:
            return False
        
        consumer_perms = self.consumer_permissions[consumer_id]
        
        # Check if consumer has required permissions
        for required_perm in request.permissions:
            if required_perm not in consumer_perms["permissions"]:
                return False
        
        return True
    
    async def can_access_context(self, consumer_id: str, context: MCPContext) -> bool:
        """Check if consumer can access specific context"""
        if consumer_id not in self.consumer_permissions:
            return False
        
        consumer_perms = self.consumer_permissions[consumer_id]
        
        # Check if any of context's permissions are accessible
        for context_perm in context.permissions:
            if context_perm in consumer_perms["permissions"]:
                return True
        
        return False
    
    def get_consumer_permissions(self, consumer_id: str) -> List[PermissionLevel]:
        """Get permissions for a consumer"""
        if consumer_id not in self.consumer_permissions:
            return []
        return self.consumer_permissions[consumer_id]["permissions"]

class ContextRouter:
    """Routes context requests to appropriate providers"""
    
    def __init__(self):
        self.routing_rules: Dict[ContextType, List[str]] = {}
        self.default_providers: List[str] = []
    
    def add_routing_rule(self, context_type: ContextType, provider_ids: List[str]):
        """Add routing rule for context type"""
        self.routing_rules[context_type] = provider_ids
    
    def set_default_providers(self, provider_ids: List[str]):
        """Set default providers"""
        self.default_providers = provider_ids
    
    async def route_request(self, request: MCPRequest, 
                          available_providers: Dict[str, MCPProvider]) -> List[str]:
        """Route request to appropriate providers"""
        provider_ids = []
        
        # Route based on context types
        for context_type in request.context_types:
            if context_type in self.routing_rules:
                provider_ids.extend(self.routing_rules[context_type])
        
        # Filter to available providers
        available_ids = [pid for pid in provider_ids if pid in available_providers]
        
        # Add default providers if no specific routing
        if not available_ids:
            available_ids = [pid for pid in self.default_providers 
                           if pid in available_providers]
        
        # Remove duplicates
        return list(set(available_ids))

class AuditLogger:
    """Audits all MCP interactions"""
    
    def __init__(self):
        self.audit_log: List[Dict[str, Any]] = []
        self.max_log_size = 10000
    
    async def log_request(self, request: MCPRequest):
        """Log a context request"""
        log_entry = {
            "type": "request",
            "timestamp": time.time(),
            "request_id": request.request_id,
            "consumer_id": request.consumer_id,
            "context_types": [ct.value for ct in request.context_types],
            "permissions": [p.value for p in request.permissions]
        }
        self._add_log_entry(log_entry)
    
    async def log_response(self, response: MCPResponse):
        """Log a context response"""
        log_entry = {
            "type": "response",
            "timestamp": time.time(),
            "request_id": response.request_id,
            "success": response.success,
            "context_count": len(response.contexts),
            "error": response.error
        }
        self._add_log_entry(log_entry)
    
    async def log_provider_registration(self, provider_id: str, permissions: List[PermissionLevel]):
        """Log provider registration"""
        log_entry = {
            "type": "provider_registration",
            "timestamp": time.time(),
            "provider_id": provider_id,
            "permissions": [p.value for p in permissions]
        }
        self._add_log_entry(log_entry)
    
    def _add_log_entry(self, entry: Dict[str, Any]):
        """Add entry to audit log"""
        self.audit_log.append(entry)
        
        # Maintain log size
        if len(self.audit_log) > self.max_log_size:
            self.audit_log = self.audit_log[-self.max_log_size:]
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit log entries"""
        return self.audit_log[-limit:]

class MCPHost:
    """Main MCP Host managing context providers and consumers"""
    
    def __init__(self):
        self.providers: Dict[str, MCPProvider] = {}
        self.permission_guard = PermissionGuard()
        self.context_router = ContextRouter()
        self.audit_logger = AuditLogger()
        self._started = False
        
        # Performance metrics
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_contexts_provided": 0,
            "average_response_time": 0.0
        }
    
    async def start(self):
        """Start MCP host"""
        try:
            logger.info("Starting Aurora OS MCP Host...")
            
            # Register built-in providers
            await self._register_builtin_providers()
            
            # Set up routing
            self._setup_routing()
            
            self._started = True
            logger.info("Aurora OS MCP Host started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start MCP Host: {e}")
            raise
    
    async def stop(self):
        """Stop MCP host"""
        try:
            logger.info("Stopping Aurora OS MCP Host...")
            
            # Stop all providers
            for provider in self.providers.values():
                await provider.stop()
            
            self._started = False
            logger.info("Aurora OS MCP Host stopped successfully")
            
        except Exception as e:
            logger.error(f"Failed to stop MCP Host: {e}")
    
    async def _register_builtin_providers(self):
        """Register built-in context providers"""
        providers = [
            FilesystemMCPProvider(),
            SystemMCPProvider(),
            SecurityMCPProvider()
        ]
        
        for provider in providers:
            await self.register_provider(provider)
    
    def _setup_routing(self):
        """Set up default routing rules"""
        self.context_router.add_routing_rule(ContextType.FILESYSTEM, ["filesystem"])
        self.context_router.add_routing_rule(ContextType.SYSTEM, ["system"])
        self.context_router.add_routing_rule(ContextType.PERFORMANCE, ["system"])
        self.context_router.add_routing_rule(ContextType.SECURITY, ["security"])
        self.context_router.set_default_providers(["system", "filesystem"])
    
    async def register_provider(self, provider: MCPProvider):
        """Register a new context provider"""
        try:
            # Start the provider
            success = await provider.start()
            if not success:
                raise Exception(f"Failed to start provider {provider.provider_id}")
            
            # Register provider
            self.providers[provider.provider_id] = provider
            
            # Log registration
            await self.audit_logger.log_provider_registration(
                provider.provider_id, provider.permissions
            )
            
            logger.info(f"Registered MCP provider: {provider.provider_id}")
            
        except Exception as e:
            logger.error(f"Failed to register provider {provider.provider_id}: {e}")
            raise
    
    async def unregister_provider(self, provider_id: str):
        """Unregister a context provider"""
        if provider_id in self.providers:
            provider = self.providers[provider_id]
            await provider.stop()
            del self.providers[provider_id]
            logger.info(f"Unregistered MCP provider: {provider_id}")
    
    def register_consumer(self, consumer_id: str, role: str = "user"):
        """Register a new consumer"""
        self.permission_guard.register_consumer(consumer_id, role)
        logger.info(f"Registered MCP consumer: {consumer_id} with role {role}")
    
    async def request_context(self, request: MCPRequest) -> MCPResponse:
        """Handle context request"""
        start_time = time.time()
        
        try:
            # Log request
            await self.audit_logger.log_request(request)
            
            # Check permissions
            if not await self.permission_guard.can_access(request.consumer_id, request):
                error = f"Consumer {request.consumer_id} lacks required permissions"
                logger.warning(error)
                return MCPResponse(
                    request_id=request.request_id,
                    contexts=[],
                    success=False,
                    error=error
                )
            
            # Route to appropriate providers
            provider_ids = await self.context_router.route_request(
                request, self.providers
            )
            
            if not provider_ids:
                error = "No providers available for request"
                logger.warning(error)
                return MCPResponse(
                    request_id=request.request_id,
                    contexts=[],
                    success=False,
                    error=error
                )
            
            # Collect contexts from providers
            all_contexts = []
            for provider_id in provider_ids:
                provider = self.providers[provider_id]
                try:
                    contexts = await provider.get_context(request)
                    all_contexts.extend(contexts)
                except Exception as e:
                    logger.error(f"Error getting context from provider {provider_id}: {e}")
            
            # Filter contexts based on permissions and filters
            filtered_contexts = await self._filter_contexts(
                all_contexts, request.consumer_id, request.filters
            )
            
            # Apply result limit
            if len(filtered_contexts) > request.max_results:
                filtered_contexts = filtered_contexts[:request.max_results]
            
            # Update metrics
            self._update_metrics(True, time.time() - start_time, len(filtered_contexts))
            
            # Log response
            response = MCPResponse(
                request_id=request.request_id,
                contexts=filtered_contexts,
                success=True
            )
            await self.audit_logger.log_response(response)
            
            logger.info(f"Provided {len(filtered_contexts)} contexts for request {request.request_id}")
            return response
            
        except Exception as e:
            error_msg = f"Error processing request {request.request_id}: {e}"
            logger.error(error_msg)
            
            # Update metrics
            self._update_metrics(False, time.time() - start_time, 0)
            
            # Log error response
            response = MCPResponse(
                request_id=request.request_id,
                contexts=[],
                success=False,
                error=error_msg
            )
            await self.audit_logger.log_response(response)
            
            return response
    
    async def _filter_contexts(self, contexts: List[MCPContext], 
                             consumer_id: str, filters: Dict[str, Any]) -> List[MCPContext]:
        """Filter contexts based on permissions and filters"""
        filtered = []
        
        for context in contexts:
            # Check permissions
            if not await self.permission_guard.can_access_context(consumer_id, context):
                continue
            
            # Check expiration
            if context.is_expired():
                continue
            
            # Apply custom filters
            if self._passes_filters(context, filters):
                filtered.append(context)
        
        return filtered
    
    def _passes_filters(self, context: MCPContext, filters: Dict[str, Any]) -> bool:
        """Check if context passes custom filters"""
        # Simple tag filtering
        if "tags" in filters:
            required_tags = filters["tags"]
            if not any(tag in context.tags for tag in required_tags):
                return False
        
        # Time range filtering
        if "time_range" in filters:
            time_range = filters["time_range"]
            if "start" in time_range and context.timestamp < time_range["start"]:
                return False
            if "end" in time_range and context.timestamp > time_range["end"]:
                return False
        
        return True
    
    def _update_metrics(self, success: bool, response_time: float, context_count: int):
        """Update performance metrics"""
        self.metrics["total_requests"] += 1
        
        if success:
            self.metrics["successful_requests"] += 1
            self.metrics["total_contexts_provided"] += context_count
        else:
            self.metrics["failed_requests"] += 1
        
        # Update average response time
        total = self.metrics["total_requests"]
        current_avg = self.metrics["average_response_time"]
        self.metrics["average_response_time"] = (
            (current_avg * (total - 1) + response_time) / total
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return self.metrics.copy()
    
    async def get_providers_info(self) -> List[Dict[str, Any]]:
        """Get information about registered providers"""
        providers_info = []
        for provider_id, provider in self.providers.items():
            health = False
            if hasattr(provider, 'health_check'):
                try:
                    health = await provider.health_check()
                except:
                    health = False
            
            info = {
                "provider_id": provider_id,
                "name": provider.name,
                "version": provider.version,
                "enabled": provider.enabled,
                "context_types": [ct.value for ct in provider.context_types],
                "permissions": [p.value for p in provider.permissions],
                "metadata": provider.metadata,
                "health": health
            }
            providers_info.append(info)
        return providers_info
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        provider_health = {}
        for provider_id, provider in self.providers.items():
            provider_health[provider_id] = await provider.health_check()
        
        return {
            "host_started": self._started,
            "provider_count": len(self.providers),
            "provider_health": provider_health,
            "metrics": self.get_metrics()
        }

# Global MCP host instance
aurora_mcp_host = MCPHost()