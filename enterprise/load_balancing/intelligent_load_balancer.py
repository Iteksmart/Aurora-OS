"""
Aurora OS Intelligent Load Balancer
AI-powered traffic distribution with advanced routing algorithms
"""

import asyncio
import json
import logging
import time
import hashlib
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import aiohttp
import numpy as np
from datetime import datetime, timedelta
import statistics
from collections import defaultdict, deque
import socket

class LoadBalancingAlgorithm(Enum):
    """Load balancing algorithms"""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    AI_POWERED = "ai_powered"
    GEOGRAPHIC = "geographic"
    APPLICATION_AWARE = "application_aware"

class HealthCheckType(Enum):
    """Health check types"""
    HTTP = "http"
    HTTPS = "https"
    TCP = "tcp"
    PING = "ping"
    APPLICATION = "application"

@dataclass
class BackendServer:
    """Backend server information"""
    id: str
    name: str
    ip_address: str
    port: int
    weight: int = 1
    max_connections: int = 1000
    current_connections: int = 0
    status: str = "healthy"
    response_time: float = 0.0
    success_rate: float = 100.0
    cpu_utilization: float = 0.0
    memory_utilization: float = 0.0
    location: str = "default"
    capabilities: List[str] = field(default_factory=list)
    last_health_check: datetime = field(default_factory=datetime.now)
    failure_count: int = 0
    total_requests: int = 0
    failed_requests: int = 0

@dataclass
class LoadBalancingConfig:
    """Load balancer configuration"""
    algorithm: LoadBalancingAlgorithm
    health_check_interval: int = 30
    health_check_timeout: int = 5
    health_check_retries: int = 3
    failure_threshold: int = 3
    recovery_threshold: int = 2
    sticky_sessions: bool = False
    session_timeout: int = 300
    max_retries: int = 3
    retry_delay: float = 1.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60
    geo_routing: bool = False
    ai_weight_factor: float = 0.3

@dataclass
class RequestMetrics:
    """Request metrics for analysis"""
    timestamp: datetime
    backend_id: str
    response_time: float
    status_code: int
    request_size: int
    response_size: int
    user_agent: str
    client_ip: str
    request_path: str

class IntelligentLoadBalancer:
    """AI-powered intelligent load balancer"""
    
    def __init__(self, config: LoadBalancingConfig):
        self.config = config
        self.backends: Dict[str, BackendServer] = {}
        self.request_history: deque = deque(maxlen=10000)
        self.performance_metrics = defaultdict(list)
        self.health_check_task = None
        self.metrics_analytics_task = None
        
        # AI components
        self.performance_predictor = None
        self.anomaly_detector = None
        self.routing_optimizer = None
        
        # Session management
        self.session_affinity: Dict[str, str] = {}
        
        # Circuit breaker state
        self.circuit_breakers: Dict[str, Dict] = {}
        
        # Geographic routing
        self.geo_location_cache: Dict[str, str] = {}
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.initialize_ai_components()

    def initialize_ai_components(self) -> None:
        """Initialize AI components for intelligent routing"""
        try:
            # Initialize performance predictor
            self.performance_predictor = PerformancePredictor()
            
            # Initialize anomaly detector
            self.anomaly_detector = TrafficAnomalyDetector()
            
            # Initialize routing optimizer
            self.routing_optimizer = RoutingOptimizer()
            
            self.logger.info("AI components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AI components: {e}")

    async def start(self) -> None:
        """Start the load balancer"""
        self.logger.info("Starting intelligent load balancer...")
        
        # Start background tasks
        self.health_check_task = asyncio.create_task(self.health_check_loop())
        self.metrics_analytics_task = asyncio.create_task(self.metrics_analytics_loop())
        
        self.logger.info("Load balancer started successfully")

    async def stop(self) -> None:
        """Stop the load balancer"""
        self.logger.info("Stopping load balancer...")
        
        # Cancel background tasks
        if self.health_check_task:
            self.health_check_task.cancel()
        if self.metrics_analytics_task:
            self.metrics_analytics_task.cancel()
        
        await asyncio.gather(
            self.health_check_task, 
            self.metrics_analytics_task,
            return_exceptions=True
        )
        
        self.logger.info("Load balancer stopped")

    def add_backend(self, backend: BackendServer) -> None:
        """Add a backend server"""
        self.backends[backend.id] = backend
        self.circuit_breakers[backend.id] = {
            "state": "closed",
            "failure_count": 0,
            "last_failure": None
        }
        self.logger.info(f"Added backend server: {backend.name}")

    def remove_backend(self, backend_id: str) -> None:
        """Remove a backend server"""
        if backend_id in self.backends:
            backend_name = self.backends[backend_id].name
            del self.backends[backend_id]
            del self.circuit_breakers[backend_id]
            self.logger.info(f"Removed backend server: {backend_name}")

    async def route_request(self, 
                           request_info: Dict[str, Any]) -> Tuple[Optional[BackendServer], str]:
        """Route a request to the optimal backend server"""
        try:
            # Get client information
            client_ip = request_info.get("client_ip", "")
            session_id = request_info.get("session_id", "")
            request_path = request_info.get("path", "")
            user_agent = request_info.get("user_agent", "")
            
            # Check session affinity
            if self.config.sticky_sessions and session_id in self.session_affinity:
                backend_id = self.session_affinity[session_id]
                if self.is_backend_available(backend_id):
                    backend = self.backends[backend_id]
                    return backend, "session_affinity"
            
            # Select backend based on algorithm
            if self.config.algorithm == LoadBalancingAlgorithm.AI_POWERED:
                backend = await self.ai_powered_routing(request_info)
            elif self.config.algorithm == LoadBalancingAlgorithm.GEOGRAPHIC:
                backend = await self.geographic_routing(client_ip)
            elif self.config.algorithm == LoadBalancingAlgorithm.APPLICATION_AWARE:
                backend = await self.application_aware_routing(request_path)
            else:
                backend = self.algorithm_based_routing()
            
            if backend:
                # Update session affinity
                if self.config.sticky_sessions and session_id:
                    self.session_affinity[session_id] = backend.id
                
                # Update connection count
                backend.current_connections += 1
                backend.total_requests += 1
                
                return backend, self.config.algorithm.value
            
            return None, "no_available_backends"
            
        except Exception as e:
            self.logger.error(f"Request routing failed: {e}")
            return None, "routing_error"

    def algorithm_based_routing(self) -> Optional[BackendServer]:
        """Route based on traditional load balancing algorithms"""
        available_backends = [
            backend for backend in self.backends.values()
            if self.is_backend_available(backend.id)
        ]
        
        if not available_backends:
            return None
        
        if self.config.algorithm == LoadBalancingAlgorithm.ROUND_ROBIN:
            return self.round_robin_routing(available_backends)
        elif self.config.algorithm == LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN:
            return self.weighted_round_robin_routing(available_backends)
        elif self.config.algorithm == LoadBalancingAlgorithm.LEAST_CONNECTIONS:
            return self.least_connections_routing(available_backends)
        elif self.config.algorithm == LoadBalancingAlgorithm.LEAST_RESPONSE_TIME:
            return self.least_response_time_routing(available_backends)
        
        return available_backends[0]

    def round_robin_routing(self, backends: List[BackendServer]) -> BackendServer:
        """Round-robin routing"""
        # Simple round-robin based on total requests
        return min(backends, key=lambda b: b.total_requests)

    def weighted_round_robin_routing(self, backends: List[BackendServer]) -> BackendServer:
        """Weighted round-robin routing"""
        # Calculate weighted scores
        weighted_backends = []
        for backend in backends:
            score = backend.weight - (backend.total_requests % backend.weight)
            weighted_backends.append((score, backend))
        
        # Select backend with highest score
        _, selected_backend = max(weighted_backends)
        return selected_backend

    def least_connections_routing(self, backends: List[BackendServer]) -> BackendServer:
        """Route to backend with least connections"""
        return min(backends, key=lambda b: b.current_connections)

    def least_response_time_routing(self, backends: List[BackendServer]) -> BackendServer:
        """Route to backend with least response time"""
        return min(backends, key=lambda b: b.response_time)

    async def ai_powered_routing(self, request_info: Dict[str, Any]) -> Optional[BackendServer]:
        """AI-powered intelligent routing"""
        try:
            available_backends = [
                backend for backend in self.backends.values()
                if self.is_backend_available(backend.id)
            ]
            
            if not available_backends:
                return None
            
            # Get AI recommendation
            recommendation = await self.routing_optimizer.get_routing_recommendation(
                available_backends, request_info, self.performance_metrics
            )
            
            if recommendation and recommendation.get("backend_id"):
                return self.backends.get(recommendation["backend_id"])
            
            # Fallback to least response time
            return self.least_response_time_routing(available_backends)
            
        except Exception as e:
            self.logger.error(f"AI-powered routing failed: {e}")
            return self.algorithm_based_routing()

    async def geographic_routing(self, client_ip: str) -> Optional[BackendServer]:
        """Geographic-based routing"""
        try:
            # Get client location
            client_location = await self.get_client_location(client_ip)
            
            # Find closest backend
            available_backends = [
                backend for backend in self.backends.values()
                if self.is_backend_available(backend.id)
            ]
            
            if not available_backends:
                return None
            
            # Calculate geographic distance (simplified)
            closest_backend = min(
                available_backends,
                key=lambda b: self.calculate_geo_distance(client_location, b.location)
            )
            
            return closest_backend
            
        except Exception as e:
            self.logger.error(f"Geographic routing failed: {e}")
            return self.algorithm_based_routing()

    async def application_aware_routing(self, request_path: str) -> Optional[BackendServer]:
        """Application-aware routing based on request type"""
        try:
            # Analyze request path to determine application type
            app_type = self.classify_application_type(request_path)
            
            # Find backends with appropriate capabilities
            suitable_backends = [
                backend for backend in self.backends.values()
                if (self.is_backend_available(backend.id) and 
                    app_type in backend.capabilities)
            ]
            
            if not suitable_backends:
                # Fallback to any available backend
                suitable_backends = [
                    backend for backend in self.backends.values()
                    if self.is_backend_available(backend.id)
                ]
            
            if suitable_backends:
                return self.least_response_time_routing(suitable_backends)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Application-aware routing failed: {e}")
            return self.algorithm_based_routing()

    def classify_application_type(self, request_path: str) -> str:
        """Classify application type based on request path"""
        path_lower = request_path.lower()
        
        if "/api/" in path_lower:
            return "api"
        elif "/static/" in path_lower or "/assets/" in path_lower:
            return "static"
        elif "/admin/" in path_lower:
            return "admin"
        elif "/database/" in path_lower:
            return "database"
        else:
            return "web"

    def is_backend_available(self, backend_id: str) -> bool:
        """Check if backend is available for routing"""
        backend = self.backends.get(backend_id)
        if not backend:
            return False
        
        # Check circuit breaker
        circuit_breaker = self.circuit_breakers.get(backend_id, {})
        if circuit_breaker.get("state") == "open":
            # Check if circuit should be half-open
            last_failure = circuit_breaker.get("last_failure")
            if (last_failure and 
                (datetime.now() - last_failure).seconds > self.config.circuit_breaker_timeout):
                circuit_breaker["state"] = "half_open"
            else:
                return False
        
        # Check backend health and capacity
        return (backend.status == "healthy" and 
                backend.current_connections < backend.max_connections)

    async def get_client_location(self, client_ip: str) -> str:
        """Get client geographic location"""
        # Check cache first
        if client_ip in self.geo_location_cache:
            return self.geo_location_cache[client_ip]
        
        # Simple IP-based location (in real implementation, use GeoIP database)
        if client_ip.startswith("192.168.") or client_ip.startswith("10."):
            location = "local"
        elif client_ip.startswith("172."):
            location = "private"
        else:
            # For demo purposes, use simple heuristics
            if "us" in client_ip or client_ip.endswith(".com"):
                location = "us"
            elif "eu" in client_ip or client_ip.endswith(".eu"):
                location = "eu"
            else:
                location = "global"
        
        # Cache the result
        self.geo_location_cache[client_ip] = location
        return location

    def calculate_geo_distance(self, location1: str, location2: str) -> int:
        """Calculate geographic distance (simplified)"""
        if location1 == location2:
            return 0
        elif location1 == "local" or location2 == "local":
            return 1
        elif (location1 in ["us", "eu"] and location2 in ["us", "eu"]):
            return 2
        else:
            return 3

    async def record_request_result(self, 
                                   backend_id: str, 
                                   response_time: float, 
                                   status_code: int,
                                   request_info: Dict[str, Any]) -> None:
        """Record request result for analytics"""
        try:
            backend = self.backends.get(backend_id)
            if not backend:
                return
            
            # Update backend metrics
            backend.response_time = (backend.response_time * 0.8 + response_time * 0.2)
            backend.current_connections = max(0, backend.current_connections - 1)
            
            # Update success rate
            if status_code >= 500:
                backend.failed_requests += 1
                backend.failure_count += 1
                
                # Update circuit breaker
                await self.update_circuit_breaker(backend_id)
            
            backend.success_rate = ((backend.total_requests - backend.failed_requests) / 
                                 max(1, backend.total_requests)) * 100
            
            # Record request metrics
            metrics = RequestMetrics(
                timestamp=datetime.now(),
                backend_id=backend_id,
                response_time=response_time,
                status_code=status_code,
                request_size=request_info.get("request_size", 0),
                response_size=request_info.get("response_size", 0),
                user_agent=request_info.get("user_agent", ""),
                client_ip=request_info.get("client_ip", ""),
                request_path=request_info.get("path", "")
            )
            
            self.request_history.append(metrics)
            
            # Update performance metrics for AI
            self.performance_metrics[backend_id].append({
                "timestamp": metrics.timestamp,
                "response_time": response_time,
                "success": status_code < 500
            })
            
            # Keep only recent metrics
            if len(self.performance_metrics[backend_id]) > 1000:
                self.performance_metrics[backend_id] = self.performance_metrics[backend_id][-1000:]
            
        except Exception as e:
            self.logger.error(f"Failed to record request result: {e}")

    async def update_circuit_breaker(self, backend_id: str) -> None:
        """Update circuit breaker state"""
        circuit_breaker = self.circuit_breakers.get(backend_id, {})
        if not circuit_breaker:
            return
        
        circuit_breaker["failure_count"] += 1
        circuit_breaker["last_failure"] = datetime.now()
        
        if circuit_breaker["failure_count"] >= self.config.circuit_breaker_threshold:
            circuit_breaker["state"] = "open"
            self.logger.warning(f"Circuit breaker opened for backend: {backend_id}")

    async def health_check_loop(self) -> None:
        """Continuous health check loop"""
        while True:
            try:
                await self.perform_health_checks()
                await asyncio.sleep(self.config.health_check_interval)
                
            except Exception as e:
                self.logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(self.config.health_check_interval * 2)

    async def perform_health_checks(self) -> None:
        """Perform health checks on all backends"""
        tasks = []
        for backend_id, backend in self.backends.items():
            task = asyncio.create_task(self.check_backend_health(backend_id, backend))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def check_backend_health(self, backend_id: str, backend: BackendServer) -> None:
        """Check health of a specific backend"""
        try:
            # Perform TCP connection test
            start_time = time.time()
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config.health_check_timeout)
            
            result = sock.connect_ex((backend.ip_address, backend.port))
            sock.close()
            
            response_time = (time.time() - start_time) * 1000
            
            if result == 0:
                # Backend is healthy
                backend.status = "healthy"
                backend.failure_count = 0
                backend.response_time = response_time
                
                # Update circuit breaker
                circuit_breaker = self.circuit_breakers.get(backend_id, {})
                if circuit_breaker.get("state") == "half_open":
                    circuit_breaker["state"] = "closed"
                    circuit_breaker["failure_count"] = 0
                
            else:
                # Backend is unhealthy
                backend.failure_count += 1
                if backend.failure_count >= self.config.failure_threshold:
                    backend.status = "unhealthy"
            
            backend.last_health_check = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Health check failed for {backend.name}: {e}")
            backend.failure_count += 1
            if backend.failure_count >= self.config.failure_threshold:
                backend.status = "unhealthy"

    async def metrics_analytics_loop(self) -> None:
        """Analyze metrics and optimize routing"""
        while True:
            try:
                await self.analyze_performance_metrics()
                await self.optimize_routing_rules()
                await asyncio.sleep(300)  # Analyze every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Metrics analytics loop error: {e}")
                await asyncio.sleep(600)

    async def analyze_performance_metrics(self) -> None:
        """Analyze performance metrics and identify patterns"""
        if len(self.request_history) < 100:
            return
        
        try:
            # Get recent metrics
            recent_requests = list(self.request_history)[-1000:]
            
            # Analyze performance patterns
            backend_performance = defaultdict(list)
            for metrics in recent_requests:
                backend_performance[metrics.backend_id].append(metrics.response_time)
            
            # Update AI components with new data
            for backend_id, response_times in backend_performance.items():
                if self.performance_predictor:
                    await self.performance_predictor.update_model(
                        backend_id, response_times
                    )
            
            # Detect anomalies
            if self.anomaly_detector:
                anomalies = await self.anomaly_detector.detect_anomalies(recent_requests)
                for anomaly in anomalies:
                    self.logger.warning(f"Traffic anomaly detected: {anomaly}")
            
        except Exception as e:
            self.logger.error(f"Performance analysis failed: {e}")

    async def optimize_routing_rules(self) -> None:
        """Optimize routing rules based on performance data"""
        try:
            if not self.routing_optimizer:
                return
            
            # Collect performance data
            performance_data = {}
            for backend_id, metrics_list in self.performance_metrics.items():
                if metrics_list:
                    recent_metrics = metrics_list[-100:]  # Last 100 metrics
                    performance_data[backend_id] = {
                        "avg_response_time": np.mean([m["response_time"] for m in recent_metrics]),
                        "success_rate": np.mean([m["success"] for m in recent_metrics]) * 100,
                        "request_count": len(recent_metrics)
                    }
            
            # Optimize routing weights
            if performance_data:
                optimization_result = await self.routing_optimizer.optimize_weights(
                    performance_data, self.backends
                )
                
                # Apply optimized weights
                for backend_id, weight in optimization_result.get("weights", {}).items():
                    if backend_id in self.backends:
                        self.backends[backend_id].weight = weight
                        
        except Exception as e:
            self.logger.error(f"Routing optimization failed: {e}")

    def get_load_balancer_stats(self) -> Dict[str, Any]:
        """Get comprehensive load balancer statistics"""
        total_requests = sum(b.total_requests for b in self.backends.values())
        total_connections = sum(b.current_connections for b in self.backends.values())
        
        backend_stats = []
        for backend in self.backends.values():
            backend_stats.append({
                "id": backend.id,
                "name": backend.name,
                "status": backend.status,
                "current_connections": backend.current_connections,
                "total_requests": backend.total_requests,
                "success_rate": backend.success_rate,
                "response_time": backend.response_time,
                "weight": backend.weight
            })
        
        return {
            "algorithm": self.config.algorithm.value,
            "total_backends": len(self.backends),
            "healthy_backends": len([b for b in self.backends.values() if b.status == "healthy"]),
            "total_requests": total_requests,
            "total_connections": total_connections,
            "circuit_breakers": self.circuit_breakers,
            "backend_stats": backend_stats
        }


class PerformancePredictor:
    """Predict backend performance based on historical data"""
    
    def __init__(self):
        self.models = {}
        
    async def update_model(self, backend_id: str, response_times: List[float]) -> None:
        """Update performance prediction model for backend"""
        # Simple moving average prediction
        if len(response_times) >= 10:
            self.models[backend_id] = {
                "avg_response_time": statistics.mean(response_times[-50:]),
                "std_response_time": statistics.stdev(response_times[-50:]) if len(response_times[-50:]) > 1 else 0,
                "trend": self.calculate_trend(response_times[-20:])
            }
    
    def calculate_trend(self, values: List[float]) -> float:
        """Calculate trend in response times"""
        if len(values) < 2:
            return 0.0
        return (values[-1] - values[0]) / len(values)


class TrafficAnomalyDetector:
    """Detect anomalies in traffic patterns"""
    
    def __init__(self):
        self.baseline_metrics = {}
        
    async def detect_anomalies(self, recent_requests: List[RequestMetrics]) -> List[Dict[str, Any]]:
        """Detect anomalies in recent requests"""
        anomalies = []
        
        # Check for unusual response times
        response_times = [r.response_time for r in recent_requests]
        if len(response_times) > 50:
            avg_time = statistics.mean(response_times)
            std_time = statistics.stdev(response_times) if len(response_times) > 1 else 0
            
            # Flag unusually slow responses
            threshold = avg_time + (2 * std_time)
            slow_requests = [r for r in recent_requests if r.response_time > threshold]
            
            if len(slow_requests) > len(recent_requests) * 0.1:  # More than 10% slow
                anomalies.append({
                    "type": "slow_response_times",
                    "count": len(slow_requests),
                    "threshold": threshold
                })
        
        return anomalies


class RoutingOptimizer:
    """Optimize routing weights based on performance"""
    
    def __init__(self):
        pass
    
    async def get_routing_recommendation(self, 
                                       backends: List[BackendServer],
                                       request_info: Dict[str, Any],
                                       performance_metrics: Dict) -> Optional[Dict[str, Any]]:
        """Get AI-powered routing recommendation"""
        try:
            # Score each backend based on multiple factors
            backend_scores = {}
            
            for backend in backends:
                score = 0.0
                
                # Response time factor (lower is better)
                if backend.response_time > 0:
                    score += 100 / backend.response_time
                
                # Success rate factor
                score += backend.success_rate
                
                # Connection load factor
                load_factor = 1 - (backend.current_connections / backend.max_connections)
                score += load_factor * 50
                
                # Weight factor
                score += backend.weight * 10
                
                backend_scores[backend.id] = score
            
            # Select best backend
            if backend_scores:
                best_backend_id = max(backend_scores, key=backend_scores.get)
                return {
                    "backend_id": best_backend_id,
                    "confidence": 0.8,
                    "reasoning": "Multi-factor scoring algorithm"
                }
            
            return None
            
        except Exception as e:
            return None
    
    async def optimize_weights(self, 
                             performance_data: Dict[str, Any],
                             backends: Dict[str, BackendServer]) -> Dict[str, Any]:
        """Optimize backend weights based on performance"""
        optimized_weights = {}
        
        for backend_id, data in performance_data.items():
            if backend_id in backends:
                # Calculate weight based on performance
                base_weight = backends[backend_id].weight
                
                # Adjust weight based on response time
                response_time_factor = max(0.1, 100 / max(1, data["avg_response_time"]))
                
                # Adjust weight based on success rate
                success_rate_factor = data["success_rate"] / 100
                
                # Calculate optimized weight
                optimized_weight = base_weight * response_time_factor * success_rate_factor
                optimized_weights[backend_id] = max(1, int(optimized_weight))
        
        return {"weights": optimized_weights}