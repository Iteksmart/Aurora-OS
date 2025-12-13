"""
Aurora OS - Task Agent
Agentic AI system that can execute tasks autonomously
Breaks down complex requests into actionable steps and executes them
"""

import os
import sys
import json
import asyncio
import subprocess
import threading
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from pathlib import Path
import logging
from datetime import datetime, timedelta
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

@dataclass
class TaskStep:
    """Individual step in a task"""
    id: str
    description: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

@dataclass
class Task:
    """Complex task that can be broken down into steps"""
    id: str
    title: str
    description: str
    steps: List[TaskStep] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    requires_confirmation: bool = False
    confirmed: bool = False

class TaskExecutor:
    """Executes individual task steps"""
    
    def __init__(self):
        self.logger = logging.getLogger("Aurora.TaskExecutor")
        self.executors = {
            'system_command': self._execute_system_command,
            'file_operation': self._execute_file_operation,
            'application': self._execute_application,
            'network': self._execute_network,
            'system_info': self._execute_system_info,
            'user_interaction': self._execute_user_interaction,
            'automation': self._execute_automation,
        }
    
    async def execute_step(self, step: TaskStep) -> Any:
        """Execute a single task step"""
        step.status = TaskStatus.RUNNING
        step.started_at = datetime.now()
        
        try:
            self.logger.info(f"Executing step: {step.description}")
            
            executor = self.executors.get(step.action)
            if executor:
                result = await executor(**step.parameters)
                step.result = result
                step.status = TaskStatus.COMPLETED
                step.completed_at = datetime.now()
                return result
            else:
                raise ValueError(f"Unknown action type: {step.action}")
        
        except Exception as e:
            step.error = str(e)
            step.status = TaskStatus.FAILED
            step.completed_at = datetime.now()
            self.logger.error(f"Step failed: {step.description} - {e}")
            raise
    
    async def _execute_system_command(self, command: str, shell: bool = True, 
                                    timeout: int = 30, **kwargs) -> str:
        """Execute system command"""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=shell
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            
            if process.returncode != 0:
                raise RuntimeError(f"Command failed: {stderr.decode().strip()}")
            
            return stdout.decode().strip()
        
        except asyncio.TimeoutError:
            raise RuntimeError(f"Command timed out after {timeout} seconds")
    
    async def _execute_file_operation(self, operation: str, path: str, **kwargs) -> Any:
        """Execute file operations"""
        path = Path(path)
        
        if operation == 'create':
            path.parent.mkdir(parents=True, exist_ok=True)
            if 'content' in kwargs:
                path.write_text(kwargs['content'])
            else:
                path.touch()
            return f"Created {path}"
        
        elif operation == 'delete':
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                import shutil
                shutil.rmtree(path)
            return f"Deleted {path}"
        
        elif operation == 'copy':
            dest = Path(kwargs['destination'])
            dest.parent.mkdir(parents=True, exist_ok=True)
            import shutil
            if path.is_file():
                shutil.copy2(path, dest)
            elif path.is_dir():
                shutil.copytree(path, dest)
            return f"Copied {path} to {dest}"
        
        elif operation == 'move':
            dest = Path(kwargs['destination'])
            dest.parent.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.move(str(path), str(dest))
            return f"Moved {path} to {dest}"
        
        elif operation == 'read':
            return path.read_text()
        
        elif operation == 'list':
            if path.is_dir():
                return [item.name for item in path.iterdir()]
            else:
                return [path.name]
        
        else:
            raise ValueError(f"Unknown file operation: {operation}")
    
    async def _execute_application(self, action: str, app_name: str, **kwargs) -> str:
        """Execute application operations"""
        if action == 'open':
            # Try different methods to open application
            commands = [
                f"gtk-launch {app_name}",
                f"{app_name}",
                f"xdg-open {app_name}"
            ]
            
            for cmd in commands:
                try:
                    await self._execute_system_command(cmd, timeout=5)
                    return f"Opened {app_name}"
                except:
                    continue
            
            raise RuntimeError(f"Could not open {app_name}")
        
        elif action == 'close':
            await self._execute_system_command(f"pkill -f '{app_name}'")
            return f"Closed {app_name}"
        
        elif action == 'focus':
            await self._execute_system_command(f"wmctrl -a '{app_name}'")
            return f"Focused {app_name}"
        
        else:
            raise ValueError(f"Unknown application action: {action}")
    
    async def _execute_network(self, action: str, **kwargs) -> Any:
        """Execute network operations"""
        if action == 'check_connectivity':
            try:
                await self._execute_system_command("ping -c 1 8.8.8.8", timeout=5)
                return True
            except:
                return False
        
        elif action == 'get_ip':
            result = await self._execute_system_command("hostname -I")
            return result.strip()
        
        elif action == 'scan_networks':
            # Scan WiFi networks
            try:
                result = await self._execute_system_command("nmcli dev wifi list")
                return result
            except:
                return "Network scanning not available"
        
        else:
            raise ValueError(f"Unknown network action: {action}")
    
    async def _execute_system_info(self, info_type: str, **kwargs) -> Any:
        """Get system information"""
        import psutil
        
        if info_type == 'cpu':
            return {
                'usage_percent': psutil.cpu_percent(interval=1),
                'count': psutil.cpu_count(),
                'frequency': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            }
        
        elif info_type == 'memory':
            memory = psutil.virtual_memory()
            return {
                'total': memory.total,
                'available': memory.available,
                'used': memory.used,
                'percent': memory.percent
            }
        
        elif info_type == 'disk':
            disk = psutil.disk_usage('/')
            return {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': (disk.used / disk.total) * 100
            }
        
        elif info_type == 'battery':
            battery = psutil.sensors_battery()
            if battery:
                return {
                    'percent': battery.percent,
                    'plugged': battery.power_plugged,
                    'time_left': battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None
                }
            else:
                return {'message': 'No battery detected'}
        
        elif info_type == 'temperature':
            temps = psutil.sensors_temperatures()
            if temps:
                return {name: [{'temp': temp.current, 'label': temp.label} 
                              for temp in temps] for name, temps in temps.items()}
            else:
                return {'message': 'No temperature sensors'}
        
        else:
            raise ValueError(f"Unknown system info type: {info_type}")
    
    async def _execute_user_interaction(self, action: str, **kwargs) -> Any:
        """Execute user interaction tasks"""
        if action == 'notification':
            title = kwargs.get('title', 'Aurora OS')
            message = kwargs.get('message', '')
            
            # Try different notification methods
            try:
                await self._execute_system_command(
                    f'notify-send "{title}" "{message}"'
                )
                return "Notification sent"
            except:
                return "Could not send notification"
        
        elif action == 'dialog':
            # Use zenity for dialogs
            dialog_type = kwargs.get('type', 'info')
            title = kwargs.get('title', 'Aurora OS')
            text = kwargs.get('text', '')
            
            try:
                cmd = f'zenity --{dialog_type} --title="{title}" --text="{text}"'
                result = await self._execute_system_command(cmd)
                return result
            except:
                return "Could not show dialog"
        
        else:
            raise ValueError(f"Unknown user interaction action: {action}")
    
    async def _execute_automation(self, action: str, **kwargs) -> Any:
        """Execute automation tasks"""
        if action == 'schedule_task':
            task_name = kwargs.get('task_name')
            schedule_time = kwargs.get('schedule_time')
            command = kwargs.get('command')
            
            # Create systemd timer or cron job
            cron_entry = f"{schedule_time} {command}"
            
            try:
                await self._execute_system_command(
                    f'(echo "{cron_entry}" | crontab -)',
                    shell=True
                )
                return f"Scheduled task: {task_name}"
            except:
                return "Could not schedule task"
        
        elif action == 'create_shortcut':
            name = kwargs.get('name')
            command = kwargs.get('command')
            icon = kwargs.get('icon', '')
            
            desktop_file = f"""
[Desktop Entry]
Version=1.0
Type=Application
Name={name}
Exec={command}
Icon={icon}
Terminal=false
"""
            
            desktop_path = Path.home() / "Desktop" / f"{name}.desktop"
            desktop_path.write_text(desktop_file.strip())
            desktop_path.chmod(0o755)
            
            return f"Created shortcut: {desktop_path}"
        
        else:
            raise ValueError(f"Unknown automation action: {action}")

class TaskAgent:
    """
    Agentic AI system for task execution
    Can understand complex requests and break them down into executable steps
    """
    
    def __init__(self):
        self.executor = TaskExecutor()
        self.active_tasks: Dict[str, Task] = {}
        self.task_history: List[Task] = []
        self.max_history = 100
        
        self.logger = logging.getLogger("Aurora.TaskAgent")
        self._setup_logging()
        
        # Task templates for common operations
        self.task_templates = self._load_task_templates()
    
    def _setup_logging(self):
        """Setup logging"""
        log_dir = Path("/var/log/aurora")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(log_dir / "task_agent.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _load_task_templates(self) -> Dict[str, Dict]:
        """Load task templates for common operations"""
        return {
            'fix_slow_system': {
                'description': 'Optimize system performance',
                'steps': [
                    {'action': 'system_info', 'description': 'Check system resource usage', 'parameters': {'info_type': 'cpu'}},
                    {'action': 'system_info', 'description': 'Check memory usage', 'parameters': {'info_type': 'memory'}},
                    {'action': 'system_command', 'description': 'Clean temporary files', 'parameters': {'command': 'rm -rf /tmp/*'}},
                    {'action': 'system_command', 'description': 'Clear package cache', 'parameters': {'command': 'apt clean'}},
                ]
            },
            'setup_development_environment': {
                'description': 'Set up development environment',
                'steps': [
                    {'action': 'system_command', 'description': 'Update package lists', 'parameters': {'command': 'apt update'}},
                    {'action': 'system_command', 'description': 'Install development tools', 'parameters': {'command': 'apt install -y git vim python3 nodejs'}},
                    {'action': 'file_operation', 'description': 'Create projects directory', 'parameters': {'operation': 'create', 'path': '~/Projects'}},
                ]
            },
            'backup_user_data': {
                'description': 'Backup important user data',
                'steps': [
                    {'action': 'file_operation', 'description': 'Create backup directory', 'parameters': {'operation': 'create', 'path': '~/Backups'}},
                    {'action': 'file_operation', 'description': 'Copy documents', 'parameters': {'operation': 'copy', 'path': '~/Documents', 'destination': '~/Backups/Documents'}},
                    {'action': 'file_operation', 'description': 'Copy pictures', 'parameters': {'operation': 'copy', 'path': '~/Pictures', 'destination': '~/Backups/Pictures'}},
                ]
            },
            'optimize_battery_life': {
                'description': 'Optimize settings for battery life',
                'steps': [
                    {'action': 'system_info', 'description': 'Check battery status', 'parameters': {'info_type': 'battery'}},
                    {'action': 'system_command', 'description': 'Reduce screen brightness', 'parameters': {'command': 'brightnessctl set 50%'}},
                    {'action': 'system_command', 'description': 'Enable power saving mode', 'parameters': {'command': 'systemctl enable power-profiles-daemon'}},
                ]
            }
        }
    
    async def identify_tasks(self, user_input: str, ai_response: str) -> List[Task]:
        """Identify executable tasks from user input and AI response"""
        tasks = []
        
        # Analyze user input for task keywords
        user_lower = user_input.lower()
        
        # Check for task templates
        for template_name, template in self.task_templates.items():
            if self._matches_template(user_lower, template_name):
                task = await self._create_task_from_template(template_name, template)
                tasks.append(task)
        
        # Check for specific patterns
        if 'open' in user_lower:
            app_name = self._extract_app_name(user_input)
            if app_name:
                task = await self._create_app_open_task(app_name)
                tasks.append(task)
        
        if 'fix' in user_lower or 'optimize' in user_lower:
            task = await self._create_system_optimization_task(user_input)
            tasks.append(task)
        
        if 'backup' in user_lower:
            task = await self._create_backup_task(user_input)
            tasks.append(task)
        
        if 'install' in user_lower:
            package = self._extract_package_name(user_input)
            if package:
                task = await self._create_install_task(package)
                tasks.append(task)
        
        # Check AI response for action items
        ai_tasks = await self._extract_tasks_from_ai_response(ai_response)
        tasks.extend(ai_tasks)
        
        return tasks
    
    def _matches_template(self, user_input: str, template_name: str) -> bool:
        """Check if user input matches a task template"""
        keywords = {
            'fix_slow_system': ['slow', 'performance', 'optimize', 'speed'],
            'setup_development_environment': ['development', 'programming', 'coding', 'dev'],
            'backup_user_data': ['backup', 'save', 'copy files'],
            'optimize_battery_life': ['battery', 'power', 'energy', 'life']
        }
        
        template_keywords = keywords.get(template_name, [])
        return any(keyword in user_input for keyword in template_keywords)
    
    async def _create_task_from_template(self, template_name: str, template: Dict) -> Task:
        """Create task from template"""
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{template_name}"
        
        steps = []
        for i, step_data in enumerate(template['steps']):
            step = TaskStep(
                id=f"{task_id}_step_{i}",
                description=step_data['description'],
                action=step_data['action'],
                parameters=step_data.get('parameters', {})
            )
            steps.append(step)
        
        return Task(
            id=task_id,
            title=template_name.replace('_', ' ').title(),
            description=template['description'],
            steps=steps
        )
    
    async def _create_app_open_task(self, app_name: str) -> Task:
        """Create task to open application"""
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_open_app"
        
        step = TaskStep(
            id=f"{task_id}_step_0",
            description=f"Open {app_name}",
            action="application",
            parameters={"action": "open", "app_name": app_name}
        )
        
        return Task(
            id=task_id,
            title=f"Open {app_name}",
            description=f"Open the {app_name} application",
            steps=[step]
        )
    
    async def _create_system_optimization_task(self, user_input: str) -> Task:
        """Create system optimization task"""
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_optimize"
        
        steps = [
            TaskStep(
                id=f"{task_id}_step_0",
                description="Check system resource usage",
                action="system_info",
                parameters={"info_type": "cpu"}
            ),
            TaskStep(
                id=f"{task_id}_step_1",
                description="Check memory usage",
                action="system_info",
                parameters={"info_type": "memory"}
            ),
            TaskStep(
                id=f"{task_id}_step_2",
                description="Clean temporary files",
                action="system_command",
                parameters={"command": "find /tmp -type f -delete"}
            )
        ]
        
        return Task(
            id=task_id,
            title="System Optimization",
            description="Optimize system performance based on user request",
            steps=steps
        )
    
    async def _create_backup_task(self, user_input: str) -> Task:
        """Create backup task"""
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_backup"
        
        steps = [
            TaskStep(
                id=f"{task_id}_step_0",
                description="Create backup directory",
                action="file_operation",
                parameters={"operation": "create", "path": "~/Backups"}
            )
        ]
        
        # Add steps for backing up specific directories
        if 'documents' in user_input.lower():
            steps.append(TaskStep(
                id=f"{task_id}_step_1",
                description="Backup documents",
                action="file_operation",
                parameters={"operation": "copy", "path": "~/Documents", "destination": "~/Backups/Documents"}
            ))
        
        if 'pictures' in user_input.lower():
            steps.append(TaskStep(
                id=f"{task_id}_step_2",
                description="Backup pictures",
                action="file_operation",
                parameters={"operation": "copy", "path": "~/Pictures", "destination": "~/Backups/Pictures"}
            ))
        
        return Task(
            id=task_id,
            title="Backup Data",
            description="Backup user data as requested",
            steps=steps
        )
    
    async def _create_install_task(self, package: str) -> Task:
        """Create package installation task"""
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_install"
        
        steps = [
            TaskStep(
                id=f"{task_id}_step_0",
                description=f"Update package lists",
                action="system_command",
                parameters={"command": "apt update"}
            ),
            TaskStep(
                id=f"{task_id}_step_1",
                description=f"Install {package}",
                action="system_command",
                parameters={"command": f"apt install -y {package}"}
            )
        ]
        
        return Task(
            id=task_id,
            title=f"Install {package}",
            description=f"Install {package} package",
            steps=steps
        )
    
    def _extract_app_name(self, user_input: str) -> Optional[str]:
        """Extract application name from user input"""
        import re
        
        # Look for "open <app>" pattern
        match = re.search(r'open\s+(\w+)', user_input.lower())
        if match:
            return match.group(1)
        
        return None
    
    def _extract_package_name(self, user_input: str) -> Optional[str]:
        """Extract package name from user input"""
        import re
        
        # Look for "install <package>" pattern
        match = re.search(r'install\s+(\w+)', user_input.lower())
        if match:
            return match.group(1)
        
        return None
    
    async def _extract_tasks_from_ai_response(self, ai_response: str) -> List[Task]:
        """Extract executable tasks from AI response"""
        tasks = []
        
        # Look for action items in AI response
        response_lower = ai_response.lower()
        
        # Simple pattern matching for now
        if "i'll" in response_lower or "i will" in response_lower:
            # Extract action after "I'll" or "I will"
            import re
            match = re.search(r'(?:i\'ll|i will)\s+(.+)', response_lower)
            if match:
                action = match.group(1).strip()
                if "open" in action:
                    app_name = self._extract_app_name(action)
                    if app_name:
                        task = await self._create_app_open_task(app_name)
                        tasks.append(task)
        
        return tasks
    
    async def execute_task(self, task: Task) -> str:
        """Execute a complete task"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        self.active_tasks[task.id] = task
        self.logger.info(f"Executing task: {task.title}")
        
        try:
            results = []
            
            # Execute steps in order (could add dependency resolution later)
            for step in task.steps:
                if step.status == TaskStatus.PENDING:
                    result = await self.executor.execute_step(step)
                    results.append(result)
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = results
            
            # Move from active to history
            if task.id in self.active_tasks:
                del self.active_tasks[task.id]
            
            self.task_history.append(task)
            if len(self.task_history) > self.max_history:
                self.task_history.pop(0)
            
            return f"Task completed successfully: {task.title}"
        
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.error = str(e)
            
            # Move from active to history
            if task.id in self.active_tasks:
                del self.active_tasks[task.id]
            
            self.task_history.append(task)
            if len(self.task_history) > self.max_history:
                self.task_history.pop(0)
            
            raise
    
    def get_active_tasks(self) -> List[Task]:
        """Get list of active tasks"""
        return list(self.active_tasks.values())
    
    def get_task_history(self) -> List[Task]:
        """Get task history"""
        return self.task_history.copy()
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            
            del self.active_tasks[task_id]
            self.task_history.append(task)
            
            return True
        return False
    
    def get_task_status(self, task_id: str) -> Optional[Task]:
        """Get status of a specific task"""
        return self.active_tasks.get(task_id)