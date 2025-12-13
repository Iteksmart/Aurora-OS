#!/usr/bin/env python3
"""
Aurora OS Enterprise Console - Complete Web-Based Fleet Management
Unified web interface for managing Aurora OS enterprise deployments
"""

import asyncio
import json
import logging
import time
import uuid
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path

import aiohttp
from aiohttp import web, WSMsgType
import aiohttp_cors
import jwt
import bcrypt
from aiohttp_jinja2 import setup as jinja_setup, template

# Import Aurora components
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

try:
    from system.core.aurora_modes import AuroraModeManager, AuroraMode
    from system.security.aurora_guardian import AuroraGuardian
    from system.ai_control_plane.aurora_intent_engine import AuroraIntentEngine
    AURORA_COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Aurora components not available: {e}")
    print("Running in standalone mode with mock data")
    AURORA_COMPONENTS_AVAILABLE = False
    
    # Create mock classes for standalone operation
    from enum import Enum
    
    class AuroraMode(Enum):
        PERSONAL = "personal"
        ENTERPRISE = "enterprise"
        DEVELOPER = "developer"
        LOCKED_DOWN = "locked_down"
    
    class AuroraModeManager:
        def __init__(self):
            pass
        
        def get_mode_config(self, mode):
            return {"mode": mode.value}
        
        def get_security_level(self, mode):
            levels = {
                AuroraMode.PERSONAL: 6,
                AuroraMode.ENTERPRISE: 9,
                AuroraMode.DEVELOPER: 3,
                AuroraMode.LOCKED_DOWN: 10
            }
            return levels.get(mode, 5)
    
    class AuroraGuardian:
        def __init__(self):
            pass
    
    class AuroraIntentEngine:
        def __init__(self):
            pass

logger = logging.getLogger(__name__)

class UserRole(Enum):
    """User roles for enterprise console."""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    DEVELOPER = "developer"
    MSP_ADMIN = "msp_admin"
    MSP_TECH = "msp_tech"

class ComplianceLevel(Enum):
    """Compliance levels for regulated environments."""
    NONE = "none"
    BASIC = "basic"
    FIPS_140_2 = "fips_140_2"
    HIPAA = "hipaa"
    GDPR = "gdpr"
    SOX = "sox"

class DeploymentType(Enum):
    """Deployment types."""
    ON_PREMISE = "on_premise"
    CLOUD = "cloud"
    HYBRID = "hybrid"
    AIR_GAPPED = "air_gapped"

@dataclass
class EnterpriseNode:
    """Enterprise node information."""
    id: str
    name: str
    hostname: str
    ip_address: str
    os_version: str
    aurora_mode: AuroraMode
    status: str
    last_seen: datetime
    hardware_info: Dict[str, Any]
    compliance_level: ComplianceLevel
    location: str
    department: str
    managed_by: Optional[str] = None
    deployment_type: DeploymentType = DeploymentType.ON_PREMISE

@dataclass
class Policy:
    """Enterprise security policy."""
    id: str
    name: str
    description: str
    rules: Dict[str, Any]
    compliance_level: ComplianceLevel
    target_nodes: List[str]
    created_at: datetime
    updated_at: datetime
    created_by: str
    active: bool

@dataclass
class SLA:
    """Service Level Agreement."""
    id: str
    name: str
    description: str
    uptime_target: float  # 99.9%
    response_time: int    # milliseconds
    resolution_time: int  # hours
    monitoring_metrics: List[str]
    nodes_covered: List[str]
    active: bool

# UserInfo class needs to be available at module level
@dataclass
class UserInfo:
    """User information."""
    id: str
    username: str
    email: str
    role: UserRole
    created_at: datetime
    last_login: Optional[datetime]
    active: bool
    permissions: List[str]

class AuroraEnterpriseConsole:
    """Main Aurora Enterprise Console application."""
    
    def __init__(self, config_file: str = "/etc/aurora/enterprise_config.json"):
        self.config_file = config_file
        self.app = web.Application()
        self.port = 8081
        self.secret_key = os.environ.get('AURORA_SECRET', 'aurora-enterprise-secret-key')
        
        # Core components
        self.mode_manager = AuroraModeManager()
        self.guardian = AuroraGuardian()
        self.intent_engine = None  # Initialize later to avoid async issues
        
        # Enterprise data
        self.nodes: Dict[str, EnterpriseNode] = {}
        self.users: Dict[str, UserInfo] = {}
        self.policies: Dict[str, Policy] = {}
        self.slas: Dict[str, SLA] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # WebSocket connections
        self.websocket_connections: Dict[str, web.WebSocketResponse] = {}
        
        # Setup application
        self._setup_middleware()
        self._setup_routes()
        self._load_configuration()
        self._initialize_sample_data()
    
    def _setup_middleware(self):
        """Setup CORS and security middleware."""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Add CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
        
        # Security middleware
        async def security_middleware(request, handler):
            # Add security headers
            response = await handler(request)
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            return response
        
        self.app.middlewares.append(security_middleware)
    
    def _setup_routes(self):
        """Setup application routes."""
        # Static files
        static_path = os.path.join(os.path.dirname(__file__), 'static')
        self.app.router.add_static('/static/', path=static_path, name='static')
        
        # API routes
        self.app.router.add_get('/api/health', self.health_check)
        self.app.router.add_post('/api/auth/login', self.login)
        self.app.router.add_post('/api/auth/logout', self.logout)
        self.app.router.add_get('/api/nodes', self.get_nodes)
        self.app.router.add_post('/api/nodes', self.register_node)
        self.app.router.add_put('/api/nodes/{node_id}', self.update_node)
        self.app.router.add_delete('/api/nodes/{node_id}', self.remove_node)
        
        # Management routes
        self.app.router.add_get('/api/policies', self.get_policies)
        self.app.router.add_post('/api/policies', self.create_policy)
        self.app.router.add_put('/api/policies/{policy_id}', self.update_policy)
        self.app.router.add_post('/api/policies/{policy_id}/deploy', self.deploy_policy)
        
        self.app.router.add_get('/api/slas', self.get_slas)
        self.app.router.add_post('/api/slas', self.create_sla)
        self.app.router.add_get('/api/compliance', self.get_compliance_status)
        self.app.router.add_get('/api/monitoring', self.get_monitoring_data)
        
        # Aurora-specific routes
        self.app.router.add_get('/api/modes', self.get_aurora_modes)
        self.app.router.add_post('/api/nodes/{node_id}/mode', self.set_node_mode)
        self.app.router.add_get('/api/security', self.get_security_status)
        self.app.router.add_post('/api/drivers/update', self.update_drivers)
        self.app.router.add_get('/api/slas', self.get_slas)
        self.app.router.add_post('/api/slas', self.create_sla)
        self.app.router.add_get('/api/monitoring', self.get_monitoring_data)
        
        # WebSocket for real-time updates
        self.app.router.add_get('/ws', self.websocket_handler)
        
        # Main console pages
        self.app.router.add_get('/', self.dashboard_page)
        self.app.router.add_get('/nodes', self.nodes_page)
        self.app.router.add_get('/policies', self.policies_page)
        self.app.router.add_get('/monitoring', self.monitoring_page)
        self.app.router.add_get('/compliance', self.compliance_page)
    
    def _load_configuration(self):
        """Load enterprise configuration."""
        try:
            config_path = Path(self.config_file)
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.port = config.get('port', 8080)
                    self.secret_key = config.get('secret_key', self.secret_key)
            else:
                logger.info(f"Config file {config_path} not found, using defaults")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
    
    def _initialize_sample_data(self):
        """Initialize sample enterprise data."""
        # Sample admin user
        admin_password = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
        self.users["admin"] = UserInfo(
            id="admin",
            username="admin",
            email="admin@aurora-os.enterprise",
            role=UserRole.ADMIN,
            created_at=datetime.now(),
            last_login=None,
            active=True,
            permissions=["read", "write", "admin", "policies", "nodes", "users"]
        )
        
        # Sample nodes
        sample_nodes = [
            EnterpriseNode(
                id="node-001",
                name="Production Server 1",
                hostname="aurora-prod-01",
                ip_address="192.168.1.100",
                os_version="Aurora OS 1.0.0",
                aurora_mode=AuroraMode.ENTERPRISE,
                status="online",
                last_seen=datetime.now(),
                hardware_info={"cpu": "Intel Xeon", "ram": "32GB", "storage": "1TB SSD"},
                compliance_level=ComplianceLevel.FIPS_140_2,
                location="Data Center A",
                department="IT Operations"
            ),
            EnterpriseNode(
                id="node-002",
                name="Development Workstation",
                hostname="aurora-dev-01",
                ip_address="192.168.2.50",
                os_version="Aurora OS 1.0.0",
                aurora_mode=AuroraMode.DEVELOPER,
                status="online",
                last_seen=datetime.now(),
                hardware_info={"cpu": "AMD Ryzen 9", "ram": "64GB", "storage": "2TB NVMe"},
                compliance_level=ComplianceLevel.BASIC,
                location="Office Building",
                department="Development"
            )
        ]
        
        for node in sample_nodes:
            self.nodes[node.id] = node
        
        # Sample policy
        sample_policy = Policy(
            id="policy-001",
            name="Enterprise Security Baseline",
            description="Minimum security requirements for all enterprise nodes",
            rules={
                "firewall": "strict",
                "encryption": True,
                "audit_logging": True,
                "auto_updates": False,
                "biometric_auth": True
            },
            compliance_level=ComplianceLevel.FIPS_140_2,
            target_nodes=["node-001", "node-002"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            created_by="admin",
            active=True
        )
        
        self.policies[sample_policy.id] = sample_policy
    
    async def health_check(self, request):
        """Health check endpoint."""
        return web.json_response({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "nodes_managed": len(self.nodes),
            "active_policies": len([p for p in self.policies.values() if p.active])
        })
    
    async def login(self, request):
        """User authentication."""
        try:
            data = await request.json()
            username = data.get('username')
            password = data.get('password')
            
            user = self.users.get(username)
            if not user or not user.active:
                return web.json_response({"error": "Invalid credentials"}, status=401)
            
            # For demo purposes, check against hardcoded password
            if username == "admin" and password == "admin123":
                # Create JWT token
                token = jwt.encode({
                    'user_id': user.id,
                    'username': user.username,
                    'role': user.role.value,
                    'exp': datetime.now() + timedelta(hours=24)
                }, self.secret_key, algorithm='HS256')
                
                # Update last login
                user.last_login = datetime.now()
                
                return web.json_response({
                    "token": token,
                    "user": asdict(user),
                    "permissions": user.permissions
                })
            else:
                return web.json_response({"error": "Invalid credentials"}, status=401)
        
        except Exception as e:
            logger.error(f"Login error: {e}")
            return web.json_response({"error": "Authentication failed"}, status=500)
    
    async def logout(self, request):
        """User logout."""
        # In a real implementation, would invalidate token
        return web.json_response({"message": "Logged out successfully"})
    
    async def get_nodes(self, request):
        """Get all managed nodes."""
        nodes_data = []
        for node in self.nodes.values():
            node_dict = asdict(node)
            node_dict['aurora_mode'] = node.aurora_mode.value
            node_dict['compliance_level'] = node.compliance_level.value
            node_dict['deployment_type'] = node.deployment_type.value
            node_dict['last_seen'] = node.last_seen.isoformat()
            node_dict['status'] = node.status
            nodes_data.append(node_dict)
        
        return web.json_response({
            "nodes": nodes_data,
            "total": len(nodes_data),
            "online": len([n for n in self.nodes.values() if n.status == "online"])
        })
    
    async def register_node(self, request):
        """Register a new node."""
        try:
            data = await request.json()
            
            node = EnterpriseNode(
                id=data.get('id', str(uuid.uuid4())),
                name=data['name'],
                hostname=data['hostname'],
                ip_address=data['ip_address'],
                os_version=data.get('os_version', 'Unknown'),
                aurora_mode=AuroraMode(data.get('aurora_mode', 'personal')),
                status="pending",
                last_seen=datetime.now(),
                hardware_info=data.get('hardware_info', {}),
                compliance_level=ComplianceLevel(data.get('compliance_level', 'none')),
                location=data.get('location', 'Unknown'),
                department=data.get('department', 'Unknown'),
                deployment_type=DeploymentType(data.get('deployment_type', 'on_premise'))
            )
            
            self.nodes[node.id] = node
            
            # Notify via WebSocket
            await self._broadcast_update({
                "type": "node_registered",
                "node": asdict(node)
            })
            
            return web.json_response({
                "message": "Node registered successfully",
                "node_id": node.id
            })
        
        except Exception as e:
            logger.error(f"Node registration error: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def update_node(self, request):
        """Update an existing node."""
        try:
            node_id = request.match_info['node_id']
            data = await request.json()
            
            if node_id not in self.nodes:
                return web.json_response({"error": "Node not found"}, status=404)
            
            node = self.nodes[node_id]
            
            # Update node properties
            if 'name' in data:
                node.name = data['name']
            if 'aurora_mode' in data:
                node.aurora_mode = AuroraMode(data['aurora_mode'])
            if 'status' in data:
                node.status = data['status']
            if 'compliance_level' in data:
                node.compliance_level = ComplianceLevel(data['compliance_level'])
            if 'location' in data:
                node.location = data['location']
            if 'department' in data:
                node.department = data['department']
            
            node.last_seen = datetime.now()
            
            # Notify via WebSocket
            await self._broadcast_update({
                "type": "node_updated",
                "node": asdict(node)
            })
            
            return web.json_response({
                "message": "Node updated successfully",
                "node_id": node.id
            })
        
        except Exception as e:
            logger.error(f"Node update error: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def remove_node(self, request):
        """Remove a node."""
        try:
            node_id = request.match_info['node_id']
            
            if node_id not in self.nodes:
                return web.json_response({"error": "Node not found"}, status=404)
            
            del self.nodes[node_id]
            
            # Notify via WebSocket
            await self._broadcast_update({
                "type": "node_removed",
                "node_id": node_id
            })
            
            return web.json_response({
                "message": "Node removed successfully",
                "node_id": node_id
            })
        
        except Exception as e:
            logger.error(f"Node removal error: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def get_policies(self, request):
        """Get all policies."""
        policies_data = []
        for policy in self.policies.values():
            policy_dict = asdict(policy)
            policy_dict['compliance_level'] = policy.compliance_level.value
            policy_dict['created_at'] = policy.created_at.isoformat()
            policy_dict['updated_at'] = policy.updated_at.isoformat()
            policies_data.append(policy_dict)
        
        return web.json_response({
            "policies": policies_data,
            "total": len(policies_data),
            "active": len([p for p in self.policies.values() if p.active])
        })
    
    async def create_policy(self, request):
        """Create a new policy."""
        try:
            data = await request.json()
            
            policy = Policy(
                id=str(uuid.uuid4()),
                name=data['name'],
                description=data['description'],
                rules=data['rules'],
                compliance_level=ComplianceLevel(data['compliance_level']),
                target_nodes=data.get('target_nodes', []),
                created_at=datetime.now(),
                updated_at=datetime.now(),
                created_by=data.get('created_by', 'admin'),
                active=data.get('active', True)
            )
            
            self.policies[policy.id] = policy
            
            return web.json_response({
                "message": "Policy created successfully",
                "policy_id": policy.id
            })
        
        except Exception as e:
            logger.error(f"Policy creation error: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def update_policy(self, request):
        """Update an existing policy."""
        try:
            policy_id = request.match_info['policy_id']
            data = await request.json()
            
            if policy_id not in self.policies:
                return web.json_response({"error": "Policy not found"}, status=404)
            
            policy = self.policies[policy_id]
            
            # Update policy properties
            if 'name' in data:
                policy.name = data['name']
            if 'description' in data:
                policy.description = data['description']
            if 'rules' in data:
                policy.rules = data['rules']
            if 'compliance_level' in data:
                policy.compliance_level = ComplianceLevel(data['compliance_level'])
            if 'target_nodes' in data:
                policy.target_nodes = data['target_nodes']
            if 'active' in data:
                policy.active = data['active']
            
            policy.updated_at = datetime.now()
            
            return web.json_response({
                "message": "Policy updated successfully",
                "policy_id": policy.id
            })
        
        except Exception as e:
            logger.error(f"Policy update error: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def deploy_policy(self, request):
        """Deploy a policy to target nodes."""
        try:
            policy_id = request.match_info['policy_id']
            
            if policy_id not in self.policies:
                return web.json_response({"error": "Policy not found"}, status=404)
            
            policy = self.policies[policy_id]
            
            # In a real implementation, this would deploy to actual nodes
            # For now, we'll simulate the deployment
            deployed_nodes = []
            for node_id in policy.target_nodes:
                if node_id in self.nodes:
                    deployed_nodes.append(node_id)
            
            # Notify via WebSocket
            await self._broadcast_update({
                "type": "policy_deployed",
                "policy": asdict(policy),
                "deployed_nodes": deployed_nodes
            })
            
            return web.json_response({
                "message": "Policy deployed successfully",
                "policy_id": policy_id,
                "deployed_nodes": len(deployed_nodes)
            })
        
        except Exception as e:
            logger.error(f"Policy deployment error: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def get_compliance_status(self, request):
        """Get compliance status across all nodes."""
        compliance_data = []
        
        for node in self.nodes.values():
            # Check node compliance against active policies
            node_compliance = {
                "node_id": node.id,
                "node_name": node.name,
                "compliance_level": node.compliance_level.value,
                "status": "compliant",  # Simplified for demo
                "last_check": datetime.now().isoformat(),
                "violations": [],
                "score": 95.0  # Simplified compliance score
            }
            compliance_data.append(node_compliance)
        
        return web.json_response({
            "compliance": compliance_data,
            "overall_compliance": 95.0,
            "total_nodes": len(self.nodes),
            "compliant_nodes": len(self.nodes)
        })
    
    async def get_aurora_modes(self, request):
        """Get Aurora modes information."""
        modes_data = []
        for mode in AuroraMode:
            mode_config = self.mode_manager.get_mode_config(mode)
            modes_data.append({
                "mode": mode.value,
                "security_level": self.mode_manager.get_security_level(mode),
                "description": {
                    AuroraMode.PERSONAL: "Balanced mode for personal use with AI assistance",
                    AuroraMode.ENTERPRISE: "Secure mode for corporate environments with policy enforcement",
                    AuroraMode.DEVELOPER: "Open mode for development with debugging tools",
                    AuroraMode.LOCKED_DOWN: "Maximum security mode for sensitive operations"
                }.get(mode, "Unknown mode")
            })
        
        return web.json_response({
            "modes": modes_data,
            "current_mode_distribution": {
                mode.value: len([n for n in self.nodes.values() if n.aurora_mode == mode])
                for mode in AuroraMode
            }
        })
    
    async def set_node_mode(self, request):
        """Set Aurora mode for a specific node."""
        try:
            node_id = request.match_info['node_id']
            data = await request.json()
            
            if node_id not in self.nodes:
                return web.json_response({"error": "Node not found"}, status=404)
            
            new_mode = AuroraMode(data['mode'])
            node = self.nodes[node_id]
            node.aurora_mode = new_mode
            node.last_seen = datetime.now()
            
            # Notify via WebSocket
            await self._broadcast_update({
                "type": "node_mode_changed",
                "node_id": node_id,
                "new_mode": new_mode.value
            })
            
            return web.json_response({
                "message": f"Node {node_id} mode set to {new_mode.value}",
                "node_id": node_id,
                "mode": new_mode.value
            })
        
        except Exception as e:
            logger.error(f"Set node mode error: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def get_security_status(self, request):
        """Get security status from Aurora Guardian."""
        try:
            if AURORA_COMPONENTS_AVAILABLE:
                security_status = self.guardian.get_security_status()
            else:
                # Mock security data
                security_status = {
                    "security_level": "high",
                    "total_decisions": len(self.nodes) * 10,
                    "blocked_actions": 2,
                    "allowed_actions": 48,
                    "compliance_status": {
                        "score": 95,
                        "level": "FIPS 140-2"
                    },
                    "recommendations": [
                        "Update drivers on production nodes",
                        "Review firewall rules for developer nodes"
                    ]
                }
            
            return web.json_response(security_status)
        
        except Exception as e:
            logger.error(f"Get security status error: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def update_drivers(self, request):
        """Update drivers across nodes."""
        try:
            data = await request.json()
            target_nodes = data.get('target_nodes', list(self.nodes.keys()))
            
            updated_nodes = []
            for node_id in target_nodes:
                if node_id in self.nodes:
                    # In real implementation, this would trigger driver updates
                    updated_nodes.append(node_id)
            
            # Notify via WebSocket
            await self._broadcast_update({
                "type": "drivers_updated",
                "updated_nodes": updated_nodes
            })
            
            return web.json_response({
                "message": "Driver updates initiated",
                "updated_nodes": updated_nodes
            })
        
        except Exception as e:
            logger.error(f"Driver update error: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def get_slas(self, request):
        """Get SLA information."""
        slas_data = []
        for sla in self.slas.values():
            sla_dict = asdict(sla)
            slas_data.append(sla_dict)
        
        return web.json_response({
            "slas": slas_data,
            "total": len(slas_data),
            "active": len([s for s in self.slas.values() if s.active])
        })
    
    async def create_sla(self, request):
        """Create a new SLA."""
        try:
            data = await request.json()
            
            sla = SLA(
                id=str(uuid.uuid4()),
                name=data['name'],
                description=data['description'],
                uptime_target=data['uptime_target'],
                response_time=data['response_time'],
                resolution_time=data['resolution_time'],
                monitoring_metrics=data.get('monitoring_metrics', []),
                nodes_covered=data.get('nodes_covered', []),
                active=data.get('active', True)
            )
            
            self.slas[sla.id] = sla
            
            return web.json_response({
                "message": "SLA created successfully",
                "sla_id": sla.id
            })
        
        except Exception as e:
            logger.error(f"SLA creation error: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def get_monitoring_data(self, request):
        """Get monitoring data."""
        # Mock monitoring data
        monitoring_data = {
            "metrics": {
                "cpu_usage": 23.5,
                "memory_usage": 67.8,
                "disk_usage": 45.2,
                "network_io": 125.6,
                "response_time": 87,
                "uptime": 99.9
            },
            "nodes": [
                {
                    "id": node.id,
                    "name": node.name,
                    "status": node.status,
                    "cpu": round(20 + (hash(node.id) % 30), 1),
                    "memory": round(50 + (hash(node.id) % 20), 1),
                    "last_update": datetime.now().isoformat()
                }
                for node in self.nodes.values()
            ],
            "alerts": [
                {
                    "id": "alert-001",
                    "type": "warning",
                    "message": "High CPU usage on production server",
                    "node_id": "node-001",
                    "timestamp": datetime.now().isoformat()
                }
            ]
        }
        
        return web.json_response(monitoring_data)
    
    async def websocket_handler(self, request):
        """WebSocket handler for real-time updates."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        session_id = str(uuid.uuid4())
        self.websocket_connections[session_id] = ws
        
        try:
            # Send initial data
            await ws.send_str(json.dumps({
                "type": "connected",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }))
            
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    # Handle WebSocket messages
                    if data.get('type') == 'ping':
                        await ws.send_str(json.dumps({"type": "pong"}))
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
        
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            if session_id in self.websocket_connections:
                del self.websocket_connections[session_id]
        
        return ws
    
    async def _broadcast_update(self, data: Dict[str, Any]):
        """Broadcast update to all connected WebSocket clients."""
        message = json.dumps(data)
        for ws in self.websocket_connections.values():
            if not ws.closed:
                try:
                    await ws.send_str(message)
                except Exception as e:
                    logger.error(f"Failed to send WebSocket message: {e}")
    
    # Web page handlers
    async def dashboard_page(self, request):
        """Main dashboard page."""
        return web.Response(text=self._get_dashboard_html(), content_type='text/html')
    
    async def nodes_page(self, request):
        """Nodes management page."""
        return web.Response(text=self._get_nodes_html(), content_type='text/html')
    
    async def policies_page(self, request):
        """Policies management page."""
        return web.Response(text=self._get_policies_html(), content_type='text/html')
    
    async def monitoring_page(self, request):
        """Monitoring page."""
        return web.Response(text=self._get_monitoring_html(), content_type='text/html')
    
    async def compliance_page(self, request):
        """Compliance page."""
        return web.Response(text=self._get_compliance_html(), content_type='text/html')
    
    def _get_dashboard_html(self) -> str:
        """Generate dashboard HTML."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aurora OS Enterprise Console</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem 2rem; }
        .dashboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; padding: 2rem; }
        .card { background: white; border-radius: 12px; padding: 1.5rem; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .card h3 { margin-bottom: 1rem; color: #333; }
        .metric { display: flex; justify-content: space-between; align-items: center; margin: 1rem 0; }
        .metric-value { font-size: 2rem; font-weight: bold; color: #667eea; }
        .status-indicator { width: 12px; height: 12px; border-radius: 50%; display: inline-block; margin-right: 0.5rem; }
        .status-online { background: #4CAF50; }
        .status-offline { background: #f44336; }
        .status-pending { background: #FF9800; }
    </style>
</head>
<body>
    <header class="header">
        <h1>🌅 Aurora OS Enterprise Console</h1>
        <p>Fleet Management & Operations Dashboard</p>
    </header>
    
    <div class="dashboard">
        <div class="card">
            <h3>📊 System Overview</h3>
            <div class="metric">
                <span>Total Nodes</span>
                <span class="metric-value" id="total-nodes">0</span>
            </div>
            <div class="metric">
                <span><span class="status-indicator status-online"></span>Online</span>
                <span class="metric-value" id="online-nodes">0</span>
            </div>
            <div class="metric">
                <span><span class="status-indicator status-offline"></span>Offline</span>
                <span class="metric-value" id="offline-nodes">0</span>
            </div>
        </div>
        
        <div class="card">
            <h3>🔒 Security Status</h3>
            <div class="metric">
                <span>Compliance Score</span>
                <span class="metric-value" id="compliance-score">95%</span>
            </div>
            <div class="metric">
                <span>Active Policies</span>
                <span class="metric-value" id="active-policies">0</span>
            </div>
            <div class="metric">
                <span>Security Alerts</span>
                <span class="metric-value" id="security-alerts">0</span>
            </div>
        </div>
        
        <div class="card">
            <h3>🎯 Aurora Modes</h3>
            <div class="metric">
                <span>Enterprise</span>
                <span class="metric-value" id="enterprise-nodes">0</span>
            </div>
            <div class="metric">
                <span>Developer</span>
                <span class="metric-value" id="developer-nodes">0</span>
            </div>
            <div class="metric">
                <span>Personal</span>
                <span class="metric-value" id="personal-nodes">0</span>
            </div>
        </div>
        
        <div class="card">
            <h3>⚡ Performance</h3>
            <div class="metric">
                <span>Avg Response Time</span>
                <span class="metric-value">87ms</span>
            </div>
            <div class="metric">
                <span>System Uptime</span>
                <span class="metric-value">99.9%</span>
            </div>
            <div class="metric">
                <span>Issues Resolved</span>
                <span class="metric-value" id="issues-resolved">0</span>
            </div>
        </div>
    </div>
    
    <script>
        // Connect to WebSocket for real-time updates
        const ws = new WebSocket('ws://localhost:8080/ws');
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            console.log('Received:', data);
            updateDashboard(data);
        };
        
        function updateDashboard(data) {
            if (data.type === 'node_registered') {
                // Refresh dashboard data
                loadDashboardData();
            }
        }
        
        async function loadDashboardData() {
            try {
                const nodesResponse = await fetch('/api/nodes');
                const nodesData = await nodesResponse.json();
                
                const policiesResponse = await fetch('/api/policies');
                const policiesData = await policiesResponse.json();
                
                const modesResponse = await fetch('/api/modes');
                const modesData = await modesResponse.json();
                
                // Update UI
                document.getElementById('total-nodes').textContent = nodesData.total;
                document.getElementById('online-nodes').textContent = nodesData.online;
                document.getElementById('offline-nodes').textContent = nodesData.total - nodesData.online;
                document.getElementById('active-policies').textContent = policiesData.active;
                
                // Update Aurora modes
                const modeCounts = modesData.current_mode_distribution;
                document.getElementById('enterprise-nodes').textContent = modeCounts.enterprise || 0;
                document.getElementById('developer-nodes').textContent = modeCounts.developer || 0;
                document.getElementById('personal-nodes').textContent = modeCounts.personal || 0;
                
            } catch (error) {
                console.error('Error loading dashboard data:', error);
            }
        }
        
        // Load initial data
        loadDashboardData();
        
        // Refresh every 30 seconds
        setInterval(loadDashboardData, 30000);
    </script>
</body>
</html>'''
    
    def _get_nodes_html(self) -> str:
        """Generate nodes management page HTML."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Node Management - Aurora OS Enterprise</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem 2rem; }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .node-table { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 1rem; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-weight: 600; }
        .status-badge { padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.875rem; font-weight: 500; }
        .status-online { background: #d4edda; color: #155724; }
        .status-offline { background: #f8d7da; color: #721c24; }
        .mode-badge { padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.875rem; }
        .mode-enterprise { background: #e3f2fd; color: #1565c0; }
        .mode-developer { background: #f3e5f5; color: #7b1fa2; }
        .mode-personal { background: #e8f5e8; color: #2e7d32; }
    </style>
</head>
<body>
    <header class="header">
        <h1>🖥️ Node Management</h1>
        <p>Manage Aurora OS enterprise nodes</p>
    </header>
    
    <div class="container">
        <div class="node-table">
            <table id="nodes-table">
                <thead>
                    <tr>
                        <th>Node Name</th>
                        <th>Status</th>
                        <th>Aurora Mode</th>
                        <th>IP Address</th>
                        <th>Location</th>
                        <th>Department</th>
                        <th>Last Seen</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="nodes-tbody">
                    <!-- Node data will be loaded here -->
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        async function loadNodes() {
            try {
                const response = await fetch('/api/nodes');
                const data = await response.json();
                
                const tbody = document.getElementById('nodes-tbody');
                tbody.innerHTML = '';
                
                data.nodes.forEach(node => {
                    const row = document.createElement('tr');
                    
                    const statusClass = node.status === 'online' ? 'status-online' : 'status-offline';
                    const modeClass = `mode-${node.aurora_mode}`;
                    
                    row.innerHTML = `
                        <td><strong>${node.name}</strong><br><small>${node.hostname}</small></td>
                        <td><span class="status-badge ${statusClass}">${node.status}</span></td>
                        <td><span class="mode-badge ${modeClass}">${node.aurora_mode}</span></td>
                        <td>${node.ip_address}</td>
                        <td>${node.location}</td>
                        <td>${node.department}</td>
                        <td>${new Date(node.last_seen).toLocaleString()}</td>
                        <td>
                            <button onclick="configureNode('${node.id}')" style="padding: 0.25rem 0.5rem; margin-right: 0.25rem;">Configure</button>
                            <button onclick="viewDetails('${node.id}')" style="padding: 0.25rem 0.5rem;">Details</button>
                        </td>
                    `;
                    
                    tbody.appendChild(row);
                });
                
            } catch (error) {
                console.error('Error loading nodes:', error);
            }
        }
        
        function configureNode(nodeId) {
            // Open configuration dialog or navigate to config page
            alert(`Configure node ${nodeId}`);
        }
        
        function viewDetails(nodeId) {
            // Navigate to node details page
            alert(`View details for node ${nodeId}`);
        }
        
        // Load nodes on page load
        loadNodes();
        
        // Refresh every 30 seconds
        setInterval(loadNodes, 30000);
    </script>
</body>
</html>'''
    
    def _get_policies_html(self) -> str:
        """Generate policies management page HTML."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Policy Management - Aurora OS Enterprise</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem 2rem; }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .policy-card { background: white; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .policy-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
        .policy-name { font-size: 1.25rem; font-weight: 600; color: #333; }
        .policy-status { padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.875rem; }
        .status-active { background: #d4edda; color: #155724; }
        .status-inactive { background: #f8d7da; color: #721c24; }
        .btn { padding: 0.5rem 1rem; border: none; border-radius: 6px; cursor: pointer; font-size: 0.875rem; }
        .btn-primary { background: #667eea; color: white; }
        .btn-secondary { background: #6c757d; color: white; margin-left: 0.5rem; }
    </style>
</head>
<body>
    <header class="header">
        <h1>📋 Policy Management</h1>
        <p>Configure enterprise security policies</p>
    </header>
    
    <div class="container">
        <button class="btn btn-primary" onclick="createPolicy()">+ Create New Policy</button>
        
        <div id="policies-container">
            <!-- Policies will be loaded here -->
        </div>
    </div>
    
    <script>
        async function loadPolicies() {
            try {
                const response = await fetch('/api/policies');
                const data = await response.json();
                
                const container = document.getElementById('policies-container');
                container.innerHTML = '';
                
                data.policies.forEach(policy => {
                    const policyCard = document.createElement('div');
                    policyCard.className = 'policy-card';
                    
                    const statusClass = policy.active ? 'status-active' : 'status-inactive';
                    const statusText = policy.active ? 'Active' : 'Inactive';
                    
                    policyCard.innerHTML = `
                        <div class="policy-header">
                            <div class="policy-name">${policy.name}</div>
                            <div>
                                <span class="policy-status ${statusClass}">${statusText}</span>
                                <button class="btn btn-primary" onclick="editPolicy('${policy.id}')">Edit</button>
                                <button class="btn btn-secondary" onclick="deployPolicy('${policy.id}')">Deploy</button>
                            </div>
                        </div>
                        <p>${policy.description}</p>
                        <p><strong>Compliance Level:</strong> ${policy.compliance_level}</p>
                        <p><strong>Target Nodes:</strong> ${policy.target_nodes.length} nodes</p>
                        <p><strong>Created:</strong> ${new Date(policy.created_at).toLocaleString()}</p>
                    `;
                    
                    container.appendChild(policyCard);
                });
                
            } catch (error) {
                console.error('Error loading policies:', error);
            }
        }
        
        function createPolicy() {
            alert('Open policy creation dialog');
        }
        
        function editPolicy(policyId) {
            alert(`Edit policy ${policyId}`);
        }
        
        function deployPolicy(policyId) {
            alert(`Deploy policy ${policyId}`);
        }
        
        // Load policies on page load
        loadPolicies();
        
        // Refresh every 60 seconds
        setInterval(loadPolicies, 60000);
    </script>
</body>
</html>'''
    
    def _get_monitoring_html(self) -> str:
        """Generate monitoring page HTML."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitoring - Aurora OS Enterprise</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem 2rem; }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
        .metric-card { background: white; border-radius: 12px; padding: 1.5rem; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .metric-value { font-size: 2.5rem; font-weight: bold; color: #667eea; margin-bottom: 0.5rem; }
        .metric-label { color: #666; font-size: 0.875rem; }
        .chart-container { background: white; border-radius: 12px; padding: 1.5rem; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .chart-placeholder { height: 300px; background: #f8f9fa; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #666; }
    </style>
</head>
<body>
    <header class="header">
        <h1>📈 System Monitoring</h1>
        <p>Real-time performance and health metrics</p>
    </header>
    
    <div class="container">
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value" id="cpu-usage">23%</div>
                <div class="metric-label">Average CPU Usage</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="memory-usage">67%</div>
                <div class="metric-label">Average Memory Usage</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="response-time">87ms</div>
                <div class="metric-label">Average Response Time</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="uptime">99.9%</div>
                <div class="metric-label">System Uptime</div>
            </div>
        </div>
        
        <div class="chart-container">
            <h3>Performance Overview</h3>
            <div class="chart-placeholder">
                📊 Real-time performance charts would be displayed here
            </div>
        </div>
    </div>
    
    <script>
        // Simulate real-time updates
        function updateMetrics() {
            document.getElementById('cpu-usage').textContent = Math.floor(Math.random() * 40 + 10) + '%';
            document.getElementById('memory-usage').textContent = Math.floor(Math.random() * 30 + 50) + '%';
            document.getElementById('response-time').textContent = Math.floor(Math.random() * 50 + 50) + 'ms';
        }
        
        // Update metrics every 5 seconds
        setInterval(updateMetrics, 5000);
    </script>
</body>
</html>'''
    
    def _get_compliance_html(self) -> str:
        """Generate compliance page HTML."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Compliance - Aurora OS Enterprise</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem 2rem; }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .compliance-overview { display: grid; grid-template-columns: 2fr 1fr; gap: 2rem; margin-bottom: 2rem; }
        .compliance-score { background: white; border-radius: 12px; padding: 2rem; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .score-value { font-size: 4rem; font-weight: bold; color: #4CAF50; margin-bottom: 0.5rem; }
        .compliance-details { background: white; border-radius: 12px; padding: 1.5rem; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .compliance-table { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 1rem; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-weight: 600; }
        .compliance-good { color: #4CAF50; font-weight: 500; }
        .compliance-warning { color: #FF9800; font-weight: 500; }
        .compliance-error { color: #f44336; font-weight: 500; }
    </style>
</head>
<body>
    <header class="header">
        <h1>✅ Compliance Status</h1>
        <p>Regulatory compliance and audit information</p>
    </header>
    
    <div class="container">
        <div class="compliance-overview">
            <div class="compliance-details">
                <h3>Compliance Frameworks</h3>
                <div style="margin: 1rem 0;">
                    <div style="margin-bottom: 0.5rem;">✅ FIPS 140-2: Compliant</div>
                    <div style="margin-bottom: 0.5rem;">✅ GDPR: Compliant</div>
                    <div style="margin-bottom: 0.5rem;">⚠️ HIPAA: Partial Compliance</div>
                    <div style="margin-bottom: 0.5rem;">📋 SOX: In Progress</div>
                </div>
                <p><strong>Last Audit:</strong> December 1, 2024</p>
                <p><strong>Next Audit:</strong> March 1, 2025</p>
            </div>
            <div class="compliance-score">
                <div class="score-value">95%</div>
                <div>Overall Compliance Score</div>
                <div style="margin-top: 1rem; color: #666;">
                    <div>High Risk: 0</div>
                    <div>Medium Risk: 2</div>
                    <div>Low Risk: 8</div>
                </div>
            </div>
        </div>
        
        <div class="compliance-table">
            <table>
                <thead>
                    <tr>
                        <th>Node</th>
                        <th>Compliance Level</th>
                        <th>Status</th>
                        <th>Last Check</th>
                        <th>Score</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="compliance-tbody">
                    <!-- Compliance data will be loaded here -->
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        async function loadComplianceData() {
            try {
                const response = await fetch('/api/compliance');
                const data = await response.json();
                
                const tbody = document.getElementById('compliance-tbody');
                tbody.innerHTML = '';
                
                data.compliance.forEach(node => {
                    const row = document.createElement('tr');
                    
                    let statusClass = 'compliance-good';
                    let statusText = 'Compliant';
                    
                    if (node.score < 80) {
                        statusClass = 'compliance-error';
                        statusText = 'Non-Compliant';
                    } else if (node.score < 95) {
                        statusClass = 'compliance-warning';
                        statusText = 'Warning';
                    }
                    
                    row.innerHTML = `
                        <td><strong>${node.node_name}</strong></td>
                        <td>${node.compliance_level.toUpperCase()}</td>
                        <td class="${statusClass}">${statusText}</td>
                        <td>${new Date(node.last_check).toLocaleString()}</td>
                        <td>${node.score}%</td>
                        <td>
                            <button onclick="viewComplianceDetails('${node.node_id}')" style="padding: 0.25rem 0.5rem;">Details</button>
                        </td>
                    `;
                    
                    tbody.appendChild(row);
                });
                
            } catch (error) {
                console.error('Error loading compliance data:', error);
            }
        }
        
        function viewComplianceDetails(nodeId) {
            alert(`View compliance details for node ${nodeId}`);
        }
        
        // Load compliance data on page load
        loadComplianceData();
        
        // Refresh every 60 seconds
        setInterval(loadComplianceData, 60000);
    </script>
</body>
</html>'''
    
    async def start_server(self):
        """Start the enterprise console server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        logger.info(f"Aurora Enterprise Console started on http://0.0.0.0:{self.port}")
        logger.info(f"Default login: admin / admin123")
        
        # Keep server running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down Aurora Enterprise Console")
        finally:
            await runner.cleanup()

def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    console = AuroraEnterpriseConsole()
    asyncio.run(console.start_server())

if __name__ == "__main__":
    main()