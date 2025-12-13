"""
Aurora OS Enterprise Management Console - Web Interface
Web-based management interface for Aurora OS enterprise deployment
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import aiohttp
from aiohttp import web, WSMsgType
import aiohttp_cors
import jwt
import bcrypt

class UserRole(Enum):
    """User roles"""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    DEVELOPER = "developer"

class PageType(Enum):
    """Console page types"""
    DASHBOARD = "dashboard"
    CLUSTER = "cluster"
    NODES = "nodes"
    MONITORING = "monitoring"
    USERS = "users"
    SETTINGS = "settings"
    LOGS = "logs"
    ALERTS = "alerts"

@dataclass
class UserInfo:
    """User information"""
    id: str
    username: str
    email: str
    role: UserRole
    created_at: datetime
    last_login: Optional[datetime]
    active: bool
    permissions: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['role'] = self.role.value
        data['created_at'] = self.created_at.isoformat()
        data['last_login'] = self.last_login.isoformat() if self.last_login else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserInfo':
        """Create from dictionary"""
        data['role'] = UserRole(data['role'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['last_login'] = datetime.fromisoformat(data['last_login']) if data['last_login'] else None
        return cls(**data)

class AuroraManagementConsole:
    """Aurora OS Enterprise Management Console"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8443):
        self.logger = logging.getLogger(__name__)
        self.host = host
        self.port = port
        
        # Authentication
        self.jwt_secret = "aurora-management-secret-key"
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.users: Dict[str, UserInfo] = {}
        
        # Web server
        self.app = web.Application()
        self.runner = None
        self.site = None
        
        # WebSocket connections for real-time updates
        self.websocket_connections: List[web.WebSocketResponse] = []
        
        # Console state
        self.dashboard_data = {}
        self.cluster_status = {}
        self.monitoring_data = {}
        self.alert_data = []
        
        # Initialize default admin user
        self._initialize_default_user()
        
        # Setup routes and middleware
        self._setup_routes()
        self._setup_middleware()
    
    def _initialize_default_user(self):
        """Initialize default admin user"""
        admin_user = UserInfo(
            id="admin-001",
            username="admin",
            email="admin@auroraos.local",
            role=UserRole.ADMIN,
            created_at=datetime.now(),
            last_login=None,
            active=True,
            permissions=["*"]  # All permissions
        )
        
        # Hash password (default: aurora123)
        password_hash = bcrypt.hashpw("aurora123".encode('utf-8'), bcrypt.gensalt())
        admin_user.password_hash = password_hash.decode('utf-8')
        
        self.users[admin_user.id] = admin_user
        self.logger.info("Default admin user initialized")
    
    def _setup_routes(self):
        """Setup web routes"""
        # Static files and main console
        self.app.router.add_get('/', self.serve_console)
        self.app.router.add_get('/dashboard', self.serve_dashboard)
        self.app.router.add_get('/cluster', self.serve_cluster_page)
        self.app.router.add_get('/nodes', self.serve_nodes_page)
        self.app.router.add_get('/monitoring', self.serve_monitoring_page)
        
        # API endpoints
        self.app.router.add_post('/api/auth/login', self.api_login)
        self.app.router.add_post('/api/auth/logout', self.api_logout)
        self.app.router.add_get('/api/dashboard/data', self.api_dashboard_data)
        self.app.router.add_get('/api/cluster/status', self.api_cluster_status)
        self.app.router.add_get('/api/nodes/list', self.api_nodes_list)
        self.app.router.add_get('/api/monitoring/metrics', self.api_monitoring_metrics)
        self.app.router.add_get('/api/alerts', self.api_alerts)
        
        # WebSocket for real-time updates
        self.app.router.add_get('/ws/updates', self.websocket_updates)
    
    def _setup_middleware(self):
        """Setup CORS and security middleware"""
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
    
    async def start(self):
        """Start the management console"""
        self.logger.info(f"Starting Aurora Management Console on {self.host}:{self.port}")
        
        # Create web server runner
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        # Create site
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        
        # Start background data collection
        asyncio.create_task(self._collect_dashboard_data())
        asyncio.create_task(self._collect_cluster_status())
        asyncio.create_task(self._collect_monitoring_data())
        asyncio.create_task(self._process_alerts())
        
        self.logger.info(f"Aurora Management Console started at https://{self.host}:{self.port}")
    
    async def stop(self):
        """Stop the management console"""
        self.logger.info("Stopping Aurora Management Console")
        
        if self.site:
            await self.site.stop()
        
        if self.runner:
            await self.runner.cleanup()
        
        # Close WebSocket connections
        for ws in self.websocket_connections:
            await ws.close()
        
        self.logger.info("Aurora Management Console stopped")
    
    async def serve_console(self, request: web.Request) -> web.Response:
        """Serve main console page"""
        return web.Response(text=self._generate_console_html(), content_type='text/html')
    
    async def serve_dashboard(self, request: web.Request) -> web.Response:
        """Serve dashboard page"""
        return web.Response(text=self._generate_dashboard_html(), content_type='text/html')
    
    async def serve_cluster_page(self, request: web.Request) -> web.Response:
        """Serve cluster management page"""
        return web.Response(text=self._generate_cluster_html(), content_type='text/html')
    
    async def serve_nodes_page(self, request: web.Request) -> web.Response:
        """Serve nodes management page"""
        return web.Response(text=self._generate_nodes_html(), content_type='text/html')
    
    async def serve_monitoring_page(self, request: web.Request) -> web.Response:
        """Serve monitoring page"""
        return web.Response(text=self._generate_monitoring_html(), content_type='text/html')
    
    # API Methods
    async def api_login(self, request: web.Request) -> web.Response:
        """API login endpoint"""
        try:
            data = await request.json()
            username = data.get('username')
            password = data.get('password')
            
            # Find user
            user = None
            for u in self.users.values():
                if u.username == username:
                    user = u
                    break
            
            if not user:
                return web.json_response({'error': 'Invalid credentials'}, status=401)
            
            # Verify password
            if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                return web.json_response({'error': 'Invalid credentials'}, status=401)
            
            # Generate JWT token
            token = jwt.encode({
                'user_id': user.id,
                'username': user.username,
                'role': user.role.value,
                'exp': datetime.utcnow() + timedelta(hours=24)
            }, self.jwt_secret, algorithm='HS256')
            
            # Update last login
            user.last_login = datetime.now()
            
            # Store session
            session_id = str(uuid.uuid4())
            self.active_sessions[session_id] = {
                'user_id': user.id,
                'token': token,
                'created_at': datetime.now()
            }
            
            return web.json_response({
                'token': token,
                'user': user.to_dict(),
                'session_id': session_id
            })
            
        except Exception as e:
            self.logger.error(f"Login error: {e}")
            return web.json_response({'error': 'Login failed'}, status=500)
    
    async def api_logout(self, request: web.Request) -> web.Response:
        """API logout endpoint"""
        try:
            session_id = request.headers.get('X-Session-ID')
            if session_id and session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            return web.json_response({'success': True})
            
        except Exception as e:
            self.logger.error(f"Logout error: {e}")
            return web.json_response({'error': 'Logout failed'}, status=500)
    
    async def api_dashboard_data(self, request: web.Request) -> web.Response:
        """API endpoint for dashboard data"""
        if not await self._verify_session(request):
            return web.json_response({'error': 'Unauthorized'}, status=401)
        
        return web.json_response(self.dashboard_data)
    
    async def api_cluster_status(self, request: web.Request) -> web.Response:
        """API endpoint for cluster status"""
        if not await self._verify_session(request):
            return web.json_response({'error': 'Unauthorized'}, status=401)
        
        return web.json_response(self.cluster_status)
    
    async def api_nodes_list(self, request: web.Request) -> web.Response:
        """API endpoint for nodes list"""
        if not await self._verify_session(request):
            return web.json_response({'error': 'Unauthorized'}, status=401)
        
        # Mock nodes data
        nodes = [
            {
                'id': 'node-001',
                'name': 'Aurora-Node-1',
                'status': 'online',
                'cpu_usage': 45.2,
                'memory_usage': 67.8,
                'role': 'manager',
                'last_heartbeat': datetime.now().isoformat()
            },
            {
                'id': 'node-002',
                'name': 'Aurora-Node-2',
                'status': 'online',
                'cpu_usage': 23.1,
                'memory_usage': 54.3,
                'role': 'worker',
                'last_heartbeat': datetime.now().isoformat()
            }
        ]
        
        return web.json_response(nodes)
    
    async def api_monitoring_metrics(self, request: web.Request) -> web.Response:
        """API endpoint for monitoring metrics"""
        if not await self._verify_session(request):
            return web.json_response({'error': 'Unauthorized'}, status=401)
        
        return web.json_response(self.monitoring_data)
    
    async def api_alerts(self, request: web.Request) -> web.Response:
        """API endpoint for alerts"""
        if not await self._verify_session(request):
            return web.json_response({'error': 'Unauthorized'}, status=401)
        
        return web.json_response(self.alert_data)
    
    async def websocket_updates(self, request: web.Request) -> web.WebSocketResponse:
        """WebSocket endpoint for real-time updates"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websocket_connections.append(ws)
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    # Handle client messages if needed
                    pass
                elif msg.type == WSMsgType.ERROR:
                    self.logger.error(f'WebSocket error: {ws.exception()}')
        except Exception as e:
            self.logger.error(f"WebSocket error: {e}")
        finally:
            if ws in self.websocket_connections:
                self.websocket_connections.remove(ws)
        
        return ws
    
    async def _verify_session(self, request: web.Request) -> bool:
        """Verify user session"""
        try:
            token = request.headers.get('Authorization')
            if not token or not token.startswith('Bearer '):
                return False
            
            token = token.split(' ')[1]
            decoded = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            
            # Check if session exists
            for session in self.active_sessions.values():
                if session['token'] == token:
                    return True
            
            return False
            
        except Exception:
            return False
    
    # Background tasks
    async def _collect_dashboard_data(self):
        """Collect dashboard data periodically"""
        while True:
            try:
                self.dashboard_data = {
                    'cluster_health': 95.2,
                    'total_nodes': 12,
                    'active_nodes': 11,
                    'total_requests': 1542839,
                    'avg_response_time': 124.5,
                    'error_rate': 0.02,
                    'cpu_usage': 42.3,
                    'memory_usage': 68.7,
                    'storage_usage': 34.8,
                    'network_throughput': 1024.5,
                    'last_updated': datetime.now().isoformat()
                }
                
                # Send real-time update via WebSocket
                await self._broadcast_update({'type': 'dashboard', 'data': self.dashboard_data})
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error collecting dashboard data: {e}")
                await asyncio.sleep(5)
    
    async def _collect_cluster_status(self):
        """Collect cluster status periodically"""
        while True:
            try:
                self.cluster_status = {
                    'cluster_name': 'Aurora-Production',
                    'cluster_id': 'aurora-prod-001',
                    'status': 'healthy',
                    'leader_node': 'node-001',
                    'total_nodes': 12,
                    'active_nodes': 11,
                    'failed_nodes': 1,
                    'replication_factor': 3,
                    'consistency_level': 'quorum',
                    'last_election': '2024-12-13T10:30:00Z',
                    'uptime': '45d 12h 34m',
                    'version': '0.1.0',
                    'last_updated': datetime.now().isoformat()
                }
                
                await asyncio.sleep(60)  # Update every minute
                
            except Exception as e:
                self.logger.error(f"Error collecting cluster status: {e}")
                await asyncio.sleep(10)
    
    async def _collect_monitoring_data(self):
        """Collect monitoring data periodically"""
        while True:
            try:
                self.monitoring_data = {
                    'metrics': {
                        'cpu': {'usage': 42.3, 'load_1m': 1.2, 'load_5m': 1.5, 'load_15m': 1.8},
                        'memory': {'usage': 68.7, 'total': 32, 'available': 10, 'cached': 8},
                        'storage': {'usage': 34.8, 'total': 1000, 'free': 652},
                        'network': {'rx_bytes': 1048576, 'tx_bytes': 2097152, 'rx_packets': 1024, 'tx_packets': 2048}
                    },
                    'alerts': [
                        {'level': 'warning', 'message': 'High memory usage on node-003', 'timestamp': datetime.now().isoformat()},
                        {'level': 'info', 'message': 'Node node-005 joined cluster', 'timestamp': datetime.now().isoformat()}
                    ],
                    'last_updated': datetime.now().isoformat()
                }
                
                await asyncio.sleep(15)  # Update every 15 seconds
                
            except Exception as e:
                self.logger.error(f"Error collecting monitoring data: {e}")
                await asyncio.sleep(5)
    
    async def _process_alerts(self):
        """Process and generate alerts"""
        while True:
            try:
                # Simulate alert generation
                if len(self.alert_data) > 100:
                    self.alert_data = self.alert_data[-50:]  # Keep last 50 alerts
                
                await asyncio.sleep(120)  # Check every 2 minutes
                
            except Exception as e:
                self.logger.error(f"Error processing alerts: {e}")
                await asyncio.sleep(30)
    
    async def _broadcast_update(self, message: Dict[str, Any]):
        """Broadcast update to all WebSocket connections"""
        if not self.websocket_connections:
            return
        
        message_str = json.dumps(message)
        
        # Create tasks for all connections
        tasks = []
        for ws in self.websocket_connections.copy():
            if ws.closed:
                self.websocket_connections.remove(ws)
                continue
            
            tasks.append(ws.send_str(message_str))
        
        # Send to all connections concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    # HTML Generation Methods
    def _generate_console_html(self) -> str:
        """Generate main console HTML"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aurora OS Management Console</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .aurora-gradient {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .glass-effect {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .metric-card {
            transition: all 0.3s ease;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        }
    </style>
</head>
<body class="bg-gray-100">
    <!-- Header -->
    <header class="aurora-gradient text-white shadow-lg">
        <div class="container mx-auto px-6 py-4">
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-4">
                    <i class="fas fa-rocket text-2xl"></i>
                    <h1 class="text-2xl font-bold">Aurora OS Management Console</h1>
                </div>
                <div class="flex items-center space-x-6">
                    <span id="connection-status" class="flex items-center">
                        <span class="w-3 h-3 bg-green-400 rounded-full mr-2 animate-pulse"></span>
                        Connected
                    </span>
                    <div class="flex items-center space-x-3">
                        <i class="fas fa-user-circle text-xl"></i>
                        <span id="user-info">Admin</span>
                        <button onclick="logout()" class="bg-red-500 hover:bg-red-600 px-3 py-1 rounded text-sm">
                            Logout
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </header>

    <!-- Navigation -->
    <nav class="bg-white shadow-md">
        <div class="container mx-auto px-6">
            <div class="flex space-x-8">
                <a href="/dashboard" class="py-4 px-6 text-gray-700 hover:text-purple-600 border-b-2 border-purple-600 font-medium">
                    <i class="fas fa-tachometer-alt mr-2"></i>Dashboard
                </a>
                <a href="/cluster" class="py-4 px-6 text-gray-700 hover:text-purple-600 border-b-2 border-transparent hover:border-purple-600">
                    <i class="fas fa-network-wired mr-2"></i>Cluster
                </a>
                <a href="/nodes" class="py-4 px-6 text-gray-700 hover:text-purple-600 border-b-2 border-transparent hover:border-purple-600">
                    <i class="fas fa-server mr-2"></i>Nodes
                </a>
                <a href="/monitoring" class="py-4 px-6 text-gray-700 hover:text-purple-600 border-b-2 border-transparent hover:border-purple-600">
                    <i class="fas fa-chart-line mr-2"></i>Monitoring
                </a>
                <a href="/users" class="py-4 px-6 text-gray-700 hover:text-purple-600 border-b-2 border-transparent hover:border-purple-600">
                    <i class="fas fa-users mr-2"></i>Users
                </a>
                <a href="/settings" class="py-4 px-6 text-gray-700 hover:text-purple-600 border-b-2 border-transparent hover:border-purple-600">
                    <i class="fas fa-cog mr-2"></i>Settings
                </a>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="container mx-auto px-6 py-8">
        <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
            <!-- Quick Stats -->
            <div class="lg:col-span-3">
                <h2 class="text-2xl font-bold mb-6">Cluster Overview</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                    <div class="metric-card bg-white rounded-lg shadow-md p-6">
                        <div class="flex items-center justify-between">
                            <div>
                                <p class="text-gray-500 text-sm">Cluster Health</p>
                                <p class="text-2xl font-bold text-green-600" id="cluster-health">95.2%</p>
                            </div>
                            <i class="fas fa-heartbeat text-green-500 text-2xl"></i>
                        </div>
                    </div>
                    
                    <div class="metric-card bg-white rounded-lg shadow-md p-6">
                        <div class="flex items-center justify-between">
                            <div>
                                <p class="text-gray-500 text-sm">Active Nodes</p>
                                <p class="text-2xl font-bold text-blue-600" id="active-nodes">11/12</p>
                            </div>
                            <i class="fas fa-server text-blue-500 text-2xl"></i>
                        </div>
                    </div>
                    
                    <div class="metric-card bg-white rounded-lg shadow-md p-6">
                        <div class="flex items-center justify-between">
                            <div>
                                <p class="text-gray-500 text-sm">CPU Usage</p>
                                <p class="text-2xl font-bold text-yellow-600" id="cpu-usage">42.3%</p>
                            </div>
                            <i class="fas fa-microchip text-yellow-500 text-2xl"></i>
                        </div>
                    </div>
                    
                    <div class="metric-card bg-white rounded-lg shadow-md p-6">
                        <div class="flex items-center justify-between">
                            <div>
                                <p class="text-gray-500 text-sm">Memory Usage</p>
                                <p class="text-2xl font-bold text-purple-600" id="memory-usage">68.7%</p>
                            </div>
                            <i class="fas fa-memory text-purple-500 text-2xl"></i>
                        </div>
                    </div>
                </div>

                <!-- Charts Section -->
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div class="bg-white rounded-lg shadow-md p-6">
                        <h3 class="text-lg font-semibold mb-4">Resource Usage</h3>
                        <canvas id="resource-chart" height="200"></canvas>
                    </div>
                    
                    <div class="bg-white rounded-lg shadow-md p-6">
                        <h3 class="text-lg font-semibold mb-4">Request Volume</h3>
                        <canvas id="request-chart" height="200"></canvas>
                    </div>
                </div>
            </div>

            <!-- Sidebar -->
            <div class="lg:col-span-1">
                <!-- Recent Alerts -->
                <div class="bg-white rounded-lg shadow-md p-6 mb-6">
                    <h3 class="text-lg font-semibold mb-4">Recent Alerts</h3>
                    <div id="alerts-list" class="space-y-3">
                        <!-- Alerts will be populated here -->
                    </div>
                </div>

                <!-- Quick Actions -->
                <div class="bg-white rounded-lg shadow-md p-6">
                    <h3 class="text-lg font-semibold mb-4">Quick Actions</h3>
                    <div class="space-y-2">
                        <button class="w-full bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded">
                            <i class="fas fa-plus mr-2"></i>Add Node
                        </button>
                        <button class="w-full bg-green-500 hover:bg-green-600 text-white py-2 px-4 rounded">
                            <i class="fas fa-sync mr-2"></i>Sync Cluster
                        </button>
                        <button class="w-full bg-yellow-500 hover:bg-yellow-600 text-white py-2 px-4 rounded">
                            <i class="fas fa-download mr-2"></i>Export Logs
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <script>
        // WebSocket connection for real-time updates
        const ws = new WebSocket(`ws://${window.location.host}/ws/updates`);
        
        ws.onmessage = function(event) {
            const message = JSON.parse(event.data);
            
            if (message.type === 'dashboard') {
                updateDashboard(message.data);
            }
        };
        
        function updateDashboard(data) {
            document.getElementById('cluster-health').textContent = data.cluster_health + '%';
            document.getElementById('active-nodes').textContent = `${data.active_nodes}/${data.total_nodes}`;
            document.getElementById('cpu-usage').textContent = data.cpu_usage + '%';
            document.getElementById('memory-usage').textContent = data.memory_usage + '%';
        }
        
        function logout() {
            window.location.href = '/api/auth/logout';
        }
        
        // Initialize charts
        const resourceCtx = document.getElementById('resource-chart').getContext('2d');
        const resourceChart = new Chart(resourceCtx, {
            type: 'line',
            data: {
                labels: ['1m', '2m', '3m', '4m', '5m'],
                datasets: [{
                    label: 'CPU',
                    data: [40, 42, 41, 43, 42],
                    borderColor: 'rgb(255, 206, 86)',
                    tension: 0.1
                }, {
                    label: 'Memory',
                    data: [65, 68, 67, 69, 68],
                    borderColor: 'rgb(153, 102, 255)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
        
        const requestCtx = document.getElementById('request-chart').getContext('2d');
        const requestChart = new Chart(requestCtx, {
            type: 'bar',
            data: {
                labels: ['1h', '2h', '3h', '4h', '5h'],
                datasets: [{
                    label: 'Requests',
                    data: [1200, 1900, 1500, 2100, 1800],
                    backgroundColor: 'rgba(102, 126, 234, 0.5)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
        
        // Load initial data
        fetch('/api/dashboard/data')
            .then(response => response.json())
            .then(data => updateDashboard(data));
            
        // Load alerts
        fetch('/api/alerts')
            .then(response => response.json())
            .then(alerts => {
                const alertsList = document.getElementById('alerts-list');
                alerts.forEach(alert => {
                    const alertDiv = document.createElement('div');
                    alertDiv.className = `p-3 rounded ${alert.level === 'warning' ? 'bg-yellow-50 border-l-4 border-yellow-400' : 'bg-blue-50 border-l-4 border-blue-400'}`;
                    alertDiv.innerHTML = `
                        <p class="text-sm font-medium">${alert.message}</p>
                        <p class="text-xs text-gray-500">${new Date(alert.timestamp).toLocaleString()}</p>
                    `;
                    alertsList.appendChild(alertDiv);
                });
            });
    </script>
</body>
</html>
        """
    
    def _generate_dashboard_html(self) -> str:
        """Generate dashboard page HTML"""
        return self._generate_console_html()  # Use main console for now
    
    def _generate_cluster_html(self) -> str:
        """Generate cluster management page HTML"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cluster Management - Aurora OS</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-gray-100">
    <div class="container mx-auto px-6 py-8">
        <h1 class="text-3xl font-bold mb-8">Cluster Management</h1>
        
        <div class="bg-white rounded-lg shadow-md p-6">
            <h2 class="text-xl font-semibold mb-4">Cluster Status</h2>
            <div id="cluster-status">
                <!-- Cluster status will be loaded here -->
            </div>
        </div>
    </div>
    
    <script>
        fetch('/api/cluster/status')
            .then(response => response.json())
            .then(data => {
                document.getElementById('cluster-status').innerHTML = `
                    <div class="grid grid-cols-2 gap-4">
                        <div><strong>Cluster Name:</strong> ${data.cluster_name}</div>
                        <div><strong>Status:</strong> <span class="text-green-600">${data.status}</span></div>
                        <div><strong>Total Nodes:</strong> ${data.total_nodes}</div>
                        <div><strong>Active Nodes:</strong> ${data.active_nodes}</div>
                    </div>
                `;
            });
    </script>
</body>
</html>
        """
    
    def _generate_nodes_html(self) -> str:
        """Generate nodes management page HTML"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Node Management - Aurora OS</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-gray-100">
    <div class="container mx-auto px-6 py-8">
        <h1 class="text-3xl font-bold mb-8">Node Management</h1>
        
        <div class="bg-white rounded-lg shadow-md p-6">
            <h2 class="text-xl font-semibold mb-4">Cluster Nodes</h2>
            <div id="nodes-list">
                <!-- Nodes will be loaded here -->
            </div>
        </div>
    </div>
    
    <script>
        fetch('/api/nodes/list')
            .then(response => response.json())
            .then(nodes => {
                const nodesList = document.getElementById('nodes-list');
                nodesList.innerHTML = nodes.map(node => `
                    <div class="border rounded-lg p-4 mb-4">
                        <div class="flex justify-between items-center">
                            <div>
                                <h3 class="font-semibold">${node.name}</h3>
                                <p class="text-sm text-gray-600">ID: ${node.id}</p>
                            </div>
                            <div class="text-right">
                                <span class="px-2 py-1 rounded text-sm ${node.status === 'online' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
                                    ${node.status}
                                </span>
                            </div>
                        </div>
                        <div class="mt-2 grid grid-cols-2 gap-4 text-sm">
                            <div>CPU: ${node.cpu_usage}%</div>
                            <div>Memory: ${node.memory_usage}%</div>
                        </div>
                    </div>
                `).join('');
            });
    </script>
</body>
</html>
        """
    
    def _generate_monitoring_html(self) -> str:
        """Generate monitoring page HTML"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Monitoring - Aurora OS</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-gray-100">
    <div class="container mx-auto px-6 py-8">
        <h1 class="text-3xl font-bold mb-8">System Monitoring</h1>
        
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div class="bg-white rounded-lg shadow-md p-6">
                <h2 class="text-xl font-semibold mb-4">CPU Usage</h2>
                <canvas id="cpu-chart"></canvas>
            </div>
            
            <div class="bg-white rounded-lg shadow-md p-6">
                <h2 class="text-xl font-semibold mb-4">Memory Usage</h2>
                <canvas id="memory-chart"></canvas>
            </div>
        </div>
    </div>
    
    <script>
        // Initialize monitoring charts
        const cpuCtx = document.getElementById('cpu-chart').getContext('2d');
        const cpuChart = new Chart(cpuCtx, {
            type: 'line',
            data: {
                labels: Array.from({length: 20}, (_, i) => `${i}s`),
                datasets: [{
                    label: 'CPU Usage %',
                    data: Array.from({length: 20}, () => Math.random() * 100),
                    borderColor: 'rgb(255, 99, 132)',
                    tension: 0.1
                }]
            }
        });
        
        const memoryCtx = document.getElementById('memory-chart').getContext('2d');
        const memoryChart = new Chart(memoryCtx, {
            type: 'line',
            data: {
                labels: Array.from({length: 20}, (_, i) => `${i}s`),
                datasets: [{
                    label: 'Memory Usage %',
                    data: Array.from({length: 20}, () => Math.random() * 100),
                    borderColor: 'rgb(54, 162, 235)',
                    tension: 0.1
                }]
            }
        });
    </script>
</body>
</html>
        """

# Test and startup function
async def start_management_console():
    """Start the Aurora Management Console"""
    console = AuroraManagementConsole()
    await console.start()
    
    try:
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await console.stop()

if __name__ == "__main__":
    asyncio.run(start_management_console())