"""
Aurora OS Disaster Recovery System
Comprehensive disaster recovery procedures and automation
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Set, Tuple, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
from concurrent.futures import ThreadPoolExecutor

class DisasterLevel(Enum):
    """Disaster severity levels"""
    MINOR = "minor"                    # Single service failure
    MODERATE = "moderate"              # Multiple services or single node failure
    MAJOR = "major"                   # Multiple nodes or data center failure
    CATASTROPHIC = "catastrophic"     # Complete system failure

class RecoveryPhase(Enum):
    """Recovery phases"""
    DETECTION = "detection"
    ASSESSMENT = "assessment"
    CONTAINMENT = "containment"
    RECOVERY = "recovery"
    VERIFICATION = "verification"
    POST_MORTEM = "post_mortem"

class RecoveryStatus(Enum):
    """Recovery status"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PARTIALLY_COMPLETED = "partially_completed"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

class DisasterType(Enum):
    """Types of disasters"""
    HARDWARE_FAILURE = "hardware_failure"
    NETWORK_OUTAGE = "network_outage"
    POWER_FAILURE = "power_failure"
    DATA_CORRUPTION = "data_corruption"
    SECURITY_BREACH = "security_breach"
    NATURAL_DISASTER = "natural_disaster"
    HUMAN_ERROR = "human_error"
    SOFTWARE_BUG = "software_bug"

@dataclass
class DisasterEvent:
    """Disaster event"""
    id: str
    disaster_type: DisasterType
    level: DisasterLevel
    title: str
    description: str
    affected_services: List[str]
    affected_nodes: List[str]
    detected_at: datetime
    detected_by: str
    impact_assessment: Dict[str, Any]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "disaster_type": self.disaster_type.value,
            "level": self.level.value,
            "title": self.title,
            "description": self.description,
            "affected_services": self.affected_services,
            "affected_nodes": self.affected_nodes,
            "detected_at": self.detected_at.isoformat(),
            "detected_by": self.detected_by,
            "impact_assessment": self.impact_assessment,
            "metadata": self.metadata
        }

@dataclass
class RecoveryStep:
    """Recovery procedure step"""
    id: str
    name: str
    description: str
    phase: RecoveryPhase
    order: int
    command: str
    timeout_seconds: int
    rollback_command: Optional[str]
    success_criteria: Dict[str, Any]
    dependencies: List[str]
    parallel_allowed: bool
    retry_count: int
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "phase": self.phase.value,
            "order": self.order,
            "command": self.command,
            "timeout_seconds": self.timeout_seconds,
            "rollback_command": self.rollback_command,
            "success_criteria": self.success_criteria,
            "dependencies": self.dependencies,
            "parallel_allowed": self.parallel_allowed,
            "retry_count": self.retry_count,
            "metadata": self.metadata
        }

@dataclass
class RecoveryPlan:
    """Disaster recovery plan"""
    id: str
    name: str
    disaster_types: List[DisasterType]
    disaster_levels: List[DisasterLevel]
    description: str
    rto_seconds: int  # Recovery Time Objective
    rpo_seconds: int  # Recovery Point Objective
    steps: List[RecoveryStep]
    notification_channels: List[str]
    escalation_policy: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    version: int
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "disaster_types": [dt.value for dt in self.disaster_types],
            "disaster_levels": [dl.value for dl in self.disaster_levels],
            "description": self.description,
            "rto_seconds": self.rto_seconds,
            "rpo_seconds": self.rpo_seconds,
            "steps": [step.to_dict() for step in self.steps],
            "notification_channels": self.notification_channels,
            "escalation_policy": self.escalation_policy,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "metadata": self.metadata
        }

@dataclass
class RecoveryExecution:
    """Recovery execution instance"""
    id: str
    disaster_event: DisasterEvent
    recovery_plan: RecoveryPlan
    status: RecoveryStatus
    started_at: datetime
    completed_at: Optional[datetime]
    current_phase: RecoveryPhase
    current_step: int
    completed_steps: List[str]
    failed_steps: List[str]
    execution_log: List[Dict[str, Any]]
    rollback_log: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "disaster_event": self.disaster_event.to_dict(),
            "recovery_plan": self.recovery_plan.to_dict(),
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "current_phase": self.current_phase.value,
            "current_step": self.current_step,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "execution_log": self.execution_log,
            "rollback_log": self.rollback_log,
            "metrics": self.metrics,
            "metadata": self.metadata
        }

class DisasterDetector:
    """Disaster detection system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.detection_rules: Dict[str, Dict[str, Any]] = {}
        self.monitoring_metrics: deque = deque(maxlen=10000)
        self.alert_thresholds: Dict[str, float] = {}
        
    def add_detection_rule(self, rule_id: str, rule: Dict[str, Any]):
        """Add disaster detection rule"""
        self.detection_rules[rule_id] = rule
        self.logger.info(f"Added detection rule: {rule_id}")
    
    def add_metric(self, metric: Dict[str, Any]):
        """Add monitoring metric"""
        metric["timestamp"] = datetime.now().isoformat()
        self.monitoring_metrics.append(metric)
    
    async def detect_disasters(self) -> List[DisasterEvent]:
        """Detect potential disasters"""
        detected_events = []
        
        for rule_id, rule in self.detection_rules.items():
            event = await self._evaluate_detection_rule(rule_id, rule)
            if event:
                detected_events.append(event)
        
        return detected_events
    
    async def _evaluate_detection_rule(self, rule_id: str, rule: Dict[str, Any]) -> Optional[DisasterEvent]:
        """Evaluate a detection rule"""
        try:
            disaster_type = DisasterType(rule["disaster_type"])
            disaster_level = DisasterLevel(rule["disaster_level"])
            
            # Check conditions
            conditions_met = await self._check_conditions(rule.get("conditions", {}))
            
            if conditions_met:
                event = DisasterEvent(
                    id=str(uuid.uuid4()),
                    disaster_type=disaster_type,
                    level=disaster_level,
                    title=rule["title"],
                    description=rule["description"],
                    affected_services=rule.get("affected_services", []),
                    affected_nodes=rule.get("affected_nodes", []),
                    detected_at=datetime.now(),
                    detected_by=f"rule_{rule_id}",
                    impact_assessment=rule.get("impact_assessment", {}),
                    metadata={"rule_id": rule_id, "rule": rule}
                )
                
                self.logger.warning(f"Disaster detected: {event.title}")
                return event
        
        except Exception as e:
            self.logger.error(f"Error evaluating detection rule {rule_id}: {e}")
        
        return None
    
    async def _check_conditions(self, conditions: Dict[str, Any]) -> bool:
        """Check if conditions are met"""
        # Simulate condition checking
        for condition_type, condition_config in conditions.items():
            if condition_type == "service_failure":
                # Check for service failures
                failed_services = condition_config.get("services", [])
                # Simulate detection
                if failed_services and random.random() < 0.1:  # 10% chance
                    return True
            
            elif condition_type == "node_failure":
                # Check for node failures
                failed_nodes = condition_config.get("nodes", [])
                # Simulate detection
                if failed_nodes and random.random() < 0.05:  # 5% chance
                    return True
            
            elif condition_type == "network_partition":
                # Check for network partitions
                # Simulate detection
                if random.random() < 0.02:  # 2% chance
                    return True
            
            elif condition_type == "data_corruption":
                # Check for data corruption
                # Simulate detection
                if random.random() < 0.01:  # 1% chance
                    return True
        
        return False

class DisasterRecoverySystem:
    """Main disaster recovery system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Components
        self.disaster_detector = DisasterDetector()
        
        # Recovery plans and executions
        self.recovery_plans: Dict[str, RecoveryPlan] = {}
        self.recovery_executions: Dict[str, RecoveryExecution] = {}
        self.active_executions: Set[str] = set()
        
        # State
        self.running = False
        self.detection_task: Optional[asyncio.Task] = None
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Event callbacks
        self.on_disaster_detected: Optional[Callable[[DisasterEvent], None]] = None
        self.on_recovery_started: Optional[Callable[[RecoveryExecution], None]] = None
        self.on_recovery_completed: Optional[Callable[[RecoveryExecution], None]] = None
        self.on_recovery_failed: Optional[Callable[[RecoveryExecution], None]] = None
        
        # Statistics
        self.stats = {
            "disasters_detected": 0,
            "recoveries_executed": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "average_recovery_time": 0.0
        }
        
        # Initialize default recovery plans
        self._initialize_default_plans()
        self._initialize_detection_rules()
    
    def _initialize_default_plans(self):
        """Initialize default recovery plans"""
        # Service failure recovery plan
        service_failure_plan = RecoveryPlan(
            id="service_failure_plan",
            name="Service Failure Recovery",
            disaster_types=[DisasterType.SOFTWARE_BUG, DisasterType.HUMAN_ERROR],
            disaster_levels=[DisasterLevel.MINOR, DisasterLevel.MODERATE],
            description="Recovery plan for service failures",
            rto_seconds=300,  # 5 minutes
            rpo_seconds=60,   # 1 minute
            steps=[
                RecoveryStep(
                    id="identify_service",
                    name="Identify Failed Service",
                    description="Identify which service has failed",
                    phase=RecoveryPhase.DETECTION,
                    order=1,
                    command="systemctl list-units --failed",
                    timeout_seconds=30,
                    rollback_command=None,
                    success_criteria={"failed_services_found": True},
                    dependencies=[],
                    parallel_allowed=False,
                    retry_count=3,
                    metadata={}
                ),
                RecoveryStep(
                    id="restart_service",
                    name="Restart Service",
                    description="Attempt to restart the failed service",
                    phase=RecoveryPhase.RECOVERY,
                    order=2,
                    command="systemctl restart {service_name}",
                    timeout_seconds=60,
                    rollback_command=None,
                    success_criteria={"service_running": True},
                    dependencies=["identify_service"],
                    parallel_allowed=False,
                    retry_count=3,
                    metadata={}
                ),
                RecoveryStep(
                    id="verify_service",
                    name="Verify Service Health",
                    description="Verify service is running and healthy",
                    phase=RecoveryPhase.VERIFICATION,
                    order=3,
                    command="curl -f http://localhost:{service_port}/health",
                    timeout_seconds=30,
                    rollback_command=None,
                    success_criteria={"http_status": 200},
                    dependencies=["restart_service"],
                    parallel_allowed=False,
                    retry_count=3,
                    metadata={}
                )
            ],
            notification_channels=["email", "slack"],
            escalation_policy={
                "level_1": {"time_seconds": 300, "channels": ["email"]},
                "level_2": {"time_seconds": 600, "channels": ["email", "slack", "sms"]}
            },
            created_at=datetime.now(),
            updated_at=datetime.now(),
            version=1,
            metadata={}
        )
        
        self.recovery_plans[service_failure_plan.id] = service_failure_plan
        
        # Node failure recovery plan
        node_failure_plan = RecoveryPlan(
            id="node_failure_plan",
            name="Node Failure Recovery",
            disaster_types=[DisasterType.HARDWARE_FAILURE, DisasterType.POWER_FAILURE],
            disaster_levels=[DisasterLevel.MODERATE, DisasterLevel.MAJOR],
            description="Recovery plan for node failures",
            rto_seconds=600,  # 10 minutes
            rpo_seconds=300,  # 5 minutes
            steps=[
                RecoveryStep(
                    id="isolate_node",
                    name="Isolate Failed Node",
                    description="Remove failed node from cluster",
                    phase=RecoveryPhase.CONTAINMENT,
                    order=1,
                    command="kubectl cordon {node_name}",
                    timeout_seconds=60,
                    rollback_command="kubectl uncordon {node_name}",
                    success_criteria={"node_cordoned": True},
                    dependencies=[],
                    parallel_allowed=False,
                    retry_count=3,
                    metadata={}
                ),
                RecoveryStep(
                    id="drain_node",
                    name="Drain Node",
                    description="Evict pods from failed node",
                    phase=RecoveryPhase.CONTAINMENT,
                    order=2,
                    command="kubectl drain {node_name} --ignore-daemonsets --delete-emptydir-data",
                    timeout_seconds=300,
                    rollback_command=None,
                    success_criteria={"node_drained": True},
                    dependencies=["isolate_node"],
                    parallel_allowed=False,
                    retry_count=2,
                    metadata={}
                ),
                RecoveryStep(
                    id="promote_replica",
                    name="Promote Replica",
                    description="Promote standby replica to primary",
                    phase=RecoveryPhase.RECOVERY,
                    order=3,
                    command="aurora-cli promote-replica --replica={replica_id}",
                    timeout_seconds=120,
                    rollback_command=None,
                    success_criteria={"promotion_successful": True},
                    dependencies=["drain_node"],
                    parallel_allowed=False,
                    retry_count=3,
                    metadata={}
                )
            ],
            notification_channels=["email", "slack", "pagerduty"],
            escalation_policy={
                "level_1": {"time_seconds": 60, "channels": ["slack"]},
                "level_2": {"time_seconds": 180, "channels": ["email", "slack", "pagerduty"]}
            },
            created_at=datetime.now(),
            updated_at=datetime.now(),
            version=1,
            metadata={}
        )
        
        self.recovery_plans[node_failure_plan.id] = node_failure_plan
        
        # Data center outage recovery plan
        datacenter_outage_plan = RecoveryPlan(
            id="datacenter_outage_plan",
            name="Data Center Outage Recovery",
            disaster_types=[DisasterType.NATURAL_DISASTER, DisasterType.NETWORK_OUTAGE, DisasterType.POWER_FAILURE],
            disaster_levels=[DisasterLevel.MAJOR, DisasterLevel.CATASTROPHIC],
            description="Recovery plan for data center outages",
            rto_seconds=3600,  # 1 hour
            rpo_seconds=900,   # 15 minutes
            steps=[
                RecoveryStep(
                    id="assess_outage",
                    name="Assess Outage Scope",
                    description="Determine scope of data center outage",
                    phase=RecoveryPhase.ASSESSMENT,
                    order=1,
                    command="aurora-cli assess-outage --datacenter={datacenter_id}",
                    timeout_seconds=120,
                    rollback_command=None,
                    success_criteria={"scope_determined": True},
                    dependencies=[],
                    parallel_allowed=False,
                    retry_count=3,
                    metadata={}
                ),
                RecoveryStep(
                    id="activate_dr_site",
                    name="Activate DR Site",
                    description="Activate disaster recovery site",
                    phase=RecoveryPhase.RECOVERY,
                    order=2,
                    command="aurora-cli activate-dr-site --site={dr_site_id}",
                    timeout_seconds=600,
                    rollback_command=None,
                    success_criteria={"dr_site_active": True},
                    dependencies=["assess_outage"],
                    parallel_allowed=False,
                    retry_count=2,
                    metadata={}
                ),
                RecoveryStep(
                    id="restore_backups",
                    name="Restore Backups",
                    description="Restore latest backups to DR site",
                    phase=RecoveryPhase.RECOVERY,
                    order=3,
                    command="aurora-cli restore-backups --target={dr_site_id}",
                    timeout_seconds=1800,
                    rollback_command=None,
                    success_criteria={"backups_restored": True},
                    dependencies=["activate_dr_site"],
                    parallel_allowed=False,
                    retry_count=2,
                    metadata={}
                ),
                RecoveryStep(
                    id="verify_services",
                    name="Verify Services",
                    description="Verify all services are running at DR site",
                    phase=RecoveryPhase.VERIFICATION,
                    order=4,
                    command="aurora-cli verify-services --site={dr_site_id}",
                    timeout_seconds=300,
                    rollback_command=None,
                    success_criteria={"services_healthy": True},
                    dependencies=["restore_backups"],
                    parallel_allowed=True,
                    retry_count=3,
                    metadata={}
                )
            ],
            notification_channels=["email", "slack", "pagerduty", "phone"],
            escalation_policy={
                "level_1": {"time_seconds": 60, "channels": ["slack", "pagerduty"]},
                "level_2": {"time_seconds": 300, "channels": ["email", "slack", "pagerduty", "phone"]},
                "level_3": {"time_seconds": 900, "channels": ["email", "slack", "pagerduty", "phone", "executive"]}
            },
            created_at=datetime.now(),
            updated_at=datetime.now(),
            version=1,
            metadata={}
        )
        
        self.recovery_plans[datacenter_outage_plan.id] = datacenter_outage_plan
    
    def _initialize_detection_rules(self):
        """Initialize default detection rules"""
        # Service failure detection rule
        self.disaster_detector.add_detection_rule("service_failure", {
            "title": "Service Failure Detected",
            "description": "One or more services have failed",
            "disaster_type": "software_bug",
            "disaster_level": "minor",
            "affected_services": ["aurora-api", "aurora-web", "aurora-db"],
            "conditions": {
                "service_failure": {
                    "services": ["aurora-api", "aurora-web", "aurora-db"],
                    "failure_threshold": 1,
                    "time_window_seconds": 60
                }
            },
            "impact_assessment": {
                "user_impact": "high",
                "business_impact": "medium",
                "estimated_downtime": "5-15 minutes"
            }
        })
        
        # Node failure detection rule
        self.disaster_detector.add_detection_rule("node_failure", {
            "title": "Node Failure Detected",
            "description": "One or more cluster nodes have failed",
            "disaster_type": "hardware_failure",
            "disaster_level": "moderate",
            "affected_nodes": ["node-1", "node-2", "node-3"],
            "conditions": {
                "node_failure": {
                    "nodes": ["node-1", "node-2", "node-3"],
                    "failure_threshold": 1,
                    "time_window_seconds": 30
                }
            },
            "impact_assessment": {
                "user_impact": "medium",
                "business_impact": "medium",
                "estimated_downtime": "10-30 minutes"
            }
        })
        
        # Network partition detection rule
        self.disaster_detector.add_detection_rule("network_partition", {
            "title": "Network Partition Detected",
            "description": "Network partition detected in cluster",
            "disaster_type": "network_outage",
            "disaster_level": "major",
            "conditions": {
                "network_partition": {
                    "quorum_loss": True,
                    "time_window_seconds": 15
                }
            },
            "impact_assessment": {
                "user_impact": "high",
                "business_impact": "high",
                "estimated_downtime": "30-60 minutes"
            }
        })
    
    async def start(self):
        """Start disaster recovery system"""
        self.logger.info("Starting disaster recovery system")
        
        self.running = True
        self.detection_task = asyncio.create_task(self._disaster_detection_loop())
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        self.logger.info("Disaster recovery system started")
    
    async def stop(self):
        """Stop disaster recovery system"""
        self.logger.info("Stopping disaster recovery system")
        
        self.running = False
        
        if self.detection_task:
            self.detection_task.cancel()
        if self.monitoring_task:
            self.monitoring_task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(
            *filter(None, [self.detection_task, self.monitoring_task]),
            return_exceptions=True
        )
        
        self.logger.info("Disaster recovery system stopped")
    
    async def _disaster_detection_loop(self):
        """Main disaster detection loop"""
        while self.running:
            try:
                # Detect disasters
                detected_events = await self.disaster_detector.detect_disasters()
                
                # Process detected disasters
                for event in detected_events:
                    await self._handle_disaster_event(event)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in disaster detection loop: {e}")
                await asyncio.sleep(10)
    
    async def _monitoring_loop(self):
        """Monitoring loop for system metrics"""
        while self.running:
            try:
                # Add mock monitoring metrics
                metrics = {
                    "cpu_usage": random.uniform(20, 90),
                    "memory_usage": random.uniform(30, 85),
                    "disk_usage": random.uniform(40, 80),
                    "network_latency": random.uniform(1, 100),
                    "error_rate": random.uniform(0, 5),
                    "service_health": random.choice(["healthy", "degraded", "unhealthy"]),
                    "timestamp": datetime.now().isoformat()
                }
                
                self.disaster_detector.add_metric(metrics)
                
                await asyncio.sleep(10)  # Collect metrics every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def _handle_disaster_event(self, event: DisasterEvent):
        """Handle detected disaster event"""
        self.logger.warning(f"Handling disaster event: {event.title}")
        
        self.stats["disasters_detected"] += 1
        
        # Notify callbacks
        if self.on_disaster_detected:
            await self._safe_callback(self.on_disaster_detected, event)
        
        # Find appropriate recovery plan
        recovery_plan = self._find_recovery_plan(event)
        if not recovery_plan:
            self.logger.error(f"No recovery plan found for disaster: {event.title}")
            return
        
        # Initiate recovery
        await self.initiate_recovery(event, recovery_plan)
    
    def _find_recovery_plan(self, event: DisasterEvent) -> Optional[RecoveryPlan]:
        """Find appropriate recovery plan for disaster event"""
        for plan in self.recovery_plans.values():
            if (event.disaster_type in plan.disaster_types and 
                event.level in plan.disaster_levels):
                return plan
        
        return None
    
    async def initiate_recovery(self, event: DisasterEvent, plan: RecoveryPlan) -> str:
        """Initiate disaster recovery"""
        execution_id = str(uuid.uuid4())
        
        execution = RecoveryExecution(
            id=execution_id,
            disaster_event=event,
            recovery_plan=plan,
            status=RecoveryStatus.IN_PROGRESS,
            started_at=datetime.now(),
            completed_at=None,
            current_phase=RecoveryPhase.DETECTION,
            current_step=0,
            completed_steps=[],
            failed_steps=[],
            execution_log=[],
            rollback_log=[],
            metrics={},
            metadata={}
        )
        
        self.recovery_executions[execution_id] = execution
        self.active_executions.add(execution_id)
        
        self.stats["recoveries_executed"] += 1
        
        self.logger.info(f"Initiated recovery {execution_id} for disaster: {event.title}")
        
        # Notify callbacks
        if self.on_recovery_started:
            await self._safe_callback(self.on_recovery_started, execution)
        
        # Start recovery execution
        asyncio.create_task(self._execute_recovery(execution))
        
        return execution_id
    
    async def _execute_recovery(self, execution: RecoveryExecution):
        """Execute recovery steps"""
        try:
            plan = execution.recovery_plan
            
            # Sort steps by order
            steps_by_phase = defaultdict(list)
            for step in plan.steps:
                steps_by_phase[step.phase].append(step)
            
            for phase in steps_by_phase:
                execution.current_phase = phase
                
                # Sort steps by order within phase
                phase_steps = sorted(steps_by_phase[phase], key=lambda x: x.order)
                
                # Execute steps in phase
                await self._execute_phase_steps(execution, phase_steps)
            
            # Mark as completed
            execution.status = RecoveryStatus.COMPLETED
            execution.completed_at = datetime.now()
            
            self.stats["successful_recoveries"] += 1
            
            # Update average recovery time
            recovery_time = (execution.completed_at - execution.started_at).total_seconds()
            self.stats["average_recovery_time"] = (
                (self.stats["average_recovery_time"] * (self.stats["successful_recoveries"] - 1) + recovery_time) /
                self.stats["successful_recoveries"]
            )
            
            self.logger.info(f"Recovery {execution.id} completed successfully")
            
            # Notify callbacks
            if self.on_recovery_completed:
                await self._safe_callback(self.on_recovery_completed, execution)
        
        except Exception as e:
            self.logger.error(f"Recovery {execution.id} failed: {e}")
            execution.status = RecoveryStatus.FAILED
            execution.completed_at = datetime.now()
            
            self.stats["failed_recoveries"] += 1
            
            # Notify callbacks
            if self.on_recovery_failed:
                await self._safe_callback(self.on_recovery_failed, execution)
        
        finally:
            self.active_executions.discard(execution.id)
    
    async def _execute_phase_steps(self, execution: RecoveryExecution, steps: List[RecoveryStep]):
        """Execute steps within a phase"""
        plan = execution.recovery_plan
        
        for step in steps:
            # Check dependencies
            if not self._check_step_dependencies(step, execution):
                self.logger.error(f"Dependencies not met for step: {step.name}")
                execution.failed_steps.append(step.id)
                continue
            
            # Execute step
            success = await self._execute_step(execution, step)
            
            if success:
                execution.completed_steps.append(step.id)
            else:
                execution.failed_steps.append(step.id)
                
                # Check if we should continue despite failure
                if step.phase in [RecoveryPhase.DETECTION, RecoveryPhase.ASSESSMENT]:
                    # Critical phases, stop execution
                    raise Exception(f"Critical step failed: {step.name}")
    
    def _check_step_dependencies(self, step: RecoveryStep, execution: RecoveryExecution) -> bool:
        """Check if step dependencies are satisfied"""
        for dep in step.dependencies:
            if dep not in execution.completed_steps:
                return False
        return True
    
    async def _execute_step(self, execution: RecoveryExecution, step: RecoveryStep) -> bool:
        """Execute a single recovery step"""
        execution.current_step += 1
        
        self.logger.info(f"Executing step: {step.name}")
        
        # Log step start
        execution.execution_log.append({
            "timestamp": datetime.now().isoformat(),
            "step_id": step.id,
            "step_name": step.name,
            "status": "started",
            "message": f"Started execution of step: {step.name}"
        })
        
        try:
            # Simulate step execution
            await asyncio.sleep(random.uniform(1, 5))
            
            # Simulate occasional step failures
            if random.random() < 0.1:  # 10% failure rate
                raise Exception(f"Step execution failed: {step.name}")
            
            # Log step success
            execution.execution_log.append({
                "timestamp": datetime.now().isoformat(),
                "step_id": step.id,
                "step_name": step.name,
                "status": "completed",
                "message": f"Successfully completed step: {step.name}"
            })
            
            return True
        
        except Exception as e:
            # Log step failure
            execution.execution_log.append({
                "timestamp": datetime.now().isoformat(),
                "step_id": step.id,
                "step_name": step.name,
                "status": "failed",
                "message": f"Step failed: {e}",
                "error": str(e)
            })
            
            # Attempt rollback if rollback command exists
            if step.rollback_command:
                await self._rollback_step(execution, step)
            
            return False
    
    async def _rollback_step(self, execution: RecoveryExecution, step: RecoveryStep):
        """Rollback a failed step"""
        self.logger.warning(f"Rolling back step: {step.name}")
        
        execution.rollback_log.append({
            "timestamp": datetime.now().isoformat(),
            "step_id": step.id,
            "step_name": step.name,
            "status": "rollback_started",
            "message": f"Started rollback of step: {step.name}"
        })
        
        try:
            # Simulate rollback
            await asyncio.sleep(random.uniform(0.5, 2))
            
            execution.rollback_log.append({
                "timestamp": datetime.now().isoformat(),
                "step_id": step.id,
                "step_name": step.name,
                "status": "rollback_completed",
                "message": f"Successfully rolled back step: {step.name}"
            })
        
        except Exception as e:
            execution.rollback_log.append({
                "timestamp": datetime.now().isoformat(),
                "step_id": step.id,
                "step_name": step.name,
                "status": "rollback_failed",
                "message": f"Rollback failed: {e}",
                "error": str(e)
            })
    
    async def _safe_callback(self, callback: Callable, *args, **kwargs):
        """Safely execute callback"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args, **kwargs)
            else:
                callback(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"Callback error: {e}")
    
    def get_recovery_status(self, execution_id: str = None) -> Union[RecoveryExecution, List[RecoveryExecution]]:
        """Get recovery execution status"""
        if execution_id:
            return self.recovery_executions.get(execution_id)
        else:
            return list(self.recovery_executions.values())
    
    def get_recovery_plans(self) -> List[RecoveryPlan]:
        """Get all recovery plans"""
        return list(self.recovery_plans.values())
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get disaster recovery statistics"""
        return self.stats.copy()

# Example usage
async def main():
    """Example usage of disaster recovery system"""
    dr_system = DisasterRecoverySystem()
    
    # Set up event callbacks
    def on_disaster_detected(event):
        print(f"DISASTER DETECTED: {event.title} - {event.description}")
    
    def on_recovery_started(execution):
        print(f"RECOVERY STARTED: {execution.id} for disaster: {execution.disaster_event.title}")
    
    def on_recovery_completed(execution):
        print(f"RECOVERY COMPLETED: {execution.id} in {(execution.completed_at - execution.started_at).total_seconds():.2f} seconds")
    
    def on_recovery_failed(execution):
        print(f"RECOVERY FAILED: {execution.id} - Check execution log for details")
    
    dr_system.on_disaster_detected = on_disaster_detected
    dr_system.on_recovery_started = on_recovery_started
    dr_system.on_recovery_completed = on_recovery_completed
    dr_system.on_recovery_failed = on_recovery_failed
    
    # Start disaster recovery system
    await dr_system.start()
    
    # Run for monitoring
    try:
        while True:
            stats = dr_system.get_statistics()
            print(f"DR Statistics: {stats['disasters_detected']} disasters, {stats['recoveries_executed']} recoveries")
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        print("\\nShutting down disaster recovery system...")
        await dr_system.stop()

if __name__ == "__main__":
    # Add import for random
    import random
    asyncio.run(main())