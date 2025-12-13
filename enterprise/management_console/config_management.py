"""
Aurora OS Configuration Management System
Centralized configuration management with versioning and validation
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
import yaml
import jsonschema
from pathlib import Path
import threading

class ConfigType(Enum):
    """Configuration types"""
    SYSTEM = "system"
    CLUSTER = "cluster"
    NODE = "node"
    APPLICATION = "application"
    SECURITY = "security"
    NETWORK = "network"
    STORAGE = "storage"
    MONITORING = "monitoring"
    BACKUP = "backup"

class ConfigFormat(Enum):
    """Configuration formats"""
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    XML = "xml"

class ConfigStatus(Enum):
    """Configuration status"""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"

class ChangeType(Enum):
    """Change operation types"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ROLLBACK = "rollback"

@dataclass
class ConfigSchema:
    """Configuration schema for validation"""
    id: str
    name: str
    config_type: ConfigType
    version: str
    schema: Dict[str, Any]
    required_fields: List[str]
    default_values: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "config_type": self.config_type.value,
            "version": self.version,
            "schema": self.schema,
            "required_fields": self.required_fields,
            "default_values": self.default_values
        }

@dataclass
class ConfigItem:
    """Configuration item"""
    id: str
    name: str
    config_type: ConfigType
    format: ConfigFormat
    data: Dict[str, Any]
    schema_id: str
    status: ConfigStatus
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str
    tags: Set[str]
    description: str
    environment: str  # development, staging, production
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "config_type": self.config_type.value,
            "format": self.format.value,
            "data": self.data,
            "schema_id": self.schema_id,
            "status": self.status.value,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "tags": list(self.tags),
            "description": self.description,
            "environment": self.environment
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    def to_yaml(self) -> str:
        """Convert to YAML string"""
        return yaml.dump(self.data, default_flow_style=False)

@dataclass
class ConfigChange:
    """Configuration change record"""
    id: str
    config_id: str
    change_type: ChangeType
    old_version: int
    new_version: int
    changes: Dict[str, Any]
    changed_by: str
    changed_at: datetime
    reason: str
    rollback_available: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "config_id": self.config_id,
            "change_type": self.change_type.value,
            "old_version": self.old_version,
            "new_version": self.new_version,
            "changes": self.changes,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at.isoformat(),
            "reason": self.reason,
            "rollback_available": self.rollback_available
        }

class ConfigManager:
    """Configuration management system"""
    
    def __init__(self, storage_path: str = "/var/lib/aurora/config"):
        self.logger = logging.getLogger(__name__)
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Data storage
        self.configs: Dict[str, ConfigItem] = {}
        self.schemas: Dict[str, ConfigSchema] = {}
        self.changes: List[ConfigChange] = []
        self.active_configs: Dict[str, str] = {}  # config_type -> config_id
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        # Initialize default schemas
        self._initialize_default_schemas()
        
        # Load existing configurations
        self._load_configurations()
    
    def _initialize_default_schemas(self):
        """Initialize default configuration schemas"""
        
        # System configuration schema
        system_schema = ConfigSchema(
            id="system-schema",
            name="System Configuration",
            config_type=ConfigType.SYSTEM,
            version="1.0",
            schema={
                "type": "object",
                "properties": {
                    "system_name": {"type": "string", "minLength": 1},
                    "version": {"type": "string"},
                    "debug_mode": {"type": "boolean"},
                    "log_level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
                    "max_connections": {"type": "integer", "minimum": 1},
                    "timeout": {"type": "integer", "minimum": 1}
                },
                "required": ["system_name", "version", "log_level"]
            },
            required_fields=["system_name", "version", "log_level"],
            default_values={
                "debug_mode": False,
                "log_level": "INFO",
                "max_connections": 1000,
                "timeout": 30
            }
        )
        
        # Cluster configuration schema
        cluster_schema = ConfigSchema(
            id="cluster-schema",
            name="Cluster Configuration",
            config_type=ConfigType.CLUSTER,
            version="1.0",
            schema={
                "type": "object",
                "properties": {
                    "cluster_name": {"type": "string", "minLength": 1},
                    "cluster_id": {"type": "string"},
                    "discovery_enabled": {"type": "boolean"},
                    "heartbeat_interval": {"type": "integer", "minimum": 1},
                    "node_timeout": {"type": "integer", "minimum": 1},
                    "replication_factor": {"type": "integer", "minimum": 1, "maximum": 10},
                    "consistency_level": {"type": "string", "enum": ["strong", "quorum", "eventual"]},
                    "auto_failover": {"type": "boolean"}
                },
                "required": ["cluster_name", "cluster_id", "heartbeat_interval", "replication_factor"]
            },
            required_fields=["cluster_name", "cluster_id", "heartbeat_interval", "replication_factor"],
            default_values={
                "discovery_enabled": True,
                "heartbeat_interval": 30,
                "node_timeout": 90,
                "replication_factor": 3,
                "consistency_level": "quorum",
                "auto_failover": True
            }
        )
        
        # Security configuration schema
        security_schema = ConfigSchema(
            id="security-schema",
            name="Security Configuration",
            config_type=ConfigType.SECURITY,
            version="1.0",
            schema={
                "type": "object",
                "properties": {
                    "authentication_required": {"type": "boolean"},
                    "session_timeout": {"type": "integer", "minimum": 60},
                    "max_login_attempts": {"type": "integer", "minimum": 1},
                    "password_policy": {
                        "type": "object",
                        "properties": {
                            "min_length": {"type": "integer", "minimum": 6},
                            "require_uppercase": {"type": "boolean"},
                            "require_numbers": {"type": "boolean"},
                            "require_special": {"type": "boolean"}
                        },
                        "required": ["min_length"]
                    },
                    "encryption_enabled": {"type": "boolean"},
                    "api_rate_limit": {"type": "integer", "minimum": 1}
                },
                "required": ["authentication_required", "session_timeout", "max_login_attempts"]
            },
            required_fields=["authentication_required", "session_timeout", "max_login_attempts"],
            default_values={
                "authentication_required": True,
                "session_timeout": 3600,
                "max_login_attempts": 5,
                "password_policy": {
                    "min_length": 8,
                    "require_uppercase": True,
                    "require_numbers": True,
                    "require_special": True
                },
                "encryption_enabled": True,
                "api_rate_limit": 100
            }
        )
        
        self.schemas.update({
            "system-schema": system_schema,
            "cluster-schema": cluster_schema,
            "security-schema": security_schema
        })
    
    def _load_configurations(self):
        """Load existing configurations from storage"""
        try:
            # Load configurations
            configs_file = self.storage_path / "configs.json"
            if configs_file.exists():
                with open(configs_file, 'r') as f:
                    configs_data = json.load(f)
                
                for config_data in configs_data:
                    config = self._dict_to_config(config_data)
                    self.configs[config.id] = config
            
            # Load schemas
            schemas_file = self.storage_path / "schemas.json"
            if schemas_file.exists():
                with open(schemas_file, 'r') as f:
                    schemas_data = json.load(f)
                
                for schema_data in schemas_data:
                    schema = ConfigSchema(**schema_data)
                    self.schemas[schema.id] = schema
            
            # Load changes
            changes_file = self.storage_path / "changes.json"
            if changes_file.exists():
                with open(changes_file, 'r') as f:
                    changes_data = json.load(f)
                
                for change_data in changes_data:
                    change = self._dict_to_change(change_data)
                    self.changes.append(change)
            
            # Load active configs
            active_file = self.storage_path / "active.json"
            if active_file.exists():
                with open(active_file, 'r') as f:
                    self.active_configs = json.load(f)
            
            self.logger.info(f"Loaded {len(self.configs)} configurations, {len(self.schemas)} schemas")
            
        except Exception as e:
            self.logger.error(f"Error loading configurations: {e}")
    
    def _save_configurations(self):
        """Save configurations to storage"""
        try:
            # Save configurations
            configs_file = self.storage_path / "configs.json"
            with open(configs_file, 'w') as f:
                configs_data = [config.to_dict() for config in self.configs.values()]
                json.dump(configs_data, f, indent=2)
            
            # Save schemas
            schemas_file = self.storage_path / "schemas.json"
            with open(schemas_file, 'w') as f:
                schemas_data = [schema.to_dict() for schema in self.schemas.values()]
                json.dump(schemas_data, f, indent=2)
            
            # Save changes
            changes_file = self.storage_path / "changes.json"
            with open(changes_file, 'w') as f:
                changes_data = [change.to_dict() for change in self.changes]
                json.dump(changes_data, f, indent=2)
            
            # Save active configs
            active_file = self.storage_path / "active.json"
            with open(active_file, 'w') as f:
                json.dump(self.active_configs, f, indent=2)
            
        except Exception as e:
            self.logger.error(f"Error saving configurations: {e}")
    
    def _dict_to_config(self, data: Dict[str, Any]) -> ConfigItem:
        """Convert dictionary to ConfigItem"""
        data = data.copy()
        data['config_type'] = ConfigType(data['config_type'])
        data['format'] = ConfigFormat(data['format'])
        data['status'] = ConfigStatus(data['status'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        data['tags'] = set(data['tags'])
        
        return ConfigItem(**data)
    
    def _dict_to_change(self, data: Dict[str, Any]) -> ConfigChange:
        """Convert dictionary to ConfigChange"""
        data = data.copy()
        data['change_type'] = ChangeType(data['change_type'])
        data['changed_at'] = datetime.fromisoformat(data['changed_at'])
        
        return ConfigChange(**data)
    
    def validate_config(self, config_data: Dict[str, Any], schema_id: str) -> Tuple[bool, List[str]]:
        """Validate configuration against schema"""
        if schema_id not in self.schemas:
            return False, [f"Schema {schema_id} not found"]
        
        schema = self.schemas[schema_id]
        
        try:
            # Validate with jsonschema
            jsonschema.validate(config_data, schema.schema)
            
            # Check required fields
            missing_fields = []
            for field in schema.required_fields:
                if field not in config_data:
                    missing_fields.append(field)
            
            if missing_fields:
                return False, [f"Missing required fields: {', '.join(missing_fields)}"]
            
            return True, []
            
        except jsonschema.ValidationError as e:
            return False, [f"Validation error: {e.message}"]
        except Exception as e:
            return False, [f"Validation error: {str(e)}"]
    
    async def create_config(self, name: str, config_type: ConfigType, format: ConfigFormat,
                          data: Dict[str, Any], schema_id: str, created_by: str,
                          environment: str = "production", description: str = "",
                          tags: Set[str] = None) -> Tuple[bool, str, Optional[str]]:
        """Create a new configuration"""
        with self._lock:
            try:
                # Validate configuration
                is_valid, errors = self.validate_config(data, schema_id)
                if not is_valid:
                    return False, f"Validation failed: {'; '.join(errors)}", None
                
                # Create configuration
                config_id = str(uuid.uuid4())
                now = datetime.now()
                
                config = ConfigItem(
                    id=config_id,
                    name=name,
                    config_type=config_type,
                    format=format,
                    data=data,
                    schema_id=schema_id,
                    status=ConfigStatus.DRAFT,
                    version=1,
                    created_at=now,
                    updated_at=now,
                    created_by=created_by,
                    updated_by=created_by,
                    tags=tags or set(),
                    description=description,
                    environment=environment
                )
                
                self.configs[config_id] = config
                
                # Record change
                change = ConfigChange(
                    id=str(uuid.uuid4()),
                    config_id=config_id,
                    change_type=ChangeType.CREATE,
                    old_version=0,
                    new_version=1,
                    changes=data,
                    changed_by=created_by,
                    changed_at=now,
                    reason="Initial configuration creation",
                    rollback_available=False
                )
                self.changes.append(change)
                
                # Save to storage
                self._save_configurations()
                
                self.logger.info(f"Configuration created: {name} ({config_id}) by {created_by}")
                return True, "Configuration created successfully", config_id
                
            except Exception as e:
                self.logger.error(f"Error creating configuration: {e}")
                return False, f"Error creating configuration: {str(e)}", None
    
    async def update_config(self, config_id: str, data: Dict[str, Any], updated_by: str,
                          reason: str = "") -> Tuple[bool, str]:
        """Update an existing configuration"""
        with self._lock:
            try:
                if config_id not in self.configs:
                    return False, "Configuration not found"
                
                config = self.configs[config_id]
                old_data = config.data.copy()
                
                # Validate new configuration
                is_valid, errors = self.validate_config(data, config.schema_id)
                if not is_valid:
                    return False, f"Validation failed: {'; '.join(errors)}", None
                
                # Update configuration
                config.data = data
                config.version += 1
                config.updated_at = datetime.now()
                config.updated_by = updated_by
                
                # Record change
                change = ConfigChange(
                    id=str(uuid.uuid4()),
                    config_id=config_id,
                    change_type=ChangeType.UPDATE,
                    old_version=config.version - 1,
                    new_version=config.version,
                    changes={"old": old_data, "new": data},
                    changed_by=updated_by,
                    changed_at=datetime.now(),
                    reason=reason,
                    rollback_available=True
                )
                self.changes.append(change)
                
                # Save to storage
                self._save_configurations()
                
                self.logger.info(f"Configuration updated: {config.name} to version {config.version} by {updated_by}")
                return True, "Configuration updated successfully"
                
            except Exception as e:
                self.logger.error(f"Error updating configuration: {e}")
                return False, f"Error updating configuration: {str(e)}"
    
    async def activate_config(self, config_id: str, activated_by: str) -> Tuple[bool, str]:
        """Activate a configuration"""
        with self._lock:
            try:
                if config_id not in self.configs:
                    return False, "Configuration not found"
                
                config = self.configs[config_id]
                
                # Deactivate existing active config of same type
                config_type = config.config_type.value
                if config_type in self.active_configs:
                    old_active_id = self.active_configs[config_type]
                    if old_active_id in self.configs:
                        self.configs[old_active_id].status = ConfigStatus.DEPRECATED
                
                # Activate new config
                config.status = ConfigStatus.ACTIVE
                self.active_configs[config_type] = config_id
                
                # Record change
                change = ConfigChange(
                    id=str(uuid.uuid4()),
                    config_id=config_id,
                    change_type=ChangeType.UPDATE,
                    old_version=config.version,
                    new_version=config.version,
                    changes={"status": "activated"},
                    changed_by=activated_by,
                    changed_at=datetime.now(),
                    reason="Configuration activated",
                    rollback_available=True
                )
                self.changes.append(change)
                
                # Save to storage
                self._save_configurations()
                
                self.logger.info(f"Configuration activated: {config.name} by {activated_by}")
                return True, "Configuration activated successfully"
                
            except Exception as e:
                self.logger.error(f"Error activating configuration: {e}")
                return False, f"Error activating configuration: {str(e)}"
    
    async def rollback_config(self, config_id: str, target_version: int, rolled_back_by: str,
                            reason: str = "") -> Tuple[bool, str]:
        """Rollback configuration to a previous version"""
        with self._lock:
            try:
                if config_id not in self.configs:
                    return False, "Configuration not found"
                
                # Find change record for target version
                target_change = None
                for change in reversed(self.changes):
                    if change.config_id == config_id and change.new_version == target_version:
                        target_change = change
                        break
                
                if not target_change:
                    return False, f"Target version {target_version} not found"
                
                config = self.configs[config_id]
                old_data = config.data.copy()
                
                # Rollback to target version data
                if target_change.change_type == ChangeType.UPDATE:
                    config.data = target_change.changes["new"]
                elif target_change.change_type == ChangeType.CREATE:
                    config.data = target_change.changes
                
                config.version += 1
                config.updated_at = datetime.now()
                config.updated_by = rolled_back_by
                
                # Record rollback change
                change = ConfigChange(
                    id=str(uuid.uuid4()),
                    config_id=config_id,
                    change_type=ChangeType.ROLLBACK,
                    old_version=config.version - 1,
                    new_version=config.version,
                    changes={"old": old_data, "new": config.data, "rollback_to": target_version},
                    changed_by=rolled_back_by,
                    changed_at=datetime.now(),
                    reason=f"Rollback to version {target_version}: {reason}",
                    rollback_available=True
                )
                self.changes.append(change)
                
                # Save to storage
                self._save_configurations()
                
                self.logger.info(f"Configuration rolled back: {config.name} to version {target_version} by {rolled_back_by}")
                return True, f"Configuration rolled back to version {target_version}"
                
            except Exception as e:
                self.logger.error(f"Error rolling back configuration: {e}")
                return False, f"Error rolling back configuration: {str(e)}"
    
    def get_config(self, config_id: str) -> Optional[ConfigItem]:
        """Get configuration by ID"""
        return self.configs.get(config_id)
    
    def get_active_config(self, config_type: ConfigType) -> Optional[ConfigItem]:
        """Get active configuration for a type"""
        type_key = config_type.value
        if type_key in self.active_configs:
            config_id = self.active_configs[type_key]
            return self.configs.get(config_id)
        return None
    
    def list_configs(self, config_type: Optional[ConfigType] = None,
                    environment: Optional[str] = None,
                    status: Optional[ConfigStatus] = None) -> List[ConfigItem]:
        """List configurations with filters"""
        configs = list(self.configs.values())
        
        if config_type:
            configs = [c for c in configs if c.config_type == config_type]
        
        if environment:
            configs = [c for c in configs if c.environment == environment]
        
        if status:
            configs = [c for c in configs if c.status == status]
        
        return sorted(configs, key=lambda c: c.updated_at, reverse=True)
    
    def get_config_history(self, config_id: str) -> List[ConfigChange]:
        """Get change history for a configuration"""
        return [c for c in self.changes if c.config_id == config_id]
    
    def export_config(self, config_id: str, format: ConfigFormat) -> Optional[str]:
        """Export configuration in specified format"""
        config = self.get_config(config_id)
        if not config:
            return None
        
        try:
            if format == ConfigFormat.JSON:
                return json.dumps(config.data, indent=2)
            elif format == ConfigFormat.YAML:
                return yaml.dump(config.data, default_flow_style=False)
            else:
                return json.dumps(config.data, indent=2)  # Default to JSON
                
        except Exception as e:
            self.logger.error(f"Error exporting configuration: {e}")
            return None
    
    async def import_config(self, config_data: str, format: ConfigFormat, name: str,
                          config_type: ConfigType, schema_id: str, imported_by: str) -> Tuple[bool, str, Optional[str]]:
        """Import configuration from string"""
        try:
            # Parse configuration data
            if format == ConfigFormat.JSON:
                data = json.loads(config_data)
            elif format == ConfigFormat.YAML:
                data = yaml.safe_load(config_data)
            else:
                return False, f"Unsupported format: {format.value}", None
            
            # Create configuration
            return await self.create_config(
                name=name,
                config_type=config_type,
                format=format,
                data=data,
                schema_id=schema_id,
                created_by=imported_by,
                description=f"Imported from {format.value}"
            )
            
        except Exception as e:
            self.logger.error(f"Error importing configuration: {e}")
            return False, f"Error importing configuration: {str(e)}", None

# Test function
async def test_config_management():
    """Test the configuration management system"""
    config_manager = ConfigManager("/tmp/aurora-config-test")
    
    # Create a system configuration
    system_config_data = {
        "system_name": "Aurora-OS",
        "version": "0.1.0",
        "debug_mode": False,
        "log_level": "INFO",
        "max_connections": 1000,
        "timeout": 30
    }
    
    success, message, config_id = await config_manager.create_config(
        name="Main System Config",
        config_type=ConfigType.SYSTEM,
        format=ConfigFormat.JSON,
        data=system_config_data,
        schema_id="system-schema",
        created_by="admin",
        environment="production",
        description="Main system configuration"
    )
    
    print(f"Config creation: {success} - {message}")
    
    if config_id:
        # Activate configuration
        success, message = await config_manager.activate_config(config_id, "admin")
        print(f"Config activation: {success} - {message}")
        
        # Get active config
        active_config = config_manager.get_active_config(ConfigType.SYSTEM)
        if active_config:
            print(f"Active system config: {active_config.name}")
        
        # Update configuration
        updated_data = system_config_data.copy()
        updated_data["debug_mode"] = True
        
        success, message = await config_manager.update_config(config_id, updated_data, "admin", "Enable debug mode")
        print(f"Config update: {success} - {message}")
        
        # List configurations
        configs = config_manager.list_configs(config_type=ConfigType.SYSTEM)
        print(f"Total system configs: {len(configs)}")
    
    # Test export/import
    if config_id:
        exported_yaml = config_manager.export_config(config_id, ConfigFormat.YAML)
        if exported_yaml:
            print(f"Exported YAML:\n{exported_yaml}")
            
            # Import back
            success, message, new_config_id = await config_manager.import_config(
                config_data=exported_yaml,
                format=ConfigFormat.YAML,
                name="Imported System Config",
                config_type=ConfigType.SYSTEM,
                schema_id="system-schema",
                imported_by="admin"
            )
            print(f"Config import: {success} - {message}")

if __name__ == "__main__":
    asyncio.run(test_config_management())