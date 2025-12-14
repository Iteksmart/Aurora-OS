"""
Aurora OS - MCP System Context Provider

This module provides system-level context through the Model Context Protocol,
enabling the AI control plane to monitor and optimize system resources.

Key Features:
- Real-time CPU and memory monitoring
- Process tracking and analysis
- Network performance monitoring
- System health assessment
- Predictive resource management
- Performance optimization suggestions
"""

import os
import asyncio
import json
import time
import psutil
import platform
import subprocess
import logging
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from ..system.mcp_host import MCPProvider, MCPContext


@dataclass
class CPUInfo:
    """CPU information and current usage"""
    architecture: str
    brand: str
    cores: int
    logical_cores: int
    max_frequency: float
    current_frequency: float
    usage_percent: float
    load_average: List[float]
    per_core_usage: List[float]
    temperature: Optional[float] = None


@dataclass
class MemoryInfo:
    """Memory information and current usage"""
    total: int
    available: int
    used: int
    percent: float
    swap_total: int
    swap_used: int
    swap_percent: float
    cached: int
    buffers: int


@dataclass
class ProcessInfo:
    """Process information"""
    pid: int
    name: str
    status: str
    cpu_percent: float
    memory_percent: float
    memory_rss: int
    memory_vms: int
    create_time: float
    num_threads: int
    cmdline: List[str]
    username: str
    nice: int
    priority: int
    io_counters: Optional[Dict[str, int]] = None
    connections: Optional[int] = None


@dataclass
class NetworkInfo:
    """Network interface information"""
    interface: str
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    errors_in: int
    errors_out: int
    drop_in: int
    drop_out: int
    speed: Optional[int] = None
    is_up: bool = True


@dataclass
class SystemHealth:
    """Overall system health assessment"""
    health_score: float  # 0-100
    cpu_health: float
    memory_health: float
    disk_health: float
    network_health: float
    temperature_health: float
    overall_load: float
    bottlenecks: List[str]
    warnings: List[str]
    recommendations: List[str]


@dataclass
class SystemMetrics:
    """System performance metrics over time"""
    timestamp: float
    cpu_usage: float
    memory_usage: float
    disk_io_read: int
    disk_io_write: int
    network_io_sent: int
    network_io_recv: int
    process_count: int
    load_average: float


class SystemContextProvider(MCPProvider):
    """MCP Provider for system context"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("system", "Aurora OS System Provider", "1.0.0")
        self.logger = logging.getLogger(f"mcp_system_provider")
        
        self.update_interval = config.get("update_interval", 5)  # seconds
        self.history_size = config.get("history_size", 1000)
        self.track_processes = config.get("track_processes", True)
        self.track_network = config.get("track_network", True)
        self.enable_predictions = config.get("enable_predictions", True)
        
        # Internal state
        self.cpu_info: Optional[CPUInfo] = None
        self.memory_info: Optional[MemoryInfo] = None
        self.network_interfaces: Dict[str, NetworkInfo] = {}
        self.processes: Dict[int, ProcessInfo] = {}
        self.system_health: Optional[SystemHealth] = None
        self.metrics_history: List[SystemMetrics] = []
        
        # Baseline for anomaly detection
        self.baseline_cpu = 0
        self.baseline_memory = 0
        self.baseline_processes = 0
        
        # Performance counters
        self.last_disk_io = None
        self.last_network_io = None
        self.last_update_time = 0
        
        # System information cache
        self.system_info = {}
        
    async def initialize(self) -> bool:
        """Initialize the system provider"""
        try:
            # Get system information
            await self._collect_system_info()
            
            # Establish baselines
            await self._establish_baselines()
            
            # Start periodic monitoring
            asyncio.create_task(self._periodic_update())
            
            self.logger.info("System provider initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize system provider: {e}")
            return False
    
    async def get_context_data(self, request: Dict[str, Any]) -> MCPContext:
        """Get system context data"""
        start_time = time.time()
        
        try:
            context_type = request.get("type", "overview")
            detailed = request.get("detailed", False)
            time_range = request.get("time_range", 300)  # 5 minutes default
            
            if context_type == "overview":
                data = await self._get_overview_context(detailed)
            elif context_type == "cpu":
                data = await self._get_cpu_context(detailed)
            elif context_type == "memory":
                data = await self._get_memory_context(detailed)
            elif context_type == "processes":
                data = await self._get_processes_context(request.get("filter", {}))
            elif context_type == "network":
                data = await self._get_network_context(detailed)
            elif context_type == "health":
                data = await self._get_health_context()
            elif context_type == "performance":
                data = await self._get_performance_context(time_range)
            elif context_type == "predictions":
                data = await self._get_predictions_context()
            elif context_type == "optimization":
                data = await self._get_optimization_context()
            else:
                data = {"error": f"Unknown context type: {context_type}"}
            
            processing_time = time.time() - start_time
            
            return MCPContext(context_id=f"ctx_{int(time.time()*1000)}_{os.urandom(4).hex()}", 
                provider_id=self.provider_id,
                context_type=context_type,
                data=data,
                timestamp=time.time(),
                metadata={
                    "processing_time": processing_time,
                    "update_interval": self.update_interval,
                    "history_size": len(self.metrics_history),
                    "tracked_processes": len(self.processes)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error getting system context: {e}")
            return MCPContext(context_id=f"ctx_{int(time.time()*1000)}_{os.urandom(4).hex()}", 
                provider_id=self.provider_id,
                context_type="error",
                data={"error": str(e)},
                timestamp=time.time(),
                metadata={"error": True}
            )
    
    async def _collect_system_info(self) -> None:
        """Collect static system information"""
        try:
            self.system_info = {
                "hostname": platform.node(),
                "platform": platform.platform(),
                "architecture": platform.architecture(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "boot_time": psutil.boot_time(),
                "uptime": time.time() - psutil.boot_time()
            }
            
            # CPU information
            cpu_freq = psutil.cpu_freq()
            self.cpu_info = CPUInfo(
                architecture=platform.architecture()[0],
                brand=platform.processor(),
                cores=psutil.cpu_count(logical=False),
                logical_cores=psutil.cpu_count(logical=True),
                max_frequency=cpu_freq.max if cpu_freq else 0,
                current_frequency=cpu_freq.current if cpu_freq else 0,
                usage_percent=psutil.cpu_percent(interval=1),
                load_average=list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else [],
                per_core_usage=psutil.cpu_percent(percpu=True, interval=1)
            )
            
            # Try to get temperature if available
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    # Get average temperature from available sensors
                    all_temps = []
                    for name, entries in temps.items():
                        for entry in entries:
                            if entry.current:
                                all_temps.append(entry.current)
                    if all_temps:
                        self.cpu_info.temperature = sum(all_temps) / len(all_temps)
            except AttributeError:
                pass  # Temperature sensors not available
            
        except Exception as e:
            self.logger.error(f"Error collecting system info: {e}")
    
    async def _establish_baselines(self) -> None:
        """Establish baseline metrics for anomaly detection"""
        try:
            # Collect samples over a short period
            samples = []
            for _ in range(10):
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                process_count = len(psutil.pids())
                
                samples.append({
                    "cpu": cpu_percent,
                    "memory": memory.percent,
                    "processes": process_count
                })
                await asyncio.sleep(0.5)
            
            # Calculate baselines as averages
            if samples:
                self.baseline_cpu = sum(s["cpu"] for s in samples) / len(samples)
                self.baseline_memory = sum(s["memory"] for s in samples) / len(samples)
                self.baseline_processes = sum(s["processes"] for s in samples) / len(samples)
            
            self.logger.info(f"Baselines established - CPU: {self.baseline_cpu:.1f}%, "
                           f"Memory: {self.baseline_memory:.1f}%, "
                           f"Processes: {self.baseline_processes:.0f}")
            
        except Exception as e:
            self.logger.error(f"Error establishing baselines: {e}")
    
    async def _update_current_state(self) -> None:
        """Update current system state"""
        try:
            current_time = time.time()
            
            # Update CPU info
            if self.cpu_info:
                self.cpu_info.usage_percent = psutil.cpu_percent(interval=0.1)
                self.cpu_info.load_average = list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else []
                self.cpu_info.per_core_usage = psutil.cpu_percent(percpu=True)
                
                cpu_freq = psutil.cpu_freq()
                if cpu_freq:
                    self.cpu_info.current_frequency = cpu_freq.current
                
                # Update temperature
                try:
                    temps = psutil.sensors_temperatures()
                    if temps:
                        all_temps = []
                        for name, entries in temps.items():
                            for entry in entries:
                                if entry.current:
                                    all_temps.append(entry.current)
                        if all_temps:
                            self.cpu_info.temperature = sum(all_temps) / len(all_temps)
                except AttributeError:
                    pass
            
            # Update memory info
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            self.memory_info = MemoryInfo(
                total=memory.total,
                available=memory.available,
                used=memory.used,
                percent=memory.percent,
                swap_total=swap.total,
                swap_used=swap.used,
                swap_percent=swap.percent,
                cached=getattr(memory, 'cached', 0),
                buffers=getattr(memory, 'buffers', 0)
            )
            
            # Update network interfaces
            if self.track_network:
                net_io = psutil.net_io_counters(pernic=True)
                net_if_addrs = psutil.net_if_addrs()
                net_if_stats = psutil.net_if_stats()
                
                self.network_interfaces.clear()
                for interface, stats in net_io.items():
                    interface_stats = net_if_stats.get(interface)
                    self.network_interfaces[interface] = NetworkInfo(
                        interface=interface,
                        bytes_sent=stats.bytes_sent,
                        bytes_recv=stats.bytes_recv,
                        packets_sent=stats.packets_sent,
                        packets_recv=stats.packets_recv,
                        errors_in=stats.errin,
                        errors_out=stats.errout,
                        drop_in=stats.dropin,
                        drop_out=stats.dropout,
                        speed=getattr(interface_stats, 'speed', None),
                        is_up=getattr(interface_stats, 'isup', True) if interface_stats else True
                    )
            
            # Update processes
            if self.track_processes:
                self.processes.clear()
                for pid in psutil.pids():
                    try:
                        proc = psutil.Process(pid)
                        
                        # Get process info
                        with proc.oneshot():
                            cpu_percent = proc.cpu_percent()
                            memory_info = proc.memory_info()
                            memory_percent = proc.memory_percent()
                            create_time = proc.create_time()
                            
                            # Get IO counters if available
                            io_counters = None
                            try:
                                io_counters_data = proc.io_counters()
                                io_counters = {
                                    "read_count": io_counters_data.read_count,
                                    "write_count": io_counters_data.write_count,
                                    "read_bytes": io_counters_data.read_bytes,
                                    "write_bytes": io_counters_data.write_bytes
                                }
                            except (psutil.AccessDenied, AttributeError):
                                pass
                            
                            # Get network connections
                            connections = None
                            try:
                                connections = len(proc.connections())
                            except (psutil.AccessDenied, AttributeError):
                                pass
                            
                            process_info = ProcessInfo(
                                pid=pid,
                                name=proc.name(),
                                status=proc.status(),
                                cpu_percent=cpu_percent,
                                memory_percent=memory_percent,
                                memory_rss=memory_info.rss,
                                memory_vms=memory_info.vms,
                                create_time=create_time,
                                num_threads=proc.num_threads(),
                                cmdline=proc.cmdline(),
                                username=proc.username(),
                                nice=proc.nice(),
                                priority=proc.nice() + 20,  # Convert to priority
                                io_counters=io_counters,
                                connections=connections
                            )
                            
                            self.processes[pid] = process_info
                            
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            
            # Update system health
            await self._calculate_system_health()
            
            # Record metrics for history
            await self._record_metrics(current_time)
            
            self.last_update_time = current_time
            
        except Exception as e:
            self.logger.error(f"Error updating system state: {e}")
    
    async def _calculate_system_health(self) -> None:
        """Calculate overall system health"""
        try:
            health_scores = []
            bottlenecks = []
            warnings = []
            recommendations = []
            
            # CPU health
            cpu_health = 100 - min(self.cpu_info.usage_percent, 100)
            if self.cpu_info.temperature and self.cpu_info.temperature > 80:
                cpu_health -= 20
                warnings.append(f"High CPU temperature: {self.cpu_info.temperature:.1f}°C")
                recommendations.append("Check CPU cooling")
            health_scores.append(cpu_health)
            
            # Memory health
            memory_health = 100 - min(self.memory_info.percent, 100)
            if self.memory_info.swap_percent > 50:
                memory_health -= 20
                bottlenecks.append("High swap usage")
                recommendations.append("Add more RAM or reduce memory usage")
            health_scores.append(memory_health)
            
            # Disk health (simplified check)
            disk_health = 100
            try:
                disk_usage = psutil.disk_usage('/')
                disk_percent = (disk_usage.used / disk_usage.total) * 100
                if disk_percent > 90:
                    disk_health -= 30
                    bottlenecks.append("Low disk space")
                    recommendations.append("Clean up disk space")
                elif disk_percent > 80:
                    disk_health -= 10
                    warnings.append(f"Disk usage: {disk_percent:.1f}%")
            except Exception:
                pass
            health_scores.append(disk_health)
            
            # Network health
            network_health = 100
            network_errors = sum(
                iface.errors_in + iface.errors_out + iface.drop_in + iface.drop_out
                for iface in self.network_interfaces.values()
            )
            if network_errors > 100:
                network_health -= 20
                warnings.append("Network errors detected")
            health_scores.append(network_health)
            
            # Temperature health
            temp_health = 100
            if self.cpu_info and self.cpu_info.temperature:
                if self.cpu_info.temperature > 85:
                    temp_health = 30
                    bottlenecks.append("Critical temperature")
                elif self.cpu_info.temperature > 75:
                    temp_health = 60
                    warnings.append(f"High temperature: {self.cpu_info.temperature:.1f}°C")
            health_scores.append(temp_health)
            
            # Overall load
            overall_load = sum(health_scores) / len(health_scores)
            
            # Calculate overall health score
            health_score = overall_load
            
            # Additional checks for system stability
            if self.cpu_info and len(self.cpu_info.load_average) >= 3:
                load_avg = self.cpu_info.load_average[0]
                if load_avg > self.cpu_info.logical_cores * 2:
                    health_score -= 20
                    bottlenecks.append("High system load")
                elif load_avg > self.cpu_info.logical_cores:
                    health_score -= 10
                    warnings.append("Moderate system load")
            
            self.system_health = SystemHealth(
                health_score=max(0, min(100, health_score)),
                cpu_health=cpu_health,
                memory_health=memory_health,
                disk_health=disk_health,
                network_health=network_health,
                temperature_health=temp_health,
                overall_load=overall_load,
                bottlenecks=bottlenecks,
                warnings=warnings,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating system health: {e}")
    
    async def _record_metrics(self, timestamp: float) -> None:
        """Record current metrics for historical analysis"""
        try:
            # Get disk and network I/O
            disk_io = psutil.disk_io_counters()
            network_io = psutil.net_io_counters()
            
            metrics = SystemMetrics(
                timestamp=timestamp,
                cpu_usage=self.cpu_info.usage_percent if self.cpu_info else 0,
                memory_usage=self.memory_info.percent if self.memory_info else 0,
                disk_io_read=disk_io.read_bytes if disk_io else 0,
                disk_io_write=disk_io.write_bytes if disk_io else 0,
                network_io_sent=network_io.bytes_sent if network_io else 0,
                network_io_recv=network_io.bytes_recv if network_io else 0,
                process_count=len(self.processes),
                load_average=self.cpu_info.load_average[0] if self.cpu_info and self.cpu_info.load_average else 0
            )
            
            self.metrics_history.append(metrics)
            
            # Limit history size
            if len(self.metrics_history) > self.history_size:
                self.metrics_history = self.metrics_history[-self.history_size:]
            
        except Exception as e:
            self.logger.error(f"Error recording metrics: {e}")
    
    async def _get_overview_context(self, detailed: bool = False) -> Dict[str, Any]:
        """Get system overview context"""
        await self._update_current_state()
        
        overview = {
            "system_info": self.system_info,
            "health": asdict(self.system_health) if self.system_health else {},
            "current_time": time.time()
        }
        
        if detailed:
            overview.update({
                "cpu": asdict(self.cpu_info) if self.cpu_info else {},
                "memory": asdict(self.memory_info) if self.memory_info else {},
                "processes": {
                    "total": len(self.processes),
                    "running": len([p for p in self.processes.values() if p.status == "running"]),
                    "sleeping": len([p for p in self.processes.values() if p.status == "sleeping"])
                },
                "network_interfaces": {
                    name: asdict(info) for name, info in self.network_interfaces.items()
                }
            })
        else:
            overview.update({
                "cpu_usage": self.cpu_info.usage_percent if self.cpu_info else 0,
                "memory_usage": self.memory_info.percent if self.memory_info else 0,
                "process_count": len(self.processes),
                "health_score": self.system_health.health_score if self.system_health else 0
            })
        
        return overview
    
    async def _get_cpu_context(self, detailed: bool = False) -> Dict[str, Any]:
        """Get CPU-specific context"""
        await self._update_current_state()
        
        if not self.cpu_info:
            return {"error": "CPU information not available"}
        
        context = asdict(self.cpu_info)
        
        if detailed:
            # Add historical CPU usage
            recent_metrics = self.metrics_history[-60:]  # Last hour if 1-minute intervals
            if recent_metrics:
                context["history"] = [
                    {
                        "timestamp": m.timestamp,
                        "usage": m.cpu_usage,
                        "load": m.load_average
                    }
                    for m in recent_metrics
                ]
                
                # Calculate trends
                cpu_trend = self._calculate_trend([m.cpu_usage for m in recent_metrics])
                context["trend"] = {
                    "direction": cpu_trend["direction"],
                    "rate": cpu_trend["rate"],
                    "prediction": self._predict_next_value([m.cpu_usage for m in recent_metrics])
                }
            
            # Add CPU-intensive processes
            cpu_intensive = sorted(
                [(pid, proc) for pid, proc in self.processes.items()],
                key=lambda x: x[1].cpu_percent,
                reverse=True
            )[:10]
            
            context["top_processes"] = [
                {
                    "pid": pid,
                    "name": proc.name,
                    "cpu_percent": proc.cpu_percent,
                    "memory_percent": proc.memory_percent
                }
                for pid, proc in cpu_intensive
            ]
        
        return context
    
    async def _get_memory_context(self, detailed: bool = False) -> Dict[str, Any]:
        """Get memory-specific context"""
        await self._update_current_state()
        
        if not self.memory_info:
            return {"error": "Memory information not available"}
        
        context = asdict(self.memory_info)
        
        if detailed:
            # Add historical memory usage
            recent_metrics = self.metrics_history[-60:]
            if recent_metrics:
                context["history"] = [
                    {
                        "timestamp": m.timestamp,
                        "usage": m.memory_usage
                    }
                    for m in recent_metrics
                ]
                
                memory_trend = self._calculate_trend([m.memory_usage for m in recent_metrics])
                context["trend"] = {
                    "direction": memory_trend["direction"],
                    "rate": memory_trend["rate"],
                    "prediction": self._predict_next_value([m.memory_usage for m in recent_metrics])
                }
            
            # Add memory-intensive processes
            memory_intensive = sorted(
                [(pid, proc) for pid, proc in self.processes.items()],
                key=lambda x: x[1].memory_percent,
                reverse=True
            )[:10]
            
            context["top_processes"] = [
                {
                    "pid": pid,
                    "name": proc.name,
                    "memory_percent": proc.memory_percent,
                    "memory_rss": proc.memory_rss,
                    "memory_vms": proc.memory_vms
                }
                for pid, proc in memory_intensive
            ]
        
        return context
    
    async def _get_processes_context(self, filter_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Get processes context with optional filtering"""
        await self._update_current_state()
        
        # Apply filters
        filtered_processes = []
        for pid, proc in self.processes.items():
            include = True
            
            if "name_contains" in filter_dict:
                if filter_dict["name_contains"].lower() not in proc.name.lower():
                    include = False
            
            if "min_cpu" in filter_dict:
                if proc.cpu_percent < filter_dict["min_cpu"]:
                    include = False
            
            if "min_memory" in filter_dict:
                if proc.memory_percent < filter_dict["min_memory"]:
                    include = False
            
            if "status" in filter_dict:
                if proc.status != filter_dict["status"]:
                    include = False
            
            if include:
                filtered_processes.append((pid, proc))
        
        # Sort by CPU usage by default
        sort_by = filter_dict.get("sort_by", "cpu_percent")
        reverse = filter_dict.get("reverse", True)
        
        if sort_by == "cpu_percent":
            filtered_processes.sort(key=lambda x: x[1].cpu_percent, reverse=reverse)
        elif sort_by == "memory_percent":
            filtered_processes.sort(key=lambda x: x[1].memory_percent, reverse=reverse)
        elif sort_by == "name":
            filtered_processes.sort(key=lambda x: x[1].name.lower(), reverse=reverse)
        elif sort_by == "pid":
            filtered_processes.sort(key=lambda x: x[0], reverse=reverse)
        
        # Limit results
        limit = filter_dict.get("limit", 100)
        filtered_processes = filtered_processes[:limit]
        
        return {
            "processes": [
                {
                    "pid": pid,
                    "name": proc.name,
                    "status": proc.status,
                    "cpu_percent": proc.cpu_percent,
                    "memory_percent": proc.memory_percent,
                    "memory_rss": proc.memory_rss,
                    "memory_vms": proc.memory_vms,
                    "create_time": proc.create_time,
                    "num_threads": proc.num_threads,
                    "username": proc.username,
                    "cmdline": proc.cmdline[:3] if proc.cmdline else [],  # First few args
                    "nice": proc.nice,
                    "priority": proc.priority
                }
                for pid, proc in filtered_processes
            ],
            "total_filtered": len(filtered_processes),
            "total_processes": len(self.processes),
            "filter_applied": filter_dict
        }
    
    async def _get_network_context(self, detailed: bool = False) -> Dict[str, Any]:
        """Get network-specific context"""
        await self._update_current_state()
        
        context = {
            "interfaces": {
                name: asdict(info) for name, info in self.network_interfaces.items()
            },
            "total_interfaces": len(self.network_interfaces)
        }
        
        if detailed:
            # Add network history
            recent_metrics = self.metrics_history[-60:]
            if recent_metrics:
                context["history"] = [
                    {
                        "timestamp": m.timestamp,
                        "bytes_sent": m.network_io_sent,
                        "bytes_recv": m.network_io_recv
                    }
                    for m in recent_metrics
                ]
                
                # Calculate bandwidth usage
                if len(recent_metrics) >= 2:
                    last = recent_metrics[-1]
                    prev = recent_metrics[-2]
                    time_delta = last.timestamp - prev.timestamp
                    
                    if time_delta > 0:
                        sent_rate = (last.network_io_sent - prev.network_io_sent) / time_delta
                        recv_rate = (last.network_io_recv - prev.network_io_recv) / time_delta
                        
                        context["bandwidth"] = {
                            "upload_bps": sent_rate,
                            "download_bps": recv_rate,
                            "upload_mbps": sent_rate / (1024 * 1024),
                            "download_mbps": recv_rate / (1024 * 1024)
                        }
            
            # Add network-intensive processes (those with connections)
            network_processes = [
                (pid, proc) for pid, proc in self.processes.items()
                if proc.connections and proc.connections > 0
            ]
            
            network_processes.sort(key=lambda x: x[1].connections, reverse=True)
            
            context["top_processes"] = [
                {
                    "pid": pid,
                    "name": proc.name,
                    "connections": proc.connections,
                    "cpu_percent": proc.cpu_percent,
                    "memory_percent": proc.memory_percent
                }
                for pid, proc in network_processes[:10]
            ]
        
        return context
    
    async def _get_health_context(self) -> Dict[str, Any]:
        """Get system health context"""
        await self._update_current_state()
        
        if not self.system_health:
            return {"error": "Health information not available"}
        
        return asdict(self.system_health)
    
    async def _get_performance_context(self, time_range: int) -> Dict[str, Any]:
        """Get performance context for a time range"""
        current_time = time.time()
        cutoff_time = current_time - time_range
        
        # Filter metrics by time range
        relevant_metrics = [
            m for m in self.metrics_history
            if m.timestamp >= cutoff_time
        ]
        
        if not relevant_metrics:
            return {"error": "No performance data available for the specified time range"}
        
        context = {
            "time_range": time_range,
            "metrics_count": len(relevant_metrics),
            "time_span": {
                "start": min(m.timestamp for m in relevant_metrics),
                "end": max(m.timestamp for m in relevant_metrics)
            }
        }
        
        # Calculate statistics for each metric
        cpu_values = [m.cpu_usage for m in relevant_metrics]
        memory_values = [m.memory_usage for m in relevant_metrics]
        load_values = [m.load_average for m in relevant_metrics]
        
        context["statistics"] = {
            "cpu": {
                "min": min(cpu_values),
                "max": max(cpu_values),
                "avg": sum(cpu_values) / len(cpu_values),
                "current": cpu_values[-1] if cpu_values else 0,
                "trend": self._calculate_trend(cpu_values)
            },
            "memory": {
                "min": min(memory_values),
                "max": max(memory_values),
                "avg": sum(memory_values) / len(memory_values),
                "current": memory_values[-1] if memory_values else 0,
                "trend": self._calculate_trend(memory_values)
            },
            "load": {
                "min": min(load_values),
                "max": max(load_values),
                "avg": sum(load_values) / len(load_values),
                "current": load_values[-1] if load_values else 0,
                "trend": self._calculate_trend(load_values)
            }
        }
        
        # Detect anomalies
        context["anomalies"] = await self._detect_performance_anomalies(relevant_metrics)
        
        return context
    
    async def _get_predictions_context(self) -> Dict[str, Any]:
        """Get predictive insights"""
        if not self.enable_predictions or len(self.metrics_history) < 10:
            return {"error": "Insufficient data for predictions"}
        
        # Get recent metrics for prediction
        recent_cpu = [m.cpu_usage for m in self.metrics_history[-20:]]
        recent_memory = [m.memory_usage for m in self.metrics_history[-20:]]
        recent_processes = [m.process_count for m in self.metrics_history[-20:]]
        
        predictions = {
            "cpu": {
                "next_value": self._predict_next_value(recent_cpu),
                "trend": self._calculate_trend(recent_cpu),
                "confidence": self._calculate_prediction_confidence(recent_cpu)
            },
            "memory": {
                "next_value": self._predict_next_value(recent_memory),
                "trend": self._calculate_trend(recent_memory),
                "confidence": self._calculate_prediction_confidence(recent_memory)
            },
            "processes": {
                "next_value": self._predict_next_value(recent_processes),
                "trend": self._calculate_trend(recent_processes),
                "confidence": self._calculate_prediction_confidence(recent_processes)
            },
            "recommendations": await self._generate_prediction_recommendations(recent_cpu, recent_memory)
        }
        
        return predictions
    
    async def _get_optimization_context(self) -> Dict[str, Any]:
        """Get optimization suggestions"""
        await self._update_current_state()
        
        suggestions = []
        
        # CPU optimization
        if self.cpu_info and self.cpu_info.usage_percent > 80:
            cpu_intensive = sorted(
                [(pid, proc) for pid, proc in self.processes.items()],
                key=lambda x: x[1].cpu_percent,
                reverse=True
            )[:5]
            
            suggestions.append({
                "type": "cpu",
                "priority": "high",
                "description": "High CPU usage detected",
                "suggestion": "Consider closing or reducing priority of CPU-intensive processes",
                "processes": [
                    {"pid": pid, "name": proc.name, "cpu_percent": proc.cpu_percent}
                    for pid, proc in cpu_intensive
                ]
            })
        
        # Memory optimization
        if self.memory_info and self.memory_info.percent > 85:
            memory_intensive = sorted(
                [(pid, proc) for pid, proc in self.processes.items()],
                key=lambda x: x[1].memory_percent,
                reverse=True
            )[:5]
            
            suggestions.append({
                "type": "memory",
                "priority": "high",
                "description": "High memory usage detected",
                "suggestion": "Consider closing memory-intensive applications or adding more RAM",
                "processes": [
                    {"pid": pid, "name": proc.name, "memory_percent": proc.memory_percent}
                    for pid, proc in memory_intensive
                ]
            })
        
        # Process optimization
        zombie_processes = [
            (pid, proc) for pid, proc in self.processes.items()
            if proc.status == "zombie"
        ]
        
        if zombie_processes:
            suggestions.append({
                "type": "processes",
                "priority": "medium",
                "description": f"Found {len(zombie_processes)} zombie processes",
                "suggestion": "Consider terminating zombie processes or rebooting the system",
                "processes": [{"pid": pid, "name": proc.name} for pid, proc in zombie_processes]
            })
        
        # Swap optimization
        if self.memory_info and self.memory_info.swap_percent > 50:
            suggestions.append({
                "type": "swap",
                "priority": "medium",
                "description": f"High swap usage: {self.memory_info.swap_percent:.1f}%",
                "suggestion": "Add more RAM or reduce memory pressure"
            })
        
        return {
            "suggestions": suggestions,
            "total_suggestions": len(suggestions),
            "health_score": self.system_health.health_score if self.system_health else 0
        }
    
    def _calculate_trend(self, values: List[float]) -> Dict[str, Any]:
        """Calculate trend for a series of values"""
        if len(values) < 2:
            return {"direction": "stable", "rate": 0}
        
        # Simple linear regression
        n = len(values)
        x = list(range(n))
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        # Calculate slope
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        
        # Determine direction
        if abs(slope) < 0.1:
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"
        
        return {
            "direction": direction,
            "rate": slope,
            "strength": abs(slope)
        }
    
    def _predict_next_value(self, values: List[float]) -> float:
        """Simple prediction of next value using linear regression"""
        if len(values) < 3:
            return values[-1] if values else 0
        
        trend = self._calculate_trend(values)
        return max(0, values[-1] + trend["rate"])
    
    def _calculate_prediction_confidence(self, values: List[float]) -> float:
        """Calculate confidence in prediction based on data consistency"""
        if len(values) < 5:
            return 0.5
        
        # Calculate variance as a measure of consistency
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        
        # Lower variance = higher confidence
        if variance < 10:
            return 0.9
        elif variance < 50:
            return 0.7
        elif variance < 100:
            return 0.5
        else:
            return 0.3
    
    async def _detect_performance_anomalies(self, metrics: List[SystemMetrics]) -> List[Dict[str, Any]]:
        """Detect performance anomalies in metrics"""
        anomalies = []
        
        if len(metrics) < 10:
            return anomalies
        
        # Calculate baseline from first half
        mid_point = len(metrics) // 2
        baseline_cpu = sum(m.cpu_usage for m in metrics[:mid_point]) / mid_point
        baseline_memory = sum(m.memory_usage for m in metrics[:mid_point]) / mid_point
        
        # Check for anomalies in second half
        for metric in metrics[mid_point:]:
            # CPU anomaly
            if metric.cpu_usage > baseline_cpu * 2:
                anomalies.append({
                    "type": "cpu_spike",
                    "timestamp": metric.timestamp,
                    "value": metric.cpu_usage,
                    "baseline": baseline_cpu,
                    "severity": "high" if metric.cpu_usage > baseline_cpu * 3 else "medium"
                })
            
            # Memory anomaly
            if metric.memory_usage > baseline_memory * 1.5:
                anomalies.append({
                    "type": "memory_spike",
                    "timestamp": metric.timestamp,
                    "value": metric.memory_usage,
                    "baseline": baseline_memory,
                    "severity": "high" if metric.memory_usage > baseline_memory * 2 else "medium"
                })
        
        return anomalies
    
    async def _generate_prediction_recommendations(self, cpu_values: List[float], memory_values: List[float]) -> List[str]:
        """Generate recommendations based on predictions"""
        recommendations = []
        
        # CPU prediction recommendations
        cpu_trend = self._calculate_trend(cpu_values)
        if cpu_trend["direction"] == "increasing" and cpu_trend["strength"] > 1:
            recommendations.append("CPU usage trending upward - consider optimizing CPU-intensive tasks")
        
        # Memory prediction recommendations
        memory_trend = self._calculate_trend(memory_values)
        if memory_trend["direction"] == "increasing" and memory_trend["strength"] > 0.5:
            recommendations.append("Memory usage trending upward - monitor for potential memory leaks")
        
        return recommendations
    
    async def _periodic_update(self) -> None:
        """Periodic system monitoring"""
        while True:
            try:
                await self._update_current_state()
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                self.logger.error(f"Error in periodic update: {e}")
                await asyncio.sleep(self.update_interval)
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        self.metrics_history.clear()
        self.processes.clear()
        self.network_interfaces.clear()
        self.logger.info("System provider cleaned up")
    
    def get_capabilities(self) -> List[str]:
        """Get provider capabilities"""
        return [
            "cpu_monitoring",
            "memory_monitoring",
            "process_tracking",
            "network_monitoring",
            "health_assessment",
            "performance_analysis",
            "predictive_insights",
            "optimization_suggestions"
        ]
    async def start(self) -> bool:
        """Start the system provider"""
        try:
            if not self.is_started:
                # Start background monitoring tasks
                asyncio.create_task(self._periodic_system_scan())
                asyncio.create_task(self._track_performance_metrics())
                
                self.is_started = True
                self.logger.info("System provider started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start system provider: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the system provider"""
        try:
            if self.is_started:
                self.is_started = False
                self.logger.info("System provider stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop system provider: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Perform health check"""
        try:
            if not self.is_started:
                return False
            
            # Check if metrics are being updated
            if self.last_update_time > 0:
                time_since_update = time.time() - self.last_update_time
                if time_since_update > self.update_interval * 3:
                    return False
            
            return True
            
        except Exception:
            return False
    
    async def get_context(self, request: Dict[str, Any]) -> MCPContext:
        """Get system context"""
        return await self.get_context_data(request)
