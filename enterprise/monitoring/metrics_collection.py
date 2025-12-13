"""
Aurora OS Metrics Collection System
Comprehensive metrics collection for system monitoring
"""

import asyncio
import json
import logging
import time
import uuid
import psutil
import threading
from typing import Dict, List, Optional, Any, Set, Tuple, Union, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics

class MetricType(Enum):
    """Metric types"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"

class MetricUnit(Enum):
    """Metric units"""
    NONE = ""
    BYTES = "bytes"
    BYTES_PER_SECOND = "bytes/sec"
    SECONDS = "seconds"
    MILLISECONDS = "milliseconds"
    COUNT = "count"
    PERCENT = "percent"
    REQUESTS_PER_SECOND = "req/sec"
    OPERATIONS_PER_SECOND = "ops/sec"

@dataclass
class MetricLabel:
    """Metric label"""
    name: str
    value: str

@dataclass
class Metric:
    """Base metric"""
    name: str
    metric_type: MetricType
    unit: MetricUnit
    description: str
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "unit": self.unit.value,
            "description": self.description,
            "labels": self.labels,
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class CounterMetric(Metric):
    """Counter metric - only increases"""
    value: float = 0.0
    
    def inc(self, amount: float = 1.0):
        """Increment counter"""
        self.value += amount
    
    def get_value(self) -> float:
        """Get current value"""
        return self.value

@dataclass
class GaugeMetric(Metric):
    """Gauge metric - can go up or down"""
    value: float = 0.0
    
    def set(self, value: float):
        """Set gauge value"""
        self.value = value
    
    def inc(self, amount: float = 1.0):
        """Increment gauge"""
        self.value += amount
    
    def dec(self, amount: float = 1.0):
        """Decrement gauge"""
        self.value -= amount
    
    def get_value(self) -> float:
        """Get current value"""
        return self.value

@dataclass
class HistogramMetric(Metric):
    """Histogram metric - distribution of values"""
    buckets: List[float] = field(default_factory=lambda: [0.1, 0.5, 1.0, 2.5, 5.0, 10.0])
    bucket_counts: Dict[float, int] = field(default_factory=dict)
    count: int = 0
    sum: float = 0.0
    
    def __post_init__(self):
        """Initialize bucket counts"""
        for bucket in self.buckets:
            self.bucket_counts[bucket] = 0
    
    def observe(self, value: float):
        """Observe a value"""
        self.count += 1
        self.sum += value
        
        for bucket in self.buckets:
            if value <= bucket:
                self.bucket_counts[bucket] += 1
    
    def get_bucket_counts(self) -> Dict[str, float]:
        """Get bucket counts for Prometheus format"""
        result = {}
        cumulative = 0
        
        for bucket in sorted(self.buckets):
            cumulative += self.bucket_counts[bucket]
            result[f"le_{bucket}"] = cumulative
        
        # Add +Inf bucket
        result["le_+Inf"] = cumulative
        return result
    
    def get_average(self) -> float:
        """Get average value"""
        return self.sum / self.count if self.count > 0 else 0.0

@dataclass
class SummaryMetric(Metric):
    """Summary metric - sliding window of quantiles"""
    max_samples: int = 1000
    age_buckets: int = 10
    samples: deque = field(default_factory=deque)
    
    def observe(self, value: float):
        """Observe a value"""
        if len(self.samples) >= self.max_samples:
            self.samples.popleft()
        self.samples.append(value)
    
    def get_quantile(self, quantile: float) -> float:
        """Get quantile value"""
        if not self.samples:
            return 0.0
        
        sorted_samples = sorted(self.samples)
        index = int(quantile * len(sorted_samples))
        return sorted_samples[min(index, len(sorted_samples) - 1)]
    
    def get_count(self) -> int:
        """Get sample count"""
        return len(self.samples)
    
    def get_sum(self) -> float:
        """Get sum of values"""
        return sum(self.samples)

class MetricsRegistry:
    """Metrics registry"""
    
    def __init__(self):
        self.metrics: Dict[str, Metric] = {}
        self.lock = threading.RLock()
    
    def register_counter(self, name: str, description: str, unit: MetricUnit = MetricUnit.NONE,
                        labels: Dict[str, str] = None) -> CounterMetric:
        """Register a counter metric"""
        with self.lock:
            if name in self.metrics:
                return self.metrics[name]
            
            metric = CounterMetric(
                name=name,
                metric_type=MetricType.COUNTER,
                unit=unit,
                description=description,
                labels=labels or {}
            )
            self.metrics[name] = metric
            return metric
    
    def register_gauge(self, name: str, description: str, unit: MetricUnit = MetricUnit.NONE,
                      labels: Dict[str, str] = None) -> GaugeMetric:
        """Register a gauge metric"""
        with self.lock:
            if name in self.metrics:
                return self.metrics[name]
            
            metric = GaugeMetric(
                name=name,
                metric_type=MetricType.GAUGE,
                unit=unit,
                description=description,
                labels=labels or {}
            )
            self.metrics[name] = metric
            return metric
    
    def register_histogram(self, name: str, description: str, buckets: List[float] = None,
                          unit: MetricUnit = MetricUnit.SECONDS,
                          labels: Dict[str, str] = None) -> HistogramMetric:
        """Register a histogram metric"""
        with self.lock:
            if name in self.metrics:
                return self.metrics[name]
            
            metric = HistogramMetric(
                name=name,
                metric_type=MetricType.HISTOGRAM,
                unit=unit,
                description=description,
                buckets=buckets or [0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
                labels=labels or {}
            )
            self.metrics[name] = metric
            return metric
    
    def register_summary(self, name: str, description: str,
                        unit: MetricUnit = MetricUnit.SECONDS,
                        labels: Dict[str, str] = None) -> SummaryMetric:
        """Register a summary metric"""
        with self.lock:
            if name in self.metrics:
                return self.metrics[name]
            
            metric = SummaryMetric(
                name=name,
                metric_type=MetricType.SUMMARY,
                unit=unit,
                description=description,
                labels=labels or {}
            )
            self.metrics[name] = metric
            return metric
    
    def get_metric(self, name: str) -> Optional[Metric]:
        """Get metric by name"""
        with self.lock:
            return self.metrics.get(name)
    
    def get_all_metrics(self) -> Dict[str, Metric]:
        """Get all metrics"""
        with self.lock:
            return self.metrics.copy()
    
    def to_prometheus_format(self) -> str:
        """Convert all metrics to Prometheus format"""
        with self.lock:
            output = []
            
            for metric in self.metrics.values():
                # Add metric description
                output.append(f"# HELP {metric.name} {metric.description}")
                output.append(f"# TYPE {metric.name} {metric.metric_type.value}")
                
                if isinstance(metric, (CounterMetric, GaugeMetric)):
                    # Simple metrics
                    value_line = f"{metric.name} {metric.get_value()}"
                    output.append(value_line)
                    
                elif isinstance(metric, HistogramMetric):
                    # Histogram with buckets
                    bucket_counts = metric.get_bucket_counts()
                    for bucket, count in bucket_counts.items():
                        bucket_name = f"{metric.name}_bucket"
                        labels_with_le = f'{{le="{bucket}"}}'
                        output.append(f"{bucket_name}{labels_with_le} {count}")
                    
                    # Add count and sum
                    output.append(f"{metric.name}_count {metric.count}")
                    output.append(f"{metric.name}_sum {metric.sum}")
                    
                elif isinstance(metric, SummaryMetric):
                    # Summary with quantiles
                    quantiles = [0.5, 0.9, 0.95, 0.99]
                    for quantile in quantiles:
                        value = metric.get_quantile(quantile)
                        quantile_name = f"{metric.name}"
                        labels_with_quantile = f'{{quantile="{quantile}"}}'
                        output.append(f"{quantile_name}{labels_with_quantile} {value}")
                    
                    # Add count and sum
                    output.append(f"{metric.name}_count {metric.get_count()}")
                    output.append(f"{metric.name}_sum {metric.get_sum()}")
                
                output.append("")  # Empty line between metrics
            
            return "\n".join(output)
    
    def to_json_format(self) -> str:
        """Convert all metrics to JSON format"""
        with self.lock:
            metrics_data = {}
            
            for name, metric in self.metrics.items():
                if isinstance(metric, (CounterMetric, GaugeMetric)):
                    metrics_data[name] = {
                        "type": metric.metric_type.value,
                        "unit": metric.unit.value,
                        "description": metric.description,
                        "labels": metric.labels,
                        "value": metric.get_value()
                    }
                elif isinstance(metric, HistogramMetric):
                    metrics_data[name] = {
                        "type": metric.metric_type.value,
                        "unit": metric.unit.value,
                        "description": metric.description,
                        "labels": metric.labels,
                        "count": metric.count,
                        "sum": metric.sum,
                        "average": metric.get_average(),
                        "buckets": metric.get_bucket_counts()
                    }
                elif isinstance(metric, SummaryMetric):
                    metrics_data[name] = {
                        "type": metric.metric_type.value,
                        "unit": metric.unit.value,
                        "description": metric.description,
                        "labels": metric.labels,
                        "count": metric.get_count(),
                        "sum": metric.get_sum(),
                        "quantiles": {
                            "0.5": metric.get_quantile(0.5),
                            "0.9": metric.get_quantile(0.9),
                            "0.95": metric.get_quantile(0.95),
                            "0.99": metric.get_quantile(0.99)
                        }
                    }
            
            return json.dumps(metrics_data, indent=2)

class SystemMetricsCollector:
    """System metrics collector"""
    
    def __init__(self, registry: MetricsRegistry):
        self.registry = registry
        self.running = False
        self.collection_interval = 30.0  # seconds
        self.thread = None
        
        # Register system metrics
        self._register_system_metrics()
    
    def _register_system_metrics(self):
        """Register system metrics"""
        # CPU metrics
        self.registry.register_gauge(
            "system_cpu_usage_percent",
            "CPU usage percentage",
            MetricUnit.PERCENT
        )
        self.registry.register_gauge(
            "system_cpu_count",
            "Number of CPU cores",
            MetricUnit.COUNT
        )
        
        # Memory metrics
        self.registry.register_gauge(
            "system_memory_usage_bytes",
            "Memory usage in bytes",
            MetricUnit.BYTES
        )
        self.registry.register_gauge(
            "system_memory_total_bytes",
            "Total memory in bytes",
            MetricUnit.BYTES
        )
        self.registry.register_gauge(
            "system_memory_usage_percent",
            "Memory usage percentage",
            MetricUnit.PERCENT
        )
        
        # Disk metrics
        self.registry.register_gauge(
            "system_disk_usage_bytes",
            "Disk usage in bytes",
            MetricUnit.BYTES
        )
        self.registry.register_gauge(
            "system_disk_total_bytes",
            "Total disk space in bytes",
            MetricUnit.BYTES
        )
        self.registry.register_gauge(
            "system_disk_usage_percent",
            "Disk usage percentage",
            MetricUnit.PERCENT
        )
        
        # Network metrics
        self.registry.register_counter(
            "system_network_bytes_sent",
            "Network bytes sent",
            MetricUnit.BYTES
        )
        self.registry.register_counter(
            "system_network_bytes_received",
            "Network bytes received",
            MetricUnit.BYTES
        )
        
        # Process metrics
        self.registry.register_gauge(
            "system_process_count",
            "Number of running processes",
            MetricUnit.COUNT
        )
        self.registry.register_gauge(
            "system_thread_count",
            "Number of threads",
            MetricUnit.COUNT
        )
    
    def start_collection(self):
        """Start metrics collection"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._collection_loop, daemon=True)
        self.thread.start()
    
    def stop_collection(self):
        """Stop metrics collection"""
        self.running = False
        if self.thread:
            self.thread.join()
    
    def _collection_loop(self):
        """Collection loop"""
        while self.running:
            try:
                self._collect_system_metrics()
                time.sleep(self.collection_interval)
            except Exception as e:
                logging.error(f"Error collecting system metrics: {e}")
                time.sleep(5)
    
    def _collect_system_metrics(self):
        """Collect system metrics"""
        # CPU metrics
        cpu_percent = psutil.cpu_percent()
        cpu_count = psutil.cpu_count()
        
        self.registry.get_metric("system_cpu_usage_percent").set(cpu_percent)
        self.registry.get_metric("system_cpu_count").set(cpu_count)
        
        # Memory metrics
        memory = psutil.virtual_memory()
        
        self.registry.get_metric("system_memory_usage_bytes").set(memory.used)
        self.registry.get_metric("system_memory_total_bytes").set(memory.total)
        self.registry.get_metric("system_memory_usage_percent").set(memory.percent)
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        
        self.registry.get_metric("system_disk_usage_bytes").set(disk.used)
        self.registry.get_metric("system_disk_total_bytes").set(disk.total)
        disk_percent = (disk.used / disk.total) * 100
        self.registry.get_metric("system_disk_usage_percent").set(disk_percent)
        
        # Network metrics
        network = psutil.net_io_counters()
        
        self.registry.get_metric("system_network_bytes_sent").inc(network.bytes_sent)
        self.registry.get_metric("system_network_bytes_received").inc(network.bytes_recv)
        
        # Process metrics
        process_count = len(psutil.pids())
        self.registry.get_metric("system_process_count").set(process_count)

# Global registry
_global_registry = MetricsRegistry()

def get_global_registry() -> MetricsRegistry:
    """Get global metrics registry"""
    return _global_registry

def init_system_metrics():
    """Initialize system metrics collection"""
    collector = SystemMetricsCollector(_global_registry)
    collector.start_collection()
    return collector

# Decorators for automatic metrics
def count_calls(metric_name: str = None, labels: Dict[str, str] = None):
    """Decorator to count function calls"""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            registry = get_global_registry()
            name = metric_name or f"function_calls_total"
            
            # Get function name for label
            func_name = f"{func.__module__}.{func.__name__}"
            func_labels = {"function": func_name}
            if labels:
                func_labels.update(labels)
            
            counter = registry.register_counter(name, "Function call count", labels=func_labels)
            counter.inc()
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def measure_latency(metric_name: str = None, labels: Dict[str, str] = None):
    """Decorator to measure function latency"""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            registry = get_global_registry()
            name = metric_name or f"function_latency_seconds"
            
            # Get function name for label
            func_name = f"{func.__module__}.{func.__name__}"
            func_labels = {"function": func_name}
            if labels:
                func_labels.update(labels)
            
            histogram = registry.register_histogram(name, "Function latency", labels=func_labels)
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                latency = time.time() - start_time
                histogram.observe(latency)
        
        return wrapper
    return decorator