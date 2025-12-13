"""
Aurora OS Comprehensive Metrics Collection System
Advanced metrics collection with aggregation and storage
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Set, Tuple, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor

class MetricType(Enum):
    """Metric types"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    TIMER = "timer"

class MetricUnit(Enum):
    """Metric units"""
    NONE = "none"
    BYTES = "bytes"
    SECONDS = "seconds"
    MILLISECONDS = "milliseconds"
    COUNT = "count"
    PERCENTAGE = "percentage"
    RATE = "rate"
    REQUESTS_PER_SECOND = "requests_per_second"

@dataclass
class MetricValue:
    """Single metric value with metadata"""
    name: str
    value: Union[int, float]
    metric_type: MetricType
    unit: MetricUnit
    labels: Dict[str, str]
    timestamp: datetime
    source: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "value": self.value,
            "metric_type": self.metric_type.value,
            "unit": self.unit.value,
            "labels": self.labels,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source
        }

@dataclass
class HistogramBucket:
    """Histogram bucket"""
    upper_bound: float
    count: int

@dataclass
class MetricSummary:
    """Metric summary statistics"""
    count: int
    sum: float
    min: float
    max: float
    mean: float
    median: float
    p95: float
    p99: float
    std_dev: float

class MetricAggregator:
    """Aggregates metric values"""
    
    def __init__(self, name: str, metric_type: MetricType, 
                 aggregation_window: timedelta = timedelta(minutes=5)):
        self.name = name
        self.metric_type = metric_type
        self.aggregation_window = aggregation_window
        
        # Time windowed values
        self.values: deque = deque()
        self.lock = threading.RLock()
        
        # Cached aggregates
        self._last_aggregate = None
        self._last_aggregate_time = 0
    
    def add_value(self, value: MetricValue):
        """Add value to aggregator"""
        with self.lock:
            self.values.append(value)
            
            # Remove old values outside window
            cutoff_time = datetime.now() - self.aggregation_window
            while self.values and self.values[0].timestamp < cutoff_time:
                self.values.popleft()
    
    def aggregate(self) -> Dict[str, Any]:
        """Aggregate values in current window"""
        with self.lock:
            if not self.values:
                return {"count": 0, "sum": 0}
            
            current_time = time.time()
            
            # Use cached result if recent
            if (self._last_aggregate and 
                current_time - self._last_aggregate_time < 1.0):
                return self._last_aggregate
            
            values = [v.value for v in self.values]
            
            if self.metric_type == MetricType.COUNTER:
                result = {
                    "count": len(values),
                    "sum": sum(values),
                    "rate": len(values) / self.aggregation_window.total_seconds()
                }
            elif self.metric_type == MetricType.GAUGE:
                result = {
                    "count": len(values),
                    "current": values[-1] if values else 0,
                    "min": min(values),
                    "max": max(values),
                    "mean": statistics.mean(values)
                }
            elif self.metric_type in [MetricType.HISTOGRAM, MetricType.TIMER]:
                result = {
                    "count": len(values),
                    "sum": sum(values),
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "min": min(values),
                    "max": max(values),
                    "p95": self._percentile(values, 95),
                    "p99": self._percentile(values, 99),
                    "std_dev": statistics.stdev(values) if len(values) > 1 else 0
                }
            else:
                result = {"count": len(values), "sum": sum(values)}
            
            # Cache result
            self._last_aggregate = result
            self._last_aggregate_time = current_time
            
            return result
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]

class MetricsCollector:
    """Comprehensive metrics collection system"""
    
    def __init__(self, collection_interval: float = 10.0):
        self.logger = logging.getLogger(__name__)
        self.collection_interval = collection_interval
        
        # Metrics storage
        self.metrics: Dict[str, MetricAggregator] = {}
        self.metric_definitions: Dict[str, Dict[str, Any]] = {}
        
        # Background collection
        self.collectors: Dict[str, Callable] = {}
        self.background_tasks: List[asyncio.Task] = []
        
        # Buffer for collected metrics
        self.metrics_buffer: deque = deque(maxlen=100000)
        
        # Statistics
        self.stats = {
            "metrics_collected": 0,
            "metrics_defined": 0,
            "collectors_registered": 0,
            "collection_errors": 0
        }
        
        # Thread pool for synchronous collectors
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        # Running state
        self._running = False
    
    def define_metric(self, name: str, metric_type: MetricType, 
                     unit: MetricUnit = MetricUnit.NONE,
                     description: str = "", labels: List[str] = None):
        """Define a new metric"""
        with self._lock:
            if name in self.metric_definitions:
                self.logger.warning(f"Metric {name} already defined, updating")
            
            self.metric_definitions[name] = {
                "type": metric_type,
                "unit": unit,
                "description": description,
                "labels": labels or []
            }
            
            # Create aggregator
            if name not in self.metrics:
                self.metrics[name] = MetricAggregator(name, metric_type)
            
            self.stats["metrics_defined"] += 1
            self.logger.debug(f"Defined metric: {name} ({metric_type.value})")
    
    def record_metric(self, name: str, value: Union[int, float],
                     labels: Dict[str, str] = None, source: str = "system"):
        """Record a metric value"""
        with self._lock:
            if name not in self.metric_definitions:
                self.logger.warning(f"Undefined metric: {name}")
                return
            
            metric_def = self.metric_definitions[name]
            
            # Create metric value
            metric_value = MetricValue(
                name=name,
                value=value,
                metric_type=metric_def["type"],
                unit=metric_def["unit"],
                labels=labels or {},
                timestamp=datetime.now(),
                source=source
            )
            
            # Add to aggregator
            self.metrics[name].add_value(metric_value)
            
            # Add to buffer
            self.metrics_buffer.append(metric_value)
            
            self.stats["metrics_collected"] += 1
    
    def increment_counter(self, name: str, value: int = 1, 
                         labels: Dict[str, str] = None):
        """Increment counter metric"""
        self.record_metric(name, value, labels, "system")
    
    def set_gauge(self, name: str, value: float, 
                 labels: Dict[str, str] = None):
        """Set gauge metric value"""
        self.record_metric(name, value, labels, "system")
    
    def record_timer(self, name: str, duration_seconds: float,
                    labels: Dict[str, str] = None):
        """Record timer metric"""
        self.record_metric(name, duration_seconds, labels, "system")
    
    def register_collector(self, name: str, collector_func: Callable,
                          interval: Optional[float] = None):
        """Register a background collector function"""
        with self._lock:
            self.collectors[name] = {
                "func": collector_func,
                "interval": interval or self.collection_interval,
                "last_run": 0
            }
            
            self.stats["collectors_registered"] += 1
            self.logger.debug(f"Registered collector: {name}")
    
    async def start_collection(self):
        """Start background metrics collection"""
        if self._running:
            return
        
        self._running = True
        self.logger.info("Starting metrics collection")
        
        # Start collector tasks
        for name, collector_info in self.collectors.items():
            task = asyncio.create_task(
                self._collector_loop(name, collector_info)
            )
            self.background_tasks.append(task)
        
        # Start cleanup task
        cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.background_tasks.append(cleanup_task)
    
    async def stop_collection(self):
        """Stop background metrics collection"""
        self._running = False
        
        # Cancel all background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Wait for tasks to finish
        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        self.background_tasks.clear()
        self.logger.info("Stopped metrics collection")
    
    async def _collector_loop(self, name: str, collector_info: Dict[str, Any]):
        """Background collector loop"""
        collector_func = collector_info["func"]
        interval = collector_info["interval"]
        
        while self._running:
            try:
                # Check if it's time to run
                current_time = time.time()
                if current_time - collector_info["last_run"] >= interval:
                    
                    # Run collector
                    if asyncio.iscoroutinefunction(collector_func):
                        await collector_func()
                    else:
                        # Run synchronous collector in thread pool
                        await asyncio.get_event_loop().run_in_executor(
                            self.executor, collector_func
                        )
                    
                    collector_info["last_run"] = current_time
                
                await asyncio.sleep(1)  # Check every second
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in collector {name}: {e}")
                self.stats["collection_errors"] += 1
                await asyncio.sleep(5)  # Wait before retry
    
    async def _cleanup_loop(self):
        """Cleanup old metrics"""
        while self._running:
            try:
                # Cleanup old aggregators (implement logic if needed)
                await asyncio.sleep(300)  # Every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup: {e}")
                await asyncio.sleep(30)
    
    def get_metric(self, name: str) -> Dict[str, Any]:
        """Get aggregated metric data"""
        with self._lock:
            if name not in self.metrics:
                return {"error": f"Metric {name} not found"}
            
            aggregator = self.metrics[name]
            aggregated = aggregator.aggregate()
            
            # Add metric definition info
            if name in self.metric_definitions:
                metric_def = self.metric_definitions[name]
                aggregated.update({
                    "name": name,
                    "type": metric_def["type"].value,
                    "unit": metric_def["unit"].value,
                    "description": metric_def["description"],
                    "labels": metric_def["labels"]
                })
            
            return aggregated
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all aggregated metrics"""
        with self._lock:
            result = {}
            for name in self.metrics:
                result[name] = self.get_metric(name)
            return result
    
    def get_recent_metrics(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get recent raw metric values"""
        recent = list(self.metrics_buffer)[-limit:]
        return [metric.to_dict() for metric in recent]
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics collection summary"""
        with self._lock:
            return {
                "stats": self.stats.copy(),
                "metrics_defined": len(self.metric_definitions),
                "collectors_active": len(self.collectors),
                "buffer_size": len(self.metrics_buffer),
                "aggregators": len(self.metrics)
            }
    
    def export_prometheus_format(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        
        with self._lock:
            for name, aggregator in self.metrics.items():
                if name not in self.metric_definitions:
                    continue
                
                metric_def = self.metric_definitions[name]
                aggregated = aggregator.aggregate()
                
                # Generate Prometheus format lines
                if metric_def["type"] == MetricType.COUNTER:
                    lines.append(f"# HELP {name} {metric_def['description']}")
                    lines.append(f"# TYPE {name} counter")
                    lines.append(f"{name} {aggregated.get('sum', 0)}")
                
                elif metric_def["type"] == MetricType.GAUGE:
                    lines.append(f"# HELP {name} {metric_def['description']}")
                    lines.append(f"# TYPE {name} gauge")
                    lines.append(f"{name} {aggregated.get('current', 0)}")
                
                elif metric_def["type"] in [MetricType.HISTOGRAM, MetricType.TIMER]:
                    lines.append(f"# HELP {name} {metric_def['description']}")
                    lines.append(f"# TYPE {name} histogram")
                    lines.append(f"{name}_sum {aggregated.get('sum', 0)}")
                    lines.append(f"{name}_count {aggregated.get('count', 0)}")
                    lines.append(f"{name}_bucket{{le=&quot;+Inf&quot;}} {aggregated.get('count', 0)}")
        
        return "\n".join(lines)
    
    def export_json_format(self) -> str:
        """Export metrics in JSON format"""
        return json.dumps(self.get_all_metrics(), indent=2)

# Predefined metric collectors
class SystemMetricsCollector:
    """System metrics collector"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.psutil = None
        
        # Import psutil if available
        try:
            import psutil
            self.psutil = psutil
        except ImportError:
            self.logger.warning("psutil not available, system metrics limited")
    
    def define_metrics(self):
        """Define system metrics"""
        self.metrics.define_metric("system_cpu_usage", MetricType.GAUGE, MetricUnit.PERCENTAGE, 
                                  "CPU usage percentage", ["core"])
        self.metrics.define_metric("system_memory_usage", MetricType.GAUGE, MetricUnit.PERCENTAGE,
                                  "Memory usage percentage", ["type"])
        self.metrics.define_metric("system_disk_usage", MetricType.GAUGE, MetricUnit.PERCENTAGE,
                                  "Disk usage percentage", ["device"])
        self.metrics.define_metric("system_network_bytes", MetricType.COUNTER, MetricUnit.BYTES,
                                  "Network bytes transferred", ["direction", "interface"])
        self.metrics.define_metric("system_process_count", MetricType.GAUGE, MetricUnit.COUNT,
                                  "Number of processes", ["status"])
    
    async def collect(self):
        """Collect system metrics"""
        if not self.psutil:
            return
        
        try:
            # CPU metrics
            cpu_percent = self.psutil.cpu_percent(interval=1)
            self.metrics.set_gauge("system_cpu_usage", cpu_percent, {"core": "all"})
            
            # Per-core CPU
            cpu_percents = self.psutil.cpu_percent(interval=1, percpu=True)
            for i, percent in enumerate(cpu_percents):
                self.metrics.set_gauge("system_cpu_usage", percent, {"core": str(i)})
            
            # Memory metrics
            memory = self.psutil.virtual_memory()
            self.metrics.set_gauge("system_memory_usage", memory.percent, {"type": "total"})
            
            swap = self.psutil.swap_memory()
            self.metrics.set_gauge("system_memory_usage", swap.percent, {"type": "swap"})
            
            # Disk metrics
            for partition in self.psutil.disk_partitions():
                try:
                    usage = self.psutil.disk_usage(partition.mountpoint)
                    self.metrics.set_gauge("system_disk_usage", 
                                         usage.percent, {"device": partition.device})
                except PermissionError:
                    continue
            
            # Network metrics
            net_io = self.psutil.net_io_counters()
            self.metrics.increment_counter("system_network_bytes", net_io.bytes_sent, 
                                         {"direction": "sent", "interface": "all"})
            self.metrics.increment_counter("system_network_bytes", net_io.bytes_recv,
                                         {"direction": "received", "interface": "all"})
            
            # Process metrics
            processes = list(self.psutil.process_iter())
            self.metrics.set_gauge("system_process_count", len(processes), {"status": "running"})
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")

class ApplicationMetricsCollector:
    """Application metrics collector"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.request_counts = defaultdict(int)
        self.response_times = deque(maxlen=10000)
        self.error_counts = defaultdict(int)
    
    def define_metrics(self):
        """Define application metrics"""
        self.metrics.define_metric("http_requests_total", MetricType.COUNTER, MetricUnit.COUNT,
                                  "Total HTTP requests", ["method", "status", "endpoint"])
        self.metrics.define_metric("http_response_time", MetricType.HISTOGRAM, MetricUnit.MILLISECONDS,
                                  "HTTP response time", ["method", "endpoint"])
        self.metrics.define_metric("http_errors_total", MetricType.COUNTER, MetricUnit.COUNT,
                                  "Total HTTP errors", ["method", "status", "endpoint"])
        self.metrics.define_metric("active_connections", MetricType.GAUGE, MetricUnit.COUNT,
                                  "Active connections", ["type"])
    
    def record_request(self, method: str, status: int, endpoint: str, response_time: float):
        """Record HTTP request"""
        labels = {"method": method, "status": str(status), "endpoint": endpoint}
        
        self.metrics.increment_counter("http_requests_total", 1, labels)
        self.metrics.record_timer("http_response_time", response_time, labels)
        
        if status >= 400:
            self.metrics.increment_counter("http_errors_total", 1, labels)
    
    def set_active_connections(self, count: int, connection_type: str = "all"):
        """Set active connections count"""
        self.metrics.set_gauge("active_connections", count, {"type": connection_type})

# Global metrics collector instance
_metrics_collector = None

def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector

def init_metrics_collection():
    """Initialize metrics collection with default collectors"""
    collector = get_metrics_collector()
    
    # Register default collectors
    system_collector = SystemMetricsCollector(collector)
    system_collector.define_metrics()
    collector.register_collector("system", system_collector.collect)
    
    app_collector = ApplicationMetricsCollector(collector)
    app_collector.define_metrics()
    
    return collector