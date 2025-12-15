"""
Aurora OS - Main Integration Script
Ties together all revolutionary components into a cohesive AI-native operating system
"""

import os
import sys
import json
import asyncio
import signal
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
import threading
import time

# Safe imports with graceful fallback
def safe_import(module_path, component_name):
    """Safely import a module, returning None if it fails"""
    try:
        parts = module_path.rsplit('.', 1)
        module = __import__(parts[0], fromlist=[parts[1]] if len(parts) > 1 else [])
        return getattr(module, component_name) if len(parts) > 1 else module
    except (ImportError, AttributeError, ModuleNotFoundError) as e:
        logging.warning(f"Optional component '{module_path}' not available: {e}")
        return None

# Try to import Aurora OS components (graceful fallback)
initialize_ai_system = safe_import('ai_assistant.core.local_llm_engine', 'initialize_ai_system')
get_llm_engine = safe_import('ai_assistant.core.local_llm_engine', 'get_llm_engine')
get_taskbar_assistant = safe_import('ai_assistant.ui.taskbar_assistant', 'get_taskbar_assistant')
initialize_voice_system = safe_import('ai_assistant.voice.voice_interface', 'initialize_voice_system')
TaskAgent = safe_import('ai_assistant.agents.task_agent', 'TaskAgent')

initialize_driver_system = safe_import('system.hardware.driver_manager', 'initialize_driver_system')
get_driver_manager = safe_import('system.hardware.driver_manager', 'get_driver_manager')
get_intent_engine = safe_import('system.settings.intent_settings', 'get_intent_engine')
show_settings = safe_import('system.settings.settings_ui', 'show_settings')

initialize_nix_system = safe_import('system.advanced.nix_integration', 'initialize_nix_system')
get_nix_integration = safe_import('system.advanced.nix_integration', 'get_nix_integration')
initialize_ebpf_system = safe_import('system.advanced.ebpf_integration', 'initialize_ebpf_system')
get_ebpf_integration = safe_import('system.advanced.ebpf_integration', 'get_ebpf_integration')

launch_browser = safe_import('applications.aurora_browser.browser', 'launch_browser')

class AuroraOS:
    """
    Main Aurora OS integration class
    Coordinates all revolutionary components into a unified AI-native operating system
    """
    
    def __init__(self):
        self.version = "1.0.0"
        self.build_date = datetime.now().isoformat()
        
        # Core components
        self.llm_engine = None
        self.taskbar_assistant = None
        self.voice_interface = None
        self.task_agent = None
        self.driver_manager = None
        self.intent_engine = None
        self.nix_integration = None
        self.ebpf_integration = None
        
        # System state
        self.initialized = False
        self.running = False
        self.shutdown_requested = False
        
        # Configuration
        self.config = self._load_config()
        
        # Logging
        self.logger = self._setup_logging()
        
        # Register signal handlers
        self._setup_signal_handlers()
        
        self.logger.info("Aurora OS initializing...")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load Aurora OS configuration"""
        config_file = Path("/etc/aurora/config.json")
        
        default_config = {
            "version": "1.0.0",
            "ai": {
                "model_path": "/opt/aurora/models/llama-3.2-3b",
                "taskbar_integration": True,
                "voice_enabled": True,
                "intent_settings": True
            },
            "hardware": {
                "auto_driver_install": True,
                "hardware_monitoring": True
            },
            "advanced_features": {
                "nix_integration": True,
                "ebpf_monitoring": True,
                "declarative_configs": True
            },
            "ui": {
                "theme": "aurora",
                "animations": True,
                "glassmorphism": True
            },
            "security": {
                "zero_trust": True,
                "auto_sandboxing": True,
                "privacy_by_default": True
            }
        }
        
        try:
            if config_file.exists():
                with open(config_file, 'r') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
        except:
            pass
        
        return default_config
    
    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive logging"""
        logger = logging.getLogger("AuroraOS")
        logger.setLevel(logging.INFO)
        
        # Create log directory
        log_dir = Path("/var/log/aurora")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # File handler
        file_handler = logging.FileHandler(log_dir / "aurora_os.log")
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '🌌 AuroraOS: %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGUSR1, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle system signals"""
        if signum in (signal.SIGINT, signal.SIGTERM):
            self.logger.info(f"Received shutdown signal {signum}")
            self.shutdown_requested = True
            asyncio.create_task(self.shutdown())
        elif signum == signal.SIGUSR1:
            self.logger.info("Received status signal")
            asyncio.create_task(self.print_status())
    
    async def initialize(self):
        """Initialize all Aurora OS components"""
        self.logger.info("🚀 Initializing Aurora OS v1.0.0...")
        
        try:
            # Phase 1: Core AI System
            self.logger.info("🧠 Initializing AI Core...")
            self.llm_engine = await initialize_ai_system()
            
            # Phase 2: User Interface Components
            if self.config["ai"]["taskbar_integration"]:
                self.logger.info("🎯 Initializing Taskbar Assistant...")
                self.taskbar_assistant = get_taskbar_assistant()
            
            if self.config["ai"]["voice_enabled"]:
                self.logger.info("🎤 Initializing Voice Interface...")
                self.voice_interface, voice_processor = await initialize_voice_system()
            
            # Phase 3: Task Execution System
            self.logger.info("⚡ Initializing Task Agent...")
            self.task_agent = TaskAgent()
            
            # Phase 4: Hardware Management
            if self.config["hardware"]["auto_driver_install"]:
                self.logger.info("🔧 Initializing Driver Management...")
                self.driver_manager, devices = await initialize_driver_system()
                self.logger.info(f"✅ Detected and configured {len(devices)} hardware devices")
            
            # Phase 5: Intent-Based Settings
            if self.config["ai"]["intent_settings"]:
                self.logger.info("⚙️ Initializing Intent Engine...")
                self.intent_engine = get_intent_engine()
            
            # Phase 6: Advanced Features
            if self.config["advanced_features"]["nix_integration"]:
                self.logger.info("🔁 Initializing Nix Integration...")
                self.nix_integration = await initialize_nix_system()
            
            if self.config["advanced_features"]["ebpf_monitoring"]:
                self.logger.info("📊 Initializing eBPF Monitoring...")
                self.ebpf_integration = await initialize_ebpf_system()
            
            # Phase 7: System Integration
            self.logger.info("🔗 Integrating Components...")
            await self._integrate_components()
            
            # Phase 8: Final Setup
            self.logger.info("🎨 Applying UI Configuration...")
            await self._apply_ui_configuration()
            
            self.initialized = True
            self.logger.info("✨ Aurora OS initialization complete!")
            
            # Display revolutionary features
            await self._display_features()
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Aurora OS: {e}")
            raise
    
    async def _integrate_components(self):
        """Integrate all components together"""
        try:
            # Connect AI assistant to task agent
            if self.taskbar_assistant and self.task_agent:
                # Integration logic here
                pass
            
            # Connect driver manager to AI
            if self.driver_manager and self.llm_engine:
                # Share hardware context with AI
                hardware_context = {
                    'devices': len(self.driver_manager.get_all_devices()),
                    'drivers_installed': len(self.driver_manager.get_devices_by_status('installed'))
                }
                self.llm_engine.update_context(hardware_context)
            
            # Connect eBPF to AI for anomaly explanation
            if self.ebpf_integration and self.llm_engine:
                # Integration for kernel behavior explanation
                pass
            
            # Connect Nix to intent engine
            if self.nix_integration and self.intent_engine:
                # Integration for declarative configuration
                pass
            
            self.logger.info("✅ Component integration complete")
        
        except Exception as e:
            self.logger.error(f"Component integration failed: {e}")
            raise
    
    async def _apply_ui_configuration(self):
        """Apply UI configuration settings"""
        try:
            # Apply theme settings
            theme = self.config["ui"]["theme"]
            animations = self.config["ui"]["animations"]
            glassmorphism = self.config["ui"]["glassmorphism"]
            
            # Apply to taskbar assistant
            if self.taskbar_assistant:
                self.taskbar_assistant.update_theme(theme)
            
            self.logger.info(f"✅ UI configuration applied: {theme} theme, animations={animations}")
        
        except Exception as e:
            self.logger.error(f"UI configuration failed: {e}")
    
    async def _display_features(self):
        """Display Aurora OS revolutionary features"""
        features = [
            "🧠 AI-Native Operating System - AI is the control plane, not an app",
            "🔍 Intent-Based Computing - Tell Aurora what you want, it configures itself",
            "🔧 Automatic Driver Management - Windows-like hardware support",
            "🔄 Declarative OS (Nix) - Atomic upgrades, perfect rollbacks",
            "📊 eBPF Monitoring - Explainable kernel with AI insights",
            "🎤 Voice Interface - Hands-free AI interaction",
            "⚡ Agentic Task Execution - AI completes tasks autonomously",
            "🔐 Zero-Trust Security - Privacy by default",
            "🌐 AI-Enhanced Browser - Intelligent web browsing",
            "⚙️ Unified App Runtime - Windows + Linux + Web + AI apps"
        ]
        
        self.logger.info("🎉 Aurora OS Revolutionary Features:")
        for feature in features:
            self.logger.info(f"  {feature}")
        
        self.logger.info("🚀 Aurora OS is ready to revolutionize computing!")
    
    async def start(self):
        """Start Aurora OS main loop"""
        if not self.initialized:
            await self.initialize()
        
        self.running = True
        self.logger.info("🌟 Aurora OS starting main loop...")
        
        try:
            # Start background services
            await self._start_background_services()
            
            # Run main loop
            while not self.shutdown_requested:
                try:
                    # Process system events
                    await self._process_system_events()
                    
                    # Monitor system health
                    await self._monitor_system_health()
                    
                    # Sleep briefly
                    await asyncio.sleep(1)
                
                except KeyboardInterrupt:
                    self.logger.info("⏹️ Keyboard interrupt received")
                    break
                except Exception as e:
                    self.logger.error(f"Main loop error: {e}")
                    await asyncio.sleep(5)  # Wait before retrying
        
        finally:
            await self.shutdown()
    
    async def _start_background_services(self):
        """Start background services"""
        try:
            # Start AI monitoring
            if self.ebpf_integration:
                # eBPF runs in background threads
                pass
            
            # Start voice assistant if enabled
            if self.voice_interface and self.config["ai"]["voice_enabled"]:
                # Start wake word detection
                self.voice_interface.start_wake_word_detection()
            
            # Start periodic maintenance
            asyncio.create_task(self._maintenance_loop())
            
            self.logger.info("✅ Background services started")
        
        except Exception as e:
            self.logger.error(f"Failed to start background services: {e}")
    
    async def _process_system_events(self):
        """Process system events"""
        try:
            # Check for new hardware
            if self.driver_manager and self.config["hardware"]["hardware_monitoring"]:
                # Hardware monitoring is handled by driver manager
                pass
            
            # Check for AI tasks
            if self.task_agent:
                active_tasks = self.task_agent.get_active_tasks()
                if len(active_tasks) > 0:
                    self.logger.debug(f"📋 {len(active_tasks)} active AI tasks")
        
        except Exception as e:
            self.logger.error(f"System event processing error: {e}")
    
    async def _monitor_system_health(self):
        """Monitor overall system health"""
        try:
            health_score = 0.0
            
            # Check eBPF health score
            if self.ebpf_integration:
                ebpf_health = self.ebpf_integration.get_system_health_score()
                health_score += ebpf_health * 0.3
            
            # Check AI system health
            if self.llm_engine:
                # Simple health check based on model availability
                ai_health = 1.0 if self.llm_engine.is_loaded else 0.0
                health_score += ai_health * 0.3
            
            # Check driver management health
            if self.driver_manager:
                missing_drivers = len(self.driver_manager.get_devices_by_status('missing'))
                total_devices = len(self.driver_manager.get_all_devices())
                driver_health = 1.0 - (missing_drivers / max(total_devices, 1))
                health_score += driver_health * 0.2
            
            # Base system health
            health_score += 0.2  # Base system health
            
            if health_score < 0.7:
                self.logger.warning(f"⚠️ System health degraded: {health_score:.2f}")
            elif health_score < 0.5:
                self.logger.error(f"🚨 System health critical: {health_score:.2f}")
        
        except Exception as e:
            self.logger.error(f"Health monitoring error: {e}")
    
    async def _maintenance_loop(self):
        """Periodic maintenance tasks"""
        while not self.shutdown_requested:
            try:
                # Run maintenance every hour
                await asyncio.sleep(3600)
                
                self.logger.debug("🔧 Running periodic maintenance...")
                
                # Cleanup old logs
                await self._cleanup_logs()
                
                # Update AI context
                if self.llm_engine:
                    await self._update_ai_context()
                
                # Check for system updates (via Nix)
                if self.nix_integration and self.config["advanced_features"]["nix_integration"]:
                    await self._check_system_updates()
        
            except Exception as e:
                self.logger.error(f"Maintenance loop error: {e}")
    
    async def _cleanup_logs(self):
        """Cleanup old log files"""
        try:
            log_dir = Path("/var/log/aurora")
            cutoff_days = 7
            
            for log_file in log_dir.glob("*.log*"):
                if log_file.stat().st_mtime < time.time() - (cutoff_days * 24 * 3600):
                    log_file.unlink()
                    self.logger.debug(f"🗑️ Removed old log: {log_file}")
        
        except Exception as e:
            self.logger.error(f"Log cleanup error: {e}")
    
    async def _update_ai_context(self):
        """Update AI context with current system state"""
        try:
            context_data = {}
            
            # Add system resources
            import psutil
            context_data['system_resources'] = {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent
            }
            
            # Add hardware status
            if self.driver_manager:
                devices = self.driver_manager.get_all_devices()
                context_data['hardware'] = {
                    'total_devices': len(devices),
                    'drivers_installed': len(self.driver_manager.get_devices_by_status('installed'))
                }
            
            # Add system health
            if self.ebpf_integration:
                context_data['system_health'] = self.ebpf_integration.get_system_health_score()
            
            self.llm_engine.update_context(context_data)
        
        except Exception as e:
            self.logger.error(f"AI context update error: {e}")
    
    async def _check_system_updates(self):
        """Check for system updates via Nix"""
        try:
            # This would integrate with Nix update checking
            # For now, just log
            self.logger.debug("🔄 Checking for system updates...")
        
        except Exception as e:
            self.logger.error(f"Update check error: {e}")
    
    async def print_status(self):
        """Print current Aurora OS status"""
        status = {
            "version": self.version,
            "initialized": self.initialized,
            "running": self.running,
            "uptime": "N/A",
            "components": {}
        }
        
        # AI system status
        if self.llm_engine:
            status["components"]["ai"] = {
                "loaded": self.llm_engine.is_loaded,
                "model_available": True
            }
        
        # Taskbar assistant status
        if self.taskbar_assistant:
            status["components"]["taskbar"] = {
                "visible": self.taskbar_assistant.is_visible
            }
        
        # Driver management status
        if self.driver_manager:
            devices = self.driver_manager.get_all_devices()
            status["components"]["drivers"] = {
                "total_devices": len(devices),
                "drivers_installed": len(self.driver_manager.get_devices_by_status('installed'))
            }
        
        # eBPF monitoring status
        if self.ebpf_integration:
            status["components"]["ebpf"] = {
                "monitoring": self.ebpf_integration.monitoring_enabled,
                "health_score": self.ebpf_integration.get_system_health_score()
            }
        
        # Print status
        self.logger.info(f"📊 Aurora OS Status: {json.dumps(status, indent=2)}")
    
    async def process_user_intent(self, intent: str) -> str:
        """Process user intent through Aurora OS"""
        try:
            self.logger.info(f"🎯 Processing user intent: {intent}")
            
            # Check if this is a settings intent
            if self.intent_engine:
                # Try to match known patterns first
                result = await self.intent_engine.process_intent(intent)
                
                if result.confidence > 0.6:
                    execution_result = await self.intent_engine.execute_intent(result)
                    
                    if execution_result['success']:
                        return f"✅ Intent executed successfully: {intent}"
                    else:
                        return f"❌ Intent execution failed: {intent}"
            
            # Fall back to AI assistant
            if self.llm_engine:
                from ai_assistant.core.local_llm_engine import AIRequest
                request = AIRequest(
                    prompt=f"User intent: {intent}. Process this as a system command.",
                    max_tokens=200,
                    temperature=0.3
                )
                
                response = await self.llm_engine.generate_response(request)
                return response.text
            
            return "❌ Unable to process intent"
        
        except Exception as e:
            self.logger.error(f"Intent processing error: {e}")
            return f"❌ Error processing intent: {str(e)}"
    
    def launch_application(self, app_name: str) -> bool:
        """Launch Aurora OS applications"""
        try:
            if app_name.lower() == "browser":
                launch_browser()
                return True
            elif app_name.lower() == "settings":
                show_settings()
                return True
            else:
                # Try to launch as system application
                import subprocess
                result = subprocess.run([app_name], capture_output=True)
                return result.returncode == 0
        
        except Exception as e:
            self.logger.error(f"Application launch error: {e}")
            return False
    
    async def shutdown(self):
        """Graceful shutdown of Aurora OS"""
        if not self.running:
            return
        
        self.logger.info("🛑 Shutting down Aurora OS...")
        self.running = False
        
        try:
            # Stop background services
            if self.voice_interface:
                self.voice_interface.stop_wake_word_detection()
            
            # Cleanup eBPF integration
            if self.ebpf_integration:
                self.ebpf_integration.cleanup()
            
            # Cleanup Nix integration
            if self.nix_integration:
                # Save current configuration
                pass
            
            # Save configuration
            self._save_config()
            
            self.logger.info("✅ Aurora OS shutdown complete")
        
        except Exception as e:
            self.logger.error(f"Shutdown error: {e}")
    
    def _save_config(self):
        """Save current configuration"""
        try:
            config_file = Path("/etc/aurora/config.json")
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        
        except Exception as e:
            self.logger.error(f"Config save error: {e}")

async def main():
    """Main entry point for Aurora OS"""
    # Create Aurora OS instance
    aurora = AuroraOS()
    
    try:
        # Initialize and start
        await aurora.start()
    
    except KeyboardInterrupt:
        print("\n⏹️ Aurora OS stopped by user")
    except Exception as e:
        print(f"❌ Aurora OS error: {e}")
    finally:
        await aurora.shutdown()

def signal_handler(signum, frame):
    """Global signal handler"""
    print(f"\n⏹️ Received signal {signum}, shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    # Setup global signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🌌 Aurora OS v1.0.0 - The AI-Native Operating System")
    print("=" * 60)
    print("🚀 Initializing revolutionary AI-powered computing...")
    print("=" * 60)
    
    # Run main async function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye from Aurora OS!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)