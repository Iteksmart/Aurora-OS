"""
Test suite for Aurora OS Advanced Monitoring & Observability
"""

import asyncio
import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from enterprise.monitoring.distributed_tracing import (
    DistributedTracer, TraceSpan, SpanKind, SpanStatus, TraceContext,
    init_tracing, get_global_tracer, trace_span
)
from enterprise.monitoring.metrics_collection import (
    MetricsRegistry, CounterMetric, GaugeMetric, HistogramMetric, 
    MetricType, MetricUnit, get_global_registry, init_system_metrics
)
from enterprise.monitoring.log_aggregation import (
    LogAggregator, LogEntry, LogLevel, LogFormat, LogSource, LogPattern,
    LogAnomalyDetector, get_log_aggregator, init_log_aggregation
)

class TestDistributedTracing:
    """Test distributed tracing system"""
    
    def test_tracer_initialization(self):
        """Test tracer initialization"""
        tracer = DistributedTracer("test-service")
        
        assert tracer.service_name == "test-service"
        assert tracer.active_spans == {}
        assert tracer.span_processors == []
        assert tracer.metrics["spans_started"] == 0
    
    def test_span_lifecycle(self):
        """Test span creation and lifecycle"""
        tracer = DistributedTracer("test-service")
        
        # Start span
        span = tracer.start_span("test-operation", SpanKind.SERVER)
        
        assert span.operation_name == "test-operation"
        assert span.kind == SpanKind.SERVER
        assert span.start_time is not None
        assert span.end_time is None
        assert span.status == SpanStatus.UNSET
        
        assert span.span_id in tracer.active_spans
        assert tracer.metrics["spans_started"] == 1
        
        # End span
        tracer.end_span(span)
        
        assert span.end_time is not None
        assert span.duration_ms is not None
        assert span.span_id not in tracer.active_spans
        assert tracer.metrics["spans_ended"] == 1
    
    def test_trace_context_propagation(self):
        """Test trace context propagation"""
        tracer = DistributedTracer("test-service")
        
        # Create parent span
        parent_span = tracer.start_span("parent-operation", SpanKind.SERVER)
        
        # Create trace context
        context = tracer.get_trace_context(parent_span)
        
        assert context.trace_id == parent_span.trace_id
        assert context.span_id == parent_span.span_id
        
        # Start child span from context
        child_span = tracer.start_span("child-operation", SpanKind.CLIENT, context)
        
        assert child_span.trace_id == parent_span.trace_id
        assert child_span.parent_span_id == parent_span.span_id
        
        tracer.end_span(child_span)
        tracer.end_span(parent_span)
    
    def test_w3c_trace_headers(self):
        """Test W3C trace context headers"""
        context = TraceContext("trace123", "span456", TraceFlags.SAMPLED)
        headers = context.to_w3c_headers()
        
        assert "traceparent" in headers
        assert headers["traceparent"].startswith("00-trace123-span456-01")
        
        # Test round-trip
        restored_context = TraceContext.from_w3c_headers(headers)
        assert restored_context is not None
        assert restored_context.trace_id == context.trace_id
        assert restored_context.span_id == context.span_id
        assert TraceFlags.is_sampled(restored_context.trace_flags)
    
    def test_span_events_and_links(self):
        """Test span events and links"""
        tracer = DistributedTracer("test-service")
        
        span = tracer.start_span("test-operation")
        
        # Add event
        span.add_event("custom-event", {"key": "value"})
        assert len(span.events) == 1
        assert span.events[0].name == "custom-event"
        assert span.events[0].attributes["key"] == "value"
        
        # Add link
        span.add_link("other-trace-id", "other-span-id", {"link-key": "link-value"})
        assert len(span.links) == 1
        assert span.links[0].trace_id == "other-trace-id"
        assert span.links[0].span_id == "other-span-id"
        
        tracer.end_span(span)
    
    def test_span_serialization(self):
        """Test span serialization"""
        tracer = DistributedTracer("test-service")
        
        span = tracer.start_span("test-operation", SpanKind.SERVER)
        span.add_event("test-event")
        span.set_status(SpanStatus.OK, "Test complete")
        tracer.end_span(span)
        
        # Test serialization
        span_dict = span.to_dict()
        
        assert span_dict["trace_id"] == span.trace_id
        assert span_dict["span_id"] == span.span_id
        assert span_dict["operation_name"] == "test-operation"
        assert span_dict["kind"] == SpanKind.SERVER.value
        assert span_dict["status"] == SpanStatus.OK.value
        assert span_dict["duration_ms"] is not None
        assert len(span_dict["events"]) == 1
    
    def test_tracer_decorator(self):
        """Test tracing decorator"""
        tracer = init_tracing("decorator-test")
        
        @trace_span("decorated-operation", SpanKind.INTERNAL)
        def test_function(x, y):
            return x + y
        
        result = test_function(2, 3)
        assert result == 5
        
        metrics = tracer.get_metrics()
        assert metrics["spans_started"] == 1
        assert metrics["spans_ended"] == 1

class TestMetricsCollection:
    """Test metrics collection system"""
    
    def test_registry_initialization(self):
        """Test metrics registry initialization"""
        registry = MetricsRegistry()
        
        assert registry.metrics == {}
        assert len(registry.metrics) == 0
    
    def test_counter_metric(self):
        """Test counter metric"""
        registry = MetricsRegistry()
        
        counter = registry.register_counter("test_counter", "Test counter", MetricUnit.COUNT)
        
        assert isinstance(counter, CounterMetric)
        assert counter.name == "test_counter"
        assert counter.metric_type == MetricType.COUNTER
        assert counter.value == 0
        
        # Increment counter
        counter.inc()
        assert counter.value == 1
        
        counter.inc(5)
        assert counter.value == 6
        
        # Get metric from registry
        retrieved = registry.get_metric("test_counter")
        assert retrieved is counter
    
    def test_gauge_metric(self):
        """Test gauge metric"""
        registry = MetricsRegistry()
        
        gauge = registry.register_gauge("test_gauge", "Test gauge", MetricUnit.PERCENT)
        
        assert isinstance(gauge, GaugeMetric)
        assert gauge.value == 0
        
        # Set gauge value
        gauge.set(75.5)
        assert gauge.value == 75.5
        
        # Increment and decrement
        gauge.inc(10)
        assert gauge.value == 85.5
        
        gauge.dec(5.5)
        assert gauge.value == 80.0
    
    def test_histogram_metric(self):
        """Test histogram metric"""
        registry = MetricsRegistry()
        
        histogram = registry.register_histogram("test_histogram", "Test histogram", [1.0, 5.0, 10.0])
        
        assert isinstance(histogram, HistogramMetric)
        assert histogram.count == 0
        assert histogram.sum == 0
        
        # Observe values
        histogram.observe(0.5)
        histogram.observe(2.0)
        histogram.observe(7.0)
        histogram.observe(15.0)
        
        assert histogram.count == 4
        assert histogram.sum == 24.5
        assert histogram.get_average() == 6.125
        
        # Check bucket counts
        bucket_counts = histogram.get_bucket_counts()
        assert bucket_counts["le_1.0"] == 1
        assert bucket_counts["le_5.0"] == 2
        assert bucket_counts["le_10.0"] == 3
        assert bucket_counts["le_+Inf"] == 4
    
    def test_prometheus_format(self):
        """Test Prometheus format export"""
        registry = MetricsRegistry()
        
        counter = registry.register_counter("test_counter", "Test counter")
        counter.inc(5)
        
        gauge = registry.register_gauge("test_gauge", "Test gauge")
        gauge.set(42)
        
        histogram = registry.register_histogram("test_histogram", "Test histogram")
        histogram.observe(1.0)
        histogram.observe(2.0)
        
        prometheus_output = registry.to_prometheus_format()
        
        assert "# HELP test_counter Test counter" in prometheus_output
        assert "# TYPE test_counter counter" in prometheus_output
        assert "test_counter 5" in prometheus_output
        
        assert "# HELP test_gauge Test gauge" in prometheus_output
        assert "# TYPE test_gauge gauge" in prometheus_output
        assert "test_gauge 42" in prometheus_output
        
        assert "# HELP test_histogram Test histogram" in prometheus_output
        assert "# TYPE test_histogram histogram" in prometheus_output
        assert "test_histogram_count 2" in prometheus_output
        assert "test_histogram_sum 3" in prometheus_output
    
    def test_json_format(self):
        """Test JSON format export"""
        registry = MetricsRegistry()
        
        counter = registry.register_counter("test_counter", "Test counter")
        counter.inc(5)
        
        json_output = registry.to_json_format()
        data = json.loads(json_output)
        
        assert "test_counter" in data
        assert data["test_counter"]["type"] == "counter"
        assert data["test_counter"]["value"] == 5

class TestLogAggregation:
    """Test log aggregation system"""
    
    def test_aggregator_initialization(self):
        """Test log aggregator initialization"""
        aggregator = LogAggregator()
        
        assert aggregator.log_entries == deque()
        assert aggregator.log_index == defaultdict(set)
        assert aggregator.patterns == {}
        assert aggregator.stats["total_logs"] == 0
    
    def test_log_entry_creation(self):
        """Test log entry creation"""
        entry = LogEntry(
            id="test-id",
            timestamp=datetime.now(),
            level=LogLevel.ERROR,
            message="Test error message",
            source="test-service",
            service="test-app",
            hostname="test-host",
            process_id=1234,
            thread_id="thread-1",
            user_id="user-123",
            session_id="session-456",
            request_id="request-789",
            trace_id="trace-abc",
            tags={"env": "test"},
            fields={"field1": "value1"},
            raw_data='{"level": "error", "message": "Test error message"}'
        )
        
        assert entry.id == "test-id"
        assert entry.level == LogLevel.ERROR
        assert entry.message == "Test error message"
        assert entry.source == "test-service"
        assert entry.service == "test-app"
        assert entry.hostname == "test-host"
        assert entry.process_id == 1234
        assert entry.thread_id == "thread-1"
        assert entry.user_id == "user-123"
        assert entry.session_id == "session-456"
        assert entry.request_id == "request-789"
        assert entry.trace_id == "trace-abc"
        assert entry.tags["env"] == "test"
        assert entry.fields["field1"] == "value1"
    
    def test_json_log_parsing(self):
        """Test JSON log parsing"""
        aggregator = LogAggregator()
        
        log_data = json.dumps({
            "timestamp": "2024-01-01T12:00:00",
            "level": "error",
            "message": "Database connection failed",
            "service": "api-server",
            "hostname": "server-01",
            "user_id": "user-123"
        })
        
        entry = aggregator.add_log_entry(log_data, LogFormat.JSON)
        
        assert entry is not None
        assert entry.level == LogLevel.ERROR
        assert entry.message == "Database connection failed"
        assert entry.service == "api-server"
        assert entry.hostname == "server-01"
        assert entry.user_id == "user-123"
        assert aggregator.stats["total_logs"] == 1
        assert aggregator.stats["logs_by_level"]["error"] == 1
    
    def test_plain_text_log_parsing(self):
        """Test plain text log parsing"""
        aggregator = LogAggregator()
        
        log_data = "2024-01-01T12:00:00 INFO [api-server] Database connection established"
        
        entry = aggregator.add_log_entry(log_data, LogFormat.PLAIN_TEXT)
        
        assert entry is not None
        assert entry.level == LogLevel.INFO
        assert "Database connection established" in entry.message
        assert entry.service == "api-server"
        assert aggregator.stats["total_logs"] == 1
    
    def test_log_patterns(self):
        """Test log pattern matching"""
        aggregator = LogAggregator()
        
        # Add error pattern
        error_pattern = LogPattern(
            name="database_error",
            pattern=re.compile(r'database.*error', re.IGNORECASE),
            severity=LogLevel.ERROR,
            description="Database error pattern",
            sample_messages=["Database connection error", "Database query error"]
        )
        aggregator.add_pattern(error_pattern)
        
        # Test matching log
        log_data = "2024-01-01T12:00:00 ERROR Database connection error: timeout"
        entry = aggregator.add_log_entry(log_data, LogFormat.PLAIN_TEXT)
        
        assert entry is not None
        assert "pattern_matched" in entry.tags
        assert entry.tags["pattern_matched"] == "database_error"
        assert aggregator.stats["patterns_matched"] == 1
    
    def test_log_querying(self):
        """Test log querying"""
        aggregator = LogAggregator()
        
        # Add test logs
        logs = [
            "2024-01-01T12:00:00 INFO Service started",
            "2024-01-01T12:01:00 ERROR Database connection failed",
            "2024-01-01T12:02:00 WARN High memory usage",
            "2024-01-01T12:03:00 INFO User logged in",
            "2024-01-01T12:04:00 ERROR Invalid user credentials"
        ]
        
        for log in logs:
            aggregator.add_log_entry(log, LogFormat.PLAIN_TEXT)
        
        # Query by level
        error_logs = aggregator.query_logs({"level": ["error"]})
        assert len(error_logs) == 2
        
        # Query by message content
        database_logs = aggregator.query_logs({"message_contains": "database"})
        assert len(database_logs) == 1
        
        # Query by time range
        start_time = datetime(2024, 1, 1, 12, 1, 0)
        end_time = datetime(2024, 1, 1, 12, 3, 0)
        time_range_logs = aggregator.query_logs({
            "start_time": start_time,
            "end_time": end_time
        })
        assert len(time_range_logs) == 2
    
    def test_log_anomaly_detection(self):
        """Test log anomaly detection"""
        aggregator = LogAggregator()
        detector = LogAnomalyDetector(aggregator)
        
        # Add normal logs
        for i in range(100):
            log_data = f"2024-01-01T12:00:{i:02d} INFO Normal operation {i}"
            aggregator.add_log_entry(log_data, LogFormat.PLAIN_TEXT)
        
        # Add error spike
        for i in range(10):
            log_data = f"2024-01-01T12:01:{i:02d} ERROR Critical error {i}"
            aggregator.add_log_entry(log_data, LogFormat.PLAIN_TEXT)
        
        # Detect anomalies
        anomalies = detector.analyze_logs()
        
        assert len(anomalies) > 0
        error_anomalies = [a for a in anomalies if a.anomaly_type.value == "spike"]
        assert len(error_anomalies) > 0

class TestIntegratedMonitoring:
    """Test integrated monitoring components"""
    
    def test_global_instances(self):
        """Test global instance management"""
        # Test global tracer
        tracer = get_global_tracer()
        assert tracer is not None
        assert tracer.service_name == "aurora-os"
        
        # Test global metrics registry
        registry = get_global_registry()
        assert registry is not None
        
        # Test global log aggregator
        log_aggregator = get_log_aggregator()
        assert log_aggregator is not None
    
    def test_monitoring_initialization(self):
        """Test monitoring system initialization"""
        # Initialize tracing
        tracer = init_tracing("test-service")
        assert tracer is not None
        
        # Initialize metrics
        registry = get_global_registry()
        assert registry is not None
        
        # Initialize log aggregation
        aggregator, detector = init_log_aggregation()
        assert aggregator is not None
        assert detector is not None
    
    def test_end_to_end_monitoring(self):
        """Test end-to-end monitoring workflow"""
        # Initialize all components
        tracer = init_tracing("e2e-test")
        registry = get_global_registry()
        aggregator, detector = init_log_aggregation()
        
        # Create a counter metric
        counter = registry.register_counter("operations_total", "Total operations")
        
        # Start a trace
        with tracer.start_span("test-operation", SpanKind.SERVER) as span:
            span.set_attribute("operation.type", "test")
            
            # Record metrics
            counter.inc()
            
            # Log an entry
            log_entry = aggregator.add_log_entry(
                json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "level": "info",
                    "message": "Operation completed successfully",
                    "service": "test-service"
                }),
                LogFormat.JSON
            )
            
            assert log_entry is not None
            
            span.set_status(SpanStatus.OK)
        
        # Verify all components recorded data
        metrics = tracer.get_metrics()
        assert metrics["spans_started"] == 1
        assert metrics["spans_ended"] == 1
        
        assert counter.get_value() == 1
        
        assert aggregator.stats["total_logs"] == 1

# Test runner
def run_advanced_monitoring_tests():
    """Run all advanced monitoring tests"""
    print("🔍 Running Advanced Monitoring & Observability Tests")
    print("=" * 60)
    
    tests = [
        ("Distributed Tracing", TestDistributedTracing),
        ("Metrics Collection", TestMetricsCollection),
        ("Log Aggregation", TestLogAggregation),
        ("Integrated Monitoring", TestIntegratedMonitoring),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_class in tests:
        try:
            print(f"  📋 {test_name}... ", end="")
            
            # Run test methods
            test_instance = test_class()
            test_methods = [method for method in dir(test_instance) if method.startswith('test_')]
            
            for test_method in test_methods:
                getattr(test_instance, test_method)()
            
            print("✅ PASSED")
            passed += 1
            
        except Exception as e:
            print(f"❌ FAILED: {e}")
            failed += 1
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    run_advanced_monitoring_tests()