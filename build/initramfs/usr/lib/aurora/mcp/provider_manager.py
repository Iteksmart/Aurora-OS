"""
Aurora OS - MCP Provider Manager

This module manages all MCP context providers, providing a unified interface
for the AI control plane to access system context from various sources.

Key Features:
- Provider lifecycle management
- Context aggregation and correlation
- Performance monitoring
- Load balancing
- Error handling and recovery
- Context caching and optimization
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Type
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from .system.mcp_host import MCPContext, MCPProvider
from .providers import (
    PROVIDER_REGISTRY,
    FileSystemContextProvider,
    SystemContextProvider,
    SecurityContextProvider
)


@dataclass
class ProviderStatus:
    """Status information for a provider"""
    provider_id: str
    name: str
    enabled: bool
    healthy: bool
    last_update: float
    response_time_ms: float
    error_count: int
    total_requests: int
    capabilities: List[str]
    config: Dict[str, Any]


@dataclass
class AggregatedContext:
    """Aggregated context from multiple providers"""
    timestamp: float
    provider_responses: Dict[str, MCPContext]
    correlated_insights: Dict[str, Any]
    confidence_score: float
    processing_time_ms: float


class MCPProviderManager:
    """Manager for all MCP context providers"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Provider management
        self.providers: Dict[str, MCPProvider] = {}
        self.provider_status: Dict[str, ProviderStatus] = {}
        self.provider_configs: Dict[str, Dict[str, Any]] = {}
        
        # Performance tracking
        self.request_count = 0
        self.error_count = 0
        self.response_times = []
        self.startup_time = time.time()
        
        # Caching
        self.context_cache: Dict[str, AggregatedContext] = {}
        self.cache_ttl = self.config.get("cache_ttl", 30)  # seconds
        
        # Logging
        self.logger = logging.getLogger(f"mcp_provider_manager")
        
        # Initialize default provider configurations
        self._init_default_configs()
    
    def _init_default_configs(self) -> None:
        """Initialize default provider configurations"""
        self.provider_configs = {
            'filesystem': {
                'monitored_paths': ['~/', '/tmp', '/var/log'],
                'max_files_cached': 10000,
                'update_interval': 30,
                'enable_hashing': False,
                'track_access_patterns': True
            },
            'system': {
                'update_interval': 5,
                'history_size': 1000,
                'track_processes': True,
                'track_network': True,
                'enable_predictions': True
            },
            'security': {
                'update_interval': 10,
                'max_events_history': 10000,
                'enable_real_time': True,
                'auto_response': True
            }
        }
    
    async def initialize(self) -> bool:
        """Initialize all providers"""
        try:
            self.logger.info("Initializing MCP Provider Manager")
            
            # Load provider configurations
            if 'providers' in self.config:
                self.provider_configs.update(self.config['providers'])
            
            # Initialize each provider
            for provider_name, provider_class in PROVIDER_REGISTRY.items():
                await self._initialize_provider(provider_name, provider_class)
            
            # Start health monitoring
            asyncio.create_task(self._health_monitor())
            
            # Start cache cleanup
            asyncio.create_task(self._cache_cleanup())
            
            self.logger.info(f"MCP Provider Manager initialized with {len(self.providers)} providers")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP Provider Manager: {e}")
            return False
    
    async def _initialize_provider(self, provider_name: str, provider_class: Type[MCPProvider]) -> None:
        """Initialize a single provider"""
        try:
            config = self.provider_configs.get(provider_name, {})
            provider = provider_class(config)
            
            # Initialize the provider
            success = await provider.initialize()
            
            if success:
                self.providers[provider_name] = provider
                self.provider_status[provider_name] = ProviderStatus(
                    provider_id=provider.provider_id,
                    name=provider_name,
                    enabled=True,
                    healthy=True,
                    last_update=time.time(),
                    response_time_ms=0,
                    error_count=0,
                    total_requests=0,
                    capabilities=provider.get_capabilities(),
                    config=config
                )
                
                self.logger.info(f"Provider '{provider_name}' initialized successfully")
            else:
                self.logger.error(f"Failed to initialize provider '{provider_name}'")
                
        except Exception as e:
            self.logger.error(f"Error initializing provider '{provider_name}': {e}")
    
    async def get_context(self, request: Dict[str, Any]) -> AggregatedContext:
        """Get aggregated context from providers"""
        start_time = time.time()
        self.request_count += 1
        
        try:
            # Parse request
            providers = request.get('providers', list(self.providers.keys()))
            context_type = request.get('type', 'overview')
            use_cache = request.get('use_cache', True)
            
            # Check cache first
            cache_key = self._generate_cache_key(request)
            if use_cache and cache_key in self.context_cache:
                cached_context = self.context_cache[cache_key]
                if time.time() - cached_context.timestamp < self.cache_ttl:
                    self.logger.debug(f"Cache hit for request: {context_type}")
                    return cached_context
            
            # Collect context from providers
            provider_responses = {}
            tasks = []
            
            for provider_name in providers:
                if provider_name in self.providers and self.provider_status[provider_name].enabled:
                    task = self._get_provider_context(provider_name, request)
                    tasks.append((provider_name, task))
            
            # Execute requests concurrently
            if tasks:
                results = await asyncio.gather(
                    *[task for _, task in tasks],
                    return_exceptions=True
                )
                
                for (provider_name, _), result in zip(tasks, results):
                    if isinstance(result, Exception):
                        self.logger.error(f"Error getting context from {provider_name}: {result}")
                        self._update_provider_error(provider_name)
                    else:
                        provider_responses[provider_name] = result
                        self._update_provider_success(provider_name, result)
            
            # Correlate and analyze the collected context
            correlated_insights = await self._correlate_context(provider_responses, request)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(provider_responses, correlated_insights)
            
            # Create aggregated context
            aggregated_context = AggregatedContext(
                timestamp=time.time(),
                provider_responses=provider_responses,
                correlated_insights=correlated_insights,
                confidence_score=confidence_score,
                processing_time_ms=(time.time() - start_time) * 1000
            )
            
            # Cache the result
            if use_cache:
                self.context_cache[cache_key] = aggregated_context
            
            # Track performance
            processing_time = (time.time() - start_time) * 1000
            self.response_times.append(processing_time)
            if len(self.response_times) > 1000:
                self.response_times = self.response_times[-1000:]
            
            self.logger.debug(f"Context request completed in {processing_time:.2f}ms")
            
            return aggregated_context
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error getting context: {e}")
            
            # Return minimal context on error
            return AggregatedContext(
                timestamp=time.time(),
                provider_responses={},
                correlated_insights={"error": str(e)},
                confidence_score=0.0,
                processing_time_ms=(time.time() - start_time) * 1000
            )
    
    async def _get_provider_context(self, provider_name: str, request: Dict[str, Any]) -> MCPContext:
        """Get context from a specific provider"""
        provider = self.providers[provider_name]
        start_time = time.time()
        
        try:
            # Create provider-specific request
            provider_request = self._create_provider_request(request, provider_name)
            
            # Get context from provider
            context_data = await provider.get_context_data(provider_request)
            
            # Add processing time to metadata
            context_data.metadata['provider_processing_time_ms'] = (time.time() - start_time) * 1000
            
            return context_data
            
        except Exception as e:
            self.logger.error(f"Error getting context from provider {provider_name}: {e}")
            raise
    
    def _create_provider_request(self, request: Dict[str, Any], provider_name: str) -> Dict[str, Any]:
        """Create a provider-specific request"""
        # Start with the original request
        provider_request = request.copy()
        
        # Add provider-specific configurations
        if provider_name in self.provider_configs:
            provider_request.update(self.provider_configs[provider_name])
        
        # Adjust request based on provider capabilities
        if provider_name in self.providers:
            capabilities = self.providers[provider_name].get_capabilities()
            
            # Filter request based on capabilities
            if 'type' in provider_request:
                context_type = provider_request['type']
                if context_type == 'overview':
                    # Overview is always supported
                    pass
                elif not any(cap in context_type for cap in capabilities):
                    # Fallback to overview if specific type not supported
                    provider_request['type'] = 'overview'
        
        return provider_request
    
    async def _correlate_context(self, provider_responses: Dict[str, MCPContext], request: Dict[str, Any]) -> Dict[str, Any]:
        """Correlate and analyze context from multiple providers"""
        insights = {}
        
        try:
            # System health correlation
            if 'system' in provider_responses and 'security' in provider_responses:
                system_data = provider_responses['system'].data
                security_data = provider_responses['security'].data
                
                insights['system_security_correlation'] = self._correlate_system_security(system_data, security_data)
            
            # Filesystem-security correlation
            if 'filesystem' in provider_responses and 'security' in provider_responses:
                fs_data = provider_responses['filesystem'].data
                security_data = provider_responses['security'].data
                
                insights['filesystem_security_correlation'] = self._correlate_filesystem_security(fs_data, security_data)
            
            # Performance insights
            insights['performance_analysis'] = self._analyze_performance(provider_responses)
            
            # Anomaly detection
            insights['anomaly_detection'] = await self._detect_anomalies(provider_responses)
            
            # Recommendations
            insights['recommendations'] = self._generate_recommendations(provider_responses, request)
            
        except Exception as e:
            self.logger.error(f"Error correlating context: {e}")
            insights['correlation_error'] = str(e)
        
        return insights
    
    def _correlate_system_security(self, system_data: Dict[str, Any], security_data: Dict[str, Any]) -> Dict[str, Any]:
        """Correlate system and security data"""
        correlation = {}
        
        try:
            # High CPU usage with security events
            system_cpu = system_data.get('cpu_usage', 0)
            security_events = security_data.get('current_status', {}).get('total_events', 0)
            
            if system_cpu > 80 and security_events > 10:
                correlation['high_cpu_security_events'] = {
                    'severity': 'medium',
                    'description': 'High CPU usage coincides with increased security events',
                    'cpu_usage': system_cpu,
                    'security_events': security_events
                }
            
            # Memory usage and threats
            system_memory = system_data.get('memory_usage', 0)
            active_threats = security_data.get('current_status', {}).get('active_threats', 0)
            
            if system_memory > 85 and active_threats > 0:
                correlation['memory_threat_correlation'] = {
                    'severity': 'high',
                    'description': 'High memory usage with active threats detected',
                    'memory_usage': system_memory,
                    'active_threats': active_threats
                }
            
        except Exception as e:
            correlation['error'] = str(e)
        
        return correlation
    
    def _correlate_filesystem_security(self, fs_data: Dict[str, Any], security_data: Dict[str, Any]) -> Dict[str, Any]:
        """Correlate filesystem and security data"""
        correlation = {}
        
        try:
            # Large file operations with security events
            recent_files = fs_data.get('recent_activity', [])
            security_events = security_data.get('current_status', {}).get('total_events', 0)
            
            large_file_ops = len([f for f in recent_files if f.get('size', 0) > 100 * 1024 * 1024])  # > 100MB
            
            if large_file_ops > 5 and security_events > 5:
                correlation['large_file_security_events'] = {
                    'severity': 'medium',
                    'description': 'Large file operations coincide with security events',
                    'large_file_operations': large_file_ops,
                    'security_events': security_events
                }
            
        except Exception as e:
            correlation['error'] = str(e)
        
        return correlation
    
    def _analyze_performance(self, provider_responses: Dict[str, MCPContext]) -> Dict[str, Any]:
        """Analyze performance across providers"""
        performance = {}
        
        try:
            response_times = {}
            for provider_name, response in provider_responses.items():
                processing_time = response.metadata.get('provider_processing_time_ms', 0)
                response_times[provider_name] = processing_time
            
            if response_times:
                performance['response_times_ms'] = response_times
                performance['avg_response_time_ms'] = sum(response_times.values()) / len(response_times)
                performance['slowest_provider'] = max(response_times.items(), key=lambda x: x[1])
                performance['fastest_provider'] = min(response_times.items(), key=lambda x: x[1])
            
        except Exception as e:
            performance['error'] = str(e)
        
        return performance
    
    async def _detect_anomalies(self, provider_responses: Dict[str, MCPContext]) -> Dict[str, Any]:
        """Detect anomalies across providers"""
        anomalies = {}
        
        try:
            # System anomalies
            if 'system' in provider_responses:
                system_data = provider_responses['system'].data
                health_score = system_data.get('health_score', 100)
                
                if health_score < 70:
                    anomalies['system_health'] = {
                        'type': 'low_health_score',
                        'severity': 'high' if health_score < 50 else 'medium',
                        'health_score': health_score,
                        'description': f'System health score is {health_score}'
                    }
            
            # Security anomalies
            if 'security' in provider_responses:
                security_data = provider_responses['security'].data
                critical_threats = security_data.get('current_status', {}).get('critical_threats', 0)
                
                if critical_threats > 0:
                    anomalies['security_critical_threats'] = {
                        'type': 'critical_threats',
                        'severity': 'critical',
                        'count': critical_threats,
                        'description': f'{critical_threats} critical security threats detected'
                    }
            
        except Exception as e:
            anomalies['detection_error'] = str(e)
        
        return anomalies
    
    def _generate_recommendations(self, provider_responses: Dict[str, MCPContext], request: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on context"""
        recommendations = []
        
        try:
            # System recommendations
            if 'system' in provider_responses:
                system_data = provider_responses['system'].data
                if system_data.get('cpu_usage', 0) > 80:
                    recommendations.append("High CPU usage detected - consider optimizing processes")
                
                if system_data.get('memory_usage', 0) > 85:
                    recommendations.append("High memory usage detected - consider closing applications")
            
            # Security recommendations
            if 'security' in provider_responses:
                security_data = provider_responses['security'].data
                if security_data.get('current_status', {}).get('active_threats', 0) > 5:
                    recommendations.append("Multiple active threats - review security settings")
            
            # Filesystem recommendations
            if 'filesystem' in provider_responses:
                fs_data = provider_responses['filesystem'].data
                space_usage = fs_data.get('statistics', {}).get('free_space', 0)
                total_space = fs_data.get('statistics', {}).get('total_space', 1)
                usage_percent = ((total_space - space_usage) / total_space) * 100
                
                if usage_percent > 90:
                    recommendations.append("Low disk space - consider cleaning up files")
            
        except Exception as e:
            recommendations.append(f"Error generating recommendations: {e}")
        
        return recommendations
    
    def _calculate_confidence_score(self, provider_responses: Dict[str, MCPContext], insights: Dict[str, Any]) -> float:
        """Calculate overall confidence score for the aggregated context"""
        if not provider_responses:
            return 0.0
        
        # Base confidence on number of providers responding
        provider_confidence = len(provider_responses) / len(self.providers) * 50
        
        # Adjust based on response quality
        quality_confidence = 0
        for response in provider_responses.values():
            if hasattr(response, 'metadata') and 'confidence' in response.metadata:
                quality_confidence += response.metadata['confidence']
        
        if provider_responses:
            quality_confidence /= len(provider_responses)
        
        # Adjust based on insights quality
        insights_confidence = 25 if 'correlation_error' not in insights else 10
        
        total_confidence = provider_confidence + quality_confidence + insights_confidence
        return min(100.0, total_confidence)
    
    def _generate_cache_key(self, request: Dict[str, Any]) -> str:
        """Generate cache key for a request"""
        # Create a deterministic key from the request
        key_parts = [
            request.get('type', 'overview'),
            ','.join(sorted(request.get('providers', []))),
            str(request.get('time_range', 0)),
            str(request.get('severity', ''))
        ]
        
        import hashlib
        key_string = '|'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _update_provider_success(self, provider_name: str, response: MCPContext) -> None:
        """Update provider statistics after successful request"""
        if provider_name in self.provider_status:
            status = self.provider_status[provider_name]
            status.total_requests += 1
            status.last_update = time.time()
            status.healthy = True
            
            # Update response time
            if 'provider_processing_time_ms' in response.metadata:
                status.response_time_ms = response.metadata['provider_processing_time_ms']
    
    def _update_provider_error(self, provider_name: str) -> None:
        """Update provider statistics after error"""
        if provider_name in self.provider_status:
            status = self.provider_status[provider_name]
            status.error_count += 1
            status.healthy = False
            
            # Disable provider if too many errors
            if status.error_count > 10:
                status.enabled = False
                self.logger.warning(f"Provider '{provider_name}' disabled due to repeated errors")
    
    async def get_provider_status(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """Get status of providers"""
        if provider_name:
            if provider_name in self.provider_status:
                return asdict(self.provider_status[provider_name])
            else:
                return {"error": f"Provider '{provider_name}' not found"}
        else:
            return {
                "providers": {name: asdict(status) for name, status in self.provider_status.items()},
                "manager_stats": {
                    "uptime_seconds": time.time() - self.startup_time,
                    "total_requests": self.request_count,
                    "error_count": self.error_count,
                    "avg_response_time_ms": sum(self.response_times) / len(self.response_times) if self.response_times else 0,
                    "cache_size": len(self.context_cache)
                }
            }
    
    async def enable_provider(self, provider_name: str) -> bool:
        """Enable a provider"""
        if provider_name in self.provider_status:
            self.provider_status[provider_name].enabled = True
            self.provider_status[provider_name].healthy = True
            self.provider_status[provider_name].error_count = 0
            self.logger.info(f"Provider '{provider_name}' enabled")
            return True
        return False
    
    async def disable_provider(self, provider_name: str) -> bool:
        """Disable a provider"""
        if provider_name in self.provider_status:
            self.provider_status[provider_name].enabled = False
            self.logger.info(f"Provider '{provider_name}' disabled")
            return True
        return False
    
    async def _health_monitor(self) -> None:
        """Monitor provider health"""
        while True:
            try:
                for provider_name, provider in self.providers.items():
                    if provider_name in self.provider_status:
                        status = self.provider_status[provider_name]
                        
                        # Check if provider is responding
                        try:
                            # Simple health check
                            start_time = time.time()
                            await provider.get_context_data({"type": "overview"})
                            response_time = (time.time() - start_time) * 1000
                            
                            status.healthy = True
                            status.response_time_ms = response_time
                            status.last_update = time.time()
                            
                        except Exception as e:
                            self.logger.debug(f"Health check failed for {provider_name}: {e}")
                            status.healthy = False
                            status.error_count += 1
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in health monitor: {e}")
                await asyncio.sleep(60)
    
    async def _cache_cleanup(self) -> None:
        """Clean up expired cache entries"""
        while True:
            try:
                current_time = time.time()
                expired_keys = [
                    key for key, context in self.context_cache.items()
                    if current_time - context.timestamp > self.cache_ttl
                ]
                
                for key in expired_keys:
                    del self.context_cache[key]
                
                if expired_keys:
                    self.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                
                await asyncio.sleep(60)  # Clean up every minute
                
            except Exception as e:
                self.logger.error(f"Error in cache cleanup: {e}")
                await asyncio.sleep(120)
    
    async def cleanup(self) -> None:
        """Cleanup all providers and resources"""
        try:
            # Cleanup all providers
            for provider_name, provider in self.providers.items():
                try:
                    await provider.cleanup()
                    self.logger.info(f"Provider '{provider_name}' cleaned up")
                except Exception as e:
                    self.logger.error(f"Error cleaning up provider '{provider_name}': {e}")
            
            # Clear internal state
            self.providers.clear()
            self.provider_status.clear()
            self.context_cache.clear()
            
            self.logger.info("MCP Provider Manager cleaned up")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def get_capabilities(self) -> Dict[str, List[str]]:
        """Get capabilities of all providers"""
        capabilities = {}
        for provider_name, provider in self.providers.items():
            capabilities[provider_name] = provider.get_capabilities()
        return capabilities