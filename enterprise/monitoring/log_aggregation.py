"""
Aurora OS Log Aggregation and Analysis System
Advanced log collection, parsing, and analysis with anomaly detection
"""

import asyncio
import json
import logging
import time
import uuid
import re
import gzip
import hashlib
from typing import Dict, List, Optional, Any, Set, Tuple, Union, Callable, Pattern
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque, Counter
import threading
from concurrent.futures import ThreadPoolExecutor
import struct

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
    PLAIN_TEXT = "plain_text"
    SYSLOG = "syslog"
    APACHE = "apache"
    NGINX = "nginx"
    CUSTOM = "custom"

class LogSource(Enum):
    """Log sources"""
    APPLICATION = "application"
    SYSTEM = "system"
    KERNEL = "kernel"
    SECURITY = "security"
    NETWORK = "network"
    DATABASE = "database"
    CONTAINER = "container"

class AnomalyType(Enum):
    """Anomaly types"""
    SPIKE = "spike"
    UNUSUAL_PATTERN = "unusual_pattern"
    ABSENT_PATTERN = "absent_pattern"
    RATE_ANOMALY = "rate_anomaly"
    CONTENT_ANOMALY = "content_anomaly"

@dataclass
class LogEntry:
    """Log entry"""
    id: str
    timestamp: datetime
    level: LogLevel
    message: str
    source: str
    service: str
    hostname: str
    process_id: Optional[int]
    thread_id: Optional[str]
    user_id: Optional[str]
    session_id: Optional[str]
    request_id: Optional[str]
    trace_id: Optional[str]
    tags: Dict[str, str]
    fields: Dict[str, Any]
    raw_data: str
    
    def __post_init__(self):
        """Post-initialization"""
        if self.tags is None:
            self.tags = {}
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
            "service": self.service,
            "hostname": self.hostname,
            "process_id": self.process_id,
            "thread_id": self.thread_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "tags": self.tags,
            "fields": self.fields,
            "raw_data": self.raw_data
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())
    
    def get_hash(self) -> str:
        """Get hash of log entry for deduplication"""
        content = f"{self.timestamp.isoformat()}{self.level.value}{self.message}{self.service}{self.hostname}"
        return hashlib.sha256(content.encode()).hexdigest()

@dataclass
class LogPattern:
    """Log pattern for matching"""
    name: str
    pattern: Pattern
    severity: LogLevel
    description: str
    sample_messages: List[str]
    field_extractors: Dict[str, Pattern] = field(default_factory=dict)
    
    def match(self, message: str) -> Optional[Dict[str, str]]:
        """Match pattern and extract fields"""
        match = self.pattern.search(message)
        if match:
            result = {"matched": True, "pattern": self.name}
            
            # Extract additional fields
            for field_name, field_pattern in self.field_extractors.items():
                field_match = field_pattern.search(message)
                if field_match:
                    result[field_name] = field_match.group(1) if field_match.groups() else field_match.group(0)
            
            return result
        return None

@dataclass
class LogAnomaly:
    """Log anomaly detection result"""
    id: str
    anomaly_type: AnomalyType
    severity: LogLevel
    confidence: float
    description: str
    affected_entries: List[str]  # Log entry IDs
    detected_at: datetime
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "anomaly_type": self.anomaly_type.value,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "description": self.description,
            "affected_entries": self.affected_entries,
            "detected_at": self.detected_at.isoformat(),
            "metadata": self.metadata
        }

class LogParser:
    """Log parser for different formats"""
    
    def __init__(self):
        self.parsers = {
            LogFormat.JSON: self._parse_json,
            LogFormat.PLAIN_TEXT: self._parse_plain_text,
            LogFormat.SYSLOG: self._parse_syslog,
            LogFormat.APACHE: self._parse_apache,
            LogFormat.NGINX: self._parse_nginx
        }
        
        # Common regex patterns
        self.timestamp_patterns = [
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',
            r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
            r'\w{3} \d{2} \d{2}:\d{2}:\d{2}',
            r'\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}'
        ]
    
    def parse(self, log_data: str, log_format: LogFormat = LogFormat.PLAIN_TEXT) -> Optional[LogEntry]:
        """Parse log entry"""
        parser_func = self.parsers.get(log_format, self._parse_plain_text)
        return parser_func(log_data)
    
    def _parse_json(self, log_data: str) -> Optional[LogEntry]:
        """Parse JSON log format"""
        try:
            data = json.loads(log_data)
            
            return LogEntry(
                id=str(uuid.uuid4()),
                timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
                level=LogLevel(data.get("level", "info").lower()),
                message=data.get("message", ""),
                source=data.get("source", "unknown"),
                service=data.get("service", "unknown"),
                hostname=data.get("hostname", ""),
                process_id=data.get("process_id"),
                thread_id=data.get("thread_id"),
                user_id=data.get("user_id"),
                session_id=data.get("session_id"),
                request_id=data.get("request_id"),
                trace_id=data.get("trace_id"),
                tags=data.get("tags", {}),
                fields=data.get("fields", {}),
                raw_data=log_data
            )
        except (json.JSONDecodeError, ValueError) as e:
            logging.error(f"Failed to parse JSON log: {e}")
            return None
    
    def _parse_plain_text(self, log_data: str) -> Optional[LogEntry]:
        """Parse plain text log format"""
        try:
            lines = log_data.strip().split('\n')
            if not lines:
                return None
            
            line = lines[0]
            
            # Try to extract timestamp
            timestamp = datetime.now()
            message = line
            
            for pattern in self.timestamp_patterns:
                match = re.search(pattern, line)
                if match:
                    timestamp_str = match.group(0)
                    try:
                        # Try different timestamp formats
                        if 'T' in timestamp_str:
                            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        else:
                            # For syslog-like formats
                            timestamp = datetime.strptime(timestamp_str, '%b %d %H:%M:%S')
                            timestamp = timestamp.replace(year=datetime.now().year)
                        
                        message = line.replace(timestamp_str, '').strip()
                        break
                    except ValueError:
                        continue
            
            # Extract log level
            level = LogLevel.INFO
            for log_level in LogLevel:
                if log_level.value.upper() in line.upper():
                    level = log_level
                    break
            
            # Extract service name (common pattern)
            service = "unknown"
            service_match = re.search(r'\[([\w\-_]+)\]', line)
            if service_match:
                service = service_match.group(1)
            
            return LogEntry(
                id=str(uuid.uuid4()),
                timestamp=timestamp,
                level=level,
                message=message,
                source=LogSource.APPLICATION.value,
                service=service,
                hostname="",
                process_id=None,
                thread_id=None,
                user_id=None,
                session_id=None,
                request_id=None,
                trace_id=None,
                tags={},
                fields={},
                raw_data=log_data
            )
        except Exception as e:
            logging.error(f"Failed to parse plain text log: {e}")
            return None
    
    def _parse_syslog(self, log_data: str) -> Optional[LogEntry]:
        """Parse syslog format"""
        # Simplified syslog parsing
        try:
            # RFC3164 format: <priority>timestamp hostname tag: message
            priority_match = re.match(r'^<(\d+)>', log_data)
            if not priority_match:
                return self._parse_plain_text(log_data)
            
            priority = int(priority_match.group(1))
            facility = priority >> 3
            severity = priority & 7
            
            remaining = log_data[priority_match.end():]
            
            # Extract timestamp
            timestamp = datetime.now()
            timestamp_match = re.match(r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+', remaining)
            if timestamp_match:
                timestamp_str = timestamp_match.group(1)
                timestamp = datetime.strptime(timestamp_str, '%b %d %H:%M:%S')
                timestamp = timestamp.replace(year=datetime.now().year)
                remaining = remaining[timestamp_match.end():]
            
            # Extract hostname
            hostname = ""
            hostname_match = re.match(r'(\S+)\s+', remaining)
            if hostname_match:
                hostname = hostname_match.group(1)
                remaining = remaining[hostname_match.end():]
            
            # Extract tag and message
            tag = ""
            message = remaining
            tag_match = re.match(r'([^:\s]+):\s*', remaining)
            if tag_match:
                tag = tag_match.group(1)
                message = remaining[tag_match.end():]
            
            # Map syslog severity to log level
            level_map = {
                0: LogLevel.FATAL,
                1: LogLevel.ERROR,
                2: LogLevel.ERROR,
                3: LogLevel.ERROR,
                4: LogLevel.WARN,
                5: LogLevel.INFO,
                6: LogLevel.INFO,
                7: LogLevel.DEBUG
            }
            level = level_map.get(severity, LogLevel.INFO)
            
            return LogEntry(
                id=str(uuid.uuid4()),
                timestamp=timestamp,
                level=level,
                message=message,
                source=LogSource.SYSTEM.value,
                service=tag,
                hostname=hostname,
                process_id=None,
                thread_id=None,
                user_id=None,
                session_id=None,
                request_id=None,
                trace_id=None,
                tags={"facility": str(facility), "severity": str(severity)},
                fields={},
                raw_data=log_data
            )
        except Exception as e:
            logging.error(f"Failed to parse syslog: {e}")
            return self._parse_plain_text(log_data)
    
    def _parse_apache(self, log_data: str) -> Optional[LogEntry]:
        """Parse Apache access log format"""
        # Simplified Apache common log format parsing
        try:
            # Common Log Format: host - user [timestamp] "request" status size
            pattern = r'^(\S+) (\S+) (\S+) \[([^\]]+)\] "([^"]*)" (\d+) (\S+)'
            match = re.match(pattern, log_data)
            
            if not match:
                return self._parse_plain_text(log_data)
            
            host, ident, user, timestamp_str, request, status, size = match.groups()
            
            # Parse timestamp
            timestamp = datetime.strptime(timestamp_str, '%d/%b/%Y:%H:%M:%S %z')
            
            # Determine log level based on status code
            status_code = int(status)
            if status_code >= 500:
                level = LogLevel.ERROR
            elif status_code >= 400:
                level = LogLevel.WARN
            else:
                level = LogLevel.INFO
            
            return LogEntry(
                id=str(uuid.uuid4()),
                timestamp=timestamp,
                level=level,
                message=f"{request} - {status} {size}",
                source=LogSource.NETWORK.value,
                service="apache",
                hostname=host,
                process_id=None,
                thread_id=None,
                user_id=user if user != "-" else None,
                session_id=None,
                request_id=None,
                trace_id=None,
                tags={"status_code": str(status_code), "request": request},
                fields={"host": host, "status": status_code, "size": int(size) if size.isdigit() else 0},
                raw_data=log_data
            )
        except Exception as e:
            logging.error(f"Failed to parse Apache log: {e}")
            return self._parse_plain_text(log_data)
    
    def _parse_nginx(self, log_data: str) -> Optional[LogEntry]:
        """Parse Nginx access log format"""
        # Similar to Apache but with different default format
        return self._parse_apache(log_data)  # Simplified for now

class LogAggregator:
    """Log aggregation system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.parser = LogParser()
        
        # Storage
        self.log_entries: deque = deque(maxlen=100000)  # Rolling buffer
        self.log_index: Dict[str, Set[str]] = defaultdict(set)  # Index by field
        self.patterns: Dict[str, LogPattern] = {}
        self.anomalies: List[LogAnomaly] = []
        
        # Processing
        self.processors: List[Callable] = []
        self.filters: List[Callable] = []
        
        # Statistics
        self.stats = {
            "total_logs": 0,
            "logs_by_level": defaultdict(int),
            "logs_by_source": defaultdict(int),
            "logs_by_service": defaultdict(int),
            "patterns_matched": 0,
            "anomalies_detected": 0
        }
        
        # Threading
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def add_log_entry(self, log_data: str, log_format: LogFormat = LogFormat.PLAIN_TEXT) -> Optional[LogEntry]:
        """Add log entry"""
        try:
            # Parse log entry
            log_entry = self.parser.parse(log_data, log_format)
            if not log_entry:
                return None
            
            # Apply filters
            for filter_func in self.filters:
                if not filter_func(log_entry):
                    return None
            
            # Add to storage
            with self.lock:
                self.log_entries.append(log_entry)
                self.stats["total_logs"] += 1
                self.stats["logs_by_level"][log_entry.level.value] += 1
                self.stats["logs_by_source"][log_entry.source] += 1
                self.stats["logs_by_service"][log_entry.service] += 1
                
                # Update indexes
                self._update_indexes(log_entry)
            
            # Apply processors
            for processor in self.processors:
                try:
                    processor(log_entry)
                except Exception as e:
                    self.logger.error(f"Log processor error: {e}")
            
            # Pattern matching
            self._match_patterns(log_entry)
            
            return log_entry
            
        except Exception as e:
            self.logger.error(f"Error adding log entry: {e}")
            return None
    
    def _update_indexes(self, log_entry: LogEntry):
        """Update log indexes"""
        # Service index
        self.log_index[f"service:{log_entry.service}"].add(log_entry.id)
        
        # Level index
        self.log_index[f"level:{log_entry.level.value}"].add(log_entry.id)
        
        # Source index
        self.log_index[f"source:{log_entry.source}"].add(log_entry.id)
        
        # Hostname index
        if log_entry.hostname:
            self.log_index[f"hostname:{log_entry.hostname}"].add(log_entry.id)
        
        # User index
        if log_entry.user_id:
            self.log_index[f"user:{log_entry.user_id}"].add(log_entry.id)
        
        # Trace index
        if log_entry.trace_id:
            self.log_index[f"trace:{log_entry.trace_id}"].add(log_entry.id)
    
    def _match_patterns(self, log_entry: LogEntry):
        """Match log entry against patterns"""
        for pattern in self.patterns.values():
            match_result = pattern.match(log_entry.message)
            if match_result:
                self.stats["patterns_matched"] += 1
                log_entry.tags["pattern_matched"] = pattern.name
                
                # Add extracted fields
                for key, value in match_result.items():
                    if key not in ["matched", "pattern"]:
                        log_entry.fields[key] = value
                
                break  # Stop after first match
    
    def add_pattern(self, pattern: LogPattern):
        """Add log pattern"""
        with self.lock:
            self.patterns[pattern.name] = pattern
    
    def add_processor(self, processor: Callable):
        """Add log processor"""
        self.processors.append(processor)
    
    def add_filter(self, filter_func: Callable):
        """Add log filter"""
        self.filters.append(filter_func)
    
    def query_logs(self, query: Dict[str, Any]) -> List[LogEntry]:
        """Query logs with filters"""
        with self.lock:
            results = []
            
            for log_entry in self.log_entries:
                if self._matches_query(log_entry, query):
                    results.append(log_entry)
            
            # Sort by timestamp (newest first)
            results.sort(key=lambda x: x.timestamp, reverse=True)
            
            return results
    
    def _matches_query(self, log_entry: LogEntry, query: Dict[str, Any]) -> bool:
        """Check if log entry matches query"""
        # Time range
        if "start_time" in query and log_entry.timestamp < query["start_time"]:
            return False
        if "end_time" in query and log_entry.timestamp > query["end_time"]:
            return False
        
        # Level filter
        if "level" in query:
            if isinstance(query["level"], list):
                if log_entry.level.value not in query["level"]:
                    return False
            elif log_entry.level.value != query["level"]:
                return False
        
        # Service filter
        if "service" in query:
            if isinstance(query["service"], list):
                if log_entry.service not in query["service"]:
                    return False
            elif log_entry.service != query["service"]:
                return False
        
        # Source filter
        if "source" in query:
            if isinstance(query["source"], list):
                if log_entry.source not in query["source"]:
                    return False
            elif log_entry.source != query["source"]:
                return False
        
        # Message text search
        if "message_contains" in query:
            if query["message_contains"].lower() not in log_entry.message.lower():
                return False
        
        # Tags filter
        if "tags" in query:
            for key, value in query["tags"].items():
                if log_entry.tags.get(key) != value:
                    return False
        
        # Fields filter
        if "fields" in query:
            for key, value in query["fields"].items():
                if log_entry.fields.get(key) != value:
                    return False
        
        return True
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """Get log statistics"""
        with self.lock:
            return {
                "total_logs": self.stats["total_logs"],
                "logs_by_level": dict(self.stats["logs_by_level"]),
                "logs_by_source": dict(self.stats["logs_by_source"]),
                "logs_by_service": dict(self.stats["logs_by_service"]),
                "patterns_matched": self.stats["patterns_matched"],
                "anomalies_detected": self.stats["anomalies_detected"],
                "buffer_size": len(self.log_entries),
                "unique_services": len(self.log_index["service:"]),
                "unique_sources": len(self.log_index["source:"])
            }
    
    def export_logs(self, format: str = "json", query: Dict[str, Any] = None) -> str:
        """Export logs in specified format"""
        logs = self.query_logs(query or {})
        
        if format.lower() == "json":
            return json.dumps([log.to_dict() for log in logs], indent=2)
        elif format.lower() == "csv":
            # Simple CSV export
            if not logs:
                return ""
            
            headers = ["timestamp", "level", "message", "service", "source", "hostname"]
            rows = []
            
            for log in logs:
                row = [
                    log.timestamp.isoformat(),
                    log.level.value,
                    log.message.replace('\n', ' '),
                    log.service,
                    log.source,
                    log.hostname or ""
                ]
                rows.append(row)
            
            return "\n".join([",".join(headers)] + [",".join(row) for row in rows])
        
        return ""

class LogAnomalyDetector:
    """Log anomaly detection"""
    
    def __init__(self, aggregator: LogAggregator):
        self.aggregator = aggregator
        self.logger = logging.getLogger(__name__)
        
        # Anomaly detection configuration
        self.config = {
            "error_rate_threshold": 0.05,  # 5% error rate
            "spike_threshold": 3.0,  # 3x normal rate
            "unusual_pattern_threshold": 0.1,  # 10% unusual patterns
            "window_minutes": 10,  # Analysis window
            "min_samples": 100  # Minimum samples for analysis
        }
        
        # Baseline statistics
        self.baseline_stats = {}
        self.last_analysis = datetime.now()
    
    def analyze_logs(self) -> List[LogAnomaly]:
        """Analyze logs for anomalies"""
        anomalies = []
        current_time = datetime.now()
        
        # Get logs in analysis window
        window_start = current_time - timedelta(minutes=self.config["window_minutes"])
        
        query = {
            "start_time": window_start,
            "end_time": current_time
        }
        
        recent_logs = self.aggregator.query_logs(query)
        
        if len(recent_logs) < self.config["min_samples"]:
            return anomalies
        
        # Check for error rate spike
        error_anomaly = self._detect_error_rate_spike(recent_logs)
        if error_anomaly:
            anomalies.append(error_anomaly)
        
        # Check for volume spike
        volume_anomaly = self._detect_volume_spike(recent_logs)
        if volume_anomaly:
            anomalies.append(volume_anomaly)
        
        # Check for unusual patterns
        pattern_anomalies = self._detect_unusual_patterns(recent_logs)
        anomalies.extend(pattern_anomalies)
        
        # Store anomalies
        with self.aggregator.lock:
            self.aggregator.anomalies.extend(anomalies)
            self.aggregator.stats["anomalies_detected"] += len(anomalies)
        
        self.last_analysis = current_time
        return anomalies
    
    def _detect_error_rate_spike(self, logs: List[LogEntry]) -> Optional[LogAnomaly]:
        """Detect error rate spike"""
        error_levels = {LogLevel.ERROR.value, LogLevel.FATAL.value}
        error_count = len([log for log in logs if log.level.value in error_levels])
        error_rate = error_count / len(logs)
        
        if error_rate > self.config["error_rate_threshold"]:
            return LogAnomaly(
                id=str(uuid.uuid4()),
                anomaly_type=AnomalyType.SPIKE,
                severity=LogLevel.ERROR,
                confidence=min(error_rate / self.config["error_rate_threshold"], 1.0),
                description=f"Error rate spike detected: {error_rate:.2%}",
                affected_entries=[log.id for log in logs if log.level.value in error_levels],
                detected_at=datetime.now(),
                metadata={
                    "error_rate": error_rate,
                    "threshold": self.config["error_rate_threshold"],
                    "error_count": error_count,
                    "total_count": len(logs)
                }
            )
        
        return None
    
    def _detect_volume_spike(self, logs: List[LogEntry]) -> Optional[LogAnomaly]:
        """Detect volume spike"""
        current_rate = len(logs) / self.config["window_minutes"]
        
        # Calculate baseline rate (simplified - would use historical data)
        baseline_rate = self.baseline_stats.get("log_rate", current_rate * 0.7)
        
        if current_rate > baseline_rate * self.config["spike_threshold"]:
            return LogAnomaly(
                id=str(uuid.uuid4()),
                anomaly_type=AnomalyType.SPIKE,
                severity=LogLevel.WARN,
                confidence=min(current_rate / (baseline_rate * self.config["spike_threshold"]), 1.0),
                description=f"Log volume spike detected: {current_rate:.1f} logs/min",
                affected_entries=[log.id for log in logs],
                detected_at=datetime.now(),
                metadata={
                    "current_rate": current_rate,
                    "baseline_rate": baseline_rate,
                    "threshold": baseline_rate * self.config["spike_threshold"],
                    "spike_factor": current_rate / baseline_rate
                }
            )
        
        # Update baseline
        self.baseline_stats["log_rate"] = (baseline_rate + current_rate) / 2
        
        return None
    
    def _detect_unusual_patterns(self, logs: List[LogEntry]) -> List[LogAnomaly]:
        """Detect unusual patterns in logs"""
        anomalies = []
        
        # Analyze message patterns
        message_patterns = defaultdict(int)
        for log in logs:
            # Simplified pattern extraction (first 50 chars)
            pattern = log.message[:50].lower()
            message_patterns[pattern] += 1
        
        # Find unusual patterns (appear only once or very few times)
        total_logs = len(logs)
        for pattern, count in message_patterns.items():
            pattern_ratio = count / total_logs
            if pattern_ratio < self.config["unusual_pattern_threshold"] and count <= 3:
                affected_logs = [log for log in logs if log.message[:50].lower() == pattern]
                
                anomaly = LogAnomaly(
                    id=str(uuid.uuid4()),
                    anomaly_type=AnomalyType.UNUSUAL_PATTERN,
                    severity=LogLevel.INFO,
                    confidence=1.0 - pattern_ratio,
                    description=f"Unusual pattern detected: '{pattern[:30]}...'",
                    affected_entries=[log.id for log in affected_logs],
                    detected_at=datetime.now(),
                    metadata={
                        "pattern": pattern[:50],
                        "count": count,
                        "ratio": pattern_ratio,
                        "threshold": self.config["unusual_pattern_threshold"]
                    }
                )
                anomalies.append(anomaly)
        
        return anomalies

# Global aggregator instance
_log_aggregator = None

def get_log_aggregator() -> LogAggregator:
    """Get global log aggregator"""
    global _log_aggregator
    if _log_aggregator is None:
        _log_aggregator = LogAggregator()
    return _log_aggregator

def init_log_aggregation():
    """Initialize log aggregation system"""
    aggregator = get_log_aggregator()
    
    # Add default patterns for common error patterns
    patterns = [
        LogPattern(
            name="database_connection_error",
            pattern=re.compile(r'database.*connection.*error', re.IGNORECASE),
            severity=LogLevel.ERROR,
            description="Database connection error",
            sample_messages=["Database connection error: timeout", "Failed to connect to database"]
        ),
        LogPattern(
            name="memory_error",
            pattern=re.compile(r'(out of memory|memory allocation|oom killer)', re.IGNORECASE),
            severity=LogLevel.FATAL,
            description="Memory related error",
            sample_messages=["Out of memory error", "Cannot allocate memory"]
        ),
        LogPattern(
            name="authentication_failure",
            pattern=re.compile(r'(authentication.*failed|login.*failed|unauthorized)', re.IGNORECASE),
            severity=LogLevel.WARN,
            description="Authentication failure",
            sample_messages=["Authentication failed for user", "Login failed: invalid credentials"]
        )
    ]
    
    for pattern in patterns:
        aggregator.add_pattern(pattern)
    
    # Initialize anomaly detector
    anomaly_detector = LogAnomalyDetector(aggregator)
    
    return aggregator, anomaly_detector