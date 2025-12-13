"""
Aurora OS Anomaly Detection and Alerting System
Intelligent anomaly detection with machine learning and alerting
"""

import asyncio
import json
import logging
import time
import uuid
import numpy as np
from typing import Dict, List, Optional, Any, Set, Tuple, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor

class AnomalyType(Enum):
    """Anomaly types"""
    STATISTICAL = "statistical"
    BEHAVIORAL = "behavioral"
    PERFORMANCE = "performance"
    SECURITY = "security"
    SYSTEM = "system"
    NETWORK = "network"
    APPLICATION = "application"

class AnomalySeverity(Enum):
    """Anomaly severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertStatus(Enum):
    """Alert status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"

class DetectionMethod(Enum):
    """Detection methods"""
    STATISTICAL = "statistical"
    THRESHOLD = "threshold"
    PATTERN = "pattern"
    ML_MODEL = "ml_model"
    BASELINE_COMPARISON = "baseline_comparison"
    RATE_ANALYSIS = "rate_analysis"

@dataclass
class Anomaly:
    """Anomaly detection result"""
    id: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    confidence: float
    title: str
    description: str
    detected_at: datetime
    source: str
    metric_name: str
    metric_value: float
    expected_value: float
    deviation: float
    detection_method: DetectionMethod
    context: Dict[str, Any]
    affected_entities: List[str]
    tags: Set[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "anomaly_type": self.anomaly_type.value,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "title": self.title,
            "description": self.description,
            "detected_at": self.detected_at.isoformat(),
            "source": self.source,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "expected_value": self.expected_value,
            "deviation": self.deviation,
            "detection_method": self.detection_method.value,
            "context": self.context,
            "affected_entities": self.affected_entities,
            "tags": list(self.tags)
        }

@dataclass
class Alert:
    """Alert notification"""
    id: str
    anomaly_id: str
    severity: AnomalySeverity
    status: AlertStatus
    title: str
    message: str
    created_at: datetime
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    acknowledged_by: Optional[str]
    resolved_by: Optional[str]
    escalation_level: int
    notification_channels: List[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "anomaly_id": self.anomaly_id,
            "severity": self.severity.value,
            "status": self.status.value,
            "title": self.title,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "acknowledged_by": self.acknowledged_by,
            "resolved_by": self.resolved_by,
            "escalation_level": self.escalation_level,
            "notification_channels": self.notification_channels,
            "metadata": self.metadata
        }

@dataclass
class AnomalyDetectorConfig:
    """Anomaly detector configuration"""
    name: str
    anomaly_type: AnomalyType
    detection_method: DetectionMethod
    metric_patterns: List[str]
    severity_threshold: float
    confidence_threshold: float
    window_size_minutes: int
    min_data_points: int
    sensitivity: float  # 0.0 to 1.0
    enabled: bool
    tags: Set[str]
    context_filters: Dict[str, Any]

class StatisticalDetector:
    """Statistical anomaly detection"""
    
    def __init__(self, window_size: int = 100, sensitivity: float = 2.0):
        self.window_size = window_size
        self.sensitivity = sensitivity  # Number of standard deviations
        self.data_points: deque = deque(maxlen=window_size)
    
    def add_data_point(self, value: float, timestamp: datetime = None):
        """Add data point for analysis"""
        self.data_points.append((value, timestamp or datetime.now()))
    
    def detect_anomaly(self, value: float) -> Tuple[bool, float, float]:
        """Detect if value is anomalous"""
        if len(self.data_points) < self.window_size // 2:
            return False, 0.0, 0.0  # Not enough data
        
        values = [point[0] for point in self.data_points]
        mean = statistics.mean(values)
        std_dev = statistics.stdev(values) if len(values) > 1 else 0.0
        
        if std_dev == 0:
            return False, 0.0, mean
        
        z_score = abs(value - mean) / std_dev
        is_anomaly = z_score > self.sensitivity
        confidence = min(z_score / self.sensitivity, 1.0)
        
        return is_anomaly, confidence, mean

class ThresholdDetector:
    """Threshold-based anomaly detection"""
    
    def __init__(self, upper_threshold: float = None, lower_threshold: float = None):
        self.upper_threshold = upper_threshold
        self.lower_threshold = lower_threshold
    
    def detect_anomaly(self, value: float) -> Tuple[bool, float, float]:
        """Detect if value exceeds thresholds"""
        is_anomaly = False
        confidence = 0.0
        expected = 0.0
        
        if self.upper_threshold is not None and value > self.upper_threshold:
            is_anomaly = True
            confidence = min((value - self.upper_threshold) / self.upper_threshold, 1.0)
            expected = self.upper_threshold
        elif self.lower_threshold is not None and value < self.lower_threshold:
            is_anomaly = True
            confidence = min((self.lower_threshold - value) / self.lower_threshold, 1.0)
            expected = self.lower_threshold
        
        return is_anomaly, confidence, expected

class RateChangeDetector:
    """Rate change anomaly detection"""
    
    def __init__(self, window_minutes: int = 5, rate_threshold: float = 2.0):
        self.window_minutes = window_minutes
        self.rate_threshold = rate_threshold
        self.data_points: deque = deque(maxlen=1000)
    
    def add_data_point(self, value: float, timestamp: datetime = None):
        """Add data point"""
        self.data_points.append((value, timestamp or datetime.now()))
    
    def detect_anomaly(self, value: float, current_time: datetime = None) -> Tuple[bool, float, float]:
        """Detect rate change anomaly"""
        current_time = current_time or datetime.now()
        window_start = current_time - timedelta(minutes=self.window_minutes)
        
        # Get recent data points
        recent_points = [(v, t) for v, t in self.data_points if t >= window_start]
        
        if len(recent_points) < 2:
            return False, 0.0, 0.0
        
        # Calculate rate of change
        recent_values = [v for v, t in recent_points]
        recent_mean = statistics.mean(recent_values)
        
        # Calculate historical baseline
        all_points = [(v, t) for v, t in self.data_points if t < window_start]
        if len(all_points) >= 2:
            historical_values = [v for v, t in all_points]
            historical_mean = statistics.mean(historical_values)
            
            if historical_mean > 0:
                rate_change = abs(recent_mean - historical_mean) / historical_mean
                is_anomaly = rate_change > self.rate_threshold
                confidence = min(rate_change / self.rate_threshold, 1.0)
                
                return is_anomaly, confidence, historical_mean
        
        return False, 0.0, recent_mean

class PatternDetector:
    """Pattern-based anomaly detection"""
    
    def __init__(self, patterns: Dict[str, Any]):
        self.patterns = patterns
    
    def detect_anomaly(self, data_point: Dict[str, Any]) -> Tuple[bool, float, str]:
        """Detect anomalies based on patterns"""
        for pattern_name, pattern_config in self.patterns.items():
            if self._matches_pattern(data_point, pattern_config):
                confidence = pattern_config.get("confidence", 0.8)
                return True, confidence, pattern_name
        
        return False, 0.0, ""
    
    def _matches_pattern(self, data_point: Dict[str, Any], pattern: Dict[str, Any]) -> bool:
        """Check if data point matches pattern"""
        # Simplified pattern matching
        for key, expected_value in pattern.get("conditions", {}).items():
            if key not in data_point:
                return False
            
            actual_value = data_point[key]
            
            if isinstance(expected_value, dict):
                # Range check
                if "min" in expected_value and actual_value < expected_value["min"]:
                    return False
                if "max" in expected_value and actual_value > expected_value["max"]:
                    return False
            else:
                # Exact match
                if actual_value != expected_value:
                    return False
        
        return True

class AnomalyDetectionEngine:
    """Main anomaly detection engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Detectors
        self.detectors: Dict[str, Any] = {}
        self.detector_configs: Dict[str, AnomalyDetectorConfig] = {}
        
        # Anomaly storage
        self.anomalies: deque = deque(maxlen=10000)
        self.anomaly_index: Dict[str, Set[str]] = defaultdict(set)
        
        # Alert management
        self.alerts: deque = deque(maxlen=5000)
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        
        # Baseline data
        self.baselines: Dict[str, Dict[str, float]] = {}
        
        # Statistics
        self.stats = {
            "anomalies_detected": 0,
            "alerts_generated": 0,
            "false_positives": 0,
            "detection_accuracy": 0.0
        }
        
        # Background processing
        self.background_tasks: List[asyncio.Task] = []
        self._running = False
        
        # Thread pool
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Lock for thread safety
        self._lock = threading.RLock()
    
    def register_detector(self, name: str, detector_config: AnomalyDetectorConfig):
        """Register anomaly detector"""
        with self._lock:
            if detector_config.detection_method == DetectionMethod.STATISTICAL:
                detector = StatisticalDetector(
                    window_size=detector_config.window_size_minutes * 60,  # Convert to seconds
                    sensitivity=2.0 / detector_config.sensitivity
                )
            elif detector_config.detection_method == DetectionMethod.THRESHOLD:
                # Extract thresholds from context
                context = detector_config.context_filters
                detector = ThresholdDetector(
                    upper_threshold=context.get("upper_threshold"),
                    lower_threshold=context.get("lower_threshold")
                )
            elif detector_config.detection_method == DetectionMethod.RATE_ANALYSIS:
                detector = RateChangeDetector(
                    window_minutes=detector_config.window_size_minutes,
                    rate_threshold=2.0 / detector_config.sensitivity
                )
            elif detector_config.detection_method == DetectionMethod.PATTERN:
                patterns = detector_config.context_filters.get("patterns", {})
                detector = PatternDetector(patterns)
            else:
                self.logger.warning(f"Unsupported detection method: {detector_config.detection_method}")
                return
            
            self.detectors[name] = detector
            self.detector_configs[name] = detector_config
            
            self.logger.info(f"Registered detector: {name}")
    
    def add_metric_data(self, metric_name: str, value: float, 
                       timestamp: datetime = None, context: Dict[str, Any] = None):
        """Add metric data for analysis"""
        timestamp = timestamp or datetime.now()
        context = context or {}
        
        with self._lock:
            for detector_name, detector in self.detectors.items():
                config = self.detector_configs[detector_name]
                
                if not config.enabled:
                    continue
                
                # Check if metric matches patterns
                matches_pattern = any(
                    pattern in metric_name for pattern in config.metric_patterns
                )
                
                if not matches_pattern:
                    continue
                
                # Check context filters
                if not self._matches_context(context, config.context_filters):
                    continue
                
                try:
                    # Add data point to detector
                    if hasattr(detector, "add_data_point"):
                        detector.add_data_point(value, timestamp)
                    
                    # Detect anomaly
                    if hasattr(detector, "detect_anomaly"):
                        is_anomaly, confidence, expected_value = detector.detect_anomaly(value)
                        
                        if is_anomaly and confidence >= config.confidence_threshold:
                            anomaly = self._create_anomaly(
                                detector_name, config, metric_name, 
                                value, expected_value, confidence, 
                                timestamp, context
                            )
                            
                            self._store_anomaly(anomaly)
                            
                            # Generate alert if needed
                            self._check_alert_rules(anomaly)
                
                except Exception as e:
                    self.logger.error(f"Error in detector {detector_name}: {e}")
    
    def _matches_context(self, context: Dict[str, Any], 
                        context_filters: Dict[str, Any]) -> bool:
        """Check if context matches filters"""
        for key, expected_value in context_filters.items():
            if key == "patterns":
                continue  # Skip patterns, handled separately
            
            if key not in context:
                return False
            
            if context[key] != expected_value:
                return False
        
        return True
    
    def _create_anomaly(self, detector_name: str, config: AnomalyDetectorConfig,
                       metric_name: str, metric_value: float, expected_value: float,
                       confidence: float, timestamp: datetime,
                       context: Dict[str, Any]) -> Anomaly:
        """Create anomaly object"""
        deviation = 0.0
        if expected_value != 0:
            deviation = abs(metric_value - expected_value) / abs(expected_value)
        
        anomaly = Anomaly(
            id=str(uuid.uuid4()),
            anomaly_type=config.anomaly_type,
            severity=self._calculate_severity(deviation, confidence, config),
            confidence=confidence,
            title=f"{config.anomaly_type.value.title()} Anomaly in {metric_name}",
            description=self._generate_description(config, metric_name, metric_value, 
                                               expected_value, deviation),
            detected_at=timestamp,
            source=detector_name,
            metric_name=metric_name,
            metric_value=metric_value,
            expected_value=expected_value,
            deviation=deviation,
            detection_method=config.detection_method,
            context=context.copy(),
            affected_entities=self._extract_affected_entities(context),
            tags=config.tags.copy()
        )
        
        return anomaly
    
    def _calculate_severity(self, deviation: float, confidence: float,
                           config: AnomalyDetectorConfig) -> AnomalySeverity:
        """Calculate anomaly severity"""
        combined_score = (deviation + confidence) / 2.0
        
        if combined_score >= config.severity_threshold:
            return AnomalySeverity.CRITICAL
        elif combined_score >= config.severity_threshold * 0.75:
            return AnomalySeverity.HIGH
        elif combined_score >= config.severity_threshold * 0.5:
            return AnomalySeverity.MEDIUM
        else:
            return AnomalySeverity.LOW
    
    def _generate_description(self, config: AnomalyDetectorConfig, metric_name: str,
                            metric_value: float, expected_value: float,
                            deviation: float) -> str:
        """Generate anomaly description"""
        if config.detection_method == DetectionMethod.STATISTICAL:
            return (f"Statistical anomaly detected in {metric_name}. "
                   f"Value {metric_value:.2f} deviates {deviation:.1%} from expected {expected_value:.2f}. "
                   f"Detection method: {config.detection_method.value}")
        elif config.detection_method == DetectionMethod.THRESHOLD:
            return (f"Threshold violation in {metric_name}. "
                   f"Value {metric_value:.2f} exceeds configured threshold of {expected_value:.2f}.")
        else:
            return (f"Anomaly detected in {metric_name}. "
                   f"Current value: {metric_value:.2f}, Expected: {expected_value:.2f}. "
                   f"Deviation: {deviation:.1%}")
    
    def _extract_affected_entities(self, context: Dict[str, Any]) -> List[str]:
        """Extract affected entities from context"""
        entities = []
        
        for key in ["service", "host", "node", "instance", "component"]:
            if key in context and context[key]:
                entities.append(f"{key}:{context[key]}")
        
        return entities
    
    def _store_anomaly(self, anomaly: Anomaly):
        """Store anomaly"""
        with self._lock:
            self.anomalies.append(anomaly)
            self.stats["anomalies_detected"] += 1
            
            # Update indexes
            self.anomaly_index["type"].add(anomaly.id)
            self.anomaly_index[f"severity:{anomaly.severity.value}"].add(anomaly.id)
            self.anomaly_index[f"source:{anomaly.source}"].add(anomaly.id)
            self.anomaly_index[f"metric:{anomaly.metric_name}"].add(anomaly.id)
            
            for entity in anomaly.affected_entities:
                self.anomaly_index[f"entity:{entity}"].add(anomaly.id)
    
    def _check_alert_rules(self, anomaly: Anomaly):
        """Check if anomaly triggers alert rules"""
        for rule_name, rule in self.alert_rules.items():
            if self._matches_alert_rule(anomaly, rule):
                alert = self._create_alert(anomaly, rule)
                self._store_alert(alert)
    
    def _matches_alert_rule(self, anomaly: Anomaly, rule: Dict[str, Any]) -> bool:
        """Check if anomaly matches alert rule"""
        # Check severity
        if "min_severity" in rule:
            severity_levels = {
                AnomalySeverity.LOW: 1,
                AnomalySeverity.MEDIUM: 2,
                AnomalySeverity.HIGH: 3,
                AnomalySeverity.CRITICAL: 4
            }
            
            min_level = severity_levels[AnomalySeverity(rule["min_severity"])]
            anomaly_level = severity_levels[anomaly.severity]
            
            if anomaly_level < min_level:
                return False
        
        # Check anomaly type
        if "anomaly_types" in rule:
            if anomaly.anomaly_type.value not in rule["anomaly_types"]:
                return False
        
        # Check source
        if "sources" in rule:
            if anomaly.source not in rule["sources"]:
                return False
        
        # Check metric patterns
        if "metric_patterns" in rule:
            matches = any(pattern in anomaly.metric_name for pattern in rule["metric_patterns"])
            if not matches:
                return False
        
        return True
    
    def _create_alert(self, anomaly: Anomaly, rule: Dict[str, Any]) -> Alert:
        """Create alert from anomaly"""
        alert = Alert(
            id=str(uuid.uuid4()),
            anomaly_id=anomaly.id,
            severity=anomaly.severity,
            status=AlertStatus.ACTIVE,
            title=f"Alert: {anomaly.title}",
            message=rule.get("message", f"Anomaly detected: {anomaly.description}"),
            created_at=datetime.now(),
            acknowledged_at=None,
            resolved_at=None,
            acknowledged_by=None,
            resolved_by=None,
            escalation_level=0,
            notification_channels=rule.get("notification_channels", ["email"]),
            metadata={
                "rule_name": rule.get("name"),
                "anomaly_id": anomaly.id,
                "auto_generated": True
            }
        )
        
        return alert
    
    def _store_alert(self, alert: Alert):
        """Store alert"""
        with self._lock:
            self.alerts.append(alert)
            self.stats["alerts_generated"] += 1
    
    def add_alert_rule(self, name: str, rule: Dict[str, Any]):
        """Add alert rule"""
        self.alert_rules[name] = rule
        self.logger.info(f"Added alert rule: {name}")
    
    def get_anomalies(self, start_time: datetime = None,
                     end_time: datetime = None,
                     anomaly_type: AnomalyType = None,
                     severity: AnomalySeverity = None,
                     source: str = None,
                     limit: int = 100) -> List[Anomaly]:
        """Get anomalies with filters"""
        with self._lock:
            anomalies = list(self.anomalies)
        
        # Apply filters
        if start_time:
            anomalies = [a for a in anomalies if a.detected_at >= start_time]
        
        if end_time:
            anomalies = [a for a in anomalies if a.detected_at <= end_time]
        
        if anomaly_type:
            anomalies = [a for a in anomalies if a.anomaly_type == anomaly_type]
        
        if severity:
            anomalies = [a for a in anomalies if a.severity == severity]
        
        if source:
            anomalies = [a for a in anomalies if a.source == source]
        
        # Sort by detected time (newest first)
        anomalies.sort(key=lambda x: x.detected_at, reverse=True)
        
        return anomalies[:limit]
    
    def get_alerts(self, status: AlertStatus = None,
                   severity: AnomalySeverity = None,
                   limit: int = 100) -> List[Alert]:
        """Get alerts with filters"""
        with self._lock:
            alerts = list(self.alerts)
        
        # Apply filters
        if status:
            alerts = [a for a in alerts if a.status == status]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        # Sort by created time (newest first)
        alerts.sort(key=lambda x: x.created_at, reverse=True)
        
        return alerts[:limit]
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        with self._lock:
            for alert in self.alerts:
                if alert.id == alert_id and alert.status == AlertStatus.ACTIVE:
                    alert.status = AlertStatus.ACKNOWLEDGED
                    alert.acknowledged_at = datetime.now()
                    alert.acknowledged_by = acknowledged_by
                    return True
        
        return False
    
    def resolve_alert(self, alert_id: str, resolved_by: str) -> bool:
        """Resolve an alert"""
        with self._lock:
            for alert in self.alerts:
                if alert.id == alert_id and alert.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]:
                    alert.status = AlertStatus.RESOLVED
                    alert.resolved_at = datetime.now()
                    alert.resolved_by = resolved_by
                    return True
        
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get anomaly detection statistics"""
        with self._lock:
            # Calculate distribution by type
            type_counts = defaultdict(int)
            severity_counts = defaultdict(int)
            source_counts = defaultdict(int)
            
            for anomaly in self.anomalies:
                type_counts[anomaly.anomaly_type.value] += 1
                severity_counts[anomaly.severity.value] += 1
                source_counts[anomaly.source] += 1
            
            # Calculate alert statistics
            alert_status_counts = defaultdict(int)
            alert_severity_counts = defaultdict(int)
            
            for alert in self.alerts:
                alert_status_counts[alert.status.value] += 1
                alert_severity_counts[alert.severity.value] += 1
            
            return {
                "stats": self.stats.copy(),
                "anomaly_distribution": {
                    "by_type": dict(type_counts),
                    "by_severity": dict(severity_counts),
                    "by_source": dict(source_counts)
                },
                "alert_distribution": {
                    "by_status": dict(alert_status_counts),
                    "by_severity": dict(alert_severity_counts)
                },
                "active_detectors": len([d for d in self.detector_configs.values() if d.enabled]),
                "total_detectors": len(self.detector_configs),
                "alert_rules": len(self.alert_rules),
                "recent_anomalies": len([a for a in self.anomalies 
                                       if (datetime.now() - a.detected_at).total_seconds() < 3600]),
                "unresolved_alerts": len([a for a in self.alerts if a.status == AlertStatus.ACTIVE])
            }

# Global detection engine instance
_anomaly_detection_engine = None

def get_anomaly_detection_engine() -> AnomalyDetectionEngine:
    """Get global anomaly detection engine instance"""
    global _anomaly_detection_engine
    if _anomaly_detection_engine is None:
        _anomaly_detection_engine = AnomalyDetectionEngine()
    return _anomaly_detection_engine

def init_anomaly_detection() -> AnomalyDetectionEngine:
    """Initialize anomaly detection system"""
    engine = get_anomaly_detection_engine()
    
    # Register default detectors
    from .metrics_collection import get_metrics_collector
    from .log_aggregation import get_log_aggregator
    
    # CPU usage anomaly detector
    cpu_detector_config = AnomalyDetectorConfig(
        name="cpu_usage_detector",
        anomaly_type=AnomalyType.PERFORMANCE,
        detection_method=DetectionMethod.STATISTICAL,
        metric_patterns=["cpu_usage"],
        severity_threshold=0.8,
        confidence_threshold=0.7,
        window_size_minutes=10,
        min_data_points=20,
        sensitivity=0.7,
        enabled=True,
        tags={"performance", "system"},
        context_filters={}
    )
    engine.register_detector("cpu_usage", cpu_detector_config)
    
    # Memory usage anomaly detector
    memory_detector_config = AnomalyDetectorConfig(
        name="memory_usage_detector",
        anomaly_type=AnomalyType.SYSTEM,
        detection_method=DetectionMethod.THRESHOLD,
        metric_patterns=["memory_usage"],
        severity_threshold=0.9,
        confidence_threshold=0.8,
        window_size_minutes=5,
        min_data_points=10,
        sensitivity=0.8,
        enabled=True,
        tags={"system", "memory"},
        context_filters={"upper_threshold": 90.0}
    )
    engine.register_detector("memory_usage", memory_detector_config)
    
    # Error rate anomaly detector
    error_detector_config = AnomalyDetectorConfig(
        name="error_rate_detector",
        anomaly_type=AnomalyType.APPLICATION,
        detection_method=DetectionMethod.RATE_ANALYSIS,
        metric_patterns=["error_rate"],
        severity_threshold=0.05,
        confidence_threshold=0.6,
        window_size_minutes=5,
        min_data_points=15,
        sensitivity=0.6,
        enabled=True,
        tags={"application", "errors"},
        context_filters={}
    )
    engine.register_detector("error_rate", error_detector_config)
    
    # Add default alert rules
    engine.add_alert_rule("critical_performance", {
        "name": "critical_performance",
        "min_severity": "high",
        "anomaly_types": ["performance", "system"],
        "notification_channels": ["email", "slack"],
        "message": "Critical performance/system anomaly detected - immediate attention required"
    })
    
    engine.add_alert_rule("security_anomaly", {
        "name": "security_anomaly",
        "anomaly_types": ["security"],
        "notification_channels": ["email", "slack", "sms"],
        "message": "Security anomaly detected - investigate immediately"
    })
    
    return engine