"""
Aurora OS Performance Profiling Tools
Advanced performance profiling and analysis for system optimization
"""

import asyncio
import json
import logging
import time
import uuid
import cProfile
import pstats
import io
import threading
import psutil
import tracemalloc
from typing import Dict, List, Optional, Any, Set, Tuple, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics
from concurrent.futures import ThreadPoolExecutor

class ProfilingType(Enum):
    """Profiling types"""
    CPU = "cpu"
    MEMORY = "memory"
    IO = "io"
    NETWORK = "network"
    DATABASE = "database"
    APPLICATION = "application"

class ProfilingMode(Enum):
    """Profiling modes"""
    CONTINUOUS = "continuous"
    SAMPLING = "sampling"
    EVENT_BASED = "event_based"
    ON_DEMAND = "on_demand"

class MetricType(Enum):
    """Performance metric types"""
    EXECUTION_TIME = "execution_time"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    IO_OPERATIONS = "io_operations"
    NETWORK_BANDWIDTH = "network_bandwidth"
    CACHE_HIT_RATE = "cache_hit_rate"
    THROUGHPUT = "throughput"
    LATENCY = "latency"

@dataclass
class PerformanceMetric:
    """Performance metric"""
    name: str
    metric_type: MetricType
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str]
    context: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "metric_type": self.metric_type.value,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
            "context": self.context
        }

@dataclass
class ProfiledFunction:
    """Profiled function information"""
    name: str
    module: str
    line_number: int
    call_count: int
    total_time: float
    average_time: float
    max_time: float
    min_time: float
    std_dev: float
    percentage_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "module": self.module,
            "line_number": self.line_number,
            "call_count": self.call_count,
            "total_time": self.total_time,
            "average_time": self.average_time,
            "max_time": self.max_time,
            "min_time": self.min_time,
            "std_dev": self.std_dev,
            "percentage_time": self.percentage_time
        }

@dataclass
class ProfiledMemoryAllocation:
    """Memory allocation profile"""
    filename: str
    line_number: int
    size: int
    count: int
    total_size: int
    average_size: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "filename": self.filename,
            "line_number": self.line_number,
            "size": self.size,
            "count": self.count,
            "total_size": self.total_size,
            "average_size": self.average_size
        }

class PerformanceProfiler:
    """Main performance profiler"""
    
    def __init__(self, sampling_interval: float = 1.0):
        self.logger = logging.getLogger(__name__)
        self.sampling_interval = sampling_interval
        
        # Profiling state
        self.profiler_enabled = False
        self.profiler_mode = ProfilingMode.SAMPLING
        
        # CPU profiling
        self.cpu_profiler = None
        self.cpu_stats = None
        
        # Memory profiling
        self.memory_profiling_enabled = False
        self.memory_snapshots = []
        
        # Performance metrics
        self.metrics_buffer: deque = deque(maxlen=100000)
        self.function_profiles: Dict[str, List[float]] = defaultdict(list)
        
        # System monitoring
        self.system_metrics: deque = deque(maxlen=1000)
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        
        # Thread pool
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        # Statistics
        self.stats = {
            "profiles_collected": 0,
            "metrics_recorded": 0,
            "functions_profiled": 0,
            "memory_snapshots": 0,
            "profiling_duration": 0.0
        }
    
    def enable_profiling(self, mode: ProfilingMode = ProfilingMode.SAMPLING):
        """Enable performance profiling"""
        if self.profiler_enabled:
            return
        
        self.profiler_enabled = True
        self.profiler_mode = mode
        
        if mode == ProfilingMode.CONTINUOUS:
            self._start_continuous_profiling()
        elif mode == ProfilingMode.SAMPLING:
            self._start_sampling_profiling()
        
        # Enable memory tracing
        tracemalloc.start()
        self.memory_profiling_enabled = True
        
        self.logger.info(f"Performance profiling enabled (mode: {mode.value})")
    
    def disable_profiling(self):
        """Disable performance profiling"""
        if not self.profiler_enabled:
            return
        
        self.profiler_enabled = False
        
        # Stop background tasks
        for task in self.background_tasks:
            task.cancel()
        
        asyncio.gather(*self.background_tasks, return_exceptions=True)
        self.background_tasks.clear()
        
        # Stop memory tracing
        if self.memory_profiling_enabled:
            current, peak = tracemalloc.get_traced_memory()
            self.memory_snapshots.append({
                "timestamp": datetime.now(),
                "current": current,
                "peak": peak
            })
            tracemalloc.stop()
            self.memory_profiling_enabled = False
        
        self.logger.info("Performance profiling disabled")
    
    def _start_continuous_profiling(self):
        """Start continuous profiling"""
        self.cpu_profiler = cProfile.Profile()
        self.cpu_profiler.enable()
        
        # Start background monitoring
        task = asyncio.create_task(self._continuous_monitoring_loop())
        self.background_tasks.append(task)
    
    def _start_sampling_profiling(self):
        """Start sampling profiling"""
        task = asyncio.create_task(self._sampling_loop())
        self.background_tasks.append(task)
    
    async def _continuous_monitoring_loop(self):
        """Continuous monitoring loop"""
        while self.profiler_enabled:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(self.sampling_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in continuous monitoring: {e}")
                await asyncio.sleep(1)
    
    async def _sampling_loop(self):
        """Sampling profiling loop"""
        while self.profiler_enabled:
            try:
                # Sample CPU usage
                await self._sample_cpu_usage()
                
                # Sample memory usage
                await self._sample_memory_usage()
                
                # Sample IO operations
                await self._sample_io_usage()
                
                # Sample network usage
                await self._sample_network_usage()
                
                await asyncio.sleep(self.sampling_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in sampling loop: {e}")
                await asyncio.sleep(1)
    
    async def _collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent()
            cpu_count = psutil.cpu_count()
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            
            self._record_metric("system_cpu_usage", MetricType.CPU_USAGE, 
                              cpu_percent, "%", {"type": "overall"})
            self._record_metric("system_cpu_count", MetricType.CPU_USAGE,
                              cpu_count, "count", {"type": "cores"})
            self._record_metric("system_load_1min", MetricType.CPU_USAGE,
                              load_avg[0], "load", {"period": "1min"})
            self._record_metric("system_load_5min", MetricType.CPU_USAGE,
                              load_avg[1], "load", {"period": "5min"})
            self._record_metric("system_load_15min", MetricType.CPU_USAGE,
                              load_avg[2], "load", {"period": "15min"})
            
            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            self._record_metric("system_memory_usage", MetricType.MEMORY_USAGE,
                              memory.percent, "%", {"type": "virtual"})
            self._record_metric("system_memory_used", MetricType.MEMORY_USAGE,
                              memory.used, "bytes", {"type": "virtual"})
            self._record_metric("system_memory_available", MetricType.MEMORY_USAGE,
                              memory.available, "bytes", {"type": "virtual"})
            
            self._record_metric("system_swap_usage", MetricType.MEMORY_USAGE,
                              swap.percent, "%", {"type": "swap"})
            
            # Process metrics
            process = psutil.Process()
            
            self._record_metric("process_cpu_percent", MetricType.CPU_USAGE,
                              process.cpu_percent(), "%", {"pid": str(process.pid)})
            self._record_metric("process_memory_rss", MetricType.MEMORY_USAGE,
                              process.memory_info().rss, "bytes", {"type": "rss"})
            self._record_metric("process_memory_vms", MetricType.MEMORY_USAGE,
                              process.memory_info().vms, "bytes", {"type": "vms"})
            self._record_metric("process_num_threads", MetricType.CPU_USAGE,
                              process.num_threads(), "count", {"type": "threads"})
            
            # Disk metrics
            disk_io = psutil.disk_io_counters()
            if disk_io:
                self._record_metric("disk_read_bytes", MetricType.IO_OPERATIONS,
                                  disk_io.read_bytes, "bytes", {"direction": "read"})
                self._record_metric("disk_write_bytes", MetricType.IO_OPERATIONS,
                                  disk_io.write_bytes, "bytes", {"direction": "write"})
                self._record_metric("disk_read_count", MetricType.IO_OPERATIONS,
                                  disk_io.read_count, "count", {"direction": "read"})
                self._record_metric("disk_write_count", MetricType.IO_OPERATIONS,
                                  disk_io.write_count, "count", {"direction": "write"})
            
            # Network metrics
            network_io = psutil.net_io_counters()
            if network_io:
                self._record_metric("network_bytes_sent", MetricType.NETWORK_BANDWIDTH,
                                  network_io.bytes_sent, "bytes", {"direction": "sent"})
                self._record_metric("network_bytes_recv", MetricType.NETWORK_BANDWIDTH,
                                  network_io.bytes_recv, "bytes", {"direction": "received"})
                self._record_metric("network_packets_sent", MetricType.NETWORK_BANDWIDTH,
                                  network_io.packets_sent, "count", {"direction": "sent"})
                self._record_metric("network_packets_recv", MetricType.NETWORK_BANDWIDTH,
                                  network_io.packets_recv, "count", {"direction": "received"})
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
    
    async def _sample_cpu_usage(self):
        """Sample CPU usage for individual processes"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    pid = proc.info['pid']
                    name = proc.info['name']
                    cpu_percent = proc.info['cpu_percent']
                    
                    if cpu_percent is not None:
                        self._record_metric("process_cpu_by_name", MetricType.CPU_USAGE,
                                          cpu_percent, "%", {"name": name, "pid": str(pid)})
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            self.logger.error(f"Error sampling CPU usage: {e}")
    
    async def _sample_memory_usage(self):
        """Sample memory usage"""
        try:
            if self.memory_profiling_enabled:
                current, peak = tracemalloc.get_traced_memory()
                
                self._record_metric("memory_traced_current", MetricType.MEMORY_USAGE,
                                  current, "bytes", {"type": "traced"})
                self._record_metric("memory_traced_peak", MetricType.MEMORY_USAGE,
                                  peak, "bytes", {"type": "traced"})
                
                # Take snapshot periodically
                if len(self.memory_snapshots) == 0 or \
                   (datetime.now() - self.memory_snapshots[-1]["timestamp"]).seconds > 60:
                    self.memory_snapshots.append({
                        "timestamp": datetime.now(),
                        "current": current,
                        "peak": peak
                    })
                    self.stats["memory_snapshots"] += 1
        except Exception as e:
            self.logger.error(f"Error sampling memory usage: {e}")
    
    async def _sample_io_usage(self):
        """Sample I/O usage"""
        try:
            disk_usage = psutil.disk_usage('/')
            
            self._record_metric("disk_usage_percent", MetricType.IO_OPERATIONS,
                              disk_usage.percent, "%", {"path": "/"})
            self._record_metric("disk_free_space", MetricType.IO_OPERATIONS,
                              disk_usage.free, "bytes", {"path": "/"})
            self._record_metric("disk_used_space", MetricType.IO_OPERATIONS,
                              disk_usage.used, "bytes", {"path": "/"})
        except Exception as e:
            self.logger.error(f"Error sampling I/O usage: {e}")
    
    async def _sample_network_usage(self):
        """Sample network usage"""
        try:
            net_connections = psutil.net_connections()
            
            connection_counts = defaultdict(int)
            for conn in net_connections:
                if conn.status:
                    connection_counts[conn.status] += 1
            
            for status, count in connection_counts.items():
                self._record_metric("network_connections", MetricType.NETWORK_BANDWIDTH,
                                  count, "count", {"status": status})
        except Exception as e:
            self.logger.error(f"Error sampling network usage: {e}")
    
    def _record_metric(self, name: str, metric_type: MetricType, 
                      value: float, unit: str, tags: Dict[str, str] = None,
                      context: Dict[str, Any] = None):
        """Record a performance metric"""
        with self._lock:
            metric = PerformanceMetric(
                name=name,
                metric_type=metric_type,
                value=value,
                unit=unit,
                timestamp=datetime.now(),
                tags=tags or {},
                context=context or {}
            )
            
            self.metrics_buffer.append(metric)
            self.stats["metrics_recorded"] += 1
    
    def profile_function(self, name: str = None):
        """Decorator to profile function performance"""
        def decorator(func: Callable):
            def wrapper(*args, **kwargs):
                if not self.profiler_enabled:
                    return func(*args, **kwargs)
                
                func_name = name or f"{func.__module__}.{func.__name__}"
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    success = True
                    error = None
                except Exception as e:
                    result = None
                    success = False
                    error = str(e)
                    raise
                finally:
                    execution_time = time.time() - start_time
                    
                    # Record function profile
                    self.function_profiles[func_name].append(execution_time)
                    self.stats["functions_profiled"] += 1
                    
                    # Record performance metric
                    self._record_metric(
                        f"function_execution_time",
                        MetricType.EXECUTION_TIME,
                        execution_time,
                        "seconds",
                        {"function": func_name, "success": str(success)},
                        {"error": error}
                    )
                
                return result
            
            return wrapper
        return decorator
    
    def profile_async_function(self, name: str = None):
        """Decorator to profile async function performance"""
        def decorator(func: Callable):
            async def wrapper(*args, **kwargs):
                if not self.profiler_enabled:
                    return await func(*args, **kwargs)
                
                func_name = name or f"{func.__module__}.{func.__name__}"
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    success = True
                    error = None
                except Exception as e:
                    result = None
                    success = False
                    error = str(e)
                    raise
                finally:
                    execution_time = time.time() - start_time
                    
                    # Record function profile
                    self.function_profiles[func_name].append(execution_time)
                    self.stats["functions_profiled"] += 1
                    
                    # Record performance metric
                    self._record_metric(
                        f"async_function_execution_time",
                        MetricType.EXECUTION_TIME,
                        execution_time,
                        "seconds",
                        {"function": func_name, "success": str(success)},
                        {"error": error}
                    )
                
                return result
            
            return wrapper
        return decorator
    
    def get_cpu_profile(self) -> List[ProfiledFunction]:
        """Get CPU profiling results"""
        if not self.cpu_profiler:
            return []
        
        self.cpu_profiler.disable()
        
        # Get stats
        stats_stream = io.StringIO()
        stats = pstats.Stats(self.cpu_profiler, stream=stats_stream)
        stats.sort_stats('cumulative')
        stats.print_stats()
        
        # Parse stats
        functions = []
        lines = stats_stream.getvalue().split('\n')
        
        for line in lines[5:]:  # Skip header
            if line.strip() and not line.startswith(' '):
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        ncalls = int(parts[0].split('/')[0])
                        tottime = float(parts[1])
                        percall = float(parts[2])
                        cumtime = float(parts[3])
                        percall_cum = float(parts[4])
                        
                        # Function name and line info
                        func_info = ' '.join(parts[5:])
                        
                        functions.append(ProfiledFunction(
                            name=func_info,
                            module="unknown",
                            line_number=0,
                            call_count=ncalls,
                            total_time=cumtime,
                            average_time=percall_cum,
                            max_time=0.0,  # Not available in basic stats
                            min_time=0.0,  # Not available in basic stats
                            std_dev=0.0,   # Not available in basic stats
                            percentage_time=0.0  # Calculate later
                        ))
                    except (ValueError, IndexError):
                        continue
        
        self.cpu_profiler.enable()
        return functions
    
    def get_memory_profile(self) -> List[ProfiledMemoryAllocation]:
        """Get memory profiling results"""
        if not self.memory_profiling_enabled:
            return []
        
        try:
            # Get memory statistics
            snapshot = tracemalloc.take_snapshot()
            stats = snapshot.statistics('lineno')
            
            allocations = []
            total_time = sum(stat.size for stat in stats)
            
            for stat in stats[:100]:  # Top 100 allocations
                allocations.append(ProfiledMemoryAllocation(
                    filename=stat.traceback.format()[-1] if stat.traceback else "unknown",
                    line_number=stat.lineno,
                    size=stat.size,
                    count=stat.count,
                    total_size=stat.size * stat.count,
                    average_size=stat.size
                ))
            
            return allocations
            
        except Exception as e:
            self.logger.error(f"Error getting memory profile: {e}")
            return []
    
    def get_function_profiles(self) -> Dict[str, Dict[str, float]]:
        """Get function profiling statistics"""
        profiles = {}
        
        with self._lock:
            for func_name, times in self.function_profiles.items():
                if times:
                    profiles[func_name] = {
                        "call_count": len(times),
                        "total_time": sum(times),
                        "average_time": statistics.mean(times),
                        "min_time": min(times),
                        "max_time": max(times),
                        "std_dev": statistics.stdev(times) if len(times) > 1 else 0.0,
                        "p50": self._percentile(times, 50),
                        "p95": self._percentile(times, 95),
                        "p99": self._percentile(times, 99)
                    }
        
        return profiles
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def get_performance_metrics(self, metric_name: str = None,
                              start_time: datetime = None,
                              end_time: datetime = None) -> List[PerformanceMetric]:
        """Get performance metrics"""
        with self._lock:
            metrics = list(self.metrics_buffer)
            
            # Filter by name
            if metric_name:
                metrics = [m for m in metrics if m.name == metric_name]
            
            # Filter by time range
            if start_time:
                metrics = [m for m in metrics if m.timestamp >= start_time]
            
            if end_time:
                metrics = [m for m in metrics if m.timestamp <= end_time]
            
            return metrics
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance profiling summary"""
        with self._lock:
            # CPU summary
            cpu_metrics = [m for m in self.metrics_buffer 
                          if m.metric_type == MetricType.CPU_USAGE]
            
            # Memory summary
            memory_metrics = [m for m in self.metrics_buffer 
                            if m.metric_type == MetricType.MEMORY_USAGE]
            
            # Performance summary
            performance_metrics = [m for m in self.metrics_buffer 
                                 if m.metric_type == MetricType.EXECUTION_TIME]
            
            return {
                "profiling_enabled": self.profiler_enabled,
                "profiling_mode": self.profiler_mode.value if self.profiler_enabled else None,
                "stats": self.stats.copy(),
                "summary": {
                    "cpu_metrics_count": len(cpu_metrics),
                    "memory_metrics_count": len(memory_metrics),
                    "performance_metrics_count": len(performance_metrics),
                    "functions_profiled": len(self.function_profiles),
                    "memory_snapshots": len(self.memory_snapshots)
                },
                "current_metrics": {
                    "latest_cpu": cpu_metrics[-1].to_dict() if cpu_metrics else None,
                    "latest_memory": memory_metrics[-1].to_dict() if memory_metrics else None
                }
            }
    
    def export_metrics(self, format_type: str = "json") -> str:
        """Export performance metrics"""
        metrics_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": self.get_performance_summary(),
            "function_profiles": self.get_function_profiles(),
            "cpu_profile": [f.to_dict() for f in self.get_cpu_profile()],
            "memory_profile": [m.to_dict() for m in self.get_memory_profile()]
        }
        
        if format_type.lower() == "json":
            return json.dumps(metrics_data, indent=2)
        else:
            return str(metrics_data)

# Performance context manager
class ProfileContext:
    """Context manager for profiling code blocks"""
    
    def __init__(self, profiler: PerformanceProfiler, name: str, 
                 tags: Dict[str, str] = None):
        self.profiler = profiler
        self.name = name
        self.tags = tags or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.profiler.profiler_enabled and self.start_time:
            execution_time = time.time() - self.start_time
            
            self.profiler._record_metric(
                f"context_execution_time",
                MetricType.EXECUTION_TIME,
                execution_time,
                "seconds",
                {"context": self.name, **self.tags},
                {"exception": str(exc_val) if exc_val else None}
            )

# Global profiler instance
_performance_profiler = None

def get_performance_profiler() -> PerformanceProfiler:
    """Get global performance profiler instance"""
    global _performance_profiler
    if _performance_profiler is None:
        _performance_profiler = PerformanceProfiler()
    return _performance_profiler

def init_performance_profiling(sampling_interval: float = 1.0,
                             mode: ProfilingMode = ProfilingMode.SAMPLING) -> PerformanceProfiler:
    """Initialize performance profiling"""
    profiler = PerformanceProfiler(sampling_interval)
    profiler.enable_profiling(mode)
    return profiler

# Decorators for easy profiling
def profile_function(name: str = None):
    """Profile function performance"""
    profiler = get_performance_profiler()
    return profiler.profile_function(name)

def profile_async_function(name: str = None):
    """Profile async function performance"""
    profiler = get_performance_profiler()
    return profiler.profile_async_function(name)

def profile_context(name: str, tags: Dict[str, str] = None):
    """Profile code block context"""
    profiler = get_performance_profiler()
    return ProfileContext(profiler, name, tags)