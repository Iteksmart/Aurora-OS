"""
Aurora OS Distributed Tracing System
Advanced distributed tracing for microservices and distributed systems
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import threading
from collections import defaultdict, deque
import struct
import base64

class SpanKind(Enum):
    """Span types"""
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"
    INTERNAL = "internal"

class SpanStatus(Enum):
    """Span status codes"""
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"

@dataclass
class SpanEvent:
    """Span event"""
    timestamp: datetime
    name: str
    attributes: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "attributes": self.attributes
        }

@dataclass
class SpanLink:
    """Link to another span"""
    trace_id: str
    span_id: str
    attributes: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "attributes": self.attributes
        }

@dataclass
class TraceSpan:
    """Distributed trace span"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    kind: SpanKind
    start_time: datetime
    end_time: Optional[datetime]
    status: SpanStatus
    service_name: str
    resource_name: str
    attributes: Dict[str, Any]
    events: List[SpanEvent]
    links: List[SpanLink]
    tags: Set[str]
    
    def __post_init__(self):
        """Post-initialization"""
        if self.events is None:
            self.events = []
        if self.links is None:
            self.links = []
        if self.tags is None:
            self.tags = set()
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Get span duration"""
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Get span duration in milliseconds"""
        if self.duration:
            return self.duration.total_seconds() * 1000
        return None
    
    def add_event(self, name: str, attributes: Dict[str, Any] = None):
        """Add event to span"""
        event = SpanEvent(
            timestamp=datetime.now(),
            name=name,
            attributes=attributes or {}
        )
        self.events.append(event)
    
    def add_link(self, trace_id: str, span_id: str, attributes: Dict[str, Any] = None):
        """Add link to another span"""
        link = SpanLink(
            trace_id=trace_id,
            span_id=span_id,
            attributes=attributes or {}
        )
        self.links.append(link)
    
    def set_attribute(self, key: str, value: Any):
        """Set attribute"""
        self.attributes[key] = value
    
    def set_status(self, status: SpanStatus, message: str = ""):
        """Set span status"""
        self.status = status
        if message:
            self.attributes["status_message"] = message
    
    def finish(self, end_time: Optional[datetime] = None):
        """Finish the span"""
        self.end_time = end_time or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "kind": self.kind.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "service_name": self.service_name,
            "resource_name": self.resource_name,
            "attributes": self.attributes,
            "events": [event.to_dict() for event in self.events],
            "links": [link.to_dict() for link in self.links],
            "tags": list(self.tags)
        }

class TraceContext:
    """Trace context for propagation"""
    
    def __init__(self, trace_id: str, span_id: str, baggage: Dict[str, str] = None):
        self.trace_id = trace_id
        self.span_id = span_id
        self.baggage = baggage or {}
    
    def to_header(self) -> str:
        """Convert to trace header format"""
        header_data = {
            "version": 1,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "baggage": self.baggage
        }
        encoded = base64.b64encode(json.dumps(header_data).encode()).decode()
        return f"aurora-trace-{encoded}"
    
    @classmethod
    def from_header(cls, header: str) -> Optional['TraceContext']:
        """Create from trace header"""
        try:
            if not header.startswith("aurora-trace-"):
                return None
            
            encoded = header[len("aurora-trace-"):]
            decoded = json.loads(base64.b64decode(encoded).decode())
            
            if decoded.get("version") != 1:
                return None
            
            return cls(
                trace_id=decoded["trace_id"],
                span_id=decoded["span_id"],
                baggage=decoded.get("baggage", {})
            )
        except Exception:
            return None

class DistributedTracer:
    """Distributed tracing system"""
    
    def __init__(self, service_name: str):
        self.logger = logging.getLogger(__name__)
        self.service_name = service_name
        
        # Active spans
        self.active_spans: Dict[str, TraceSpan] = {}
        
        # Completed spans storage
        self.spans_buffer: deque = deque(maxlen=10000)  # Ring buffer
        self.trace_storage: Dict[str, List[TraceSpan]] = defaultdict(list)
        
        # Configuration
        self.sampling_rate = 1.0  # 100% sampling by default
        self.max_attributes = 100
        self.max_events = 100
        self.max_links = 100
        
        # Statistics
        self.stats = {
            "spans_created": 0,
            "spans_completed": 0,
            "spans_dropped": 0,
            "traces_collected": 0
        }
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        # Background processing
        self._running = False
        self._background_task = None
    
    def start_span(self, operation_name: str, parent_span: Optional[TraceSpan] = None,
                  kind: SpanKind = SpanKind.INTERNAL, resource_name: str = None,
                  attributes: Dict[str, Any] = None) -> TraceSpan:
        """Start a new span"""
        with self._lock:
            try:
                # Generate IDs
                if parent_span:
                    trace_id = parent_span.trace_id
                    parent_span_id = parent_span.span_id
                else:
                    trace_id = self._generate_trace_id()
                    parent_span_id = None
                
                span_id = self._generate_span_id()
                
                # Create span
                span = TraceSpan(
                    trace_id=trace_id,
                    span_id=span_id,
                    parent_span_id=parent_span_id,
                    operation_name=operation_name,
                    kind=kind,
                    start_time=datetime.now(),
                    end_time=None,
                    status=SpanStatus.OK,
                    service_name=self.service_name,
                    resource_name=resource_name or operation_name,
                    attributes=attributes or {},
                    events=[],
                    links=[],
                    tags=set()
                )
                
                # Add service and trace attributes
                span.set_attribute("service.name", self.service_name)
                span.set_attribute("service.version", "0.1.0")
                span.set_attribute("trace.sampling_rate", self.sampling_rate)
                
                # Store active span
                self.active_spans[span_id] = span
                self.stats["spans_created"] += 1
                
                self.logger.debug(f"Started span: {operation_name} ({span_id})")
                return span
                
            except Exception as e:
                self.logger.error(f"Error starting span: {e}")
                self.stats["spans_dropped"] += 1
                raise
    
    def finish_span(self, span: TraceSpan, end_time: Optional[datetime] = None, 
                   status: SpanStatus = None):
        """Finish a span"""
        with self._lock:
            try:
                if span.span_id not in self.active_spans:
                    self.logger.warning(f"Span not found in active spans: {span.span_id}")
                    return
                
                # Finish the span
                span.finish(end_time)
                if status:
                    span.set_status(status)
                
                # Move from active to completed
                del self.active_spans[span.span_id]
                
                # Store in buffer and trace storage
                self.spans_buffer.append(span)
                self.trace_storage[span.trace_id].append(span)
                
                self.stats["spans_completed"] += 1
                
                self.logger.debug(f"Finished span: {span.operation_name} ({span.span_id}) in {span.duration_ms:.2f}ms")
                
            except Exception as e:
                self.logger.error(f"Error finishing span: {e}")
                self.stats["spans_dropped"] += 1
    
    def get_span(self, span_id: str) -> Optional[TraceSpan]:
        """Get active span by ID"""
        return self.active_spans.get(span_id)
    
    def get_trace(self, trace_id: str) -> List[TraceSpan]:
        """Get all spans for a trace"""
        return self.trace_storage.get(trace_id, [])
    
    def create_context(self, span: TraceSpan) -> TraceContext:
        """Create trace context from span"""
        baggage = {k: str(v) for k, v in span.attributes.items() if isinstance(v, (str, int, float, bool))}
        return TraceContext(span.trace_id, span.span_id, baggage)
    
    def extract_context(self, headers: Dict[str, str]) -> Optional[TraceContext]:
        """Extract trace context from headers"""
        # Check common trace header names
        header_names = ["x-trace-id", "traceparent", "aurora-trace", "x-aurora-trace"]
        
        for header_name in header_names:
            if header_name in headers:
                context = TraceContext.from_header(headers[header_name])
                if context:
                    return context
        
        return None
    
    def inject_context(self, context: TraceContext, headers: Dict[str, str]):
        """Inject trace context into headers"""
        headers["x-aurora-trace"] = context.to_header()
    
    def start_span_from_context(self, operation_name: str, context: TraceContext,
                              kind: SpanKind = SpanKind.INTERNAL,
                              resource_name: str = None) -> TraceSpan:
        """Start span from existing context"""
        span = self.start_span(
            operation_name=operation_name,
            parent_span=None,  # We'll set parent manually
            kind=kind,
            resource_name=resource_name
        )
        
        # Set trace context
        span.trace_id = context.trace_id
        span.parent_span_id = context.span_id
        
        # Add baggage as attributes
        for key, value in context.baggage.items():
            span.set_attribute(f"baggage.{key}", value)
        
        return span
    
    def get_active_spans(self) -> List[TraceSpan]:
        """Get all active spans"""
        return list(self.active_spans.values())
    
    def get_recent_spans(self, limit: int = 100) -> List[TraceSpan]:
        """Get recent completed spans"""
        return list(self.spans_buffer)[-limit:]
    
    def get_trace_statistics(self, trace_id: str) -> Dict[str, Any]:
        """Get statistics for a specific trace"""
        spans = self.get_trace(trace_id)
        if not spans:
            return {}
        
        durations = [span.duration_ms for span in spans if span.duration_ms]
        
        return {
            "trace_id": trace_id,
            "span_count": len(spans),
            "service_count": len(set(span.service_name for span in spans)),
            "duration_ms": max(durations) if durations else 0,
            "error_count": len([s for s in spans if s.status == SpanStatus.ERROR]),
            "span_kinds": dict(Counter(span.kind.value for span in spans))
        }
    
    def get_service_statistics(self, service_name: str = None) -> Dict[str, Any]:
        """Get statistics for a service"""
        spans = list(self.spans_buffer)
        
        if service_name:
            spans = [s for s in spans if s.service_name == service_name]
        
        if not spans:
            return {}
        
        durations = [span.duration_ms for span in spans if span.duration_ms]
        error_spans = [s for s in spans if s.status == SpanStatus.ERROR]
        
        return {
            "service_name": service_name or self.service_name,
            "span_count": len(spans),
            "error_rate": len(error_spans) / len(spans) if spans else 0,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "max_duration_ms": max(durations) if durations else 0,
            "min_duration_ms": min(durations) if durations else 0,
            "p95_duration_ms": self._percentile(durations, 95) if durations else 0,
            "p99_duration_ms": self._percentile(durations, 99) if durations else 0
        }
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def _generate_trace_id(self) -> str:
        """Generate trace ID"""
        return str(uuid.uuid4()).replace("-", "")
    
    def _generate_span_id(self) -> str:
        """Generate span ID"""
        return str(uuid.uuid4()).replace("-", "")[:16]
    
    def start_background_processing(self):
        """Start background processing tasks"""
        if self._running:
            return
        
        self._running = True
        self._background_task = asyncio.create_task(self._background_processing_loop())
    
    def stop_background_processing(self):
        """Stop background processing tasks"""
        self._running = False
        if self._background_task:
            self._background_task.cancel()
    
    async def _background_processing_loop(self):
        """Background processing loop"""
        while self._running:
            try:
                # Cleanup old traces
                await self._cleanup_old_traces()
                
                # Update statistics
                self.stats["traces_collected"] = len(self.trace_storage)
                
                await asyncio.sleep(60)  # Process every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in background processing: {e}")
                await asyncio.sleep(10)
    
    async def _cleanup_old_traces(self, max_age_hours: int = 24):
        """Cleanup old traces"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        # Clean up trace storage
        traces_to_remove = []
        for trace_id, spans in self.trace_storage.items():
            # Check if all spans are old
            if all(span.start_time < cutoff_time for span in spans):
                traces_to_remove.append(trace_id)
        
        for trace_id in traces_to_remove:
            del self.trace_storage[trace_id]
        
        self.logger.debug(f"Cleaned up {len(traces_to_remove)} old traces")

# Context manager for automatic span management
class SpanContext:
    """Context manager for automatic span lifecycle"""
    
    def __init__(self, tracer: DistributedTracer, operation_name: str,
                 parent_span: Optional[TraceSpan] = None, kind: SpanKind = SpanKind.INTERNAL,
                 resource_name: str = None, attributes: Dict[str, Any] = None):
        self.tracer = tracer
        self.operation_name = operation_name
        self.parent_span = parent_span
        self.kind = kind
        self.resource_name = resource_name
        self.attributes = attributes
        self.span: Optional[TraceSpan] = None
    
    def __enter__(self) -> TraceSpan:
        """Enter context"""
        self.span = self.tracer.start_span(
            operation_name=self.operation_name,
            parent_span=self.parent_span,
            kind=self.kind,
            resource_name=self.resource_name,
            attributes=self.attributes
        )
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context"""
        if self.span:
            if exc_type:
                self.span.set_status(SpanStatus.ERROR, str(exc_val))
                self.span.add_event("exception", {
                    "exception.type": exc_type.__name__,
                    "exception.message": str(exc_val)
                })
            
            self.tracer.finish_span(self.span)

# Global tracer instance
_global_tracer: Optional[DistributedTracer] = None

def get_tracer(service_name: str = None) -> DistributedTracer:
    """Get global tracer instance"""
    global _global_tracer
    
    if _global_tracer is None and service_name:
        _global_tracer = DistributedTracer(service_name)
    
    return _global_tracer or DistributedTracer("default")

def trace(operation_name: str, kind: SpanKind = SpanKind.INTERNAL,
          resource_name: str = None, attributes: Dict[str, Any] = None):
    """Decorator for automatic function tracing"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            
            with SpanContext(tracer, operation_name or func.__name__,
                           kind=kind, resource_name=resource_name,
                           attributes=attributes):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

# Helper function
from collections import Counter

# Test function
async def test_distributed_tracing():
    """Test distributed tracing functionality"""
    tracer = DistributedTracer("test-service")
    
    # Start a root span
    with SpanContext(tracer, "root-operation", kind=SpanKind.SERVER) as root_span:
        root_span.set_attribute("user.id", "user123")
        root_span.add_event("request_started")
        
        # Start child spans
        with SpanContext(tracer, "database-query", parent_span=root_span,
                       kind=SpanKind.CLIENT, resource_name="database") as db_span:
            db_span.set_attribute("db.statement", "SELECT * FROM users")
            db_span.set_attribute("db.type", "postgresql")
            await asyncio.sleep(0.01)  # Simulate work
        
        with SpanContext(tracer, "api-call", parent_span=root_span,
                       kind=SpanKind.CLIENT, resource_name="external-api") as api_span:
            api_span.set_attribute("http.method", "POST")
            api_span.set_attribute("http.url", "https://api.example.com/users")
            await asyncio.sleep(0.02)  # Simulate work
        
        root_span.add_event("request_completed")
    
    # Check results
    spans = tracer.get_recent_spans()
    print(f"Created {len(spans)} spans")
    
    for span in spans:
        print(f"Span: {span.operation_name} ({span.duration_ms:.2f}ms)")
    
    # Get trace
    if spans:
        trace = tracer.get_trace(spans[0].trace_id)
        print(f"Trace has {len(trace)} spans")
        
        # Get statistics
        stats = tracer.get_trace_statistics(spans[0].trace_id)
        print(f"Trace stats: {stats}")

if __name__ == "__main__":
    asyncio.run(test_distributed_tracing())