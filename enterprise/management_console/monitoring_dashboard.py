"""
Aurora OS System Monitoring and Alerting Dashboard
Real-time system monitoring with intelligent alerting
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import statistics
import threading

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class MetricType(Enum):
    """Metric types"""
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_USAGE = "disk_usage"
    NETWORK_THROUGHPUT = "network_throughput"
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    REQUEST_RATE = "request_rate"
    QUEUE_DEPTH = "queue_depth"

class AlertStatus(Enum):
    """Alert status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"

@dataclass
class Metric:
    """System metric"""
    metric_type: MetricType
    value: float
    unit: str
    timestamp: datetime
    node_id: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['metric_type'] = self.metric_type.value
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class Alert:
    """System alert"""
    id: str
    title: str
    description: str
    severity: AlertSeverity
    status: AlertStatus
    metric_type: MetricType
    threshold: float
    current_value: float
    node_id: str
    created_at: datetime
    updated_at: datetime
    acknowledged_by: Optional[str]
    resolved_at: Optional[datetime]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['severity'] = self.severity.value
        data['status'] = self.status.value
        data['metric_type'] = self.metric_type.value
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        data['resolved_at'] = self.resolved_at.isoformat() if self.resolved_at else None
        return data

@dataclass
class ThresholdRule:
    """Alert threshold rule"""
    id: str
    name: str
    metric_type: MetricType
    severity: AlertSeverity
    threshold_value: float
    comparison_operator: str  # ">", "<", ">=", "<=", "=="
    duration_seconds: int
    enabled: bool
    node_filter: Optional[str]  # Filter for specific nodes
    
    def evaluate(self, metric: Metric) -> bool:
        """Evaluate if metric exceeds threshold"""
        if metric.metric_type != self.metric_type:
            return False
        
        if not self.enabled:
            return False
        
        # Apply node filter if specified
        if self.node_filter and not self._matches_node_filter(metric.node_id):
            return False
        
        # Evaluate comparison
        if self.comparison_operator == ">":
            return metric.value > self.threshold_value
        elif self.comparison_operator == "<":
            return metric.value < self.threshold_value
        elif self.comparison_operator == ">=":
            return metric.value >= self.threshold_value
        elif self.comparison_operator == "<=":
            return metric.value <= self.threshold_value
        elif self.comparison_operator == "==":
            return metric.value == self.threshold_value
        
        return False
    
    def _matches_node_filter(self, node_id: str) -> bool:
        """Check if node matches filter"""
        if not self.node_filter:
            return True
        
        # Simple wildcard matching for now
        import fnmatch
        return fnmatch.fnmatch(node_id, self.node_filter)

class MonitoringDashboard:
    """System monitoring and alerting dashboard"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Metrics storage
        self.metrics_history: Dict[str, List[Metric]] = {}  # node_id -> list of metrics
        self.current_metrics: Dict[str, Dict[MetricType, Metric]] = {}  # node_id -> metric_type -> metric
        
        # Alerts
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.threshold_rules: Dict[str, ThresholdRule] = {}
        
        # Monitoring state
        self.monitoring_active = False
        self.collection_interval = 30  # seconds
        self.retention_period = timedelta(hours=24)
        
        # Callbacks
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        
        # Initialize default threshold rules
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default threshold rules"""
        default_rules = [
            ThresholdRule(
                id="cpu_high",
                name="High CPU Usage",
                metric_type=MetricType.CPU_USAGE,
                severity=AlertSeverity.WARNING,
                threshold_value=80.0,
                comparison_operator=">",
                duration_seconds=300,  # 5 minutes
                enabled=True
            ),
            ThresholdRule(
                id="cpu_critical",
                name="Critical CPU Usage",
                metric_type=MetricType.CPU_USAGE,
                severity=AlertSeverity.CRITICAL,
                threshold_value=95.0,
                comparison_operator=">",
                duration_seconds=60,  # 1 minute
                enabled=True
            ),
            ThresholdRule(
                id="memory_high",
                name="High Memory Usage",
                metric_type=MetricType.MEMORY_USAGE,
                severity=AlertSeverity.WARNING,
                threshold_value=85.0,
                comparison_operator=">",
                duration_seconds=300,
                enabled=True
            ),
            ThresholdRule(
                id="memory_critical",
                name="Critical Memory Usage",
                metric_type=MetricType.MEMORY_USAGE,
                severity=AlertSeverity.CRITICAL,
                threshold_value=95.0,
                comparison_operator=">",
                duration_seconds=60,
                enabled=True
            ),
            ThresholdRule(
                id="disk_high",
                name="High Disk Usage",
                metric_type=MetricType.DISK_USAGE,
                severity=AlertSeverity.WARNING,
                threshold_value=90.0,
                comparison_operator=">",
                duration_seconds=600,  # 10 minutes
                enabled=True
            ),
            ThresholdRule(
                id="error_rate_high",
                name="High Error Rate",
                metric_type=MetricType.ERROR_RATE,
                severity=AlertSeverity.ERROR,
                threshold_value=5.0,  # 5%
                comparison_operator=">",
                duration_seconds=180,  # 3 minutes
                enabled=True
            ),
            ThresholdRule(
                id="response_time_high",
                name="High Response Time",
                metric_type=MetricType.RESPONSE_TIME,
                severity=AlertSeverity.WARNING,
                threshold_value=1000.0,  # 1 second
                comparison_operator=">",
                duration_seconds=300,
                enabled=True
            )
        ]
        
        for rule in default_rules:
            self.threshold_rules[rule.id] = rule
    
    def start_monitoring(self):
        """Start monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.logger.info("Starting system monitoring")
        
        # Start background collection
        asyncio.create_task(self._collect_metrics_loop())
        asyncio.create_task(self._evaluate_alerts_loop())
        asyncio.create_task(self._cleanup_old_data_loop())
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring_active = False
        self.logger.info("Stopping system monitoring")
    
    async def add_metric(self, metric: Metric):
        """Add a new metric"""
        node_id = metric.node_id
        metric_type = metric.metric_type
        
        # Store in current metrics
        if node_id not in self.current_metrics:
            self.current_metrics[node_id] = {}
        self.current_metrics[node_id][metric_type] = metric
        
        # Store in history
        if node_id not in self.metrics_history:
            self.metrics_history[node_id] = []
        self.metrics_history[node_id].append(metric)
        
        # Limit history size
        max_history = 1000
        if len(self.metrics_history[node_id]) > max_history:
            self.metrics_history[node_id] = self.metrics_history[node_id][-max_history:]
    
    async def _collect_metrics_loop(self):
        """Background metrics collection loop"""
        while self.monitoring_active:
            try:
                # Simulate metric collection from nodes
                await self._simulate_metric_collection()
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                self.logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(5)
    
    async def _simulate_metric_collection(self):
        """Simulate metric collection for testing"""
        nodes = ["node-001", "node-002", "node-003"]
        
        for node_id in nodes:
            # Generate random metrics
            cpu_metric = Metric(
                metric_type=MetricType.CPU_USAGE,
                value=min(max(20 + (hash(node_id) % 40) + (time.time() % 20 - 10), 0), 100),
                unit="percent",
                timestamp=datetime.now(),
                node_id=node_id,
                metadata={}
            )
            
            memory_metric = Metric(
                metric_type=MetricType.MEMORY_USAGE,
                value=min(max(50 + (hash(node_id) % 30) + (time.time() % 15 - 7.5), 0), 100),
                unit="percent",
                timestamp=datetime.now(),
                node_id=node_id,
                metadata={}
            )
            
            disk_metric = Metric(
                metric_type=MetricType.DISK_USAGE,
                value=30 + (hash(node_id) % 50),
                unit="percent",
                timestamp=datetime.now(),
                node_id=node_id,
                metadata={}
            )
            
            # Add metrics
            await self.add_metric(cpu_metric)
            await self.add_metric(memory_metric)
            await self.add_metric(disk_metric)
    
    async def _evaluate_alerts_loop(self):
        """Background alert evaluation loop"""
        while self.monitoring_active:
            try:
                await self._evaluate_thresholds()
                await asyncio.sleep(60)  # Evaluate every minute
                
            except Exception as e:
                self.logger.error(f"Error evaluating alerts: {e}")
                await asyncio.sleep(10)
    
    async def _evaluate_thresholds(self):
        """Evaluate all threshold rules against current metrics"""
        for rule in self.threshold_rules.values():
            if not rule.enabled:
                continue
            
            for node_id, node_metrics in self.current_metrics.items():
                if rule.metric_type in node_metrics:
                    metric = node_metrics[rule.metric_type]
                    
                    # Check if threshold is exceeded
                    if rule.evaluate(metric):
                        await self._handle_threshold_exceeded(rule, metric)
                    else:
                        await self._handle_threshold_normal(rule, metric)
    
    async def _handle_threshold_exceeded(self, rule: ThresholdRule, metric: Metric):
        """Handle when threshold is exceeded"""
        alert_id = f"{rule.id}_{metric.node_id}"
        
        # Check if alert already exists
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.current_value = metric.value
            alert.updated_at = datetime.now()
            return
        
        # Create new alert
        alert = Alert(
            id=alert_id,
            title=rule.name,
            description=f"{rule.name} on {metric.node_id}: {metric.value:.1f}{metric.unit} (threshold: {rule.threshold_value}{metric.unit})",
            severity=rule.severity,
            status=AlertStatus.ACTIVE,
            metric_type=rule.metric_type,
            threshold=rule.threshold_value,
            current_value=metric.value,
            node_id=metric.node_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            acknowledged_by=None,
            resolved_at=None,
            metadata={"rule_id": rule.id}
        )
        
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        self.logger.warning(f"Alert created: {alert.title} on {alert.node_id}")
        
        # Trigger callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")
    
    async def _handle_threshold_normal(self, rule: ThresholdRule, metric: Metric):
        """Handle when threshold returns to normal"""
        alert_id = f"{rule.id}_{metric.node_id}"
        
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now()
            alert.updated_at = datetime.now()
            
            # Move from active to history
            del self.active_alerts[alert_id]
            self.alert_history.append(alert)
            
            self.logger.info(f"Alert resolved: {alert.title} on {alert.node_id}")
    
    async def _cleanup_old_data_loop(self):
        """Cleanup old metrics and alerts"""
        while self.monitoring_active:
            try:
                cutoff_time = datetime.now() - self.retention_period
                
                # Cleanup old metrics
                for node_id in list(self.metrics_history.keys()):
                    self.metrics_history[node_id] = [
                        m for m in self.metrics_history[node_id] 
                        if m.timestamp > cutoff_time
                    ]
                    
                    if not self.metrics_history[node_id]:
                        del self.metrics_history[node_id]
                
                # Cleanup old resolved alerts
                self.alert_history = [
                    alert for alert in self.alert_history
                    if alert.status != AlertStatus.RESOLVED or alert.resolved_at > cutoff_time
                ]
                
                await asyncio.sleep(3600)  # Cleanup every hour
                
            except Exception as e:
                self.logger.error(f"Error cleaning up old data: {e}")
                await asyncio.sleep(300)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data for UI"""
        # Calculate summary statistics
        total_nodes = len(self.current_metrics)
        total_alerts = len(self.active_alerts)
        critical_alerts = len([a for a in self.active_alerts.values() if a.severity == AlertSeverity.CRITICAL])
        warning_alerts = len([a for a in self.active_alerts.values() if a.severity == AlertSeverity.WARNING])
        
        # Calculate average metrics
        all_cpu_values = []
        all_memory_values = []
        
        for node_metrics in self.current_metrics.values():
            if MetricType.CPU_USAGE in node_metrics:
                all_cpu_values.append(node_metrics[MetricType.CPU_USAGE].value)
            if MetricType.MEMORY_USAGE in node_metrics:
                all_memory_values.append(node_metrics[MetricType.MEMORY_USAGE].value)
        
        avg_cpu = statistics.mean(all_cpu_values) if all_cpu_values else 0
        avg_memory = statistics.mean(all_memory_values) if all_memory_values else 0
        
        return {
            "summary": {
                "total_nodes": total_nodes,
                "total_alerts": total_alerts,
                "critical_alerts": critical_alerts,
                "warning_alerts": warning_alerts,
                "avg_cpu_usage": round(avg_cpu, 1),
                "avg_memory_usage": round(avg_memory, 1)
            },
            "active_alerts": [alert.to_dict() for alert in self.active_alerts.values()],
            "recent_alerts": [alert.to_dict() for alert in sorted(self.alert_history, key=lambda a: a.created_at, reverse=True)[:10]],
            "metrics": {
                node_id: {
                    metric_type.value: metric.to_dict()
                    for metric_type, metric in node_metrics.items()
                }
                for node_id, node_metrics in self.current_metrics.items()
            },
            "threshold_rules": [rule.to_dict() for rule in self.threshold_rules.values()]
        }
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_by = acknowledged_by
            alert.updated_at = datetime.now()
            
            self.logger.info(f"Alert acknowledged: {alert.title} by {acknowledged_by}")
            return True
        
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Manually resolve an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now()
            alert.updated_at = datetime.now()
            
            # Move from active to history
            del self.active_alerts[alert_id]
            self.alert_history.append(alert)
            
            self.logger.info(f"Alert manually resolved: {alert.title}")
            return True
        
        return False
    
    def add_alert_callback(self, callback: Callable[[Alert], None]):
        """Add alert callback"""
        self.alert_callbacks.append(callback)
    
    def update_threshold_rule(self, rule_id: str, **kwargs) -> bool:
        """Update threshold rule"""
        if rule_id in self.threshold_rules:
            rule = self.threshold_rules[rule_id]
            
            for key, value in kwargs.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)
            
            self.logger.info(f"Updated threshold rule: {rule.name}")
            return True
        
        return False

# Test function
async def test_monitoring_dashboard():
    """Test the monitoring dashboard"""
    dashboard = MonitoringDashboard()
    
    # Add alert callback
    def on_alert(alert):
        print(f"🚨 Alert: {alert.title} - {alert.description}")
    
    dashboard.add_alert_callback(on_alert)
    
    # Start monitoring
    dashboard.start_monitoring()
    
    try:
        # Run for a few minutes to see alerts
        await asyncio.sleep(300)
    finally:
        dashboard.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(test_monitoring_dashboard())