"""
Aurora OS - eBPF/bpftrace Integration for Programmable Kernel Observability
Provides live kernel behavior inspection, AI-powered anomaly detection, and human-readable explanations
"""

import os
import sys
import json
import asyncio
import subprocess
import tempfile
import time
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import logging
from datetime import datetime, timedelta
import re
from collections import defaultdict, deque

try:
    import bcc
    from bcc import BPF
    BCC_AVAILABLE = True
except ImportError:
    BCC_AVAILABLE = False

from ...ai_assistant.core.local_llm_engine import get_llm_engine

@dataclass
class KernelEvent:
    """Kernel event captured by eBPF"""
    timestamp: datetime
    event_type: str
    process_name: str
    pid: int
    syscall: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "info"  # info, warning, critical

@dataclass
class AnomalyDetection:
    """AI-detected anomaly in kernel behavior"""
    id: str
    detected_at: datetime
    anomaly_type: str
    description: str
    confidence: float
    affected_processes: List[str]
    recommendation: str
    events: List[KernelEvent] = field(default_factory=list)

@dataclass
class BehaviorPattern:
    """Learned behavior pattern for anomaly detection"""
    pattern_name: str
    baseline_metrics: Dict[str, float]
    tolerance_range: Dict[str, Tuple[float, float]]
    last_updated: datetime = field(default_factory=datetime.now)

class EBPFIntegration:
    """
    Advanced eBPF integration for Aurora OS
    AI-powered kernel observability and anomaly detection
    """
    
    def __init__(self):
        self.llm_engine = get_llm_engine()
        self.events: deque = deque(maxlen=10000)  # Keep last 10K events
        self.anomalies: List[AnomalyDetection] = []
        self.behavior_patterns: Dict[str, BehaviorPattern] = {}
        self.active_tracers: Dict[str, BPF] = {}
        
        # Monitoring configuration
        self.monitoring_enabled = True
        self.tracing_interval = 1.0  # seconds
        self.anomaly_threshold = 0.7
        
        self.logger = logging.getLogger("Aurora.EBPFIntegration")
        self._setup_logging()
        
        # Initialize eBPF environment
        self._init_ebpf_environment()
        
        # Start background monitoring
        self._start_monitoring()
    
    def _setup_logging(self):
        """Setup logging"""
        log_dir = Path("/var/log/aurora")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(log_dir / "ebpf_integration.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _init_ebpf_environment(self):
        """Initialize eBPF environment"""
        try:
            # Check if eBPF is supported
            if not os.path.exists('/sys/fs/bpf'):
                subprocess.run(['mount', '-t', 'bpf', 'bpf', '/sys/fs/bpf'], check=True)
            
            # Check if bcc tools are available
            result = subprocess.run(['which', 'bpftrace'], capture_output=True)
            if result.returncode != 0:
                self.logger.warning("bpftrace not found, installing...")
                self._install_bcc_tools()
            
            # Initialize basic behavior patterns
            self._init_behavior_patterns()
            
            self.logger.info("eBPF environment initialized")
        
        except Exception as e:
            self.logger.error(f"Failed to initialize eBPF: {e}")
    
    def _install_bcc_tools(self):
        """Install BCC tools for eBPF"""
        try:
            subprocess.run(['apt', 'update'], check=True)
            subprocess.run(['apt', 'install', '-y', 'bcc-tools', 'bpftrace'], check=True)
            self.logger.info("BCC tools installed successfully")
        except Exception as e:
            self.logger.error(f"Failed to install BCC tools: {e}")
    
    def _init_behavior_patterns(self):
        """Initialize baseline behavior patterns"""
        # System call patterns
        self.behavior_patterns['syscall_frequency'] = BehaviorPattern(
            pattern_name="syscall_frequency",
            baseline_metrics={
                'syscalls_per_second': 1000.0,
                'error_rate': 0.01,
                'unique_syscalls': 50.0
            },
            tolerance_range={
                'syscalls_per_second': (500.0, 5000.0),
                'error_rate': (0.0, 0.05),
                'unique_syscalls': (20.0, 100.0)
            }
        )
        
        # File access patterns
        self.behavior_patterns['file_access'] = BehaviorPattern(
            pattern_name="file_access",
            baseline_metrics={
                'file_ops_per_second': 200.0,
                'read_write_ratio': 0.7,
                'unique_files_per_second': 50.0
            },
            tolerance_range={
                'file_ops_per_second': (100.0, 1000.0),
                'read_write_ratio': (0.3, 1.0),
                'unique_files_per_second': (20.0, 200.0)
            }
        )
        
        # Network patterns
        self.behavior_patterns['network_activity'] = BehaviorPattern(
            pattern_name="network_activity",
            baseline_metrics={
                'packets_per_second': 500.0,
                'connection_rate': 5.0,
                'bandwidth_utilization': 0.1
            },
            tolerance_range={
                'packets_per_second': (100.0, 2000.0),
                'connection_rate': (1.0, 20.0),
                'bandwidth_utilization': (0.0, 0.5)
            }
        )
    
    def _start_monitoring(self):
        """Start background monitoring"""
        def monitoring_loop():
            while self.monitoring_enabled:
                try:
                    # Collect system metrics
                    self._collect_system_metrics()
                    
                    # Run anomaly detection
                    asyncio.create_task(self._detect_anomalies())
                    
                    # Clean old events
                    self._cleanup_old_events()
                    
                    time.sleep(self.tracing_interval)
                
                except Exception as e:
                    self.logger.error(f"Monitoring loop error: {e}")
                    time.sleep(5)  # Wait before retrying
        
        # Start monitoring thread
        import threading
        monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
        monitoring_thread.start()
        
        self.logger.info("Background monitoring started")
    
    def _collect_system_metrics(self):
        """Collect system metrics using eBPF"""
        try:
            # System call tracing
            self._trace_syscalls()
            
            # File system tracing
            self._trace_file_operations()
            
            # Network tracing
            self._trace_network_activity()
            
            # Process tracing
            self._trace_processes()
        
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
    
    def _trace_syscalls(self):
        """Trace system calls using eBPF"""
        syscall_program = """
        #include <uapi/linux/ptrace.h>
        #include <linux/sched.h>
        
        struct syscall_event_t {
            u32 pid;
            char comm[TASK_COMM_LEN];
            u64 syscall_nr;
            u64 timestamp_ns;
            int retval;
        };
        
        BPF_PERF_OUTPUT(syscall_events);
        
        // Trace entry point for syscalls
        TRACEPOINT_PROBE(syscalls, sys_enter) {
            struct syscall_event_t event = {};
            event.pid = bpf_get_current_pid_tgid() >> 32;
            bpf_get_current_comm(&event.comm, sizeof(event.comm));
            event.syscall_nr = args->id;
            event.timestamp_ns = bpf_ktime_get_ns();
            
            syscall_events.perf_submit(args, &event, sizeof(event));
            return 0;
        }
        """
        
        try:
            if BCC_AVAILABLE:
                bpf = BPF(text=syscall_program)
                
                def handle_syscall(cpu, data, size):
                    event = bpf["syscall_events"].event(data)
                    
                    kernel_event = KernelEvent(
                        timestamp=datetime.fromtimestamp(event.timestamp_ns / 1e9),
                        event_type="syscall",
                        process_name=event.comm.decode(),
                        pid=event.pid,
                        syscall=f"syscall_{event.syscall_nr}",
                        details={'syscall_nr': event.syscall_nr}
                    )
                    
                    self.events.append(kernel_event)
                
                bpf["syscall_events"].open_perf_buffer(handle_syscall)
                bpf.perf_buffer_poll(timeout=100)
                
                if 'syscalls' not in self.active_tracers:
                    self.active_tracers['syscalls'] = bpf
        
        except Exception as e:
            self.logger.error(f"Syscall tracing error: {e}")
    
    def _trace_file_operations(self):
        """Trace file system operations"""
        fs_program = """
        #include <uapi/linux/ptrace.h>
        #include <linux/fs.h>
        
        struct file_event_t {
            u32 pid;
            char comm[TASK_COMM_LEN];
            char filename[256];
            u64 timestamp_ns;
            int operation;  // 0=read, 1=write, 2=open, 3=close
        };
        
        BPF_PERF_OUTPUT(file_events);
        
        TRACEPOINT_PROBE(syscalls, sys_enter_openat) {
            struct file_event_t event = {};
            event.pid = bpf_get_current_pid_tgid() >> 32;
            bpf_get_current_comm(&event.comm, sizeof(event.comm));
            bpf_probe_read_user_str(&event.filename, sizeof(event.filename), args->filename);
            event.timestamp_ns = bpf_ktime_get_ns();
            event.operation = 2;  // open
            
            file_events.perf_submit(args, &event, sizeof(event));
            return 0;
        }
        """
        
        try:
            if BCC_AVAILABLE:
                bpf = BPF(text=fs_program)
                
                def handle_file_event(cpu, data, size):
                    event = bpf["file_events"].event(data)
                    
                    kernel_event = KernelEvent(
                        timestamp=datetime.fromtimestamp(event.timestamp_ns / 1e9),
                        event_type="file_operation",
                        process_name=event.comm.decode(),
                        pid=event.pid,
                        details={
                            'filename': event.filename.decode(),
                            'operation': event.operation
                        }
                    )
                    
                    self.events.append(kernel_event)
                
                bpf["file_events"].open_perf_buffer(handle_file_event)
                bpf.perf_buffer_poll(timeout=100)
                
                if 'file_ops' not in self.active_tracers:
                    self.active_tracers['file_ops'] = bpf
        
        except Exception as e:
            self.logger.error(f"File operation tracing error: {e}")
    
    def _trace_network_activity(self):
        """Trace network activity"""
        network_program = """
        #include <uapi/linux/ptrace.h>
        #include <net/sock.h>
        
        struct network_event_t {
            u32 pid;
            char comm[TASK_COMM_LEN];
            u32 saddr;
            u32 daddr;
            u16 sport;
            u16 dport;
            u64 timestamp_ns;
            int protocol;  // 0=TCP, 1=UDP
        };
        
        BPF_PERF_OUTPUT(network_events);
        
        TRACEPOINT_PROBE(syscalls, sys_enter_connect) {
            struct network_event_t event = {};
            struct sockaddr_in *addr = (struct sockaddr_in *)args->addr;
            
            event.pid = bpf_get_current_pid_tgid() >> 32;
            bpf_get_current_comm(&event.comm, sizeof(event.comm));
            event.saddr = addr->sin_addr.s_addr;
            event.dport = addr->sin_port;
            event.timestamp_ns = bpf_ktime_get_ns();
            event.protocol = 0;  // TCP
            
            network_events.perf_submit(args, &event, sizeof(event));
            return 0;
        }
        """
        
        try:
            if BCC_AVAILABLE:
                bpf = BPF(text=network_program)
                
                def handle_network_event(cpu, data, size):
                    event = bpf["network_events"].event(data)
                    
                    kernel_event = KernelEvent(
                        timestamp=datetime.fromtimestamp(event.timestamp_ns / 1e9),
                        event_type="network",
                        process_name=event.comm.decode(),
                        pid=event.pid,
                        details={
                            'source_addr': event.saddr,
                            'dest_port': event.dport,
                            'protocol': event.protocol
                        }
                    )
                    
                    self.events.append(kernel_event)
                
                bpf["network_events"].open_perf_buffer(handle_network_event)
                bpf.perf_buffer_poll(timeout=100)
                
                if 'network' not in self.active_tracers:
                    self.active_tracers['network'] = bpf
        
        except Exception as e:
            self.logger.error(f"Network tracing error: {e}")
    
    def _trace_processes(self):
        """Trace process creation and termination"""
        process_program = """
        #include <uapi/linux/ptrace.h>
        #include <linux/sched.h>
        
        struct process_event_t {
            u32 pid;
            u32 ppid;
            char comm[TASK_COMM_LEN];
            char pcomm[TASK_COMM_LEN];
            u64 timestamp_ns;
            int exit_code;
            int event_type;  // 0=fork, 1=exec, 2=exit
        };
        
        BPF_PERF_OUTPUT(process_events);
        
        TRACEPOINT_PROBE(sched, sched_process_fork) {
            struct process_event_t event = {};
            event.pid = bpf_get_current_pid_tgid() >> 32;
            event.ppid = args->parent_pid;
            bpf_get_current_comm(&event.comm, sizeof(event.comm));
            bpf_probe_read(&event.pcomm, sizeof(event.pcomm), args->parent_comm);
            event.timestamp_ns = bpf_ktime_get_ns();
            event.event_type = 0;  // fork
            
            process_events.perf_submit(args, &event, sizeof(event));
            return 0;
        }
        """
        
        try:
            if BCC_AVAILABLE:
                bpf = BPF(text=process_program)
                
                def handle_process_event(cpu, data, size):
                    event = bpf["process_events"].event(data)
                    
                    kernel_event = KernelEvent(
                        timestamp=datetime.fromtimestamp(event.timestamp_ns / 1e9),
                        event_type="process",
                        process_name=event.comm.decode(),
                        pid=event.pid,
                        details={
                            'parent_pid': event.ppid,
                            'parent_comm': event.pcomm.decode(),
                            'event_type': event.event_type
                        }
                    )
                    
                    self.events.append(kernel_event)
                
                bpf["process_events"].open_perf_buffer(handle_process_event)
                bpf.perf_buffer_poll(timeout=100)
                
                if 'processes' not in self.active_tracers:
                    self.active_tracers['processes'] = bpf
        
        except Exception as e:
            self.logger.error(f"Process tracing error: {e}")
    
    def _cleanup_old_events(self):
        """Clean old events to prevent memory buildup"""
        cutoff_time = datetime.now() - timedelta(hours=1)
        
        # Remove events older than cutoff
        while self.events and self.events[0].timestamp < cutoff_time:
            self.events.popleft()
        
        # Clean old anomalies
        cutoff_anomaly = datetime.now() - timedelta(days=7)
        self.anomalies = [a for a in self.anomalies if a.detected_at > cutoff_anomaly]
    
    async def _detect_anomalies(self):
        """Detect anomalies in kernel behavior using AI"""
        try:
            # Get recent events
            recent_events = [e for e in self.events if e.timestamp > datetime.now() - timedelta(minutes=5)]
            
            if len(recent_events) < 100:
                return  # Not enough data for anomaly detection
            
            # Check each behavior pattern
            for pattern_name, pattern in self.behavior_patterns.items():
                anomaly = await self._check_pattern_anomaly(recent_events, pattern)
                if anomaly:
                    self.anomalies.append(anomaly)
                    self.logger.warning(f"Anomaly detected: {anomaly.description}")
        
        except Exception as e:
            self.logger.error(f"Anomaly detection error: {e}")
    
    async def _check_pattern_anomaly(self, events: List[KernelEvent], pattern: BehaviorPattern) -> Optional[AnomalyDetection]:
        """Check for anomalies in a specific pattern"""
        try:
            # Calculate current metrics
            current_metrics = self._calculate_pattern_metrics(events, pattern.pattern_name)
            
            # Check if metrics are outside tolerance range
            anomalies = []
            
            for metric_name, current_value in current_metrics.items():
                if metric_name in pattern.tolerance_range:
                    min_val, max_val = pattern.tolerance_range[metric_name]
                    if not (min_val <= current_value <= max_val):
                        anomalies.append({
                            'metric': metric_name,
                            'current': current_value,
                            'expected_range': (min_val, max_val),
                            'severity': 'high' if abs(current_value - (min_val + max_val) / 2) > (max_val - min_val) / 2 else 'medium'
                        })
            
            if anomalies:
                # Generate human-readable description using AI
                description = await self._explain_anomaly(anomalies, pattern)
                
                # Get affected processes
                affected_processes = list(set(e.process_name for e in events[-100:]))
                
                # Generate recommendation
                recommendation = await self._generate_recommendation(anomalies, pattern)
                
                return AnomalyDetection(
                    id=f"anomaly_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    detected_at=datetime.now(),
                    anomaly_type=pattern.pattern_name,
                    description=description,
                    confidence=min(0.9, sum(1 for a in anomalies if a['severity'] == 'high') / len(anomalies) + 0.5),
                    affected_processes=affected_processes,
                    recommendation=recommendation,
                    events=events[-10:]  # Keep last 10 events as context
                )
        
        except Exception as e:
            self.logger.error(f"Pattern anomaly check error: {e}")
        
        return None
    
    def _calculate_pattern_metrics(self, events: List[KernelEvent], pattern_name: str) -> Dict[str, float]:
        """Calculate metrics for a specific pattern"""
        if not events:
            return {}
        
        if pattern_name == 'syscall_frequency':
            return self._calculate_syscall_metrics(events)
        elif pattern_name == 'file_access':
            return self._calculate_file_metrics(events)
        elif pattern_name == 'network_activity':
            return self._calculate_network_metrics(events)
        
        return {}
    
    def _calculate_syscall_metrics(self, events: List[KernelEvent]) -> Dict[str, float]:
        """Calculate system call metrics"""
        syscall_events = [e for e in events if e.event_type == 'syscall']
        
        if not syscall_events:
            return {}
        
        time_span = (events[-1].timestamp - events[0].timestamp).total_seconds()
        syscalls_per_second = len(syscall_events) / max(time_span, 1)
        
        # Calculate error rate (this would need more sophisticated logic)
        error_rate = 0.01  # Placeholder
        
        unique_syscalls = len(set(e.syscall for e in syscall_events))
        
        return {
            'syscalls_per_second': syscalls_per_second,
            'error_rate': error_rate,
            'unique_syscalls': float(unique_syscalls)
        }
    
    def _calculate_file_metrics(self, events: List[KernelEvent]) -> Dict[str, float]:
        """Calculate file access metrics"""
        file_events = [e for e in events if e.event_type == 'file_operation']
        
        if not file_events:
            return {}
        
        time_span = (events[-1].timestamp - events[0].timestamp).total_seconds()
        file_ops_per_second = len(file_events) / max(time_span, 1)
        
        # Calculate read/write ratio
        read_ops = sum(1 for e in file_events if e.details.get('operation') == 0)
        write_ops = sum(1 for e in file_events if e.details.get('operation') == 1)
        read_write_ratio = read_ops / max(read_ops + write_ops, 1)
        
        unique_files = len(set(e.details.get('filename', '') for e in file_events))
        unique_files_per_second = unique_files / max(time_span, 1)
        
        return {
            'file_ops_per_second': file_ops_per_second,
            'read_write_ratio': read_write_ratio,
            'unique_files_per_second': unique_files_per_second
        }
    
    def _calculate_network_metrics(self, events: List[KernelEvent]) -> Dict[str, float]:
        """Calculate network activity metrics"""
        network_events = [e for e in events if e.event_type == 'network']
        
        if not network_events:
            return {}
        
        time_span = (events[-1].timestamp - events[0].timestamp).total_seconds()
        packets_per_second = len(network_events) / max(time_span, 1)
        
        # Connection rate (simplified)
        connection_rate = packets_per_second / 10  # Assume 10 packets per connection
        
        # Bandwidth utilization (simplified)
        bandwidth_utilization = min(1.0, packets_per_second / 1000)
        
        return {
            'packets_per_second': packets_per_second,
            'connection_rate': connection_rate,
            'bandwidth_utilization': bandwidth_utilization
        }
    
    async def _explain_anomaly(self, anomalies: List[Dict], pattern: BehaviorPattern) -> str:
        """Generate human-readable explanation of anomaly"""
        try:
            prompt = f"""
            Explain the following kernel behavior anomalies in simple terms:
            
            Pattern: {pattern.pattern_name}
            Anomalies detected:
            {json.dumps(anomalies, indent=2)}
            
            Explain what this means for the user and why it matters.
            Keep the explanation technical but understandable.
            """
            
            from ...ai_assistant.core.local_llm_engine import AIRequest
            request = AIRequest(
                prompt=prompt,
                max_tokens=300,
                temperature=0.5
            )
            
            response = await self.llm_engine.generate_response(request)
            return response.text
        
        except Exception as e:
            self.logger.error(f"Failed to explain anomaly: {e}")
            return f"Anomaly detected in {pattern.pattern_name} with {len(anomalies)} metric deviations"
    
    async def _generate_recommendation(self, anomalies: List[Dict], pattern: BehaviorPattern) -> str:
        """Generate recommendation for addressing the anomaly"""
        try:
            prompt = f"""
            Generate a recommendation for addressing these kernel anomalies:
            
            Pattern: {pattern.pattern_name}
            Anomalies: {json.dumps(anomalies, indent=2)}
            
            Provide actionable steps the system or user should take.
            Focus on security, performance, and stability.
            """
            
            from ...ai_assistant.core.local_llm_engine import AIRequest
            request = AIRequest(
                prompt=prompt,
                max_tokens=200,
                temperature=0.3
            )
            
            response = await self.llm_engine.generate_response(request)
            return response.text
        
        except Exception as e:
            self.logger.error(f"Failed to generate recommendation: {e}")
            return "Monitor system closely and consider investigating affected processes"
    
    async def explain_kernel_behavior(self, query: str, time_window_minutes: int = 5) -> str:
        """Explain kernel behavior in response to user query"""
        try:
            # Get relevant events
            cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
            relevant_events = [e for e in self.events if e.timestamp > cutoff_time]
            
            if not relevant_events:
                return "No recent kernel activity to analyze"
            
            # Prepare event summary
            event_summary = {
                'total_events': len(relevant_events),
                'event_types': list(set(e.event_type for e in relevant_events)),
                'affected_processes': list(set(e.process_name for e in relevant_events)),
                'time_span_minutes': time_window_minutes,
                'sample_events': [
                    {
                        'type': e.event_type,
                        'process': e.process_name,
                        'timestamp': e.timestamp.isoformat(),
                        'details': e.details
                    }
                    for e in relevant_events[:10]
                ]
            }
            
            # Generate explanation using AI
            prompt = f"""
            User query: "{query}"
            
            Recent kernel activity:
            {json.dumps(event_summary, indent=2)}
            
            Explain what's happening in the kernel in response to the user's query.
            Be specific and helpful, focusing on the aspects the user asked about.
            """
            
            from ...ai_assistant.core.local_llm_engine import AIRequest
            request = AIRequest(
                prompt=prompt,
                max_tokens=500,
                temperature=0.5
            )
            
            response = await self.llm_engine.generate_response(request)
            return response.text
        
        except Exception as e:
            self.logger.error(f"Failed to explain kernel behavior: {e}")
            return f"Unable to analyze kernel behavior: {str(e)}"
    
    def get_recent_anomalies(self, hours: int = 24) -> List[AnomalyDetection]:
        """Get recent anomalies"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [a for a in self.anomalies if a.detected_at > cutoff_time]
    
    def get_system_health_score(self) -> float:
        """Calculate overall system health score"""
        try:
            recent_anomalies = self.get_recent_anomalies(hours=1)
            
            # Base score starts at 1.0
            score = 1.0
            
            # Deduct points for recent anomalies
            for anomaly in recent_anomalies:
                score -= anomaly.confidence * 0.1
            
            # Consider system load
            recent_events = [e for e in self.events if e.timestamp > datetime.now() - timedelta(minutes=5)]
            if len(recent_events) > 5000:  # Very high activity
                score -= 0.1
            
            return max(0.0, min(1.0, score))
        
        except:
            return 0.5  # Default to medium health
    
    def get_event_statistics(self, minutes: int = 60) -> Dict[str, Any]:
        """Get statistics about recent events"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_events = [e for e in self.events if e.timestamp > cutoff_time]
        
        if not recent_events:
            return {}
        
        # Calculate statistics
        event_types = defaultdict(int)
        processes = defaultdict(int)
        severity_counts = defaultdict(int)
        
        for event in recent_events:
            event_types[event.event_type] += 1
            processes[event.process_name] += 1
            severity_counts[event.severity] += 1
        
        return {
            'total_events': len(recent_events),
            'event_types': dict(event_types),
            'top_processes': dict(sorted(processes.items(), key=lambda x: x[1], reverse=True)[:10]),
            'severity_distribution': dict(severity_counts),
            'events_per_minute': len(recent_events) / minutes,
            'time_span_minutes': minutes
        }
    
    def cleanup(self):
        """Cleanup eBPF resources"""
        try:
            self.monitoring_enabled = False
            
            # Detach all active tracers
            for tracer_name, tracer in self.active_tracers.items():
                try:
                    tracer.cleanup()
                except:
                    pass
            
            self.active_tracers.clear()
            self.events.clear()
            self.anomalies.clear()
            
            self.logger.info("eBPF integration cleaned up")
        
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")

# Global eBPF integration instance
_ebpf_integration = None

def get_ebpf_integration() -> EBPFIntegration:
    """Get global eBPF integration instance"""
    global _ebpf_integration
    if _ebpf_integration is None:
        _ebpf_integration = EBPFIntegration()
    return _ebpf_integration

async def initialize_ebpf_system():
    """Initialize the eBPF integration system"""
    ebpf = get_ebpf_integration()
    return ebpf