"""
Test suite for Aurora OS Enterprise Management Console
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

from enterprise.management_console.web_interface import AuroraManagementConsole, UserRole
from enterprise.management_console.monitoring_dashboard import MonitoringDashboard, AlertSeverity, MetricType
from enterprise.management_console.user_management import UserManagementSystem, UserRole as UMUserRole, UserStatus
from enterprise.management_console.config_management import ConfigManager, ConfigType, ConfigFormat, ConfigStatus

class TestAuroraManagementConsole:
    """Test Aurora Management Console"""
    
    def test_console_initialization(self):
        """Test console initialization"""
        console = AuroraManagementConsole(host="127.0.0.1", port=8443)
        
        assert console.host == "127.0.0.1"
        assert console.port == 8443
        assert console.jwt_secret is not None
        assert len(console.users) == 1  # Default admin user
        assert len(console.dashboard_data) == 0
    
    def test_default_admin_user(self):
        """Test default admin user creation"""
        console = AuroraManagementConsole()
        
        # Check that default admin user exists
        admin_user = None
        for user in console.users.values():
            if user.username == "admin":
                admin_user = user
                break
        
        assert admin_user is not None
        assert admin_user.role == UserRole.ADMIN
        assert admin_user.active is True
        assert admin_user.email == "admin@auroraos.local"
        assert len(admin_user.permissions) > 0
    
    def test_dashboard_data_collection(self):
        """Test dashboard data collection"""
        console = AuroraManagementConsole()
        
        # Simulate dashboard data
        asyncio.run(console._collect_dashboard_data())
        
        assert console.dashboard_data is not None
        assert "cluster_health" in console.dashboard_data
        assert "total_nodes" in console.dashboard_data
        assert "active_nodes" in console.dashboard_data
        assert "cpu_usage" in console.dashboard_data
        assert "memory_usage" in console.dashboard_data
    
    def test_cluster_status_collection(self):
        """Test cluster status collection"""
        console = AuroraManagementConsole()
        
        # Simulate cluster status collection
        asyncio.run(console._collect_cluster_status())
        
        assert console.cluster_status is not None
        assert "cluster_name" in console.cluster_status
        assert "cluster_id" in console.cluster_status
        assert "status" in console.cluster_status
        assert "total_nodes" in console.cluster_status
    
    def test_html_generation(self):
        """Test HTML generation"""
        console = AuroraManagementConsole()
        
        # Test main console HTML
        console_html = console._generate_console_html()
        assert isinstance(console_html, str)
        assert len(console_html) > 1000
        assert "Aurora OS Management Console" in console_html
        assert "dashboard" in console_html.lower()
        assert "cluster" in console_html.lower()
        
        # Test cluster page HTML
        cluster_html = console._generate_cluster_html()
        assert isinstance(cluster_html, str)
        assert "Cluster Management" in cluster_html
        
        # Test nodes page HTML
        nodes_html = console._generate_nodes_html()
        assert isinstance(nodes_html, str)
        assert "Node Management" in nodes_html
        
        # Test monitoring page HTML
        monitoring_html = console._generate_monitoring_html()
        assert isinstance(monitoring_html, str)
        assert "System Monitoring" in monitoring_html

class TestMonitoringDashboard:
    """Test Monitoring Dashboard"""
    
    def test_dashboard_initialization(self):
        """Test dashboard initialization"""
        dashboard = MonitoringDashboard()
        
        assert dashboard.metrics_history == {}
        assert dashboard.current_metrics == {}
        assert dashboard.active_alerts == {}
        assert dashboard.alert_history == []
        assert len(dashboard.threshold_rules) > 0
        
        # Check default rules
        assert "cpu_high" in dashboard.threshold_rules
        assert "memory_high" in dashboard.threshold_rules
        assert "disk_high" in dashboard.threshold_rules
    
    def test_threshold_rules(self):
        """Test default threshold rules"""
        dashboard = MonitoringDashboard()
        
        # Check CPU rules
        cpu_high_rule = dashboard.threshold_rules["cpu_high"]
        assert cpu_high_rule.metric_type == MetricType.CPU_USAGE
        assert cpu_high_rule.severity == AlertSeverity.WARNING
        assert cpu_high_rule.threshold_value == 80.0
        assert cpu_high_rule.enabled is True
        
        cpu_critical_rule = dashboard.threshold_rules["cpu_critical"]
        assert cpu_critical_rule.metric_type == MetricType.CPU_USAGE
        assert cpu_critical_rule.severity == AlertSeverity.CRITICAL
        assert cpu_critical_rule.threshold_value == 95.0
    
    def test_metric_addition(self):
        """Test adding metrics"""
        dashboard = MonitoringDashboard()
        
        # Add a test metric
        from enterprise.management_console.monitoring_dashboard import Metric
        metric = Metric(
            metric_type=MetricType.CPU_USAGE,
            value=85.0,
            unit="percent",
            timestamp=datetime.now(),
            node_id="test-node",
            metadata={}
        )
        
        asyncio.run(dashboard.add_metric(metric))
        
        # Check metric storage
        assert "test-node" in dashboard.current_metrics
        assert MetricType.CPU_USAGE in dashboard.current_metrics["test-node"]
        assert dashboard.current_metrics["test-node"][MetricType.CPU_USAGE].value == 85.0
    
    def test_threshold_evaluation(self):
        """Test threshold evaluation"""
        dashboard = MonitoringDashboard()
        
        # Test high CPU threshold
        from enterprise.management_console.monitoring_dashboard import Metric
        high_cpu_metric = Metric(
            metric_type=MetricType.CPU_USAGE,
            value=90.0,
            unit="percent",
            timestamp=datetime.now(),
            node_id="test-node",
            metadata={}
        )
        
        rule = dashboard.threshold_rules["cpu_high"]
        assert rule.evaluate(high_cpu_metric) is True
        
        # Test normal CPU threshold
        normal_cpu_metric = Metric(
            metric_type=MetricType.CPU_USAGE,
            value=50.0,
            unit="percent",
            timestamp=datetime.now(),
            node_id="test-node",
            metadata={}
        )
        
        assert rule.evaluate(normal_cpu_metric) is False
    
    def test_dashboard_data(self):
        """Test dashboard data generation"""
        dashboard = MonitoringDashboard()
        
        # Start monitoring to generate data
        dashboard.start_monitoring()
        
        # Wait a moment for data collection
        asyncio.sleep(2)
        
        # Get dashboard data
        data = dashboard.get_dashboard_data()
        
        assert "summary" in data
        assert "active_alerts" in data
        assert "recent_alerts" in data
        assert "metrics" in data
        assert "threshold_rules" in data
        
        summary = data["summary"]
        assert "total_nodes" in summary
        assert "total_alerts" in summary
        assert "avg_cpu_usage" in summary
        assert "avg_memory_usage" in summary
        
        dashboard.stop_monitoring()
    
    def test_alert_acknowledgement(self):
        """Test alert acknowledgement"""
        dashboard = MonitoringDashboard()
        
        # Manually create an alert
        from enterprise.management_console.monitoring_dashboard import Alert, AlertStatus
        alert = Alert(
            id="test-alert",
            title="Test Alert",
            description="Test alert description",
            severity=AlertSeverity.WARNING,
            status=AlertStatus.ACTIVE,
            metric_type=MetricType.CPU_USAGE,
            threshold=80.0,
            current_value=85.0,
            node_id="test-node",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            acknowledged_by=None,
            resolved_at=None,
            metadata={}
        )
        
        dashboard.active_alerts["test-alert"] = alert
        
        # Acknowledge alert
        success = dashboard.acknowledge_alert("test-alert", "admin")
        assert success is True
        assert alert.status == AlertStatus.ACKNOWLEDGED
        assert alert.acknowledged_by == "admin"
        
        # Test acknowledging non-existent alert
        success = dashboard.acknowledge_alert("non-existent", "admin")
        assert success is False

class TestUserManagementSystem:
    """Test User Management System"""
    
    def test_system_initialization(self):
        """Test system initialization"""
        ums = UserManagementSystem("test-secret")
        
        assert ums.jwt_secret == "test-secret"
        assert len(ums.roles) > 0
        assert len(ums.users) == 1  # Default admin user
        
        # Check default roles
        assert "super_admin" in ums.roles
        assert "admin" in ums.roles
        assert "operator" in ums.roles
        assert "viewer" in ums.roles
    
    def test_role_hierarchy(self):
        """Test role hierarchy and permissions"""
        ums = UserManagementSystem("test-secret")
        
        # Check role levels
        super_admin_role = ums.roles["super_admin"]
        admin_role = ums.roles["admin"]
        viewer_role = ums.roles["viewer"]
        
        assert super_admin_role.level > admin_role.level
        assert admin_role.level > viewer_role.level
        
        # Super admin should have all permissions
        from enterprise.management_console.user_management import Permission
        assert len(super_admin_role.permissions) == len(Permission)
        
        # Viewer should have limited permissions
        assert len(viewer_role.permissions) < len(super_admin_role.permissions)
    
    def test_user_creation(self):
        """Test user creation"""
        ums = UserManagementSystem("test-secret")
        
        # Create a new user
        success, message = asyncio.run(ums.create_user(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            role=UMUserRole.DEVELOPER,
            password="TestPass123!",
            created_by="admin"
        ))
        
        assert success is True
        assert "created successfully" in message.lower()
        
        # Check user was created
        found_user = None
        for user in ums.users.values():
            if user.username == "testuser":
                found_user = user
                break
        
        assert found_user is not None
        assert found_user.email == "test@example.com"
        assert found_user.role == UMUserRole.DEVELOPER
        assert found_user.status == UserStatus.ACTIVE
    
    def test_user_authentication(self):
        """Test user authentication"""
        ums = UserManagementSystem("test-secret")
        
        # Authenticate with default admin
        success, message, session = asyncio.run(ums.authenticate_user(
            username="admin",
            password="aurora123",
            ip_address="127.0.0.1",
            user_agent="Test Agent"
        ))
        
        assert success is True
        assert session is not None
        assert session.user_id is not None
        assert session.token is not None
        assert session.refresh_token is not None
        
        # Test invalid password
        success, message, session = asyncio.run(ums.authenticate_user(
            username="admin",
            password="wrongpassword",
            ip_address="127.0.0.1",
            user_agent="Test Agent"
        ))
        
        assert success is False
        assert session is None
        assert "invalid credentials" in message.lower()
    
    def test_session_validation(self):
        """Test session validation"""
        ums = UserManagementSystem("test-secret")
        
        # Authenticate first
        success, message, session = asyncio.run(ums.authenticate_user(
            username="admin",
            password="aurora123",
            ip_address="127.0.0.1",
            user_agent="Test Agent"
        ))
        
        assert success is True
        assert session is not None
        
        # Validate session
        valid, user = asyncio.run(ums.validate_session(session.token))
        assert valid is True
        assert user is not None
        assert user.username == "admin"
        
        # Test logout
        logout_success = asyncio.run(ums.logout_user(session.token))
        assert logout_success is True
        
        # Session should no longer be valid
        valid, user = asyncio.run(ums.validate_session(session.token))
        assert valid is False
        assert user is None
    
    def test_permission_checking(self):
        """Test permission checking"""
        ums = UserManagementSystem("test-secret")
        
        # Get admin user
        admin_user = None
        for user in ums.users.values():
            if user.username == "admin":
                admin_user = user
                break
        
        assert admin_user is not None
        
        # Admin should have all permissions
        from enterprise.management_console.user_management import Permission
        for permission in Permission:
            assert ums.check_permission(admin_user, permission) is True
        
        # Create a viewer user
        success, _ = asyncio.run(ums.create_user(
            username="viewer",
            email="viewer@example.com",
            full_name="Viewer User",
            role=UMUserRole.VIEWER,
            password="ViewerPass123!",
            created_by="admin"
        ))
        
        if success:
            viewer_user = None
            for user in ums.users.values():
                if user.username == "viewer":
                    viewer_user = user
                    break
            
            assert viewer_user is not None
            
            # Viewer should have limited permissions
            assert ums.check_permission(viewer_user, Permission.CLUSTER_VIEW) is True
            assert ums.check_permission(viewer_user, Permission.USER_MANAGE) is False
            assert ums.check_permission(viewer_user, Permission.SYSTEM_CONFIGURE) is False
    
    def test_user_list(self):
        """Test user listing"""
        ums = UserManagementSystem("test-secret")
        
        users = ums.get_users_list()
        assert len(users) >= 1  # At least the default admin
        
        # Check user data structure
        for user_data in users:
            assert "username" in user_data
            assert "email" in user_data
            assert "role" in user_data
            assert "status" in user_data
            assert "created_at" in user_data

class TestConfigManager:
    """Test Configuration Management"""
    
    def test_config_manager_initialization(self):
        """Test config manager initialization"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(storage_path=temp_dir)
            
            assert config_manager.storage_path == Path(temp_dir)
            assert len(config_manager.schemas) > 0
            assert len(config_manager.configs) == 0
            assert len(config_manager.changes) == 0
            
            # Check default schemas
            assert "system-schema" in config_manager.schemas
            assert "cluster-schema" in config_manager.schemas
            assert "security-schema" in config_manager.schemas
    
    def test_config_validation(self):
        """Test configuration validation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(storage_path=temp_dir)
            
            # Valid system config
            valid_config = {
                "system_name": "Aurora-OS",
                "version": "0.1.0",
                "log_level": "INFO",
                "debug_mode": False,
                "max_connections": 1000,
                "timeout": 30
            }
            
            is_valid, errors = config_manager.validate_config(valid_config, "system-schema")
            assert is_valid is True
            assert len(errors) == 0
            
            # Invalid system config (missing required fields)
            invalid_config = {
                "debug_mode": False,
                "max_connections": 1000
            }
            
            is_valid, errors = config_manager.validate_config(invalid_config, "system-schema")
            assert is_valid is False
            assert len(errors) > 0
            assert "missing required fields" in errors[0].lower()
    
    def test_config_creation(self):
        """Test configuration creation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(storage_path=temp_dir)
            
            system_config = {
                "system_name": "Aurora-OS",
                "version": "0.1.0",
                "log_level": "INFO",
                "debug_mode": False,
                "max_connections": 1000,
                "timeout": 30
            }
            
            success, message, config_id = asyncio.run(config_manager.create_config(
                name="Test System Config",
                config_type=ConfigType.SYSTEM,
                format=ConfigFormat.JSON,
                data=system_config,
                schema_id="system-schema",
                created_by="admin",
                environment="production",
                description="Test configuration"
            ))
            
            assert success is True
            assert config_id is not None
            
            # Check config was created
            config = config_manager.get_config(config_id)
            assert config is not None
            assert config.name == "Test System Config"
            assert config.config_type == ConfigType.SYSTEM
            assert config.status == ConfigStatus.DRAFT
            assert config.version == 1
    
    def test_config_activation(self):
        """Test configuration activation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(storage_path=temp_dir)
            
            # Create config first
            system_config = {
                "system_name": "Aurora-OS",
                "version": "0.1.0",
                "log_level": "INFO"
            }
            
            success, message, config_id = asyncio.run(config_manager.create_config(
                name="Test System Config",
                config_type=ConfigType.SYSTEM,
                format=ConfigFormat.JSON,
                data=system_config,
                schema_id="system-schema",
                created_by="admin"
            ))
            
            assert success is True
            
            # Activate config
            success, message = asyncio.run(config_manager.activate_config(config_id, "admin"))
            assert success is True
            
            # Check config is active
            config = config_manager.get_config(config_id)
            assert config.status == ConfigStatus.ACTIVE
            
            # Check it's the active config for the type
            active_config = config_manager.get_active_config(ConfigType.SYSTEM)
            assert active_config is not None
            assert active_config.id == config_id
    
    def test_config_update(self):
        """Test configuration update"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(storage_path=temp_dir)
            
            # Create config
            system_config = {
                "system_name": "Aurora-OS",
                "version": "0.1.0",
                "log_level": "INFO"
            }
            
            success, message, config_id = asyncio.run(config_manager.create_config(
                name="Test System Config",
                config_type=ConfigType.SYSTEM,
                format=ConfigFormat.JSON,
                data=system_config,
                schema_id="system-schema",
                created_by="admin"
            ))
            
            assert success is True
            
            # Update config
            updated_config = system_config.copy()
            updated_config["debug_mode"] = True
            updated_config["max_connections"] = 2000
            
            success, message = asyncio.run(config_manager.update_config(
                config_id, updated_config, "admin", "Add debug mode"
            ))
            
            assert success is True
            
            # Check update
            config = config_manager.get_config(config_id)
            assert config.version == 2
            assert config.data["debug_mode"] is True
            assert config.data["max_connections"] == 2000
    
    def test_config_export_import(self):
        """Test configuration export and import"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(storage_path=temp_dir)
            
            # Create config
            system_config = {
                "system_name": "Aurora-OS",
                "version": "0.1.0",
                "log_level": "INFO",
                "debug_mode": True
            }
            
            success, message, config_id = asyncio.run(config_manager.create_config(
                name="Export Test Config",
                config_type=ConfigType.SYSTEM,
                format=ConfigFormat.JSON,
                data=system_config,
                schema_id="system-schema",
                created_by="admin"
            ))
            
            assert success is True
            
            # Export to YAML
            exported_yaml = config_manager.export_config(config_id, ConfigFormat.YAML)
            assert exported_yaml is not None
            assert "Aurora-OS" in exported_yaml
            assert "debug_mode: true" in exported_yaml
            
            # Import back
            success, message, new_config_id = asyncio.run(config_manager.import_config(
                config_data=exported_yaml,
                format=ConfigFormat.YAML,
                name="Imported Config",
                config_type=ConfigType.SYSTEM,
                schema_id="system-schema",
                imported_by="admin"
            ))
            
            assert success is True
            assert new_config_id is not None
            assert new_config_id != config_id  # Should be a new config
            
            # Check imported config
            imported_config = config_manager.get_config(new_config_id)
            assert imported_config is not None
            assert imported_config.name == "Imported Config"
            assert imported_config.data["system_name"] == "Aurora-OS"
            assert imported_config.data["debug_mode"] is True
    
    def test_config_history(self):
        """Test configuration change history"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(storage_path=temp_dir)
            
            # Create config
            system_config = {
                "system_name": "Aurora-OS",
                "version": "0.1.0",
                "log_level": "INFO"
            }
            
            success, message, config_id = asyncio.run(config_manager.create_config(
                name="History Test Config",
                config_type=ConfigType.SYSTEM,
                format=ConfigFormat.JSON,
                data=system_config,
                schema_id="system-schema",
                created_by="admin"
            ))
            
            assert success is True
            
            # Update config
            updated_config = system_config.copy()
            updated_config["debug_mode"] = True
            
            success, message = asyncio.run(config_manager.update_config(
                config_id, updated_config, "admin", "Enable debug"
            ))
            
            assert success is True
            
            # Check history
            history = config_manager.get_config_history(config_id)
            assert len(history) >= 2  # Create + Update
            
            # Check change records
            create_change = next((c for c in history if c.change_type.value == "create"), None)
            update_change = next((c for c in history if c.change_type.value == "update"), None)
            
            assert create_change is not None
            assert update_change is not None
            assert create_change.new_version == 1
            assert update_change.new_version == 2

# Test runner function
def run_enterprise_management_console_tests():
    """Run all enterprise management console tests"""
    print("🏢 Running Enterprise Management Console Tests")
    print("=" * 60)
    
    test_classes = [
        TestAuroraManagementConsole,
        TestMonitoringDashboard,
        TestUserManagementSystem,
        TestConfigManager
    ]
    
    total_passed = 0
    total_failed = 0
    
    for test_class in test_classes:
        print(f"\n📋 {test_class.__name__}")
        print("-" * 40)
        
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for test_method in test_methods:
            try:
                print(f"  ✅ {test_method}... ", end="")
                
                # Create test instance
                test_instance = test_class()
                
                # Run test method
                method = getattr(test_instance, test_method)
                method()
                
                print("PASSED")
                total_passed += 1
                
            except Exception as e:
                print(f"❌ FAILED: {e}")
                total_failed += 1
    
    print(f"\n📊 Test Results: {total_passed} passed, {total_failed} failed")
    
    if total_failed == 0:
        print("🎉 All Enterprise Management Console tests passed!")
    
    return total_failed == 0

if __name__ == "__main__":
    success = run_enterprise_management_console_tests()
    sys.exit(0 if success else 1)