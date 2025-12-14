"""
Aurora OS Enterprise Management Dashboard
Real-time monitoring and control interface for enterprise deployments
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
import aiohttp
from aiohttp import web
import aiofiles
from pathlib import Path
import yaml
from collections import defaultdict, deque

class DashboardTheme(Enum):
    """Dashboard themes"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class DashboardAlert:
    """Dashboard alert notification"""
    id: str
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime
    source: str
    acknowledged: bool = False
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DashboardConfig:
    """Dashboard configuration"""
    title: str = "Aurora OS Enterprise Dashboard"
    refresh_interval: int = 5
    max_history_points: int = 1000
    theme: DashboardTheme = DashboardTheme.DARK
    enable_notifications: bool = True
    enable_auto_refresh: bool = True
    data_retention_days: int = 30

class EnterpriseDashboard:
    """Enterprise management dashboard with real-time monitoring"""
    
    def __init__(self, config: DashboardConfig):
        self.config = config
        self.metrics_history = defaultdict(lambda: deque(maxlen=config.max_history_points))
        self.alerts: List[DashboardAlert] = []
        self.connected_clients = set()
        self.is_running = False
        
        # Data sources
        self.cluster_orchestrator = None
        self.load_balancer = None
        self.monitoring_system = None
        
        # Dashboard components
        self.websocket_handler = None
        self.api_server = None
        
        self.logger = logging.getLogger(__name__)
        
        # File paths
        self.dashboard_dir = Path("/var/lib/aurora/dashboard")
        self.dashboard_dir.mkdir(parents=True, exist_ok=True)

    async def initialize(self, 
                        cluster_orchestrator=None,
                        load_balancer=None,
                        monitoring_system=None) -> None:
        """Initialize dashboard with data sources"""
        self.cluster_orchestrator = cluster_orchestrator
        self.load_balancer = load_balancer
        self.monitoring_system = monitoring_system
        
        self.logger.info("Dashboard initialized with data sources")

    async def start_dashboard(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        """Start the dashboard web server"""
        self.logger.info(f"Starting dashboard on {host}:{port}")
        
        # Create web application
        app = web.Application()
        
        # Setup routes
        app.router.add_get("/", self.serve_dashboard)
        app.router.add_get("/api/dashboard/data", self.get_dashboard_data)
        app.router.add_get("/api/dashboard/metrics", self.get_metrics_data)
        app.router.add_get("/api/dashboard/alerts", self.get_alerts)
        app.router.add_post("/api/dashboard/alerts/{alert_id}/acknowledge", self.acknowledge_alert)
        app.router.add_post("/api/dashboard/alerts/{alert_id}/resolve", self.resolve_alert)
        app.router.add_get("/ws", self.websocket_handler_function)
        
        # Static files
        app.router.add_static("/static/", self.dashboard_dir / "static")
        
        # Start background tasks
        asyncio.create_task(self.data_collection_loop())
        asyncio.create_task(self.alert_processing_loop())
        
        self.is_running = True
        
        # Start server
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        self.logger.info(f"Dashboard started successfully at http://{host}:{port}")

    async def stop_dashboard(self) -> None:
        """Stop the dashboard"""
        self.is_running = False
        self.logger.info("Dashboard stopped")

    async def serve_dashboard(self, request: web.Request) -> web.Response:
        """Serve the main dashboard HTML"""
        html_content = await self.generate_dashboard_html()
        return web.Response(text=html_content, content_type="text/html")

    async def generate_dashboard_html(self) -> str:
        """Generate the dashboard HTML"""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.config.title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ font-family: 'Inter', sans-serif; }}
        .dark {{ background: #1a202c; color: #e2e8f0; }}
        .metric-card {{ 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            transition: transform 0.2s;
        }}
        .metric-card:hover {{ transform: translateY(-2px); }}
        .alert-{{{{level}}}} {{ 
            border-left: 4px solid var(--alert-color);
            background: var(--alert-bg);
        }}
        .status-healthy {{ color: #48bb78; }}
        .status-warning {{ color: #ed8936; }}
        .status-critical {{ color: #f56565; }}
    </style>
</head>
<body class="bg-gray-100 min-h-screen">
    <div class="container mx-auto px-4 py-8">
        <!-- Header -->
        <header class="mb-8">
            <h1 class="text-3xl font-bold text-gray-800 mb-2">{self.config.title}</h1>
            <p class="text-gray-600">Real-time monitoring and control</p>
        </header>

        <!-- Metrics Overview -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div class="metric-card text-white p-6 rounded-lg shadow-lg">
                <h3 class="text-lg font-semibold mb-2">Cluster Nodes</h3>
                <p class="text-3xl font-bold" id="cluster-nodes">-</p>
                <p class="text-sm opacity-75" id="cluster-status">Loading...</p>
            </div>
            
            <div class="metric-card text-white p-6 rounded-lg shadow-lg">
                <h3 class="text-lg font-semibold mb-2">CPU Usage</h3>
                <p class="text-3xl font-bold" id="cpu-usage">-</p>
                <p class="text-sm opacity-75" id="cpu-trend">Loading...</p>
            </div>
            
            <div class="metric-card text-white p-6 rounded-lg shadow-lg">
                <h3 class="text-lg font-semibold mb-2">Memory Usage</h3>
                <p class="text-3xl font-bold" id="memory-usage">-</p>
                <p class="text-sm opacity-75" id="memory-trend">Loading...</p>
            </div>
            
            <div class="metric-card text-white p-6 rounded-lg shadow-lg">
                <h3 class="text-lg font-semibold mb-2">Request Rate</h3>
                <p class="text-3xl font-bold" id="request-rate">-</p>
                <p class="text-sm opacity-75" id="request-trend">Loading...</p>
            </div>
        </div>

        <!-- Charts Section -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div class="bg-white p-6 rounded-lg shadow-lg">
                <h3 class="text-lg font-semibold mb-4">Resource Utilization</h3>
                <canvas id="resource-chart"></canvas>
            </div>
            
            <div class="bg-white p-6 rounded-lg shadow-lg">
                <h3 class="text-lg font-semibold mb-4">Request Metrics</h3>
                <canvas id="request-chart"></canvas>
            </div>
        </div>

        <!-- Cluster Status -->
        <div class="bg-white p-6 rounded-lg shadow-lg mb-8">
            <h3 class="text-lg font-semibold mb-4">Cluster Status</h3>
            <div id="cluster-status-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <!-- Cluster nodes will be populated here -->
            </div>
        </div>

        <!-- Alerts Section -->
        <div class="bg-white p-6 rounded-lg shadow-lg mb-8">
            <h3 class="text-lg font-semibold mb-4">Recent Alerts</h3>
            <div id="alerts-container">
                <!-- Alerts will be populated here -->
            </div>
        </div>

        <!-- Control Panel -->
        <div class="bg-white p-6 rounded-lg shadow-lg">
            <h3 class="text-lg font-semibold mb-4">Control Panel</h3>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <button onclick="scaleCluster('up')" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
                    Scale Up
                </button>
                <button onclick="scaleCluster('down')" class="bg-yellow-500 text-white px-4 py-2 rounded hover:bg-yellow-600">
                    Scale Down
                </button>
                <button onclick="refreshData()" class="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600">
                    Refresh Data
                </button>
            </div>
        </div>
    </div>

    <script>
        // WebSocket connection for real-time updates
        const ws = new WebSocket(`ws://${{window.location.host}}/ws`);
        
        ws.onmessage = function(event) {{
            const data = JSON.parse(event.data);
            updateDashboard(data);
        }};
        
        // Initialize charts
        const resourceChart = new Chart(document.getElementById('resource-chart'), {{
            type: 'line',
            data: {{
                labels: [],
                datasets: [
                    {{
                        label: 'CPU Usage %',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    }},
                    {{
                        label: 'Memory Usage %',
                        data: [],
                        borderColor: 'rgb(255, 99, 132)',
                        tension: 0.1
                    }}
                ]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100
                    }}
                }}
            }}
        }});
        
        const requestChart = new Chart(document.getElementById('request-chart'), {{
            type: 'line',
            data: {{
                labels: [],
                datasets: [
                    {{
                        label: 'Requests/sec',
                        data: [],
                        borderColor: 'rgb(54, 162, 235)',
                        tension: 0.1
                    }},
                    {{
                        label: 'Response Time (ms)',
                        data: [],
                        borderColor: 'rgb(255, 206, 86)',
                        tension: 0.1,
                        yAxisID: 'y1'
                    }}
                ]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        type: 'linear',
                        display: true,
                        position: 'left',
                    }},
                    y1: {{
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: {{
                            drawOnChartArea: false,
                        }},
                    }}
                }}
            }}
        }});
        
        // Update dashboard with new data
        function updateDashboard(data) {{
            // Update metrics
            document.getElementById('cluster-nodes').textContent = data.cluster_metrics?.total_nodes || '-';
            document.getElementById('cpu-usage').textContent = data.cluster_metrics?.cpu_utilization?.toFixed(1) + '%' || '-';
            document.getElementById('memory-usage').textContent = data.cluster_metrics?.memory_utilization?.toFixed(1) + '%' || '-';
            document.getElementById('request-rate').textContent = (data.cluster_metrics?.request_rate || 0).toFixed(1);
            
            // Update charts
            updateCharts(data);
            
            // Update cluster status
            updateClusterStatus(data.cluster_nodes || []);
            
            // Update alerts
            updateAlerts(data.alerts || []);
        }}
        
        function updateCharts(data) {{
            const timestamp = new Date().toLocaleTimeString();
            
            // Update resource chart
            if (resourceChart.data.labels.length > 20) {{
                resourceChart.data.labels.shift();
                resourceChart.data.datasets[0].data.shift();
                resourceChart.data.datasets[1].data.shift();
            }}
            
            resourceChart.data.labels.push(timestamp);
            resourceChart.data.datasets[0].data.push(data.cluster_metrics?.cpu_utilization || 0);
            resourceChart.data.datasets[1].data.push(data.cluster_metrics?.memory_utilization || 0);
            resourceChart.update();
            
            // Update request chart
            if (requestChart.data.labels.length > 20) {{
                requestChart.data.labels.shift();
                requestChart.data.datasets[0].data.shift();
                requestChart.data.datasets[1].data.shift();
            }}
            
            requestChart.data.labels.push(timestamp);
            requestChart.data.datasets[0].data.push(data.cluster_metrics?.request_rate || 0);
            requestChart.data.datasets[1].data.push(data.cluster_metrics?.response_time || 0);
            requestChart.update();
        }}
        
        function updateClusterStatus(nodes) {{
            const container = document.getElementById('cluster-status-grid');
            container.innerHTML = '';
            
            nodes.forEach(node => {{
                const nodeCard = document.createElement('div');
                nodeCard.className = 'border rounded-lg p-4';
                nodeCard.innerHTML = `
                    <h4 class="font-semibold">${{node.name || node.id}}</h4>
                    <p class="text-sm text-gray-600">Status: <span class="status-${{node.status}}">${{node.status}}</span></p>
                    <p class="text-sm">CPU: ${{node.cpu_utilization?.toFixed(1) || 0}}%</p>
                    <p class="text-sm">Memory: ${{node.memory_utilization?.toFixed(1) || 0}}%</p>
                    <p class="text-sm">Connections: ${{node.current_connections || 0}}</p>
                `;
                container.appendChild(nodeCard);
            }});
        }}
        
        function updateAlerts(alerts) {{
            const container = document.getElementById('alerts-container');
            container.innerHTML = '';
            
            if (alerts.length === 0) {{
                container.innerHTML = '<p class="text-gray-500">No active alerts</p>';
                return;
            }}
            
            alerts.slice(0, 5).forEach(alert => {{
                const alertDiv = document.createElement('div');
                alertDiv.className = `alert-${{alert.level}} p-4 mb-2 rounded border`;
                alertDiv.innerHTML = `
                    <div class="flex justify-between items-start">
                        <div>
                            <h4 class="font-semibold">${{alert.title}}</h4>
                            <p class="text-sm">${{alert.message}}</p>
                            <p class="text-xs text-gray-500">${{new Date(alert.timestamp).toLocaleString()}}</p>
                        </div>
                        <div class="flex space-x-2">
                            ${{!alert.acknowledged ? `<button onclick="acknowledgeAlert('${{alert.id}}')" class="text-xs bg-yellow-500 text-white px-2 py-1 rounded">Acknowledge</button>` : ''}}
                            ${{!alert.resolved ? `<button onclick="resolveAlert('${{alert.id}}')" class="text-xs bg-green-500 text-white px-2 py-1 rounded">Resolve</button>` : ''}}
                        </div>
                    </div>
                `;
                container.appendChild(alertDiv);
            }});
        }}
        
        // Control functions
        async function scaleCluster(direction) {{
            try {{
                const response = await fetch(`/api/dashboard/scale/${{direction}}`, {{
                    method: 'POST'
                }});
                const result = await response.json();
                console.log('Scale result:', result);
            }} catch (error) {{
                console.error('Scale error:', error);
            }}
        }}
        
        async function acknowledgeAlert(alertId) {{
            try {{
                const response = await fetch(`/api/dashboard/alerts/${{alertId}}/acknowledge`, {{
                    method: 'POST'
                }});
                const result = await response.json();
                refreshData();
            }} catch (error) {{
                console.error('Acknowledge error:', error);
            }}
        }}
        
        async function resolveAlert(alertId) {{
            try {{
                const response = await fetch(`/api/dashboard/alerts/${{alertId}}/resolve`, {{
                    method: 'POST'
                }});
                const result = await response.json();
                refreshData();
            }} catch (error) {{
                console.error('Resolve error:', error);
            }}
        }}
        
        async function refreshData() {{
            try {{
                const response = await fetch('/api/dashboard/data');
                const data = await response.json();
                updateDashboard(data);
            }} catch (error) {{
                console.error('Refresh error:', error);
            }}
        }}
        
        // Initial data load
        refreshData();
        
        // Auto-refresh
        if ({self.config.enable_auto_refresh}) {{
            setInterval(refreshData, {self.config.refresh_interval * 1000});
        }}
    </script>
</body>
</html>
        """

    async def get_dashboard_data(self, request: web.Request) -> web.Response:
        """Get comprehensive dashboard data"""
        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "cluster_metrics": await self.get_cluster_metrics(),
                "cluster_nodes": await self.get_cluster_nodes(),
                "load_balancer_stats": await self.get_load_balancer_stats(),
                "alerts": await self.get_active_alerts(),
                "system_info": await self.get_system_info()
            }
            
            return web.json_response(data)
            
        except Exception as e:
            self.logger.error(f"Failed to get dashboard data: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def get_cluster_metrics(self) -> Dict[str, Any]:
        """Get cluster performance metrics"""
        if self.cluster_orchestrator:
            try:
                # Get current metrics from orchestrator
                if hasattr(self.cluster_orchestrator, 'collect_cluster_metrics'):
                    metrics = await self.cluster_orchestrator.collect_cluster_metrics()
                    return asdict(metrics)
            except Exception as e:
                self.logger.error(f"Failed to get cluster metrics: {e}")
        
        # Return mock data if orchestrator not available
        return {
            "total_nodes": 5,
            "active_nodes": 5,
            "cpu_utilization": 65.5,
            "memory_utilization": 72.3,
            "network_throughput": 1250.0,
            "storage_utilization": 45.8,
            "request_rate": 850.2,
            "error_rate": 1.2,
            "response_time": 125.5
        }

    async def get_cluster_nodes(self) -> List[Dict[str, Any]]:
        """Get information about cluster nodes"""
        nodes = []
        
        if self.cluster_orchestrator and hasattr(self.cluster_orchestrator, 'node_manager'):
            try:
                node_list = await self.cluster_orchestrator.node_manager.get_active_nodes()
                for node in node_list:
                    nodes.append({
                        "id": node.id,
                        "name": node.name,
                        "ip_address": node.ip_address,
                        "node_type": node.node_type.value if hasattr(node.node_type, 'value') else str(node.node_type),
                        "status": node.status.value if hasattr(node.status, 'value') else str(node.status),
                        "cpu_utilization": node.resources.get("cpu_used", 0),
                        "memory_utilization": (node.resources.get("memory_used_gb", 0) / max(1, node.resources.get("memory_gb", 1))) * 100,
                        "current_connections": node.metadata.get("connections", 0),
                        "response_time": node.metadata.get("response_time", 0)
                    })
            except Exception as e:
                self.logger.error(f"Failed to get cluster nodes: {e}")
        
        # Return mock data if no nodes available
        if not nodes:
            nodes = [
                {
                    "id": "node-1",
                    "name": "Controller Node 1",
                    "ip_address": "10.0.1.10",
                    "node_type": "control",
                    "status": "active",
                    "cpu_utilization": 45.2,
                    "memory_utilization": 62.8,
                    "current_connections": 25,
                    "response_time": 95.5
                },
                {
                    "id": "node-2",
                    "name": "Worker Node 1",
                    "ip_address": "10.0.1.20",
                    "node_type": "worker",
                    "status": "active",
                    "cpu_utilization": 78.3,
                    "memory_utilization": 85.1,
                    "current_connections": 150,
                    "response_time": 145.2
                }
            ]
        
        return nodes

    async def get_load_balancer_stats(self) -> Dict[str, Any]:
        """Get load balancer statistics"""
        if self.load_balancer:
            try:
                return self.load_balancer.get_load_balancer_stats()
            except Exception as e:
                self.logger.error(f"Failed to get load balancer stats: {e}")
        
        return {
            "algorithm": "ai_powered",
            "total_backends": 3,
            "healthy_backends": 3,
            "total_requests": 15420,
            "total_connections": 75
        }

    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active alerts"""
        active_alerts = [alert for alert in self.alerts if not alert.resolved]
        
        # Convert to dict for JSON serialization
        return [
            {
                "id": alert.id,
                "level": alert.level.value,
                "title": alert.title,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "source": alert.source,
                "acknowledged": alert.acknowledged,
                "resolved": alert.resolved,
                "metadata": alert.metadata
            }
            for alert in active_alerts[:50]  # Limit to 50 most recent
        ]

    async def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        return {
            "dashboard_version": "1.0.0",
            "uptime": "2d 14h 32m",
            "last_update": datetime.now().isoformat(),
            "auto_refresh": self.config.enable_auto_refresh,
            "refresh_interval": self.config.refresh_interval
        }

    async def get_metrics_data(self, request: web.Request) -> web.Response:
        """Get historical metrics data for charts"""
        try:
            # Get query parameters
            metric_type = request.query.get("type", "all")
            hours = int(request.query.get("hours", 24))
            
            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            # Collect metrics data
            data = {
                "timestamps": [],
                "cpu_utilization": [],
                "memory_utilization": [],
                "request_rate": [],
                "response_time": [],
                "error_rate": []
            }
            
            # This would typically query a time-series database
            # For now, generate sample data
            import random
            current_time = start_time
            while current_time <= end_time:
                data["timestamps"].append(current_time.isoformat())
                data["cpu_utilization"].append(random.uniform(40, 80))
                data["memory_utilization"].append(random.uniform(50, 90))
                data["request_rate"].append(random.uniform(500, 1500))
                data["response_time"].append(random.uniform(50, 200))
                data["error_rate"].append(random.uniform(0, 5))
                
                current_time += timedelta(minutes=5)
            
            return web.json_response(data)
            
        except Exception as e:
            self.logger.error(f"Failed to get metrics data: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def acknowledge_alert(self, request: web.Request) -> web.Response:
        """Acknowledge an alert"""
        try:
            alert_id = request.match_info["alert_id"]
            
            for alert in self.alerts:
                if alert.id == alert_id:
                    alert.acknowledged = True
                    break
            
            return web.json_response({"success": True})
            
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def resolve_alert(self, request: web.Request) -> web.Response:
        """Resolve an alert"""
        try:
            alert_id = request.match_info["alert_id"]
            
            for alert in self.alerts:
                if alert.id == alert_id:
                    alert.resolved = True
                    break
            
            return web.json_response({"success": True})
            
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def websocket_handler_function(self, request: web.Request):
        """Handle WebSocket connections for real-time updates"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.connected_clients.add(ws)
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    # Handle client messages
                    pass
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    self.logger.error(f"WebSocket error: {ws.exception()}")
        except Exception as e:
            self.logger.error(f"WebSocket handler error: {e}")
        finally:
            self.connected_clients.discard(ws)
        
        return ws

    async def broadcast_update(self, data: Dict[str, Any]) -> None:
        """Broadcast updates to all connected clients"""
        if not self.connected_clients:
            return
        
        message = json.dumps(data)
        disconnected_clients = set()
        
        for client in self.connected_clients:
            try:
                await client.send_str(message)
            except Exception as e:
                self.logger.error(f"Failed to send update to client: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        self.connected_clients -= disconnected_clients

    async def data_collection_loop(self) -> None:
        """Collect data and broadcast updates"""
        while self.is_running:
            try:
                # Collect dashboard data
                data = await self.get_dashboard_data()
                
                # Broadcast to connected clients
                await self.broadcast_update(data)
                
                # Sleep until next collection
                await asyncio.sleep(self.config.refresh_interval)
                
            except Exception as e:
                self.logger.error(f"Data collection loop error: {e}")
                await asyncio.sleep(self.config.refresh_interval * 2)

    async def alert_processing_loop(self) -> None:
        """Process and generate alerts"""
        while self.is_running:
            try:
                await self.check_for_alerts()
                await self.cleanup_old_alerts()
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Alert processing loop error: {e}")
                await asyncio.sleep(120)

    async def check_for_alerts(self) -> None:
        """Check for conditions that should generate alerts"""
        try:
            metrics = await self.get_cluster_metrics()
            
            # CPU usage alert
            if metrics.get("cpu_utilization", 0) > 85:
                await self.create_alert(
                    AlertLevel.WARNING,
                    "High CPU Usage",
                    f"Cluster CPU usage is {metrics['cpu_utilization']:.1f}%",
                    "cluster_monitor"
                )
            
            # Memory usage alert
            if metrics.get("memory_utilization", 0) > 90:
                await self.create_alert(
                    AlertLevel.ERROR,
                    "High Memory Usage", 
                    f"Cluster memory usage is {metrics['memory_utilization']:.1f}%",
                    "cluster_monitor"
                )
            
            # Error rate alert
            if metrics.get("error_rate", 0) > 5:
                await self.create_alert(
                    AlertLevel.ERROR,
                    "High Error Rate",
                    f"Cluster error rate is {metrics['error_rate']:.1f}%",
                    "cluster_monitor"
                )
            
        except Exception as e:
            self.logger.error(f"Alert check failed: {e}")

    async def create_alert(self, 
                          level: AlertLevel,
                          title: str,
                          message: str,
                          source: str,
                          metadata: Dict[str, Any] = None) -> None:
        """Create a new alert"""
        alert = DashboardAlert(
            id=f"alert_{int(time.time())}_{len(self.alerts)}",
            level=level,
            title=title,
            message=message,
            timestamp=datetime.now(),
            source=source,
            metadata=metadata or {}
        )
        
        self.alerts.append(alert)
        
        # Keep only recent alerts
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-1000:]
        
        # Broadcast new alert
        await self.broadcast_update({"new_alert": asdict(alert)})

    async def cleanup_old_alerts(self) -> None:
        """Clean up old resolved alerts"""
        cutoff_time = datetime.now() - timedelta(days=self.config.data_retention_days)
        
        self.alerts = [
            alert for alert in self.alerts
            if alert.timestamp > cutoff_time or not alert.resolved
        ]

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics"""
        return {
            "connected_clients": len(self.connected_clients),
            "total_alerts": len(self.alerts),
            "active_alerts": len([a for a in self.alerts if not a.resolved]),
            "uptime": "2d 14h 32m",  # Would calculate actual uptime
            "last_update": datetime.now().isoformat()
        }