"""
Aurora OS Log Aggregation and Analysis System
Advanced log collection, aggregation, and intelligent analysis
"""

import asyncio
import json
import logging
import time
import uuid
import re
from typing import Dict, List, Optional, Any, Set, Tuple, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
import gzip
import hashlib

class LogLevel(Enum):
    """Log levels"""
    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    FATAL = "fatal"

class LogFormat(Enum):
    """Log formats"""
    JSON = "json"
    PLAINTEXT = "plaintext"
    STRUCTURED = "structured"
    SYSLOG = "syslog"

class LogSourceType(Enum):
    """Log source types"""
    APPLICATION = "application"
    SYSTEM = "system"
    KERNEL = "kernel"
    NETWORK = "network"
    SECURITY = "security"
    DATABASE = "database"
    WEB_SERVER = "web_server"

@dataclass
class LogEntry:
    """Log entry"""
    id: str
    timestamp: datetime
    level: LogLevel
    message: str
    source: str
    source_type: LogSourceType
    host: str
    process_id: Optional[int]
    thread_id: Optional[str]
    user_id: Optional[str]
    session_id: Optional[str]
    request_id: Optional[str]
    trace_id: Optional[str]
    span_id: Optional[str]
    tags: Set[str]
    fields: Dict[str, Any]
    raw_message: str
    
    def __post_init__(self):
        """Post-initialization"""
        if self.tags is None:
            self.tags = set()
        if self.fields is None:
            self.fields = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "message": self.message,
            "source": self.source,
            "source_type": self.source_type.value,
            "host": self.host,
            "process_id": self.process_id,
            "thread_id": self.thread_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "tags": list(self.tags),
            "fields": self.fields,
            "raw_message": self.raw_message
        }
    
    def get_severity_score(self) -> int:
        """Get severity score for prioritization"""
        severity_scores = {
            LogLevel.TRACE: 1,
            LogLevel.DEBUG: 2,
            LogLevel.INFO: 3,
            LogLevel.WARN: 4,
            LogLevel.ERROR: 5,
            LogLevel.FATAL: 6
        }
        return severity_scores.get(self.level, 3)

class LogParser:
    """Log parser for different formats"""
    
    @staticmethod
    def parse_json_log(raw_log: str) -> Optional[LogEntry]:
        """Parse JSON log entry"""
        try:
            data = json.loads(raw_log)
            
            return LogEntry(
                id=data.get("id", str(uuid.uuid4())),
                timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
                level=LogLevel(data.get("level", "info")),
                message=data.get("message", ""),
                source=data.get("source", "unknown"),
                source_type=LogSourceType(data.get("source_type", "application")),
                host=data.get("host", ""),
                process_id=data.get("process_id"),
                thread_id=data.get("thread_id"),
                user_id=data.get("user_id"),
                session_id=data.get("session_id"),
                request_id=data.get("request_id"),
                trace_id=data.get("trace_id"),
                span_id=data.get("span_id"),
                tags=set(data.get("tags", [])),
                fields=data.get("fields", {}),
                raw_message=raw_log
            )
        except Exception as e:
            logging.error(f"Error parsing JSON log: {e}")
            return None
    
    @staticmethod
    def parse_syslog(raw_log: str) -> Optional[LogEntry]:
        """Parse syslog format"""
        # Basic syslog regex: <priority>timestamp host process: message
        syslog_pattern = r'^<(\d+)>(\w+\s+\d+\s+\d+:\d+:\d+)\s+(\S+)\s+([^:]+):\s*(.*)$'
        match = re.match(syslog_pattern, raw_log.strip())
        
        if not match:
            return None
        
        priority, timestamp_str, host, process, message = match.groups()
        
        # Convert syslog priority to level
        facility = int(priority) >> 3
        severity = int(priority) & 7
        
        level_map = {
            0: LogLevel.FATAL,  # Emergency
            1: LogLevel.FATAL,  # Alert
            2: LogLevel.ERROR,  # Critical
            3: LogLevel.ERROR,  # Error
            4: LogLevel.WARN,   # Warning
            5: LogLevel.INFO,   # Notice
            6: LogLevel.INFO,   # Info
            7: LogLevel.DEBUG   # Debug
        }
        
        return LogEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.strptime(timestamp_str, "%b %d %H:%M:%S"),
            level=level_map.get(severity, LogLevel.INFO),
            message=message,
            source=process,
            source_type=LogSourceType.SYSTEM,
            host=host,
            process_id=None,
            thread_id=None,
            user_id=None,
            session_id=None,
            request_id=None,
            trace_id=None,
            span_id=None,
            tags={"syslog"},
            fields={"facility": facility, "severity": severity},
            raw_message=raw_log
        )
    
    @staticmethod
    def parse_plaintext(raw_log: str) -> LogEntry:
        """Parse plain text log entry"""
        return LogEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            message=raw_log.strip(),
            source="plaintext",
            source_type=LogSourceType.APPLICATION,
            host="",
            process_id=None,
            thread_id=None,
            user_id=None,
            session_id=None,
            request_id=None,
            trace_id=None,
            span_id=None,
            tags=set(),
            fields={},
            raw_message=raw_log
        )

class LogFilter:
    """Log entry filter"""
    
    def __init__(self):
        self.filters: List[Callable[[LogEntry], bool]] = []
    
    def add_level_filter(self, min_level: LogLevel):
        """Add level filter"""
        def level_filter(entry: LogEntry) -> bool:
            level_scores = {
                LogLevel.TRACE: 1,
                LogLevel.DEBUG: 2,
                LogLevel.INFO: 3,
                LogLevel.WARN: 4,
                LogLevel.ERROR: 5,
                LogLevel.FATAL: 6
            }
            return level_scores[entry.level] >= level_scores[min_level]
        
        self.filters.append(level_filter)
    
    def add_source_filter(self, source_pattern: str):
        """Add source filter"""
        def source_filter(entry: LogEntry) -> bool:
            return re.search(source_pattern, entry.source, re.IGNORECASE) is not None
        
        self.filters.append(source_filter)
    
    def add_time_range_filter(self, start_time: datetime, end_time: datetime):
        """Add time range filter"""
        def time_filter(entry: LogEntry) -> bool:
            return start_time <= entry.timestamp <= end_time
        
        self.filters.append(time_filter)
    
    def add_message_filter(self, message_pattern: str):
        """Add message content filter"""
        def message_filter(entry: LogEntry) -> bool:
            return re.search(message_pattern, entry.message, re.IGNORECASE) is not None
        
        self.filters.append(message_filter)
    
    def add_tag_filter(self, required_tags: Set[str]):
        """Add tag filter"""
        def tag_filter(entry: LogEntry) -> bool:
            return required_tags.issubset(entry.tags)
        
        self.filters.append(tag_filter)
    
    def matches(self, entry: LogEntry) -> bool:
        """Check if entry matches all filters"""
        return all(filter_func(entry) for filter_func in self.filters)

class LogAnalyzer:
    """Log analysis and pattern detection"""
    
    def __init__(self):
        self.patterns = {
            "error_patterns": [
                r"error",
                r"exception",
                r"failed",
                r"timeout",
                r"connection refused",
                r"access denied"
            ],
            "security_patterns": [
                r"authentication failed",
                r"unauthorized access",
                r"suspicious activity",
                r"brute force",
                r"intrusion detected"
            ],
            "performance_patterns": [
                r"slow query",
                r"high latency",
                r"memory leak",
                r"cpu overload",
                r"disk space low"
            ]
        }
        
        self.analysis_cache: Dict[str, Dict[str, Any]] = {}
    
    def analyze_entry(self, entry: LogEntry) -> Dict[str, Any]:
        """Analyze a single log entry"""
        analysis = {
            "severity_score": entry.get_severity_score(),
            "categories": [],
            "anomalies": [],
            "correlations": [],
            "recommendations": []
        }
        
        # Check for patterns
        message_lower = entry.message.lower()
        
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    analysis["categories"].append(category)
                    
                    # Add recommendations based on category
                    if category == "error_patterns":
                        analysis["recommendations"].append("Review error logs and fix underlying issues")
                    elif category == "security_patterns":
                        analysis["recommendations"].append("Investigate potential security threat")
                    elif category == "performance_patterns":
                        analysis["recommendations"].append("Optimize system performance")
        
        # Detect anomalies
        if entry.level in [LogLevel.ERROR, LogLevel.FATAL]:
            analysis["anomalies"].append(f"High severity log: {entry.level.value}")
        
        if len(entry.message) > 1000:
            analysis["anomalies"].append("Unusually long log message")
        
        return analysis
    
    def analyze_batch(self, entries: List[LogEntry], 
                     time_window: timedelta = timedelta(hours=1)) -> Dict[str, Any]:
        """Analyze a batch of log entries"""
        if not entries:
            return {}
        
        # Sort by timestamp
        entries.sort(key=lambda e: e.timestamp)
        
        # Group by time windows
        windows = defaultdict(list)
        start_time = entries[0].timestamp
        
        for entry in entries:
            window_index = int((entry.timestamp - start_time) // time_window)
            windows[window_index].append(entry)
        
        analysis = {
            "total_entries": len(entries),
            "time_range": {
                "start": entries[0].timestamp.isoformat(),
                "end": entries[-1].timestamp.isoformat()
            },
            "level_distribution": defaultdict(int),
            "source_distribution": defaultdict(int),
            "error_rate": 0,
            "anomaly_count": 0,
            "patterns_detected": defaultdict(int),
            "recommendations": []
        }
        
        # Calculate distributions
        error_count = 0
        for entry in entries:
            analysis["level_distribution"][entry.level.value] += 1
            analysis["source_distribution"][entry.source] += 1
            
            if entry.level in [LogLevel.ERROR, LogLevel.FATAL]:
                error_count += 1
            
            # Analyze individual entries
            entry_analysis = self.analyze_entry(entry)
            for category in entry_analysis["categories"]:
                analysis["patterns_detected"][category] += 1
            
            analysis["anomaly_count"] += len(entry_analysis["anomalies"])
        
        analysis["error_rate"] = (error_count / len(entries)) * 100
        
        # Generate recommendations
        if analysis["error_rate"] > 10:
            analysis["recommendations"].append("High error rate detected - investigate system health")
        
        if analysis["patterns_detected"]["security_patterns"] > 0:
            analysis["recommendations"].append("Security patterns detected - review access logs")
        
        if analysis["patterns_detected"]["performance_patterns"] > 0:
            analysis["recommendations"].append("Performance issues detected - optimize system")
        
        return analysis

class LogStorage:
    """Log storage backend"""
    
    def __init__(self, storage_path: str = "/var/log/aurora"):
        self.storage_path = storage_path
        self.index_file = f"{storage_path}/logs.index"
        self.lock = threading.RLock()
        
        # Create storage directory
        import os
        os.makedirs(storage_path, exist_ok=True)
    
    def store_entry(self, entry: LogEntry) -> bool:
        """Store a log entry"""
        try:
            with self.lock:
                # Generate file path based on date
                date_str = entry.timestamp.strftime("%Y/%m/%d")
                file_path = f"{self.storage_path}/{date_str}/logs.jsonl"
                
                # Ensure directory exists
                import os
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Append to file
                with open(file_path, "a") as f:
                    f.write(json.dumps(entry.to_dict()) + "\n")
                
                # Update index
                self._update_index(entry, file_path)
                
                return True
        except Exception as e:
            logging.error(f"Error storing log entry: {e}")
            return False
    
    def _update_index(self, entry: LogEntry, file_path: str):
        """Update log index"""
        try:
            index_entry = {
                "id": entry.id,
                "timestamp": entry.timestamp.isoformat(),
                "level": entry.level.value,
                "source": entry.source,
                "file_path": file_path,
                "hash": hashlib.md5(entry.raw_message.encode()).hexdigest()
            }
            
            with open(self.index_file, "a") as f:
                f.write(json.dumps(index_entry) + "\n")
        except Exception as e:
            logging.error(f"Error updating index: {e}")
    
    def query_entries(self, filter_obj: LogFilter, 
                     limit: int = 1000, 
                     offset: int = 0) -> List[LogEntry]:
        """Query log entries"""
        entries = []
        
        try:
            with self.lock:
                # Read index
                matching_files = set()
                
                if os.path.exists(self.index_file):
                    with open(self.index_file, "r") as f:
                        for line in f:
                            try:
                                index_entry = json.loads(line.strip())
                                # This is simplified - in production, would use proper indexing
                                matching_files.add(index_entry["file_path"])
                            except json.JSONDecodeError:
                                continue
                
                # Read log files
                for file_path in matching_files:
                    if os.path.exists(file_path):
                        with open(file_path, "r") as f:
                            for line in f:
                                try:
                                    log_data = json.loads(line.strip())
                                    entry = LogEntry(
                                        id=log_data["id"],
                                        timestamp=datetime.fromisoformat(log_data["timestamp"]),
                                        level=LogLevel(log_data["level"]),
                                        message=log_data["message"],
                                        source=log_data["source"],
                                        source_type=LogSourceType(log_data["source_type"]),
                                        host=log_data["host"],
                                        process_id=log_data.get("process_id"),
                                        thread_id=log_data.get("thread_id"),
                                        user_id=log_data.get("user_id"),
                                        session_id=log_data.get("session_id"),
                                        request_id=log_data.get("request_id"),
                                        trace_id=log_data.get("trace_id"),
                                        span_id=log_data.get("span_id"),
                                        tags=set(log_data.get("tags", [])),
                                        fields=log_data.get("fields", {}),
                                        raw_message=log_data["raw_message"]
                                    )
                                    
                                    if filter_obj.matches(entry):
                                        entries.append(entry)
                                        
                                        if len(entries) >= limit + offset:
                                            break
                                except (json.JSONDecodeError, KeyError, ValueError):
                                    continue
                            
                            if len(entries) >= limit + offset:
                                break
                
                return entries[offset:offset + limit]
                
        except Exception as e:
            logging.error(f"Error querying log entries: {e}")
            return []

class LogAggregator:
    """Main log aggregation system"""
    
    def __init__(self, storage_path: str = "/var/log/aurora"):
        self.logger = logging.getLogger(__name__)
        self.storage = LogStorage(storage_path)
        self.analyzer = LogAnalyzer()
        
        # Log collection sources
        self.sources: Dict[str, Callable] = {}
        
        # Buffer for collected logs
        self.log_buffer: deque = deque(maxlen=10000)
        
        # Statistics
        self.stats = {
            "logs_collected": 0,
            "logs_stored": 0,
            "logs_processed": 0,
            "errors": 0,
            "sources_active": 0
        }
        
        # Background processing
        self.background_tasks: List[asyncio.Task] = []
        self._running = False
        
        # Thread pool for synchronous operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Lock for thread safety
        self._lock = threading.RLock()
    
    def add_source(self, name: str, source_func: Callable):
        """Add log source"""
        self.sources[name] = source_func
        self.stats["sources_active"] += 1
        self.logger.info(f"Added log source: {name}")
    
    def collect_log(self, raw_log: str, format_type: LogFormat = LogFormat.PLAINTEXT,
                   source_name: str = "unknown") -> Optional[LogEntry]:
        """Collect and parse a log entry"""
        try:
            # Parse log based on format
            if format_type == LogFormat.JSON:
                entry = LogParser.parse_json_log(raw_log)
            elif format_type == LogFormat.SYSLOG:
                entry = LogParser.parse_syslog(raw_log)
            else:
                entry = LogParser.parse_plaintext(raw_log)
            
            if entry:
                entry.source = source_name
                
                with self._lock:
                    self.log_buffer.append(entry)
                    self.stats["logs_collected"] += 1
                
                return entry
            
        except Exception as e:
            self.logger.error(f"Error collecting log: {e}")
            self.stats["errors"] += 1
        
        return None
    
    async def start_aggregation(self):
        """Start log aggregation"""
        if self._running:
            return
        
        self._running = True
        self.logger.info("Starting log aggregation")
        
        # Start source collection tasks
        for name, source_func in self.sources.items():
            task = asyncio.create_task(self._source_loop(name, source_func))
            self.background_tasks.append(task)
        
        # Start processing task
        processing_task = asyncio.create_task(self._processing_loop())
        self.background_tasks.append(processing_task)
        
        # Start cleanup task
        cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.background_tasks.append(cleanup_task)
    
    async def stop_aggregation(self):
        """Stop log aggregation"""
        self._running = False
        
        # Cancel all background tasks
        for task in self.background_tasks:
            task.cancel()
        
        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        self.background_tasks.clear()
        self.logger.info("Stopped log aggregation")
    
    async def _source_loop(self, name: str, source_func: Callable):
        """Background source collection loop"""
        while self._running:
            try:
                if asyncio.iscoroutinefunction(source_func):
                    logs = await source_func()
                else:
                    logs = await asyncio.get_event_loop().run_in_executor(
                        self.executor, source_func
                    )
                
                if logs:
                    for log_data in logs:
                        if isinstance(log_data, str):
                            self.collect_log(log_data, LogFormat.PLAINTEXT, name)
                        elif isinstance(log_data, dict):
                            self.collect_log(json.dumps(log_data), LogFormat.JSON, name)
                
                await asyncio.sleep(1)  # Collect every second
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in source {name}: {e}")
                self.stats["errors"] += 1
                await asyncio.sleep(5)
    
    async def _processing_loop(self):
        """Background processing loop"""
        while self._running:
            try:
                # Process log buffer
                entries_to_process = []
                
                with self._lock:
                    while self.log_buffer:
                        entries_to_process.append(self.log_buffer.popleft())
                
                # Store entries
                for entry in entries_to_process:
                    success = self.storage.store_entry(entry)
                    if success:
                        self.stats["logs_stored"] += 1
                    self.stats["logs_processed"] += 1
                
                await asyncio.sleep(0.1)  # Process every 100ms
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in processing: {e}")
                self.stats["errors"] += 1
                await asyncio.sleep(1)
    
    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while self._running:
            try:
                # Cleanup old log files (implement if needed)
                await asyncio.sleep(3600)  # Every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup: {e}")
                await asyncio.sleep(300)
    
    def query_logs(self, filter_obj: LogFilter, 
                   limit: int = 100, offset: int = 0) -> List[LogEntry]:
        """Query logs"""
        return self.storage.query_entries(filter_obj, limit, offset)
    
    def analyze_logs(self, filter_obj: LogFilter = None,
                    time_window: timedelta = timedelta(hours=1)) -> Dict[str, Any]:
        """Analyze logs"""
        # Get recent logs
        if filter_obj is None:
            filter_obj = LogFilter()
            filter_obj.add_time_range_filter(
                datetime.now() - timedelta(hours=24),
                datetime.now()
            )
        
        entries = self.query_logs(filter_obj, limit=10000)
        
        return self.analyzer.analyze_batch(entries, time_window)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get aggregation statistics"""
        with self._lock:
            stats = self.stats.copy()
            stats["buffer_size"] = len(self.log_buffer)
            stats["background_tasks"] = len(self.background_tasks)
            return stats

# Log collection sources
class FileLogSource:
    """File-based log source"""
    
    def __init__(self, file_path: str, format_type: LogFormat = LogFormat.PLAINTEXT):
        self.file_path = file_path
        self.format_type = format_type
        self.last_position = 0
    
    def __call__(self) -> List[str]:
        """Read new lines from file"""
        try:
            if not os.path.exists(self.file_path):
                return []
            
            with open(self.file_path, "r") as f:
                f.seek(self.last_position)
                new_lines = f.readlines()
                self.last_position = f.tell()
                
                return [line.strip() for line in new_lines if line.strip()]
        
        except Exception as e:
            logging.error(f"Error reading file {self.file_path}: {e}")
            return []

class ApplicationLogSource:
    """Application log source"""
    
    def __init__(self):
        self.log_buffer = deque(maxlen=1000)
    
    def log(self, level: str, message: str, **kwargs):
        """Add log entry"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            **kwargs
        }
        self.log_buffer.append(json.dumps(log_entry))
    
    def __call__(self) -> List[str]:
        """Get buffered logs"""
        logs = list(self.log_buffer)
        self.log_buffer.clear()
        return logs

# Global log aggregator instance
_log_aggregator = None

def get_log_aggregator() -> LogAggregator:
    """Get global log aggregator instance"""
    global _log_aggregator
    if _log_aggregator is None:
        _log_aggregator = LogAggregator()
    return _log_aggregator

def init_log_aggregation(storage_path: str = "/var/log/aurora"):
    """Initialize log aggregation"""
    aggregator = LogAggregator(storage_path)
    
    # Add default sources
    app_source = ApplicationLogSource()
    aggregator.add_source("application", app_source)
    
    return aggregator